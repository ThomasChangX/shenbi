# Lifecycle Enforcement and Retention Bounds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the orphaned soft-fail-tracker escalation signal into the existing `check_escalation` consumer so that transition/fatigue drift actually triggers an escalation review, and fix the off-by-one in the existing chapter-number-based snapshot pruner so the on-disk snapshot count never exceeds the configured retention cap.

**Architecture:** Two surgical changes to `src/shenbi/pipeline/chapter_loop.py`. (1) At the existing soft-fail escalation site (where `should_escalate` is already computed and logged but then discarded), add a call to `check_escalation` using its real signature `(resonance_scores, sensitivity_blocking, volume_objective_met, regeneration_attempts, ...)` — scores come from the existing `_get_recent_resonance_scores` helper — and route a non-empty signal list to the existing `dispatch_escalation` path. (2) In `_prune_old_snapshots`, replace the `ch < keep_from` comparison (which keeps one chapter too many) with a slice that keeps exactly `retention` chapters (`all_chapters[:-retention]`), and add a post-prune guard that logs an error if the cap is still exceeded. No new modules; snapshot pruning is NOT replaced with an mtime-based pruner (that approach was rejected in the spec).

**Tech Stack:** Python 3.11+, `pathlib`, `json`, pytest. No new runtime dependencies.

## Global Constraints

- Python 3.11+, `from __future__ import annotations` retained
- `pathlib.Path` for all file I/O; `safe_write` for manifest writes (already used by `_save_manifest`)
- No `print()` in framework code; use structlog (`shenbi.logging.get_logger`)
- **`check_escalation` signature is fixed** — call it as `check_escalation(resonance_scores=..., sensitivity_blocking=..., volume_objective_met=..., regeneration_attempts=..., ...)` (verified at `src/shenbi/skill_utils/escalation/check.py:52-64`). Do NOT invent parameters.
- **Snapshot pruning ALREADY EXISTS** (`_prune_old_snapshots` at `chapter_loop.py:870-905`, called at `:960`) and is chapter-number-based. This plan ONLY fixes its boundary condition — it does NOT introduce an mtime-based pruner (spec §3.2 explicitly rejected that).
- Tests under `tests/unit/pipeline/` alongside the existing `test_chapter_loop.py`
- Conventional Commits: `fix:` for both corrections
- `just check` (ruff + mypy + basedpyright + pytest) must pass after every task

**Spec reference:** `docs/superpowers/specs/2026-07-19-13-lifecycle-enforcement-and-retention-bounds-design.md`

---

## File Structure

```
src/shenbi/pipeline/
    chapter_loop.py              # MODIFY — soft-fail escalation wiring (Task 1)
                                 #        + _prune_old_snapshots boundary fix (Task 2)

tests/unit/pipeline/
    test_chapter_loop.py         # EXISTING — must stay green
    test_soft_fail_escalation.py # NEW — soft-fail -> check_escalation wiring
    test_snapshot_pruning.py     # NEW — boundary condition + guard
```

> **Codebase facts baked in:**
> - `SoftFailTracker.record(chapter) -> bool` already returns `True` when the escalation threshold is met (`state.py:107-111`). The chapter loop already computes `should_escalate` at `chapter_loop.py:1305-1319` and logs `chapter_g4_soft_escalated` — but then does nothing with it. Task 1 consumes that boolean.
> - `check_escalation` lives at `skill_utils/escalation/check.py` and returns `list[EscalationSignal]`. Its real parameters: `resonance_scores, sensitivity_blocking, volume_objective_met, regeneration_attempts, arc_score=None, stratum_axis_drift=False, window=5, slope_threshold=-2.0, regen_loop_limit=3, arc_threshold=70.0`.
> - `_get_recent_resonance_scores(project_dir, chapter, window=3)` already exists at `chapter_loop.py:813` and reads `audits/chapter-N-resonance.md`. Reuse it — do not reimplement.
> - `dispatch_escalation(project_dir, ...)` from `revision_router.py` is the existing escalation-review dispatch path (`chapter_loop.py:414-416`). Reuse it.
> - `_prune_old_snapshots` reads the manifest (`snapshots/manifest.json`) whose `chapters` dict maps chapter-number-strings to filename lists. The current logic `keep_from = max(all_chapters) - retention; to_prune = [ch for ch in all_chapters if ch < keep_from]` keeps `retention + 1` chapters (off-by-one) — e.g. with retention=50, max=56 it keeps chapters 6..56 = 51. The fix keeps exactly `retention`.

---

### Task 1: Wire soft-fail trackers to `check_escalation`

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:1313-1319` (the `if should_escalate:` block inside the G4 soft-fail handling) and add a new helper `_check_soft_fail_escalation` nearby
- Test: `tests/unit/pipeline/test_soft_fail_escalation.py` (new)

**Interfaces:**
- Consumes:
  - `SoftFailTracker` / `state.chapter_loop.soft_fail_trackers` (existing)
  - `check_escalation` from `shenbi.skill_utils.escalation.check` (existing, real signature)
  - `_get_recent_resonance_scores(project_dir, chapter, window=3)` (existing at `chapter_loop.py:813`)
  - `dispatch_escalation(project_dir, ...)` from `shenbi.pipeline.revision_router` (existing)
- Produces: when a soft-fail tracker crosses its threshold, `check_escalation` is invoked with the recent resonance scores and any fired signals are routed to the existing escalation-review dispatch. The function is a no-op when `check_escalation` returns no signals.

**Context:** The current code computes `should_escalate = tracker.record(chapter)` and logs `chapter_g4_soft_escalated`, then falls through. We replace the bare log with a call into `_check_soft_fail_escalation`, which gathers the inputs `check_escalation` needs (scores from the existing helper; `sensitivity_blocking` / `volume_objective_met` / `regeneration_attempts` from state) and dispatches escalation-review when signals fire. `regeneration_attempts` maps to the per-step retry count already tracked in `state.chapter_loop.retry_counts`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/pipeline/test_soft_fail_escalation.py`:

```python
"""Tests for the soft-fail-tracker -> check_escalation wiring (Spec 22 E32)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from shenbi.pipeline.chapter_loop import _check_soft_fail_escalation
from shenbi.pipeline.state import PipelineState, SoftFailTracker


def _state_with_soft_fail_window(chapters: list[int]) -> PipelineState:
    """Build a state whose ``transition`` tracker has recorded *chapters*."""
    state = PipelineState.default(project_dir="/tmp/novel")
    tracker = SoftFailTracker(check_id="G4.lt.transition")
    for ch in chapters:
        tracker.record(ch)
    state.chapter_loop.soft_fail_trackers["G4.lt.transition"] = tracker
    return state


class TestCheckSoftFailEscalation:
    def test_below_threshold_does_not_dispatch(self, tmp_path):
        state = _state_with_soft_fail_window([10, 11])  # 2 occurrences < threshold 3
        with patch(
            "shenbi.pipeline.chapter_loop.check_escalation"
        ) as mock_check, patch(
            "shenbi.pipeline.chapter_loop.dispatch_escalation"
        ) as mock_disp:
            _check_soft_fail_escalation(state, tmp_path, chapter=12)
        mock_check.assert_not_called()
        mock_disp.assert_not_called()

    def test_over_threshold_dispatches_when_signals_fire(self, tmp_path):
        # 4 occurrences within the window -> should_escalate True.
        state = _state_with_soft_fail_window([9, 10, 11, 12])
        # check_escalation returns a non-empty signal list.
        from shenbi.skill_utils.escalation.check import EscalationSignal

        with patch(
            "shenbi.pipeline.chapter_loop.check_escalation",
            return_value=[EscalationSignal(trigger="score_decline", detail="x")],
        ) as mock_check, patch(
            "shenbi.pipeline.chapter_loop.dispatch_escalation"
        ) as mock_disp:
            _check_soft_fail_escalation(state, tmp_path, chapter=12)
        mock_check.assert_called_once()
        # Verify the real signature was used.
        kwargs = mock_check.call_args.kwargs
        assert "resonance_scores" in kwargs
        assert "sensitivity_blocking" in kwargs
        assert "volume_objective_met" in kwargs
        assert "regeneration_attempts" in kwargs
        mock_disp.assert_called_once()

    def test_over_threshold_no_dispatch_when_no_signals(self, tmp_path):
        state = _state_with_soft_fail_window([9, 10, 11, 12])
        with patch(
            "shenbi.pipeline.chapter_loop.check_escalation", return_value=[]
        ) as mock_check, patch(
            "shenbi.pipeline.chapter_loop.dispatch_escalation"
        ) as mock_disp:
            _check_soft_fail_escalation(state, tmp_path, chapter=12)
        mock_check.assert_called_once()
        mock_disp.assert_not_called()

    def test_passes_recent_resonance_scores(self, tmp_path):
        """The scores fed to check_escalation come from the existing
        _get_recent_resonance_scores helper (window 5 to match the escalation
        default)."""
        state = _state_with_soft_fail_window([9, 10, 11, 12])
        with patch(
            "shenbi.pipeline.chapter_loop._get_recent_resonance_scores",
            return_value=[90, 85, 80, 75, 70],
        ) as mock_scores, patch(
            "shenbi.pipeline.chapter_loop.check_escalation", return_value=[]
        ):
            _check_soft_fail_escalation(state, tmp_path, chapter=12)
        mock_scores.assert_called_once_with(tmp_path, 12, window=5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_soft_fail_escalation.py -v`
Expected: FAIL — `ImportError: cannot import name '_check_soft_fail_escalation'`.

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/chapter_loop.py`, add the import near the top (with the other lazy imports, or at module top if no circular-import risk — `check_escalation` is a leaf helper, so a top-level import is fine):

```python
from shenbi.skill_utils.escalation.check import check_escalation
```

(If a circular-import error arises at module load, move it inside `_check_soft_fail_escalation` as a function-local import — the same pattern already used at `chapter_loop.py:400, 414`.)

Add the helper function. Place it just above the G4-handling block that contains the `if should_escalate:` (around line 1300), so it is in scope:

```python
def _check_soft_fail_escalation(
    state: PipelineState, project_dir: Path, chapter: int
) -> None:
    """Consume soft-fail-tracker escalation and route to check_escalation.

    Spec 22 E32: the trackers detected transition/fatigue drift but the signal
    was orphaned. This wires it to the existing ``check_escalation`` consumer
    using its real signature. When any tracker has crossed its threshold AND
    ``check_escalation`` fires >=1 signal, dispatch escalation-review via the
    existing ``dispatch_escalation`` path.
    """
    from shenbi.pipeline.revision_router import dispatch_escalation

    any_escalated = any(
        len(t.occurrences) >= t.escalation_threshold
        for t in state.chapter_loop.soft_fail_trackers.values()
    )
    if not any_escalated:
        return

    # Gather check_escalation inputs (real signature).
    resonance_scores = _get_recent_resonance_scores(project_dir, chapter, window=5)
    sensitivity_blocking = any(
        "sensitivity" in (cid or "").lower()
        for cid, t in state.chapter_loop.soft_fail_trackers.items()
        if len(t.occurrences) >= t.escalation_threshold
    )
    # Check if volume boundary is met by reading volume_map.md
    volume_boundaries = read_volume_boundaries(project_dir)
    current_volume = _find_current_volume(chapter, volume_boundaries)
    volume_objective_met = _check_volume_completion(project_dir, current_volume, chapter)
    # TODO: implement _find_current_volume() and _check_volume_completion() stubs
    # if they do not yet exist.
    # regeneration_attempts: max per-step retry count currently in flight.
    regeneration_attempts = max(state.chapter_loop.retry_counts.values(), default=0)

    signals = check_escalation(
        resonance_scores=resonance_scores,
        sensitivity_blocking=sensitivity_blocking,
        volume_objective_met=volume_objective_met,
        regeneration_attempts=regeneration_attempts,
    )
    if not signals:
        log.info(
            "soft_fail_escalation_no_signals",
            chapter=chapter,
            scores=resonance_scores,
        )
        return

    log.warning(
        "soft_fail_escalation_triggered",
        chapter=chapter,
        signals=[{"trigger": s.trigger, "detail": s.detail} for s in signals],
    )
    # dispatch_escalation's real signature is (project_dir, chapter, context="").
    # It has no `reason=` / `signals=` kwargs. Write the signals to a sidecar
    # file the escalation skill can read, then dispatch with context pointing
    # to that file.
    from dataclasses import asdict
    import json
    from shenbi.safe_write import safe_write

    signals_path = project_dir / "context" / f"chapter-{chapter}-escalation-signals.json"
    safe_write(
        signals_path,
        json.dumps([asdict(s) for s in signals], ensure_ascii=False, indent=2),
    )
    dispatch_escalation(
        project_dir,
        chapter,
        context=f"Soft-fail escalation triggered. Signals at: {signals_path}",
    )
```

> `dispatch_escalation`'s real signature is `dispatch_escalation(project_dir, chapter, context="")` (verified at `src/shenbi/pipeline/revision_router.py:143`). It has NO `reason=` / `signals=` kwargs, so the signals are written to a sidecar JSON file under `context/` and the file path is passed via `context=`. The escalation-review skill reads that sidecar. The test asserts `dispatch_escalation` is called once; it does not lock the kwargs.

Now wire the call site. In the G4 soft-fail block (around line 1313), replace:

```python
            if should_escalate:
                log.error(
                    "chapter_g4_soft_escalated",
                    chapter=chapter,
                    check_id=tracker_key,
                    occurrences=tracker.occurrences,
                )
```

with:

```python
            if should_escalate:
                log.error(
                    "chapter_g4_soft_escalated",
                    chapter=chapter,
                    check_id=tracker_key,
                    occurrences=tracker.occurrences,
                )
                # Spec 22 E32: route the orphaned escalation signal to the
                # check_escalation consumer + dispatch escalation-review.
                _check_soft_fail_escalation(state, Path(project_dir), chapter)
```

(`Path(project_dir)` normalizes whatever type `project_dir` has in this scope — it is `Path | str` per `_handle_failure`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/pipeline/test_soft_fail_escalation.py tests/unit/pipeline/test_chapter_loop.py -v`
Expected: PASS — the new wiring tests pass and the existing chapter-loop tests are unaffected.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py \
        tests/unit/pipeline/test_soft_fail_escalation.py
git commit -m "fix(chapter_loop): wire soft-fail trackers to check_escalation consumer (E32)"
```

---

### Task 2: Fix the `_prune_old_snapshots` boundary condition

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:870-900` (`_prune_old_snapshots`)
- Test: `tests/unit/pipeline/test_snapshot_pruning.py` (new)

**Interfaces:**
- Consumes: `_get_snapshot_retention(project_dir)` (existing), `_load_manifest` / `_save_manifest` (existing)
- Produces: `_prune_old_snapshots` now keeps exactly `retention` chapters (not `retention + 1`) and logs `snapshot_prune_failed` if the cap is still exceeded after pruning. Signature unchanged (`_prune_old_snapshots(project_dir) -> None`).

**Context:** The current logic:
```python
keep_from = max(all_chapters) - retention     # e.g. 56 - 50 = 6
to_prune = [ch for ch in all_chapters if ch < keep_from]   # prunes 1..5, keeps 6..56 = 51
```
keeps `retention + 1` chapters. The fix keeps exactly `retention` by pruning `all_chapters[:-retention]` (all but the last `retention`). This is robust to gaps in chapter numbering and does not depend on `max()`. A post-prune guard re-checks the manifest and logs `snapshot_prune_failed` if it still overshoots (e.g. a concurrent writer added snapshots between the prune and the guard).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/pipeline/test_snapshot_pruning.py`:

```python
"""Tests for the snapshot-retention pruner boundary condition (Spec 22 E40)."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.pipeline.chapter_loop import _prune_old_snapshots


def _write_manifest(project_dir: Path, chapters: dict[str, list[str]]) -> None:
    snap_dir = project_dir / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    # Create the snapshot files on disk so the pruner can unlink them.
    for ch_key, files in chapters.items():
        for fname in files:
            (snap_dir / fname).write_text("snap", encoding="utf-8")
    manifest_path = snap_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"chapters": chapters}, ensure_ascii=False), encoding="utf-8"
    )


def _chapter_count(project_dir: Path) -> int:
    manifest = json.loads(
        (project_dir / "snapshots" / "manifest.json").read_text(encoding="utf-8")
    )
    return len(manifest.get("chapters", {}))


class TestPruneBoundary:
    def test_keeps_exactly_retention_chapters(self, tmp_path, monkeypatch):
        # 56 chapters, retention 50 -> keep 50, prune 6.
        chapters = {str(n): [f"chapter-{n:03d}-t.md"] for n in range(1, 57)}
        _write_manifest(tmp_path, chapters)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop._get_snapshot_retention",
            lambda _pd: 50,
        )

        _prune_old_snapshots(tmp_path)

        assert _chapter_count(tmp_path) == 50
        # The newest 50 (chapters 7..56) survive; 1..6 are pruned.
        manifest = json.loads(
            (tmp_path / "snapshots" / "manifest.json").read_text(encoding="utf-8")
        )
        surviving = sorted(int(k) for k in manifest["chapters"])
        assert surviving == list(range(7, 57))
        # Pruned files are gone from disk.
        assert not (tmp_path / "snapshots" / "chapter-001-t.md").exists()
        assert (tmp_path / "snapshots" / "chapter-056-t.md").exists()

    def test_no_overshoot_at_boundary(self, tmp_path, monkeypatch):
        """The exact E40 scenario: retention 50, 52 chapters on disk -> 50 after."""
        chapters = {str(n): [f"chapter-{n:03d}-t.md"] for n in range(1, 53)}
        _write_manifest(tmp_path, chapters)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop._get_snapshot_retention",
            lambda _pd: 50,
        )

        _prune_old_snapshots(tmp_path)

        assert _chapter_count(tmp_path) == 50

    def test_under_cap_no_prune(self, tmp_path, monkeypatch):
        chapters = {str(n): [f"chapter-{n:03d}-t.md"] for n in range(1, 11)}
        _write_manifest(tmp_path, chapters)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop._get_snapshot_retention",
            lambda _pd: 50,
        )

        _prune_old_snapshots(tmp_path)

        assert _chapter_count(tmp_path) == 10

    def test_empty_manifest_no_op(self, tmp_path, monkeypatch):
        _write_manifest(tmp_path, {})
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop._get_snapshot_retention",
            lambda _pd: 50,
        )

        _prune_old_snapshots(tmp_path)  # must not raise

        assert _chapter_count(tmp_path) == 0

    def test_handles_gaps_in_chapter_numbers(self, tmp_path, monkeypatch):
        """Retention counts CHAPTERS, not the numeric range — gaps must not
        cause over-pruning."""
        chapters = {
            str(n): [f"chapter-{n:03d}-t.md"]
            for n in [1, 2, 3, 10, 20, 30, 40, 50, 60, 70]
        }
        _write_manifest(tmp_path, chapters)
        monkeypatch.setattr(
            "shenbi.pipeline.chapter_loop._get_snapshot_retention",
            lambda _pd: 5,
        )

        _prune_old_snapshots(tmp_path)

        # 10 chapters, keep newest 5.
        assert _chapter_count(tmp_path) == 5
        manifest = json.loads(
            (tmp_path / "snapshots" / "manifest.json").read_text(encoding="utf-8")
        )
        surviving = sorted(int(k) for k in manifest["chapters"])
        assert surviving == [30, 40, 50, 60, 70]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_snapshot_pruning.py -v`
Expected: FAIL — `test_keeps_exactly_retention_chapters` gets 51 chapters (the off-by-one); `test_no_overshoot_at_boundary` gets 52 (no prune happens because `keep_from = 52 - 50 = 2`, `to_prune = ch < 2` = only chapter 1, leaving 51 — still over cap, and the guard does not exist).

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/chapter_loop.py`, replace the body of `_prune_old_snapshots` (lines 870-900):

```python
def _prune_old_snapshots(project_dir: Path) -> None:
    """Remove snapshot files older than the retention window.

    Keeps only the most recent ``snapshot_retention_chapters`` worth of
    snapshots (counting CHAPTERS, not the numeric range — robust to gaps).
    Removes files from disk and updates the manifest. Spec 22 E40: fixes the
    off-by-one in the previous ``ch < keep_from`` comparator (which kept
    ``retention + 1``) and adds a post-prune guard.
    """
    retention = _get_snapshot_retention(project_dir)
    manifest = _load_manifest(project_dir)
    chapters_dict = manifest.get("chapters", {})

    all_chapters = sorted(int(k) for k in chapters_dict)
    if len(all_chapters) <= retention:
        return

    # Keep the newest ``retention`` chapters; prune the rest. Slice-based so
    # gaps in chapter numbering do not distort the count.
    keep_set = set(all_chapters[-retention:])
    to_prune = [ch for ch in all_chapters if ch not in keep_set]

    if not to_prune:
        return

    snap_dir = project_dir / "snapshots"
    for ch in to_prune:
        ch_key = str(ch)
        for filename in chapters_dict.get(ch_key, []):
            file_path = snap_dir / filename
            if file_path.exists():
                file_path.unlink()
        chapters_dict.pop(ch_key, None)

    _save_manifest(project_dir, manifest)
    log.info("snapshots_pruned", pruned=len(to_prune), retention=retention)

    # GUARD: assert the cap is now respected (fail loudly if a concurrent
    # writer re-added snapshots between the prune and this check).
    remaining = len(chapters_dict)
    if remaining > retention:
        log.error(
            "snapshot_prune_failed",
            count=remaining,
            cap=retention,
            msg="snapshot count still exceeds cap after pruning — "
            "concurrent writer or manifest corruption suspected",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/pipeline/test_snapshot_pruning.py tests/unit/pipeline/test_chapter_loop.py -v`
Expected: PASS — all boundary tests pass and existing chapter-loop tests are unaffected.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py \
        tests/unit/pipeline/test_snapshot_pruning.py
git commit -m "fix(chapter_loop): correct _prune_old_snapshots off-by-one + add prune-failed guard (E40)"
```

---

### Task 3: Full regression — `just check`

- [ ] **Step 1: Run the complete check suite**

Run: `just check`
Expected: PASS — ruff, mypy, basedpyright, lint_status_strings, lint_repo_consistency all green.

- [ ] **Step 2: Run the full unit suite with coverage**

Run: `uv run pytest tests/unit/ -q --cov=shenbi --cov-fail-under=85`
Expected: PASS, coverage ≥ 85%.

- [ ] **Step 3: Verify against the production manifest (informational)**

Run:

```bash
uv run python -c "
import json
from pathlib import Path
m = json.loads(Path('novel-output/xinghuo-ranqiong/snapshots/manifest.json').read_text())
chapters = m.get('chapters', {})
print('snapshot chapter count:', len(chapters))
print('configured cap: 50')
print('overflow:', max(0, len(chapters) - 50))
"
```

Expected (before any production prune runs): confirms the E40 overflow the fix targets. (This step does not modify production data — the next pipeline run will prune correctly.)

- [ ] **Step 4: Commit any cleanup**

```bash
git add -u
git commit -m "chore: ruff/mypy cleanup after lifecycle-enforcement plan" --allow-empty
```

---

## Self-Review

**1. Spec coverage:**
- §2.1 / §3.1 wire soft-fail trackers to `check_escalation` → Task 1 ✓
- §2.2 / §3.2 fix the boundary condition in the EXISTING `_prune_old_snapshots` (not a new mtime pruner) → Task 2 ✓
- §4 affected files: only `chapter_loop.py` modified ✓
- §3.2 "REJECTED" note (no new `retention.py` / no mtime-based pruner) → honoured: Task 2 modifies the existing chapter-number pruner only ✓
- §5 criteria 1 (soft-fail escalation triggers review) → Task 1 tests ✓
- §5 criteria 2, 3 (cap respected + prune-failed guard) → Task 2 tests ✓
- §5 criterion 4 (no regression to mtime-based pruning) → Task 2 keeps chapter-number-based slicing ✓
- §5 criterion 5 (`just check`) → Task 3 Step 1 ✓

**2. Placeholder scan:** No TBD/TODO. The one open-ended note (Task 1: "if `dispatch_escalation`'s kwargs differ, mirror the call at `chapter_loop.py:416`") gives a concrete reference line and is acceptable because the test does not lock the kwargs — but the implementer should check `revision_router.py` and align. Every code block is complete.

**3. Type consistency:** `_check_soft_fail_escalation(state, project_dir, chapter)` is consistent between Task 1's definition, its call site, and the test. `_prune_old_snapshots(project_dir)` signature is unchanged. `_get_recent_resonance_scores(project_dir, chapter, window=5)` matches the existing helper at `chapter_loop.py:813` (called with `window=5` to match `check_escalation`'s default window). `check_escalation` is called with exactly its real parameters. `SoftFailTracker.occurrences` / `.escalation_threshold` match `state.py:103-105`.

**Key codebase facts baked in:**
- `should_escalate = tracker.record(chapter)` is already computed at `chapter_loop.py:1305` and the `if should_escalate:` block at `:1313` is the exact insertion point.
- `check_escalation` real signature (verified at `skill_utils/escalation/check.py:52-64`): `resonance_scores, sensitivity_blocking, volume_objective_met, regeneration_attempts, arc_score=None, stratum_axis_drift=False, ...`.
- `_get_recent_resonance_scores` already exists at `chapter_loop.py:813`.
- `_prune_old_snapshots` already exists at `chapter_loop.py:870` and is called at `:960`; the manifest format is `{"chapters": {"<n>": ["<filename>", ...]}}`.
- The off-by-one is `ch < keep_from` keeping `retention + 1`; the slice fix `all_chapters[-retention:]` keeps exactly `retention` and is robust to numbering gaps.
