# Spec 17: State-Counter Integrity and Telemetry Wiring Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** High
> **Source:** Systematic debugging Phase 1 evidence (E7, E8, E36)
> **Consolidated from findings:**
> - E7: `retry_counts` empty {} despite 54 HARD-gate failures across 42 chapters
> - E8: `revision_count` is 0 for all chapters despite 34 revision routes
> - E36: `last_snapshot:{}` empty despite 51 snapshots existing

---

## 1. Executive Summary

The pipeline-state.json declares per-chapter counters and pointers whose maintenance is **defective** — either never wired to the events that should increment them, or incremented but not durable across the retry cycle. This makes pipeline telemetry structurally untrustworthy — you cannot reliably detect retry loops, revision exhaustion, or find the latest recovery snapshot from state alone. Three specific fields are affected:

1. **`retry_counts`**: Incremented at `chapter_loop.py:398-399` and `1327-1328`, but cleared by `_reset_retries` at line 456 on step success. The production state shows `{}` because successful retries reset the counter. The real issue is that the counter does not persist across the retry cycle — if the pipeline crashes mid-retry, the count is lost. This makes retry-budget enforcement unreliable on resume.

2. **`revision_count`**: Declared per chapter state, but NEVER incremented when `_route_revision_after_resonance` fires a revision route. All 56 chapters report `revision_count: 0`, yet 34 `chapter-N-revision-decisions.json` files exist on disk. This makes it impossible to detect revision loops or revision exhaustion from state.

3. **`last_snapshot`**: Declared in state, but always `{}` — the pointer to the most recent snapshot is never updated after `_snapshot_chapter_files` runs. This means resume/rollback cannot find the recovery point from state; it must scan the snapshots directory.

**Root cause:** The state schema declares these fields but the code paths that should mutate them don't. This is a wiring defect, not a schema defect — the fields exist, they're just orphaned.

---

## 2. Root Cause Analysis

### 2.1 retry_counts Not Persisted Across Retry Cycle (E7)

In `chapter_loop.py`, the retry flow is:
1. G4 HARD check fails → failure recorded in `retry_feedback`
2. The retry counter IS incremented at `chapter_loop.py:398-399` and again at `1327-1328` (verified)
3. Step is retried (re-dispatched)
4. On retry SUCCESS, `_reset_retries` is called at `chapter_loop.py:456`, which clears the counter back to `{}`

**The real defect:** The counter is incremented, but it is cleared by `_reset_retries` (line 456) on step success. The production state shows `{}` because successful retries reset the counter. The real issue is that the counter does not persist across the retry cycle — if the pipeline crashes mid-retry, the count is lost. This makes retry-budget enforcement unreliable on resume.

**Evidence:** `pipeline-state.json` → `chapter_loop.retry_counts: {}` (empty for all 56 chapters) despite `retry_feedback` containing 54 distinct entries — consistent with `_reset_retries` clearing the counter after each successful retry, leaving no durable record of the budget consumed.

### 2.2 revision_count Never Incremented (E8)

When `_route_revision_after_resonance` (`chapter_loop.py:1021`) determines a revision is needed and dispatches `shenbi-chapter-revision`:
1. The revision skill runs
2. Revision decisions are written to disk
3. **MISSING:** `cs.revision_count += 1` is never called

**Evidence:** All 56 chapters have `revision_count: 0`, but 34 `chapter-N-revision-decisions.json` files exist. Revision routes recorded: spot-fix (23), regenerate (6), constrained-regenerate (5).

### 2.3 last_snapshot Pointer Never Updated (E36)

When `_snapshot_chapter_files` (`chapter_loop.py:903-960`) writes a snapshot:
1. The snapshot file is written to `snapshots/chapter-NNN-TIMESTAMP.md`
2. The manifest is updated
3. **MISSING:** `state.last_snapshot = {"chapter": N, "path": "snapshots/...", "timestamp": "..."}` is never set

**Evidence:** `pipeline-state.json` → `last_snapshot: {}` despite 51 snapshot files on disk.

---

## 3. Fix Strategy

### 3.1 Wire retry_counts to G4 Failure Events

```python
# Root cause fix: retry_counts IS incremented (chapter_loop.py:398-399) but
# _reset_retries (line 456) clears it on step success. This destroys the
# retry budget trail, making crash-resume unable to enforce retry limits.
#
# Fix: Maintain a SEPARATE durable counter that is NOT cleared on success.

def _handle_g4_failure(state: PipelineState, chapter: int, skill: str, failures: list[str]):
    """Record G4 failure for durable retry budget tracking."""
    step_key = f"ch{chapter}-{skill}"

    # Increment durable budget (NOT cleared on success)
    current_budget = state.chapter_loop.retry_budget_consumed.get(step_key, 0)
    state.chapter_loop.retry_budget_consumed[step_key] = current_budget + 1

    # Record failure reason (existing behavior — retry_feedback can stay ephemeral)
    state.chapter_loop.retry_feedback[step_key] = "; ".join(failures)

    # Enforce retry limit using DURABLE counter
    max_retries = state.config.max_audit_retries
    if current_budget + 1 > max_retries:
        logger.error("retry_limit_exhausted", chapter=chapter, skill=skill,
                     consumed=current_budget + 1, max=max_retries)
        raise RetryExhaustedError(f"Retry budget ({max_retries}) exhausted for {step_key}")
```

### 3.2 Wire revision_count to Revision Routing

```python
# In chapter_loop.py, in _route_revision_after_resonance (after revision dispatch decision)
def _route_revision_after_resonance(state, project_dir, chapter):
    # ... existing routing logic ...
    if route != "no_revision":
        # INCREMENT revision counter (currently missing!)
        cs = state.chapter_loop.chapter_states[chapter - 1]
        cs.revision_count += 1  # ADD THIS LINE

        logger.info("revision_routed", chapter=chapter, route=route,
                    revision_count=cs.revision_count)
```

### 3.3 Wire last_snapshot to Snapshot Creation

```python
# In chapter_loop.py, in _snapshot_chapter_files (after snapshot is written)
def _snapshot_chapter_files(project_dir, chapter, ...):
    # ... existing snapshot creation logic ...
    snapshot_path = snapshot_dir / f"chapter-{chapter:03d}-{timestamp}.md"
    safe_write(snapshot_path, content)

    # UPDATE the pointer (currently missing!)
    state.last_snapshot = {
        "chapter": chapter,
        "path": str(snapshot_path.relative_to(project_dir)),
        "timestamp": timestamp,
    }
    logger.info("snapshot_pointer_updated", chapter=chapter, path=str(snapshot_path))
```

### 3.4 Self-Heal on Resume

On pipeline resume, verify all counters/pointers against disk reality:

```python
def _heal_state_counters(state: PipelineState, project_dir: Path):
    """Self-heal orphaned state counters by cross-checking against disk."""

    # Heal retry_budget_consumed: ensure the durable counter field exists and
    # is populated from retry_feedback (which records distinct failure events).
    # retry_budget_consumed is the durable counterpart to retry_counts — it
    # is NOT cleared on success, so crash-resume can enforce retry limits.
    budget = getattr(state.chapter_loop, "retry_budget_consumed", None)
    if budget is None:
        state.chapter_loop.retry_budget_consumed = {}
        budget = state.chapter_loop.retry_budget_consumed
    for step_key in state.chapter_loop.retry_feedback:
        # Each retry_feedback key represents at least one consumed budget unit.
        # If the durable budget is missing for a key with recorded feedback,
        # seed it with a minimum of 1 (conservative: never undercount consumed budget).
        if step_key not in budget:
            budget[step_key] = 1
            logger.warning("retry_budget_consumed_healed", step_key=step_key,
                           seeded_value=1,
                           note="durable budget missing for key with retry_feedback")

    # Heal revision_count: count revision-decisions files on disk
    # Note: this counts at most 1 since the latest revision-decisions file
    # overwrites prior ones (each chapter has a single chapter-N-revision-decisions.json
    # that is rewritten on every revision round). For accurate revision history
    # tracking, see Spec 17 §3.5 (proposed: revision history ledger).
    for cs in state.chapter_loop.chapter_states:
        rev_path = project_dir / f"chapters/chapter-{cs.chapter_number}-revision-decisions.json"
        disk_count = 1 if rev_path.exists() else 0
        if cs.revision_count != disk_count:
            logger.warning("revision_count_healed", chapter=cs.chapter_number,
                           state_value=cs.revision_count, disk_value=disk_count,
                           note="disk_count undercounts: revision-decisions file is overwritten per round")
            cs.revision_count = disk_count

    # Heal last_snapshot: find the most recent snapshot on disk
    snapshot_dir = project_dir / "snapshots"
    if snapshot_dir.exists():
        snapshots = sorted(snapshot_dir.glob("chapter-*.md"), key=lambda p: p.stat().st_mtime)
        if snapshots and not state.last_snapshot:
            latest = snapshots[-1]
            state.last_snapshot = {
                "chapter": _extract_chapter_from_snapshot_name(latest.name),
                "path": str(latest.relative_to(project_dir)),
                "timestamp": latest.stat().st_mtime,
            }
            logger.info("last_snapshot_healed", path=str(latest))
```

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/pipeline/chapter_loop.py` (G4 retry handler) | Add `retry_budget_consumed[key] += 1` (durable counter NOT cleared by `_reset_retries`) | Maintain durable retry budget trail since `retry_counts` is cleared on success (line 456) |
| `src/shenbi/pipeline/chapter_loop.py:1021` (`_route_revision_after_resonance`) | Add `cs.revision_count += 1` | Wire revision counter to routing events |
| `src/shenbi/pipeline/chapter_loop.py:903-960` (`_snapshot_chapter_files`) | Add `state.last_snapshot = {...}` | Wire snapshot pointer to creation events |
| `src/shenbi/pipeline/chapter_loop.py` or `cli.py` (resume) | Add `_heal_state_counters()` | Self-heal orphaned counters on resume |

---

## 5. Verification Criteria

1. **retry_budget_consumed populated:** After a G4 HARD failure + retry + subsequent success, `retry_budget_consumed[chN-skill]` = 1 (NOT reset to 0 — unlike `retry_counts` which `_reset_retries` clears)
2. **retry limit enforced:** After budget exceeds `max_audit_retries`, `RetryExhaustedError` is raised (budget persists across success/reset, so crash-resume still enforces it)
3. **revision_count populated:** After revision dispatch, `cs.revision_count` >= 1
4. **last_snapshot populated:** After snapshot creation, `state.last_snapshot` is non-empty with correct chapter/path
5. **Self-heal:** On resume after crash, counters/pointers are healed from disk evidence
6. **Regression:** `just check` passes fully

---

## 6. Dependencies

```
Spec 17 (this spec, State-Counter Integrity and Telemetry Wiring)
    |
    +---> Enhances: Spec 7 (progress tracking depends on accurate retry counters)
    +---> Enhances: Spec 3 (snapshot recovery depends on last_snapshot pointer)

Prerequisites: None (standalone wiring fix)
```
