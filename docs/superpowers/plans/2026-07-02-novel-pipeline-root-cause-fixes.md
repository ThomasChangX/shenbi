# Novel Pipeline 根因修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 55 discovered correctness defects, robustness gaps, test coverage blind spots, and code debt in the novel-pipeline through root-cause analysis and targeted fixes.

**Architecture:** Modifications to existing `src/shenbi/pipeline/` modules (19 files) following established patterns: TDD, structlog logging, safe_write for state, StrEnum typing. No new modules — all fixes are within existing files.

**Tech Stack:** Python 3.11+, pathlib, json, structlog, pytest, existing pipeline framework

**Spec:** `docs/superpowers/specs/2026-07-02-novel-pipeline-root-cause-fixes-design.md`

## Global Constraints

- Python 3.11+, `from __future__ import annotations` in all modified files
- `pathlib.Path` for all file I/O, `json` for structured output
- No `print()` in framework code; use structlog (stderr) + `cli_utils.emit_json` (stdout)
- `safe_write` for all state file writes (atomic, fsync, lock)
- Typed enums via `StrEnum` (matching `status.py` pattern)
- Tests in `tests/unit/pipeline/`
- Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`
- Branch: `codex/novel-pipeline` (existing)
- Use `io.StringIO`-via-monkeypatch test pattern (NOT capsys, see W1T6 lesson)

## File Structure

Files modified (no new files):

```
src/shenbi/pipeline/
    state.py              # +audit_retry_count, +modify_feedback, +modify_pending_step, +needs_truth_sync, +DEFAULT_MAX_*_RETRIES
    machine.py            # clear_checkpoint idempotency guard
    audit_layer.py        # GENRE_ACTIVATION_MATRIX rewrite
    chapter_loop.py       # audit wiring, BLOCKING loop, G4 staging glob, resonance parser, dispatch prompt
    cli.py                # modify behavior, rollback stub, feedback error, genesis save
    error_handler.py      # import constants from state.py
    genesis.py            # escalation dispatch, modify prompt
    closure.py            # escalation dispatch
    revision_router.py    # _gate_passed removal
    dispatch_helper.py    # _gate_passed extraction, fail-closed, G1 optional filter
    context_assemble.py   # try/finally for store
    truth_index.py        # sorted() returns
    truth_embed.py        # rebuild log
    triggers.py           # total_chapters recompute, run_triggered_skills return check

tests/unit/pipeline/
    test_audit_layer.py
    test_chapter_loop.py
    test_chapter_loop_full.py
    test_cli.py
    test_error_handler.py
    test_machine.py
    test_state.py
    test_context_assemble.py
    test_truth_index.py
    test_truth_embed.py
    test_genesis.py
    test_closure.py
    test_dispatch_helper.py
    test_revision_router.py
    test_triggers.py
    test_root_cause_fixes.py  # new test file for cross-cutting fixes
```

---

## Phase 1: 正确性阻塞修复 (Tasks 1-8)

Dependency chain: Task 1 → Task 2 → Task 3 → Task 4. Tasks 5-8 independent.

### Task 1: A3 — genre-config 审计维度对齐

**Files:**
- Modify: `src/shenbi/pipeline/audit_layer.py:40-55` (GENRE_ACTIVATION_MATRIX + get_active_genre_audits)
- Test: `tests/unit/pipeline/test_audit_layer.py`

**Interfaces:**
- Consumes: `genre_config: Mapping[str, object]` (genre-config.json parsed)
- Produces: `GENRE_ACTIVATION_MATRIX` with camelCase keys matching real fixture; `get_active_genre_audits` reads `auditDimensions` top-level key

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_audit_layer.py — add to existing file

class TestGenreActivationMatrixRealFormat:
    """Tests that the activation matrix matches real genre-config.json format."""

    def test_reads_audit_dimensions_camel_case(self):
        """Real fixture uses auditDimensions (camelCase), not audit_dimensions."""
        gc = {"auditDimensions": {"sensitivity": True, "worldRules": True}}
        result = get_active_genre_audits(gc)
        assert "shenbi-review-sensitivity" in result
        assert "shenbi-review-world-rules" in result

    def test_motivation_activates_review(self):
        gc = {"auditDimensions": {"motivation": True}}
        result = get_active_genre_audits(gc)
        assert "shenbi-review-motivation" in result

    def test_dialogue_activates_review(self):
        gc = {"auditDimensions": {"dialogue": True}}
        result = get_active_genre_audits(gc)
        assert "shenbi-review-dialogue" in result

    def test_texture_activates_review(self):
        gc = {"auditDimensions": {"texture": True}}
        result = get_active_genre_audits(gc)
        assert "shenbi-review-texture" in result

    def test_era_dimension_supported(self):
        """era is a spec §6.2 dimension not yet in real fixture but supported."""
        gc = {"auditDimensions": {"era": True}}
        result = get_active_genre_audits(gc)
        assert "shenbi-review-era" in result

    def test_fanfic_dimension_supported(self):
        gc = {"auditDimensions": {"fanfic": True}}
        result = get_active_genre_audits(gc)
        assert "shenbi-review-fanfic" in result

    def test_core_circle_keys_not_in_genre_circle(self):
        """antiAi, character, pacing, continuity, foreshadowing are core circle."""
        gc = {"auditDimensions": {"antiAi": True, "character": True, "pacing": True}}
        result = get_active_genre_audits(gc)
        # These should NOT activate genre-circle skills
        assert "shenbi-review-anti-ai" not in result
        assert "shenbi-review-character" not in result
        assert "shenbi-review-pacing" not in result

    def test_empty_audit_dimensions_returns_empty(self):
        gc = {"auditDimensions": {}}
        assert get_active_genre_audits(gc) == []

    def test_missing_audit_dimensions_returns_empty(self):
        gc = {}
        assert get_active_genre_audits(gc) == []

    def test_snake_case_fallback_still_works(self):
        """Backward compat: if someone uses audit_dimensions (snake_case)."""
        gc = {"audit_dimensions": {"sensitivity": True}}
        result = get_active_genre_audits(gc)
        assert "shenbi-review-sensitivity" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_audit_layer.py::TestGenreActivationMatrixRealFormat -v`
Expected: FAIL — current matrix uses snake_case keys and reads `audit_dimensions`

- [ ] **Step 3: Implement the fix**

```python
# src/shenbi/pipeline/audit_layer.py — replace GENRE_ACTIVATION_MATRIX and get_active_genre_audits

# Maps genre-config.json ``auditDimensions`` keys to review skills.
# Keys match the real genre-config.json fixture produced by shenbi-genre-config
# (camelCase). Core-circle dimensions (antiAi, character, pacing, continuity,
# foreshadowing) are NOT here — they run as chapter_loop steps 10-16.
GENRE_ACTIVATION_MATRIX: dict[str, str] = {
    "sensitivity": "shenbi-review-sensitivity",
    "worldRules": "shenbi-review-world-rules",
    "motivation": "shenbi-review-motivation",
    "dialogue": "shenbi-review-dialogue",
    "texture": "shenbi-review-texture",
    # Spec §6.2 dimensions not yet in real fixture but supported for forward compat:
    "era": "shenbi-review-era",
    "fanfic": "shenbi-review-fanfic",
    "readerPull": "shenbi-review-reader-pull",
    "highpoint": "shenbi-review-highpoint",
}


def get_active_genre_audits(genre_config: Mapping[str, object]) -> list[str]:
    """Determine which genre-circle audits to run based on genre-config.json.

    Reads the ``auditDimensions`` sub-dict (camelCase, matching real fixture).
    Falls back to ``audit_dimensions`` (snake_case) for backward compat.
    Every key set to a truthy value maps (via :data:`GENRE_ACTIVATION_MATRIX`)
    to a review skill.
    """
    audit_dims = genre_config.get("auditDimensions")
    if audit_dims is None:
        audit_dims = genre_config.get("audit_dimensions", {})
    if not isinstance(audit_dims, dict):
        return []
    return sorted(
        skill
        for dim_key, skill in GENRE_ACTIVATION_MATRIX.items()
        if audit_dims.get(dim_key, False)
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_audit_layer.py -v`
Expected: PASS — all existing + new tests

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/audit_layer.py tests/unit/pipeline/test_audit_layer.py
git commit -m "fix: align genre-config activation matrix with real fixture format (A3)"
```

---

### Task 2: A8 — 审计 BLOCKING 即时停止 + genre 圈接线

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (replace TODO(W3T4) markers, add audit retry loop)
- Modify: `src/shenbi/pipeline/state.py` (add `audit_retry_count` to ChapterState)
- Test: `tests/unit/pipeline/test_chapter_loop.py`

**Interfaces:**
- Consumes: `run_audit_layer(project_dir, chapter, genre_config)` from `audit_layer.py` (Task 1)
- Consumes: `handle_audit_blocking(state, chapter)` from `error_handler.py`
- Produces: chapter_loop step 8 now calls audit layer; BLOCKING triggers step_index rollback

**Prerequisite:** Task 1 complete (genre-config matrix aligned).

- [ ] **Step 1: Add audit_retry_count to ChapterState**

```python
# src/shenbi/pipeline/state.py — in ChapterState dataclass, add field:
@dataclass
class ChapterState:
    steps_done: list[str] = field(default_factory=list)
    status: str = "pending"
    resonance_score: int | None = None
    audit_results: dict[str, Any] = field(default_factory=dict)
    revision_count: int = 0
    audit_retry_count: int = 0  # NEW: tracks audit BLOCKING revision attempts
```

Also update `to_dict` and `from_dict` for ChapterState to serialize this field.

- [ ] **Step 2: Write failing test for audit layer call**

```python
# tests/unit/pipeline/test_chapter_loop.py — add class

class TestAuditLayerWiring:
    """Tests that audit layer is called and BLOCKING findings trigger revision loop."""

    def test_audit_layer_called_after_core_circle(self, tmp_path, monkeypatch):
        """run_audit_layer is called after the last core-circle audit step."""
        # Setup: state at step 16 (last core-circle audit) complete
        # Mock run_audit_layer to return AuditResult(blocking_found=False)
        # Run one more step
        # Assert run_audit_layer was called
        pass  # Implement with real fixtures

    def test_blocking_finds_triggers_step_rollback(self, tmp_path, monkeypatch):
        """BLOCKING audit finding rolls step_index back to revision step."""
        # Setup: state at audit complete, mock audit_result.blocking_found=True
        # Run the audit step
        # Assert step_index rolled back to revision step index - 1
        # Assert audit_retry_count incremented
        pass

    def test_max_audit_retries_triggers_escalation(self, tmp_path, monkeypatch):
        """After max_audit_retries BLOCKING findings, escalation checkpoint is set."""
        # Setup: audit_retry_count = config.max_audit_retries - 1
        # Mock audit_result.blocking_found=True
        # Assert CheckpointType.ESCALATION is set
        pass

    def test_no_blocking_advances_normally(self, tmp_path, monkeypatch):
        """No BLOCKING findings → normal step advancement."""
        pass
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py::TestAuditLayerWiring -v`
Expected: FAIL — audit layer not wired

- [ ] **Step 4: Wire audit layer into chapter_loop**

Replace the `TODO(W3T4)` blocks in `chapter_loop.py` with actual audit layer calls. Key logic:

```python
# After last core-circle audit step (step 16):
if step.is_audit and step_idx == _LAST_AUDIT_IDX:
    from shenbi.pipeline.audit_layer import run_audit_layer

    gc_path = project_dir / "genre-config.json"
    gc: dict[str, object] = {}
    if gc_path.exists():
        gc = json.loads(gc_path.read_text(encoding="utf-8"))

    audit_result = run_audit_layer(project_dir, chapter, gc)

    # Store audit results for revision routing
    cs = state.chapter_loop.chapter_states[str(chapter)]
    cs.audit_results["blocking_found"] = audit_result.blocking_found
    cs.audit_results["issues"] = [i.model_dump() if hasattr(i, "model_dump") else i for i in audit_result.issues]

    if audit_result.blocking_found:
        from shenbi.pipeline.error_handler import handle_audit_blocking
        should_retry = handle_audit_blocking(state, chapter)
        if should_retry:
            # Step_index rollback: go back to revision step (step 18)
            # revision_step_index = index of ChapterStep with skill "shenbi-chapter-revision"
            _REVISION_STEP_IDX = next(
                i for i, s in enumerate(CHAPTER_STEPS) if s.skill == "shenbi-chapter-revision"
            )
            state.chapter_loop.step_index = _REVISION_STEP_IDX - 1
            log.info("audit_blocking_revision_loop", chapter=chapter,
                     retry=cs.audit_retry_count)
            return False  # don't advance, loop will re-run from revision step
        else:
            # Max retries exhausted → escalation (will be fully wired in Task 4)
            set_checkpoint(state, CheckpointType.ESCALATION, chapter=chapter,
                          artifact=f"audits/escalation-{chapter}-report.md")
            return True  # checkpoint raised
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py -v`
Expected: PASS

- [ ] **Step 6: Run full pipeline suite**

Run: `uv run pytest tests/unit/pipeline/ -v`
Expected: PASS, no regressions

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/state.py tests/unit/pipeline/test_chapter_loop.py
git commit -m "fix: wire audit layer into chapter_loop with BLOCKING revision loop (A8)"
```

---

### Task 3: A5 — error_handler 三函数接线

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (wire handle_scoring_failure, handle_state_settle_failure)
- Test: `tests/unit/pipeline/test_chapter_loop.py`, `tests/unit/pipeline/test_error_handler.py`

**Prerequisite:** Task 2 complete (audit wiring + handle_audit_blocking already called).

- [ ] **Step 1: Write failing tests**

```python
# Test that scoring failure exit codes are checked
class TestScoringFailureWiring:
    def test_exit_code_2_triggers_redispatch(self):
        """review-resonance returncode=2 → re-dispatch with G3 re-verify."""
        pass

    def test_exit_code_3_triggers_g4_first(self):
        """review-resonance returncode=3 → run G4 then re-dispatch."""
        pass

# Test that state-settling failure marks settling_failed
class TestStateSettleFailureWiring:
    def test_state_settle_failure_marks_settling_failed(self):
        """state-settling dispatch failure → status='settling_failed', checkpoint."""
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Wire scoring failure handling**

In `chapter_loop.py`, after review-resonance dispatch:
```python
if "review-resonance" in step.skill:
    result = dispatch_skill(...)  # existing
    if not result.success or result.returncode in (2, 3):
        from shenbi.pipeline.error_handler import handle_scoring_failure
        should_retry = handle_scoring_failure(state, result.returncode)
        if should_retry:
            # Re-dispatch (exit code 2 or 3)
            return False  # don't advance, retry this step
        else:
            return _handle_failure(state, step, chapter, "scoring")
```

- [ ] **Step 4: Wire state-settling failure handling**

In `chapter_loop.py`, for state-settling step:
```python
if "state-settling" in step.skill:
    result = dispatch_skill(...)
    if not result.success:
        from shenbi.pipeline.error_handler import handle_state_settle_failure
        handle_state_settle_failure(state, chapter)
        return True  # checkpoint set, pause for human
```

- [ ] **Step 5: Run tests, full suite, commit**

```bash
git commit -m "fix: wire scoring and state-settle failure handlers into chapter_loop (A5)"
```

---

### Task 4: A4 — escalation-review dispatch 接线

**Files:**
- Modify: `src/shenbi/pipeline/genesis.py`, `src/shenbi/pipeline/chapter_loop.py`, `src/shenbi/pipeline/closure.py`
- Test: corresponding test files

**Prerequisite:** Task 3 complete.

- [ ] **Step 1: Write failing test**

```python
def test_escalation_dispatched_before_checkpoint(tmp_path, monkeypatch):
    """When retries exhausted, dispatch_escalation runs before set_checkpoint."""
    # Mock dispatch_escalation to track call
    # Trigger max retries failure
    # Assert dispatch_escalation called BEFORE set_checkpoint
    pass
```

- [ ] **Step 2: Wire escalation dispatch**

In `_handle_failure` functions (genesis, chapter_loop, closure), when `handle_dispatch_failure` returns `False`:
```python
if not handle_dispatch_failure(state, skill, attempt):
    # A4: Dispatch escalation-review before checkpoint
    from shenbi.pipeline.revision_router import dispatch_escalation
    dispatch_escalation(state, project_dir, chapter)
    set_checkpoint(state, CheckpointType.ESCALATION, chapter=chapter,
                   artifact=f"audits/escalation-{chapter}-report.md")
    return True
```

- [ ] **Step 3: Run tests, full suite, commit**

```bash
git commit -m "fix: dispatch escalation-review before checkpoint on retry exhaustion (A4)"
```

---

### Task 5: A1 — total_chapters 动态重算

**Files:**
- Modify: `src/shenbi/pipeline/triggers.py`
- Test: `tests/unit/pipeline/test_triggers.py`

**Independent of Tasks 1-4.**

- [ ] **Step 1: Write failing test**

```python
def test_total_chapters_recomputed_after_volume_expansion(tmp_path):
    """After volume boundary expansion, total_chapters is recalculated."""
    # Create volume_map.md with 3 volumes (5+5+3 = 13 chapters)
    # Set novel.json total_chapters = 10 (original estimate)
    # Run run_triggered_skills with volume_boundary
    # Assert novel.json total_chapters updated to 13
    pass
```

- [ ] **Step 2: Implement recompute**

In `triggers.py`, after volume expansion steps complete in `run_triggered_skills`:
```python
# After expansion, recompute total_chapters
volume_map = project_dir / "outline" / "volume_map.md"
if volume_map.exists():
    new_total = _count_total_chapters(volume_map.read_text(encoding="utf-8"))
    novel_json = project_dir / "novel.json"
    if novel_json.exists():
        data = json.loads(novel_json.read_text(encoding="utf-8"))
        old_total = data.get("total_chapters")
        if old_total != new_total:
            data["total_chapters"] = new_total
            safe_write(novel_json, json.dumps(data, ensure_ascii=False, indent=2))
            log.info("total_chapters_updated", old=old_total, new=new_total)
```

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "fix: recompute total_chapters after volume boundary expansion (A1)"
```

---

### Task 6: A2 — resonance 评分解析器

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (add `_parse_resonance_score` and call after review-resonance)
- Test: `tests/unit/pipeline/test_chapter_loop.py`

**Independent.**

- [ ] **Step 1: Write failing test**

```python
def test_resonance_score_extracted_from_report(tmp_path):
    """Resonance score is parsed from audits/chapter-N-resonance.md."""
    # Create a resonance report with score 72
    report = tmp_path / "audits" / "chapter-1-resonance.md"
    report.parent.mkdir(parents=True)
    report.write_text("共振分数: 72\n")
    score = _parse_resonance_score(report)
    assert score == 72

def test_resonance_score_none_on_missing_file(tmp_path):
    assert _parse_resonance_score(tmp_path / "nonexistent.md") is None
```

- [ ] **Step 2: Implement parser**

```python
_RESONANCE_PATTERNS = [
    re.compile(r"共振分数[:\s]*(\d+)"),
    re.compile(r"resonance[_\s]*score[:\s]*(\d+)", re.IGNORECASE),
]

def _parse_resonance_score(report_path: Path) -> int | None:
    if not report_path.exists():
        return None
    text = report_path.read_text(encoding="utf-8")
    for pattern in _RESONANCE_PATTERNS:
        m = pattern.search(text)
        if m:
            return int(m.group(1))
    return None
```

Call it after review-resonance dispatch completes successfully:
```python
cs.resonance_score = _parse_resonance_score(project_dir / "audits" / f"chapter-{chapter}-resonance.md")
```

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "fix: parse resonance score from review report (A2)"
```

---

### Task 7: A6 — modify 决策行为修正

**Files:**
- Modify: `src/shenbi/pipeline/state.py` (+modify_feedback, +modify_pending_step fields)
- Modify: `src/shenbi/pipeline/cli.py` (cmd_review MODIFY branch)
- Modify: `src/shenbi/pipeline/chapter_loop.py` (dispatch prompt feedback injection)
- Modify: `src/shenbi/pipeline/genesis.py` (dispatch prompt feedback injection)
- Test: `tests/unit/pipeline/test_cli.py`, `tests/unit/pipeline/test_state.py`

**Independent.**

- [ ] **Step 1: Add state fields**

```python
# state.py PipelineState:
modify_feedback: str | None = None
modify_pending_step: int | None = None
needs_truth_sync: bool = False
needs_truth_sync_files: list[str] = field(default_factory=list)
```

Update `to_dict` / `from_dict`.

- [ ] **Step 2: Write failing test**

```python
def test_modify_does_not_commit_staging(tmp_path):
    """MODIFY clears staging and sets modify_pending, does NOT commit."""
    # Setup checkpoint with staging content
    # Call cmd_review with modify + feedback
    # Assert staging cleared (not committed)
    # Assert state.modify_feedback set
    # Assert state.modify_pending_step set to checkpoint step
    pass

def test_modify_feedback_injected_into_dispatch(tmp_path, monkeypatch):
    """On resume after modify, feedback is injected into dispatch prompt."""
    pass
```

- [ ] **Step 3: Fix cmd_review MODIFY branch**

```python
# cli.py cmd_review:
if decision == ReviewDecision.APPROVE:
    _commit_staging_for_checkpoint(project_dir, cp)
elif decision == ReviewDecision.MODIFY:
    # A6: Do NOT commit staging. Clear it, set modify_pending.
    from shenbi.pipeline.checkpoint import clear_staging
    clear_staging(project_dir)
    state.modify_feedback = feedback
    state.modify_pending_step = _step_number_for_checkpoint(cp)
elif decision == ReviewDecision.REJECT:
    # B5: Reset step_index for redo
    clear_staging(project_dir)
    state.chapter_loop.step_index = _step_index_for_checkpoint(cp)
```

- [ ] **Step 4: Add feedback injection in dispatch prompt**

In chapter_loop and genesis dispatch:
```python
prompt = f"Execute {step.skill}. Project dir: {project_dir}"
if state.modify_feedback and state.modify_pending_step == step.number:
    prompt += f"\n\n## Reviewer Feedback\n{state.modify_feedback}"
    state.modify_feedback = None
    state.modify_pending_step = None
```

- [ ] **Step 5: Run tests, commit**

```bash
git commit -m "fix: modify decision clears staging and re-dispatches with feedback (A6+B5)"
```

---

### Task 8: A7 — state-settling G4 目录验证

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`
- Test: `tests/unit/pipeline/test_chapter_loop.py`

**Independent.**

- [ ] **Step 1: Write failing test**

```python
def test_state_settle_g4_validates_staging_truth_glob(tmp_path, monkeypatch):
    """State-settling G4 validates staging/truth/*.md, not empty list."""
    # Create staging/truth/character_matrix.md, staging/truth/current_state.md
    # Mock run_gate_g4 to capture args
    # Run state-settling step
    # Assert run_gate_g4 called with list of staging/truth/*.md paths (not empty)
    pass
```

- [ ] **Step 2: Implement glob validation**

```python
# In chapter_loop, after state-settling dispatch:
if "state-settling" in step.skill:
    staging_truth = project_dir / "staging" / "truth"
    if staging_truth.exists():
        truth_files = sorted(str(f.relative_to(project_dir)) for f in staging_truth.glob("*.md"))
        if truth_files:
            g4_result = run_gate_g4(step.skill, truth_files, project_dir)
```

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "fix: state-settling G4 validates staging/truth glob (A7)"
```

---

## Phase 2: 补充正确性 (Tasks 9-10)

### Task 9: E1-E3+E5 — 小修复批次

**Files:**
- Modify: `src/shenbi/pipeline/context_assemble.py` (E1: try/finally for store)
- Modify: `src/shenbi/pipeline/machine.py` (E2: clear_checkpoint guard)
- Modify: `src/shenbi/pipeline/cli.py` (E3: feedback FileNotFoundError)
- Modify: `src/shenbi/pipeline/truth_index.py` (E5: sorted returns)
- Test: corresponding test files

- [ ] **Step 1: Write failing tests for all 4 fixes**

```python
# E1: store.close in finally
def test_route_b_store_closed_on_exception(monkeypatch):
    """Even if search_cosine raises, store.close() is called."""
    pass

# E2: clear_checkpoint idempotent
def test_clear_checkpoint_already_none_is_noop():
    state = PipelineState.default("/tmp")
    state.pending_checkpoint = CheckpointData(type=CheckpointType.NONE)
    clear_checkpoint(state, ReviewDecision.APPROVE)
    # Should NOT append to history
    assert len(state.checkpoint_history) == 0

# E3: feedback file not found
def test_feedback_file_not_found_returns_error(tmp_path):
    """Missing feedback file returns error envelope, not traceback."""
    pass

# E5: sorted returns
def test_extract_entities_sorted():
    """Characters/rules lists are sorted."""
    pass
```

- [ ] **Step 2: Implement all 4 fixes**

E1 — wrap store in try/finally:
```python
store = EmbeddingStore(db_path)
try:
    results = store.search_cosine(query_vec, top_k=5)
finally:
    store.close()
```

E2 — guard in clear_checkpoint:
```python
def clear_checkpoint(state: PipelineState, decision: ReviewDecision) -> None:
    cp = state.pending_checkpoint
    if cp.type == CheckpointType.NONE:
        return
    # ... rest unchanged
```

E3 — wrap feedback read:
```python
if args.feedback:
    try:
        feedback = Path(args.feedback).read_text(encoding="utf-8")
    except FileNotFoundError:
        emit_json({"status": CommandStatus.ERROR, "message": f"feedback file not found: {args.feedback}"})
        return 1
```

E5 — sorted returns in extract_entities_from_plan:
```python
return {
    "characters": sorted(char_hits),
    "hooks": sorted(hook_hits),
    "rules": sorted(rule_hits),
}
```

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "fix: SQLite leak + clear_checkpoint guard + feedback error + sorted returns (E1-E3,E5)"
```

---

### Task 10: E4 — cmd_rollback stub 修复

**Files:**
- Modify: `src/shenbi/pipeline/cli.py`
- Test: `tests/unit/pipeline/test_cli.py`

- [ ] **Step 1: Write failing test**

```python
def test_rollback_returns_nonzero_for_stub(tmp_path):
    """Rollback stub returns exit code 1 (not 0)."""
    pass

def test_rollback_validates_project_exists(tmp_path):
    """Rollback on missing project returns error."""
    pass
```

- [ ] **Step 2: Fix rollback stub**

```python
def cmd_rollback(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir)
    try:
        with WriteLock(project_dir):
            load_state(project_dir)  # validate project exists
    except FileNotFoundError:
        emit_json({"status": CommandStatus.ERROR, "message": "project not found"})
        return 1
    log.info("rollback_requested", project_dir=str(project_dir), chapter=args.chapter)
    emit_json({"status": "not_implemented", "message": "Rollback not yet implemented"})
    return 1  # non-zero: this is a stub
```

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "fix: rollback stub returns non-zero + validates project (E4)"
```

---

## Phase 3: 健壮性增强 (Tasks 11-13)

### Task 11: B1+B4 — G1 可选过滤 + fail-closed

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`
- Test: `tests/unit/pipeline/test_dispatch_helper.py`

- [ ] **Step 1: Write failing tests**

```python
def test_optional_reads_filtered_before_dispatch():
    """Reads containing N template or marked optional are filtered if not present."""
    pass

def test_requires_independent_fail_closed_for_scoring():
    """For known scoring skills, requires_independent returns True on error."""
    pass
```

- [ ] **Step 2: Implement**

B1: Add `_OPTIONAL_READ_PATTERNS` set and filter in dispatch_skill before subprocess call.
B4: For known scoring skills, catch exceptions and return `True` (fail-closed).

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "fix: G1 optional read filtering + requires_independent fail-closed (B1+B4)"
```

---

### Task 12: B2 — Resume checksum 校验 + B5 reject step reset

**Files:**
- Modify: `src/shenbi/pipeline/cli.py` (cmd_resume checksum check)
- Test: `tests/unit/pipeline/test_cli.py`

Note: B5 (reject step_index reset) was partially implemented in Task 7. This task completes it for non-modify rejects.

- [ ] **Step 1: Write failing test**

```python
def test_resume_checksum_mismatch_triggers_truth_sync(tmp_path):
    """Resume with corrupted truth files triggers truth-sync warning."""
    pass

def test_reject_resets_step_index(tmp_path):
    """Reject checkpoint resets step_index to redo the step."""
    pass
```

- [ ] **Step 2: Implement checksum check in cmd_resume**

```python
# In cmd_resume, after load_state:
if state.last_snapshot and "checksums" in state.last_snapshot:
    mismatches = _verify_truth_checksums(project_dir, state.last_snapshot["checksums"])
    if mismatches:
        state.needs_truth_sync = True
        state.needs_truth_sync_files = mismatches
        save_state(project_dir, state)
        emit_json({"status": "blocked", "message": "truth_sync_needed",
                   "files": mismatches})
        return 1
```

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "fix: resume checksum verification + reject step reset (B2+B5)"
```

---

### Task 13: B3 — truth-sync 传播标记

**Files:**
- Modify: `src/shenbi/pipeline/state.py` (already added in Task 7)
- Modify: `src/shenbi/pipeline/cli.py` (cmd_status shows warning)

- [ ] **Step 1: Write failing test**

```python
def test_status_shows_truth_sync_warning(tmp_path):
    """cmd_status shows truth_sync_needed when flag is set."""
    pass
```

- [ ] **Step 2: Add warning to cmd_status output**

```python
# In cmd_status, after building status dict:
if state.needs_truth_sync:
    status["warnings"] = ["truth_sync_needed: " + ", ".join(state.needs_truth_sync_files)]
```

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "fix: truth-sync propagation marking on modify (B3)"
```

---

## Phase 4: 测试补全 (Tasks 14-17)

### Task 14: C1+C2 — CLI 冒烟 + dispatch chain 集成测试

**Files:**
- Test: `tests/unit/pipeline/test_root_cause_fixes.py` (new file)

- [ ] **Step 1: Write CLI smoke tests**

```python
class TestCLISmokeTests:
    def test_truth_index_main_smoke(self, tmp_path):
        """pipeline-truth-index main() with rebuild returns 0."""
        from shenbi.pipeline.truth_index import main
        # Setup minimal project, call main(["rebuild", ...]), assert exit 0

    def test_truth_embed_main_smoke(self, tmp_path):
        from shenbi.pipeline.truth_embed import main
        # call main(["query", ...]), assert exit 0

    def test_context_assemble_main_smoke(self, tmp_path):
        from shenbi.pipeline.context_assemble import main
        # call main([...]), assert exit 0

class TestDispatchChainIntegration:
    def test_dispatch_skill_returns_success(self, tmp_path):
        """dispatch_skill end-to-end against a minimal fixture skill."""
        # Use a real (non-mocked) subprocess against a tiny test skill
        # Assert DispatchResult.success == True
        pass
```

- [ ] **Step 2: Run tests, commit**

```bash
git commit -m "test: add CLI smoke tests + dispatch chain integration test (C1+C2)"
```

---

### Task 15: C3+C4+C5 — Route B 向量 + closure + cmd_next 测试

**Files:**
- Test: `tests/unit/pipeline/test_root_cause_fixes.py`

- [ ] **Step 1: Write tests**

C3: Fix Route B test to use 1024-dim vectors (or use mock model with matching dim).
C4: Integration test: book-closure approve → resume → snapshot dispatch → completed.
C5: Test cmd_next behavior when checkpoint pending vs cleared.

- [ ] **Step 2: Run tests, commit**

```bash
git commit -m "test: fix Route B vector dim + closure e2e + cmd_next behavior (C3+C4+C5)"
```

---

### Task 16: C6 — 审计 BLOCKING revision 闭环端到端测试

**Prerequisite:** Task 2 complete.

**Files:**
- Test: `tests/unit/pipeline/test_root_cause_fixes.py`

- [ ] **Step 1: Write comprehensive e2e test**

```python
class TestAuditBlockingRevisionLoop:
    def test_blocking_to_revision_to_pass(self):
        """BLOCKING → revision → re-audit → pass."""
        pass

    def test_blocking_to_revision_to_blocking_to_pass(self):
        """BLOCKING → revision → still BLOCKING → revision → pass."""
        pass

    def test_max_retries_to_escalation(self):
        """BLOCKING × max_audit_retries → escalation checkpoint."""
        pass
```

- [ ] **Step 2: Run tests, commit**

```bash
git commit -m "test: audit BLOCKING revision loop end-to-end (C6)"
```

---

### Task 17: F1-F7 — 序列化往返 + 覆盖率补全

**Files:**
- Test: `tests/unit/pipeline/test_state.py`, `tests/unit/pipeline/test_machine.py`, `tests/unit/pipeline/test_genesis.py`

- [ ] **Step 1: Write all 7 test additions**

F1: ChapterState round-trip with populated chapter_states.
F2: Checkpoint options/context round-trip assertions.
F3: Full 12-field PipelineConfig round-trip.
F4: Rename test_save_is_atomic → test_save_writes_valid_json.
F5: embed_and_store mock model success path.
F6: G4 assert_called_with argument verification.
F7: genesis phase transition + save_state before orchestration.

- [ ] **Step 2: Run tests, commit**

```bash
git commit -m "test: complete serialization round-trips + coverage gaps (F1-F7)"
```

---

## Phase 5: 代码清理 + 文档 (Tasks 18-20)

### Task 18: D1+D2+G1 — _gate_passed 提取 + 常量连接 + 类型一致

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (add `gate_passed()` shared helper)
- Modify: `src/shenbi/pipeline/state.py` (add `DEFAULT_MAX_DISPATCH_RETRIES`/`DEFAULT_MAX_AUDIT_RETRIES`)
- Modify: `src/shenbi/pipeline/error_handler.py` (import from state.py)
- Modify: `src/shenbi/pipeline/chapter_loop.py`, `audit_layer.py`, `closure.py` (use shared `gate_passed()`)
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (G1: `GateStatus.FAIL.value` for type consistency)

- [ ] **Step 1: Write tests verifying shared gate_passed**

- [ ] **Step 2: Implement extraction + constant connection**

- [ ] **Step 3: Run full suite, commit**

```bash
git commit -m "refactor: extract gate_passed + connect retry constants + type consistency (D1+D2+G1)"
```

---

### Task 19: D3+D4+G2-G7 — 代码质量批次

**Files:**
- Modify: `src/shenbi/pipeline/audit_layer.py` (D3: comments on dead entries)
- Modify: `src/shenbi/pipeline/chapter_loop.py` (G2: conditional resolve G4, G3: staging_path(), D4: prompt comment)
- Modify: `src/shenbi/pipeline/truth_embed.py` (G4: rebuild log)
- Modify: `src/shenbi/pipeline/truth_index.py` (G5: update alias)
- Modify: `src/shenbi/pipeline/cli.py` (G6: remove redundant save)

- [ ] **Step 1: Make all changes**

- [ ] **Step 2: Run full suite, commit**

```bash
git commit -m "refactor: dead entry comments + G2/G3 fixes + rebuild log + update alias (D3+D4+G2-G7)"
```

---

### Task 20: H1+H2+I1-I3 — 文档与流程修复

**Files:**
- Modify: `docs/superpowers/plans/2026-07-02-pipeline-coverage-matrix.md` (H1: update to 20/20)
- Modify: `src/shenbi/pipeline/cli.py` (H2: rollback stub message)
- Modify: `src/shenbi/pipeline/state.py` (I2: PipelineState docstring for closure fields)
- Modify: `.superpowers/sdd/novel-pipeline/progress.md` (I1: clean stale TODOs)

- [ ] **Step 1: Make all changes**

- [ ] **Step 2: Commit**

```bash
git commit -m "docs: update coverage matrix + cleanup ledger + state docstring (H1+H2+I1-I3)"
```

---

## Final Task: 批判性审核

After all 20 tasks complete, dispatch a final whole-branch code review using `superpowers:requesting-code-review`.

Review package: `scripts/review-package MERGE_BASE HEAD`

Focus areas:
1. State consistency across all transition paths
2. Flow correctness (genesis → chapter-loop → closure)
3. Error recovery completeness
4. Concurrency safety
5. Cross-module interface consistency

**Pass criteria:** No Critical or Important findings.
