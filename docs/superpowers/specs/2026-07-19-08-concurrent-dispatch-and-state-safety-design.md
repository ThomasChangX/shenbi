# Spec 12: Concurrent Dispatch and State Safety Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** High
> **Source:** SHOUT-OUT — discovered during cross-spec review of Specs 1-11
> **Relationship:** Independent of Specs 1-11, but interacts with Spec 6 (parallelization) and Spec 1 (truth file writes)

---

## 1. Executive Summary

> **IMPORTANT — Scope clarification:** This spec is a PREREQUISITE/CONSTRAINT on Spec 6's proposed parallelization expansion, NOT a fix for a current defect. The current `parallel_dispatch.py` only parallelizes read-only audit skills (`shenbi-review-*`). The race conditions described here will ONLY manifest if Spec 6's proposed state-settling || foreshadowing-lifecycle parallelization is implemented.

The existing `parallel_dispatch.py` (`src/shenbi/pipeline/parallel_dispatch.py`, 223 lines) uses `ThreadPoolExecutor` + `Semaphore(MAX_CONCURRENT_REVIEWS=4)` to dispatch audit reviews in two parallel waves (`chapter_loop.py:1090-1168`). This was verified during the Spec 6 review. The current design is SAFE because it ONLY parallelizes read-only audit skills (`shenbi-review-*`) that produce audit reports and do not mutate shared state.

The state-safety concerns below are a CONSTRAINT on any future expansion (e.g., Spec 6's proposal to parallelize state-settling || foreshadowing-lifecycle). They describe risks that will manifest ONLY IF write-capable skills are placed on the concurrent dispatch path. No spec in the existing 1-11 set establishes these constraints:

1. **Truth file write races:** IF multiple write-capable skills run concurrently and each triggers state-settling (which writes to `truth/*.md` via `safe_write`), concurrent writes to the same truth file could corrupt data — even though `safe_write` uses `os.replace` (atomic), the read-merge-write sequence in append-mode files (Spec 1's `write_truth_file`) is NOT atomic across threads.

2. **Staging directory races:** IF multiple concurrent dispatches that use staging are placed on the parallel path, they could overwrite each other's staging files before `commit_staging()` runs.

3. **Pipeline state mutation:** `PipelineState` is a mutable object passed to `run_triggered_skills` and audit dispatch. IF write-capable skills mutate it concurrently, mutations to `cs.steps_done`, `cs.audit_results`, retry counters would not be thread-safe.

4. **G4 gate execution:** G4 runs after each dispatch. IF multiple G4 checks ran concurrently against the same output directory, they could see partial writes from other concurrent skills.

**Root cause (prospective):** The parallel dispatch infrastructure exists and is correctly scoped to read-only audit skills today. It was deliberately designed for read-only audits. If Spec 6's expansion is implemented without the constraints in this spec, the thread-safety assumptions will break.

---

## 2. Root Cause Analysis

### 2.1 ThreadPoolExecutor Without State Isolation

`parallel_dispatch.py` dispatches skills via `dispatch_skill()` in worker threads. Each thread:
- Calls `dispatch_skill()` which writes output files via `_write_parsed_outputs` → `safe_write`
- Runs G4 via `run_gate_g4()`
- On success, the main thread advances state

The problem: `dispatch_skill` and `run_gate_g4` both read/write to the shared `project_dir` filesystem. While individual `safe_write` calls are atomic (temp + os.replace), multi-file transactions are not.

### 2.2 Append-Mode Truth File Race (Interaction with Spec 1)

Spec 1's `write_truth_file(mode="upsert_markdown_row")` does:
1. Read existing file
2. Parse rows
3. Deduplicate by key
4. Write merged content

If two threads execute this concurrently on the same file:
- Thread A reads Ch1-5 rows
- Thread B reads Ch1-5 rows
- Thread A appends Ch6, writes Ch1-6
- Thread B appends Ch7, writes Ch1-5,7 (Ch6 lost!)

This is a classic lost-update race.

### 2.3 PipelineState Mutation Without Locks

`PipelineState` dataclass fields like `cs.steps_done` (list append), `cs.audit_results` (dict update) are mutated without synchronization. While Python's GIL prevents memory corruption, concurrent list/dict mutations can still lose entries.

---

## 3. Fix Strategy

### 3.1 Classify Skills by Write Safety

Create a `WRITE_SAFETY` classification:

| Category | Skills | Concurrent? |
|----------|--------|-------------|
| **Read-only audit** | All `shenbi-review-*` skills that only produce `audits/chapter-N-*.md` | ✅ Safe to parallelize |
| **Write-isolated** | Skills that write to disjoint files (different truth files, different staging subdirs) | ⚠️ Safe with file-level locking |
| **Write-shared** | `shenbi-state-settling` (writes to shared truth files), `shenbi-foreshadowing-track` (writes to pending_hooks.md) | ❌ Must serialize |

### 3.2 File-Level Locking for Truth File Writes

The concurrency model is in-process `ThreadPoolExecutor` (threads, not processes). Therefore the correct synchronization primitive is `threading.Lock` — NOT `fcntl.flock`, which is for inter-process locking and creates unwanted filesystem side-effects (`.lock` files). Use a `threading.Lock` keyed by file path so that writes to different files do not block each other, while concurrent writes to the same file serialize.

Add a path-keyed lock registry in `write_truth_file()` (Spec 1):

```python
import threading
from pathlib import Path

# Module-level registry of per-path locks. Access to the registry itself
# is guarded by _REGISTRY_LOCK to avoid races when lazily creating locks.
_REGISTRY_LOCK = threading.Lock()
_PATH_LOCKS: dict[str, threading.Lock] = {}

def _path_lock(path: Path) -> threading.Lock:
    key = str(path)
    with _REGISTRY_LOCK:
        if key not in _PATH_LOCKS:
            _PATH_LOCKS[key] = threading.Lock()
        return _PATH_LOCKS[key]

def write_truth_file(project_dir, filename, new_data, *, mode="replace", key_field=None):
    path = project_dir / "truth" / filename
    lock = _path_lock(path)  # Block other threads writing THIS file only
    with lock:
        # ... existing read-merge-write logic ...
```

This is in-process only; no `.lock` files are written to disk.

### 3.3 Thread-Safe PipelineState Access

Wrap `PipelineState` mutations in a `threading.Lock`. The lock MUST be an instance attribute (created in `__init__`), NOT a class attribute. A class-level lock is shared across all instances, which is incorrect if multiple `PipelineState` objects are ever created (each instance should guard its own state independently).

```python
import threading

class PipelineState:
    def __init__(self, ...):
        # ... existing init ...
        self._lock = threading.Lock()  # INSTANCE attribute, not class attribute

    def add_step_done(self, step: str):
        with self._lock:
            self.chapter_loop.steps_done.append(step)
```

### 3.4 Concurrency Boundary Enforcement

Modify `parallel_dispatch.py` to only parallelize skills classified as "Read-only audit". Skills classified as "Write-shared" must run serially, even if Spec 6 proposes otherwise.

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/pipeline/parallel_dispatch.py` | Add WRITE_SAFETY classification check | Prevent unsafe concurrent dispatch |
| `src/shenbi/pipeline/truth_io.py` (Spec 1) | Add path-keyed `threading.Lock` around read-merge-write | Prevent lost-update race on truth files (in-process, no `.lock` files) |
| `src/shenbi/pipeline/state.py` | Add instance-level `self._lock = threading.Lock()` for mutable fields | Prevent concurrent state corruption (instance-scoped, not class-shared) |
| `src/shenbi/pipeline/chapter_loop.py:1090-1168` | Verify only read-only audits are parallelized | Enforce concurrency boundary |

---

## 5. Verification Criteria

1. **Race condition test:** 4 concurrent `write_truth_file` calls on the same file → no lost rows
2. **State mutation test:** 4 concurrent `add_step_done` calls → all 4 steps recorded
3. **Classification test:** state-settling is classified "Write-shared" and runs serially even in parallel mode
4. **Regression:** `just check` passes fully

---

## 6. Dependencies

```
Spec 12 (this spec, Concurrent Dispatch and State Safety)
    |
    +---> Depends on: Spec 1 (truth_io.py write_truth_file) -- locking wraps this
    +---> Interacts with: Spec 6 (parallelization) -- constrains what can be parallelized

Prerequisites: Spec 1's write_truth_file must exist before adding locking
```
