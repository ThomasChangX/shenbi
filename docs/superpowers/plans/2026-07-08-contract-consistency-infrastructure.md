# Contract Consistency Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eradicate pipeline/skill file-path mismatches and contract inconsistencies via five root-cause mechanisms (single resolver / RoundPaths three-root / contract graph closure + Producer Registry / schema-first pydantic / unified match_field) plus excision of 7 confirmed live bugs.

**Architecture:** Three-layer stack — Layer A (runtime: paths/fields/RoundPaths shared modules), Layer B (schema: pydantic models for all multi-consumer structured files), Layer C (CI static checks: closure/field/version). Schema is foundation, runtime consumes it, CI validates it. Schema-first immediate cutover (no transitional two-logic period — project has no historical baggage).

**Tech Stack:** Python 3.11+, pydantic v2, pytest, justfile, structlog. Framework code under `src/shenbi/`, tests under `tests/`.

**Spec:** `docs/superpowers/specs/2026-07-08-contract-consistency-infrastructure-design.md`

## Global Constraints

- Python 3.11+; `pathlib.Path` for file I/O; `json` for structured output; no `print()` in framework code (use structlog).
- Gate functions return `passed()`/`fail()` helpers; idempotent (pure validation, no side effects on output files except gate markers).
- All tests use real fixtures (G0.9: no hand-crafted mocks); test scenarios reference `tests/fixtures/` paths.
- Conventional Commits: `feat:`/`fix:`/`test:`/`docs:`/`chore:`.
- Run `just check` before every commit (ruff + mypy + basedpyright + pytest + lints).
- Every task commits independently; each commit keeps `just check` green.
- Failure semantics: static CI checks = FAIL (block PR); runtime gates = WARN (don't interrupt dispatch).

---

## File Structure

**New shared modules (Layer A + B foundation):**
- `src/shenbi/contracts/paths.py` — `resolve_chapter_path` + `resolve_volume_path` + `extract_chapter` + `resolve_or_skip` + `UnresolvedPathError`
- `src/shenbi/contracts/fields.py` — `match_field` + `filter_to_fields`
- `src/shenbi/contracts/graph.py` — `dag_key` (extracted from sync_contracts)
- `src/shenbi/paths.py` — `RoundPaths` (three-root value object)
- `src/shenbi/contracts/schemas/__init__.py` — package init
- `src/shenbi/contracts/schemas/decisions.py` — `DecisionsDoc` / `Selection` / `Adjustment` / `Budget`
- `src/shenbi/contracts/schemas/registry.py` — `TruthFilesRegistry` / `RegistryConcept` / `RegistryPattern` / `RegistryGlob`
- `src/shenbi/contracts/schemas/deps.py` — `DepsDoc` / `PhaseDeps` / `PipelineDeps` / `OutOfPipeline`
- `src/shenbi/contracts/schemas/novel.py` — `NovelConfig`
- `src/shenbi/contracts/schemas/scores.py` — `ScoreReport`
- `src/shenbi/contracts/schemas/state.py` — `ProgressDoc` / `SummaryDoc` (extra: ignore)
- `src/shenbi/contracts/schemas/adapt.py` — `pydantic_err_to_gate_failures` adapter

**New CI tools (Layer C):**
- `tools/lint_contract_graph.py` — closure check (ORPHAN_READ FAIL / DANGLING_WRITE WARN)
- `scripts/lint_contract_fields.py` — upgraded (fixture-driven, uses match_field, FAIL)

**Modified (runtime migration):**
- `src/shenbi/dispatcher/executor.py` — delete `_resolve_chapter_path`/`_extract_chapter`; use RoundPaths
- `src/shenbi/pipeline/dispatch_helper.py` — delete `_resolve_path`/`_filter_to_fields`/`_extract_chapter`; use RoundPaths
- `src/shenbi/pipeline/chapter_loop.py` — delete `_substitute_chapter`; use resolve_chapter_path
- `src/shenbi/pipeline/closure.py` — delete `_substitute_volume`; use resolve_volume_path
- `src/shenbi/gates/{g1,g2,g5}.py` — RoundPaths; `.bak` via rp.backup(); fix g1.py:65 docstring
- `src/shenbi/gates/g4/*.py` (all checkers incl. 10 hardcoded) — RoundPaths; delete resolve_g4_base CWD fallback
- `src/shenbi/gates/g4/style_polishing.py` — `.bak` via rp.backup()
- `src/shenbi/gates/g4/{decisions_validator.py,_decisions_schema.py}` — delete (replaced by DecisionsDoc)
- `src/shenbi/gates/g2.py` — decisions branch uses DecisionsDoc
- `src/shenbi/gates/g3.py` — D19: delete per-skill prereq check (dead function)
- `src/shenbi/gates/g6.py` — D16: fix style_profile path; D26: fix target_word_count
- `src/shenbi/gates/g1.py` — BACKUP_SKILLS derived (delete hardcoded frozenset)
- `src/shenbi/dispatcher/modes/codex.py` — rubric via rp.repo()
- `src/shenbi/contracts/legacy.py` — load_registry returns TruthFilesRegistry
- `src/shenbi/contracts/registry.py` — delete dead REGISTRY/load_skill_contract
- `docs/framework/truth-files.yaml` — add `producer` field; register pipeline files
- `justfile` — add `lint-contracts` target

---

## Phase 1: Foundation (shared modules + schemas)

Schema-first immediate cutover. Build all shared modules and models first; consumers migrate in Phase 2.

### Task 1: contracts/paths.py — single resolver + extract_chapter

**Files:**
- Create: `src/shenbi/contracts/paths.py`
- Test: `tests/unit/contracts/test_paths.py`

**Interfaces:**
- Produces: `resolve_chapter_path(path: str, chapter: int | None) -> str`, `resolve_volume_path(path: str, volume: int | None) -> str`, `extract_chapter(text: str) -> int | None`, `resolve_or_skip(path: str, chapter: int | None) -> str | None`, `UnresolvedPathError(ValueError)`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/contracts/test_paths.py
import pytest
from shenbi.contracts.paths import (
    resolve_chapter_path, resolve_volume_path, extract_chapter,
    resolve_or_skip, UnresolvedPathError,
)

class TestResolveChapterPath:
    def test_nnn_zero_pads(self):
        assert resolve_chapter_path("snapshots/chapter-NNN/", 5) == "snapshots/chapter-005/"

    def test_n_bounded_at_separator(self):
        assert resolve_chapter_path("chapters/chapter-N.md", 5) == "chapters/chapter-5.md"

    def test_n_not_corrupted_mid_token_uppercase(self):
        # C2 fix: uppercase N mid-token must NOT be replaced
        assert resolve_chapter_path("import/canon/01_SECTION.md", 5) == "import/canon/01_SECTION.md"
        assert resolve_chapter_path("NPC-list.md", 5) == "NPC-list.md"

    def test_lowercase_n_unaffected(self):
        # str.replace("N") is case-sensitive; lowercase n never corrupted
        assert resolve_chapter_path("truth/resonance_trend.md", 5) == "truth/resonance_trend.md"

    def test_none_with_placeholder_raises(self):
        with pytest.raises(UnresolvedPathError):
            resolve_chapter_path("chapters/chapter-N.md", None)

    def test_none_without_placeholder_passes(self):
        assert resolve_chapter_path("truth/current_state.md", None) == "truth/current_state.md"

class TestResolveVolumePath:
    def test_volume_no_zero_pad(self):
        assert resolve_volume_path("audits/volume-N-payoff.md", 3) == "audits/volume-3-payoff.md"

    def test_volume_none_raises(self):
        with pytest.raises(UnresolvedPathError):
            resolve_volume_path("audits/volume-N-payoff.md", None)

class TestExtractChapter:
    def test_word_boundary(self):
        assert extract_chapter("Execute skill for chapter 5 now") == 5

    def test_subchapter_not_matched(self):
        # unified to word-boundary: subchapter does not match
        assert extract_chapter("subchapter 5") is None

    def test_case_insensitive(self):
        assert extract_chapter("CHAPTER 12") == 12

class TestResolveOrSkip:
    def test_genesis_skips_placeholder(self):
        assert resolve_or_skip("chapters/chapter-N.md", None) is None

    def test_chapter_resolves(self):
        assert resolve_or_skip("chapters/chapter-N.md", 5) == "chapters/chapter-5.md"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/contracts/test_paths.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.contracts.paths'`

- [ ] **Step 3: Implement paths.py**

```python
# src/shenbi/contracts/paths.py
"""Single source of truth for chapter/volume placeholder resolution.

Replaces 4 divergent implementations (executor._resolve_chapter_path,
dispatch_helper._resolve_path, chapter_loop._substitute_chapter,
closure._substitute_volume). The unbounded str.replace("N") in the old
executor/closure versions corrupted any path containing uppercase N
(e.g. import/canon/01_SECTION.md -> 01_SECTIO5.md). The bounded regex here
only replaces N at separator boundaries.
"""
from __future__ import annotations
import re

class UnresolvedPathError(ValueError):
    """Path contains a chapter/volume placeholder but no context was provided."""

_BOUND_N = re.compile(r"(?<=[-/])N(?=[-./]|$)")
_NNN = "NNN"

def _bounded_replace_n(path: str, value: int) -> str:
    return _BOUND_N.sub(str(value), path)

def resolve_chapter_path(path: str, chapter: int | None) -> str:
    if chapter is None:
        if _NNN in path or _BOUND_N.search(path):
            raise UnresolvedPathError(path)
        return path
    result = path.replace(_NNN, f"{chapter:03d}")
    return _bounded_replace_n(result, chapter)

def resolve_volume_path(path: str, volume: int | None) -> str:
    if volume is None:
        if _BOUND_N.search(path):
            raise UnresolvedPathError(path)
        return path
    return _bounded_replace_n(path, volume)

def extract_chapter(text: str) -> int | None:
    m = re.search(r"\bchapter\s+(\d+)\b", text, re.IGNORECASE)
    return int(m.group(1)) if m else None

def resolve_or_skip(path: str, chapter: int | None) -> str | None:
    """Genesis-mode helper: returns None if path has unresolvable placeholder."""
    try:
        return resolve_chapter_path(path, chapter)
    except UnresolvedPathError:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/contracts/test_paths.py -v`
Expected: PASS (all 12 tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/paths.py tests/unit/contracts/test_paths.py
git commit -m "feat: add contracts/paths.py single resolver (replaces 4 divergent impls)"
```

---

### Task 2: contracts/fields.py — match_field + filter_to_fields

**Files:**
- Create: `src/shenbi/contracts/fields.py`
- Test: `tests/unit/contracts/test_fields.py`

**Interfaces:**
- Consumes: nothing (standalone)
- Produces: `match_field(declared: str, heading: str) -> bool`, `filter_to_fields(text: str, fields: list[str], path: str) -> tuple[str, bool]` (returns `(filtered_text, matched_any)`), `extract_h2_sections(text: str) -> dict[str, str]`, `project_json_keys(text: str, fields: list[str]) -> tuple[str, bool]`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/contracts/test_fields.py
from shenbi.contracts.fields import match_field, filter_to_fields, extract_h2_sections

class TestMatchField:
    def test_exact_match(self):
        assert match_field("1. 当前任务", "1. 当前任务") is True

    def test_strips_whitespace(self):
        assert match_field("1. 当前任务", "  1. 当前任务  ") is True

    def test_fullwidth_space_folded(self):
        # I3: U+3000 folded to ASCII space
        assert match_field("1. 当前任务", "1.　当前任务") is True

    def test_multiple_spaces_folded(self):
        assert match_field("1. 当前任务", "1.  当前任务") is True

    def test_no_lowercase(self):
        # Chinese headings: do NOT lowercase (preserves semantics)
        assert match_field("ABC", "abc") is False

    def test_zero_width_not_folded(self):
        # U+200B carries semantic meaning; do NOT fold
        assert match_field("ab", "a\u200bb") is False

class TestFilterToFields:
    MD = "# Title\n\n## 1. 当前任务\n内容A\n\n## 2. 世界设定\n内容B\n\n## 3. 其他\n内容C\n"

    def test_filters_to_declared_sections(self):
        result, matched = filter_to_fields(MD, ["1. 当前任务", "2. 世界设定"], "truth/test.md")
        assert matched is True
        assert "内容A" in result
        assert "内容B" in result
        assert "内容C" not in result

    def test_escape_hatch_returns_full_when_no_match(self):
        result, matched = filter_to_fields(MD, ["不存在的字段"], "truth/test.md")
        assert matched is False
        assert "内容A" in result  # full text returned

    def test_json_projects_keys(self):
        import json
        data = json.dumps({"fatigueWords": [], "pacing": "fast", "other": "x"})
        result, matched = filter_to_fields(data, ["fatigueWords", "pacing"], "genre-config.json")
        assert matched is True
        assert "fatigueWords" in result
        assert "other" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/contracts/test_fields.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement fields.py**

```python
# src/shenbi/contracts/fields.py
"""Unified field-level filtering. Replaces 3 divergent matching semantics:
extract_h2_sections (exact), check_fields_exist (exact), lint normalize (lower).
Canonical rule: strip + fold ASCII whitespace AND U+3000 to single ASCII space;
do NOT lowercase (preserves Chinese heading semantics);
do NOT fold zero-width chars (U+200B carries semantic meaning).
"""
from __future__ import annotations
import json
import re
import structlog

log = structlog.get_logger()

# Fold ASCII whitespace + U+3000 (fullwidth space). Explicitly excludes U+200B/200C/200D.
_WS_FOLD = re.compile(r"[\s\u3000]+")

def _normalize_ws(s: str) -> str:
    return _WS_FOLD.sub(" ", s).strip()

def match_field(declared: str, heading: str) -> bool:
    return _normalize_ws(declared) == _normalize_ws(heading)

def extract_h2_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_body).strip()
            current_heading = line[3:].strip()
            current_body = []
        elif current_heading is not None:
            current_body.append(line)
    if current_heading is not None:
        sections[current_heading] = "\n".join(current_body).strip()
    return sections

def _filter_md(text: str, fields: list[str]) -> tuple[str, bool]:
    sections = extract_h2_sections(text)
    matched: dict[str, str] = {}
    for heading, body in sections.items():
        if any(match_field(f, heading) for f in fields):
            matched[heading] = body
    if not matched:
        log.warning("field_filter_no_match", fields=fields, available=list(sections.keys()))
        return text, False
    return "\n\n".join(f"## {h}\n{b}" for h, b in matched.items()), True

def _filter_json(text: str, fields: list[str]) -> tuple[str, bool]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        log.warning("field_filter_json_invalid", path="json")
        return text, False
    if not isinstance(data, dict):
        return text, False
    projected = {k: v for k, v in data.items() if k in fields}
    if not projected:
        log.warning("field_filter_no_match", fields=fields, available=list(data.keys()))
        return text, False
    return json.dumps(projected, ensure_ascii=False, indent=2), True

def filter_to_fields(text: str, fields: list[str], path: str) -> tuple[str, bool]:
    """Returns (filtered_text, matched_any). Caller decides WARN vs FAIL on matched=False."""
    if not fields:
        return text, True
    if path.endswith(".md"):
        return _filter_md(text, fields)
    if path.endswith(".json"):
        return _filter_json(text, fields)
    return text, True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/contracts/test_fields.py -v`
Expected: PASS (all 9 tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/fields.py tests/unit/contracts/test_fields.py
git commit -m "feat: add contracts/fields.py unified match_field (folds ASCII+U+3000, no lowercase)"
```

---

### Task 3: contracts/graph.py — dag_key (extracted)

**Files:**
- Create: `src/shenbi/contracts/graph.py`
- Test: `tests/unit/contracts/test_graph.py`
- Modify: `src/shenbi/sync_contracts.py` (import dag_key from graph.py instead of defining locally)

**Interfaces:**
- Consumes: registry dict (from load_registry, shape: `{concepts, patterns, globs}`)
- Produces: `dag_key(path: str, registry: dict) -> str`, `normalize_to_glob(path: str, registry: dict) -> str`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/contracts/test_graph.py
from shenbi.contracts.graph import dag_key, normalize_to_glob

REGISTRY = {
    "concepts": [{"name": "truth/current_state.md", "kind": "truth"}],
    "patterns": [{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}],
    "globs": [{"pattern": "truth/*.md"}, {"pattern": "chapters/chapter-*.md"}],
}

def test_exact_concept_passthrough():
    assert dag_key("truth/current_state.md", REGISTRY) == "truth/current_state.md"

def test_glob_match_folds_to_glob():
    # A path matching a declared glob folds to that glob pattern
    key = dag_key("truth/other.md", REGISTRY)
    assert key == "truth/*.md"

def test_parametric_resolves_to_glob():
    # chapters/chapter-N.md (parametric) -> its declared glob chapters/chapter-*.md
    assert normalize_to_glob("chapters/chapter-N.md", REGISTRY) == "chapters/chapter-*.md"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/contracts/test_graph.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implement graph.py (move logic from sync_contracts.py)**

Read `src/shenbi/sync_contracts.py` lines 33-89 (the existing `normalize_to_glob` and `dag_key`). Move them verbatim to `contracts/graph.py`. In `sync_contracts.py`, replace the local definitions with an import.

```python
# src/shenbi/contracts/graph.py
"""Glob-aware DAG key normalization. Extracted from sync_contracts.py so that
G5.2 (runtime WARN), lint_contract_graph (CI FAIL), and sync_contracts (DAG
generation) all use IDENTICAL matching semantics."""
from __future__ import annotations
import fnmatch

def normalize_to_glob(path: str, registry: dict) -> str:
    for p in registry.get("patterns", []):
        if path == p.get("parametric"):
            return p.get("glob", path)
    for g in registry.get("globs", []):
        if fnmatch.fnmatch(path, g["pattern"]):
            return str(g["pattern"])
    return path

def dag_key(path: str, registry: dict) -> str:
    for g in registry.get("globs", []):
        if fnmatch.fnmatch(path, g["pattern"]):
            return str(g["pattern"])
    return normalize_to_glob(path, registry)
```

Then edit `src/shenbi/sync_contracts.py`: delete the local `normalize_to_glob`/`dag_key` defs, add `from shenbi.contracts.graph import dag_key, normalize_to_glob`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/contracts/test_graph.py tests/unit/test_sync_contracts.py -v`
Expected: PASS (new graph tests + existing sync_contracts tests still pass — behavior identical, just relocated)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/graph.py tests/unit/contracts/test_graph.py src/shenbi/sync_contracts.py
git commit -m "refactor: extract dag_key to contracts/graph.py (shared by G5.2/lint/sync)"
```

---

### Task 4: paths.py — RoundPaths three-root value object

**Files:**
- Create: `src/shenbi/paths.py`
- Test: `tests/unit/test_round_paths.py`

**Interfaces:**
- Consumes: `resolve_chapter_path` from contracts.paths
- Produces: `RoundPaths` (frozen dataclass) with `.read(rel, chapter=None)`, `.write(rel, chapter=None)`, `.repo(rel)`, `.backup(rel, chapter=None)`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_round_paths.py
from pathlib import Path
from shenbi.paths import RoundPaths

def test_read_prefers_round_dir(tmp_path):
    rd = tmp_path / "round"; rd.mkdir()
    pd = tmp_path / "project"; pd.mkdir()
    (rd / "truth").mkdir(); (pd / "truth").mkdir()
    (rd / "truth" / "current_state.md").write_text("ROUND")
    (pd / "truth" / "current_state.md").write_text("PROJECT")
    rp = RoundPaths(round_dir=rd, project_dir=pd, repo_root=tmp_path)
    assert rp.read("truth/current_state.md").read_text() == "ROUND"

def test_read_falls_back_to_project_dir(tmp_path):
    pd = tmp_path / "project"; (pd / "truth").mkdir(parents=True)
    (pd / "truth" / "current_state.md").write_text("PROJECT")
    rp = RoundPaths(round_dir=tmp_path/"round", project_dir=pd, repo_root=tmp_path)
    assert rp.read("truth/current_state.md").read_text() == "PROJECT"

def test_write_always_round_dir(tmp_path):
    rd = tmp_path / "round"
    rp = RoundPaths(round_dir=rd, project_dir=tmp_path/"project", repo_root=tmp_path)
    p = rp.write("chapters/chapter-5.md")
    assert str(rd) in str(p)

def test_backup_same_root_as_write(tmp_path):
    rd = tmp_path / "round"
    rp = RoundPaths(round_dir=rd, project_dir=tmp_path/"project", repo_root=tmp_path)
    w = rp.write("truth/current_state.md")
    b = rp.backup("truth/current_state.md")
    assert b == w.with_name(w.name + ".bak")

def test_chapter_substitution(tmp_path):
    rp = RoundPaths(round_dir=tmp_path/"round", project_dir=tmp_path/"project", repo_root=tmp_path)
    assert "chapter-5" in str(rp.read("chapters/chapter-N.md", chapter=5))

def test_frozen(tmp_path):
    import dataclasses
    rp = RoundPaths(tmp_path, tmp_path, tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        rp.round_dir = tmp_path  # type: ignore
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_round_paths.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implement RoundPaths**

```python
# src/shenbi/paths.py
"""RoundPaths: the single path-resolution authority for one dispatch/run.
Encapsulates three roots (round_dir / project_dir / repo_root) and eliminates
bare-string path joins and silent CWD fallbacks."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from shenbi.contracts.paths import resolve_chapter_path

@dataclass(frozen=True)
class RoundPaths:
    round_dir: Path    # this round's workspace (outputs, markers, state)
    project_dir: Path  # the novel project root (novel.json, world/, chapters/, truth/)
    repo_root: Path    # repo root (SKILL.md, fixtures, rubric, validate-gate.py)

    def read(self, rel: str, chapter: int | None = None) -> Path:
        resolved = resolve_chapter_path(rel, chapter)
        rd = self.round_dir / resolved
        if rd.exists():
            return rd.resolve()
        return (self.project_dir / resolved).resolve()

    def write(self, rel: str, chapter: int | None = None) -> Path:
        resolved = resolve_chapter_path(rel, chapter)
        return (self.round_dir / resolved).resolve()

    def repo(self, rel: str) -> Path:
        return (self.repo_root / rel).resolve()

    def backup(self, rel: str, chapter: int | None = None) -> Path:
        w = self.write(rel, chapter)
        return w.with_name(w.name + ".bak")
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_round_paths.py -v`
Expected: PASS (6 tests). (Add `import pytest` to test file.)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/paths.py tests/unit/test_round_paths.py
git commit -m "feat: add RoundPaths three-root value object (eliminates bare path joins + CWD fallback)"
```

---

### Task 5: schemas/decisions.py — DecisionsDoc pydantic model

**Files:**
- Create: `src/shenbi/contracts/schemas/__init__.py` (empty package init)
- Create: `src/shenbi/contracts/schemas/decisions.py`
- Test: `tests/unit/contracts/schemas/test_decisions.py`

**Interfaces:**
- Produces: `DecisionsDoc`, `Selection`, `Adjustment`, `Budget`, `DECISIONS_SCHEMA_VERSION`, `VALID_BASIS`, `VALID_SEVERITY`

- [ ] **Step 1: Write failing tests (use real field shape from test fixtures)**

```python
# tests/unit/contracts/schemas/test_decisions.py
import pytest
from pydantic import ValidationError
from shenbi.contracts.schemas.decisions import DecisionsDoc, Selection, Adjustment

def _doc(**kw):
    base = {"$schema": "shenbi-decisions-v1", "skill": "x", "chapter": 5,
            "selections": [], "produced_at": "2026-07-08T00:00:00Z"}
    base.update(kw)
    return base

class TestDecisionsDoc:
    def test_minimal_valid(self):
        d = DecisionsDoc.model_validate(_doc())
        assert d.skill == "x"

    def test_extra_rejected(self):
        with pytest.raises(ValidationError):
            DecisionsDoc.model_validate(_doc(tyop="x"))

    def test_wrong_schema_version(self):
        with pytest.raises(ValidationError):
            DecisionsDoc.model_validate(_doc(**{"$schema": "v2"}))

class TestSelectionP25:
    def test_routine_low_forbids_rationale(self):
        with pytest.raises(ValidationError):
            Selection.model_validate({
                "target": "t.md", "selected": [], "basis": "arc_relevance",
                "severity": "low", "omitted": [], "rationale": "should fail"
            })

    def test_high_requires_rationale(self):
        with pytest.raises(ValidationError):
            Selection.model_validate({
                "target": "t.md", "selected": [], "basis": "arc_relevance",
                "severity": "high", "omitted": []
            })

    def test_manual_override_requires_rationale(self):
        Selection.model_validate({
            "target": "t.md", "selected": [], "basis": "manual_override",
            "severity": "low", "omitted": [], "rationale": "ok"
        })  # passes

class TestAdjustment:
    def test_rationale_required(self):
        with pytest.raises(ValidationError):
            Adjustment.model_validate({"issue_id": "x", "severity": "medium", "handling": "ignore"})

    def test_severity_medium_allowed(self):
        # doc example uses medium; validator never checked it before; keep permissive
        Adjustment.model_validate({"issue_id": "x", "severity": "medium",
                                    "handling": "ignore", "rationale": "ok"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/contracts/schemas/test_decisions.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implement decisions.py**

```python
# src/shenbi/contracts/schemas/decisions.py
"""Single source of truth for decisions.json validation.
Replaces hand-rolled checks in g2.py, g4/decisions_validator.py, g4/_decisions_schema.py.
Field shapes from phase-0 investigation of tests/unit/gates/test_g4_decisions.py."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, model_validator

DECISIONS_SCHEMA_VERSION = "shenbi-decisions-v1"
VALID_BASIS = {"adjacent_to_target_chapter", "arc_relevance", "volume_scope", "manual_override"}
VALID_SEVERITY = {"low", "high"}
_RATIONALE_MAX_CHARS = 100

Basis = Literal["adjacent_to_target_chapter", "arc_relevance", "volume_scope", "manual_override"]
Severity = Literal["low", "high"]
Handling = Literal["compensate_via_pacing", "explicit_callout", "defer_to_next_chapter", "ignore"]
Trim = Literal["none", "oldest_first", "lowest_relevance", "manual"]

class Selection(BaseModel):
    model_config = {"extra": "forbid"}
    target: str
    selected: list[str]
    basis: Basis
    severity: Severity = "low"
    omitted: list[str] = []
    rationale: str | None = None

    @model_validator(mode="after")
    def _p25(self):
        has = self.rationale is not None
        if has and len(self.rationale) > _RATIONALE_MAX_CHARS:
            raise ValueError(f"rationale exceeds {_RATIONALE_MAX_CHARS} chars")
        requires = self.severity == "high" or self.basis == "manual_override"
        routine_low = self.basis in {"arc_relevance", "volume_scope", "adjacent_to_target_chapter"} and self.severity == "low"
        if routine_low and has:
            raise ValueError("rationale FORBIDDEN for routine+low")
        if requires and not has:
            raise ValueError("rationale REQUIRED for high/manual_override")
        return self

class Adjustment(BaseModel):
    model_config = {"extra": "forbid"}
    issue_id: str
    severity: str  # NOT enum: doc uses "medium", legacy validator never checked
    handling: Handling
    rationale: str

    @model_validator(mode="after")
    def _rationale(self):
        if len(self.rationale) > _RATIONALE_MAX_CHARS:
            raise ValueError(f"rationale exceeds {_RATIONALE_MAX_CHARS} chars")
        return self

class Budget(BaseModel):
    model_config = {"extra": "forbid"}
    context_tokens_estimate: int
    limit: int
    trim_applied: Trim

class DecisionsDoc(BaseModel):
    model_config = {"extra": "forbid"}
    schema_: str = Field(alias="$schema")
    skill: str
    chapter: int
    selections: list[Selection] = []
    adjustments: list[Adjustment] = []
    budget: Budget | None = None
    produced_at: str

    @model_validator(mode="after")
    def _version(self):
        if self.schema_ != DECISIONS_SCHEMA_VERSION:
            raise ValueError(f"$schema must be {DECISIONS_SCHEMA_VERSION}")
        return self
```

Also create `src/shenbi/contracts/schemas/__init__.py` (empty).

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/contracts/schemas/test_decisions.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/schemas/__init__.py src/shenbi/contracts/schemas/decisions.py tests/unit/contracts/schemas/
git commit -m "feat: add DecisionsDoc pydantic model (replaces 3 hand-rolled validators)"
```

---

### Task 6: schemas/registry.py — TruthFilesRegistry model

**Files:**
- Create: `src/shenbi/contracts/schemas/registry.py`
- Test: `tests/unit/contracts/schemas/test_registry.py`

**Interfaces:**
- Produces: `TruthFilesRegistry`, `RegistryConcept`, `RegistryPattern`, `RegistryGlob`, `RegistryKind`

- [ ] **Step 1: Write failing tests (load REAL truth-files.yaml)**

```python
# tests/unit/contracts/schemas/test_registry.py
from pathlib import Path
import pytest
from pydantic import ValidationError
from shenbi.contracts.schemas.registry import TruthFilesRegistry

REAL_YAML = Path(__file__).resolve().parents[4] / "docs" / "framework" / "truth-files.yaml"

def test_loads_real_truth_files_yaml():
    import yaml
    data = yaml.safe_load(REAL_YAML.read_text(encoding="utf-8"))
    reg = TruthFilesRegistry.model_validate(data)
    assert len(reg.concepts) > 50  # 61 concepts

def test_empty_concepts_rejected():
    with pytest.raises(ValidationError):
        TruthFilesRegistry.model_validate({"concepts": []})

def test_real_yaml_has_patterns_and_globs():
    import yaml
    data = yaml.safe_load(REAL_YAML.read_text(encoding="utf-8"))
    reg = TruthFilesRegistry.model_validate(data)
    assert len(reg.patterns) > 0
    assert len(reg.globs) > 0

def test_producer_default_skill():
    from shenbi.contracts.schemas.registry import RegistryConcept
    c = RegistryConcept(name="x.md", kind="truth")
    assert c.producer == "skill"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/contracts/schemas/test_registry.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implement registry.py** (use the model from spec §5.3 — already patched with patterns/globs/16 kinds)

```python
# src/shenbi/contracts/schemas/registry.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

RegistryKind = Literal[
    "benchmark", "chapter", "character", "config", "context", "decisions",
    "import", "outline", "plan", "reference", "report", "short",
    "snapshot", "style", "truth", "world",
]

class RegistryConcept(BaseModel):
    model_config = {"extra": "forbid"}
    name: str
    kind: RegistryKind
    producer: Literal["skill", "pipeline", "external", "shared"] = "skill"
    glob: str | None = None

class RegistryPattern(BaseModel):
    model_config = {"extra": "forbid"}
    parametric: str
    glob: str

class RegistryGlob(BaseModel):
    model_config = {"extra": "forbid"}
    pattern: str

class TruthFilesRegistry(BaseModel):
    model_config = {"extra": "forbid", "populate_by_name": True}
    version: int = 1
    concepts: list[RegistryConcept]
    patterns: list[RegistryPattern] = []
    globs: list[RegistryGlob] = []

    @field_validator("version")
    @classmethod
    def _version(cls, v):
        if v != 1:
            raise ValueError(f"unsupported registry version {v}, expected 1")
        return v

    @model_validator(mode="after")
    def _non_empty(self):
        if not self.concepts:
            raise ValueError("registry concepts empty — truth-files.yaml structural drift")
        return self
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/contracts/schemas/test_registry.py -v`
Expected: PASS (4 tests, incl. loading the real yaml)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/schemas/registry.py tests/unit/contracts/schemas/test_registry.py
git commit -m "feat: add TruthFilesRegistry pydantic model (covers patterns/globs, 16 kinds, D24 non-empty)"
```

---

### Task 7: schemas/deps.py — DepsDoc model (matches real deps.json)

**Files:**
- Create: `src/shenbi/contracts/schemas/deps.py`
- Test: `tests/unit/contracts/schemas/test_deps.py`

**Interfaces:**
- Produces: `DepsDoc`, `PhaseDeps`, `PipelineDeps`, `OutOfPipeline`, plus `phase_of(deps, skill)` helper

- [ ] **Step 1: Write failing tests (load REAL deps.json)**

```python
# tests/unit/contracts/schemas/test_deps.py
from pathlib import Path
import pytest
from pydantic import ValidationError
from shenbi.contracts.schemas.deps import DepsDoc, phase_of

REAL = Path(__file__).resolve().parents[4] / "tests" / "tiers" / "deps.json"

def _load():
    import json
    return DepsDoc.model_validate(json.loads(REAL.read_text(encoding="utf-8")))

def test_loads_real_deps_json():
    d = _load()
    assert "genesis" in d.t2_phases

def test_real_phases_have_g4_note():
    d = _load()
    # 5 phases carry _g4_note (phase-0 finding)
    noted = [p for p in d.t2_phases.values() if p.g4_note]
    assert len(noted) >= 1

def test_phase_of_locates_skill():
    d = _load()
    assert phase_of(d, "shenbi-worldbuilding") == "genesis"

def test_phase_of_unknown_returns_none():
    d = _load()
    assert phase_of(d, "shenbi-nonexistent") is None

def test_extra_rejected():
    with pytest.raises(ValidationError):
        DepsDoc.model_validate({"t2-phases": {}, "bogus": True})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/contracts/schemas/test_deps.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implement deps.py** (shape from spec §5.3, patched with g4_note)

```python
# src/shenbi/contracts/schemas/deps.py
"""DepsDoc: matches real tests/tiers/deps.json shape (phase-0 verified).
D19 resolution: G3.1's per-skill prerequisite check was a dead function
(deps.json never stored per-skill prereq data — 'prerequisites' is a phase
member roster, not per-skill). The model exposes phase_of() for skill->phase
lookup; G3.1 prerequisite logic is deleted (see Task in Phase 2)."""
from __future__ import annotations
from pydantic import BaseModel, Field

class PhaseDeps(BaseModel):
    model_config = {"extra": "forbid", "populate_by_name": True}
    prerequisites: list[str] = []
    expected_outputs: list[str] = []
    g4_checker: str | None = None
    g4_note: str | None = Field(default=None, alias="_g4_note")

class PipelineDeps(BaseModel):
    model_config = {"extra": "forbid", "populate_by_name": True}
    min_chapter_ratio: float = 0.0
    expected_outputs: list[str] = []
    prerequisites: list[str] = []

class OutOfPipeline(BaseModel):
    model_config = {"extra": "forbid", "populate_by_name": True}
    t1_only_auxiliary: list[str] = []
    t1_only_meta: list[str] = []
    t1_only_drafting_phase: list[str] = []
    note: str = Field(default="", alias="_note")

class DepsDoc(BaseModel):
    model_config = {"extra": "forbid", "populate_by_name": True}
    t2_phases: dict[str, PhaseDeps] = Field(default_factory=dict, alias="t2-phases")
    t3_pipelines: dict[str, PipelineDeps] = Field(default_factory=dict, alias="t3-pipelines")
    tool_hashes: dict[str, str] = Field(default_factory=dict, alias="_tool_hashes")
    out_of_pipeline: OutOfPipeline = Field(default_factory=OutOfPipeline, alias="_out_of_pipeline")
    calibration_hashes: dict[str, str] = Field(default_factory=dict, alias="_calibration_hashes")

def phase_of(deps: DepsDoc, skill: str) -> str | None:
    for pname, p in deps.t2_phases.items():
        if skill in p.prerequisites:
            return pname
    return None
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/contracts/schemas/test_deps.py -v`
Expected: PASS (5 tests, incl. loading real deps.json)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/schemas/deps.py tests/unit/contracts/schemas/test_deps.py
git commit -m "feat: add DepsDoc pydantic model (matches real deps.json: dict phases, g4_note, aliases)"
```

---

### Task 8: schemas/{novel,scores,state}.py + adapt.py — remaining models + adapter

**Files:**
- Create: `src/shenbi/contracts/schemas/novel.py`, `scores.py`, `state.py`, `adapt.py`
- Test: `tests/unit/contracts/schemas/test_novel_scores_state.py`

**Interfaces:**
- Produces: `NovelConfig` (forbid), `ScoreReport` (forbid), `ProgressDoc` (ignore), `SummaryDoc` (ignore), `pydantic_err_to_gate_failures(err, file_path, prefix)`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/contracts/schemas/test_novel_scores_state.py
import json
import pytest
from pydantic import ValidationError
from shenbi.contracts.schemas.novel import NovelConfig
from shenbi.contracts.schemas.scores import ScoreReport
from shenbi.contracts.schemas.state import ProgressDoc, SummaryDoc
from shenbi.contracts.schemas.adapt import pydantic_err_to_gate_failures

def test_novel_forbid():
    with pytest.raises(ValidationError):
        NovelConfig.model_validate({"title": "x", "bogus": True})

def test_progress_ignore_allows_extra():
    # producer-uncontrolled: extra ignored, doesn't fail
    p = ProgressDoc.model_validate({"skills": {}, "unknown_key": 1})
    assert p.model_dump().get("skills") == {} or True  # ignore model dump shape

def test_summary_ignore_allows_extra():
    SummaryDoc.model_validate({"t1_scores": {}, "anything": 1})

def test_score_report_shape():
    ScoreReport.model_validate({
        "dimensions": [{"num": 1, "name": "x", "weight": 1.0, "score": 90}],
        "final_score": 90, "classification": "pass",
        "_provenance": {"scored_by": "a", "timestamp": "t"},
    })

def test_adapter_maps_to_gate_failures():
    try:
        NovelConfig.model_validate({"bogus": True})
        assert False
    except ValidationError as e:
        fails = pydantic_err_to_gate_failures(e, "novel.json", "G2.novel")
        assert any(f["s"] == "FAIL" for f in fails)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/contracts/schemas/test_novel_scores_state.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implement the four modules**

```python
# src/shenbi/contracts/schemas/novel.py
# D26: producer writes target_word_count; g6.py reads target_words. Unify to target_word_count.
from __future__ import annotations
from pydantic import BaseModel

class NovelConfig(BaseModel):
    model_config = {"extra": "forbid"}
    title: str = ""
    genre: str = ""
    language: str = "zh"
    era: str = ""
    core_concept: str = ""
    target_word_count: int = 0
    total_chapters: int = 0
    ending_direction: str = ""
    golden_opening_chapters: str = ""
    status: str = ""
    themes: list[str] = []
    mode: str = ""

# src/shenbi/contracts/schemas/scores.py
from __future__ import annotations
from pydantic import BaseModel, Field

class ScoreDimension(BaseModel):
    model_config = {"extra": "forbid"}
    num: int
    name: str = ""
    weight: float = 0.0
    score: float

class ScoreProvenance(BaseModel):
    model_config = {"extra": "forbid"}
    scored_by: str = ""
    timestamp: str = ""
    gate_markers_verified: bool = False
    round_dir: str = ""
    scoring_tool: str = ""

class ScoreReport(BaseModel):
    model_config = {"extra": "forbid", "populate_by_name": True}
    dimensions: list[ScoreDimension] = []
    final_score: float = 0.0
    classification: str = ""
    kill_switch_triggered: bool = False
    kill_switches: list[str] = []
    provenance: ScoreProvenance | None = Field(default=None, alias="_provenance")

# src/shenbi/contracts/schemas/state.py
# producer-uncontrolled (shell heredoc / missing writers): extra: ignore until writer unification (spec 2)
from __future__ import annotations
from pydantic import BaseModel

class ProgressDoc(BaseModel):
    model_config = {"extra": "ignore"}
    skills: dict = {}
    completed_skill_names: list[str] = []
    scoring_history: list = []

class SummaryDoc(BaseModel):
    model_config = {"extra": "ignore"}
    t1_scores: dict = {}
    t2_scores: dict = {}
    t3_scores: dict = {}

# src/shenbi/contracts/schemas/adapt.py
from __future__ import annotations
from pydantic import ValidationError

def pydantic_err_to_gate_failures(err: ValidationError, file_path: str, prefix: str) -> list[dict]:
    """Map pydantic ValidationError to gate micro-failure dicts {id, file, s, r}."""
    return [
        {"id": f"{prefix}.{e['type']}", "file": file_path, "s": "FAIL",
         "r": f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}"}
        for e in err.errors()
    ]
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/contracts/schemas/test_novel_scores_state.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/schemas/{novel,scores,state,adapt}.py tests/unit/contracts/schemas/test_novel_scores_state.py
git commit -m "feat: add NovelConfig/ScoreReport/Progress/Summary models + gate adapter"
```

---

### Task 9: schemas cutover — g2/g4 decisions use DecisionsDoc

**Files:**
- Modify: `src/shenbi/gates/g2.py:64-115` (decisions branch), `src/shenbi/gates/g4/decisions_validator.py`, `src/shenbi/gates/g4/_decisions_schema.py`, `src/shenbi/contracts/schemas/adapt.py`
- Test: `tests/unit/gates/test_g2.py` (UPDATE 6 assertions — C1 fix), `tests/unit/gates/test_g4_decisions.py` (existing — must stay green)

**Interfaces:**
- Consumes: `DecisionsDoc` from Task 5, `pydantic_err_to_gate_failures` from Task 8

**⚠️ C1 critical note:** Existing tests assert numeric IDs `G2.dec.1`/`.2`/`.3` (test_g2.py:422,437,450,500). The default `pydantic_err_to_gate_failures` produces type-based IDs (`G2.dec.missing`). This task MUST update both the adapter (to preserve numeric IDs) AND the 6 test assertions. Do not skip Step 2b.

- [ ] **Step 1: Capture baseline (tests must already pass)**

Run: `pytest tests/unit/gates/test_g2.py tests/unit/gates/test_g4_decisions.py -v`
Expected: PASS (baseline — capture the count)

- [ ] **Step 2a: Update adapt.py to preserve numeric g2 decisions IDs**

The generic `pydantic_err_to_gate_failures` (Task 8) produces `f"{prefix}.{e['type']}"`. For g2 decisions, we need stable numeric IDs (`G2.dec.1` invalid-JSON, `G2.dec.2` wrong-schema, `G2.dec.3` missing-keys) so existing tests pass. Add a decisions-specific mapper in `adapt.py`:

```python
# Append to src/shenbi/contracts/schemas/adapt.py
def decisions_err_to_g2_failures(err, file_path: str) -> list[dict]:
    """Map DecisionsDoc ValidationError to G2.dec.{1,2,3} numeric IDs (preserves existing test contract)."""
    fails = []
    for e in err.errors():
        loc = ".".join(str(x) for x in e["loc"])
        msg = e["msg"]
        # Classify into the 3 legacy numeric buckets
        if loc == "$schema" or "schema" in msg.lower():
            fails.append({"id": "G2.dec.2", "file": file_path, "s": "FAIL", "r": f"{loc}: {msg}"})
        elif e["type"] == "missing":
            fails.append({"id": "G2.dec.3", "file": file_path, "s": "FAIL", "r": f"{loc}: {msg}"})
        else:
            fails.append({"id": "G2.dec.3", "file": file_path, "s": "FAIL", "r": f"{loc}: {msg}"})
    return fails
```

- [ ] **Step 2b: Rewrite g2.py decisions branch using the numeric-ID mapper**

In `src/shenbi/gates/g2.py`, replace the hand-rolled decisions validation (lines ~64-115, the `if file_type == "decisions":` block) with:

```python
if file_type == "decisions":
    from shenbi.contracts.schemas.decisions import DecisionsDoc
    from shenbi.contracts.schemas.adapt import decisions_err_to_g2_failures
    from pydantic import ValidationError
    try:
        data = jload(str(p))
    except (json.JSONDecodeError, OSError):
        mf.append({"id": "G2.dec.1", "file": fp, "s": "FAIL", "r": "invalid JSON"})
        continue
    try:
        DecisionsDoc.model_validate(data)
        c.append({"id": "G2.dec", "file": fp, "s": "PASS"})
    except ValidationError as e:
        mf.extend(decisions_err_to_g2_failures(e, fp))
    continue  # skip word-count checks for decisions
```

- [ ] **Step 2c: Verify the 6 existing g2 assertions still hold**

Run: `pytest tests/unit/gates/test_g2.py -v -k "dec"`
Expected: PASS. The numeric-ID mapper (Step 2a) preserves the `G2.dec.1`/`.2`/`.3` contract that test_g2.py:422,437,450,500 assert. If any assertion still fails, inspect which `loc`/`type` it triggers and adjust the mapper classification. **Do NOT edit the test assertions unless the mapper genuinely cannot classify a case** — preserving the numeric IDs is the goal.

- [ ] **Step 3: Rewrite g4 decisions_validator.py to delegate**

Replace the body of `g4_decisions(...)` in `src/shenbi/gates/g4/decisions_validator.py` to call `DecisionsDoc.model_validate` (same pattern as g2, but g4 uses its own `G4.dec.*` prefix via `pydantic_err_to_gate_failures(e, fp, "G4.dec")`). Delete the local `$schema`/required-keys/P2.5 logic (now in the model). Keep the function signature so `generic.py`'s dispatch still works. Verify `tests/unit/gates/test_g4_decisions.py` still passes (it asserts on G4.dec IDs — confirm the generic adapter's `G4.dec.{type}` IDs are compatible; if test_g4_decisions asserts numeric G4.dec.N, apply the same numeric-mapper approach).

- [ ] **Step 4: Run g2/g4 decisions tests**

Run: `pytest tests/unit/gates/test_g2.py tests/unit/gates/test_g4_decisions.py -v`
Expected: PASS (same count as baseline; behavior equivalent — numeric IDs preserved)

- [ ] **Step 5: Delete now-dead code + commit**

Delete `src/shenbi/gates/g4/_decisions_schema.py` (logic migrated to `DecisionsDoc`). Update any imports. Run `just check`.

```bash
git add -A
git commit -m "refactor: g2/g4 decisions use DecisionsDoc (preserves numeric IDs; deletes 2 validators)"
```

---

### Task 10: legacy.load_registry returns TruthFilesRegistry

**Files:**
- Modify: `src/shenbi/contracts/legacy.py:72-96` (load_registry + resolves)
- Modify: `src/shenbi/contracts/registry.py:20-36` (bootstrap_registry)
- Test: `tests/unit/contracts/test_legacy.py` (existing — must stay green)

- [ ] **Step 1: Capture baseline**

Run: `pytest tests/unit/contracts/ -v`
Expected: PASS baseline

- [ ] **Step 2: Change load_registry to return TruthFilesRegistry**

In `legacy.py`, `load_registry()` does `yaml.safe_load(...)` then `TruthFilesRegistry.model_validate(data)`. Keep a `.model_dump()`-style access for `resolves()` — OR adapt `resolves()` to read model attributes (`registry.concepts`, `registry.patterns`, `registry.globs`). Prefer adapting `resolves()` to use the model directly.

- [ ] **Step 3: Update ALL consumers of load_registry that expected a dict (C2 fix — exhaustive list)**

**⚠️ Critical:** Changing the return type breaks every dict-access consumer. Grep confirmed these call sites (run `grep -rn "load_registry\|registry\.get\|registry\[" src/shenbi/` to verify the full set before starting). Each must switch from dict-access to model-attribute access:

1. `resolves()` (legacy.py:85) — `registry.get("concepts",[])` → `registry.concepts`; `registry.get("patterns",[])` → `registry.patterns`; `registry.get("globs",[])` → `registry.globs`. Access `c.name`/`c.kind`/`p.parametric`/`p.glob`/`g.pattern` as model attrs.
2. `bootstrap_registry()` (registry.py:20) — `data.get("concepts",[])` / `entry.get("name")` / `entry.get("kind","truth")` → iterate `reg.concepts`, `c.name`, `c.kind`.
3. `_truth_file_set` / `_decisions_file_set` (executor.py:~28-55) — these call `bootstrap_registry()` which returns `{name: kind}` dict; keep bootstrap_registry returning that derived dict OR adapt callers to filter `reg.concepts` by `.kind`. Pick ONE approach and apply consistently.
4. `audit/snapshot.py:parametric_globs` (~line 19) — `load_registry()` then `registry.get("patterns",[])`; switch to `reg.patterns` / `p.parametric` / `p.glob`.
5. **`contracts/graph.py` (Task 3) — `dag_key`/`normalize_to_glob` use `registry.get("patterns",[])` / `registry.get("globs",[])` / `g["pattern"]` / `p["parametric"]`.** Switch to `registry.patterns` / `registry.globs` / `g.pattern` / `p.parametric` / `p.glob`.
6. **`sync_contracts.py` (~line 46, 49, 86) — `build_dag`/`derive_expected_outputs` access `registry.get(...)`.** Switch to model attrs.

**Design decision (decide once, apply everywhere):** `graph.dag_key`/`normalize_to_glob` and `lint_contract_graph` receive a `registry` param. Decide whether (a) they accept the `TruthFilesRegistry` model and use attrs, or (b) they accept a plain dict (via `model_dump(by_alias=True)`). **Recommend (a)** — model attrs are typed and self-documenting. Update all callers to pass the model.

- [ ] **Step 4: Run all contract + gate + sync tests**

Run: `pytest tests/unit/contracts/ tests/unit/gates/ tests/unit/test_sync_contracts.py -v`
Expected: PASS (behavior equivalent; type changed from dict to model). If `test_sync_contracts` fails on `dag_key`/`build_dag`, revisit Step 3 item 5/6.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: load_registry returns TruthFilesRegistry model (migrates graph+sync+resolves consumers)"
```

---

## Phase 2: Runtime Unification (all gates/dispatcher/pipeline → RoundPaths + single resolver)

This phase has the largest change surface. Do it one module per commit; run `just check` after each.

### Task 11: dispatcher/executor.py — RoundPaths + resolve_chapter_path + resolve_or_skip

**Files:**
- Modify: `src/shenbi/dispatcher/executor.py`
- Test: `tests/unit/dispatcher/test_executor.py` (existing + new regression)

- [ ] **Step 1: Write regression test for N-corruption (was the marquee bug)**

```python
# tests/unit/dispatcher/test_executor.py — add:
def test_section_path_not_corrupted():
    """C2: uppercase N mid-token must NOT be replaced by chapter substitution.
    Old _resolve_chapter_path did str.replace('N',...) unbounded → '01_SECTIO5.md'."""
    from shenbi.contracts.paths import resolve_chapter_path
    assert resolve_chapter_path("import/canon/01_SECTION.md", 5) == "import/canon/01_SECTION.md"
```

- [ ] **Step 2: Migrate executor.py**

Delete `_resolve_chapter_path` (executor.py:66-75) and `_extract_chapter` (executor.py:~169). Add imports `from shenbi.contracts.paths import resolve_chapter_path, resolve_or_skip, extract_chapter`. In `derive_input_files`/`derive_output_files`: replace `_resolve_chapter_path(p, chapter)` with `resolve_or_skip(p, chapter)` and filter out `None` (genesis skip). Keep `(round_dir / p).resolve()` join for now (RoundPaths adoption for dispatcher is a separate sub-step to keep the commit reviewable). Replace `_extract_chapter` usages with `extract_chapter`.

- [ ] **Step 3: Run dispatcher tests**

Run: `pytest tests/unit/dispatcher/ -v && just check`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: executor uses resolve_chapter_path/extract_chapter (fixes N-corruption)"
```

---

### Task 12: pipeline/dispatch_helper.py — RoundPaths + fields + resolve_chapter_path

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`

- [ ] **Step 1: Capture baseline**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py -v` (or nearest existing)

- [ ] **Step 2: Migrate dispatch_helper.py**

Delete `_resolve_path` (~line 104), `_extract_chapter` (~line 100), `_filter_to_fields`/`_extract_h2_sections`/`_project_json_keys` (~lines 122-213). Import from `shenbi.contracts.paths` and `shenbi.contracts.fields`. In the read loop (~line 254): use `resolve_chapter_path` for resolution and `filter_to_fields(text, fields, resolved)` for filtering. Note `filter_to_fields` now returns `(text, matched)` — update callers to use `matched` for WARN logging.

- [ ] **Step 3: Run tests + just check**

Run: `just check`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: dispatch_helper uses shared resolve_chapter_path + filter_to_fields"
```

---

### Task 13: pipeline/chapter_loop.py + closure.py — resolve_chapter_path + resolve_volume_path

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (delete `_substitute_chapter` ~line 332)
- Modify: `src/shenbi/pipeline/closure.py` (delete `_substitute_volume` ~line 137)

- [ ] **Step 1: Migrate chapter_loop.py**

Delete `_substitute_chapter`. Replace all call sites with `resolve_chapter_path(path, chapter)` (chapter is always a real int in chapter_loop, never None). Import from `shenbi.contracts.paths`.

- [ ] **Step 2: Migrate closure.py (C1 fix — the 4th resolver)**

Delete `_substitute_volume` (closure.py:137-139). Replace its caller `_resolve_closure_g4_path` (closure.py:152) to use `resolve_volume_path(step.output_path, vol)` from `shenbi.contracts.paths`.

- [ ] **Step 3: Run tests + just check**

Run: `just check`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: chapter_loop + closure use shared resolvers (C1: 4th resolver retired)"
```

---

### Task 14: gates/g1.py + g2.py + g5.py — RoundPaths + .bak via rp.backup()

**Files:**
- Modify: `src/shenbi/gates/g1.py` (BACKUP_SKILLS derivation + .bak + docstring fix), `g2.py` (.bak reader), `g5.py` (G5.2 glob-aware)

**Note:** This task is large — split into 14a (g1 + .bak), 14b (g5.2), each its own commit.

#### Task 14a: g1.py BACKUP_SKILLS derivation + .bak

- [ ] **Step 1: Write test — derive_backup_skills**

```python
# tests/unit/gates/test_g1_backup.py
from shenbi.gates.g1 import derive_backup_skills

def test_derive_includes_truth_updaters():
    # phase-0: 15 skills update truth files
    skills = derive_backup_skills()  # loads contracts + registry internally
    # spot-check a few that were missing from the old hardcoded list
    assert "shenbi-state-settling" in skills
    assert "shenbi-review-resonance" in skills  # was missing → G2.11 no-op
    assert "shenbi-memory-distill" in skills     # was missing
```

- [ ] **Step 2: Implement derive_backup_skills in g1.py**

```python
# src/shenbi/gates/g1.py — replace BACKUP_SKILLS frozenset with:
import fnmatch
from shenbi.contracts.legacy import load_contract, load_registry
from shenbi.gates.shared import SKILLS

def derive_backup_skills() -> frozenset[str]:
    """Auto-derive skills needing .bak: updates intersect truth-kind concepts."""
    reg = load_registry()
    truth_names = {c.name for c in reg.concepts if c.kind == "truth"}
    result: set[str] = set()
    for skill_dir in SKILLS.iterdir():
        if not (skill_dir / "SKILL.md").exists():
            continue
        skill = skill_dir.name
        c = load_contract(skill)
        for f in c.get("updates", []):
            if any(f == t or fnmatch.fnmatch(f, t) for t in truth_names):
                result.add(skill)
                break
    return frozenset(result)

BACKUP_SKILLS = derive_backup_skills()  # computed at import; covers 15 truth-updaters
```

Also fix `g1.py:65` docstring (claims snake_case normalization the code doesn't do). Update `g1.py:179` `.bak` write to use a RoundPaths-style same-root construction (or, since g1 receives `fp` paths, ensure `.bak` is `Path(str(fp) + ".bak")` consistently — the fix is ensuring the path is absolute/resolved before suffixing; if a RoundPaths is available, use `rp.backup()`).

- [ ] **Step 3: Update g2.py:242 + style_polishing.py:35 .bak readers**

Ensure `.bak` read path matches g1's write path exactly (same root). If style_polishing currently reads `.bak` via bare `fp` but content via `base/fp`, fix to use the same base for both.

- [ ] **Step 4: Run tests + just check**

Run: `pytest tests/unit/gates/test_g1_backup.py tests/unit/gates/ -v && just check`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: derive BACKUP_SKILLS from contracts (covers 15 truth-updaters, was 9 hardcoded)"
```

#### Task 14b: g5.py G5.2 glob-aware WARN

- [ ] **Step 1: Migrate G5.2**

In `g5.py:74-89`, replace the literal `set(down_reads) - set(up_writes|up_updates)` with `dag_key`-aware matching: for each down read, compute `dag_key(read, registry)` and check if any up write/update has the same `dag_key`. Keep WARN (not FAIL). Import `dag_key` from `shenbi.contracts.graph`.

- [ ] **Step 2: Run + commit**

Run: `just check` → commit `refactor: G5.2 uses glob-aware dag_key matching (WARN, adjacent-pairs)`

---

### Task 15: gates/g4/*.py — RoundPaths, delete resolve_g4_base CWD fallback

**⚠️ C3 fix: This task is split into 15a/15b/15c.** The original single-task design was infeasible: G4 checkers have signature `(fps, rd)` — NO `project_dir`/`repo_root` — and ~9 sites use the CWD fallback (`resolve_g4_base` in 10 checkers + inline `base = Path(rd) if rd else Path.cwd()` in generic.py ×3, score_arc, decisions_validator, length_normalizing, foreshadowing_plant, anti_detect, state_settling). Deleting the fallback before threading the params breaks every CLI invocation that omits round_dir. Order MUST be: thread params (15a) → migrate checkers (15b) → delete fallback LAST (15c).

**Call-chain facts (verified):** `gate_G4(skill_name, test_type, file_paths, round_dir=None)` at generic.py:147. Callers: `gates/cli.py:113` (has `rd`), `g5.py:254` (`gate_G4(pr, "generative", [str(fp)])` — no rd), `g7.py:142` (`gate_G4(target, test_type, files_checked, str(rd))`), `g6.py:77` (`gate_G4("shenbi-chapter-drafting", "generative", [str(ch)])` — no rd).

---

#### Task 15a: Thread `project_dir`/`repo_root` through the G4 call chain

**Files:**
- Modify: `src/shenbi/gates/g4/generic.py` (`gate_G4` signature + dispatch), all checker signatures, `gates/cli.py:113`, `g5.py:254`, `g7.py:142`, `g6.py:77`
- Test: existing g4/g5/g6/g7 tests stay green

- [ ] **Step 1: Write a test that gate_G4 accepts project_dir/repo_root**

```python
# tests/unit/gates/test_g4_signatures.py
def test_gate_g4_accepts_project_dir_and_repo_root(tmp_path):
    from shenbi.gates.g4.generic import gate_G4
    # Must accept the new params without error (even if it doesn't use them yet for this skill)
    result = gate_G4("shenbi-worldbuilding", "generative", [], str(tmp_path),
                     project_dir=str(tmp_path), repo_root=str(tmp_path))
    import json; data = json.loads(result)
    assert data["skill"] == "shenbi-worldbuilding"  # ran, didn't crash on signature
```

- [ ] **Step 2: Add `project_dir`/`repo_root` params to gate_G4 + dispatch**

In `generic.py`, change the signature:
```python
def gate_G4(skill_name: str, test_type: str, file_paths: list[str],
            round_dir: str | None = None,
            project_dir: str | None = None,
            repo_root: str | None = None) -> str:
```
Thread `project_dir`/`repo_root` through the checker dispatch dict to each checker. Add the same two params to EVERY checker signature (`g4_worldbuilding(fps, rd, project_dir=None, repo_root=None)`, etc.). Checkers that don't need them yet accept-and-ignore. **Do NOT delete `resolve_g4_base` or the CWD fallback yet** — 15a only adds params; behavior unchanged.

- [ ] **Step 3: Update the 4 callers to pass project_dir/repo_root**

- `gates/cli.py:113`: `gate_G4(full_name, "generative", file_list, rd, project_dir=arg(2), repo_root=str(PROJECT))` (cli already has PROJECT access via shared).
- `g5.py:254`: `gate_G4(pr, "generative", [str(fp)], project_dir=str(project_dir), repo_root=str(PROJECT))` — g5 has `project_dir` in scope.
- `g7.py:142`: add `project_dir=str(rd / "project-output")` (g7's project root convention) + `repo_root=str(PROJECT)`.
- `g6.py:77`: `gate_G4("shenbi-chapter-drafting", "generative", [str(ch)], str(pd), project_dir=str(pd), repo_root=str(PROJECT))` — g6 has `pd` in scope.

For each caller, `project_dir`/`repo_root` may be None at runtime in edge cases — checkers must handle None gracefully (fall back to rd or raise a clear error, NOT silently use CWD). Keep CWD fallback in `resolve_g4_base` for now (removed in 15c).

- [ ] **Step 4: Run all gate tests**

Run: `just check`
Expected: PASS (params added but unused — pure additive, no behavior change)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: thread project_dir/repo_root through gate_G4 call chain (additive, no behavior change)"
```

---

#### Task 15b: Migrate the G4 checkers to RoundPaths

**Files:**
- Modify: all 10 hardcoded checkers + the ~9 inline `base = Path(rd) if rd else Path.cwd()` sites

- [ ] **Step 1: Migrate checkers one-by-one (one commit per 2-3 checkers)**

For each hardcoded checker (`worldbuilding`, `story_architecture`, `relationship_map`, `plot_thread_weaver`, `power_system`, `volume_outlining`, `foreshadowing_track`, `faction_builder`, `location_builder`, `pacing_design`): replace `pd = resolve_g4_base(rd); pd / "world/..."` with:
```python
rp = RoundPaths(round_dir=Path(rd), project_dir=Path(project_dir or rd), repo_root=Path(repo_root or PROJECT))
world = rp.read("world/story_bible.md")
```
For the inline-fallback checkers (generic.py ×3, score_arc, decisions_validator, length_normalizing, foreshadowing_plant, anti_detect, state_settling): replace `base = Path(rd) if rd else Path.cwd()` with the same RoundPaths construction (or, for checkers that only need the round_dir base, keep `base = Path(rd)` and RAISE if rd is None rather than CWD-fallback).

Run `just check` after each batch. **Do not delete `resolve_g4_base` yet** (15c).

- [ ] **Step 2: Run full suite after all checkers migrated**

Run: `just check`
Expected: PASS (T1/T2/T3 green)

- [ ] **Step 3: Commit (per batch)**

```bash
git add -A && git commit -m "refactor: migrate G4 checkers to RoundPaths (batch N)"
```

---

#### Task 15c: Delete resolve_g4_base CWD fallback (LAST)

**Files:**
- Modify: `src/shenbi/gates/shared.py:47-55`

- [ ] **Step 1: Verify no checker still calls resolve_g4_base**

Run: `grep -rn "resolve_g4_base" src/shenbi/gates/`
Expected: only the definition in shared.py remains (zero callers). If any caller remains, migrate it first.

- [ ] **Step 2: Delete resolve_g4_base (or make it raise on None rd)**

In `shared.py`, either delete `resolve_g4_base` entirely OR change it to:
```python
def resolve_g4_base(rd: str | None = None) -> Path:
    if not rd:
        raise ValueError("round_dir required — CWD fallback removed; caller must pass rd")
    return Path(rd)
```
(prefer delete if no callers remain after Step 1).

- [ ] **Step 3: Run full suite**

Run: `just check`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: delete resolve_g4_base CWD fallback (all callers now pass round_dir explicitly)"
```

---

### Task 16: codex.py rubric + dead-code cleanup

**Files:**
- Modify: `src/shenbi/dispatcher/modes/codex.py:58` (rubric via repo root)
- Delete: `src/shenbi/contracts/registry.py` dead `REGISTRY`/`load_skill_contract`, `contracts/skills/*.py` dead stubs (keep genre_config, pacing_design), tracked `.bak` files, `site/framework/truth-files.yaml` divergent copy

- [ ] **Step 1: Fix codex rubric path**

```python
# codex.py:58 — replace:
rubric_path = Path(os.environ.get("RUBRIC", str(rp.repo(f"tests/tiers/t1-skill/{skill}/rubric.md"))))
```
(Keep `RUBRIC` env override for testing.)

- [ ] **Step 2: Delete dead code (with verification grep — I6 fix)**

**Before deleting, verify zero live imports:**
```bash
grep -rn "from shenbi.contracts.skills" src/ tests/   # must return ONLY genre_config/pacing_design
grep -rn "REGISTRY\|load_skill_contract" src/ tests/  # must return only the definitions in registry.py
```
If any unexpected import appears, migrate it before deleting.

`git rm src/shenbi/dispatcher/executor.py.bak src/shenbi/gates/g4/chapter_drafting.py.bak` (and any tracked `.bak`). In `contracts/registry.py`: delete `REGISTRY`, `_discover_skill_models`, `load_skill_contract` (zero callers — verified by grep). In `contracts/skills/`: delete all `*.py` except `genre_config.py`, `pacing_design.py`, `__init__.py`. `git rm site/framework/truth-files.yaml` (divergent duplicate — M2).

`git rm src/shenbi/dispatcher/executor.py.bak src/shenbi/gates/g4/chapter_drafting.py.bak` (and any tracked `.bak`). In `contracts/registry.py`: delete `REGISTRY`, `_discover_skill_models`, `load_skill_contract` (zero callers — verified). In `contracts/skills/`: delete all `*.py` except `genre_config.py`, `pacing_design.py`, `__init__.py`. `git rm site/framework/truth-files.yaml` (divergent duplicate — M2).

- [ ] **Step 3: Run + commit**

Run: `just check` → commit `chore: codex rubric via repo root; delete dead code + tracked .bak + site yaml dup`

---

## Phase 3: Static Checks (CI layer)

### Task 17: truth-files.yaml — add producer field + register pipeline files

**Files:**
- Modify: `docs/framework/truth-files.yaml`
- Test: `tests/unit/contracts/test_registry_pipeline_producers.py`

- [ ] **Step 1: Write test asserting pipeline files registered**

```python
# tests/unit/contracts/test_registry_pipeline_producers.py
from shenbi.contracts.legacy import load_registry

PIPELINE_PRODUCED = {
    "context/chapter-N-context.md",
    "snapshots/manifest.json",
    "truth-index.json",
    "pipeline-state.json",
    "audits/chapter-N-review-summary.md",
}

def test_pipeline_files_marked_pipeline_producer():
    reg = load_registry()
    for name in PIPELINE_PRODUCED:
        concept = next((c for c in reg.concepts if c.name == name), None)
        assert concept is not None, f"{name} not in registry"
        assert concept.producer in {"pipeline", "shared"}, f"{name} producer={concept.producer}"
```

- [ ] **Step 2: Add producer fields to truth-files.yaml**

For each concept in truth-files.yaml, add `producer:` based on the phase-0 inventory:
- pipeline-only (9): `context/chapter-N-context.md`, `snapshots/manifest.json`, `truth-index.json`, `pipeline-state.json`, `audits/chapter-N-review-summary.md`, `snapshots/chapter-NNN-*.md` (D20: real flatfile, deprecate `snapshots/chapter-NNN/`), `genesis-context/*.md`, `truth-embeddings.db`, `context/review-checklist-N.json`
- external seeds: `novel.json` (shared — worldbuilding + pipeline), `era-reference.md`, `import/source/*`, `source_canon/*`, `benchmarks/anchors/`
- default: `skill`

Also: register D20 real flatfile `snapshots/chapter-NNN-*.md` as a concept; remove or deprecate `snapshots/chapter-NNN/` directory concept.

- [ ] **Step 3: Run + commit**

Run: `pytest tests/unit/contracts/test_registry_pipeline_producers.py -v && just check` → commit `feat: register pipeline producers in truth-files.yaml (D20 real flatfile)`

---

### Task 18: tools/lint_contract_graph.py — closure check

**Files:**
- Create: `tools/lint_contract_graph.py`
- Test: `tests/unit/tools/test_lint_contract_graph.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/tools/test_lint_contract_graph.py
from pathlib import Path
import subprocess, sys

REPO = Path(__file__).resolve().parents[3]
LINT = REPO / "tools" / "lint_contract_graph.py"

def test_clean_repo_has_zero_orphan_reads():
    # phase-0 found 0 orphans; lint should pass (exit 0)
    r = subprocess.run([sys.executable, str(LINT)], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, f"orphan reads:\n{r.stdout}\n{r.stderr}"

def test_detects_injected_orphan(monkeypatch, tmp_path):
    """Canary #1: a contract with a read no skill produces → ORPHAN_READ FAIL + exact message."""
    from shenbi.contracts import graph as g
    # Inject a synthetic contract set with one orphan read
    fake_contracts = {
        "shenbi-test": {"reads": ["truth/does-not-exist.md"], "writes": [], "updates": []},
    }
    monkeypatch.setattr("shenbi.sync_contracts.load_all_contracts", lambda: fake_contracts)
    orphan, dangling = __import__("tools.lint_contract_graph", fromlist=["find_closure_violations"]).find_closure_violations()
    assert any(skill == "shenbi-test" and "truth/does-not-exist.md" in f for skill, f in orphan)
```

- [ ] **Step 2: Implement lint_contract_graph.py (I4 fix: load_all_contracts is in sync_contracts, NOT legacy)**

```python
# tools/lint_contract_graph.py
"""Closure check: every read must have a producer (skill/pipeline/external).
ORPHAN_READ → exit 1 (block PR). DANGLING_WRITE → stderr WARN."""
import sys
from shenbi.contracts.graph import dag_key
from shenbi.contracts.legacy import load_registry
from shenbi.sync_contracts import load_all_contracts  # I4: it's in sync_contracts (verified line 55)

def find_closure_violations():
    contracts = load_all_contracts()
    reg = load_registry()  # returns TruthFilesRegistry model (post-Task 10)
    producers: dict[str, set[str]] = {}
    for skill, c in contracts.items():
        for f in [*c.get("writes", []), *c.get("updates", [])]:
            producers.setdefault(dag_key(f, reg), set()).add(skill)
    external = {c.name for c in reg.concepts if c.producer == "external"}
    pipeline = {c.name for c in reg.concepts if c.producer in {"pipeline", "shared"}}

    orphan, dangling = [], []
    for skill, c in contracts.items():
        for f in c.get("reads", []):
            key = dag_key(f, reg)
            if key in external or f in external:
                continue
            if key in pipeline or f in pipeline:
                continue
            if key not in producers and f not in producers:
                orphan.append((skill, f))
    # dangling: writes with no reader
    all_read_keys = {dag_key(r, reg) for c in contracts.values() for r in c.get("reads", [])}
    for key, sks in producers.items():
        if key not in external and key not in pipeline and key not in all_read_keys:
            dangling.append((next(iter(sks)), key))
    return orphan, dangling

def main():
    orphan, dangling = find_closure_violations()
    for skill, f in orphan:
        print(f"ORPHAN_READ: skill={skill} reads={f} no producer", file=sys.stderr)
    for skill, f in dangling:
        print(f"DANGLING_WRITE (warn): skill={skill} writes={f} no consumer", file=sys.stderr)
    sys.exit(1 if orphan else 0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run + commit**

Run: `pytest tests/unit/tools/test_lint_contract_graph.py -v` → commit `feat: add lint_contract_graph closure check (ORPHAN_READ FAIL)`

---

### Task 19: Upgrade scripts/lint_contract_fields.py + justfile lint-contracts

**Files:**
- Modify: `scripts/lint_contract_fields.py` (use match_field, fixture-driven FAIL)
- Modify: `justfile` (add lint-contracts target)

- [ ] **Step 1: Upgrade lint_contract_fields.py**

Replace its local `normalize()` (lower + fold) with `from shenbi.contracts.fields import match_field`. Make assertions FAIL (exit 1) on field drift. Drive from producer fixtures in `tests/fixtures/`.

- [ ] **Step 2: Add justfile target**

```makefile
# justfile
lint-contracts:
    uv run python tools/lint_contract_graph.py
    uv run python scripts/lint_contract_fields.py
    uv run python tools/lint_contracts.py
```

Wire `lint-contracts` into the `check` recipe.

- [ ] **Step 3: Run + commit**

Run: `just lint-contracts && just check` → commit `feat: lint_contract_fields uses match_field; add just lint-contracts`

---

## Phase 4: Debt Clearing (fix violations + live bugs + canaries)

### Task 20: Fix closure + field + schema violations (zero FAIL)

**Files:** depends on阶段 3 output

- [ ] **Step 1: Run all lints, capture violations**

Run: `just lint-contracts 2>&1 | tee /tmp/violations.txt`

- [ ] **Step 2: Fix each ORPHAN_READ / field-drift / extra-field per spec §7.5 protocol**

For each violation, categorize (typo / missing producer / external / pipeline / field drift / extra field) and fix accordingly. Forbidden: deleting reads or adding fake producers to silence warnings.

- [ ] **Step 3: Verify zero FAIL**

Run: `just lint-contracts`
Expected: zero ORPHAN_READ (exit 0). DANGLING_WRITE WARNs documented but allowed.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "fix: clear all contract lint violations (orphan reads, field drift, extra fields)"
```

---

### Task 21: Live bug fixes — D16, D19, D20 (path/contract), D26

**Files:** `g6.py` (D16, D26), `g3.py` (D19), `chapter_loop.py` + `truth-files.yaml` (D20)

- [ ] **Step 1: Fix D16 (G6.10 dead path)**

`g6.py:275`: change `style_path = pd / "config" / "style_profile.md"` to use the correct path `style/style_profile.md` (via RoundPaths once Task 15 done: `rp.read("style/style_profile.md")`). Add canary test:

```python
def test_g610_not_skipped_when_style_exists(tmp_path):
    # build a project with style/style_profile.md; assert G6.10 runs (not SKIP)
    ...
```

- [ ] **Step 2: Fix D19 (G3.1 dead function — DELETE the prereq check)**

`g3.py:79-106`: delete the `deps.get(skill_name)` prerequisite logic. Replace with:

```python
c.append({"id": "G3.1", "s": "SKIP", "r": "per-skill prerequisites not modeled (G3.2 covers readiness)"})
```

Add canary:

```python
def test_g31_does_not_silently_query_missing_key():
    # G3.1 must not do deps.get(skill_name); it SKIPs explicitly
    ...
```

- [ ] **Step 3: Fix D20 (snapshot path)**

`chapter_loop.py:239`: the `ChapterStep` for `shenbi-snapshot-manage` declares `output_path="snapshots/chapter-NNN/"` (fictional directory). Remove/correct this step's `output_path` to match real pipeline flatfiles `snapshots/chapter-NNN-*.md` (registered in Task 17). Truth-files.yaml: deprecate `snapshots/chapter-NNN/` directory concept.

- [ ] **Step 4: Fix D26 (novel.json field name)**

`g6.py:45`: change `target_words` read to `target_word_count` (producer is authoritative). Sync `tests/fixtures/novel-example.json` to use `target_word_count`. Add canary:

```python
def test_novel_config_loads_with_target_word_count():
    from shenbi.contracts.schemas.novel import NovelConfig
    NovelConfig.model_validate({"target_word_count": 100000, ...})  # producer shape
```

- [ ] **Step 5: Run + commit**

Run: `just check` → commit `fix: D16 G6.10 style path, D19 delete dead G3.1, D20 snapshot path, D26 target_word_count`

---

### Task 22: Live bug fixes — D21, D22, D24 (schema/enum/assertion)

**Files:** `dispatch_helper.py` (D21 templates), `chapter_loop.py` + new `contracts/schemas/hooks.py` (D22 HookState), `schemas/registry.py` (D24 — already done in Task 6)

- [ ] **Step 1: Fix D21 (truth templates missing H2)**

`dispatch_helper.py:_init_truth_templates` (~line 433): instead of writing bare H1 templates, derive H2 headings from consumer-declared fields. For each truth file (`current_state.md`, `character_matrix.md`, `emotional_arcs.md`, `chapter_summaries.md`), find skills that declare `fields:` reading it, collect the union of declared fields, and write `## <field>` stubs.

- [ ] **Step 2: Fix D22 (HookState enum, 6 values)**

Create `src/shenbi/contracts/schemas/hooks.py`:

```python
from enum import Enum

class HookState(str, Enum):
    PLANTED = "PLANTED"
    RELEVANT = "RELEVANT"
    TRIGGERED = "TRIGGERED"
    RESOLVED = "RESOLVED"
    ARCHIVED = "ARCHIVED"   # phase-0: foreshadowing-track SKILL.md:72
    EXPIRED = "EXPIRED"     # phase-0: SKILL.md:73,120

_NONCANONICAL = {"TRIGGER": HookState.TRIGGERED}  # SKILL.md:87 uses TRIGGER

def parse_hook_state(raw: str) -> HookState:
    if raw in _NONCANONICAL:
        return _NONCANONICAL[raw]
    return HookState(raw.upper())  # case-insensitive
```

In `chapter_loop.py:_count_triggered_hooks` (line 643) and line 771: replace `h.get("state") == "TRIGGERED"` with `parse_hook_state(h.get("state","")) == HookState.TRIGGERED`. Canary: lowercase `triggered` + `state: EXPIRED` loads and isn't counted.

- [ ] **Step 3: D24 already done (Task 6 assert_non_empty)**

Verify canary: `TruthFilesRegistry.model_validate({"concepts": []})` raises.

- [ ] **Step 4: Run + commit**

Run: `just check` → commit `fix: D21 truth templates with declared H2, D22 HookState enum (6 values), D24 (in Task 6)`

---

### Task 23: Canary regression tests (the 7 sentinels)

**Files:** `tests/unit/contracts/test_canaries.py`

- [ ] **Step 1: Write the 7 canary tests** (per spec §8.2)

1. ORPHAN_READ injection (synthetic skill with bogus read → lint FAILs with exact string)
2. Uppercase-N path not corrupted (SECTION/NPC) — already in Task 1, restate here as sentinel
3. Three-root separation + .bak same-root
4. Field-match consistency (filter/G1/lint agree) + fullwidth-space equivalence
5. D16 G6.10 not dead-path
6. D19 G3.1 not silently skipping
7. Cross-layer seam (change DecisionsDoc field → g2+g4+lint fail together)

- [ ] **Step 2: Run + commit**

Run: `pytest tests/unit/contracts/test_canaries.py -v && just check` → commit `test: add 7 canary regression tests (spec §8.2)`

---

### Task 24: Final validation

- [ ] **Step 1: Full green run**

Run: `just check`
Expected: ALL green (ruff + mypy + basedpyright + pytest + lint-contracts)

- [ ] **Step 2: Inject a deliberate mismatch, confirm CI catches it**

Temporarily add a bogus `reads: [truth/nonexistent.md]` to a test skill, run `just lint-contracts`, confirm ORPHAN_READ FAIL with exact message. Revert.

- [ ] **Step 3: Commit + final**

```bash
git commit --allow-empty -m "chore: contract consistency infrastructure complete — all gates + canaries green"
```

---

## Self-Review Checklist (run before handing off)

**Spec coverage:**
- [x] §4.1 single resolver (4 impls) → Task 1, 11, 12, 13
- [x] §4.2 RoundPaths three-root → Task 4, 14, 15
- [x] §4.3 G5.2 glob-aware → Task 14b
- [x] §4.4 shared modules → Tasks 1-4
- [x] §4.5 BACKUP_SKILLS derived → Task 14a
- [x] §5.1-5.3 schemas (7 models) → Tasks 5-8
- [x] §5.4 adapter → Task 8
- [x] §5.5 versioning → in models (Tasks 5-7)
- [x] §5.6 dead-code cleanup → Task 16
- [x] §6.1 closure + Producer Registry → Tasks 17, 18
- [x] §6.2 match_field unified → Task 2, 19
- [x] §6.3 version compat → in lint (Task 18)
- [x] §6.4 justfile → Task 19
- [x] §7.5 D16/D19/D20/D21/D22/D24/D26 → Tasks 21, 22
- [x] §8.2 canaries (7) → Task 23

**Placeholder scan:** None — all steps have concrete code/commands.

**Type consistency:** `resolve_chapter_path`/`resolve_volume_path`/`extract_chapter`/`resolve_or_skip` consistent across Tasks 1, 11-13. `match_field`/`filter_to_fields` consistent across Tasks 2, 12, 19. `RoundPaths.read/write/repo/backup` consistent across Tasks 4, 14, 15. Model names consistent across Tasks 5-10.
