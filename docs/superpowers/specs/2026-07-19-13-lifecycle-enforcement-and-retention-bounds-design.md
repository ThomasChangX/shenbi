# Spec 22: Lifecycle Enforcement and Retention Bounds Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Medium
> **Source:** Systematic debugging Phase 1 evidence (E32, E40)
> **Consolidated from findings:**
> - E32: soft_fail_trackers show transition/fatigue drift in Ch30-36 exceeding escalation threshold (3) but no action was taken
> - E40: Snapshot retention exceeded config (52 snapshots vs configured cap of 50)

---

## 1. Executive Summary

Two mechanisms **detect or bound state but their outputs are never consumed or enforced**:

1. **Soft-fail trackers without intervention (E32):** `pipeline-state.json` → `chapter_loop.soft_fail_trackers` shows `transition.occurrences: [32,34,35,36]` and `fatigue.occurrences: [30,32,33,34,35]`. Both exceed the `escalation_threshold: 3` within a `window_size: 5`. The trackers **detected** the drift — but nothing consumed the escalation signal. No intervention was applied until Ch35's state-settling timeout forced a manual checkpoint.

2. **Retention cap boundary overflow (E40):** `genre-config.json` sets `snapshot_retention_chapters: 50`. Snapshot pruning EXISTS — `_prune_old_snapshots()` (`chapter_loop.py:870-905`) runs and is called at `chapter_loop.py:960`. However, the production run shows 52 snapshots vs the configured cap of 50 — a 2-snapshot overflow suggesting a boundary condition or off-by-one in the pruning threshold, or snapshots created before the pruning threshold kicks in.

**Root cause:** Detection/enforcement asymmetry — the system records signals and declares limits but lacks the consumer/enforcer wiring that would act on them.

---

## 2. Root Cause Analysis

### 2.1 Soft-Fail Trackers: Detection Without Intervention (E32)

The `soft_fail_trackers` data structure tracks:
- `transition`: chapters where transition-word density is anomalous
- `fatigue`: chapters where fatigue-word density is anomalous
- `escalation_threshold: 3` — if >= 3 occurrences within `window_size: 5` chapters, escalate

The data shows BOTH trackers exceeded their threshold in the Ch30-36 window:
- `transition`: 4 occurrences (Ch32,34,35,36) > threshold 3
- `fatigue`: 5 occurrences (Ch30,32,33,34,35) > threshold 3

**But no code path consumes this escalation signal.** The `check_escalation()` function exists in `skill_utils/escalation/check.py` but is never imported by the chapter loop or `_should_run_step` (verified in Spec 5 correction). The soft-fail data is collected but orphaned.

### 2.2 Retention Boundary Overflow (E40)

`genre-config.json` → `snapshot_retention_chapters: 50`. This config value IS read AND enforced — `_prune_old_snapshots()` exists at `chapter_loop.py:870-905` and is called at line 960. Pruning by chapter number is already implemented and runs.

**The real finding:** The production run shows 52 snapshots on disk vs the configured cap of 50. Since pruning exists and runs, the 2-snapshot overflow indicates either (a) a boundary condition / off-by-one in the pruning threshold logic inside `_prune_old_snapshots()`, or (b) snapshots created before the pruning threshold kicks in (e.g., the pruning check runs after new-snapshot creation, allowing a transient overshoot that is not re-checked).

**Evidence:** 52 snapshots on disk vs configured cap of 50, with `_prune_old_snapshots()` present and invoked. This is a threshold/boundary bug in existing code, NOT a missing-pruning defect.

---

## 3. Fix Strategy

### 3.1 Wire Soft-Fail Trackers to Escalation Consumer

```python
# In chapter_loop.py, after each chapter's audits complete
def _check_soft_fail_escalation(state: PipelineState, project_dir: Path, chapter: int):
    """Check if soft-fail trackers have exceeded escalation threshold."""
    from shenbi.skill_utils.escalation.check import check_escalation

    for tracker_name, tracker in state.chapter_loop.soft_fail_trackers.items():
        occurrences = tracker.get('occurrences', [])
        threshold = tracker.get('escalation_threshold', 3)
        window = tracker.get('window_size', 5)

        # Count occurrences within the sliding window
        window_start = max(1, chapter - window + 1)
        recent = [occ for occ in occurrences if occ >= window_start]

        if len(recent) >= threshold:
            logger.warning(
                "soft_fail_escalation_triggered",
                tracker=tracker_name,
                occurrences=recent,
                threshold=threshold,
                chapter=chapter,
            )
            # Wire to escalation review
            signals = check_escalation(
                resonance_scores=_get_recent_scores(project_dir, chapter),
                sensitivity_blocking=False,
                volume_objective_met=True,
            )
            if signals:
                _trigger_escalation_intervention(state, project_dir, chapter, signals)
```

### 3.2 Fix the Boundary Condition in the Existing `_prune_old_snapshots()`

> **Removed section note:** A previous version of this spec (former §3.2) proposed a NEW `_enforce_snapshot_retention()` based on `st_mtime`. That was WRONG — it duplicated already-existing code (`_prune_old_snapshots()` at `chapter_loop.py:870-905`, called at line 960) and proposed a WORSE approach (mtime-based ordering) than the existing chapter-number-based pruning. The original §3.2 has been removed. The real fix is to correct the boundary/off-by-one in the existing chapter-number-based pruner.

The existing pruner is invoked but overshoots the cap by 2. Investigate and fix the threshold logic:

```python
# chapter_loop.py — fix the boundary condition in the EXISTING _prune_old_snapshots()
# (do NOT replace it with an mtime-based pruner)
def _prune_old_snapshots(project_dir: Path, state: PipelineState):
    """Prune old snapshots to respect the chapter-based retention cap.

    Existing implementation already runs (called at chapter_loop.py:960).
    Fix the boundary condition that allows a 2-snapshot overshoot.
    """
    max_snapshots = state.config.snapshot_retention_chapters  # e.g., 50
    snapshot_dir = project_dir / "snapshots"
    if not snapshot_dir.exists():
        return

    # Order by CHAPTER NUMBER (parse from filename), NOT mtime.
    snapshots = sorted(
        snapshot_dir.glob("chapter-*.md"),
        key=lambda p: _chapter_number_from_snapshot_name(p.name),
    )

    # FIX: the cap is INCLUSIVE — keep the newest `max_snapshots` and
    # delete the rest. The previous comparator/threshold allowed off-by-one
    # overshoot when a new snapshot was created just before pruning ran.
    while len(snapshots) > max_snapshots:
        oldest = snapshots.pop(0)
        oldest.unlink()
        logger.info("snapshot_pruned", file=oldest.name,
                    remaining=len(snapshots), cap=max_snapshots)

    # GUARD: assert the cap is now respected (fail loudly if still overshooting)
    if len(snapshots) > max_snapshots:
        logger.error("snapshot_prune_failed", count=len(snapshots), cap=max_snapshots)
```

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/pipeline/chapter_loop.py` (post-audit) | Add `_check_soft_fail_escalation()` call | Wire soft-fail trackers to intervention (genuine gap) |
| `src/shenbi/pipeline/chapter_loop.py:870-905` (`_prune_old_snapshots`) | Fix boundary/off-by-one in threshold + add prune-failed guard | Correct the existing chapter-number-based pruner that overshoots cap by 2 |

> **Not done:** A new `retention.py` generic framework and a new mtime-based `_enforce_snapshot_retention()` were considered and REJECTED — they duplicate the existing `_prune_old_snapshots()` and propose a worse (mtime-based) ordering than the existing chapter-number-based pruning.

---

## 5. Verification Criteria

1. **Soft-fail escalation:** When transition/fatigue occurrences exceed threshold, escalation review is triggered
2. **Snapshot cap respected:** After fixing the boundary condition in the existing `_prune_old_snapshots()`, snapshot count never exceeds the configured cap (no 2-snapshot overshoot)
3. **Prune-failed guard:** `_prune_old_snapshots()` logs an error if the cap is still exceeded after pruning
4. **No regression to mtime-based pruning:** pruning remains chapter-number-based (mtime-based pruner rejected)
5. **Regression:** `just check` passes fully

---

## 6. Dependencies

```
Spec 22 (this spec, Lifecycle Enforcement and Retention Bounds)
    |
    +---> Enhances: Spec 4 (soft-fail trackers complement linguistic drift detection)
    +---> Enhances: Spec 3 (snapshot management includes pruning)
    +---> Enhances: Spec 7 (progress tracking depends on enforced lifecycle)

Prerequisites: None (standalone enforcement fix)
```
