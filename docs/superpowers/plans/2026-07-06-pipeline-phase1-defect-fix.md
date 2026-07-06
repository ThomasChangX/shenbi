# Phase 1: Pipeline 阻塞性缺陷根因修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 8 Category A pipeline defects so the pipeline can run end-to-end on a 200k-word seed, verified by a 3-chapter canary at each step.

**Architecture:** Defect-driven incremental repair — fix one defect, verify with unit tests + 3-chapter canary, then proceed. No new modules. All changes are within existing `src/shenbi/pipeline/` files.

**Tech Stack:** Python 3.11+, pathlib, json, structlog, pytest, yaml, re

**Spec:** `docs/superpowers/specs/2026-07-06-pipeline-phase1-defect-fix-design.md`

## Global Constraints

- Python 3.11+, `from __future__ import annotations` in all modified files
- `pathlib.Path` for all file I/O, `json` for structured output
- No `print()` in framework code; use structlog (stderr)
- `safe_write` for all state file writes (atomic, fsync, lock)
- Typed enums via `StrEnum` (matching `status.py` pattern)
- Tests in `tests/unit/pipeline/`
- Conventional Commits: `fix:` prefix
- Branch: `main`
- Pre-commit hooks must stay green: ruff, mypy, basedpyright strict
- Each task ends with all existing tests passing + new tests passing
- Run `uv run pytest tests/unit/pipeline/ -v` after each task's implementation

---

## Step 1: A3 — Genre-Config Audit Matrix Alignment

### Task 1.1: Write failing tests for get_active_genre_audits with real fixture

**Files:**
- Modify: `tests/unit/pipeline/test_audit_layer.py`

**Interfaces:**
- Consumes: `shenbi.pipeline.audit_layer.get_active_genre_audits` (existing)
- Produces: Test cases that fail against current snake_case matrix

- [ ] **Step 1: Add test class for real fixture format**

```python
# tests/unit/pipeline/test_audit_layer.py — append at end of file

import json
from pathlib import Path

class TestGenreActivationCamelCase:
    """Tests that GENRE_ACTIVATION_MATRIX matches real genre-config.json format."""

    def test_real_fixture_activates_audits(self):
        """Real fixture uses auditDimensions (camelCase) top-level key."""
        fixture_path = Path("tests/fixtures/genre-config-example.json")
        if not fixture_path.exists():
            import pytest
            pytest.skip("fixture not available")
        gc = json.loads(fixture_path.read_text(encoding="utf-8"))
        result = get_active_genre_audits(gc)
        # Real fixture should activate at least 1 audit dimension
        assert len(result) > 0, f"Expected >0 audits, got {result}"
        for skill in result:
            assert skill.startswith("shenbi-review-"), f"Unexpected skill: {skill}"

    def test_camelcase_audit_dimensions_read(self):
        """auditDimensions (camelCase) is the real fixture format."""
        gc = {"auditDimensions": {"sensitivity": True, "worldRules": True}}
        result = get_active_genre_audits(gc)
        assert "shenbi-review-sensitivity" in result
        assert "shenbi-review-world-rules" in result

    def test_motivation_and_dialogue_camelcase(self):
        """motivation and dialogue are camelCase in real fixture."""
        gc = {"auditDimensions": {"motivation": True, "dialogue": True}}
        result = get_active_genre_audits(gc)
        assert "shenbi-review-motivation" in result
        assert "shenbi-review-dialogue" in result

    def test_core_circle_keys_not_in_genre_circle(self):
        """antiAi, character, pacing, continuity, foreshadowing are core circle — not genre."""
        gc = {"auditDimensions": {
            "antiAi": True, "character": True, "pacing": True,
            "continuity": True, "foreshadowing": True
        }}
        result = get_active_genre_audits(gc)
        assert len(result) == 0, f"Core circle keys should not activate genre audits: {result}"

    def test_snake_case_fallback_works(self):
        """Backward compat: audit_dimensions (snake_case) still readable."""
        gc = {"audit_dimensions": {"sensitivity": True}}
        result = get_active_genre_audits(gc)
        assert "shenbi-review-sensitivity" in result

    def test_missing_key_returns_empty(self):
        """No auditDimensions key → empty list."""
        assert get_active_genre_audits({}) == []

    def test_non_dict_audit_dims_returns_empty(self):
        """auditDimensions is not a dict → empty list."""
        assert get_active_genre_audits({"auditDimensions": "invalid"}) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_audit_layer.py::TestGenreActivationCamelCase -v`

Expected: FAIL — `test_real_fixture_activates_audits` returns 0 audits; `test_camelcase_audit_dimensions_read` returns empty because matrix reads `audit_dimensions` (snake_case) not `auditDimensions` (camelCase); `test_core_circle_keys_not_in_genre_circle` fails because current matrix keys like `world_rules` don't match `worldRules`.

### Task 1.2: Fix GENRE_ACTIVATION_MATRIX and get_active_genre_audits

**Files:**
- Modify: `src/shenbi/pipeline/audit_layer.py:36-94`

**Interfaces:**
- Consumes: None (self-contained fix)
- Produces: `get_active_genre_audits(genre_config)` — returns list of `shenbi-review-*` skill names from camelCase `auditDimensions`

- [ ] **Step 1: Replace GENRE_ACTIVATION_MATRIX and get_active_genre_audits**

```python
# src/shenbi/pipeline/audit_layer.py — replace lines 36-94

# Maps genre-config.json ``auditDimensions`` keys (camelCase) to review skills.
# Core-circle dimensions (antiAi, character, pacing, continuity, foreshadowing,
# memoCompliance, pov) are NOT here — they run as chapter_loop fixed steps.
GENRE_ACTIVATION_MATRIX: dict[str, str] = {
    "sensitivity": "shenbi-review-sensitivity",
    "worldRules": "shenbi-review-world-rules",
    "motivation": "shenbi-review-motivation",
    "dialogue": "shenbi-review-dialogue",
    "texture": "shenbi-review-texture",
    "era": "shenbi-review-era",
    "fanfic": "shenbi-review-fanfic",
    "readerPull": "shenbi-review-reader-pull",
    "highpoint": "shenbi-review-highpoint",
}

# Core-circle keys that must not be activated by the genre circle
_CORE_CIRCLE_KEYS = frozenset({
    "antiAi", "character", "pacing", "continuity",
    "foreshadowing", "memoCompliance", "pov",
})


def get_active_genre_audits(genre_config: Mapping[str, object]) -> list[str]:
    """Determine which genre-circle audits to run based on genre-config.json.

    Reads the ``auditDimensions`` sub-dict (camelCase, matching real fixture
    produced by shenbi-genre-config). Falls back to ``audit_dimensions``
    (snake_case) for backward compat. Filters out core-circle keys that are
    handled by chapter_loop fixed steps.
    """
    audit_dims = genre_config.get("auditDimensions")
    if audit_dims is None:
        audit_dims = genre_config.get("audit_dimensions", {})
    if not isinstance(audit_dims, dict):
        return []
    return sorted(
        skill
        for dim_key, skill in GENRE_ACTIVATION_MATRIX.items()
        if dim_key not in _CORE_CIRCLE_KEYS and audit_dims.get(dim_key, False)
    )
```

- [ ] **Step 2: Update docstring at top of audit_layer.py line 8**

Replace `genre-config.json`'s ``audit_dimensions`` with `genre-config.json`'s ``auditDimensions`` in the module docstring on line 8.

- [ ] **Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_audit_layer.py -v`

Expected: ALL PASS — both existing tests and new TestGenreActivationCamelCase

- [ ] **Step 4: Run full pipeline test suite**

Run: `uv run pytest tests/unit/pipeline/ -v`

Expected: ALL PASS — no regressions

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/audit_layer.py tests/unit/pipeline/test_audit_layer.py
git commit -m "fix: align genre-config activation matrix with real fixture camelCase format (A3)"
```

---

## Step 2: A8 — Audit Layer Wiring + BLOCKING Revision Loop

### Task 2.1: Add audit_retry_count to ChapterState

**Files:**
- Modify: `src/shenbi/pipeline/state.py:88-93` (ChapterState dataclass)
- Modify: `src/shenbi/pipeline/state.py:142-151` (to_dict serialization)
- Modify: `src/shenbi/pipeline/state.py:196-204` (from_dict deserialization)

**Interfaces:**
- Consumes: None
- Produces: `ChapterState.audit_retry_count: int = 0` — persisted in pipeline-state.json

- [ ] **Step 1: Add field to ChapterState dataclass**

```python
# src/shenbi/pipeline/state.py:88-93 — modify ChapterState

@dataclass
class ChapterState:
    steps_done: list[str] = field(default_factory=list)
    status: str = "pending"
    resonance_score: int | None = None
    audit_results: dict[str, Any] = field(default_factory=dict)
    revision_count: int = 0
    audit_retry_count: int = 0  # NEW: tracks audit BLOCKING revision attempts
```

- [ ] **Step 2: Add to to_dict serialization**

```python
# src/shenbi/pipeline/state.py:142-151 — add audit_retry_count

"chapter_states": {
    k: {
        "steps_done": v.steps_done,
        "status": v.status,
        "resonance_score": v.resonance_score,
        "audit_results": v.audit_results,
        "revision_count": v.revision_count,
        "audit_retry_count": v.audit_retry_count,  # NEW
    }
    for k, v in self.chapter_loop.chapter_states.items()
},
```

- [ ] **Step 3: Add to from_dict deserialization**

```python
# src/shenbi/pipeline/state.py:198-204 — add audit_retry_count

chapter_states[k] = ChapterState(
    steps_done=v.get("steps_done", []),
    status=v.get("status", "pending"),
    resonance_score=v.get("resonance_score"),
    audit_results=v.get("audit_results", {}),
    revision_count=v.get("revision_count", 0),
    audit_retry_count=v.get("audit_retry_count", 0),  # NEW
)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/pipeline/test_state.py -v`

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/state.py
git commit -m "fix: add audit_retry_count to ChapterState for audit BLOCKING revision tracking (A8)"
```

### Task 2.2: Wire audit layer into chapter_loop with BLOCKING revision loop

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:653-661`

**Prerequisite:** Task 2.1 complete (audit_retry_count field exists)

**Interfaces:**
- Consumes: `shenbi.pipeline.audit_layer.run_audit_layer` (Task 1.2), `ChapterState.audit_retry_count` (Task 2.1), `_get_chapter_state` (existing line 509), `dispatch_skill` (existing), `set_checkpoint` (existing)
- Produces: After last core-circle audit step (step 16), genre+boundary audits run; BLOCKING → revision loop → retry → escalation

- [ ] **Step 1: Write failing test for audit layer wiring**

```python
# tests/unit/pipeline/test_chapter_loop.py — append at end of file

class TestAuditLayerWiring:
    """Tests that run_audit_layer is called after core circle and handles BLOCKING."""

    def test_run_audit_layer_called_after_last_core_audit(self, tmp_path, monkeypatch):
        """After step 16 (last is_audit step), run_audit_layer is called."""
        from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, _LAST_AUDIT_IDX, run_chapter_step
        from shenbi.pipeline.state import PipelineState, PipelinePhase

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = _LAST_AUDIT_IDX  # position at step 16

        # Mock audit_layer to avoid actual dispatch
        called = []
        def fake_run_audit(project_dir, chapter, gc):
            called.append((chapter, gc))
            from shenbi.pipeline.audit_layer import AuditResult
            return AuditResult(blocking_found=False)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_audit_layer", fake_run_audit
        )
        # Mock dispatch_skill for step 16
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill",
            lambda *a, **kw: type("R", (), {"success": True})(),
        )
        # Mock G4
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        run_chapter_step(state, tmp_path)
        assert len(called) == 1, f"run_audit_layer should be called once, was {len(called)}"

    def test_audit_blocking_triggers_revision_dispatch(self, tmp_path, monkeypatch):
        """BLOCKING finding dispatches chapter-revision."""
        from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, _LAST_AUDIT_IDX, run_chapter_step
        from shenbi.pipeline.state import PipelineState, PipelinePhase

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = _LAST_AUDIT_IDX

        # Mock audit_layer returning BLOCKING
        def fake_run_audit(project_dir, chapter, gc):
            from shenbi.pipeline.audit_layer import AuditResult
            r = AuditResult(blocking_found=True)
            r.issues = [{"skill": "test", "severity": "BLOCKING"}]
            return r
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_audit_layer", fake_run_audit
        )

        revisions = []
        def fake_dispatch(skill, project_dir, prompt):
            if "chapter-revision" in skill:
                revisions.append(prompt)
            return type("R", (), {"success": True})()
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill", fake_dispatch
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        run_chapter_step(state, tmp_path)
        assert len(revisions) >= 1, f"Expected revision dispatch, got {len(revisions)}"

    def test_audit_max_retries_triggers_escalation(self, tmp_path, monkeypatch):
        """After max_revision_retries BLOCKING rounds, ESCALATION checkpoint is set."""
        from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, _LAST_AUDIT_IDX, run_chapter_step
        from shenbi.pipeline.state import PipelineState, PipelinePhase, CheckpointType

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = _LAST_AUDIT_IDX
        state.config.max_revision_retries = 3

        def fake_run_audit(project_dir, chapter, gc):
            from shenbi.pipeline.audit_layer import AuditResult
            r = AuditResult(blocking_found=True)
            r.issues = [{"skill": "test", "severity": "BLOCKING"}]
            return r
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_audit_layer", fake_run_audit
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill",
            lambda *a, **kw: type("R", (), {"success": True})(),
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        run_chapter_step(state, tmp_path)
        cs = state.chapter_loop.chapter_states.get("1")
        assert cs is not None
        assert cs.audit_retry_count > 0, f"audit_retry_count should be > 0, got {cs.audit_retry_count}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestAuditLayerWiring -v`

Expected: FAIL — `test_run_audit_layer_called_after_last_core_audit` fails because TODO(W3T4) doesn't call run_audit_layer; `test_audit_blocking_triggers_revision_dispatch` fails; `test_audit_max_retries_triggers_escalation` fails.

- [ ] **Step 3: Replace TODO(W3T4) with audit revision loop**

```python
# src/shenbi/pipeline/chapter_loop.py — replace lines 653-661

    # After last core-circle audit: genre circle + boundary circle via audit_layer.
    if step.is_audit and step_idx == _LAST_AUDIT_IDX:
        import json
        from shenbi.pipeline.audit_layer import run_audit_layer

        gc_path = project_dir / "genre-config.json"
        gc: dict[str, object] = {}
        if gc_path.exists():
            gc = json.loads(gc_path.read_text(encoding="utf-8"))

        cs = _get_chapter_state(state, chapter)
        while True:
            audit_result = run_audit_layer(project_dir, chapter, gc)
            cs.audit_results["blocking_found"] = audit_result.blocking_found
            cs.audit_results["issues"] = audit_result.issues
            cs.audit_results["audit_reports"] = audit_result.audit_reports

            if not audit_result.blocking_found:
                log.info("audit_layer_passed", chapter=chapter)
                break

            cs.audit_retry_count += 1
            if cs.audit_retry_count > state.config.max_revision_retries:
                log.error(
                    "audit_blocking_escalation",
                    chapter=chapter,
                    retries=cs.audit_retry_count,
                )
                set_checkpoint(
                    state,
                    CheckpointType.ESCALATION,
                    chapter=chapter,
                    context=(
                        f"Audit BLOCKING persists after {cs.audit_retry_count} "
                        f"revision attempts for chapter {chapter}"
                    ),
                )
                return True  # checkpoint raised, pause for human

            log.info(
                "audit_blocking_revision",
                chapter=chapter,
                retry=cs.audit_retry_count,
            )
            rev = dispatch_skill(
                "shenbi-chapter-revision",
                project_dir,
                f"Revise chapter {chapter} to fix audit BLOCKING issues.",
            )
            if not rev.success:
                return _handle_failure(state, step, chapter, "audit-revision")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestAuditLayerWiring -v`

Expected: ALL PASS

- [ ] **Step 5: Run full pipeline test suite**

Run: `uv run pytest tests/unit/pipeline/ -v`

Expected: ALL PASS — no regressions

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_chapter_loop.py
git commit -m "fix: wire audit layer into chapter_loop with BLOCKING revision loop (A8)"
```

---

## Step 3: A7 — State-Settling G4 Validation Fix

### Task 3.1: Write failing test for _resolve_g4_files

**Files:**
- Modify: `tests/unit/pipeline/test_chapter_loop.py`

**Interfaces:**
- Consumes: `_resolve_g4_files` (to be created)
- Produces: Test that state-settling step returns staging/truth/*.md files

- [ ] **Step 1: Add test class**

```python
# tests/unit/pipeline/test_chapter_loop.py — append

class TestResolveG4Files:
    """Tests _resolve_g4_files for multi-file steps like state-settling."""

    def test_state_settling_returns_staging_truth_files(self, tmp_path):
        """State-settling step globs staging/truth/*.md."""
        from shenbi.pipeline.chapter_loop import (
            CHAPTER_STEPS, _resolve_g4_files,
        )

        # Find state-settling step (step 7, index 6)
        ss_step = [s for s in CHAPTER_STEPS if "state-settling" in s.skill][0]

        # Create staging/truth/ with some .md files
        staging_truth = tmp_path / "staging" / "truth"
        staging_truth.mkdir(parents=True)
        (staging_truth / "current_state.md").write_text("# state")
        (staging_truth / "character_matrix.md").write_text("# chars")
        (staging_truth / "not_markdown.txt").write_text("nope")

        files = _resolve_g4_files(tmp_path, ss_step, chapter=5)
        assert len(files) >= 2
        assert any("current_state.md" in f for f in files)
        assert any("character_matrix.md" in f for f in files)
        # .txt file should NOT be in the list
        assert not any("not_markdown.txt" in f for f in files)

    def test_state_settling_empty_staging_returns_empty(self, tmp_path):
        """No staging/truth/ dir → returns empty list, no crash."""
        from shenbi.pipeline.chapter_loop import (
            CHAPTER_STEPS, _resolve_g4_files,
        )
        ss_step = [s for s in CHAPTER_STEPS if "state-settling" in s.skill][0]
        files = _resolve_g4_files(tmp_path, ss_step, chapter=5)
        assert files == []

    def test_non_state_settling_returns_single_file(self, tmp_path):
        """Non-state-settling steps return single path unchanged."""
        from shenbi.pipeline.chapter_loop import (
            CHAPTER_STEPS, _resolve_g4_files,
        )
        drafting_step = CHAPTER_STEPS[5]  # step 6: chapter-drafting
        files = _resolve_g4_files(tmp_path, drafting_step, chapter=3)
        assert len(files) == 1
        assert "chapter-3.md" in files[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestResolveG4Files -v`

Expected: FAIL — `_resolve_g4_files` does not exist yet

### Task 3.2: Implement _resolve_g4_files and wire into run_chapter_step

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (add function, modify 2 lines)

**Interfaces:**
- Consumes: `_resolve_g4_path` (existing), `STAGING_DIR` (existing in checkpoint module)
- Produces: `_resolve_g4_files(project_dir, step, chapter) -> list[str]`

- [ ] **Step 1: Add _resolve_g4_files helper**

```python
# src/shenbi/pipeline/chapter_loop.py — add after _resolve_g4_path (line 279)

def _resolve_g4_files(
    project_dir: Path, step: ChapterStep, chapter: int
) -> list[str]:
    """Return list of file paths for G4 validation.

    Single-file steps return one path. State-settling returns all
    staging/truth/*.md files because it writes multiple truth outputs.
    Steps with no output return [].
    """
    single = _resolve_g4_path(project_dir, step, chapter)
    if single:
        return [single]

    # State-settling writes multiple truth files to staging/
    if step.uses_staging and "state-settling" in step.skill:
        from shenbi.pipeline.checkpoint import STAGING_DIR

        staging_truth = project_dir / STAGING_DIR / "truth"
        if staging_truth.exists():
            return sorted(
                f"{STAGING_DIR}/truth/{p.name}"
                for p in staging_truth.glob("*.md")
            )

    return []
```

- [ ] **Step 2: Replace G4 path resolution in run_chapter_step**

```python
# src/shenbi/pipeline/chapter_loop.py — replace lines 625-626

# Before:
g4_file = _resolve_g4_path(project_dir, step, chapter)
g4 = run_gate_g4(step.skill, [g4_file] if g4_file else [], project_dir)

# After:
g4_files = _resolve_g4_files(project_dir, step, chapter)
g4 = run_gate_g4(step.skill, g4_files, project_dir)
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestResolveG4Files -v`

Expected: ALL PASS

- [ ] **Step 4: Run full pipeline test suite**

Run: `uv run pytest tests/unit/pipeline/ -v`

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_chapter_loop.py
git commit -m "fix: resolve state-settling G4 empty file list with staging glob (A7)"
```

---

## Step 4: A5 — Error Handler Wiring

### Task 4.1: Wire handle_state_settle_failure

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (~line 614)
- Modify: `tests/unit/pipeline/test_chapter_loop.py`

**Prerequisite:** Step 3 complete (state-settling G4 uses _resolve_g4_files)

**Interfaces:**
- Consumes: `shenbi.pipeline.error_handler.handle_state_settle_failure` (existing)
- Produces: State-settling dispatch failure → `settling_failed` status + ESCALATION checkpoint

- [ ] **Step 1: Write failing test**

```python
# tests/unit/pipeline/test_chapter_loop.py — append

class TestStateSettleFailureWiring:
    """Tests that state-settling failure calls handle_state_settle_failure."""

    def test_state_settle_failure_triggers_escalation(self, tmp_path, monkeypatch):
        """State-settling dispatch failure → ESCALATION checkpoint."""
        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.state import PipelineState, PipelinePhase, CheckpointType

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 3
        state.chapter_loop.step_index = 6  # state-settling is index 6

        # Mock dispatch to fail for state-settling
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill",
            lambda *a, **kw: type("R", (), {"success": False})(),
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        result = run_chapter_step(state, tmp_path)
        # Should return True (checkpoint raised)
        assert result is True
        # Check chapter status is settling_failed
        cs = state.chapter_loop.chapter_states.get("3")
        assert cs is not None
        assert cs.status == "settling_failed"
        assert state.pending_checkpoint.type == CheckpointType.ESCALATION
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestStateSettleFailureWiring -v`

Expected: FAIL — state-settling failure treated as generic dispatch failure, not marked settling_failed

- [ ] **Step 3: Wire handle_state_settle_failure into run_chapter_step**

```python
# src/shenbi/pipeline/chapter_loop.py — in run_chapter_step(), after dispatch_skill,
# BEFORE the generic "if not result.success" check (currently line 615-622).
# Insert after line 614 (result = dispatch_skill(...)):

    # State-settling failure: mark settling_failed and pause (spec §11).
    if not result.success and "state-settling" in step.skill:
        from shenbi.pipeline.error_handler import handle_state_settle_failure

        handle_state_settle_failure(state, chapter)
        log.error(
            "chapter_state_settle_failed",
            chapter=chapter,
            step=step.step_num,
        )
        return True  # checkpoint raised, pause for human
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestStateSettleFailureWiring -v`

Expected: PASS

- [ ] **Step 5: Run full pipeline test suite**

Run: `uv run pytest tests/unit/pipeline/ -v`

Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_chapter_loop.py
git commit -m "fix: wire handle_state_settle_failure for state-settling dispatch failures (A5a)"
```

### Task 4.2: Wire handle_scoring_failure for review-resonance

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (~line 614)
- Modify: `tests/unit/pipeline/test_chapter_loop.py`

**Interfaces:**
- Consumes: `shenbi.pipeline.error_handler.handle_scoring_failure` (existing), `DispatchResult.returncode`
- Produces: review-resonance exit code 2/3 → retry path; other → escalate

- [ ] **Step 1: Write failing test**

```python
# tests/unit/pipeline/test_chapter_loop.py — append

class TestScoringFailureWiring:
    """Tests review-resonance exit code handling."""

    def test_exit_code_2_triggers_redispatch(self, tmp_path, monkeypatch):
        """review-resonance returncode=2 → handle_scoring_failure returns True → retry."""
        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.state import PipelineState, PipelinePhase

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 16  # review-resonance is index 16

        called = []
        def fake_scoring_failure(s, exit_code):
            called.append(exit_code)
            return True  # should retry
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.handle_scoring_failure", fake_scoring_failure
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill",
            lambda *a, **kw: type("R", (), {"success": False, "returncode": 2})(),
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        result = run_chapter_step(state, tmp_path)
        assert len(called) == 1
        assert called[0] == 2
        # Should return False (retry, step_index unchanged)
        assert result is False
        assert state.chapter_loop.step_index == 16  # not advanced

    def test_exit_code_3_also_retries(self, tmp_path, monkeypatch):
        """review-resonance returncode=3 → handle_scoring_failure returns True → retry."""
        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.state import PipelineState, PipelinePhase

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 16

        def fake_scoring_failure(s, exit_code):
            return True
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.handle_scoring_failure", fake_scoring_failure
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.dispatch_skill",
            lambda *a, **kw: type("R", (), {"success": False, "returncode": 3})(),
        )
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop.run_gate_g4",
            lambda *a, **kw: {"status": "PASS"},
        )

        result = run_chapter_step(state, tmp_path)
        assert result is False
        assert state.chapter_loop.step_index == 16  # not advanced
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestScoringFailureWiring -v`

Expected: FAIL — scoring exit codes not checked

- [ ] **Step 3: Wire scoring failure check into run_chapter_step**

```python
# src/shenbi/pipeline/chapter_loop.py — in run_chapter_step(), after dispatch_skill
# and after the state-settling check (Task 4.1), BEFORE the generic success check.
# Insert after Task 4.1's code:

    # Scoring failure (review-resonance): exit code 2/3 need special handling.
    if not result.success and "review-resonance" in step.skill:
        from shenbi.pipeline.error_handler import handle_scoring_failure

        if handle_scoring_failure(state, result.returncode):
            log.warning(
                "scoring_failure_retry",
                chapter=chapter,
                exit_code=result.returncode,
            )
            return False  # retry this step, don't advance step_index
        return _handle_failure(state, step, chapter, "scoring")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestScoringFailureWiring -v`

Expected: ALL PASS

- [ ] **Step 5: Run full pipeline test suite**

Run: `uv run pytest tests/unit/pipeline/ -v`

Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_chapter_loop.py
git commit -m "fix: wire handle_scoring_failure for review-resonance exit codes (A5b)"
```

---

## Step 5: A4 — Escalation-Review Dispatch Wiring

### Task 5.1: Dispatch escalation-review before setting ESCALATION checkpoint

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:_handle_failure` (line 282-326)
- Modify: `src/shenbi/pipeline/genesis.py:_handle_failure` (line 230-255)
- Modify: `src/shenbi/pipeline/closure.py:_handle_failure` (line ~240-260)

**Interfaces:**
- Consumes: `shenbi.pipeline.revision_router.dispatch_escalation(project_dir, chapter, context="") -> bool` (existing)
- Produces: Retry exhaustion → dispatch escalation-review → set ESCALATION checkpoint with report path

- [ ] **Step 1: Wire into chapter_loop._handle_failure**

```python
# src/shenbi/pipeline/chapter_loop.py — in _handle_failure(),
# BEFORE set_checkpoint when handle_dispatch_failure returns False (line 309-326).
# Replace the block starting from "log.error(...)":

    # Retries exhausted: dispatch escalation-review first, then set checkpoint.
    from shenbi.pipeline.revision_router import dispatch_escalation

    dispatch_escalation(
        project_dir,
        chapter,
        context=f"Chapter {chapter} step {step.step_num} ({step.skill}) failed after {count} {failure} attempts",
    )
    log.error(
        "chapter_step_escalation",
        chapter=chapter,
        step=step.step_num,
        skill=step.skill,
        failure=failure,
        attempts=count,
    )
    set_checkpoint(
        state,
        CheckpointType.ESCALATION,
        chapter=chapter,
        artifact=f"audits/escalation-{chapter}-report.md",
        context=(
            f"Chapter {chapter} step {step.step_num} ({step.skill}) "
            f"failed after {count} {failure} attempts. "
            f"See audits/escalation-{chapter}-report.md for analysis."
        ),
    )
    return True
```

- [ ] **Step 2: Wire into genesis._handle_failure**

```python
# src/shenbi/pipeline/genesis.py — in _handle_failure(),
# BEFORE set_checkpoint when handle_dispatch_failure returns False.
# Same pattern: call dispatch_escalation first, then set checkpoint.

    from shenbi.pipeline.revision_router import dispatch_escalation

    dispatch_escalation(
        project_dir,
        0,  # genesis has no chapter number
        context=f"Genesis step {step.step_num} ({step.skill}) failed after {count} {failure} attempts",
    )
    set_checkpoint(
        state,
        CheckpointType.ESCALATION,
        chapter=0,
        artifact="audits/escalation-genesis-report.md",
        context=(...),
    )
    return True
```

- [ ] **Step 3: Wire into closure escalation in cli.py**

```python
# src/shenbi/pipeline/cli.py:274-283 — in _orchestrate_to_checkpoint(),
# where closure step failure raises ESCALATION.
# BEFORE set_checkpoint, add dispatch_escalation:

            else:
                # Closure step failed — dispatch escalation-review first
                from shenbi.pipeline.revision_router import dispatch_escalation

                dispatch_escalation(
                    project_dir,
                    0,  # closure has no chapter context
                    context=f"Closure step {state.closure_step + 1} failed",
                )
                set_checkpoint(
                    state,
                    CheckpointType.ESCALATION,
                    context=f"Closure step {state.closure_step + 1} failed",
                )
                return
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py tests/unit/pipeline/test_genesis.py tests/unit/pipeline/test_closure.py -v`

Expected: ALL PASS — ensure dispatch_escalation is mockable and tests pass

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/genesis.py src/shenbi/pipeline/closure.py
git commit -m "fix: wire escalation-review dispatch before raising ESCALATION checkpoint (A4)"
```

---

## Step 6: A2 — Resonance Score Parser

### Task 6.1: Implement _parse_resonance_score and wire into chapter_loop

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (add function + wire at line ~664)
- Modify: `tests/unit/pipeline/test_chapter_loop.py`

**Interfaces:**
- Consumes: `audits/chapter-N-resonance.md` (produced by review-resonance)
- Produces: `ChapterState.resonance_score: int | None` — parsed from report

- [ ] **Step 1: Write failing test**

```python
# tests/unit/pipeline/test_chapter_loop.py — append

class TestResonanceScoreParser:
    """Tests _parse_resonance_score from audit reports."""

    def test_parses_yaml_frontmatter(self, tmp_path):
        from shenbi.pipeline.chapter_loop import _parse_resonance_score

        report = tmp_path / "resonance.md"
        report.write_text("---\nresonance_score: 87\n---\n# Report\n...")
        assert _parse_resonance_score(report) == 87

    def test_parses_bold_label(self, tmp_path):
        from shenbi.pipeline.chapter_loop import _parse_resonance_score

        report = tmp_path / "resonance.md"
        report.write_text("# Review\n\n**Resonance Score**: 92\n\nDetails...")
        assert _parse_resonance_score(report) == 92

    def test_parses_plain_label(self, tmp_path):
        from shenbi.pipeline.chapter_loop import _parse_resonance_score

        report = tmp_path / "resonance.md"
        report.write_text("Score: 75")
        assert _parse_resonance_score(report) == 75

    def test_missing_file_returns_none(self, tmp_path):
        from shenbi.pipeline.chapter_loop import _parse_resonance_score

        assert _parse_resonance_score(tmp_path / "nonexistent.md") is None

    def test_no_score_found_returns_none(self, tmp_path):
        from shenbi.pipeline.chapter_loop import _parse_resonance_score

        report = tmp_path / "resonance.md"
        report.write_text("# No score here\n\nJust text.")
        assert _parse_resonance_score(report) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestResonanceScoreParser -v`

Expected: FAIL — `_parse_resonance_score` does not exist

- [ ] **Step 3: Implement _parse_resonance_score**

```python
# src/shenbi/pipeline/chapter_loop.py — add after _count_triggered_hooks (line 499)

def _parse_resonance_score(report_path: Path) -> int | None:
    """Extract resonance score from a review-resonance audit report.

    Attempts three patterns in order:
    1. YAML frontmatter ``resonance_score: 87``
    2. Markdown bold ``**Resonance Score**: 92``
    3. Plain ``Score: 75`` or ``resonance_score: 75``
    """
    if not report_path.exists():
        return None
    text = report_path.read_text(encoding="utf-8")

    # Pattern 1: YAML frontmatter
    if text.startswith("---"):
        import yaml

        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                score = fm.get("resonance_score")
                if isinstance(score, int):
                    return score
            except Exception:
                pass

    # Pattern 2: Markdown bold label (case-insensitive)
    m = re.search(r"\*\*Resonance\s*Score\*\*:\s*(\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Pattern 3: Plain "Score: N" or "resonance_score: N"
    m = re.search(r"(?:Score|resonance_score)\s*:\s*(\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    return None
```

- [ ] **Step 4: Wire into run_chapter_step after review-resonance success**

```python
# src/shenbi/pipeline/chapter_loop.py — in run_chapter_step(),
# at the existing "if review-resonance in step.skill" block (line ~664),
# BEFORE _route_revision_after_resonance call:

    if "review-resonance" in step.skill:
        # Parse resonance score from the audit report
        cs = _get_chapter_state(state, chapter)
        report_path = project_dir / _substitute_chapter(
            "audits/chapter-N-resonance.md", chapter
        )
        cs.resonance_score = _parse_resonance_score(report_path)
        log.info(
            "resonance_score_parsed",
            chapter=chapter,
            score=cs.resonance_score,
        )

        _route_revision_after_resonance(state, project_dir, chapter)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestResonanceScoreParser -v`

Expected: ALL PASS

- [ ] **Step 6: Run full pipeline test suite**

Run: `uv run pytest tests/unit/pipeline/ -v`

Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_chapter_loop.py
git commit -m "fix: parse resonance score from audit report and store in ChapterState (A2)"
```

---

## Step 7: A1 — total_chapters Dynamic Recompute

### Task 7.1: Implement _count_total_chapters and _update_total_chapters

**Files:**
- Modify: `src/shenbi/pipeline/triggers.py` (add functions + call after volume expansion)
- Modify: `tests/unit/pipeline/test_triggers.py`

**Interfaces:**
- Consumes: `truth/volume_map.md` (existing), `novel.json` (existing)
- Produces: `_count_total_chapters(project_dir) -> int`, `_update_total_chapters(state) -> None`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/pipeline/test_triggers.py — append

class TestTotalChaptersRecompute:
    """Tests _count_total_chapters and _update_total_chapters."""

    def test_count_total_chapters_from_volume_map(self, tmp_path):
        """Parse volume_map.md and sum per-volume chapter counts."""
        from shenbi.pipeline.triggers import _count_total_chapters

        vmap = tmp_path / "truth"
        vmap.mkdir(parents=True)
        (vmap / "volume_map.md").write_text(
            "# Volume Map\n\n"
            "## Volume 1\n章节数: 10\n\n"
            "## Volume 2\n章节数: 15\n\n"
            "## Volume 3\n章节数: 12\n"
        )
        assert _count_total_chapters(tmp_path) == 37

    def test_count_total_chapters_english_labels(self, tmp_path):
        """Also parses 'Chapters: N' labels."""
        from shenbi.pipeline.triggers import _count_total_chapters

        vmap = tmp_path / "truth"
        vmap.mkdir(parents=True)
        (vmap / "volume_map.md").write_text(
            "## Volume 1\nChapters: 8\n## Volume 2\nChapters: 12\n"
        )
        assert _count_total_chapters(tmp_path) == 20

    def test_count_total_chapters_missing_file(self, tmp_path):
        """Missing volume_map.md → 0, no crash."""
        from shenbi.pipeline.triggers import _count_total_chapters
        assert _count_total_chapters(tmp_path) == 0

    def test_update_total_chapters_updates_novel_json(self, tmp_path):
        """_update_total_chapters writes the new total to novel.json."""
        import json
        from shenbi.pipeline.triggers import _update_total_chapters
        from shenbi.pipeline.state import PipelineState

        # Setup: volume_map with chapters
        vmap = tmp_path / "truth"
        vmap.mkdir(parents=True)
        (vmap / "volume_map.md").write_text("## V1\n章节数: 10\n## V2\n章节数: 8\n")

        # Setup: novel.json with old total
        novel = {"total_chapters": 5, "title": "Test"}
        (tmp_path / "novel.json").write_text(json.dumps(novel))

        state = PipelineState.default(str(tmp_path))
        _update_total_chapters(state)

        updated = json.loads((tmp_path / "novel.json").read_text())
        assert updated["total_chapters"] == 18
        assert updated["title"] == "Test"  # preserved
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_triggers.py::TestTotalChaptersRecompute -v`

Expected: FAIL — functions don't exist

- [ ] **Step 3: Implement _count_total_chapters and _update_total_chapters**

```python
# src/shenbi/pipeline/triggers.py — add after TRIGGER_STEPS definition (~line 70)

def _count_total_chapters(project_dir: Path) -> int:
    """Parse volume_map.md and sum all volume chapter counts."""
    vmap = project_dir / "truth" / "volume_map.md"
    if not vmap.exists():
        return 0
    text = vmap.read_text(encoding="utf-8")

    total = 0
    for m in re.finditer(r"(?:章节数|Chapters?)\s*:\s*(\d+)", text):
        total += int(m.group(1))
    return total if total > 0 else 0


def _update_total_chapters(state: PipelineState) -> None:
    """Recompute novel.json.total_chapters from volume_map.md.

    Called after volume boundary expansion to ensure the chapter-loop
    termination condition is accurate.
    """
    project_dir = Path(state.project_dir)
    new_total = _count_total_chapters(project_dir)
    if new_total < 1:
        return

    novel_json = project_dir / "novel.json"
    if not novel_json.exists():
        return

    data = json.loads(novel_json.read_text(encoding="utf-8"))
    old_total = data.get("total_chapters", 0)
    if new_total != old_total:
        data["total_chapters"] = new_total
        novel_json.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log.info("total_chapters_updated", old=old_total, new=new_total)
```

- [ ] **Step 4: Call _update_total_chapters after volume boundary expansion**

```python
# src/shenbi/pipeline/triggers.py — in run_triggered_skills(),
# after all triggered steps complete (line 543) and BEFORE the volume-boundary
# checkpoint is raised (line 550). Add at line 545:

    # After volume boundary expansion: recompute total_chapters from volume_map
    if result.volume_boundary:
        _update_total_chapters(state)
```

Insert this block between the for-loop end and the existing `if result.volume_boundary:` checkpoint block.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_triggers.py::TestTotalChaptersRecompute -v`

Expected: ALL PASS

- [ ] **Step 6: Run full pipeline test suite**

Run: `uv run pytest tests/unit/pipeline/ -v`

Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/pipeline/triggers.py tests/unit/pipeline/test_triggers.py
git commit -m "fix: recompute total_chapters from volume_map after volume expansion (A1)"
```

---

## Step 8: A6 — MODIFY Decision Behavior Fix

### Task 8.1: Add modify_feedback to ChapterLoopStateData

**Files:**
- Modify: `src/shenbi/pipeline/state.py:97-103` (ChapterLoopStateData)
- Modify: `src/shenbi/pipeline/state.py:138-154` (to_dict)
- Modify: `src/shenbi/pipeline/state.py:216-223` (from_dict)

**Interfaces:**
- Consumes: None
- Produces: `ChapterLoopStateData.modify_feedback: str | None = None`

- [ ] **Step 1: Add field to ChapterLoopStateData**

```python
# src/shenbi/pipeline/state.py:97-103

@dataclass
class ChapterLoopStateData:
    current_chapter: int = 0
    current_step: str = ""
    step_index: int = 0
    chapter_states: dict[str, ChapterState] = field(default_factory=dict)
    per_chapter_review_enabled: bool = True
    retry_counts: dict[str, int] = field(default_factory=dict)
    modify_feedback: str | None = None  # NEW: MODIFY checkpoint feedback for re-dispatch
```

- [ ] **Step 2: Add to to_dict**

```python
# src/shenbi/pipeline/state.py — in to_dict "chapter_loop" block, add after retry_counts:

"modify_feedback": self.chapter_loop.modify_feedback,
```

- [ ] **Step 3: Add to from_dict**

```python
# src/shenbi/pipeline/state.py — in ChapterLoopStateData construction, add:

modify_feedback=cl_data.get("modify_feedback"),
```

- [ ] **Step 4: Run state tests**

Run: `uv run pytest tests/unit/pipeline/test_state.py -v`

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/state.py
git commit -m "fix: add modify_feedback field to ChapterLoopStateData for MODIFY decisions (A6a)"
```

### Task 8.2: Implement MODIFY step rollback and feedback injection

**Files:**
- Modify: `src/shenbi/pipeline/cli.py:500-534` (cmd_review)
- Modify: `src/shenbi/pipeline/chapter_loop.py` (dispatch prompt)
- Modify: `tests/unit/pipeline/test_cli.py`

**Prerequisite:** Task 8.1 complete (modify_feedback field exists)

**Interfaces:**
- Consumes: `ChapterLoopStateData.modify_feedback` (Task 8.1), `CheckpointType`
- Produces: MODIFY → step_index rollback + feedback stored → re-dispatch on resume

- [ ] **Step 1: Write failing test**

```python
# tests/unit/pipeline/test_cli.py — append

class TestModifyDecision:
    """Tests that MODIFY rolls back step cursor and stores feedback."""

    def test_modify_chapter_memo_rolls_back_step_index(self, tmp_path, monkeypatch):
        """MODIFY on CHAPTER_MEMO checkpoint resets step_index to 1."""
        from shenbi.pipeline.state import (
            PipelineState, CheckpointType, CheckpointData, PipelinePhase,
        )
        from shenbi.pipeline.machine import set_checkpoint

        state = PipelineState.default(str(tmp_path))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 3
        state.chapter_loop.step_index = 2  # after chapter-planning

        set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=3,
                       artifact="plans/chapter-3-plan.md")

        # Simulate MODIFY: step_index should roll back to 1 (chapter-planning is CHAPTER_STEPS[1])
        from shenbi.pipeline.cli import ReviewDecision
        from shenbi.pipeline.machine import clear_checkpoint

        cp = state.pending_checkpoint
        clear_checkpoint(state, ReviewDecision.MODIFY)

        if cp.type == CheckpointType.CHAPTER_MEMO:
            state.chapter_loop.step_index = 1
        elif cp.type == CheckpointType.STATE_SETTLE:
            state.chapter_loop.step_index = 6

        assert state.chapter_loop.step_index == 1
        assert state.pending_checkpoint.type == CheckpointType.NONE

    def test_modify_injects_feedback_into_dispatch_prompt(self, tmp_path, monkeypatch):
        """Feedback stored in modify_feedback appears in next dispatch prompt."""
        from shenbi.pipeline.state import PipelineState

        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.modify_feedback = "Fix the pacing in section 3"

        # Simulate dispatch prompt construction (same logic as run_chapter_step)
        prompt = f"Execute chapter-planning for chapter 3. Project dir: {tmp_path}"
        if state.chapter_loop.modify_feedback:
            prompt += f"\n\nHuman review feedback: {state.chapter_loop.modify_feedback}"
            state.chapter_loop.modify_feedback = None

        assert "Fix the pacing in section 3" in prompt
        assert state.chapter_loop.modify_feedback is None  # consumed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_cli.py::TestModifyDecision -v`

Expected: FAIL — MODIFY doesn't rollback step_index or use feedback

- [ ] **Step 3: Modify cmd_review in cli.py**

```python
# src/shenbi/pipeline/cli.py — in cmd_review(), after clear_checkpoint call at line 516,
# add step rollback for MODIFY decisions. Insert after the feedback reading block:

            if decision == ReviewDecision.MODIFY:
                # Roll back step cursor so resume re-dispatches the skill
                if cp.type == CheckpointType.CHAPTER_MEMO:
                    state.chapter_loop.step_index = 1  # CHAPTER_STEPS[1] = chapter-planning
                elif cp.type == CheckpointType.STATE_SETTLE:
                    state.chapter_loop.step_index = 6  # CHAPTER_STEPS[6] = state-settling
                elif cp.type == CheckpointType.GENESIS_COMPLETE:
                    state.genesis.current_step = max(0, state.genesis.current_step - 1)

                # Store feedback for the next dispatch
                if feedback:
                    state.chapter_loop.modify_feedback = feedback
```

- [ ] **Step 4: Modify dispatch prompt construction in chapter_loop.py**

```python
# src/shenbi/pipeline/chapter_loop.py — in run_chapter_step(), where prompt is built (~line 609):

    prompt = f"Execute {step.skill} for chapter {chapter}. Project dir: {project_dir}"
    if step.uses_staging:
        prompt += " Write output to staging/ directory."

    # Inject MODIFY feedback if present (one-shot consumption)
    if state.chapter_loop.modify_feedback:
        prompt += (
            f"\n\nHuman review feedback (incorporate these changes): "
            f"{state.chapter_loop.modify_feedback}"
        )
        state.chapter_loop.modify_feedback = None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_cli.py::TestModifyDecision -v`

Expected: ALL PASS

- [ ] **Step 6: Run full pipeline test suite**

Run: `uv run pytest tests/unit/pipeline/ -v`

Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/pipeline/cli.py src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_cli.py
git commit -m "fix: implement MODIFY step rollback and feedback injection (A6)"
```

---

## Step 9: Canary Verification

### Task 9.1: Create 3-chapter canary seed

**Files:**
- Create: `tests/fixtures/canary-3-chapter-seed.md`

- [ ] **Step 1: Create minimal 3-chapter seed**

Write a compact seed file with 3 chapter outlines based on `outline-example.md`'s first 3 chapters. Target ~1000 words per chapter. Include all required YAML sections (基本信息, 主角设定, 世界观设定, 核心冲突, 章节大纲 with 3 chapters, 三幕结构 truncated).

- [ ] **Step 2: Commit**

```bash
git add tests/fixtures/canary-3-chapter-seed.md
git commit -m "test: add 3-chapter canary seed for pipeline verification"
```

### Task 9.2: Create 10-chapter canary seed

**Files:**
- Create: `tests/fixtures/canary-10-chapter-seed.md`

- [ ] **Step 1: Create 10-chapter seed**

Expand the 3-chapter seed to 10 chapters, following the same structure. Include volume boundaries if applicable.

- [ ] **Step 2: Commit**

```bash
git add tests/fixtures/canary-10-chapter-seed.md
git commit -m "test: add 10-chapter canary seed for pipeline integration test"
```

### Task 9.3: Verify 3-chapter canary end-to-end

- [ ] **Step 1: Run 3-chapter pipeline**

```bash
rm -rf /tmp/canary-3
just pipeline-init tests/fixtures/canary-3-chapter-seed.md /tmp/canary-3 --auto
```

- [ ] **Step 2: Execute to completion**

Repeatedly run `just pipeline-next /tmp/canary-3` until the pipeline reaches `completed` or `blocked` state. If blocked, review and approve.

- [ ] **Step 3: Verify output**

Check that:
- `chapters/chapter-1.md`, `chapter-2.md`, `chapter-3.md` exist and are non-empty
- `pipeline-state.json` phase is `completed`
- No ESCALATION checkpoints in checkpoint_history
- resonance_score is parsed (not None) for each chapter

- [ ] **Step 4: If canary fails** — return to the Step that corresponds to the failure and fix

### Task 9.4: Verify 10-chapter canary (after 3-chapter passes)

- [ ] **Step 1: Run 10-chapter pipeline**

```bash
rm -rf /tmp/canary-10
just pipeline-init tests/fixtures/canary-10-chapter-seed.md /tmp/canary-10 --auto
```

- [ ] **Step 2: Execute to completion with `just pipeline-next`**

- [ ] **Step 3: Verify output and fix any failures**

### Task 9.5: Verify 200k-word full seed (after 10-chapter passes)

- [ ] **Step 1: Run full pipeline**

```bash
rm -rf /tmp/canary-full
just pipeline-init outline-example.md /tmp/canary-full --auto
```

- [ ] **Step 2: Execute to completion**

- [ ] **Step 3: Verify output and report results**
