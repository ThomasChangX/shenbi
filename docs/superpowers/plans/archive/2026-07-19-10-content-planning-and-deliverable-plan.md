# Content Planning and Deliverable Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three pipeline defects: volume_map.md is never consumed for per-chapter content/context injection (it IS consumed for structure validation and chapter-count derivation), character archives for supporting characters are never created, and META blocks contaminate deliverable chapter files at ~31% average ratio.

**Architecture:** Inject volume_map into the three-route context assembly system (Route C) for per-chapter content injection, create a deterministic plan skeleton generator that pre-fills 55% of chapter plan content from the volume map reducing LLM token consumption, add WARN-level blueprint alignment checks after drafting, and restructure the character-design skill into four mandatory phases with G4 gate enforcement. META block strategy remains status quo with documentation and a G2 monitoring warning.

> **Volume boundaries:** Volume boundaries MUST be parsed at runtime via `triggers.py:read_volume_boundaries()` (returns a `set[int]` of last-chapter numbers per volume), NOT hard-coded as Python literals. Hard-coding `('Volume 1', (1, 15))` duplicates the map and will diverge.

**Tech Stack:** Python 3.11+, pathlib, structlog, json, pytest

## Global Constraints

- `just check` passes with zero failures throughout (ruff + mypy + basedpyright + pytest)
- No breaking changes to existing pipeline orchestration (chapter_loop.py, dispatch_helper.py)
- All gate checks use existing `shenbi.gates.shared` helpers (`fail`, `passed`, `yload`, `safe_write`)
- Skeleton must not eliminate LLM creativity: Section 5 (Key Decisions) is fully LLM-generated
- Character archive archetype fields must be validated at G4, not at generation time
- META block behavior is unchanged short-term; only documentation and monitoring added
- Token reduction target: hybrid planning tokens reduced by >= 40% vs pure LLM planning

---

### Task 1: Inject Volume Map Context into Route C Assembly

**Files:**
- Modify: `src/shenbi/pipeline/context_assemble.py:44-49, 175-184`
- Test: `tests/unit/pipeline/test_context_assemble.py`

**Interfaces:**
- Produces: `_load_volume_context(project_dir: Path, chapter: int) -> str`
- Consumes: existing `_ROUTE_C_FILES`, `assemble_context()` function

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from shenbi.pipeline.context_assemble import _load_volume_context, BUDGET_BY_ROLE

@pytest.fixture
def project_with_volume_map(tmp_path: Path) -> Path:
    outline_dir = tmp_path / "outline"
    outline_dir.mkdir()
    volume_map = outline_dir / "volume_map.md"
    volume_map.write_text("""# Volume Map

## Volume 1: Awakening (Ch 1-15)
**Objective:** Introduce protagonist Lin Feng and establish the cultivation world

### Key Results
#### KR1: Foundation Building
- Opening (Ch1-3): Lin Feng discovers spiritual roots
- Progression (Ch4-7): Basic training at Qingyun Sect
- Turn (Ch8-11): First crisis - sect invasion
- Closing (Ch12-15): Resolution and advancement

### Chapter Nodes
| Ch | Role | Content |
|----|------|---------|
| 1 | opening | Lin Feng awakens in a mysterious cave with no memory |
| 2 | progression | First encounter with cultivation elder Chen Weimin |

## Volume 2: Rising Storm (Ch 16-35)
**Objective:** Expand the world, introduce political factions

## Cross-Volume Bridges
| Bridge ID | Content | Expected Activation Ch |
|-----------|---------|----------------------|
| V1-B1 | Brahmi inscription metal fragment | Ch 26 |
| V1-B2 | Spirit beast egg prophecy | Ch 28 |
""")
    return tmp_path


def test_load_volume_context_returns_current_volume_info(project_with_volume_map: Path):
    result = _load_volume_context(project_with_volume_map, chapter=3)
    assert "Volume 1" in result
    assert "Awakening" in result
    assert "Lin Feng" in result


def test_load_volume_context_includes_chapter_node(project_with_volume_map: Path):
    result = _load_volume_context(project_with_volume_map, chapter=1)
    assert "Lin Feng awakens" in result
    assert "opening" in result.lower()


def test_load_volume_context_returns_bridge_info_when_near_activation(project_with_volume_map: Path):
    result = _load_volume_context(project_with_volume_map, chapter=25)
    assert "V1-B1" in result
    assert "Brahmi inscription" in result


def test_load_volume_context_returns_empty_for_missing_volume_map(tmp_path: Path):
    result = _load_volume_context(tmp_path, chapter=5)
    assert result == ""


def test_load_volume_context_returns_empty_for_chapter_out_of_range(project_with_volume_map: Path):
    result = _load_volume_context(project_with_volume_map, chapter=200)
    assert result == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_context_assemble.py::test_load_volume_context_returns_current_volume_info -v`
Expected: FAIL with ImportError or AttributeError (function not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/context_assemble.py`:

```python
import re as _re_module

# Volume boundaries are parsed at runtime from volume_map.md via
# triggers.py:read_volume_boundaries() -- NEVER hard-coded. Hard-coding
# ('Volume 1', (1, 15)) duplicates the map and will diverge.

# Shared constant — defined here in context_assemble.py to avoid circular imports.
# plan_skeleton.py imports from context_assemble (one-way dependency only).
_BRIDGE_ACTIVATION_WINDOW = 3

# Canonical definition — plan_skeleton.py imports from here
def _resolve_volume_at_runtime(project_dir: Path, chapter: int) -> tuple[str, int, int] | None:
    """Resolve (volume_name, ch_start, ch_end) for a chapter at runtime.

    Parses volume_map.md via triggers.py:read_volume_boundaries() which
    returns a set of last-chapter numbers per volume. We build the
    (start, end) ranges from that set.
    """
    from shenbi.pipeline.triggers import read_volume_boundaries

    boundary_chapters = read_volume_boundaries(project_dir)
    if not boundary_chapters:
        return None

    boundaries_sorted = sorted(boundary_chapters)
    prev_end = 0
    for i, end in enumerate(boundaries_sorted, 1):
        ch_start = prev_end + 1
        if ch_start <= chapter <= end:
            return (f"Volume {i}", ch_start, end)
        prev_end = end
    return None


def _load_volume_context(project_dir: Path, chapter: int) -> str:
    """Extract current volume context from volume_map.md for the given chapter.

    Returns a markdown string containing:
    - Current volume Objective
    - Current chapter's node role and content description
    - Pending cross-volume bridges approaching activation
    """
    vm_path = project_dir / "outline" / "volume_map.md"
    if not vm_path.exists():
        return ""

    volume_map_text = vm_path.read_text(encoding="utf-8")

    # Determine current volume at runtime (NEVER hard-code boundaries)
    resolved = _resolve_volume_at_runtime(project_dir, chapter)
    if resolved is None:
        return ""
    current_volume = resolved[0]

    parts: list[str] = []
    parts.append(f"## Current Volume Context (from volume_map.md)\n")

    # Extract volume objective
    vol_pattern = _re_module.compile(
        rf"## {_re_module.escape(current_volume)}.*?\n\*\*Objective:\*\*\s*(.+?)(?=\n##|\n###|\Z)",
        _re_module.DOTALL,
    )
    vol_match = vol_pattern.search(volume_map_text)
    if vol_match:
        parts.append(f"**Volume Objective:** {vol_match.group(1).strip()}\n")

    # Extract chapter node info
    chapter_node_pattern = _re_module.compile(
        rf"\|\s*{chapter}\s*\|([^|]+)\|([^|]+)\|",
    )
    node_match = chapter_node_pattern.search(volume_map_text)
    if node_match:
        role = node_match.group(1).strip()
        content = node_match.group(2).strip()
        parts.append(f"**Chapter Role:** {role}")
        parts.append(f"**Expected Content:** {content}\n")

    # Extract pending cross-volume bridges
    bridge_section = volume_map_text.split("## Cross-Volume Bridges")
    if len(bridge_section) > 1:
        bridge_pattern = _re_module.compile(
            r"\|\s*(V\d+-B\d+)\s*\|([^|]+)\|\s*(\d+)\s*\|",
        )
        pending_bridges: list[str] = []
        for m in bridge_pattern.finditer(bridge_section[1]):
            bridge_id = m.group(1)
            bridge_content = m.group(2).strip()
            activation_ch = int(m.group(3))
            if chapter >= activation_ch - _BRIDGE_ACTIVATION_WINDOW:
                pending_bridges.append(
                    f"- **{bridge_id}** ({bridge_content}) activates Ch {activation_ch}"
                )
        if pending_bridges:
            parts.append("**Pending Cross-Volume Bridges:**")
            parts.extend(pending_bridges)
            parts.append("")

    return "\n".join(parts)
```

Now inject `_load_volume_context` into `assemble_context()`. The function signature is `assemble_context(project_dir, chapter_plan_path) -> ContextPackage` — there is NO `chapter` integer parameter and NO `context_parts` list. Instead, the three routes (`_route_a`/`_route_b`/`_route_c`) each return a list of dict entries with keys `source/weight/text/id`, which are concatenated and fed to `rerank_results()`, then converted into `ContextSection` objects (fields `source/priority/text/category/estimated_tokens`).

Inject the volume context as a Route C dict entry so it flows through the existing rerank/budget path. Parse the chapter number from the plan path (`plans/chapter-N-plan.md` -> N):

```python
# Inject volume map context into Route C assembly. Route entries are dicts
# (source/weight/text/id); rerank_results + the section-building loop convert
# them to ContextSection(source/priority/text/category/estimated_tokens).
import re as _re_chapter
_chapter_match = _re_chapter.search(r"chapter-(\d+)", chapter_plan_path)
_chapter_num = int(_chapter_match.group(1)) if _chapter_match else 0
volume_ctx = _load_volume_context(project_dir, _chapter_num)
if volume_ctx:
    route_c.append(
        {
            "source": "route-c:volume_map",
            "weight": 0.6,
            "text": volume_ctx,
            "id": "volume_map",
        }
    )
```

This must be inserted AFTER `route_c = _route_c(project_dir)` (line ~223) and BEFORE `ranked = rerank_results(route_a + route_b + route_c)` (line ~225), so the volume entry is included in the rerank+dedup+budget pass.

Update `_ROUTE_C_FILES` comment to document that volume_map is now included at runtime.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_context_assemble.py::test_load_volume_context_returns_current_volume_info tests/unit/pipeline/test_context_assemble.py::test_load_volume_context_includes_chapter_node tests/unit/pipeline/test_context_assemble.py::test_load_volume_context_returns_bridge_info_when_near_activation tests/unit/pipeline/test_context_assemble.py::test_load_volume_context_returns_empty_for_missing_volume_map tests/unit/pipeline/test_context_assemble.py::test_load_volume_context_returns_empty_for_chapter_out_of_range -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/context_assemble.py tests/unit/pipeline/test_context_assemble.py
git commit -m "feat: inject volume_map context into Route C assembly

Add _load_volume_context() that extracts current volume objective,
chapter node role/content, and pending cross-volume bridges from
volume_map.md. Injected into assemble_context() Route C at weight 0.6.
"
```

---

### Task 2: Create Deterministic Plan Skeleton Generator

**Files:**
- Create: `src/shenbi/pipeline/plan_skeleton.py`
- Test: `tests/unit/pipeline/test_plan_skeleton.py`

**Interfaces:**
- Produces: `generate_plan_skeleton(project_dir: Path, chapter: int) -> str`
- Consumes: `outline/volume_map.md` (read), `truth/book_spine.md` (read)
- Later Task 3 _check_volume_map_alignment() uses same volume_map parsing

> **Editable context, not locked output:** Pre-filled sections from the skeleton are EDITABLE CONTEXT, not immutable output. The LLM should see them as a suggested starting point it may modify, override, or deviate from. If the skeleton is treated as immutable, creative deviation drops to ~0%, conflicting with the design intent. The skeleton must include an explicit instruction: "以下为参考骨架，可根据创作需要调整" (The following is a reference skeleton; adjust as needed for creative purposes).

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from shenbi.pipeline.plan_skeleton import generate_plan_skeleton


@pytest.fixture
def project_with_volume_map(tmp_path: Path) -> Path:
    outline_dir = tmp_path / "outline"
    outline_dir.mkdir()
    volume_map = outline_dir / "volume_map.md"
    volume_map.write_text("""# Volume Map

## Volume 1: Awakening (Ch 1-15)
**Objective:** Introduce protagonist and establish cultivation world

### Chapter Nodes
| Ch | Role | Content |
|----|------|---------|
| 1 | opening | Lin Feng awakens in cave |
| 2 | progression | First encounter with elder |

## Cross-Volume Bridges
| Bridge ID | Content | Expected Activation Ch |
|-----------|---------|----------------------|
| V1-B1 | Brahmi inscription | 26 |
""")
    truth_dir = tmp_path / "truth"
    truth_dir.mkdir()
    (truth_dir / "book_spine.md").write_text("# Book Spine\nThree-act structure placeholder.")
    return tmp_path


def test_skeleton_has_eight_sections(project_with_volume_map: Path):
    skeleton = generate_plan_skeleton(project_with_volume_map, chapter=1)
    assert "## 1. Current Task" in skeleton
    assert "## 2. Reader Expectations" in skeleton
    assert "## 3. Fulfill/Defer Decisions" in skeleton
    assert "## 4. Transition Role" in skeleton
    assert "## 5. Key Decisions" in skeleton
    assert "## 6. End-of-Chapter Change" in skeleton
    assert "## 7. Hook Ledger" in skeleton
    assert "## 8. Don't Do" in skeleton


def test_skeleton_section_1_prefilled_from_volume_map(project_with_volume_map: Path):
    skeleton = generate_plan_skeleton(project_with_volume_map, chapter=1)
    assert "Lin Feng awakens in cave" in skeleton
    assert "opening" in skeleton.lower()


def test_skeleton_section_5_is_llm_generated_placeholder(project_with_volume_map: Path):
    skeleton = generate_plan_skeleton(project_with_volume_map, chapter=1)
    # Section 5 should be a placeholder for LLM, not pre-filled
    section_5_start = skeleton.index("## 5. Key Decisions")
    section_6_start = skeleton.index("## 6. End-of-Chapter Change")
    section_5 = skeleton[section_5_start:section_6_start]
    assert "[LLM]" in section_5 or "placeholder" in section_5.lower()


def test_skeleton_returns_empty_on_missing_volume_map(tmp_path: Path):
    skeleton = generate_plan_skeleton(tmp_path, chapter=1)
    # Should still produce the 8-section template but with all [LLM] placeholders
    assert "## 1. Current Task" in skeleton
    assert "[LLM]" in skeleton


def test_skeleton_section_7_includes_pending_bridges(project_with_volume_map: Path):
    skeleton = generate_plan_skeleton(project_with_volume_map, chapter=25)
    assert "V1-B1" in skeleton or "Brahmi" in skeleton


def test_skeleton_marks_prefilled_sections_as_editable_context(project_with_volume_map: Path):
    """Pre-filled sections MUST be marked EDITABLE CONTEXT, not locked output.

    The skeleton must include an explicit instruction (Chinese and/or English)
    telling the LLM it may modify, override, or deviate from pre-filled content.
    """
    skeleton = generate_plan_skeleton(project_with_volume_map, chapter=1)
    # Must include the editable-context instruction in Chinese or English
    assert "以下为参考骨架" in skeleton or "EDITABLE CONTEXT" in skeleton or "adjust as needed" in skeleton.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_plan_skeleton.py::test_skeleton_has_eight_sections -v`
Expected: FAIL (module or function not found)

- [ ] **Step 3: Write minimal implementation**

Create `src/shenbi/pipeline/plan_skeleton.py`:

```python
"""Deterministic plan skeleton generator.

Derives ~55% of chapter plan content from volume_map.md, reducing LLM token
consumption and ensuring blueprint alignment. The LLM's role shifts from
"generator" to "polisher + creative filler" for sections 1,4,6,7 while
retaining full creative control over section 5 (Key Decisions).

Sections derived from volume_map:
  - 1. Current Task: fully (node role + description)
  - 4. Transition Role: fully (node role)
  - 6. End-of-Chapter Change: basic (current + next chapter node)
  - 7. Hook Ledger: bridges within activation window

Sections with partial derivation:
  - 2. Reader Expectations: tension curve hints
  - 3. Fulfill/Defer Decisions: cross-volume bridges
  - 8. Don't Do: volume boundary constraints

Section fully LLM-generated:
  - 5. Key Decisions
"""

from __future__ import annotations

import re
from pathlib import Path

# Volume boundaries are parsed at runtime via triggers.py:read_volume_boundaries()
# -- NEVER hard-coded. See _resolve_volume_at_runtime().

from shenbi.pipeline.context_assemble import _BRIDGE_ACTIVATION_WINDOW

_SKELETON_TEMPLATE = """# Chapter {chapter} Plan Skeleton

> **以下为参考骨架，可根据创作需要调整。** (The following is a reference
> skeleton; adjust as needed for creative purposes.)
> Pre-filled sections are EDITABLE CONTEXT derived from volume_map.md, not
> locked output. You may modify, override, or deviate from any pre-filled
> content. Section 5 (Key Decisions) is entirely yours to create.

## 1. Current Task
{section_1}

## 2. Reader Expectations
{section_2}

## 3. Fulfill/Defer Decisions
{section_3}

## 4. Transition Role
{section_4}

## 5. Key Decisions
{section_5}

## 6. End-of-Chapter Change
{section_6}

## 7. Hook Ledger
{section_7}

## 8. Don't Do
{section_8}
"""


def generate_plan_skeleton(project_dir: Path, chapter: int) -> str:
    """Generate a deterministic plan skeleton from volume_map.md.

    Returns a markdown string with sections 1,4,6,7 pre-filled where
    possible and the remaining sections containing [LLM] placeholders
    with guidance for completion.
    """
    vm_path = project_dir / "outline" / "volume_map.md"
    if not vm_path.exists():
        return _empty_skeleton(chapter)

    volume_map_text = vm_path.read_text(encoding="utf-8")

    # Resolve current volume at runtime via triggers.py (NEVER hard-code)
    resolved = _resolve_volume_at_runtime(project_dir, chapter)
    if resolved is None:
        current_volume, next_chapter = "Unknown", chapter + 1
    else:
        current_volume, _ch_start, ch_end = resolved
        next_chapter = min(chapter + 1, ch_end)
    chapter_node = _extract_chapter_node(volume_map_text, chapter)
    next_node = _extract_chapter_node(volume_map_text, next_chapter)
    pending_bridges = _extract_pending_bridges(volume_map_text, chapter)

    # Section 1: Current Task (fully derivable)
    if chapter_node:
        section_1 = (
            f"**Role:** {chapter_node['role']}\n"
            f"**Content:** {chapter_node['content']}\n"
            f"**Volume:** {current_volume}"
        )
    else:
        section_1 = f"[LLM] Determine current task for Ch{chapter}. Volume: {current_volume}"

    # Section 2: Reader Expectations (partial)
    section_2 = (
        f"[LLM] Define 3-5 reader expectations for this chapter. "
        f"Consider: what promises does the previous chapter make? "
        f"What tension level is appropriate for a '{chapter_node['role'] if chapter_node else 'unknown'}' chapter?"
    )

    # Section 3: Fulfill/Defer Decisions (partial)
    if pending_bridges:
        bridge_list = "\n".join(f"  - {b}" for b in pending_bridges)
        section_3 = (
            f"[LLM] Decide which hooks to fulfill or defer this chapter.\n"
            f"Pending cross-volume bridges:\n{bridge_list}\n"
            f"Also consider intra-chapter hooks from previous chapter."
        )
    else:
        section_3 = "[LLM] Decide which hooks to fulfill or defer this chapter."

    # Section 4: Transition Role (fully derivable)
    if chapter_node:
        section_4 = (
            f"**Node Role:** {chapter_node['role']}\n"
            f"**From volume_map:** This chapter serves as a '{chapter_node['role']}' node "
            f"within {current_volume}."
        )
    else:
        section_4 = f"[LLM] Define the transition role for Ch{chapter}."

    # Section 5: Key Decisions (full LLM)
    section_5 = (
        "[LLM] List 3-5 key creative decisions for this chapter. "
        "This is fully LLM-generated; the skeleton provides no constraints here. "
        "Consider: character choices, plot pivots, revelation timing."
    )

    # Section 6: End-of-Chapter Change (basic)
    if chapter_node and next_node:
        section_6 = (
            f"**Current chapter role:** {chapter_node['role']}\n"
            f"**Next chapter (Ch{next_chapter}) role:** {next_node['role']}\n"
            f"**Next chapter content hint:** {next_node['content']}\n\n"
            f"[LLM] Refine: what specific changes should occur by end of this chapter "
            f"to set up Ch{next_chapter}?"
        )
    elif chapter_node:
        section_6 = (
            f"**Current chapter role:** {chapter_node['role']}\n\n"
            f"[LLM] Define the end-of-chapter change that propels into the next chapter."
        )
    else:
        section_6 = "[LLM] Define the end-of-chapter change."

    # Section 7: Hook Ledger (partially derivable)
    if pending_bridges:
        bridge_list = "\n".join(f"  - {b}" for b in pending_bridges)
        section_7 = (
            f"[LLM] Track all hooks and their fulfillment status.\n"
            f"Cross-volume bridges approaching activation:\n{bridge_list}\n\n"
            f"[LLM] Add intra-chapter hooks planted/fulfilled this chapter."
        )
    else:
        section_7 = "[LLM] Track all hooks planted and fulfilled this chapter. Include hook IDs."

    # Section 8: Don't Do (partial)
    if chapter_node:
        role = chapter_node['role']
        if role == "opening":
            section_8 = (
                f"[LLM] Avoid: rushing exposition, introducing too many characters. "
                f"This is an opening chapter - focus on hooking the reader."
            )
        elif role == "closing":
            section_8 = (
                f"[LLM] Avoid: introducing new plot threads, unresolved cliffhangers "
                f"that won't pay off soon. This is a closing chapter - deliver resolution."
            )
        else:
            section_8 = f"[LLM] List 3-5 things to avoid in this chapter. Consider volume boundaries."
    else:
        section_8 = "[LLM] List 3-5 things to avoid in this chapter."

    return _SKELETON_TEMPLATE.format(
        chapter=chapter,
        section_1=section_1,
        section_2=section_2,
        section_3=section_3,
        section_4=section_4,
        section_5=section_5,
        section_6=section_6,
        section_7=section_7,
        section_8=section_8,
    )


# _resolve_volume_at_runtime imported from context_assemble (canonical definition)
from shenbi.pipeline.context_assemble import _resolve_volume_at_runtime


def _extract_chapter_node(volume_map_text: str, chapter: int) -> dict[str, str] | None:
    """Extract {role, content} for a chapter from the volume_map table."""
    pattern = re.compile(rf"\|\s*{chapter}\s*\|([^|]+)\|([^|]+)\|")
    m = pattern.search(volume_map_text)
    if m:
        return {"role": m.group(1).strip(), "content": m.group(2).strip()}
    return None


def _extract_pending_bridges(volume_map_text: str, chapter: int) -> list[str]:
    """Return list of bridge descriptions near activation for this chapter."""
    bridge_section = volume_map_text.split("## Cross-Volume Bridges")
    if len(bridge_section) < 2:
        return []

    pattern = re.compile(r"\|\s*(V\d+-B\d+)\s*\|([^|]+)\|\s*(\d+)\s*\|")
    bridges: list[str] = []
    for m in pattern.finditer(bridge_section[1]):
        bridge_id = m.group(1)
        content = m.group(2).strip()
        activation_ch = int(m.group(3))
        if chapter >= activation_ch - _BRIDGE_ACTIVATION_WINDOW:
            bridges.append(f"{bridge_id}: {content} (activates Ch {activation_ch})")
    return bridges


def _empty_skeleton(chapter: int) -> str:
    """Return skeleton with all [LLM] placeholders when volume_map is missing."""
    return _SKELETON_TEMPLATE.format(
        chapter=chapter,
        section_1=f"[LLM] Determine current task for Ch{chapter}.",
        section_2="[LLM] Define reader expectations.",
        section_3="[LLM] Decide which hooks to fulfill or defer.",
        section_4="[LLM] Define transition role.",
        section_5="[LLM] List key creative decisions.",
        section_6="[LLM] Define end-of-chapter change.",
        section_7="[LLM] Track hooks planted and fulfilled.",
        section_8="[LLM] List things to avoid.",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_plan_skeleton.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/plan_skeleton.py tests/unit/pipeline/test_plan_skeleton.py
git commit -m "feat: add deterministic plan skeleton generator from volume_map

generate_plan_skeleton() pre-fills sections 1,4,6,7 from volume_map.md
(~55% of content), leaving section 5 fully LLM-generated. Expected token
reduction: >= 40% vs pure LLM planning.
"
```

---

### Task 3: Add WARN-Level Blueprint Alignment Checks in Chapter Loop

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (add `_check_volume_map_alignment()`)
- Test: `tests/unit/pipeline/test_chapter_loop.py`

**Interfaces:**
- Consumes: `chapter_loop.py` orchestrator (called after chapter drafting step), `plan_skeleton._extract_chapter_node()`
- Produces: WARN-level structlog messages when blueprint deviation detected

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from shenbi.pipeline.chapter_loop import _check_volume_map_alignment


@pytest.fixture
def project_with_volume_map_and_chapter(tmp_path: Path) -> Path:
    outline_dir = tmp_path / "outline"
    outline_dir.mkdir()
    (outline_dir / "volume_map.md").write_text("""# Volume Map
## Volume 1: Awakening (Ch 1-15)
### Chapter Nodes
| Ch | Role | Content |
|----|------|---------|
| 1 | opening | Lin Feng awakens, cultivates, meets elder |
""")
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    return tmp_path


def test_alignment_check_passes_when_key_terms_present(project_with_volume_map_and_chapter: Path):
    chapter_text = "Lin Feng slowly awoke in the dark cave. He began to cultivate, sensing the elder's presence."
    (project_with_volume_map_and_chapter / "chapters" / "chapter-1.md").write_text(chapter_text)

    with patch("shenbi.pipeline.chapter_loop.log") as mock_log:
        _check_volume_map_alignment(project_with_volume_map_and_chapter, chapter=1)
        # Should not warn when terms match
        warn_calls = [c for c in mock_log.warning.call_args_list if "volume_map_alignment" in str(c)]
        assert len(warn_calls) == 0


def test_alignment_check_warns_when_key_terms_missing(project_with_volume_map_and_chapter: Path):
    chapter_text = "The sun rose over the mountains. Birds sang in the trees. A gentle breeze blew."
    (project_with_volume_map_and_chapter / "chapters" / "chapter-1.md").write_text(chapter_text)

    with patch("shenbi.pipeline.chapter_loop.log") as mock_log:
        _check_volume_map_alignment(project_with_volume_map_and_chapter, chapter=1)
        mock_log.warning.assert_any_call(
            "volume_map_alignment", chapter=1, missing_terms=["Lin Feng", "awakens", "cultivate", "elder"]
        )


def test_alignment_check_skips_when_no_volume_map(project_with_volume_map_and_chapter: Path):
    (project_with_volume_map_and_chapter / "outline" / "volume_map.md").unlink()
    chapter_text = "Anything."
    (project_with_volume_map_and_chapter / "chapters" / "chapter-1.md").write_text(chapter_text)

    with patch("shenbi.pipeline.chapter_loop.log") as mock_log:
        _check_volume_map_alignment(project_with_volume_map_and_chapter, chapter=1)
        warn_calls = [c for c in mock_log.warning.call_args_list if "volume_map_alignment" in str(c)]
        assert len(warn_calls) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_chapter_loop.py::test_alignment_check_passes_when_key_terms_present -v`
Expected: FAIL (function not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/chapter_loop.py`:

```python
import re as _re

def _check_volume_map_alignment(project_dir: Path, chapter: int) -> None:
    """WARN-level check: compare volume_map chapter node terms against chapter text.

    Non-blocking: blueprint is guidance, creative deviation is allowed.
    Warns when >70% of key terms from volume_map are missing from chapter.
    """
    vm_path = project_dir / "outline" / "volume_map.md"
    chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"

    if not vm_path.exists() or not chapter_path.exists():
        return

    volume_map_text = vm_path.read_text(encoding="utf-8")

    # Extract chapter node description
    node = _extract_chapter_node_from_map(volume_map_text, chapter)
    if node is None:
        return

    # Extract key terms (nouns and proper nouns, Chinese/English)
    key_terms = _extract_key_terms(node["content"])
    if not key_terms:
        return

    chapter_text = chapter_path.read_text(encoding="utf-8")

    # Check term presence
    found_terms: list[str] = []
    missing_terms: list[str] = []
    for term in key_terms:
        if term.lower() in chapter_text.lower():
            found_terms.append(term)
        else:
            missing_terms.append(term)

    total = len(key_terms)
    match_rate = len(found_terms) / total if total > 0 else 1.0

    if match_rate < 0.3:  # >70% missing
        log.warning(
            "volume_map_alignment",
            chapter=chapter,
            match_rate=f"{match_rate:.1%}",
            found_terms=found_terms,
            missing_terms=missing_terms,
            expected=node["content"][:120],
        )


def _extract_chapter_node_from_map(volume_map_text: str, chapter: int) -> dict[str, str] | None:
    """Extract {role, content} from volume_map table row for a chapter."""
    pattern = _re.compile(rf"\|\s*{chapter}\s*\|([^|]+)\|([^|]+)\|")
    m = pattern.search(volume_map_text)
    if m:
        return {"role": m.group(1).strip(), "content": m.group(2).strip()}
    return None


def _extract_key_terms(text: str) -> list[str]:
    """Extract significant key terms from a description.

    Returns Chinese words (2+ chars) and English words (3+ chars),
    skipping common stop words.
    """
    stop_words = {"the", "and", "in", "of", "to", "a", "is", "for", "with", "this", "that", "from", "be"}
    terms: list[str] = []

    # English words 3+ chars
    eng_words = _re.findall(r"[a-zA-Z]{3,}", text)
    for w in eng_words:
        if w.lower() not in stop_words:
            terms.append(w)

    # Chinese character sequences 2+ chars
    cn_seqs = _re.findall(r"[\u4e00-\u9fff]{2,}", text)
    terms.extend(cn_seqs)

    # Filter generic terms
    filtered: list[str] = []
    for t in terms:
        if t.lower() not in {"chapter", "volume", "node", "role", "content", "character"}:
            filtered.append(t)

    return filtered
```

Integrate into the chapter loop: after chapter drafting completes (after the dispatch step), add:

```python
# Blueprint alignment check (WARN-level, non-blocking)
_check_volume_map_alignment(project_dir, chapter)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_chapter_loop.py::test_alignment_check_passes_when_key_terms_present tests/unit/pipeline/test_chapter_loop.py::test_alignment_check_warns_when_key_terms_missing tests/unit/pipeline/test_chapter_loop.py::test_alignment_check_skips_when_no_volume_map -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_chapter_loop.py
git commit -m "feat: add WARN-level volume_map alignment check after chapter drafting

Checks key term presence (>70% missing triggers warning). Non-blocking;
creative deviation from blueprint is allowed. Check runs after each
chapter drafting completes.
"
```

---

### Task 4: Create Bridge Tracker and Update Foreshadowing-Track Skill

**Files:**
- Create: `truth/bridge_tracker.md` (template, populated at runtime)
- Modify: `skills/shenbi-foreshadowing-track/SKILL.md`
- Test: `tests/unit/pipeline/test_bridge_tracker.py`

**Interfaces:**
- Produces: `truth/bridge_tracker.md` (markdown table with bridge states)
- Consumes: `outline/volume_map.md` (initialization), chapter text (activation detection)
- Later: bridge tracker updates occur in chapter_loop.py after each chapter

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path


BRIDGE_TRACKER_HEADER = "| Bridge ID | Content | Expected Activation Ch | Actual Activation Ch | Status |"


def test_bridge_tracker_template_has_correct_structure():
    """The bridge tracker template file must contain the expected table header."""
    template_path = Path(__file__).resolve().parents[3] / "truth" / "bridge_tracker.md"
    if not template_path.exists():
        pytest.skip("bridge_tracker.md template not yet created")
    content = template_path.read_text(encoding="utf-8")
    assert BRIDGE_TRACKER_HEADER in content
    assert "PENDING" in content
    assert "ACTIVATED" in content or "| Status |" in content


def test_bridge_tracker_template_is_valid_markdown_table():
    template_path = Path(__file__).resolve().parents[3] / "truth" / "bridge_tracker.md"
    if not template_path.exists():
        pytest.skip("bridge_tracker.md template not yet created")
    content = template_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    # Must have at least a header row and separator row
    pipe_lines = [l for l in lines if "|" in l]
    assert len(pipe_lines) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_bridge_tracker.py::test_bridge_tracker_template_has_correct_structure -v`
Expected: FAIL (file not found or test skipped)

- [ ] **Step 3: Write minimal implementation**

Create `truth/bridge_tracker.md`:

```markdown
# Cross-Volume Bridge Tracker

> Auto-generated from outline/volume_map.md at Genesis time.
> Updated each chapter by shenbi-foreshadowing-track.
> States: PENDING | ACTIVATED | DEFERRED | ABANDONED

| Bridge ID | Content | Expected Activation Ch | Actual Activation Ch | Status |
|-----------|---------|----------------------|---------------------|--------|
| V1-B1 | | 0 | — | PENDING |
| V1-B2 | | 0 | — | PENDING |
| V1-B3 | | 0 | — | PENDING |
| V1-B4 | | 0 | — | PENDING |
| V2-B1 | | 0 | — | PENDING |
| V2-B2 | | 0 | — | PENDING |
| V2-B3 | | 0 | — | PENDING |
| V2-B4 | | 0 | — | PENDING |
| V3-B1 | | 0 | — | PENDING |
| V3-B2 | | 0 | — | PENDING |
| V3-B3 | | 0 | — | PENDING |
| V3-B4 | | 0 | — | PENDING |
| V4-B1 | | 0 | — | PENDING |
| V4-B2 | | 0 | — | PENDING |
| V4-B3 | | 0 | — | PENDING |
| V4-B4 | | 0 | — | PENDING |

**Last Updated:** Genesis
```

Update `skills/shenbi-foreshadowing-track/SKILL.md`.

Read the current file first, then add after the `writes:` frontmatter section a new write target and append a responsibility section at the end of the prompt body:

```yaml
writes:
  - truth/foreshadowing_ledger.md
  - truth/bridge_tracker.md          # NEW: cross-volume bridge activation tracking
```

Append to the prompt body:

```markdown
## Cross-Volume Bridge Tracking (NEW)

After updating foreshadowing_ledger.md, also check `truth/bridge_tracker.md`:

1. Read the current chapter text
2. For each bridge in PENDING state: if the chapter contains the bridge's key
   terms (character name, item name, event description), mark it ACTIVATED
   with the current chapter number as Actual Activation Ch
3. If a bridge was expected to activate by this chapter but has not, mark it
   DEFERRED with a note
4. Write updated bridge_tracker.md back to disk
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_bridge_tracker.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add truth/bridge_tracker.md skills/shenbi-foreshadowing-track/SKILL.md tests/unit/pipeline/test_bridge_tracker.py
git commit -m "feat: add cross-volume bridge tracker and foreshadowing-track update

truth/bridge_tracker.md tracks all 16 cross-volume bridges with states
PENDING/ACTIVATED/DEFERRED/ABANDONED. shenbi-foreshadowing-track updated
to check and update bridge activation after each chapter.
"
```

---

### Task 5: Add Wildcard Path Resolution in _write_parsed_outputs

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (around `_write_parsed_outputs`, line 294 area)
- Test: `tests/unit/pipeline/test_dispatch_helper.py`

**Interfaces:**
- Consumes: SKILL.md contract `writes:` with wildcard patterns like `characters/major/*.md`
- Produces: Auto-created directories for concrete paths matching wildcard patterns

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from shenbi.pipeline.dispatch_helper import _resolve_wildcard_path


def test_resolve_wildcard_creates_directory_for_concrete_path(tmp_path: Path):
    """When a contract declares characters/major/*.md and LLM outputs
    characters/major/chen-weimin.md, auto-create the major/ directory."""
    contract_pattern = "characters/major/*.md"
    concrete_path = tmp_path / "characters" / "major" / "chen-weimin.md"
    assert not concrete_path.parent.exists()

    _resolve_wildcard_path(contract_pattern, str(concrete_path), base_dir=tmp_path)

    assert concrete_path.parent.exists()


def test_resolve_wildcard_matches_pattern(tmp_path: Path):
    """Wildcard pattern should match concrete paths."""
    assert _resolve_wildcard_path(
        "characters/major/*.md",
        str(tmp_path / "characters" / "major" / "chen-weimin.md"),
        base_dir=tmp_path,
    ) is True


def test_resolve_wildcard_rejects_non_matching_path(tmp_path: Path):
    """Concrete path must match the wildcard pattern."""
    assert _resolve_wildcard_path(
        "characters/major/*.md",
        str(tmp_path / "characters" / "protagonist.md"),
        base_dir=tmp_path,
    ) is False


def test_resolve_wildcard_with_minor_characters(tmp_path: Path):
    """Test with minor character wildcard."""
    contract_pattern = "characters/minor/*.md"
    concrete_path = tmp_path / "characters" / "minor" / "zhao-tiezhu.md"
    assert not concrete_path.parent.exists()

    _resolve_wildcard_path(contract_pattern, str(concrete_path), base_dir=tmp_path)
    assert concrete_path.parent.exists()


def test_wildcard_pattern_to_regex():
    """Internal: pattern conversion."""
    import re
    from shenbi.pipeline.dispatch_helper import _wildcard_to_regex
    pattern = _wildcard_to_regex("characters/major/*.md")
    regex = re.compile(pattern)
    assert regex.match("characters/major/chen-weimin.md")
    assert not regex.match("characters/major/subdir/chen-weimin.md")
    assert not regex.match("characters/protagonist.md")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py::test_resolve_wildcard_creates_directory_for_concrete_path -v`
Expected: FAIL (function not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/dispatch_helper.py`:

```python
import fnmatch
import re as _re


def _wildcard_to_regex(pattern: str) -> str:
    """Convert a glob-style pattern to a regex pattern string.

    'characters/major/*.md' -> 'characters/major/[^/]*\\.md'
    """
    escaped = _re.escape(pattern)
    # Replace escaped \* with a non-slash wildcard
    return "^" + escaped.replace(r"\*", r"[^/]*") + "$"


def _resolve_wildcard_path(
    contract_pattern: str,
    concrete_path: str,
    base_dir: Path | None = None,
) -> bool:
    """Check if concrete_path matches contract_pattern and ensure parent dirs exist.

    Returns True if the path matches and directories were handled.
    Returns False if the path does not match the pattern.

    contract_pattern examples:
        'characters/major/*.md'
        'characters/minor/*.md'

    When a match is found, all intermediate directories are created so the
    caller can safely write the file.
    """
    regex = _re.compile(_wildcard_to_regex(contract_pattern))

    # Normalize path separator
    normalized = concrete_path.replace("\\", "/")

    if not regex.match(normalized):
        return False

    p = Path(concrete_path)
    if base_dir is not None and not p.is_absolute():
        p = base_dir / p

    p.parent.mkdir(parents=True, exist_ok=True)
    return True


def _resolve_all_wildcards(
    contract_writes: list[str],
    concrete_path: str,
    base_dir: Path | None = None,
) -> list[str]:
    """Return the list of contract patterns that match concrete_path.

    For each matching pattern, ensure directories exist.
    """
    matching: list[str] = []
    for pattern in contract_writes:
        if "*" in pattern or "?" in pattern:
            if _resolve_wildcard_path(pattern, concrete_path, base_dir):
                matching.append(pattern)
        elif pattern in concrete_path or concrete_path.endswith(pattern):
            matching.append(pattern)
    return matching
```

Now integrate into `_write_parsed_outputs()`. Find the section where `### FILE:` markers are parsed (approximately line 217-226), and before writing the file, call:

```python
# Resolve wildcard contract paths before writing
_resolve_all_wildcards(contract_writes, output_file_path, base_dir=project_dir)
```

Where `contract_writes` is the list of `writes:` entries from the skill's SKILL.md frontmatter.

> **Note:** This requires the `skill` parameter on `_write_parsed_outputs` (added by Plan 14). If Plan 14 has not landed, add `skill: str | None = None` to `_write_parsed_outputs` signature, then use `load_contract(skill)` to retrieve `contract_writes`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py::test_resolve_wildcard_creates_directory_for_concrete_path tests/unit/pipeline/test_dispatch_helper.py::test_resolve_wildcard_matches_pattern tests/unit/pipeline/test_dispatch_helper.py::test_resolve_wildcard_rejects_non_matching_path tests/unit/pipeline/test_dispatch_helper.py::test_resolve_wildcard_with_minor_characters tests/unit/pipeline/test_dispatch_helper.py::test_wildcard_pattern_to_regex -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_helper.py
git commit -m "feat: add wildcard path resolution in _write_parsed_outputs

_resolve_wildcard_path() auto-creates intermediate directories when
LLM outputs a concrete path matching a wildcard contract pattern
(e.g., characters/major/*.md). Enables character archive creation.
"
```

---

### Task 6: Restructure character-design SKILL.md into 4 Phases

**Files:**
- Modify: `skills/shenbi-character-design/SKILL.md`

**Interfaces:**
- Consumes: existing SKILL.md content (line 38-49 flow diagram, prompt body)
- Produces: restructured 4-phase prompt with iron law enforcement

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path


def test_skill_md_has_four_explicit_phases():
    skill_path = Path(__file__).resolve().parents[3] / "skills" / "shenbi-character-design" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "Phase 1:" in content or "阶段一" in content or "第一阶段" in content  # Chinese or English
    assert "Phase 2:" in content
    assert "Phase 3:" in content
    assert "Phase 4:" in content


def test_skill_md_has_iron_law_for_named_characters():
    skill_path = Path(__file__).resolve().parents[3] / "skills" / "shenbi-character-design" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "every character" in content.lower() or "iron law" in content.lower()
    assert "chapter_outline" in content or "three_act" in content


def test_skill_md_declares_major_and_minor_writes():
    skill_path = Path(__file__).resolve().parents[3] / "skills" / "shenbi-character-design" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "characters/major/" in content
    assert "characters/minor/" in content


def test_skill_md_includes_archetype_sources_requirement():
    skill_path = Path(__file__).resolve().parents[3] / "skills" / "shenbi-character-design" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "archetype_sources" in content
    assert "historical" in content.lower() or "archetype" in content.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/g4/test_character_design.py::test_skill_md_has_four_explicit_phases -v`
Expected: FAIL (content does not match)

- [ ] **Step 3: Write minimal implementation**

Read the current `skills/shenbi-character-design/SKILL.md`, then restructure.

The key changes are:
1. Replace the existing flow section (lines 38-49) with four explicit numbered phases
2. Add iron law requiring every named character from outlines gets an archive
3. Add archetype-driven design methodology in Phase 2

The frontmatter `writes:` must include:
```yaml
writes:
  - characters/protagonist.md
  - characters/major/*.md
  - characters/minor/*.md
  - characters/relationships.md
```

The four-phase prompt structure (replace content after frontmatter and before the existing prompt body's core sections):

```markdown
# Character Design Protocol

You must complete ALL FOUR phases in order. Each phase produces specific files.
No phase is optional. No character explicitly named in `outline/chapter_outline.md`
or `outline/three_act.md` may be omitted.

---

## Phase 1: Protagonist Depth Portrait
**Output:** `characters/protagonist.md`

Create a comprehensive protagonist profile with these required YAML frontmatter fields:
- name, role, personality_tags (>= 5), core_value, goal_surface, goal_deep
- fear, arc_type, arc_starting, arc_turning, arc_ending
- voice_profile: speech_patterns (>= 2), catchphrases (>= 1), avoid_patterns (>= 1)
- archetype_sources (see Archetype Requirements below)

[Existing protagonist detail prompt from current SKILL.md goes here]

---

## Phase 2: Major Supporting Character Portraits
**Output:** `characters/major/{slug}.md` (one per major character)

A character is MAJOR if they appear in >= 3 chapters with an independent arc.
Generate one `.md` file per major character identified from chapter_outline.md
and three_act.md.

Each major character file must include:

```yaml
name: <character name>
role: <e.g., mentor, antagonist, ally>
slug: <lowercase-hyphenated>
first_appearance_chapter: <number>
total_appearance_chapters: <count>
arc_summary: <one-line arc description>
archetype_sources:
  - name: <historical figure name>
    period: <era, e.g. "1930s Shanghai">
    traits_borrowed: [>= 3 specific traits]
    traits_discarded: [>= 2 specific traits]
    adaptation_rationale: <>= 100 characters explaining why this archetype
      was chosen and how it was adapted to the novel's world>
personality_tags: [>= 5]
relationship_to_protagonist: <description>
current_state: active
```

### Archetype Requirements (applies to ALL character files)
1. Prefer specific historical figures over abstract archetypes
   - GOOD: "Zhou Enlai 1930s Shanghai underground period"
   - BAD: "wise elder archetype"
2. 1-2 archetypes per character
3. Explicit borrow/discard: character is NOT a copy of the historical figure
4. Adapt to novel's world (skills -> world equivalents, social roles -> caste system mapping)
5. Avoid: overused figures (Napoleon, Caesar), mythological/fictional figures, living public figures

[Existing supporting character detail prompt from current SKILL.md goes here]

---

## Phase 3: Minor Character Registration
**Output:** `characters/minor/{slug}.md` (one per minor character)

A character is MINOR if they appear in 1-2 chapters or serve a functional role.
Generate one `.md` file per minor character.

Each minor character file must include at minimum:
```yaml
name: <character name>
slug: <lowercase-hyphenated>
first_appearance_chapter: <number>
role: <functional description>
personality_tags: [>= 3]
archetype_sources:
  - name: <historical figure name>
    period: <era>
    traits_borrowed: [>= 3]
    traits_discarded: [>= 2]
    adaptation_rationale: <>= 100 characters>
```

---

## Phase 4: Relationship Graph
**Output:** `characters/relationships.md`

Map all character-character relationships using slug-based references.
Each relationship pair must include:
- character_a (slug), character_b (slug)
- relationship_type (e.g., mentor-student, rivalry, alliance)
- intensity (1-5)
- key_exchange_summary (one paragraph)
- first_active_chapter
- last_active_chapter (or "ongoing")

Generate >= 3 relationship pairs. Include protagonist with each major character.

[Existing relationships detail prompt from current SKILL.md goes here]

---

## IRON LAW: Character Completeness

Before declaring completion, verify:
1. Every character explicitly named in `outline/chapter_outline.md` has a
   corresponding archive in either `characters/major/` or `characters/minor/`
2. Every character explicitly named in `outline/three_act.md` has an archive
3. `characters/major/` contains >= 3 `.md` files
4. `characters/minor/` contains >= 2 `.md` files
5. Every archive includes `archetype_sources` with >= 1 historical archetype,
   >= 3 borrowed traits, >= 2 discarded traits, and >= 100 char rationale

If any of these fail, go back and create the missing archives.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/g4/test_character_design.py::test_skill_md_has_four_explicit_phases tests/unit/gates/g4/test_character_design.py::test_skill_md_has_iron_law_for_named_characters tests/unit/gates/g4/test_character_design.py::test_skill_md_declares_major_and_minor_writes tests/unit/gates/g4/test_character_design.py::test_skill_md_includes_archetype_sources_requirement -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add skills/shenbi-character-design/SKILL.md tests/unit/gates/g4/test_character_design.py
git commit -m "feat: restructure character-design SKILL.md into 4 mandatory phases

Phase 1: Protagonist, Phase 2: Major Characters, Phase 3: Minor Characters,
Phase 4: Relationship Graph. Added iron law enforcement for completeness
and archetype-driven design methodology with historical figure anchors.
"
```

---

### Task 7: Raise existing G4.cd.major_chars threshold and add G4.cd.minor_chars

**Files:**
- Modify: `src/shenbi/gates/g4/character_design.py`
- Test: `tests/unit/gates/g4/test_character_design.py`

**Interfaces:**
- Consumes: `RoundPaths.read("characters/major")`, `RoundPaths.read("characters/minor")`
- Produces: `G4.cd.major_chars` (existing, raise threshold to >= 3), `G4.cd.minor_chars` (new, >= 2)

> **Spec correction:** `G4.cd.major_chars` ALREADY EXISTS in the current code (lines 118-136: PASS if `characters/major/` contains >= 2 files, WARN if == 1, SKIP if the directory is absent). This task raises its threshold to >= 3 and adds the NEW `G4.cd.minor_chars` check. Do NOT introduce new IDs `G4.char.major_count` / `G4.char.minor_count` -- the spec uses the `G4.cd.*` namespace to match the existing check.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from shenbi.gates.g4.character_design import g4_character_design


@pytest.fixture
def project_with_characters(tmp_path: Path) -> Path:
    """Create a project directory with character archives."""
    major_dir = tmp_path / "characters" / "major"
    minor_dir = tmp_path / "characters" / "minor"
    major_dir.mkdir(parents=True)
    minor_dir.mkdir(parents=True)

    # Create protagonist
    protag = tmp_path / "characters" / "protagonist.md"
    protag.write_text("""---
name: Lin Feng
role: protagonist
personality_tags: [brave, curious, loyal, determined, compassionate]
core_value: Freedom
goal_surface: Become strongest cultivator
goal_deep: Protect those he loves
fear: Powerlessness
arc_type: hero's journey
arc_starting: naive villager
arc_turning: loss of mentor
arc_ending: enlightened protector
voice_profile:
  speech_patterns: [short sentences, asks questions]
  catchphrases: ["This is my path"]
  avoid_patterns: [self-pity]
---""")

    # Create 3 major characters
    for i, name in enumerate(["Chen Weimin", "Zhao Tiezhu", "Chu Yunlan"]):
        slug = name.lower().replace(" ", "-")
        (major_dir / f"{slug}.md").write_text(f"# {name}\n\nMajor character profile.")

    # Create 2 minor characters
    for name in ["Koen Whiteman", "Gangshan Tieya"]:
        slug = name.lower().replace(" ", "-")
        (minor_dir / f"{slug}.md").write_text(f"# {name}\n\nMinor character profile.")

    # Create relationships
    rel = tmp_path / "characters" / "relationships.md"
    rel.write_text("""| Character A | Character B | Type |
|---|---|---|
| Lin Feng | Chen Weimin | mentor-student |
| Lin Feng | Zhao Tiezhu | partnership |
| Lin Feng | Chu Yunlan | alliance |
""")

    return tmp_path


def test_g4_character_design_major_count_pass(project_with_characters: Path):
    fps = [
        str(project_with_characters / "characters" / "protagonist.md"),
        str(project_with_characters / "characters" / "relationships.md"),
    ]
    result = g4_character_design(fps, rd=str(project_with_characters))
    import json
    data = json.loads(result)
    assert data["status"] == "PASS"

    # Verify G4.cd.major_chars check exists (ALREADY EXISTS, threshold raised to >= 3) and passes
    major_check = None
    for c in data.get("checks", []):
        if c.get("id", "") == "G4.cd.major_chars":
            major_check = c
            break
    assert major_check is not None, "G4.cd.major_chars check missing"
    assert major_check["s"] == "PASS", f"Expected PASS, got {major_check['s']}"
    assert major_check.get("count", 0) >= 3


def test_g4_character_design_minor_count_pass(project_with_characters: Path):
    fps = [
        str(project_with_characters / "characters" / "protagonist.md"),
        str(project_with_characters / "characters" / "relationships.md"),
    ]
    result = g4_character_design(fps, rd=str(project_with_characters))
    import json
    data = json.loads(result)

    # Verify G4.cd.minor_chars check exists (NEW, threshold >= 2) and passes
    minor_check = None
    for c in data.get("checks", []):
        if c.get("id", "") == "G4.cd.minor_chars":
            minor_check = c
            break
    assert minor_check is not None, "G4.cd.minor_chars check missing"
    assert minor_check["s"] == "PASS", f"Expected PASS, got {minor_check['s']}"
    assert minor_check.get("count", 0) >= 2


def test_g4_character_design_fails_when_too_few_major(tmp_path: Path):
    major_dir = tmp_path / "characters" / "major"
    major_dir.mkdir(parents=True)
    (tmp_path / "characters" / "minor").mkdir()
    (major_dir / "only-one.md").write_text("# Only One")

    # No protagonist or relationships needed in fps for this check
    fps: list[str] = []
    result = g4_character_design(fps, rd=str(tmp_path))
    import json
    data = json.loads(result)
    assert data["status"] == "FAIL"
    assert any("G4.cd.major_chars" in f for f in data.get("failures", []))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/g4/test_character_design.py::test_g4_character_design_major_count_pass -v`
Expected: FAIL (existing G4.cd.major_chars threshold is >= 2, needs raising to >= 3)

- [ ] **Step 3: Write minimal implementation**

Modify `src/shenbi/gates/g4/character_design.py`. The existing `G4.cd.major_chars` check (lines 118-136) currently PASSes at >= 2 files. Raise its threshold to >= 3, and ADD the new `G4.cd.minor_chars` check. The check IDs MUST stay in the `G4.cd.*` namespace (do NOT rename to `G4.char.*`):

```python
        # G4.cd.major_chars (EXISTING -- raise threshold from >=2 to >=3):
        # characters/major/ must have >= 3 .md files
        major_dir = rp.read("characters/major")
        if major_dir.exists():
            major_files = list(major_dir.glob("*.md"))
            if len(major_files) >= 3:
                c.append({
                    "id": "G4.cd.major_chars",
                    "s": "PASS",
                    "count": len(major_files),
                })
            elif len(major_files) >= 1:
                mf.append(
                    f"G4.cd.major_chars:need_3_got_{len(major_files)}"
                )
            else:
                mf.append("G4.cd.major_chars:need_3_got_0")
        else:
            mf.append("G4.cd.major_chars:directory_missing")

        # G4.cd.minor_chars (NEW): characters/minor/ must have >= 2 .md files
        minor_dir = rp.read("characters/minor")
        if minor_dir.exists():
            minor_files = list(minor_dir.glob("*.md"))
            if len(minor_files) >= 2:
                c.append({
                    "id": "G4.cd.minor_chars",
                    "s": "PASS",
                    "count": len(minor_files),
                })
            elif len(minor_files) >= 1:
                mf.append(
                    f"G4.cd.minor_chars:need_2_got_{len(minor_files)}"
                )
            else:
                mf.append("G4.cd.minor_chars:need_2_got_0")
        else:
            mf.append("G4.cd.minor_chars:directory_missing")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/g4/test_character_design.py::test_g4_character_design_major_count_pass tests/unit/gates/g4/test_character_design.py::test_g4_character_design_minor_count_pass tests/unit/gates/g4/test_character_design.py::test_g4_character_design_fails_when_too_few_major -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/character_design.py tests/unit/gates/g4/test_character_design.py
git commit -m "feat: raise G4.cd.major_chars threshold to >=3 and add G4.cd.minor_chars

G4.cd.major_chars ALREADY EXISTS (was >=2); raised to >=3. New
G4.cd.minor_chars (>=2) check added. Gate FAILS if characters/major/
has fewer than 3 .md files or characters/minor/ has fewer than 2 .md files.
Check IDs stay in the G4.cd.* namespace per spec.
"
```

---

### Task 8: Add Historical-Archetype Validation in G4 Character Checks

**Files:**
- Modify: `src/shenbi/gates/g4/character_design.py`
- Test: `tests/unit/gates/g4/test_character_design.py`

**Interfaces:**
- Consumes: major/minor character `.md` files with `archetype_sources` frontmatter
- Produces: `G4.cd.archetype` checks (PASS/FAIL per character file) -- uses `G4.cd.*` namespace for consistency with `G4.cd.major_chars` / `G4.cd.minor_chars`

- [ ] **Step 1: Write the failing test**

```python
def test_archetype_validation_passes_with_valid_archetype(tmp_path: Path):
    major_dir = tmp_path / "characters" / "major"
    minor_dir = tmp_path / "characters" / "minor"
    major_dir.mkdir(parents=True)
    minor_dir.mkdir(parents=True)

    # Create 3 major and 2 minor with valid archetypes
    for i, name in enumerate(["Chen Weimin", "Zhao Tiezhu", "Chu Yunlan"]):
        slug = name.lower().replace(" ", "-")
        (major_dir / f"{slug}.md").write_text(f"""---
name: {name}
archetype_sources:
  - name: Zhou Enlai 1930s Shanghai
    period: 1930s Republic China
    traits_borrowed: [diplomatic, patient, strategic, loyal]
    traits_discarded: [political ideology, party loyalty]
    adaptation_rationale: Adapted Zhou's underground negotiation skills to the cultivation world's sect diplomacy,
      replacing political maneuvering with spiritual power dynamics. The character retains Zhou's legendary patience
      and ability to find common ground.
---
""")

    for name in ["Koen Whiteman", "Gangshan Tieya"]:
        slug = name.lower().replace(" ", "-")
        (minor_dir / f"{slug}.md").write_text(f"""---
name: {name}
archetype_sources:
  - name: T.E. Lawrence
    period: WWI Middle East
    traits_borrowed: [charismatic, unconventional, adaptive, bridge-builder]
    traits_discarded: [British imperialism, self-loathing]
    adaptation_rationale: Lawrence's cross-cultural bridge-building adapted to this character's role as intermediary
      between cultivation sects and foreign powers, discarding the colonial context while preserving the outsider-who-understands dynamic.
---
""")

    (tmp_path / "characters" / "protagonist.md").write_text("""---
name: Lin Feng
role: protagonist
personality_tags: [brave, curious, loyal, determined, compassionate]
core_value: Freedom
goal_surface: Power
goal_deep: Protection
fear: Powerlessness
arc_type: hero's journey
arc_starting: villager
arc_turning: loss
arc_ending: protector
voice_profile:
  speech_patterns: [short, questions]
  catchphrases: [path]
  avoid_patterns: [self-pity]
archetype_sources:
  - name: Liu Bang
    period: Han Dynasty founding
    traits_borrowed: [commoner-to-king, pragmatic, delegator, people-first]
    traits_discarded: [ruthlessness, paranoia in later years]
    adaptation_rationale: Liu Bang's rise from peasant to emperor mirrors the cultivation journey from mortal to immortal,
      adapted by discarding historical ruthlessness in favor of a more compassionate leadership style suited to the novel's themes.
---
""")

    (tmp_path / "characters" / "relationships.md").write_text("""| A | B | Type |
|---|---|---|
| Lin Feng | Chen Weimin | mentor |
| Lin Feng | Zhao Tiezhu | partner |
| Lin Feng | Chu Yunlan | ally |
""")

    from shenbi.gates.g4.character_design import g4_character_design
    fps = [
        str(tmp_path / "characters" / "protagonist.md"),
        str(tmp_path / "characters" / "relationships.md"),
    ]
    result = g4_character_design(fps, rd=str(tmp_path))
    import json
    data = json.loads(result)

    archetype_checks = [c for c in data.get("checks", []) if "archetype" in c.get("id", "").lower()]
    assert len(archetype_checks) > 0, "No archetype checks found"
    for ac in archetype_checks:
        assert ac["s"] == "PASS", f"Archetype check failed: {ac}"


def test_archetype_validation_fails_when_traits_borrowed_insufficient(tmp_path: Path):
    major_dir = tmp_path / "characters" / "major"
    minor_dir = tmp_path / "characters" / "minor"
    major_dir.mkdir(parents=True)
    minor_dir.mkdir(parents=True)

    (major_dir / "chen-weimin.md").write_text("""---
name: Chen Weimin
archetype_sources:
  - name: Zhou Enlai
    period: 1930s
    traits_borrowed: [diplomatic]  # Only 1, need >= 3
    traits_discarded: [political]
    adaptation_rationale: Short.  # < 100 chars
---
""")
    (major_dir / "zhao-tiezhu.md").write_text("""---
name: Zhao Tiezhu
archetype_sources:
  - name: Guan Yu
    period: Three Kingdoms
    traits_borrowed: [loyal, strong, honorable]
    traits_discarded: [arrogance, rigidity]
    adaptation_rationale: A very long and detailed adaptation rationale that exceeds one hundred characters minimum requirement for this field.
---
""")
    (major_dir / "chu-yunlan.md").write_text("""---
name: Chu Yunlan
archetype_sources:
  - name: Wu Zetian
    period: Tang Dynasty
    traits_borrowed: [ambitious, strategic, charismatic, resilient]
    traits_discarded: [ruthlessness, paranoia]
    adaptation_rationale: Wu Zetian's unprecedented rise as a female ruler adapted to a cultivation world where gender barriers exist but can be overcome through power.
---
""")
    for name in ["Koen Whiteman", "Gangshan Tieya"]:
        slug = name.lower().replace(" ", "-")
        (minor_dir / f"{slug}.md").write_text(f"""---
name: {name}
archetype_sources:
  - name: T.E. Lawrence
    period: WWI
    traits_borrowed: [charismatic, unconventional, adaptive]
    traits_discarded: [imperialism, self-loathing]
    adaptation_rationale: Lawrence's cross-cultural role adapted to this character's position as intermediary between cultivation sects and outsiders.
---
""")

    (tmp_path / "characters" / "protagonist.md").write_text("""---
name: Lin Feng
role: protagonist
personality_tags: [brave, curious, loyal, determined, compassionate]
core_value: Freedom
goal_surface: Power
goal_deep: Protection
fear: Powerlessness
arc_type: hero's journey
arc_starting: villager
arc_turning: loss
arc_ending: protector
voice_profile:
  speech_patterns: [short, questions]
  catchphrases: [path]
  avoid_patterns: [self-pity]
---
""")
    (tmp_path / "characters" / "relationships.md").write_text("""| A | B | Type |
|---|---|---|
| Lin Feng | Chen Weimin | mentor |
| Lin Feng | Zhao Tiezhu | partner |
| Lin Feng | Chu Yunlan | ally |
""")

    from shenbi.gates.g4.character_design import g4_character_design
    fps = [
        str(tmp_path / "characters" / "protagonist.md"),
        str(tmp_path / "characters" / "relationships.md"),
    ]
    result = g4_character_design(fps, rd=str(tmp_path))
    import json
    data = json.loads(result)
    assert data["status"] == "FAIL"
    failures = data.get("failures", [])
    assert any("archetype" in f.lower() for f in failures), f"No archetype failure found in {failures}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/g4/test_character_design.py::test_archetype_validation_passes_with_valid_archetype -v`
Expected: FAIL (archetype check not implemented or no check found)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/gates/g4/character_design.py`, after the major/minor count checks:

```python
        # G4.cd.archetype: validate archetype_sources in major character files
        major_dir = rp.read("characters/major")
        if major_dir.exists():
            for mf_path in sorted(major_dir.glob("*.md")):
                _validate_archetype(mf_path, c, [])

        # Also check protagonist for archetype
        for fp in (fps or []):
            pf = resolve_input_path(fp, rd)
            if pf.suffix == ".md" and "protagonist" in str(fp):
                archetype_issues = _validate_archetype(pf, c, [])
                mf.extend(archetype_issues)
                break
```

And add the `_validate_archetype` function:

```python
def _validate_archetype(
    file_path: Path,
    checks: list[dict[str, Any]],
    failures: list[str],
) -> list[str]:
    """Validate archetype_sources frontmatter in a character archive.

    Returns a list of failure strings (empty if valid).
    """
    local_failures: list[str] = []
    char_name = file_path.stem

    try:
        fm = yload(str(file_path))
    except Exception:
        return [f"G4.cd.archetype.yaml_error:{char_name}"]

    archetype_sources = fm.get("archetype_sources", [])

    if not archetype_sources or not isinstance(archetype_sources, list):
        local_failures.append(f"G4.cd.archetype.missing:{char_name}")
        return local_failures

    for i, source in enumerate(archetype_sources):
        prefix = f"G4.cd.archetype.{char_name}[{i}]"

        # Historical figure name (must be specific, not abstract)
        name = source.get("name", "")
        if not name or not isinstance(name, str) or len(name) < 3:
            local_failures.append(f"{prefix}.name:too_short_or_missing")
            continue

        abstract_terms = ["elder", "mentor", "warrior", "sage", "hero", "villain",
                          "trickster", "maiden", "crone", "everyman"]
        if name.lower() in abstract_terms:
            local_failures.append(f"{prefix}.name:abstract_type_not_historical_figure")

        # traits_borrowed: >= 3
        borrowed = source.get("traits_borrowed", [])
        if not isinstance(borrowed, list) or len(borrowed) < 3:
            local_failures.append(
                f"{prefix}.traits_borrowed:need_3_got_{len(borrowed) if isinstance(borrowed, list) else 0}"
            )

        # traits_discarded: >= 2
        discarded = source.get("traits_discarded", [])
        if not isinstance(discarded, list) or len(discarded) < 2:
            local_failures.append(
                f"{prefix}.traits_discarded:need_2_got_{len(discarded) if isinstance(discarded, list) else 0}"
            )

        # adaptation_rationale: >= 100 characters
        rationale = source.get("adaptation_rationale", "")
        if not isinstance(rationale, str) or len(rationale) < 100:
            local_failures.append(
                f"{prefix}.adaptation_rationale:need_100_chars_got_{len(rationale) if isinstance(rationale, str) else 0}"
            )

        if not local_failures:
            checks.append({
                "id": f"G4.cd.archetype.{char_name}",
                "s": "PASS",
                "archetype_name": name,
                "borrowed_count": len(borrowed),
                "discarded_count": len(discarded),
                "rationale_chars": len(rationale),
            })

    return local_failures
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/g4/test_character_design.py::test_archetype_validation_passes_with_valid_archetype tests/unit/gates/g4/test_character_design.py::test_archetype_validation_fails_when_traits_borrowed_insufficient -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/character_design.py tests/unit/gates/g4/test_character_design.py
git commit -m "feat: add historical-archetype validation in G4 character checks

_validate_archetype() checks: specific historical figure name (not abstract
type), >= 3 traits_borrowed, >= 2 traits_discarded, >= 100 char
adaptation_rationale. Applied to protagonist and all major character files.
"
```

---

### Task 9: Restore character_matrix.md and Add arc_log Entries

**Files:**
- Create: `truth/character_matrix.md` (template)
- Modify: `skills/shenbi-state-settling/SKILL.md`

**Interfaces:**
- Consumes: character archives from `characters/` directories
- Produces: `truth/character_matrix.md` with slug-based cross-references updated per chapter

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path


def test_character_matrix_template_has_slug_column():
    matrix_path = Path(__file__).resolve().parents[3] / "truth" / "character_matrix.md"
    if not matrix_path.exists():
        pytest.skip("character_matrix.md not yet created")
    content = matrix_path.read_text(encoding="utf-8")
    assert "Slug" in content
    assert "Current State" in content
    assert "Arc Stage" in content
    assert "Last Updated Ch" in content


def test_state_settling_skill_mentions_character_matrix():
    skill_path = Path(__file__).resolve().parents[3] / "skills" / "shenbi-state-settling" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "character_matrix" in content


def test_state_settling_skill_mentions_arc_log():
    skill_path = Path(__file__).resolve().parents[3] / "skills" / "shenbi-state-settling" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "arc_log" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/g4/test_state_settling.py::test_character_matrix_template_has_slug_column -v`
Expected: FAIL or SKIP (file not found)

- [ ] **Step 3: Write minimal implementation**

Create `truth/character_matrix.md`:

```markdown
# Character Matrix

> Slug-based cross-reference tracker. Updated each chapter by shenbi-state-settling.

| Character | Slug | Current State | Current Location | Current Emotion | Active Relationships | Arc Stage | Last Updated Ch |
|-----------|------|--------------|-----------------|----------------|---------------------|-----------|----------------|
| Lin Feng | lin-feng | Active | — | — | — | Stage 1: Departure | 0 |
| Chen Weimin | chen-weimin | Active | — | — | Lin Feng (mentor) | Stage 1 | 0 |
| Zhao Tiezhu | zhao-tiezhu | Active | — | — | Lin Feng (partner) | Stage 1 | 0 |
| Chu Yunlan | chu-yunlan | Active | — | — | Lin Feng (ally) | Stage 1 | 0 |
| Koen Whiteman | koen-whiteman | Active | — | — | — | Stage 1 | 0 |
| Gangshan Tieya | gangshan-tieya | Active | — | — | — | Stage 1 | 0 |

**Last Updated:** Genesis
```

Update `skills/shenbi-state-settling/SKILL.md`. Add to `writes:` frontmatter:

```yaml
writes:
  - truth/character_matrix.md
```

Append to the prompt body:

```markdown
## Character Matrix Update (NEW)

After updating character state, update `truth/character_matrix.md`:

1. For each character that appeared in the current chapter:
   - Update "Current State" (e.g., Active, Deceased, Injured, Missing)
   - Update "Current Location" with slug reference to location
   - Update "Current Emotion" (primary emotional state)
   - Update "Active Relationships" with slug references
   - Update "Arc Stage" if a stage transition occurred this chapter
   - Set "Last Updated Ch" to current chapter number

2. For the protagonist specifically, append an `arc_log` entry to
   `characters/protagonist.md` frontmatter:

```yaml
arc_log:
  - chapter: {N}
    stage: {current_arc_stage}
    key_beat: {one-line description of arc-relevant event}
    emotional_shift: {from -> to}
    relationship_change: {brief description or "none"}
```

3. Write updated character_matrix.md to disk.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/g4/test_state_settling.py::test_character_matrix_template_has_slug_column tests/unit/gates/g4/test_state_settling.py::test_state_settling_skill_mentions_character_matrix tests/unit/gates/g4/test_state_settling.py::test_state_settling_skill_mentions_arc_log -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add truth/character_matrix.md skills/shenbi-state-settling/SKILL.md tests/unit/gates/g4/test_state_settling.py
git commit -m "feat: restore character_matrix.md with slug-based cross-references

Adds character_matrix.md template with slug column for referencing
character archives. Updates shenbi-state-settling SKILL.md to populate
matrix per chapter and append arc_log entries to protagonist.md.
"
```

---

### Task 10: Create chapter-file-format.md Documentation

**Files:**
- Create: `docs/framework/chapter-file-format.md`

**Interfaces:**
- Consumes: existing META block implementation in `gates/shared.py:120-121`
- Produces: documentation file, no code dependencies

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path


def test_chapter_file_format_doc_exists():
    doc_path = Path(__file__).resolve().parents[3] / "docs" / "framework" / "chapter-file-format.md"
    assert doc_path.exists(), f"Expected {doc_path} to exist"


def test_chapter_file_format_documents_meta_blocks():
    doc_path = Path(__file__).resolve().parents[3] / "docs" / "framework" / "chapter-file-format.md"
    if not doc_path.exists():
        pytest.skip("File not yet created")
    content = doc_path.read_text(encoding="utf-8")
    assert "META" in content
    assert "<!--META-BEGIN-->" in content or "META-BEGIN" in content


def test_chapter_file_format_documents_stripping_method():
    doc_path = Path(__file__).resolve().parents[3] / "docs" / "framework" / "chapter-file-format.md"
    if not doc_path.exists():
        pytest.skip("File not yet created")
    content = doc_path.read_text(encoding="utf-8")
    assert "strip" in content.lower() or "shared.py" in content


def test_chapter_file_format_states_meta_not_prose():
    doc_path = Path(__file__).resolve().parents[3] / "docs" / "framework" / "chapter-file-format.md"
    if not doc_path.exists():
        pytest.skip("File not yet created")
    content = doc_path.read_text(encoding="utf-8")
    assert "not part of" in content.lower() or "not prose" in content.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_docs_accuracy.py::test_chapter_file_format_doc_exists -v`
Expected: FAIL (file not found)

- [ ] **Step 3: Write minimal implementation**

Create `docs/framework/chapter-file-format.md`:

```markdown
# Chapter File Format Specification

## Overview

Each chapter file (`chapters/chapter-N.md`) serves as both a novel chapter
deliverable and an internal quality-control document. It contains two types
of content:

1. **Prose Body** -- the actual novel chapter content (the deliverable)
2. **META Blocks** -- internal quality-control self-check artifacts (not prose)

## File Structure

```markdown
<!--META-BEGIN-->
## PRE_WRITE_CHECK
[core task, hooks to fulfill, taboos, ending pattern, AI traps,
 resonance gaps, transition budget]
<!--META-END-->

# Chapter N: [Title]

[Prose content -- the actual novel chapter]

<!--META-BEGIN-->
## POST_WRITE_SELF_CHECK
[transition density check, curiosity check, meta-narrative check]
<!--META-END-->
```

## META Blocks

META blocks are quality-control artifacts embedded in chapter files.
They are **not part of the novel prose**. They exist to:
- Document the writer's pre-write planning checklist (PRE_WRITE_CHECK)
- Document the writer's post-write self-assessment (POST_WRITE_SELF_CHECK)
- Provide traceability for quality gate verification

### META Block Ratio

Across 56 generated chapters, the average META block proportion is
approximately 31.3% of file size. The pipeline monitoring gate (G2.meta_ratio)
triggers a WARN when this exceeds 50%.

## Stripping META Blocks

Any consumer that reads chapter files for pure prose must strip META blocks.
The canonical stripping implementation is at `src/shenbi/gates/shared.py:120-121`:

```python
c = re.sub(r"<!--META-BEGIN-->.*?<!--META-END-->", "", c, flags=re.DOTALL)
```

### Consumers that MUST strip:
- Word count functions (e.g., `shared.py:word_count_md`)
- Chapter scoring and quality analysis
- External publication tools
- Human readers

### Consumers that may read META blocks:
- Pipeline quality gate verification (G2, G4)
- Audit and scoring skills
- The pipeline itself (for checkpointing and state tracking)

## Future: META Block Separation

In a future specification (post Spec 2 stabilization), META blocks will be
extracted to separate `chapters/chapter-N-meta.md` files. At that point:
- `chapters/chapter-N.md` becomes pure prose
- META stripping logic in `shared.py` is removed
- All downstream audit/scoring skills read from `chapter-N-meta.md`
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_docs_accuracy.py::test_chapter_file_format_doc_exists tests/integration/test_docs_accuracy.py::test_chapter_file_format_documents_meta_blocks tests/integration/test_docs_accuracy.py::test_chapter_file_format_documents_stripping_method tests/integration/test_docs_accuracy.py::test_chapter_file_format_states_meta_not_prose -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add docs/framework/chapter-file-format.md tests/integration/test_docs_accuracy.py
git commit -m "docs: add chapter file format specification with META block documentation

Documents the dual-purpose nature of chapter-N.md files (prose + META),
the canonical stripping method, and the future separation plan.
"
```

---

### Task 11: Elevate META Stripping Warning in chapter-drafting SKILL.md

**Files:**
- Modify: `skills/shenbi-chapter-drafting/SKILL.md` (around line 129)

**Interfaces:**
- Consumes: none (documentation-only change)
- Produces: elevated warning block in skill prompt

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path


def test_chapter_drafting_skill_has_meta_warning_block():
    skill_path = Path(__file__).resolve().parents[3] / "skills" / "shenbi-chapter-drafting" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "WARNING" in content or "IMPORTANT" in content
    assert "META" in content
    assert "strip" in content.lower() or "not prose" in content.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/g4/test_chapter_drafting.py::test_chapter_drafting_skill_has_meta_warning_block -v`
Expected: FAIL or partial match

- [ ] **Step 3: Write minimal implementation**

Read the current `skills/shenbi-chapter-drafting/SKILL.md`, locate the existing comment around line 129, and replace it with a prominent warning block:

```markdown
> **WARNING: META blocks are NOT part of the novel prose.**
>
> META blocks (`<!--META-BEGIN-->...<!--META-END-->`) contain internal
> quality-control self-checks (PRE_WRITE_CHECK and POST_WRITE_SELF_CHECK).
> These are for pipeline use only. Downstream parsers (word count, audit,
> scoring, publication) MUST strip META blocks before processing prose.
> The canonical stripping method is in `src/shenbi/gates/shared.py:120-121`.
> See `docs/framework/chapter-file-format.md` for full specification.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/g4/test_chapter_drafting.py::test_chapter_drafting_skill_has_meta_warning_block -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/shenbi-chapter-drafting/SKILL.md tests/unit/gates/g4/test_chapter_drafting.py
git commit -m "docs: elevate META stripping comment to prominent warning block

Replaces inline comment at line 129 with a clearly marked WARNING block
that documents META block purpose, stripping requirement, and references
the canonical stripping method and format specification.
"
```

---

### Task 12: Add G2.meta_ratio WARN Check

**Files:**
- Modify: `src/shenbi/gates/g2.py`
- Test: `tests/unit/gates/test_g2.py`

**Interfaces:**
- Consumes: chapter `.md` files, META block regex pattern
- Produces: `G2.meta_ratio` WARN when META proportion exceeds 50%

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from shenbi.gates.g2 import _check_meta_ratio


def test_meta_ratio_returns_pass_when_under_50_percent(tmp_path: Path):
    chapter = tmp_path / "chapter-1.md"
    # 20% META content
    chapter.write_text("""<!--META-BEGIN-->
some meta
<!--META-END-->
This is the actual prose content of the chapter. It is much longer than the META block.
The prose continues for several more lines to ensure the ratio stays low.
Extra text here to pad the prose content and keep the META ratio under 50 percent.
More prose content to ensure the ratio is healthy.
Even more content here to make the prose section larger.
""")
    checks, failures = _check_meta_ratio(chapter)
    assert len(failures) == 0
    meta_check = [c for c in checks if "meta_ratio" in c.get("id", "")]
    assert len(meta_check) > 0
    assert meta_check[0]["s"] == "PASS"


def test_meta_ratio_warns_when_over_50_percent(tmp_path: Path):
    chapter = tmp_path / "chapter-1.md"
    # 60% META content
    chapter.write_text("""<!--META-BEGIN-->
some meta content that takes up a lot of space in the file
more meta content to pad the ratio
even more meta content to make it really large
still more meta content to ensure ratio exceeds 50%
additional meta content for padding purposes
<!--META-END-->
short prose.
""")
    checks, failures = _check_meta_ratio(chapter)
    assert len(failures) > 0
    assert any("G2.meta_ratio" in f for f in failures)


def test_meta_ratio_skips_file_with_no_meta_blocks(tmp_path: Path):
    chapter = tmp_path / "chapter-1.md"
    chapter.write_text("Pure prose content with no META blocks at all.")
    checks, failures = _check_meta_ratio(chapter)
    assert len(failures) == 0


def test_meta_ratio_calculates_correctly(tmp_path: Path):
    chapter = tmp_path / "chapter-1.md"
    chapter.write_text("""<!--META-BEGIN-->
AAAA
<!--META-END-->
BBBB
""")
    checks, failures = _check_meta_ratio(chapter)
    # 4 chars META / 8 chars total = 50% -- exactly at threshold, should PASS
    assert len(failures) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/test_g2.py::test_meta_ratio_returns_pass_when_under_50_percent -v`
Expected: FAIL (function not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/gates/g2.py`:

```python
_META_RE = re.compile(r"<!--META-BEGIN-->.*?<!--META-END-->", re.DOTALL)


def _check_meta_ratio(
    file_path: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Check META block proportion in chapter files.

    Returns (checks, failures). WARN-level: triggers when META block
    content exceeds 50% of total file size (indicates planning bloat).
    """
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    if not file_path.exists() or not file_path.suffix == ".md":
        return checks, failures

    content = file_path.read_text(encoding="utf-8")
    total_chars = len(content)

    meta_chars = sum(
        len(m.group(0)) for m in _META_RE.finditer(content)
    )

    if total_chars == 0:
        return checks, failures

    ratio = meta_chars / total_chars

    if meta_chars > 0:
        checks.append({
            "id": "G2.meta_ratio",
            "s": "WARN" if ratio > 0.5 else "PASS",
            "ratio": f"{ratio:.1%}",
            "meta_chars": meta_chars,
            "total_chars": total_chars,
        })

        if ratio > 0.5:
            failures.append(
                f"G2.meta_ratio:{ratio:.1%}_meta_exceeds_50%_threshold"
            )

    return checks, failures
```

Now integrate into `gate_G2()`. Find the section where individual file checks are performed (after G2.1 exists check) and add:

```python
# G2.meta_ratio: WARN when META block proportion > 50%
meta_checks, meta_failures = _check_meta_ratio(p)
checks.extend(meta_checks)
if meta_failures:
    mf.extend(meta_failures)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/test_g2.py::test_meta_ratio_returns_pass_when_under_50_percent tests/unit/gates/test_g2.py::test_meta_ratio_warns_when_over_50_percent tests/unit/gates/test_g2.py::test_meta_ratio_skips_file_with_no_meta_blocks tests/unit/gates/test_g2.py::test_meta_ratio_calculates_correctly -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g2.py tests/unit/gates/test_g2.py
git commit -m "feat: add G2.meta_ratio WARN check for META block proportion

Warns when META block content exceeds 50% of chapter file size,
indicating planning bloat. WARN-level only — does not block pipeline.
"
```

---

### Task 13: Final Integration -- Wire Plan Skeleton into Chapter Planning Dispatch

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (around `_build_skill_prompt`)
- Modify: `skills/shenbi-chapter-planning/SKILL.md`

**Interfaces:**
- Consumes: `plan_skeleton.generate_plan_skeleton()`
- Produces: chapter planning prompt injected with skeleton instead of blank slate

- [ ] **Step 1: Write the failing test**

> **Why this test is NOT a no-op:** The previous version of this test mocked `_build_skill_prompt` entirely and then called `generate_plan_skeleton` directly, which only re-tested Task 2 without verifying the wiring in `_build_skill_prompt`. This version calls the REAL `_build_skill_prompt` (no mock of that function) so it verifies the plan-skeleton content actually appears in the assembled dispatch prompt when `volume_map.md` exists.

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from shenbi.pipeline.dispatch_helper import _build_skill_prompt


def test_chapter_planning_prompt_includes_skeleton(tmp_path: Path):
    """When dispatching shenbi-chapter-planning, the REAL _build_skill_prompt
    must include a plan skeleton when volume_map.md exists.

    This does NOT mock _build_skill_prompt (that would make the test a no-op).
    Instead it exercises the real function and asserts the skeleton-derived
    content appears in the returned prompt, proving the Task 13 wiring works.
    """
    outline_dir = tmp_path / "outline"
    outline_dir.mkdir()
    (outline_dir / "volume_map.md").write_text("""# Volume Map
## Volume 1 (Ch 1-15)
### Chapter Nodes
| Ch | Role | Content |
|----|------|---------|
| 1 | opening | Test content |
""")
    # _build_skill_prompt needs a project structure; stub only the peripheral
    # I/O (skill lookup / project paths), NOT _build_skill_prompt itself.
    skill_dir = tmp_path / "skills" / "shenbi-chapter-planning"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: shenbi-chapter-planning\ndescription: Use when planning\n"
        "contract: {kind: artifact}\n---\n# Chapter Planning Skill body\n",
        encoding="utf-8",
    )

    # Call the REAL _build_skill_prompt. The exact signature/kwargs must match
    # dispatch_helper._build_skill_prompt; if it accepts (project_dir, skill,
    # chapter, ...) pass them. The assertion below is what proves wiring:
    # the skeleton content ("opening", "Test content", the "Plan Skeleton"
    # header) must appear in the prompt.
    prompt = _build_skill_prompt(
        project_dir=tmp_path,
        skill="shenbi-chapter-planning",
        chapter=1,
    )
    # Skeleton-derived content proves the Task 13 wiring injected the skeleton.
    assert "Plan Skeleton" in prompt or "plan skeleton" in prompt.lower()
    assert "Test content" in prompt
    assert "opening" in prompt.lower()
```

> **Signature note:** `_build_skill_prompt`'s exact keyword arguments must match the real function in `dispatch_helper.py`. If the real signature is `_build_skill_prompt(skill, project_dir, chapter)` (positional) or takes a `skills_dir=`, adjust the call accordingly while keeping the assertions identical. The test's purpose is to verify the skeleton content reaches the prompt through the REAL code path — do not mock `_build_skill_prompt`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py::test_chapter_planning_prompt_includes_skeleton -v`
Expected: FAIL before the Task 13 wiring is added (skeleton content absent from the real `_build_skill_prompt` output)

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/dispatch_helper.py`, in `_build_skill_prompt()` (or the function that assembles the prompt for dispatch), add skeleton injection for `shenbi-chapter-planning`:

```python
# In _build_skill_prompt, after loading the skill's SKILL.md prompt body:
if skill_name == "shenbi-chapter-planning" and chapter is not None:
    vm_path = project_dir / "outline" / "volume_map.md"
    if vm_path.exists():
        from shenbi.pipeline.plan_skeleton import generate_plan_skeleton
        skeleton = generate_plan_skeleton(project_dir, chapter)
        # Inject skeleton before the skill's own prompt
        prompt_parts = [
            "## Plan Skeleton (auto-generated from volume_map.md)",
            "",
            skeleton,
            "",
            "---",
            "",
            "Complete the [LLM]-marked sections above. Pre-filled sections",
            "are derived from the blueprint and are EDITABLE CONTEXT -- you",
            "may modify, override, or deviate from them as the story requires.",
            "Section 5 (Key Decisions) is entirely yours to create.",
            "",
            "---",
            "",
            prompt_body,
        ]
        prompt_body = "\n".join(prompt_parts)
```

Update `skills/shenbi-chapter-planning/SKILL.md` to document that it receives a pre-filled skeleton:

In the prompt body, near the top:

```markdown
## Input: Plan Skeleton

You will receive a pre-generated "Plan Skeleton" derived from the volume_map.md
blueprint. Sections marked `[LLM]` require your creative completion. Sections
with concrete content are EDITABLE CONTEXT derived from the blueprint -- you may
modify, override, or deviate from them as the story requires.

Do NOT regenerate pre-filled sections from scratch unless you are deliberately
deviating. Polish them if needed, and preserve the volume_map intent where it
serves the story. Section 5 (Key Decisions) is fully yours to create -- the
skeleton provides no constraints there.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py -v -k "chapter_planning or skeleton"`
Expected: PASS for relevant tests

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py skills/shenbi-chapter-planning/SKILL.md tests/unit/pipeline/test_dispatch_helper.py
git commit -m "feat: wire plan skeleton into chapter planning dispatch

_build_skill_prompt() now generates and injects a plan skeleton from
volume_map.md when dispatching shenbi-chapter-planning. The SKILL.md
prompt updated to document skeleton consumption contract.
"
```

---

### Task 14: Run Full Test Suite and Verify

- [ ] **Step 1: Run just check**

Run: `just check`
Expected: All four tools pass (ruff, mypy, basedpyright, pytest) with zero failures

- [ ] **Step 2: Run the specific new test modules**

Run: `pytest tests/unit/pipeline/test_context_assemble.py tests/unit/pipeline/test_plan_skeleton.py tests/unit/pipeline/test_bridge_tracker.py tests/unit/gates/g4/test_character_design.py tests/unit/gates/test_g2.py tests/unit/pipeline/test_dispatch_helper.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: final integration verification -- all tests passing"
```
