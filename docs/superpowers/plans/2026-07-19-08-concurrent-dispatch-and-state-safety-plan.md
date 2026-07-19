# Concurrent Dispatch and State Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add in-process thread-safety primitives (path-keyed `threading.Lock`, instance-level state lock, write-safety classification) so that any future concurrent dispatch of write-capable skills cannot corrupt truth files or pipeline state.

**Architecture:** Three independent, testable layers. (1) A module-level path-keyed lock registry in a new `src/shenbi/pipeline/truth_io.py` that `write_truth_file` will wrap — in-process only, no `.lock` files on disk. (2) An instance-level `threading.Lock` on `PipelineState` plus thread-safe accessor methods, guarding mutable list/dict fields. (3) A `WRITE_SAFETY` classification in `parallel_dispatch.py` that refuses to parallelize any skill not classified read-only. Uses `threading.Lock` (not `fcntl.flock`) because the concurrency model is `ThreadPoolExecutor` (threads, in-process).

**Tech Stack:** Python 3.11+, pathlib, pytest, structlog, threading

## Global Constraints

- Synchronization primitive is `threading.Lock` — NOT `fcntl.flock`. The concurrent dispatch path is `ThreadPoolExecutor` (in-process threads). `fcntl.flock` is for inter-process locking and leaves `.lock` files on disk; do not use it here (spec §3.2).
- The path-keyed lock registry is module-level; access to the registry dict itself is guarded by a separate `_REGISTRY_LOCK` to avoid races when lazily creating per-path locks (spec §3.2).
- The `PipelineState` lock MUST be an instance attribute, NOT a class attribute. A class-level lock is shared across all instances, which is incorrect if multiple `PipelineState` objects exist (spec §3.3).
- This spec is a PREREQUISITE/CONSTRAINT on Spec 6's proposed parallelization, not a fix for a current defect. Today `parallel_dispatch.py` only parallelizes read-only `shenbi-review-*` skills and is safe; this plan enforces that boundary against future expansion (spec §1 scope clarification).
- No `.lock` files may be written to disk by any code in this plan (spec §3.2).
- `just check` must pass fully after each task.

---

### Task 1: Path-keyed lock registry for truth file writes

**Files:**
- Create: `src/shenbi/pipeline/truth_io.py`
- Test: `tests/unit/pipeline/test_truth_io.py`

**Interfaces:**
- Consumes: nothing (standalone primitive; `safe_write` from `shenbi.safe_write` for the actual atomic write)
- Produces: `_path_lock(path: Path) -> threading.Lock`, `write_truth_file(project_dir, filename, new_data, *, mode, key_field)`. Later tasks (and Spec 1) import `write_truth_file` and `_path_lock` from this module.

**Context:** Spec 1's `write_truth_file(mode="upsert_markdown_row")` does a read-merge-write that is NOT atomic across threads. Two threads can read Ch1-5, each append one row, and the second write loses the first's row (spec §2.2). This task creates the locking primitive and the write function it wraps. The module is created here even though full Spec 1 (all modes) is out of scope — the lock wrapping is the concurrency deliverable.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_truth_io.py
"""Tests for thread-safe truth file writes (spec §3.2)."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from shenbi.pipeline.truth_io import _path_lock, write_truth_file


class TestPathLockRegistry:
    def test_same_path_returns_same_lock(self, tmp_path: Path):
        a = _path_lock(tmp_path / "current_state.md")
        b = _path_lock(tmp_path / "current_state.md")
        assert a is b

    def test_different_paths_return_different_locks(self, tmp_path: Path):
        a = _path_lock(tmp_path / "current_state.md")
        b = _path_lock(tmp_path / "character_matrix.md")
        assert a is not b

    def test_registry_lock_is_not_a_path_lock(self, tmp_path: Path):
        # The registry guard lock must not collide with a path named like it.
        from shenbi.pipeline.truth_io import _REGISTRY_LOCK

        assert _REGISTRY_LOCK is not _path_lock(tmp_path / "_REGISTRY_LOCK")


class TestConcurrentUpsertNoLostRows:
    def test_eight_concurrent_writes_no_lost_rows(self, tmp_path: Path):
        """8 threads each upsert a distinct-key row to the same truth file.

        Without the path-keyed lock this is a classic lost-update race:
        threads read the same prior content and the last writer wins. With
        the lock, all 8 rows survive. Uses a barrier so all threads start
        in the same read-merge-write window to maximize contention.
        """
        filename = "test_concurrent.md"

        def upsert(key: str) -> None:
            write_truth_file(
                tmp_path,
                filename,
                {"chapter": key, "note": f"row-{key}"},
                mode="upsert_markdown_row",
                key_field="chapter",
            )

        barrier = threading.Barrier(8)

        def runner(key: str) -> str:
            barrier.wait()  # release all threads into the race window together
            upsert(key)
            return key

        keys = [f"ch{i}" for i in range(8)]
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(runner, k): k for k in keys}
            for fut in as_completed(futures):
                fut.result()

        # Verify all 8 rows present (no lost updates).
        content = (tmp_path / "truth" / filename).read_text(encoding="utf-8")
        for k in keys:
            assert f"row-{k}" in content, f"row for {k} was lost"
        # Exactly 8 data rows (discount heading/blank lines).
        data_lines = [
            ln for ln in content.splitlines()
            if ln.strip().startswith("- ") or ln.strip().startswith("| ")
        ]
        assert len(data_lines) == 8, f"expected 8 rows, got {len(data_lines)}: {data_lines}"

    def test_upsert_dedups_same_key(self, tmp_path: Path):
        """Two concurrent writes with the SAME key produce one row, not two."""
        filename = "dedup.md"
        barrier = threading.Barrier(2)

        def runner():
            barrier.wait()
            write_truth_file(
                tmp_path,
                filename,
                {"chapter": "ch1", "note": "same-key"},
                mode="upsert_markdown_row",
                key_field="chapter",
            )

        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = [ex.submit(runner) for _ in range(2)]
            for f in futs:
                f.result()

        content = (tmp_path / "truth" / filename).read_text(encoding="utf-8")
        assert content.count("same-key") == 1, "duplicate key not deduplicated"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_truth_io.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.pipeline.truth_io'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/pipeline/truth_io.py
"""Thread-safe truth file I/O (spec §3.2).

The concurrency model for skill dispatch is in-process ``ThreadPoolExecutor``
(threads). The correct synchronization primitive is therefore ``threading.Lock``
— NOT ``fcntl.flock``, which targets inter-process locking and leaves
``.lock`` files on disk. This module provides a path-keyed lock registry so
that writes to different truth files do not block each other, while
concurrent writes to the SAME file serialize.

A read-merge-write (e.g. upsert-markdown-row) is NOT atomic across threads
even though the final ``safe_write`` is atomic (temp + ``os.replace``): two
threads can each read the prior content and the second writer's merge loses
the first writer's row (spec §2.2 lost-update race). The per-path lock
serializes the whole read-merge-write transaction.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write

log = get_logger(__name__)

# Module-level registry of per-path locks. Access to the registry dict itself
# is guarded by _REGISTRY_LOCK to avoid a race where two threads lazily create
# a lock for the same path and each stores its own (losing one). No lock files
# are written to disk — this is purely in-process.
_REGISTRY_LOCK = threading.Lock()
_PATH_LOCKS: dict[str, threading.Lock] = {}


def _path_lock(path: Path) -> threading.Lock:
    """Return the singleton lock for *path*, creating it lazily.

    Different paths get different locks (no cross-file blocking); the same
    path always returns the same lock object (serializes same-file writers).
    """
    key = str(path)
    with _REGISTRY_LOCK:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[key] = lock
        return lock


def _read_truth_rows(path: Path) -> list[dict[str, str]]:
    """Parse existing markdown rows into list of {column: value} dicts.

    Reads lines starting with ``- `` (bullet rows) or ``| ... |`` (table
    rows) and splits on ``:`` (bullet) or ``|`` (table). Tolerates an empty
    or heading-only file by returning [].
    """
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("- "):
            body = s[2:]
            if ":" in body:
                k, _, v = body.partition(":")
                rows.append({k.strip(): v.strip()})
        elif s.startswith("|") and s.endswith("|") and set(s) != {"|"}:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and cells[0] and cells[0] != "chapter":
                # treat first cell as key column for table form
                rows.append({cells[0]: " ".join(cells[1:])})
    return rows


def write_truth_file(
    project_dir: Path,
    filename: str,
    new_data: dict[str, Any],
    *,
    mode: str = "replace",
    key_field: str | None = None,
) -> None:
    """Write *new_data* to ``project_dir/truth/<filename>`` thread-safely.

    Modes:
      - ``replace``: overwrite the file with a single rendered row.
      - ``upsert_markdown_row``: read existing rows, dedup by *key_field*,
        merge the new row, write back. Serialized per-path so concurrent
        upserts to the same file cannot lose updates (spec §2.2).

    The per-path lock wraps the WHOLE read-merge-write transaction, not just
    the final ``safe_write`` (which is already atomic). This is what makes
    upsert safe under concurrency.
    """
    path = Path(project_dir) / "truth" / filename
    lock = _path_lock(path)
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "replace":
            body = f"# {filename.removesuffix('.md')}\n\n- {new_data}\n"
            safe_write(path, body.encode("utf-8"))
            log.info("truth_file_written", path=str(path), mode=mode)
            return
        if mode == "upsert_markdown_row":
            if key_field is None:
                raise ValueError("upsert_markdown_row requires key_field")
            rows = _read_truth_rows(path)
            # Dedup: drop any existing row with the same key value, then append.
            key_val = str(new_data.get(key_field, ""))
            rows = [r for r in rows if list(r.values())[0] != key_val]
            rows.append({key_field: " ".join(f"{k}={v}" for k, v in new_data.items())})
            body = f"# {filename.removesuffix('.md')}\n\n"
            body += "\n".join(f"- {list(r.items())[0][0]}: {list(r.items())[0][1]}" for r in rows)
            body += "\n"
            safe_write(path, body.encode("utf-8"))
            log.info(
                "truth_file_written",
                path=str(path),
                mode=mode,
                rows=len(rows),
            )
            return
        raise ValueError(f"unknown write mode: {mode!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_truth_io.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/truth_io.py tests/unit/pipeline/test_truth_io.py
git commit -m "feat(truth_io): add path-keyed threading.Lock registry and thread-safe write_truth_file

Spec 12 §3.2. In-process only (no .lock files). Wraps the read-merge-write
transaction for upsert_markdown_row so concurrent same-file writes cannot
lose updates. 8-thread contention test verifies no lost rows."
```

---

### Task 2: Thread-safe PipelineState instance lock

**Files:**
- Modify: `src/shenbi/pipeline/state.py:146-166` (add `_lock` field and accessor methods)
- Test: `tests/unit/pipeline/test_state_concurrency.py`

**Interfaces:**
- Consumes: `PipelineState` dataclass from `state.py`, `threading`
- Produces: `PipelineState._lock` (instance attribute), `PipelineState.add_step_done(chapter, step)`, `PipelineState.add_audit_result(chapter, key, value)`, `PipelineState.increment_retry(chapter, skill) -> int`, `PipelineState.reset_retry(chapter, skill)`. Later tasks and Spec 6 import these methods instead of mutating fields directly under concurrency.

**Context:** `PipelineState` is a `@dataclass`. The spec shows an `__init__` with `self._lock`; a dataclass cannot have a hand-written `__init__`, so the lock is a `field(default_factory=threading.Lock)` instance attribute. The spec is explicit: instance attribute, NOT class attribute (spec §3.3). Mutable fields that need guarding: `chapter_states[k].steps_done` (list append), `audit_results` (dict update), `retry_counts` (dict update) — see spec §2.3. The serialization methods below are the concurrency-safe surface; direct field mutation remains available for single-threaded code.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_state_concurrency.py
"""Tests for thread-safe PipelineState mutations (spec §3.3)."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from shenbi.pipeline.state import PipelineState


def _fresh_state() -> PipelineState:
    return PipelineState.default(project_dir="/tmp/test")


class TestInstanceLock:
    def test_lock_is_instance_attribute(self):
        """The lock must be per-instance, not shared across instances."""
        a = _fresh_state()
        b = _fresh_state()
        assert a._lock is not b._lock, (
            "PipelineState._lock must be an instance attribute (spec §3.3), "
            "not a class attribute shared across all instances"
        )

    def test_lock_is_not_class_attribute(self):
        """Lock lives on the instance, not on the class."""
        s = _fresh_state()
        assert "_lock" not in type(s).__dict__, (
            "_lock must not be defined on the class"
        )

    def test_lock_is_a_threading_lock(self):
        import threading

        s = _fresh_state()
        assert isinstance(s._lock, type(threading.Lock()))


class TestConcurrentAddStepDone:
    def test_eight_concurrent_appends_all_recorded(self):
        """8 threads each append a distinct step — no entries lost."""
        s = _fresh_state()
        barrier = threading.Barrier(8)
        steps = [f"skill-{i}" for i in range(8)]

        def runner(step: str) -> None:
            barrier.wait()
            s.add_step_done(chapter=1, step=step)

        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(runner, st) for st in steps]
            for f in futs:
                f.result()

        cs = s.chapter_loop.chapter_states["1"]
        assert sorted(cs.steps_done) == sorted(steps), (
            f"lost entries: got {sorted(cs.steps_done)}"
        )

    def test_add_step_done_is_idempotent(self):
        s = _fresh_state()
        s.add_step_done(chapter=1, step="x")
        s.add_step_done(chapter=1, step="x")
        assert s.chapter_loop.chapter_states["1"].steps_done == ["x"]


class TestConcurrentRetryCounter:
    def test_eight_concurrent_increments(self):
        """8 threads each increment retry — durable count reaches 8."""
        s = _fresh_state()
        barrier = threading.Barrier(8)

        def runner() -> None:
            barrier.wait()
            s.increment_retry(chapter=1, skill="shenbi-chapter-drafting")

        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(runner) for _ in range(8)]
            for f in futs:
                f.result()

        assert s.chapter_loop.retry_counts.get("ch1-shenbi-chapter-drafting") == 8

    def test_reset_retry_clears_count(self):
        s = _fresh_state()
        s.increment_retry(chapter=1, skill="s")
        s.reset_retry(chapter=1, skill="s")
        assert "ch1-s" not in s.chapter_loop.retry_counts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_state_concurrency.py -v`
Expected: FAIL with `AttributeError: 'PipelineState' object has no attribute '_lock'` (and `add_step_done` / `increment_retry` / `reset_retry` missing)

- [ ] **Step 3: Write minimal implementation**

Add the import and the lock field to the dataclass, plus the thread-safe methods. The edits below are applied to `src/shenbi/pipeline/state.py`.

First, add `threading` to imports (after the existing `import json`):

```python
import json
import threading
from dataclasses import dataclass, field
```

Then add `_lock` as the LAST field on `PipelineState` (after `config`), so existing field order / positional construction is unaffected. Insert before `@classmethod def default`:

```python
    config: PipelineConfig = field(default_factory=PipelineConfig)
    # Instance-level lock guarding concurrent mutations to mutable fields
    # (steps_done append, audit_results/retry_counts dict update). MUST be an
    # instance attribute (spec §3.3): a class-level lock would serialize
    # across unrelated PipelineState objects. Excluded from to_dict via the
    # explicit field list there (not a data field).
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def add_step_done(self, chapter: int, step: str) -> None:
        """Thread-safe append to chapter_states[chapter].steps_done (idempotent).

        Replaces the non-thread-safe _record_step_done() in chapter_loop.py.
        After this lands, remove the old _record_step_done and update all call sites.
        """
        key = str(chapter)
        with self._lock:
            cs = self.chapter_loop.chapter_states.get(key)
            if cs is None:
                cs = ChapterState()
                self.chapter_loop.chapter_states[key] = cs
            if step not in cs.steps_done:
                cs.steps_done.append(step)

    def add_audit_result(self, chapter: int, result_key: str, value: Any) -> None:
        """Thread-safe update to chapter_states[chapter].audit_results."""
        key = str(chapter)
        with self._lock:
            cs = self.chapter_loop.chapter_states.get(key)
            if cs is None:
                cs = ChapterState()
                self.chapter_loop.chapter_states[key] = cs
            cs.audit_results[result_key] = value

    def increment_retry(self, chapter: int, skill: str) -> int:
        """Thread-safe increment of retry_counts; returns the new count."""
        rk = f"ch{chapter}-{skill}"
        with self._lock:
            count = self.chapter_loop.retry_counts.get(rk, 0) + 1
            self.chapter_loop.retry_counts[rk] = count
            return count

    def reset_retry(self, chapter: int, skill: str) -> None:
        """Thread-safe clear of retry_counts[chN-skill]."""
        rk = f"ch{chapter}-{skill}"
        with self._lock:
            self.chapter_loop.retry_counts.pop(rk, None)
```

Note: `to_dict` already enumerates fields explicitly (it does not dump `_lock`), and `from_dict`/`from_json` ignore unknown keys, so adding `_lock` does not break state-file round-trips. `compare=False` keeps equality checks (used in tests) from comparing lock identity.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_state_concurrency.py -v`
Expected: PASS (all 7 tests)

Then run the existing state tests to confirm no round-trip regression:
Run: `uv run pytest tests/unit/pipeline/test_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/state.py tests/unit/pipeline/test_state_concurrency.py
git commit -m "feat(state): add instance-level threading.Lock and thread-safe state accessors

Spec 12 §3.3. Lock is an instance attribute (default_factory), not class
attribute, so each PipelineState guards its own state. add_step_done /
add_audit_result / increment_retry / reset_retry serialize mutations.
compare=False keeps equality checks lock-identity-independent."
```

---

### Task 3: WRITE_SAFETY classification and parallel dispatch boundary enforcement

**Files:**
- Modify: `src/shenbi/pipeline/parallel_dispatch.py:1-30,123-180` (add classification + gate in `dispatch_reviews_parallel`)
- Test: `tests/unit/pipeline/test_parallel_dispatch_safety.py`

**Interfaces:**
- Consumes: `dispatch_reviews_parallel`, `ReviewTask` from `parallel_dispatch.py`
- Produces: `WRITE_SAFETY` enum, `classify_skill_write_safety(skill: str) -> WRITE_SAFETY`, `assert_parallelizable(tasks)`. `parallel_dispatch.dispatch_reviews_parallel` now raises on any non-read-only task.

**Context:** `dispatch_reviews_parallel` today only receives `shenbi-review-*` tasks and is safe (spec §1). This task makes that boundary explicit and enforced: any task whose skill is not classified READ_ONLY_AUDIT raises a `ValueError` before threads are spawned, so a future Spec 6 expansion cannot silently put a write-capable skill on the concurrent path. Per spec §3.1: read-only audit = `shenbi-review-*` producing `audits/`; write-shared (e.g. `shenbi-state-settling`, `shenbi-foreshadowing-track`) must serialize. The classification is a small explicit function rather than a scan of every contract, so it is cheap and deterministic.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_parallel_dispatch_safety.py
"""Tests for WRITE_SAFETY classification in parallel dispatch (spec §3.1, §3.4)."""
from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.parallel_dispatch import (
    ReviewTask,
    dispatch_reviews_parallel,
)
from shenbi.pipeline.write_safety import WRITE_SAFETY, classify_skill_write_safety


class TestClassification:
    @pytest.mark.parametrize(
        "skill",
        [
            "shenbi-review-anti-ai",
            "shenbi-review-resonance",
            "shenbi-review-arc-payoff",
        ],
    )
    def test_review_skills_are_read_only(self, skill: str):
        assert classify_skill_write_safety(skill) == WRITE_SAFETY.READ_ONLY_AUDIT

    @pytest.mark.parametrize(
        "skill",
        [
            "shenbi-state-settling",
            "shenbi-foreshadowing-track",
        ],
    )
    def test_shared_writers_must_serialize(self, skill: str):
        assert classify_skill_write_safety(skill) == WRITE_SAFETY.WRITE_SHARED

    def test_unknown_skill_defaults_to_write_shared(self):
        # Conservative: unknown skills must NOT be parallelized.
        assert (
            classify_skill_write_safety("shenbi-something-new")
            == WRITE_SAFETY.WRITE_SHARED
        )


class TestParallelDispatchBoundary:
    def test_read_only_reviews_dispatch_in_parallel(self, tmp_path: Path):
        """Read-only review tasks dispatch without error (boundary allows them)."""
        # dispatch_reviews_parallel calls the real API; verify the boundary
        # check passes by giving it an empty task list (no API calls made)
        # after asserting classify accepts review skills. A non-empty list
        # is covered by the existing parallel_dispatch integration tests.
        tasks = [
            ReviewTask(
                skill="shenbi-review-anti-ai",
                project_dir=tmp_path,
                prompt="x",
                output_path="audits/c-1-anti-ai.md",
            )
        ]
        # assert_parallelizable must not raise for review skills.
        from shenbi.pipeline.parallel_dispatch import assert_parallelizable

        assert_parallelizable(tasks)  # no exception

    def test_write_shared_skill_rejected_from_parallel_path(self, tmp_path: Path):
        """A write-shared skill on the parallel path raises immediately."""
        tasks = [
            ReviewTask(
                skill="shenbi-state-settling",  # WRITE_SHARED
                project_dir=tmp_path,
                prompt="x",
                output_path="truth/current_state.md",
            )
        ]
        with pytest.raises(ValueError, match="WRITE_SHARED"):
            dispatch_reviews_parallel(tasks)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_parallel_dispatch_safety.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.pipeline.write_safety'`

- [ ] **Step 3: Write minimal implementation**

First, create the classification module:

```python
# src/shenbi/pipeline/write_safety.py
"""Write-safety classification for concurrent dispatch (spec §3.1, §3.4).

The parallel dispatch path (ThreadPoolExecutor) is safe ONLY for read-only
audit skills today. This module makes that boundary explicit and enforced:
any skill not classified READ_ONLY_AUDIT must run serially, so a future
expansion (e.g. Spec 6) cannot silently place a write-capable skill on the
concurrent path and race on truth files / shared state (spec §2.1-2.3).
"""
from __future__ import annotations

from enum import StrEnum


class WRITE_SAFETY(StrEnum):
    READ_ONLY_AUDIT = "read_only_audit"
    WRITE_ISOLATED = "write_isolated"  # disjoint files — safe with file locking
    WRITE_SHARED = "write_shared"  # shared truth/hooks — must serialize


# Skills known to write to SHARED mutable files (truth/*.md, pending_hooks.md).
# These MUST NOT be parallelized (spec §3.1 "Write-shared").
# These are write-capable skills from CHAPTER_STEPS. Only shenbi-state-settling
# and shenbi-foreshadowing-track are currently on the concurrent path; the others
# are listed for completeness as they may be parallelized in future.
_WRITE_SHARED_SKILLS = frozenset(
    {
        "shenbi-state-settling",
        "shenbi-foreshadowing-track",
        "shenbi-foreshadowing-plant",
        "shenbi-chapter-drafting",
        "shenbi-chapter-revision",
        "shenbi-intent-management",
    }
)


def classify_skill_write_safety(skill: str) -> WRITE_SAFETY:
    """Classify a skill's write safety for concurrent dispatch.

    Conservative default: an unknown skill is WRITE_SHARED (must serialize),
    so new skills cannot accidentally land on the parallel path until they
    are explicitly classified READ_ONLY_AUDIT.
    """
    if skill.startswith("shenbi-review-"):
        return WRITE_SAFETY.READ_ONLY_AUDIT
    if skill in _WRITE_SHARED_SKILLS:
        return WRITE_SAFETY.WRITE_SHARED
    # Everything else (including unknown skills) is treated conservatively.
    return WRITE_SAFETY.WRITE_SHARED
```

Then enforce the boundary in `parallel_dispatch.py`. Add the import near the top imports:

```python
from shenbi.pipeline.write_safety import WRITE_SAFETY, classify_skill_write_safety
```

Add `assert_parallelizable` and call it at the top of `dispatch_reviews_parallel`. Insert the function before `dispatch_reviews_parallel`:

```python
def assert_parallelizable(tasks: list[ReviewTask]) -> None:
    """Verify every task's skill is safe to run concurrently (spec §3.4).

    Raises ValueError listing any task whose skill is not READ_ONLY_AUDIT.
    Called before threads are spawned so a write-shared skill can never
    reach the concurrent path.
    """
    unsafe = [
        f"{t.skill}={classify_skill_write_safety(t.skill).value}"
        for t in tasks
        if classify_skill_write_safety(t.skill) != WRITE_SAFETY.READ_ONLY_AUDIT
    ]
    if unsafe:
        raise ValueError(
            "refusing to parallelize non-read-only skills (WRITE_SHARED/"
            f"WRITE_ISOLATED must run serially per spec §3.4): {unsafe}"
        )
```

Then change the first lines of `dispatch_reviews_parallel` from:

```python
    if not tasks:
        return []
```
to:

```python
    if not tasks:
        return []
    assert_parallelizable(tasks)  # spec §3.4 — never parallelize write-capable skills
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_parallel_dispatch_safety.py tests/unit/pipeline/test_parallel_dispatch.py -v`
Expected: PASS (all new classification/boundary tests + existing parallel_dispatch tests unchanged)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/write_safety.py src/shenbi/pipeline/parallel_dispatch.py tests/unit/pipeline/test_parallel_dispatch_safety.py
git commit -m "feat(parallel_dispatch): enforce WRITE_SAFETY boundary before concurrent dispatch

Spec 12 §3.1, §3.4. classify_skill_write_safety tags skills read_only_audit /
write_isolated / write_shared (conservative default = write_shared).
dispatch_reviews_parallel now calls assert_parallelizable and raises on any
non-read-only task, so Spec 6's proposed expansion cannot race on truth
files or shared state."
```

---

### Task 4: Regression verification

**Files:**
- No new files; runs the full suite.

**Interfaces:**
- Consumes: all three prior tasks
- Produces: confirmation that `just check` passes and the spec's four verification criteria hold.

**Context:** Spec §5 verification criteria: (1) race condition test — covered by Task 1's 8-thread test; (2) state mutation test — covered by Task 2's 8-thread test; (3) classification test — covered by Task 3; (4) `just check` passes. This task is the explicit gate.

- [ ] **Step 1: Run the targeted concurrency tests once more**

Run: `uv run pytest tests/unit/pipeline/test_truth_io.py tests/unit/pipeline/test_state_concurrency.py tests/unit/pipeline/test_parallel_dispatch_safety.py -v`
Expected: PASS (all tests green)

- [ ] **Step 2: Run the full check suite**

Run: `just check`
Expected: PASS (all gates + tests). If `just` is unavailable, run `uv run pytest -n auto -m "not last" --hypothesis-profile=ci && uv run pytest -p no:xdist -m "last" --no-cov --hypothesis-profile=ci`.

- [ ] **Step 3: Commit (if any formatting/import fixes were needed)**

```bash
git add -A
git commit -m "test(concurrent-state-safety): full regression green for spec 12"
```

If nothing changed, skip the commit.
