# State-Counter Integrity and Telemetry Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire three orphaned pipeline-state fields so telemetry is trustworthy: a durable `retry_budget_consumed` counter that survives the retry cycle, an incrementing `revision_count`, and a populated `last_snapshot` pointer — plus a self-heal pass on resume.

**Architecture:** Four targeted wiring fixes plus a new exception. The existing `retry_counts` IS incremented (`chapter_loop.py:398-399`, `1327-1328`) but `_reset_retries` (line 456) clears it on success — so a SEPARATE durable counter `retry_budget_consumed` is added and never cleared, enabling crash-resume to enforce the retry limit. `revision_count` gets `+= 1` in `_route_revision_after_resonance`; `last_snapshot` gets set in `_snapshot_chapter_files` (which must gain a `state` parameter to receive it). On resume (`cmd_resume` → after `load_state`), `_heal_state_counters` cross-checks all three against disk. State-schema changes are additive: `retry_budget_consumed` is a new field on `ChapterLoopStateData`, serialized in `to_dict`/`from_dict`.

**Tech Stack:** Python 3.11+, pathlib, pytest, structlog

## Global Constraints

- `retry_counts` is NOT the fix target — it is correctly incremented and intentionally cleared by `_reset_retries` on step success (`chapter_loop.py:456`). The fix is a SEPARATE durable counter `retry_budget_consumed` that is NEVER cleared by `_reset_retries` (spec §2.1, §3.1). Do not change `_reset_retries` to preserve `retry_counts`.
- The retry limit is enforced via `state.config.max_audit_retries` (the G4 hard-fail budget). `handle_dispatch_failure` uses `max_revision_retries` for the dispatch/gate failure path — keep that path intact; the durable counter guards the G4 HARD-fail retry budget for crash-resume (spec §3.1).
- `_snapshot_chapter_files` currently has signature `(project_dir, chapter)` and takes NO `state`. To set `last_snapshot`, add a `state: PipelineState | None = None` parameter (default None preserves existing callers that don't have state handy) (spec §3.3).
- `RetryExhaustedError` does NOT exist yet — create it in `src/shenbi/exceptions.py` (subclass of `ShenbiError`), mirroring the existing `ScoringRejectError` pattern (spec §3.1).
- New state field `retry_budget_consumed` is additive: `to_dict` gains the key; `from_dict` reads it with a default of `{}` so old state files load cleanly. All counters/pointers are healed from disk on resume, so an old state file self-corrects.
- `just check` must pass fully after each task.

---

### Task 1: Add retry_budget_consumed durable counter + RetryExhaustedError

**Files:**
- Modify: `src/shenbi/exceptions.py` (add `RetryExhaustedError`)
- Modify: `src/shenbi/pipeline/state.py:133-143` (`ChapterLoopStateData` — add `retry_budget_consumed` field), `state.py:179-201` (`to_dict`), `state.py:269-279` (`from_dict`)
- Modify: `src/shenbi/pipeline/chapter_loop.py:383-440` (`_handle_failure` — increment durable counter + enforce limit), `chapter_loop.py:1321-1339` (G4 hard-fail path — increment durable counter)
- Test: `tests/unit/pipeline/test_retry_budget.py`

**Interfaces:**
- Consumes: `PipelineState`, `ChapterLoopStateData`, `state.config.max_audit_retries`, `_retry_key(chapter, skill)`
- Produces: `RetryExhaustedError` exception; `ChapterLoopStateData.retry_budget_consumed: dict[str,int]` (durable, never cleared); `_handle_failure` and the G4 hard-fail path increment it. `_reset_retries` is left unchanged (still clears `retry_counts`).

**Context:** Spec §2.1 / §3.1. The retry counter is cleared on success, so crash-resume cannot enforce the budget. The durable counter is the missing trail. The G4 hard-fail path at lines 1321-1339 currently increments `retry_counts` directly (1327-1328) and pops it (1339); wire `retry_budget_consumed` there too. `_handle_failure` is the dispatch/gate failure path; it already computes `count` from `retry_counts`. Add the durable increment at both increment sites.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_retry_budget.py
"""Tests for the durable retry_budget_consumed counter (spec §3.1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.exceptions import RetryExhaustedError
from shenbi.pipeline.chapter_loop import ChapterStep, _handle_failure, _reset_retries, _retry_key
from shenbi.pipeline.state import PipelineState


def _state() -> PipelineState:
    s = PipelineState.default(project_dir="/tmp/test")
    s.config.max_audit_retries = 2
    s.config.max_revision_retries = 2
    return s


def _step(skill: str = "shenbi-chapter-drafting") -> ChapterStep:
    return ChapterStep(step_num=1, skill=skill, name="x")


class TestDurableCounter:
    def test_reset_retries_clears_retry_counts_not_budget(self, tmp_path: Path):
        """_reset_retries clears retry_counts but MUST leave retry_budget_consumed."""
        s = _state()
        key = _retry_key(1, "shenbi-chapter-drafting")
        s.chapter_loop.retry_counts[key] = 3
        s.chapter_loop.retry_budget_consumed[key] = 3

        _reset_retries(s, _step(), chapter=1)

        assert key not in s.chapter_loop.retry_counts, "retry_counts should be cleared"
        assert s.chapter_loop.retry_budget_consumed.get(key) == 3, (
            "retry_budget_consumed must NOT be cleared on success (spec §3.1)"
        )

    def test_handle_failure_increments_durable_budget(self, tmp_path: Path, monkeypatch):
        """A G4/dispatch failure increments the durable budget (and retry_counts)."""
        s = _state()
        # keep handle_dispatch_failure returning True so _handle_failure retries
        monkeypatch.setattr(
            "shenbi.pipeline.error_handler.handle_dispatch_failure",
            lambda state, skill, count: True,
        )
        escalated = _handle_failure(s, _step(), chapter=1, failure="gate", project_dir=tmp_path)
        assert escalated is False  # retries, does not escalate yet
        key = _retry_key(1, "shenbi-chapter-drafting")
        assert s.chapter_loop.retry_budget_consumed.get(key, 0) >= 1


class TestBudgetEnforcement:
    def test_exceeding_max_audit_retries_raises(self, tmp_path: Path, monkeypatch):
        """When durable budget exceeds max_audit_retries, RetryExhaustedError is raised."""
        s = _state()
        s.config.max_audit_retries = 2
        key = _retry_key(1, "shenbi-chapter-drafting")
        # Pre-seed budget at the limit so the next failure trips it.
        s.chapter_loop.retry_budget_consumed[key] = 2
        monkeypatch.setattr(
            "shenbi.pipeline.error_handler.handle_dispatch_failure",
            lambda state, skill, count: True,
        )
        with pytest.raises(RetryExhaustedError):
            _handle_failure(s, _step(), chapter=1, failure="gate", project_dir=tmp_path)


class TestStateRoundTrip:
    def test_retry_budget_consumed_serializes(self):
        s = _state()
        s.chapter_loop.retry_budget_consumed = {"ch1-x": 2}
        data = s.to_dict()
        assert data["chapter_loop"]["retry_budget_consumed"] == {"ch1-x": 2}

    def test_retry_budget_consumed_loads_with_default(self):
        # Old state file without the key loads to {} (additive field).
        import json

        s = PipelineState.from_json(
            json.dumps({"version": 1, "project_dir": "/x", "phase": "genesis"})
        )
        assert s.chapter_loop.retry_budget_consumed == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_retry_budget.py -v`
Expected: FAIL with `ImportError: cannot import name 'RetryExhaustedError'` and `AttributeError: retry_budget_consumed`.

- [ ] **Step 3: Write minimal implementation**

First, add the exception in `src/shenbi/exceptions.py` (near the other `ShenbiError` subclasses, e.g. after `ScoringRejectError`):

```python
class RetryExhaustedError(ShenbiError):
    """The durable retry budget for a chapter step has been exceeded.

    Raised when retry_budget_consumed exceeds state.config.max_audit_retries,
    so crash-resume still enforces the limit even though the ephemeral
    retry_counts is cleared on success (spec §3.1).
    """
```

Next, add the field to `ChapterLoopStateData` in `src/shenbi/pipeline/state.py` (after `retry_counts`):

```python
@dataclass
class ChapterLoopStateData:
    current_chapter: int = 0
    current_step: str = ""
    step_index: int = 0
    chapter_states: dict[str, ChapterState] = field(default_factory=dict)
    per_chapter_review_enabled: bool = True
    retry_counts: dict[str, int] = field(default_factory=dict)
    # Durable retry budget (spec §3.1): NOT cleared by _reset_retries, so
    # crash-resume can enforce max_audit_retries. Contrast retry_counts above,
    # which is intentionally cleared on step success.
    retry_budget_consumed: dict[str, int] = field(default_factory=dict)
    modify_feedback: str | None = None
    retry_feedback: dict[str, str] = field(default_factory=dict)
    soft_fail_trackers: dict[str, SoftFailTracker] = field(default_factory=dict)
```

In `PipelineState.to_dict`, inside the `"chapter_loop": {...}` dict, add after `"retry_counts":`:

```python
                "retry_counts": self.chapter_loop.retry_counts,
                "retry_budget_consumed": self.chapter_loop.retry_budget_consumed,
```

In `PipelineState.from_dict`, in the `ChapterLoopStateData(...)` construction, add after `retry_counts=`:

```python
                retry_counts=cl_data.get("retry_counts", {}),
                retry_budget_consumed=cl_data.get("retry_budget_consumed", {}),
```

Then wire the increment + enforcement in `chapter_loop.py`. Add the import at the top of the file (with the other shenbi imports):

```python
from shenbi.exceptions import RetryExhaustedError
```

Modify `_handle_failure` to increment the durable counter and enforce the limit. Change the body that currently reads:

```python
    key = _retry_key(chapter, step.skill)
    count = state.chapter_loop.retry_counts.get(key, 0) + 1
    state.chapter_loop.retry_counts[key] = count
    from shenbi.pipeline.error_handler import handle_dispatch_failure
```
to:

```python
    key = _retry_key(chapter, step.skill)
    count = state.chapter_loop.retry_counts.get(key, 0) + 1
    state.chapter_loop.retry_counts[key] = count

    # Durable budget (spec §3.1): NOT cleared by _reset_retries, so crash-resume
    # can enforce max_audit_retries even after a successful retry.
    consumed = state.chapter_loop.retry_budget_consumed.get(key, 0) + 1
    state.chapter_loop.retry_budget_consumed[key] = consumed
    if consumed > state.config.max_audit_retries:
        log.error(
            "retry_budget_exhausted",
            chapter=chapter,
            skill=step.skill,
            consumed=consumed,
            max=state.config.max_audit_retries,
        )
        raise RetryExhaustedError(
            f"Retry budget ({state.config.max_audit_retries}) exhausted for {key} "
            f"(consumed {consumed})"
        )

    from shenbi.pipeline.error_handler import handle_dispatch_failure
```

For the G4 hard-fail direct-increment path (lines 1321-1339), change:

```python
        if hard_fails:
            state.chapter_loop.retry_feedback[retry_key] = (
                f"G4 HARD check failed: {hard_fails}\nFull result: {json.dumps(g4, default=str)}"
            )
            if state.config.per_chapter_review_enabled:
                return _handle_failure(state, step, chapter, "gate", project_dir)
            count = state.chapter_loop.retry_counts.get(retry_key, 0) + 1
            state.chapter_loop.retry_counts[retry_key] = count
            if count <= 1:
```
to (add the durable increment before the existing logic):

```python
        if hard_fails:
            state.chapter_loop.retry_feedback[retry_key] = (
                f"G4 HARD check failed: {hard_fails}\nFull result: {json.dumps(g4, default=str)}"
            )
            # Durable budget trail for both paths (spec §3.1).
            consumed = state.chapter_loop.retry_budget_consumed.get(retry_key, 0) + 1
            state.chapter_loop.retry_budget_consumed[retry_key] = consumed
            if consumed > state.config.max_audit_retries:
                raise RetryExhaustedError(
                    f"Retry budget ({state.config.max_audit_retries}) exhausted for {retry_key} "
                    f"(consumed {consumed})"
                )
            if state.config.per_chapter_review_enabled:
                return _handle_failure(state, step, chapter, "gate", project_dir)
            count = state.chapter_loop.retry_counts.get(retry_key, 0) + 1
            state.chapter_loop.retry_counts[retry_key] = count
            if count <= 1:
```

Note: `_reset_retries` is intentionally left unchanged — it still clears `retry_counts` only.

Add caller-level handling around the dispatch that may raise `RetryExhaustedError`:

```python
try:
    _dispatch_with_retry(...)
except RetryExhaustedError:
    # Translate to escalation checkpoint
    dispatch_escalation(project_dir, chapter, context="retry_exhausted")
    cs.checkpoint = "escalation"
    raise  # Re-raise to abort the current chapter step
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_retry_budget.py tests/unit/pipeline/test_chapter_loop_full.py tests/unit/pipeline/test_state.py -v`
Expected: PASS (new tests + existing state/chapter-loop tests unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/exceptions.py src/shenbi/pipeline/state.py src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_retry_budget.py
git commit -m "fix(state): add durable retry_budget_consumed counter + RetryExhaustedError

Spec 17 §3.1. retry_counts IS incremented but cleared by _reset_retries on
success, so crash-resume couldn't enforce the budget. New durable counter is
never cleared. Budget enforcement raises RetryExhaustedError. State field is
additive (loads with default {} from old files)."
```

---

### Task 2: Wire revision_count to revision routing

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:1021-1051` (`_route_revision_after_resonance` — add `cs.revision_count += 1`)
- Test: `tests/unit/pipeline/test_revision_count.py`

**Interfaces:**
- Consumes: `_get_chapter_state`, `route_chapter_revision`, `RevisionRoute`
- Produces: every non-no-op revision route increments `cs.revision_count` and logs `revision_count`.

**Context:** Spec §2.2 / §3.2. All 56 chapters report `revision_count: 0` despite 34 revision-decisions files on disk — the increment is simply missing. `_route_revision_after_resonance` already obtains `cs` via `_get_chapter_state` and stores the route; add the increment after the route is decided, only when `route != NO_REVISION`. `RevisionRoute.NO_REVISION` is imported from `revision_router`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_revision_count.py
"""Tests that revision_count is incremented on revision routing (spec §3.2)."""
from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import _route_revision_after_resonance
from shenbi.pipeline.revision_router import RevisionRoute
from shenbi.pipeline.state import PipelineState


def test_revision_count_increments_on_non_noop_route(tmp_path: Path, monkeypatch):
    s = PipelineState.default(project_dir=str(tmp_path))
    # Force the router to return a revision route.
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.route_chapter_revision",
        lambda issues, blocking: RevisionRoute.SPOT_FIX,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.collect_audit_issues",
        lambda pd, ch: (["some issue"], False),
    )

    _route_revision_after_resonance(s, tmp_path, chapter=1)

    cs = s.chapter_loop.chapter_states["1"]
    assert cs.revision_count == 1, f"revision_count should be 1, got {cs.revision_count}"


def test_revision_count_unchanged_on_no_revision(tmp_path: Path, monkeypatch):
    s = PipelineState.default(project_dir=str(tmp_path))
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.route_chapter_revision",
        lambda issues, blocking: RevisionRoute.NO_REVISION,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.collect_audit_issues",
        lambda pd, ch: ([], False),
    )

    _route_revision_after_resonance(s, tmp_path, chapter=1)

    cs = s.chapter_loop.chapter_states["1"]
    assert cs.revision_count == 0, "NO_REVISION must not increment revision_count"


def test_revision_count_accumulates_across_routes(tmp_path: Path, monkeypatch):
    s = PipelineState.default(project_dir=str(tmp_path))
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.route_chapter_revision",
        lambda issues, blocking: RevisionRoute.SPOT_FIX,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.collect_audit_issues",
        lambda pd, ch: (["issue"], False),
    )
    _route_revision_after_resonance(s, tmp_path, chapter=2)
    _route_revision_after_resonance(s, tmp_path, chapter=2)

    assert s.chapter_loop.chapter_states["2"].revision_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_revision_count.py -v`
Expected: FAIL (`revision_count == 0` instead of 1 — increment missing).

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/chapter_loop.py`, in `_route_revision_after_resonance`, after `cs = _get_chapter_state(state, chapter)` and the `cs.audit_results[_REVISION_ROUTE_KEY] = route.value` line, add the increment guarded by the route. The current block:

```python
    issues, blocking = collect_audit_issues(project_dir, chapter)
    route = route_chapter_revision(issues, blocking)
    cs = _get_chapter_state(state, chapter)
    cs.audit_results[_REVISION_ROUTE_KEY] = route.value
```
becomes:

```python
    issues, blocking = collect_audit_issues(project_dir, chapter)
    route = route_chapter_revision(issues, blocking)
    cs = _get_chapter_state(state, chapter)
    cs.audit_results[_REVISION_ROUTE_KEY] = route.value

    # Wire revision_count (spec §3.2): increment only on an actual revision
    # route, not on NO_REVISION. Previously this was missing entirely, leaving
    # revision_count at 0 for all chapters.
    if route != RevisionRoute.NO_REVISION:
        cs.revision_count += 1
        log.info(
            "revision_count_incremented",
            chapter=chapter,
            route=route.value,
            revision_count=cs.revision_count,
        )
```

Add the import for `RevisionRoute` near the existing `revision_router` import in `chapter_loop.py`:

```python
from shenbi.pipeline.revision_router import RevisionRoute, route_chapter_revision
```
(If `route_chapter_revision` is already imported, only add `RevisionRoute`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_revision_count.py tests/unit/pipeline/test_chapter_loop_full.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_revision_count.py
git commit -m "fix(state): increment revision_count on revision routing

Spec 17 §3.2. _route_revision_after_resonance now does cs.revision_count += 1
when route != NO_REVISION. Previously revision_count was always 0 despite 34
revision-decisions files on disk."
```

---

### Task 3: Wire last_snapshot pointer in _snapshot_chapter_files

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:903-960` (`_snapshot_chapter_files` — add `state` param, set `state.last_snapshot`), `chapter_loop.py:997` and `:1215` (callers — pass `state`)
- Test: `tests/unit/pipeline/test_last_snapshot.py`

**Interfaces:**
- Consumes: `safe_write`, `_load_manifest`/`_save_manifest`, `PipelineState`
- Produces: `_snapshot_chapter_files(project_dir, chapter, state=None)` sets `state.last_snapshot = {"chapter", "path", "timestamp"}` when `state` is passed. Existing callers that omit `state` behave unchanged.

**Context:** Spec §2.3 / §3.3. The function takes no `state` today, so `last_snapshot` is always `{}`. Two callers pass nothing useful: line 997 (`_should_run_step`, no state in scope there but it can be threaded) and line 1215 (the inline snapshot path has `state` in scope). The signature change is backward-compatible via a default `None`. The pointer uses the snapshot's filename timestamp for the `timestamp` field.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_last_snapshot.py
"""Tests that last_snapshot is set after snapshot creation (spec §3.3)."""
from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import _snapshot_chapter_files
from shenbi.pipeline.state import PipelineState


def test_last_snapshot_set_with_chapter_path_timestamp(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    # Seed a chapter file so the snapshot has content.
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-5.md").write_text("# Ch5\nbody", encoding="utf-8")

    _snapshot_chapter_files(tmp_path, chapter=5, state=s)

    assert s.last_snapshot, "last_snapshot must be populated"
    assert s.last_snapshot["chapter"] == 5
    assert s.last_snapshot["path"].startswith("snapshots/")
    assert "chapter-005-" in s.last_snapshot["path"]
    assert "timestamp" in s.last_snapshot


def test_state_none_keeps_old_behavior(tmp_path: Path):
    """Caller may omit state; snapshot still created, no pointer to set."""
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-1.md").write_text("# Ch1\n", encoding="utf-8")
    # Must not raise.
    _snapshot_chapter_files(tmp_path, chapter=1, state=None)
    snaps = list((tmp_path / "snapshots").glob("chapter-001-*.md"))
    assert len(snaps) == 1


def test_path_is_relative_to_project_dir(tmp_path: Path, monkeypatch):
    s = PipelineState.default(project_dir=str(tmp_path))
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-3.md").write_text("x", encoding="utf-8")
    _snapshot_chapter_files(tmp_path, chapter=3, state=s)
    # path should be relative, not absolute.
    assert not s.last_snapshot["path"].startswith("/")
    assert (tmp_path / s.last_snapshot["path"]).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_last_snapshot.py -v`
Expected: FAIL (`last_snapshot` stays `{}` / `TypeError: unexpected keyword argument 'state'`).

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/chapter_loop.py`, change the signature and add the pointer update. The current function start:

```python
def _snapshot_chapter_files(project_dir: Path, chapter: int) -> None:
    """Create a timestamped file-based snapshot of chapter outputs.
    ...
    """
    from datetime import datetime

    snap_dir = project_dir / "snapshots"
```
becomes:

```python
def _snapshot_chapter_files(
    project_dir: Path,
    chapter: int,
    *,
    state: PipelineState | None = None,
) -> None:
    """Create a timestamped file-based snapshot of chapter outputs.

    When *state* is provided, updates ``state.last_snapshot`` to point at the
    newly written snapshot (spec §3.3) so resume/rollback can find the recovery
    point from state without scanning the snapshots directory.

    Copies chapter files, audit reports, and truth files into a single
    timestamped markdown file under ``snapshots/``. Updates the manifest
    and prunes old snapshots.

    This replaces the ``shenbi-snapshot-manage`` LLM dispatch with pure
    file operations — no git dependency.
    """
    from datetime import datetime

    snap_dir = project_dir / "snapshots"
```

Then, after the `safe_write(snap_path, content.encode("utf-8"))` line and before the manifest update, add the pointer update:

```python
    content = "\n\n---\n\n".join(parts) if parts else f"# Snapshot Chapter {chapter}\n\n(no files)"
    safe_write(snap_path, content.encode("utf-8"))

    # Wire last_snapshot (spec §3.3): point state at the newest snapshot so
    # resume/rollback can find the recovery point without a directory scan.
    if state is not None:
        state.last_snapshot = {
            "chapter": chapter,
            "path": str(snap_path.relative_to(project_dir)),
            "timestamp": timestamp,
        }
        log.info(
            "last_snapshot_updated",
            chapter=chapter,
            path=state.last_snapshot["path"],
        )

    # Update manifest
    manifest = _load_manifest(project_dir)
```

Now update the two callers to pass `state` where it is in scope. At line ~1215 (the inline snapshot path inside the step runner, where `state` IS in scope — the function signature there includes `state`), change:

```python
            pass  # snapshot already taken + manifest updated in _snapshot_chapter_files
```

Find the actual `_snapshot_chapter_files(project_dir, chapter)` call that precedes it and change it to `_snapshot_chapter_files(project_dir, chapter, state=state)`.

For the `_should_run_step` caller at line 997:

```python
    if skill == "shenbi-snapshot-manage":
        # Replace LLM dispatch with deterministic file-based snapshot.
        _snapshot_chapter_files(project_dir, chapter)
        return False
```
`_should_run_step` has `state` in its signature (`def _should_run_step(step, state, project_dir)`), so change to:

```python
    if skill == "shenbi-snapshot-manage":
        # Replace LLM dispatch with deterministic file-based snapshot.
        _snapshot_chapter_files(project_dir, chapter, state=state)
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_last_snapshot.py tests/unit/pipeline/test_chapter_loop_full.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_last_snapshot.py
git commit -m "fix(state): wire last_snapshot pointer in _snapshot_chapter_files

Spec 17 §3.3. _snapshot_chapter_files gains state= param and sets
state.last_snapshot = {chapter, path, timestamp}. Both in-scope callers pass
state. Previously last_snapshot was always {} despite 51 snapshots on disk."
```

---

### Task 4: Self-heal state counters on resume

**Files:**
- Create: `src/shenbi/pipeline/state_heal.py`
- Modify: `src/shenbi/pipeline/cli.py:672-690` (`cmd_resume` — call `_heal_state_counters` after `load_state`)
- Test: `tests/unit/pipeline/test_state_heal.py`

**Interfaces:**
- Consumes: `PipelineState`, `_retry_key`, project dir layout (`snapshots/`, `chapters/chapter-N-revision-decisions.json`)
- Produces: `_heal_state_counters(state, project_dir) -> list[str]` (list of heal-action descriptions; empty = nothing healed). `cmd_resume` calls it right after `load_state`, before `_verify_truth_integrity`.

**Context:** Spec §3.4. After a crash, state counters may be stale. The healer cross-checks: `retry_budget_consumed` is seeded (min 1) for any `retry_feedback` key missing from the budget; `revision_count` is reconciled against the presence of a `chapters/chapter-N-revision-decisions.json` file (note: that file is overwritten per round, so disk presence is a floor, not exact history — log the caveat); `last_snapshot` is set to the newest on-disk snapshot if empty. Healing is conservative (never undercount consumed budget) and logged so it is auditable.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_state_heal.py
"""Tests for _heal_state_counters on resume (spec §3.4)."""
from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.state import PipelineState
from shenbi.pipeline.state_heal import _heal_state_counters


def test_heals_retry_budget_from_retry_feedback(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    s.chapter_loop.retry_feedback = {"ch1-shenbi-x": "G4 failed"}
    # retry_budget_consumed missing for that key.
    actions = _heal_state_counters(s, tmp_path)
    assert s.chapter_loop.retry_budget_consumed.get("ch1-shenbi-x") == 1
    assert any("retry_budget_consumed_healed" in a for a in actions)


def test_does_not_overwrite_existing_budget(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    s.chapter_loop.retry_feedback = {"ch1-x": "fail"}
    s.chapter_loop.retry_budget_consumed = {"ch1-x": 5}
    _heal_state_counters(s, tmp_path)
    assert s.chapter_loop.retry_budget_consumed["ch1-x"] == 5  # untouched


def test_heals_revision_count_from_disk(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    from shenbi.pipeline.state import ChapterState

    s.chapter_loop.chapter_states = {
        "3": ChapterState(revision_count=0, status="pending")
    }
    # Put a revision-decisions file on disk.
    (tmp_path / "chapters").mkdir(parents=True)
    (tmp_path / "chapters" / "chapter-3-revision-decisions.json").write_text("{}", encoding="utf-8")

    _heal_state_counters(s, tmp_path)
    assert s.chapter_loop.chapter_states["3"].revision_count >= 1


def test_heals_last_snapshot_from_disk(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    assert s.last_snapshot == {}
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    (snap_dir / "chapter-007-20260101T000000.md").write_text("# snap", encoding="utf-8")

    _heal_state_counters(s, tmp_path)
    assert s.last_snapshot, "last_snapshot should be healed from disk"
    assert s.last_snapshot["chapter"] == 7
    assert s.last_snapshot["path"].startswith("snapshots/")


def test_no_changes_returns_empty_actions(tmp_path: Path):
    s = PipelineState.default(project_dir=str(tmp_path))
    # Nothing on disk, no feedback, last_snapshot already empty is left empty.
    actions = _heal_state_counters(s, tmp_path)
    # No snapshots/revision files/feedback -> nothing to heal.
    assert actions == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_state_heal.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.pipeline.state_heal'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/pipeline/state_heal.py
"""Self-heal orphaned state counters on resume (spec §3.4).

After a crash, retry_budget_consumed / revision_count / last_snapshot may be
stale or empty. _heal_state_counters cross-checks each against disk reality
and repairs conservatively (never undercount consumed retry budget). Every
heal action is logged and returned as a description string for auditability.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.state import PipelineState

log = get_logger(__name__)

_SNAPSHOT_CHAPTER_RE = re.compile(r"chapter-(\d+)-")


def _extract_chapter_from_snapshot_name(name: str) -> int:
    m = _SNAPSHOT_CHAPTER_RE.search(name)
    return int(m.group(1)) if m else 0


def _heal_retry_budget(state: PipelineState, project_dir: Path) -> list[str]:
    """Seed retry_budget_consumed (min 1) for retry_feedback keys missing it."""
    actions: list[str] = []
    budget = state.chapter_loop.retry_budget_consumed
    for step_key in state.chapter_loop.retry_feedback:
        if step_key not in budget:
            budget[step_key] = 1
            log.warning(
                "retry_budget_consumed_healed",
                step_key=step_key,
                seeded_value=1,
                note="durable budget missing for key with retry_feedback",
            )
            actions.append(f"retry_budget_consumed_healed:{step_key}")
    return actions


def _heal_revision_counts(state: PipelineState, project_dir: Path) -> list[str]:
    """Reconcile revision_count with the presence of a revision-decisions file.

    Note (spec §3.4): the revision-decisions file is overwritten per round, so
    disk presence is a floor (0 or 1), not an exact revision history. Logged so
    the undercount is visible.
    """
    actions: list[str] = []
    for key, cs in state.chapter_loop.chapter_states.items():
        try:
            chapter_num = int(key)
        except ValueError:
            continue
        rev_path = project_dir / "chapters" / f"chapter-{chapter_num}-revision-decisions.json"
        disk_count = 1 if rev_path.exists() else 0
        if cs.revision_count != disk_count:
            log.warning(
                "revision_count_healed",
                chapter=chapter_num,
                state_value=cs.revision_count,
                disk_value=disk_count,
                note="disk_count undercounts: revision-decisions file is overwritten per round",
            )
            actions.append(f"revision_count_healed:ch{chapter_num}:{cs.revision_count}->{disk_count}")
            # Use max() so we don't lose the in-memory count if it's higher than the disk floor.
            cs.revision_count = max(cs.revision_count, disk_count)
    return actions


def _heal_last_snapshot(state: PipelineState, project_dir: Path) -> list[str]:
    """Point last_snapshot at the newest on-disk snapshot if it is empty."""
    if state.last_snapshot:
        return []
    snap_dir = project_dir / "snapshots"
    if not snap_dir.exists():
        return []
    snaps = sorted(snap_dir.glob("chapter-*.md"), key=lambda p: p.stat().st_mtime)
    if not snaps:
        return []
    latest = snaps[-1]
    state.last_snapshot = {
        "chapter": _extract_chapter_from_snapshot_name(latest.name),
        "path": str(latest.relative_to(project_dir)),
        "timestamp": datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc).strftime("%Y%m%dT%H%M%S"),
    }
    log.info("last_snapshot_healed", path=str(latest))
    return [f"last_snapshot_healed:{state.last_snapshot['path']}"]


def _heal_state_counters(state: PipelineState, project_dir: Path) -> list[str]:
    """Self-heal orphaned state counters by cross-checking against disk.

    Returns a list of heal-action description strings (empty == nothing healed).
    Safe to call on every resume; idempotent.
    """
    actions: list[str] = []
    actions += _heal_retry_budget(state, project_dir)
    actions += _heal_revision_counts(state, project_dir)
    actions += _heal_last_snapshot(state, project_dir)
    return actions
```

Then wire it into `cmd_resume` in `src/shenbi/pipeline/cli.py`. Right after `state = load_state(project_dir)` (the line inside `with WriteLock(project_dir):`), and before `_verify_truth_integrity(state, project_dir)`, add:

```python
            state = load_state(project_dir)

            # Self-heal orphaned counters/pointers from disk (spec §3.4):
            # retry_budget_consumed, revision_count, last_snapshot.
            from shenbi.pipeline.state_heal import _heal_state_counters

            _heal_state_counters(state, project_dir)

            # Persist healed values immediately so crash-resume sees them.
            save_state(project_dir, state)

            # Truth-integrity check (spec §3.4): verify truth files exist
            # before resuming, so missing files surface immediately rather than
            # on the first step dispatch.
            _verify_truth_integrity(state, project_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_state_heal.py tests/unit/pipeline/test_retry_budget.py tests/unit/pipeline/test_revision_count.py tests/unit/pipeline/test_last_snapshot.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/state_heal.py src/shenbi/pipeline/cli.py tests/unit/pipeline/test_state_heal.py
git commit -m "feat(state): self-heal retry_budget/revision_count/last_snapshot on resume

Spec 17 §3.4. _heal_state_counters runs after load_state in cmd_resume.
Seeds durable retry budget from retry_feedback, reconciles revision_count
with revision-decisions file presence, points last_snapshot at newest on-disk
snapshot. Conservative + idempotent + logged."
```

---

### Task 5: Regression verification

**Files:**
- No new files.

**Interfaces:**
- Consumes: all four prior tasks.

**Context:** Spec §5 verification: (1) `retry_budget_consumed` persists across success/reset; (2) retry limit enforced via `RetryExhaustedError`; (3) `revision_count` >= 1 after a revision route; (4) `last_snapshot` non-empty after snapshot; (5) self-heal on resume; (6) `just check` passes.

- [ ] **Step 1: Run the spec-17 suite**

Run: `uv run pytest tests/unit/pipeline/test_retry_budget.py tests/unit/pipeline/test_revision_count.py tests/unit/pipeline/test_last_snapshot.py tests/unit/pipeline/test_state_heal.py -v`
Expected: PASS.

- [ ] **Step 2: Run the full pipeline test set + check suite**

Run: `uv run pytest tests/unit/pipeline/ -v`
Expected: PASS.

Run: `just check`
Expected: PASS.

- [ ] **Step 3: Commit (only if fixes were needed)**

```bash
git add -A
git commit -m "test(state-counters): full regression green for spec 17"
```
