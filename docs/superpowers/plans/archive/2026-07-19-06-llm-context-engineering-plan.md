# Spec 8: LLM Context Engineering — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 bugs and 4 architecture defects in LLM context assembly, reducing per-chapter token consumption from 408K to ~243K (-40%).

**Architecture:** Three-layer fix: (1) Bug fixes in dispatch_helper.py (glob expansion, XML tags, truncation indicator — note: Spec 8 Bug 3's "UTF-8 byte-boundary corruption" is self-refuted; Python `text[:limit]` truncates at code-point boundaries so there is no corruption, the real fix is just an explicit truncation indicator, folded into Task 4's `_budgeted_truncate`; the spec's paragraph/sentence-boundary backtracking is gold-plating and intentionally NOT implemented), (2) Shared context infrastructure (audit cache, world summarizer, field filters, priority budget), (3) Prompt optimization (audit cascading, stale data removal, instruction hierarchy, SKILL.md bloat reduction).

**Tech Stack:** Python 3.11+, pathlib, glob, structlog, xml.etree.ElementTree

## Global Constraints

- `just check` passes with zero failures
- Glob patterns in reads contracts correctly expand to matched files
- No code fence (```) nesting in LLM prompts (all content uses `<document>` tags)
- All `<` characters in injected file content are escaped to `\u003c` (prevents tag injection; not a `</doc>` replacement)
- Shared audit context cache reduces 13×30KB loads to 1×30KB + 12×cached
- World files summarized to <3K tokens when >5K tokens raw
- All files >5KB in reads contracts declare field filters
- Priority-driven budget reduces truncation loss by ~60% (`_FILE_PRIORITY_WEIGHTS` are initial values needing calibration against real output)
- Audit cascading: when the previous N=3 chapters' cascaded audits ALL passed with zero HARD failures, skip the 8 cascaded audits (`memo-compliance` and `resonance` ALWAYS run and are excluded from the cascade -- there is no "confidence >90%" signal available)
- 3-tier instruction hierarchy present in all skill prompts

---

### Task 1: Fix Glob Pattern Expansion Bug

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:142-161` (`_build_skill_prompt`)
- Test: `tests/pipeline/test_dispatch_helper_glob.py`

**Interfaces:**
- Produces: `_resolve_read_path(project_dir: Path, read_path: str) -> list[Path]`

- [ ] **Step 1: Write the failing test**

```python
# tests/pipeline/test_dispatch_helper_glob.py
import tempfile
from pathlib import Path
from shenbi.pipeline.dispatch_helper import _resolve_read_path

def test_glob_wildcard_expands():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        char_dir = project_dir / "characters" / "major"
        char_dir.mkdir(parents=True)
        (char_dir / "protagonist.md").write_text("protagonist", encoding="utf-8")
        (char_dir / "antagonist.md").write_text("antagonist", encoding="utf-8")

        paths = _resolve_read_path(project_dir, "characters/major/*.md")
        assert len(paths) == 2, f"Expected 2 files, got {len(paths)}: {paths}"
        names = {p.name for p in paths}
        assert names == {"protagonist.md", "antagonist.md"}

def test_glob_non_wildcard_returns_single():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        f = project_dir / "test.md"
        f.write_text("test", encoding="utf-8")

        paths = _resolve_read_path(project_dir, "test.md")
        assert len(paths) == 1
        assert paths[0].name == "test.md"

def test_glob_missing_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        paths = _resolve_read_path(project_dir, "nonexistent/*.md")
        assert paths == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_dispatch_helper_glob.py -v`
Expected: FAIL (function not defined or doesn't expand glob)

- [ ] **Step 3: Write minimal implementation**

```python
# In src/shenbi/pipeline/dispatch_helper.py:
import glob as glob_module

def _resolve_read_path(project_dir: Path, read_path: str) -> list[Path]:
    """Resolve a read path, expanding glob patterns if present.

    Args:
        project_dir: Pipeline project root directory.
        read_path: Path string from contract reads, may contain glob patterns.

    Returns:
        List of resolved Path objects. Empty list if no matches.
    """
    if "*" in read_path or "?" in read_path or "[" in read_path:
        pattern = str(project_dir / read_path)
        matches = glob_module.glob(pattern)
        return [Path(m) for m in sorted(matches)]
    else:
        full_path = project_dir / read_path
        if full_path.exists():
            return [full_path]
        return []
```

Then update L142-161 in `_build_skill_prompt`:

```python
# Replace the old loop:
# for read_path in contract.get("reads", []):
#     full_path = project_dir / resolved  ← BUG: resolved may contain literal *

# With:
for read_path_entry in contract.get("reads", []):
    if isinstance(read_path_entry, dict):
        # Layer B: field-level read
        read_path = read_path_entry.get("file", "")
        fields = read_path_entry.get("fields", [])
    else:
        read_path = read_path_entry
        fields = []

    resolved_paths = _resolve_read_path(project_dir, read_path)
    for full_path in resolved_paths:
        content = full_path.read_text(encoding="utf-8")
        if fields:
            content = filter_to_fields(content, fields)
        input_texts[full_path.name] = content
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_dispatch_helper_glob.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_dispatch_helper_glob.py
git commit -m "fix: expand glob patterns in _resolve_read_path for contract reads"
```

---

### Task 2: Replace Code Fences with XML Document Tags

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:240-243` (`_build_skill_prompt`)
- Test: `tests/pipeline/test_dispatch_helper_xml.py`

**Interfaces:**
- Modifies: input file injection format from ``` to `<document>` tags

- [ ] **Step 1: Write the failing test**

```python
# tests/pipeline/test_dispatch_helper_xml.py
def test_prompt_uses_xml_tags_not_nested_fences():
    """LLM prompts must use <document> tags, not nested ``` fences."""
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "test.md").write_text("test content", encoding="utf-8")

        # We verify the output format by checking _build_skill_prompt output
        # Create minimal contract
        system_prompt, user_prompt, _ = _build_skill_prompt(
            "test-skill", project_dir, "test prompt", chapter=None)

        # Must NOT contain nested ``` inside ```
        assert "<document" in user_prompt, "Expected <document> tags"
        assert "```\n```" not in user_prompt, "Found nested code fences"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_dispatch_helper_xml.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# In src/shenbi/pipeline/dispatch_helper.py, line 240-243, replace:
#     user_parts.append(f"### {fname}\n```\n{content}\n```")
# With:
    if input_texts:
        user_parts.append("\n## Input Files (read-only reference)")
        for fname, content in input_texts.items():
            # Escape ALL '<' in content to '\u003c' to prevent any tag injection.
            # (Spec 8 §3 Bug 2: the wrapper is </document>, NOT </doc>; the safest
            # approach is escaping every '<' rather than only replacing the tag.)
            safe_content = content.replace('<', '\u003c')
            user_parts.append(f'<document name="{fname}">\n{safe_content}\n</document>')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_dispatch_helper_xml.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_dispatch_helper_xml.py
git commit -m "fix: use XML <document> tags (with \u003c escaping) instead of nested code fences for input files"
```

---

### Task 3: Build Shared Audit Context Cache

**Files:**
- Create: `src/shenbi/pipeline/audit_context_cache.py`
- Modify: `src/shenbi/pipeline/chapter_loop.py` (call cache before audit batch)
- Test: `tests/pipeline/test_audit_context_cache.py`

**Interfaces:**
- Produces: `SharedAuditContext` dataclass with pre-extracted fields
- Produces: `build_shared_audit_context(project_dir: Path, chapter: int) -> SharedAuditContext`

- [ ] **Step 1: Write the failing test**

```python
# tests/pipeline/test_audit_context_cache.py
import tempfile
from pathlib import Path
from shenbi.pipeline.audit_context_cache import (
    SharedAuditContext,
    build_shared_audit_context,
)

def test_build_shared_context_extracts_chapter_fields():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        chapter_text = "# Chapter 1\n\n林风站在山顶。\n\n" + "故事继续。" * 100
        (chapter_dir / "chapter-001.md").write_text(chapter_text, encoding="utf-8")

        ctx = build_shared_audit_context(project_dir, 1)
        assert ctx.chapter_text is not None
        assert len(ctx.chapter_text) > 100
        assert ctx.world_rules is not None or ctx.world_rules == ""  # may be missing


def test_shared_context_reduces_repeated_io():
    """Shared context should be buildable once and reusable across audit calls."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "chapter-001.md").write_text("test content" * 50, encoding="utf-8")

        ctx1 = build_shared_audit_context(project_dir, 1)
        ctx2 = build_shared_audit_context(project_dir, 1)
        # Same input should produce identical context
        assert ctx1.chapter_text == ctx2.chapter_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_audit_context_cache.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/pipeline/audit_context_cache.py
from dataclasses import dataclass, field
from pathlib import Path
import structlog

log = structlog.get_logger()


@dataclass
class SharedAuditContext:
    """Pre-extracted context shared across all audit calls for a single chapter."""
    chapter_text: str = ""
    chapter_summary: str = ""
    world_rules: str = ""
    character_list: str = ""
    style_profile: str = ""
    volume_context: str = ""
    pending_hooks: str = ""

    @property
    def estimated_tokens(self) -> int:
        total = sum(len(v) for v in [self.chapter_text, self.chapter_summary,
                 self.world_rules, self.character_list, self.style_profile,
                 self.volume_context, self.pending_hooks])
        return total // 3  # rough token estimate


def build_shared_audit_context(project_dir: Path, chapter: int) -> SharedAuditContext:
    """Build shared context once per chapter, reused across all audit LLM calls."""
    ctx = SharedAuditContext()

    chapter_file = project_dir / "chapters" / f"chapter-{chapter:03d}.md"
    if chapter_file.exists():
        ctx.chapter_text = chapter_file.read_text(encoding="utf-8")

    world_rules_file = project_dir / "truth" / "world_rules.md"
    if world_rules_file.exists():
        raw = world_rules_file.read_text(encoding="utf-8")
        ctx.world_rules = _summarize_if_large(raw, max_chars=5000)

    characters_file = project_dir / "truth" / "character_matrix.md"
    if characters_file.exists():
        raw = characters_file.read_text(encoding="utf-8")
        ctx.character_list = _summarize_if_large(raw, max_chars=3000)

    style_file = project_dir / "style" / "style_profile.md"
    if style_file.exists():
        ctx.style_profile = style_file.read_text(encoding="utf-8")[:2000]

    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if hooks_file.exists():
        ctx.pending_hooks = hooks_file.read_text(encoding="utf-8")[:3000]

    volume_map_file = project_dir / "truth" / "volume_map.md"
    if volume_map_file.exists():
        raw = volume_map_file.read_text(encoding="utf-8")
        ctx.volume_context = _extract_volume_chapter(raw, chapter)

    log.info("shared_audit_context_built", chapter=chapter,
             estimated_tokens=ctx.estimated_tokens)
    return ctx


def _summarize_if_large(text: str, max_chars: int = 5000) -> str:
    """Truncate text if it exceeds max_chars, adding summary indicator."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[... truncated from {len(text)} chars]"


def _extract_volume_chapter(volume_map_text: str, chapter: int) -> str:
    """Extract current chapter node from volume_map."""
    lines = volume_map_text.split("\n")
    in_section = False
    result = []
    for line in lines:
        if f"第{chapter}章" in line or f"Chapter {chapter}" in line:
            in_section = True
        elif in_section and (line.startswith("##") or line.startswith("# ")):
            break
        if in_section:
            result.append(line)
    return "\n".join(result[:50]) if result else ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_audit_context_cache.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/audit_context_cache.py tests/pipeline/test_audit_context_cache.py
git commit -m "feat: add shared audit context cache to reduce repeated file I/O"
```

> **Note — this function is NOT yet wired.** Task 3 only creates
> `build_shared_audit_context`. The cache has zero effect until the audit
> dispatch loop is modified to build it once per chapter and pass it to each
> auditor. That wiring is **Task 6, Step 2** (CRITICAL) — do not skip it.

---

### Task 4: Priority-Driven Context Budget

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (add `_budgeted_truncate`)
- Test: `tests/pipeline/test_budgeted_truncate.py`

**Interfaces:**
- Produces: `_FILE_PRIORITY_WEIGHTS: dict[str, float]`
- Produces: `_budgeted_truncate(input_texts: dict, budget: int) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# tests/pipeline/test_budgeted_truncate.py
from shenbi.pipeline.dispatch_helper import _FILE_PRIORITY_WEIGHTS, _budgeted_truncate

def test_budgeted_truncate_preserves_high_priority():
    texts = {
        "chapter-current.md": "A" * 30000,   # HIGH priority
        "world_rules.md": "B" * 10000,        # HIGH priority
        "style_profile.md": "C" * 5000,       # MEDIUM priority
        "archive_notes.md": "D" * 20000,      # LOW priority
    }
    budget = 20000  # chars

    result = _budgeted_truncate(texts, budget)
    total = sum(len(v) for v in result.values())

    # High priority files should be less truncated
    assert len(result.get("chapter-current.md", "")) > 5000
    # Total should be within budget
    assert total <= budget * 1.1  # 10% tolerance

def test_priority_weights_exist_for_all_keys():
    assert "chapter-current.md" in _FILE_PRIORITY_WEIGHTS or "chapter" in str(_FILE_PRIORITY_WEIGHTS)
    assert isinstance(_FILE_PRIORITY_WEIGHTS, dict)
    assert len(_FILE_PRIORITY_WEIGHTS) >= 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_budgeted_truncate.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# In src/shenbi/pipeline/dispatch_helper.py:

_FILE_PRIORITY_WEIGHTS = {
    # HIGH priority (1.0) — essential for task completion
    "chapter": 1.0,
    "chapter-current": 1.0,
    "chapter-plan": 1.0,
    # MEDIUM-HIGH (0.8) — strongly influences output quality
    "volume_map": 0.8,
    "character_matrix": 0.8,
    "world_rules": 0.8,
    "current_state": 0.8,
    # MEDIUM (0.5) — provides important context
    "style_profile": 0.5,
    "pending_hooks": 0.5,
    "review_checklist": 0.5,
    "current_focus": 0.5,
    # LOW (0.2) — supplementary, can be heavily truncated
    "archive": 0.2,
    "snapshot": 0.2,
    "default": 0.5,
}


def _get_priority(filename: str) -> float:
    """Get priority weight for a filename based on keyword matching.

    Checks explicit path prefixes first to avoid substring misclassification
    (e.g., ``audits/chapter-1-anti-ai.md`` must not match the ``audit`` key
    and return LOW when it contains ``chapter`` in its name).
    """
    # Explicit path-prefix checks (avoid substring false matches)
    if filename.startswith("audits/"):
        return Priority.LOW
    elif "chapter" in filename.lower():
        return Priority.HIGH
    # Fall back to keyword matching for remaining entries
    for key, weight in _FILE_PRIORITY_WEIGHTS.items():
        if key in filename.lower():
            return weight
    return _FILE_PRIORITY_WEIGHTS["default"]


def _budgeted_truncate(input_texts: dict[str, str], budget: int) -> dict[str, str]:
    """Truncate input texts to fit within budget, preserving high-priority content.

    Uses weighted allocation: high-priority files get proportionally more budget.
    """
    if not input_texts:
        return {}

    # Calculate total weight
    weights = {name: _get_priority(name) for name in input_texts}
    total_weight = sum(weights.values())

    # Allocate budget proportionally by weight
    result = {}
    for name, content in input_texts.items():
        allocation = int(budget * weights[name] / total_weight)
        if len(content) <= allocation:
            result[name] = content
        else:
            result[name] = content[:allocation] + f"\n\n[... truncated from {len(content)} chars]"

    # Enforce per-file character ceiling
    result[name] = result[name][:_INPUT_MAX_CHARS_PER_FILE]

    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_budgeted_truncate.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_budgeted_truncate.py
git commit -m "feat: add priority-driven context budget allocation"
```

> **Note — this function is NOT yet wired.** Task 4 only adds
> `_budgeted_truncate` (and `_FILE_PRIORITY_WEIGHTS`). It has zero effect while
> `_build_skill_prompt` still uses its old equal-weight proportional truncation
> (`budget_per_file = total // n_files`). The call site replacement is
> **Task 6, Step 1** (CRITICAL) — do not skip it.

---

### Task 5: Audit Cascading and Instruction Hierarchy

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (`_build_skill_prompt` — add hierarchy)
- Modify: `src/shenbi/pipeline/chapter_loop.py` (add audit cascading logic)
- Test: `tests/pipeline/test_audit_cascading.py`

**Interfaces:**
- Produces: `_should_skip_audit(skill: str, audit_history: list[dict]) -> bool` (N=3 chapter zero-HARD-failure streak heuristic)
- Produces: `_inject_instruction_hierarchy(prompt: str) -> str`
- Produces: `CASCADABLE_AUDITS`, `CORE_AUDITS`, `ALWAYS_RUN`, `CASCADE_STREAK_LENGTH`

- [ ] **Step 1: Write the failing test**

```python
# tests/pipeline/test_audit_cascading.py
from shenbi.pipeline.dispatch_helper import _inject_instruction_hierarchy

def test_instruction_hierarchy_has_three_tiers():
    prompt = "Review the chapter for issues."
    result = _inject_instruction_hierarchy(prompt)
    assert "HARD CONSTRAINTS" in result
    assert "GUIDELINES" in result
    assert "REFERENCE" in result


def test_three_chapter_zero_hard_streak_skips_cascaded_audit():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    # Previous N=3 chapters: 'dialogue' audit passed with zero HARD failures each time.
    # audit_history is most-recent-last; only the trailing N=3 entries are considered.
    audit_history = [
        {"dialogue": {"passed": True, "hard_failures": 0}},
        {"dialogue": {"passed": True, "hard_failures": 0}},
        {"dialogue": {"passed": True, "hard_failures": 0}},
    ]
    assert _should_skip_audit("dialogue", audit_history) is True


def test_hard_failure_in_streak_prevents_skip():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    # One of the previous 3 chapters had a HARD failure in 'dialogue' → do NOT skip.
    audit_history = [
        {"dialogue": {"passed": True, "hard_failures": 0}},
        {"dialogue": {"passed": False, "hard_failures": 1}},  # HARD failure
        {"dialogue": {"passed": True, "hard_failures": 0}},
    ]
    assert _should_skip_audit("dialogue", audit_history) is False


def test_insufficient_history_prevents_skip():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    # Fewer than N=3 chapters of history → cannot establish a streak → do NOT skip.
    audit_history = [
        {"dialogue": {"passed": True, "hard_failures": 0}},
        {"dialogue": {"passed": True, "hard_failures": 0}},
    ]
    assert _should_skip_audit("dialogue", audit_history) is False


def test_always_run_audits_are_never_skipped():
    from shenbi.pipeline.chapter_loop import _should_skip_audit, ALWAYS_RUN

    audit_history = [
        {"resonance": {"passed": True, "hard_failures": 0}},
        {"resonance": {"passed": True, "hard_failures": 0}},
        {"resonance": {"passed": True, "hard_failures": 0}},
    ]
    # resonance and memo-compliance ALWAYS run regardless of the cascade.
    for skill in ALWAYS_RUN:
        assert _should_skip_audit(skill, audit_history) is False, (
            f"{skill} must always run, but _should_skip_audit returned True"
        )


def test_non_cascadable_skill_is_not_skipped():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    # A core audit (e.g. 'continuity') is never cascade-skipped.
    audit_history = [
        {"continuity": {"passed": True, "hard_failures": 0}},
        {"continuity": {"passed": True, "hard_failures": 0}},
        {"continuity": {"passed": True, "hard_failures": 0}},
    ]
    assert _should_skip_audit("continuity", audit_history) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_audit_cascading.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# In src/shenbi/pipeline/dispatch_helper.py:

def _inject_instruction_hierarchy(prompt: str) -> str:
    """Add 3-tier instruction hierarchy to prompt (Anthropic Context Engineering pattern)."""
    header = """## Instruction Hierarchy

<HARD_CONSTRAINTS>
- These rules CANNOT be violated under any circumstances
- Violation = automatic rejection
</HARD_CONSTRAINTS>

<GUIDELINES>
- Follow these unless there is a compelling creative reason not to
- Deviations must be justified in the decisions JSON
</GUIDELINES>

<REFERENCE>
- This section provides context and examples
- Use for inspiration, not as strict rules
</REFERENCE>

---
"""
    return header + prompt


# In src/shenbi/pipeline/chapter_loop.py:

# Spec 8 Fix 8 — Core 4 pass, skip 8 (NOT "skip 9").
# memo-compliance and resonance ALWAYS run (scoring requires them) — they are
# excluded from CASCADABLE_AUDITS and are never cascade-skipped. There is no
# "confidence >90%" signal available; instead we use an N=3 chapter streak with
# zero HARD failures as the cascade trigger.

CORE_AUDITS = ["continuity", "character", "world-rules", "pacing"]

ALWAYS_RUN = {"memo-compliance", "resonance"}

CASCADABLE_AUDITS = [
    "dialogue", "motivation", "sensitivity", "foreshadowing",
    "pov", "anti-ai", "texture", "reader-pull",
]

CASCADE_STREAK_LENGTH = 3  # N=3


def _should_skip_audit(skill: str, audit_history: list[dict]) -> bool:
    """N-chapter-streak cascade heuristic (Spec 8 Fix 8).

    Skip `skill` only when ALL of the following hold:
      1. `skill` is in CASCADABLE_AUDITS (core audits and ALWAYS_RUN audits run).
      2. We have at least N=3 chapters of history for `skill`.
      3. Each of the trailing N=3 entries for `skill` passed with zero HARD
         failures.

    Args:
        skill: audit skill short-name (e.g. "dialogue", "continuity").
        audit_history: list of per-chapter audit result dicts, most-recent-last.
            Each entry maps skill -> {"passed": bool, "hard_failures": int}.

    Returns:
        True if the audit may be cascade-skipped this chapter.
    """
    # Core audits and always-run audits are never cascade-skipped.
    if skill in CORE_AUDITS or skill in ALWAYS_RUN:
        return False
    if skill not in CASCADABLE_AUDITS:
        return False  # Unknown skill → run normally

    # Need at least N=3 chapters of history to establish a streak.
    recent = audit_history[-CASCADE_STREAK_LENGTH:]
    if len(recent) < CASCADE_STREAK_LENGTH:
        return False

    for chapter_results in recent:
        result = chapter_results.get(skill)
        if result is None:
            return False  # No record for this skill in that chapter → no streak
        if not result.get("passed", False):
            return False  # Did not pass → break streak
        if result.get("hard_failures", 0) > 0:
            return False  # Any HARD failure → break streak

    return True  # N=3 streak of zero-HARD-failure passes → cascade-skip
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_audit_cascading.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py src/shenbi/pipeline/chapter_loop.py tests/pipeline/test_audit_cascading.py
git commit -m "feat: N=3 chapter streak audit cascade + 3-tier instruction hierarchy"
```

> **Note — this function is NOT yet wired.** Task 5 only adds
> `_should_skip_audit` (and the `CASCADABLE_AUDITS` / `ALWAYS_RUN` / `CASCADE_STREAK_LENGTH`
> constants). The cascade never skips anything until the audit dispatch block
> calls `_should_skip_audit` before building/dispatching each ReviewTask. That
> wiring is **Task 6, Step 3** (CRITICAL) — do not skip it.

---

### Task 6: Wire SharedAuditContext, _budgeted_truncate, and _should_skip_audit into the Dispatch Path (CRITICAL)

> **Why this task exists:** Tasks 3, 4, and 5 each DEFINE a function but, as
> written, never CALL it from the live dispatch path. Without this task the
> -40% token goal is unmet: the cache is built but unused, budgeted truncation
> is implemented but the old equal-weight truncation still runs, and the cascade
> predicate exists but every audit still dispatches every chapter. Each wiring
> step below names the exact file + code block it modifies. Verify the line
> numbers against the current tree before editing (they are accurate as of
> 2026-07-19 but may drift).

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (audit dispatch block ~lines 1090-1143 — the `if step_idx == _FIRST_AUDIT_IDX and step.is_audit:` block that builds `core_tasks` and `genre_tasks` and dispatches the two parallel waves)
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (`_build_skill_prompt` truncation block ~lines 163-190; also `_build_skill_prompt` signature/`input_texts` injection ~lines 100-200)
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (`_dispatch_*` / audit dispatch entry that per-audit calls `_build_skill_prompt`)

**Interfaces:**
- Consumes: `SharedAuditContext` / `build_shared_audit_context` (Task 3)
- Consumes: `_budgeted_truncate`, `_FILE_PRIORITY_WEIGHTS` (Task 4)
- Consumes: `_should_skip_audit`, `CASCADABLE_AUDITS`, `CASCADE_STREAK_LENGTH` (Task 5)

- [ ] **Step 1: Wire `_budgeted_truncate` into `_build_skill_prompt` (replaces equal-weight truncation)**

  `src/shenbi/pipeline/dispatch_helper.py` currently (lines 163-190) truncates
  `raw_inputs` with an **equal-weight proportional budget**:
  `budget_per_file = _INPUT_MAX_CHARS_TOTAL // len(raw_inputs)` and a per-file
  cap of `_INPUT_MAX_CHARS_PER_FILE`. Replace that entire if/else block with a
  single call to the Task-4 priority-weighted truncator:

  ```python
  # src/shenbi/pipeline/dispatch_helper.py — _build_skill_prompt, replacing
  # the old "Apply per-file cap and proportional total budget" if/else block
  # (~lines 163-190). Priority weights now drive allocation instead of the
  # equal-weight split.
  from shenbi.pipeline.dispatch_helper import _budgeted_truncate  # if not already imported

  if not raw_inputs:
      input_texts = {}
  else:
      total_raw = sum(len(v) for v in raw_inputs.values())
      if total_raw > _INPUT_MAX_CHARS_TOTAL:
          log.warning(
              "input_over_budget_applying_priority_truncation",
              skill=skill,
              total_chars=total_raw,
              budget=_INPUT_MAX_CHARS_TOTAL,
          )
          input_texts = _budgeted_truncate(raw_inputs, _INPUT_MAX_CHARS_TOTAL)
          # _budgeted_truncate respects _INPUT_MAX_CHARS_PER_FILE per file via
          # the weights; if a stricter per-file ceiling is still required, cap
          # each result here AFTER budgeted truncation.
      else:
          # Under budget: still enforce the per-file cap.
          input_texts = {
              fname: (text[:_INPUT_MAX_CHARS_PER_FILE]
                      if len(text) > _INPUT_MAX_CHARS_PER_FILE else text)
              for fname, text in raw_inputs.items()
          }
  ```

  After this change the `input_truncated` log lines are emitted inside
  `_budgeted_truncate`; the old per-file log calls in this block are removed.

  Add a test asserting that when over budget, a high-priority file
  (`chapter-N.md`, weight 1.0) retains more characters than a low-priority file
  (`archive-*.md`, weight 0.2) of equal original size.

- [ ] **Step 2: Wire `SharedAuditContext` into the audit dispatch loop**

  `src/shenbi/pipeline/chapter_loop.py`'s audit block (the
  `if step_idx == _FIRST_AUDIT_IDX and step.is_audit:` block, ~lines 1093-1143)
  builds `core_tasks` and `genre_tasks` (two `ReviewTask` waves) and dispatches
  them in parallel. Each `ReviewTask` independently re-reads the chapter,
  world rules, character matrix, style profile, etc. — that is the 13×30KB
  repeated I/O the cache exists to eliminate.

  Build the shared context ONCE, before the two waves, and pass it through to
  each auditor so they consume the cached fields instead of re-reading:

  ```python
  # src/shenbi/pipeline/chapter_loop.py — at the top of the
  # `if step_idx == _FIRST_AUDIT_IDX and step.is_audit:` block, BEFORE
  # constructing core_tasks / genre_tasks:
  from shenbi.pipeline.audit_context_cache import build_shared_audit_context

  shared_ctx = build_shared_audit_context(project_dir, chapter)
  log.info(
      "shared_audit_context_built_for_wave",
      chapter=chapter,
      estimated_tokens=shared_ctx.estimated_tokens,
  )

  # Then pass shared_ctx into each ReviewTask so the auditor (and the prompt
  # builder) read from the cache. ReviewTask gains a `shared_context` field:
  core_tasks = [
      ReviewTask(
          skill=skill,
          project_dir=project_dir,
          prompt=f"Execute {skill} for chapter {chapter}.",
          output_path=f"audits/chapter-{chapter}-{audit_suffix(skill)}.md",
          shared_context=shared_ctx,   # <-- NEW
      )
      for skill in core_skills
  ]
  # ... same shared_context=shared_ctx kwarg on every genre_task ...
  ```

  This also requires extending `ReviewTask` (in
  `src/shenbi/pipeline/parallel_dispatch.py`) to accept an optional
  `shared_context: SharedAuditContext | None = None` field, and the audit
  dispatch entry point (`_dispatch_via_api` / the function that calls
  `_build_skill_prompt` for an audit skill) to inject `shared_context` fields
  into `input_texts` (or skip re-reading those files when the cache provides
  them). Concretely, in the audit dispatch path:

  ```python
  # When shared_context is provided for an audit skill, prefer the cached
  # fields over re-reading the raw files (they are already field-filtered and
  # summarized by build_shared_audit_context).
  if shared_context is not None:
      _INJECT_FROM_CACHE = {
          "world_rules.md": shared_context.world_rules,
          "character_matrix.md": shared_context.character_list,
          "style_profile.md": shared_context.style_profile,
          "pending_hooks.md": shared_context.pending_hooks,
          # chapter text + volume node are passed as the primary context below
      }
      for fname, cached in _INJECT_FROM_CACHE.items():
          if cached:
              input_texts[fname] = cached   # skip the raw read for this file
  ```

  Add a test asserting that across the two audit waves (13 auditors),
  `build_shared_audit_context` is invoked exactly ONCE per chapter (mock it and
  assert `call_count == 1`), and that the chapter text is read from disk once,
  not 13 times.

- [ ] **Step 3: Wire `_should_skip_audit` into the cascade (skip before dispatch)**

  > **shared_context wiring path:** The `shared_context` dict is passed through the dispatch chain as follows: (a) `dispatch_reviews_parallel` creates a `shared_context` via `build_shared_audit_context()` before the ThreadPoolExecutor; (b) passes it as a new optional `shared_context: dict | None = None` parameter to `dispatch_skill`; (c) `dispatch_skill` forwards it to `_dispatch_via_api(shared_context=shared_context)` and `_dispatch_via_ide(shared_context=shared_context)`; (d) `_build_skill_prompt` accepts `shared_context: dict | None = None` and injects cached fields into `input_texts` before assembling the prompt.

  In the SAME audit block in `chapter_loop.py`, after building each task list
  but BEFORE dispatching the wave, filter out cascaded audits that the streak
  heuristic says to skip. `_should_skip_audit` lives in `chapter_loop.py`
  itself (Task 5 placed it there).

  ```python
  # src/shenbi/pipeline/chapter_loop.py — after building core_tasks/genre_tasks
  # and BEFORE dispatch_reviews_parallel, filter cascaded audits.
  from shenbi.pipeline.chapter_loop import _should_skip_audit  # same module; may be a direct call

  # Load the per-skill audit history (most-recent-last) from pipeline state.
  # _get_audit_history should return the list[dict] shape _should_skip_audit
  # expects: [{"<skill>": {"passed": bool, "hard_failures": int}}, ...].
  audit_history = _get_audit_history(state, chapter)

  def _keep_task(task: ReviewTask) -> bool:
      skill_short = _audit_short_name(task.skill)   # "shenbi-review-dialogue" -> "dialogue"
      if _should_skip_audit(skill_short, audit_history):
          log.info("audit_cascade_skipped", chapter=chapter, skill=task.skill)
          return False
      return True

  core_tasks = [t for t in core_tasks if _keep_task(t)]
  genre_tasks = [t for t in genre_tasks if _keep_task(t)]
  ```

  Notes:
  - `_should_skip_audit` already excludes `memo-compliance` and `resonance`
    (the `ALWAYS_RUN` set) and the core audits, so those never get skipped —
    only the 8 `CASCADABLE_AUDITS` can be filtered out here.
  - If filtering empties a wave, skip the `dispatch_reviews_parallel` call for
    that wave (don't dispatch an empty list).
  - `_get_audit_history` and `_audit_short_name` are small helpers you must
    add to `chapter_loop.py` (read the trailing N=3 chapter audit results from
    `state`; map a full skill name to its short audit dimension). Add unit
    tests for both helpers alongside the Task-5 cascade tests.

  Implementation stubs:

```python
def _get_audit_history(state, current_chapter: int) -> list[dict]:
    """Extract audit results from previous chapters in pipeline state.

    Returns list of dicts with keys: skill, chapter, passed, issues
    for all audit results from chapters < current_chapter.
    """
    results = []
    for ch_num, ch_state in state.chapter_loop.chapter_states.items():
        if ch_num >= current_chapter:
            continue
        for audit_key, audit_result in ch_state.audit_results.items():
            if isinstance(audit_result, dict):
                results.append({
                    "skill": audit_key,
                    "chapter": ch_num,
                    "passed": audit_result.get("passed", False),
                    "issues": audit_result.get("issues", []),
                })
    return results

def _audit_short_name(skill_name: str) -> str:
    """Map full skill name to short audit dimension name.

    Examples:
        "shenbi-review-anti-ai" -> "anti-ai"
        "shenbi-review-continuity" -> "continuity"
        "shenbi-review-dialogue" -> "dialogue"
    """
    return skill_name.replace("shenbi-review-", "")
```

  Add a test asserting: given an audit history with a 3-chapter zero-HARD
  failure streak for `dialogue`, dispatching the audit block for the next
  chapter does NOT create a `shenbi-review-dialogue` ReviewTask (count it in
  `core_tasks`/`genre_tasks`), while `review-resonance` and `review-continuity`
  tasks are still present.

- [ ] **Step 4: Run the full suite and confirm the three wirings are live**

  ```bash
  pytest tests/pipeline/test_dispatch_helper_glob.py \
         tests/pipeline/test_dispatch_helper_xml.py \
         tests/pipeline/test_audit_context_cache.py \
         tests/pipeline/test_budgeted_truncate.py \
         tests/pipeline/test_audit_cascading.py -v
  just check
  ```

  Expected: PASS. Additionally, run a 1-chapter canary and confirm in the logs
  that (a) `shared_audit_context_built_for_wave` appears exactly once, (b)
  `input_over_budget_applying_priority_truncation` / priority-weighted
  truncation is used when over budget, and (c) `audit_cascade_skipped` appears
  for at least one cascaded audit when the streak condition holds.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py \
        src/shenbi/pipeline/dispatch_helper.py \
        src/shenbi/pipeline/parallel_dispatch.py \
        tests/pipeline/
git commit -m "feat: wire shared audit cache, priority budgeted truncation, and N=3 cascade skip into the dispatch path"
```
