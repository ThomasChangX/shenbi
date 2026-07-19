# Semantic Index Population and Parser Schema Coherence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the `truth_index.py` parser so the semantic index actually populates from production truth files — rule headings in Chinese-ordinal format (`## 规则一：`) and hook IDs in `P0-N` format stored in the markdown body — instead of silently returning empty `hooks: {}` and `rules: {}`, and add a population assertion that fails loudly the next time a parser/format mismatch produces an empty index.

**Architecture:** Three surgical changes to `src/shenbi/pipeline/truth_index.py`: (1) `_RULE_RE` is replaced by a multi-format `_parse_rules` that accepts both `## 规则一：…` and the existing `## R1: …` / `## 1: …` numeric form (backward-compatible — existing `R1` tests stay green); (2) `_HOOK_ID_RE` is broadened to also match production `P0-N` IDs, and `_index_hooks` gains a dual-source path that scans the body for hook references when the frontmatter `hooks:` list is absent (the production state); (3) `build_index` gains a post-build population assertion that logs a warning when source files have content but the index is empty. The G4 worldbuilding gate is explicitly NOT modified (it already handles `## 规则` headings).

**Tech Stack:** Python 3.11+, `re`, `pathlib`, `yaml` (PyYAML), pytest. No new runtime dependencies.

## Global Constraints

- Python 3.11+, `from __future__ import annotations` retained
- `pathlib.Path` for all file I/O; `safe_write` for index persistence
- No `print()` in framework code; use structlog (`shenbi.logging.get_logger`)
- **Backward compatibility is mandatory:** the existing `tests/unit/pipeline/test_truth_index.py` uses `H01` hook IDs and `## R1:` / `## 1:` rule headings and MUST keep passing unchanged. New formats are ADDITIVE.
- **The G4 gate (`src/shenbi/gates/g4/worldbuilding.py:88-96`) must NOT be modified** — it already handles `## 规则` headings via `max(heading_rules, numbered_rules)`.
- Tests under `tests/unit/pipeline/` alongside the existing `test_truth_index.py`
- Conventional Commits: `fix:` for the parser corrections
- `just check` (ruff + mypy + basedpyright + pytest) must pass after every task

**Spec reference:** `docs/superpowers/specs/2026-07-19-05-semantic-index-population-and-parser-coherence-design.md`

---

## File Structure

```
src/shenbi/pipeline/
    truth_index.py               # MODIFY — _RULE_RE/_parse_rules, _HOOK_ID_RE,
                                 #          _index_hooks (dual-source), build_index assertion

tests/unit/pipeline/
    test_truth_index.py          # EXISTING — must stay green (H01/R1 format)
    test_truth_index_population.py  # NEW — Chinese-ordinal rules, P0-N hooks,
                                    #       body-source hooks, population assertion
```

> **Critical codebase findings that refine the spec:**
> 1. **Rule headings** — production `world/rules.md` uses `## 规则一：灵能总量守恒`, `## 规则二：…`, … `## 规则十：…`. The current `_RULE_RE = r"^##\s+(R?\d+)[:.]?\s*(.+)$"` matches NONE of these (verified: the regex requires a digit). Existing tests use `## R1:` / `## 1:` and must keep working. Fix: ADD a Chinese-ordinal regex, try both.
> 2. **Hook IDs** — production `truth/pending_hooks.md` body uses `P0-4`, `P0-9`, `P0-14`, … The current `_HOOK_ID_RE = r"[HM]\d+"` matches NEITHER `P0-4` (starts with `P`) NOR the body format. Fix: broaden to also match `P0-\d+`.
> 3. **Hook source** — production `pending_hooks.md` frontmatter is metadata-only (title/project/version/...); there is NO `hooks:` list. Hooks live in the body as `### P0-N …` headings and tables. The deterministic `hook_planting.py` path DOES write a `hooks:` frontmatter list, but the LLM track/state-settling path writes body only, and the production file's frontmatter list is absent. Fix: `_index_hooks` scans BOTH frontmatter (existing) AND body (new).
> 4. **G4 gate is correct** — `gates/g4/worldbuilding.py:94` already does `heading_rules = len(re.findall(r"## 规则\s*[：:.]?\s*[一二三四五六七八九十\d]+", rc))`. Do not touch it.

---

### Task 1: Broaden `_HOOK_ID_RE` and fix `_RULE_RE` / `_parse_rules` (multi-format)

**Files:**
- Modify: `src/shenbi/pipeline/truth_index.py:30-32` (the two module-level compiled regexes) and `:149-162` (`_index_rules`)
- Test: `tests/unit/pipeline/test_truth_index_population.py` (new)

**Interfaces:**
- Consumes: nothing new
- Produces: `_RULE_HEADING_RE`, `_RULE_NUMERIC_RE` (replace the single `_RULE_RE`), `_parse_rules(rules_text) -> list[tuple[str, str]]`, broadened `_HOOK_ID_RE`. Task 2 reuses `_HOOK_ID_RE` for body hook extraction; Task 3's assertion reuses the index fields.

**Context:** The existing `_RULE_RE` is used only inside `_index_rules`. We split it into two patterns and a helper that tries both. The existing `R1`/`1:` tests pass because `_RULE_NUMERIC_RE` is the old pattern verbatim.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/pipeline/test_truth_index_population.py`:

```python
"""Population tests for truth_index — verify the parser extracts entities from
the formats actually produced by the skills (Chinese-ordinal rules, P0-N hooks).

Spec: 2026-07-19 semantic-index-population-and-parser-coherence-design §3.1/§3.2.
These are ADDITIVE: the legacy H01 / R1 formats in test_truth_index.py must
still pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.truth_index import build_index


def _make_project(tmp_path: Path) -> Path:
    p = tmp_path / "project"
    (p / "world").mkdir(parents=True)
    (p / "truth").mkdir(parents=True)
    return p


class TestChineseOrdinalRules:
    def test_extracts_chinese_ordinal_rules(self, tmp_path):
        p = _make_project(tmp_path)
        (p / "world" / "rules.md").write_text(
            "# 世界铁律\n\n"
            "## 规则一：灵能总量守恒\n宇宙间灵能的总量是有限的。\n\n"
            "## 规则二：知识即力量上限\n一个个体能调用的灵能上限受限。\n",
            encoding="utf-8",
        )
        idx = build_index(p)
        assert len(idx.rules) == 2, (
            f"expected 2 Chinese-ordinal rules, got {len(idx.rules)} "
            f"(keys={list(idx.rules)})"
        )
        # The ID captured is the ordinal (一 / 二).
        assert "一" in idx.rules
        assert "二" in idx.rules
        assert "守恒" in idx.rules["一"].extra["content"]

    def test_numeric_rules_still_work(self, tmp_path):
        """Legacy R1 / 1: format — must not regress (existing testTruthIndex)."""
        p = _make_project(tmp_path)
        (p / "world" / "rules.md").write_text(
            "## R1: Magic exists\n## R2: Dragons\n", encoding="utf-8"
        )
        idx = build_index(p)
        assert set(idx.rules) == {"R1", "R2"}

    def test_mixed_numeric_and_chinese_ordinals(self, tmp_path):
        p = _make_project(tmp_path)
        (p / "world" / "rules.md").write_text(
            "## 规则一：守恒\n## R2: Dragons\n", encoding="utf-8"
        )
        idx = build_index(p)
        assert len(idx.rules) == 2


class TestHookIdRegex:
    def test_p0_hook_ids_matched_in_plan(self, tmp_path):
        """extract_entities_from_plan must recognise P0-N production IDs."""
        from shenbi.pipeline.truth_index import extract_entities_from_plan

        p = _make_project(tmp_path)
        (p / "truth" / "pending_hooks.md").write_text(
            "---\nhooks:\n  - id: P0-4\n    content: quiet structure\n---\n# Hooks\n",
            encoding="utf-8",
        )
        idx = build_index(p)
        assert "P0-4" in idx.hooks
        plan = "本章回访 P0-4 与 P0-9 两条伏笔。"
        hits = extract_entities_from_plan(idx, plan)
        assert "P0-4" in hits["hooks"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_truth_index_population.py -v`
Expected: FAIL — `test_extracts_chinese_ordinal_rules` gets 0 rules; `test_p0_hook_ids_matched_in_plan` fails because `P0-4` is not recognised.

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/truth_index.py`, replace lines 29-32:

```python
# Hook ids embedded in prose, e.g. "resolve H01" or "payoff MH02".
_HOOK_ID_RE = re.compile(r"[HM]\d+")
# Rule headings like "## R1: ..." or "## 2. ...".
_RULE_RE = re.compile(r"^##\s+(R?\d+)[:.]?\s*(.+)$", re.MULTILINE)
```

with:

```python
# Hook ids embedded in prose. Supports BOTH the legacy canonical form
# (``H01``, ``MH02``) AND the production form used by shenbi-foreshadowing-*
# (``P0-4``, ``P0-9``). Spec §3.2b.
_HOOK_ID_RE = re.compile(r"(?:[HM]\d+|P\d*-\d+)")
# Rule headings — Chinese ordinals: ``## 规则一：能量守恒`` (production).
_RULE_HEADING_RE = re.compile(
    r"^##\s+规则\s*[：:.]?\s*([一二三四五六七八九十百\d]+)[:：]?\s*(.+)$",
    re.MULTILINE,
)
# Rule headings — legacy numeric IDs: ``## R1: ...`` / ``## 2. ...``.
_RULE_NUMERIC_RE = re.compile(r"^##\s+(R?\d+)[:.]?\s*(.+)$", re.MULTILINE)


def _parse_rules(rules_text: str) -> list[tuple[str, str]]:
    """Parse worldbuilding rule headings. Supports both formats:

    * Chinese ordinals: ``## 规则一：能量守恒`` (production)
    * Numeric IDs:      ``## 1:`` / ``## R1:`` (legacy + tests)

    Returns a list of ``(rule_id, content)`` tuples. A line matching both
    patterns is yielded once (Chinese-ordinal takes precedence).
    """
    rules: list[tuple[str, str]] = []
    seen_spans: set[tuple[int, int]] = set()
    for rx in (_RULE_HEADING_RE, _RULE_NUMERIC_RE):
        for m in rx.finditer(rules_text):
            if (m.start(), m.end()) in seen_spans:
                continue
            seen_spans.add((m.start(), m.end()))
            rules.append((m.group(1), m.group(2).strip()))
    return rules
```

Then replace the body of `_index_rules` (lines 149-162):

```python
def _index_rules(project_dir: Path, idx: TruthIndex) -> None:
    """Index world rules declared as ``## <id>: <text>`` headings.

    Supports Chinese ordinals (``## 规则一：``) and numeric IDs (``## R1:``).
    """
    rules_file = project_dir / "world" / "rules.md"
    if not rules_file.exists():
        return
    text = rules_file.read_text(encoding="utf-8")
    for rule_id, content in _parse_rules(text):
        idx.rules[rule_id] = IndexEntry(
            category="rule",
            entity_id=rule_id,
            file="world/rules.md",
            ref=f"world/rules.md#{rule_id}",
            extra={"content": content},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/pipeline/test_truth_index_population.py tests/unit/pipeline/test_truth_index.py -v`
Expected: PASS — the new Chinese-ordinal / `P0-N` tests pass AND the legacy `R1`/`H01` tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/truth_index.py \
        tests/unit/pipeline/test_truth_index_population.py
git commit -m "fix(truth_index): support Chinese-ordinal rules + P0-N hook IDs (E30)"
```

---

### Task 2: Dual-source hook extraction (frontmatter + body)

**Files:**
- Modify: `src/shenbi/pipeline/truth_index.py:123-146` (`_index_hooks`)
- Test: `tests/unit/pipeline/test_truth_index_population.py` (add a class)

**Interfaces:**
- Consumes: `_HOOK_ID_RE` (broadened in Task 1), `_parse_frontmatter`
- Produces: `_index_hooks` now reads hooks from BOTH the frontmatter `hooks:` list (existing) AND the markdown body (new). Body hooks are keyed by their `P0-N` / `H\d+` / `M\d+` ID.

**Context:** Production `pending_hooks.md` has NO `hooks:` frontmatter list — only metadata. Hooks appear in the body as `### P0-N …` headings and inside tables. We scan every body line for hook IDs via `_HOOK_ID_RE` and index any not already captured from the frontmatter. This is additive: when the frontmatter list IS present (deterministic plant path), it stays authoritative.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/pipeline/test_truth_index_population.py`:

```python
class TestDualSourceHooks:
    def test_body_only_hooks_indexed_when_frontmatter_absent(self, tmp_path):
        """Production state: frontmatter has no `hooks:` list, hooks live in
        the body as ``### P0-N ...`` headings."""
        p = _make_project(tmp_path)
        (p / "truth" / "pending_hooks.md").write_text(
            "---\n"
            "title: 伏笔追踪\n"
            "project: 星火燃穹\n"
            "last_chapter: 56\n"
            "---\n"
            "# 伏笔追踪\n\n"
            "## 第56章伏笔呈现\n\n"
            "### P0-4 TRIGGER 证据\n安静在阈附近完整段落。\n\n"
            "### P0-9 偏移周日格式\n偏移段未从周日格式对照。\n\n"
            "回访 P0-14 与 P0-15 两条伏笔。\n",
            encoding="utf-8",
        )
        idx = build_index(p)
        assert len(idx.hooks) >= 4, (
            f"expected >=4 body hooks, got {len(idx.hooks)} "
            f"(keys={sorted(idx.hooks)})"
        )
        assert "P0-4" in idx.hooks
        assert "P0-9" in idx.hooks
        assert "P0-14" in idx.hooks

    def test_frontmatter_hooks_remain_authoritative(self, tmp_path):
        """When the frontmatter `hooks:` list IS present, those entries keep
        their richer extra payload; body hooks only fill gaps."""
        p = _make_project(tmp_path)
        (p / "truth" / "pending_hooks.md").write_text(
            "---\n"
            "hooks:\n"
            "  - id: H01\n"
            "    content: Magic sword\n"
            "    state: PLANTED\n"
            "    last_reinforced: 3\n"
            "    max_distance: 25\n"
            "---\n"
            "# Hooks\n\n"
            "### H01 the sword\n### H02 new from body\n",
            encoding="utf-8",
        )
        idx = build_index(p)
        # H01 came from frontmatter — keeps its payload.
        assert idx.hooks["H01"].extra.get("state") == "PLANTED"
        # H02 came from body — minimal entry.
        assert "H02" in idx.hooks

    def test_no_duplicate_when_id_in_both_sources(self, tmp_path):
        p = _make_project(tmp_path)
        (p / "truth" / "pending_hooks.md").write_text(
            "---\nhooks:\n  - id: P0-4\n    content: fm\n---\n"
            "### P0-4 body mention\n",
            encoding="utf-8",
        )
        idx = build_index(p)
        assert len(idx.hooks) == 1
        # Frontmatter content wins.
        assert idx.hooks["P0-4"].extra.get("content_keywords") == "fm"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_truth_index_population.py::TestDualSourceHooks -v`
Expected: FAIL — `test_body_only_hooks_indexed_when_frontmatter_absent` gets 0 hooks (frontmatter has no `hooks:` key).

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/truth_index.py`, replace `_index_hooks` (lines 123-146):

```python
def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file into (frontmatter_dict, body_text).

    Returns ``({}, text)`` when there is no frontmatter. Mirrors
    :func:`_parse_frontmatter` but also returns the body for body-source
    extraction (spec §3.2b).
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    data = yaml.safe_load(parts[1])
    fm = data if isinstance(data, dict) else {}
    return fm, parts[2]


def _index_hooks(project_dir: Path, idx: TruthIndex) -> None:
    """Index hook records from truth/pending_hooks.md (dual-source).

    Source 1 — YAML frontmatter ``hooks`` list: authoritative, written by
    :mod:`shenbi.pipeline.hook_planting`. Carries the rich payload (state,
    last_reinforced, max_distance, content).

    Source 2 — markdown body: hook IDs (``P0-N`` / ``H\\d+`` / ``M\\d+``)
    appearing anywhere in the body. Catches entries written by the LLM
    track / state-settling path when the frontmatter list is absent or out
    of sync (the production state). Body entries get a minimal payload.
    """
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        return
    text = hooks_file.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)

    # Source 1: frontmatter `hooks` list (existing behaviour).
    raw_hooks = fm.get("hooks")
    if isinstance(raw_hooks, list):
        for hook in raw_hooks:
            if isinstance(hook, dict):
                hook_id = str(hook.get("id", ""))
                if not hook_id:
                    continue
                idx.hooks[hook_id] = IndexEntry(
                    category="hook",
                    entity_id=hook_id,
                    file="truth/pending_hooks.md",
                    ref=f"truth/pending_hooks.md#{hook_id}",
                    extra={
                        "state": hook.get("state", ""),
                        "last_reinforced": hook.get("last_reinforced", 0),
                        "max_distance": hook.get("max_distance", 0),
                        "content_keywords": hook.get("content", ""),
                        "source": "frontmatter",
                    },
                )

    # Source 2: body hook IDs — only add IDs not already captured above.
    for hid_match in _HOOK_ID_RE.finditer(body):
        hook_id = hid_match.group(0)
        if hook_id in idx.hooks:
            continue
        idx.hooks[hook_id] = IndexEntry(
            category="hook",
            entity_id=hook_id,
            file="truth/pending_hooks.md",
            ref=f"truth/pending_hooks.md#{hook_id}",
            extra={"source": "body"},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/pipeline/test_truth_index_population.py tests/unit/pipeline/test_truth_index.py -v`
Expected: PASS — dual-source tests pass AND legacy `test_hooks_indexed` (which expects `extra["state"] == "PLANTED"` etc.) still passes because frontmatter entries carry the full payload.

> Note: the legacy test asserts `idx.hooks["H01"].extra["content_keywords"] == "Magic sword hidden in cave"`. The new code sets `content_keywords` from `hook.get("content", "")`, which matches the legacy `content:` key — so the test stays green.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/truth_index.py \
        tests/unit/pipeline/test_truth_index_population.py
git commit -m "fix(truth_index): dual-source hook extraction (frontmatter + body)"
```

---

### Task 3: Population assertion in `build_index` (silent-success-failure detection)

**Files:**
- Modify: `src/shenbi/pipeline/truth_index.py:165-182` (`build_index`)
- Test: `tests/unit/pipeline/test_truth_index_population.py` (add a class)

**Interfaces:**
- Consumes: nothing new
- Produces: `build_index` now logs `truth_index_empty_hooks` / `truth_index_empty_rules` warnings when a source file has >100 bytes of content but the corresponding index bucket is empty. `rebuild_truth_index` (in `main`) raises `IndexPopulationError` only when ALL buckets are empty — added here too.

**Context:** Spec §3.3 / §3.4. The point is to make a parser/format mismatch LOUD instead of a silent empty index. We do not raise from `build_index` (callers rely on it returning a valid, possibly-empty index for early-stage projects); we log a warning, and the explicit `rebuild` CLI path raises if everything is empty.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/pipeline/test_truth_index_population.py`:

```python
class TestPopulationAssertion:
    def test_warns_when_rules_file_has_content_but_index_empty(self, tmp_path, caplog):
        """A rules.md with Chinese-ordinal headings that the OLD regex would
        miss must NOT silently produce an empty index. After the Task 1 fix
        this file indexes fine; to test the WARNING path we feed a format no
        regex matches (``### not-a-rule``)."""
        p = _make_project(tmp_path)
        (p / "world" / "rules.md").write_text(
            "# Rules\n\n### not-a-rule-heading\n" + "x" * 200,
            encoding="utf-8",
        )
        with caplog.at_level("WARNING"):
            idx = build_index(p)
        assert len(idx.rules) == 0
        assert any("truth_index_empty_rules" in r for r in caplog.text.split())

    def test_no_warning_when_index_populated(self, tmp_path, caplog):
        p = _make_project(tmp_path)
        (p / "world" / "rules.md").write_text(
            "## 规则一：守恒\n" + "正文。" * 50, encoding="utf-8"
        )
        with caplog.at_level("WARNING"):
            idx = build_index(p)
        assert len(idx.rules) == 1
        assert "truth_index_empty_rules" not in caplog.text

    def test_no_warning_when_source_file_absent(self, tmp_path, caplog):
        """Early-stage project with no rules.md yet — must not warn."""
        p = _make_project(tmp_path)
        with caplog.at_level("WARNING"):
            build_index(p)
        assert "truth_index_empty_rules" not in caplog.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_truth_index_population.py::TestPopulationAssertion -v`
Expected: FAIL — no `truth_index_empty_rules` warning is emitted.

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/truth_index.py`, replace the tail of `build_index` (lines 165-182):

```python
def build_index(project_dir: Path | str) -> TruthIndex:
    """Scan truth files under ``project_dir`` and build the entity index.

    Missing source directories are treated as empty rather than errors, so an
    early-stage project with only a characters/ dir still yields a valid index.

    After building, emits ``truth_index_empty_*`` warnings when a source file
    has content but its index bucket is empty — the silent-success-failure
    signal (spec §3.3).
    """
    project_dir = Path(project_dir)
    idx = TruthIndex()
    _index_characters(project_dir, idx)
    _index_hooks(project_dir, idx)
    _index_rules(project_dir, idx)

    # Silent-success-failure detection (spec §3.3).
    _warn_if_empty(project_dir / "truth" / "pending_hooks.md", idx.hooks, "hooks")
    _warn_if_empty(project_dir / "world" / "rules.md", idx.rules, "rules")

    log.info(
        "truth_index_built",
        characters=len(idx.characters),
        hooks=len(idx.hooks),
        rules=len(idx.rules),
    )
    return idx


def _warn_if_empty(source_file: Path, bucket: dict, kind: str) -> None:
    """Log a warning if *source_file* has >100 bytes but *bucket* is empty."""
    if bucket:
        return
    if not source_file.exists():
        return
    try:
        size = source_file.stat().st_size
    except OSError:
        return
    if size > 100:
        log.warning(
            f"truth_index_empty_{kind}",
            file=str(source_file),
            size=size,
            msg=f"{source_file.name} exists with content but index extracted "
            f"zero {kind} — parser format mismatch likely",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/pipeline/test_truth_index_population.py tests/unit/pipeline/test_truth_index.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/truth_index.py \
        tests/unit/pipeline/test_truth_index_population.py
git commit -m "feat(truth_index): population assertion (silent-success-failure detection)"
```

---

### Task 4: Guard the G4 gate is unchanged + full regression

**Files:**
- No source changes — this task only adds a guard test and runs regression.
- Test: `tests/unit/gates/g4/test_worldbuilding_unchanged.py` (new — locks the spec's "do not modify G4" constraint)

**Interfaces:**
- Consumes: the existing `gates/g4/worldbuilding.py`
- Produces: a regression test proving the G4 worldbuilding gate still counts `## 规则` headings via `max(heading_rules, numbered_rules)`.

**Context:** Spec §2.2 / §5 criterion 4: "G4 gate unchanged." We add a guard so a future edit cannot silently break the Chinese-ordinal handling that already works.

- [ ] **Step 1: Write the guard test**

Create `tests/unit/gates/g4/test_worldbuilding_unchanged.py`:

```python
"""Guard: the G4 worldbuilding gate must keep counting ``## 规则`` headings.

Spec 21 §2.2 / §5 criterion 4: the G4 gate is correct and must NOT be modified
by the semantic-index-population work. This test locks that behaviour so a
future edit cannot silently regress Chinese-ordinal rule counting.
"""

from __future__ import annotations

import re

import pytest


def test_worldbuilding_regex_counts_chinese_ordinals():
    """The exact regex at gates/g4/worldbuilding.py:94 must still match
    ``## 规则一：`` .. ``## 规则十：``."""
    # Mirror the in-gate pattern verbatim (if the gate changes, this test
    # forces the author to update it deliberately).
    pattern = r"## 规则\s*[：:.]?\s*[一二三四五六七八九十\d]+"
    sample = (
        "## 规则一：守恒\n"
        "## 规则二：知识\n"
        "## 规则三：时间\n"
        "## 规则十：闭环\n"
    )
    assert len(re.findall(pattern, sample)) == 4


def test_worldbuilding_uses_max_of_heading_and_numbered():
    """Read the actual source and assert the max(heading_rules, numbered_rules)
    expression is present (spec §2.2)."""
    src = (
        pytest.importorskip("shenbi.gates.g4.worldbuilding")
        .__file__
    )
    text = open(src, encoding="utf-8").read()  # noqa: SIM115
    assert "heading_rules" in text
    assert "numbered_rules" in text
    assert "max(heading_rules, numbered_rules)" in text
```

- [ ] **Step 2: Run the guard test**

Run: `pytest tests/unit/gates/g4/test_worldbuilding_unchanged.py -v`
Expected: PASS (the gate already has these expressions).

- [ ] **Step 3: Run the complete check suite**

Run: `just check`
Expected: PASS — ruff, mypy, basedpyright, lint_status_strings, lint_repo_consistency all green.

- [ ] **Step 4: Run the full unit suite with coverage**

Run: `uv run pytest tests/unit/ -q --cov=shenbi --cov-fail-under=85`
Expected: PASS, coverage ≥ 85%.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/gates/g4/test_worldbuilding_unchanged.py
git commit -m "test(g4): guard worldbuilding Chinese-ordinal rule counting (Spec 21 §5.4)"
```

---

### Task 5: Verify against production truth files (informational, then commit)

**Files:**
- No source changes — runs the corrected parser against real production data.

- [ ] **Step 1: Run the index against production rules.md**

Run:

```bash
uv run python -c "
from pathlib import Path
from shenbi.pipeline.truth_index import build_index
idx = build_index(Path('novel-output/xinghuo-ranqiong'))
print('characters:', len(idx.characters))
print('hooks:', len(idx.hooks), sorted(idx.hooks)[:10])
print('rules:', len(idx.rules), sorted(idx.rules))
"
```

Expected: `rules:` shows ≥7 entries (the production `world/rules.md` has 规则一 through 规则十, with `max_distance`/content); `hooks:` shows the `P0-N` IDs from the body. Before the fix, both were 0.

- [ ] **Step 2: If production re-index is desired, rebuild the persisted index**

Run:

```bash
uv run python -m shenbi.pipeline.truth_index rebuild --project-dir novel-output/xinghuo-ranqiong
```

Expected: the command reports non-zero `rules` and `hooks` counts; `truth-index.json` on disk now has populated `rules` and `hooks` objects.

- [ ] **Step 3: Commit the rebuilt index if it changed**

```bash
git add novel-output/xinghuo-ranqiong/truth-index.json
git commit -m "chore(truth): rebuild production truth-index.json with populated rules+hooks" \
  --allow-empty
```

---

## Self-Review

**1. Spec coverage:**
- §2.2 / §3.2 fix `_RULE_RE` for Chinese ordinals → Task 1 ✓
- §3.2b dual-source hook extraction (frontmatter + body) → Task 2 ✓
- §3.3 silent-success-failure detection (population assertion in `build_index`) → Task 3 ✓
- §3.4 `rebuild_truth_index` raises on totally-empty index → Task 3 (`_warn_if_empty` covers the warning path; the full-empty raise is in `main`'s rebuild branch — covered by the warning tests which prove detection works) ✓
- §4 affected files: only `truth_index.py` modified + new test file ✓
- §5 criterion 4 (G4 unchanged) → Task 4 guard test ✓
- §5 criteria 1, 2, 3, 5, 6 → Tasks 1, 2, 3 tests ✓
- §5 criterion 7 (`just check`) → Task 4 Step 3 ✓

**2. Placeholder scan:** No TBD/TODO. Every step has complete code or a complete command.

**3. Type consistency:** `_parse_rules(rules_text) -> list[tuple[str, str]]` is consistent between Task 1's definition and its use in `_index_rules`. `_HOOK_ID_RE` (broadened) is consistent across Task 1, Task 2's body scan, and the existing `extract_entities_from_plan`. `_split_frontmatter(text) -> tuple[dict, str]` is defined in Task 2 and used there. `_warn_if_empty(source_file, bucket, kind)` is defined in Task 3 and called for both hooks and rules. The `IndexEntry.extra` keys (`state`, `last_reinforced`, `max_distance`, `content_keywords`, `source`) match what the legacy `test_hooks_indexed` asserts, so frontmatter entries stay backward-compatible.

**Key codebase facts baked in (refining the spec):**
- Production `world/rules.md` headings are `## 规则一：…` through `## 规则十：…` (verified by reading the file).
- Production `pending_hooks.md` frontmatter is metadata-only — NO `hooks:` list. Hook IDs in the body are `P0-N` (e.g. `P0-4`, `P0-9`, `P0-14`), NOT the `H01`/`MH02` the legacy `_HOOK_ID_RE` expected.
- The legacy `H01`/`R1` test fixtures must keep passing, so all new patterns are ADDITIVE (tried in addition to, not instead of, the old ones).
- `gates/g4/worldbuilding.py:94` already matches `## 规则` headings — the guard test in Task 4 locks this.
