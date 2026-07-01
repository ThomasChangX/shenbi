# Novel Pipeline Wave 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pipeline state machine core, CLI command interface, seed file parser, and file locking — the foundation that all subsequent waves (retrieval, orchestrators, integration) build upon.

**Architecture:** Python state machine in `src/shenbi/pipeline/` following existing patterns (`phase_runner.py`, `status.py`, `safe_write.py`). The state machine is project-scoped, process-stateless, serializes to `pipeline-state.json`, and uses read/write lock separation for multi-user concurrency.

**Tech Stack:** Python 3.11+, pathlib, json, filelock (new dep), pyyaml, structlog, argparse, pytest

**Spec reference:** `docs/superpowers/specs/2026-07-01-novel-pipeline-design.md` Sections 2-4, 9

## Global Constraints

- Python 3.11+, `from __future__ import annotations` in all new files
- `pathlib.Path` for all file I/O, `json` for structured output
- No `print()` in framework code; use structlog (stderr) + `cli_utils.emit_json` (stdout)
- `safe_write` for all state file writes (atomic, fsync, lock)
- Typed enums via `StrEnum` (matching `status.py` pattern)
- Tests in `tests/unit/pipeline/`
- Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`
- `filelock` is a new dependency — add to `pyproject.toml [project] dependencies`

---

## File Structure

```
src/shenbi/pipeline/
    __init__.py           # package init
    state.py              # PipelinePhase, PipelineState enums + dataclasses
    machine.py            # state machine: load/save/transition logic
    seed_parser.py        # parse seed file -> novel.json + genesis context
    checkpoint.py         # checkpoint types + staging commit/rollback
    filelock_utils.py     # read/write lock helpers
    cli.py                # argparse CLI entry point

tests/unit/pipeline/
    __init__.py
    conftest.py           # shared fixtures (tmp project, sample seed)
    test_state.py         # state enum/dataclass tests
    test_machine.py       # state transition tests
    test_seed_parser.py   # seed parsing tests
    test_checkpoint.py    # checkpoint + staging tests
    test_filelock_utils.py # lock tests
    test_cli.py           # CLI integration tests
```

---

### Task 1: Pipeline State Types

**Files:**
- Create: `src/shenbi/pipeline/__init__.py`
- Create: `src/shenbi/pipeline/state.py`
- Create: `tests/unit/pipeline/__init__.py`
- Create: `tests/unit/pipeline/conftest.py`
- Create: `tests/unit/pipeline/test_state.py`

**Interfaces:**
- Produces: `PipelinePhase`, `GenesisState`, `ClosureState`, `CheckpointType`, `ReviewDecision` (StrEnums); `PipelineState`, `GenesisStateData`, `ChapterLoopStateData`, `ClosureStateData`, `CheckpointData`, `PipelineConfig` (dataclasses)

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/pipeline/test_state.py
"""Tests for pipeline state types."""

from __future__ import annotations

import json

from shenbi.pipeline.state import (
    ChapterLoopStateData,
    CheckpointData,
    CheckpointType,
    ClosureState,
    GenesisState,
    PipelineConfig,
    PipelinePhase,
    PipelineState,
    ReviewDecision,
)


class TestPipelineEnums:
    def test_pipeline_phase_values(self):
        assert PipelinePhase.GENESIS == "genesis"
        assert PipelinePhase.CHAPTER_LOOP == "chapter-loop"
        assert PipelinePhase.CLOSURE == "closure"
        assert PipelinePhase.COMPLETED == "completed"
        assert PipelinePhase.FAILED == "failed"

    def test_checkpoint_type_values(self):
        assert CheckpointType.NONE == "none"
        assert CheckpointType.GENESIS_COMPLETE == "genesis-complete"
        assert CheckpointType.CHAPTER_MEMO == "chapter-memo"
        assert CheckpointType.STATE_SETTLE == "state-settle"
        assert CheckpointType.ESCALATION == "escalation"
        assert CheckpointType.PER_CHAPTER == "per-chapter"
        assert CheckpointType.VOLUME_BOUNDARY == "volume-boundary"
        assert CheckpointType.BOOK_CLOSURE == "book-closure"

    def test_review_decision_values(self):
        assert ReviewDecision.APPROVE == "approve"
        assert ReviewDecision.MODIFY == "modify"
        assert ReviewDecision.REJECT == "reject"


class TestPipelineStateSerialization:
    def test_default_state(self):
        state = PipelineState.default(project_dir="/tmp/novel")
        assert state.phase == PipelinePhase.GENESIS
        assert state.genesis.state == GenesisState.PENDING
        assert state.pending_checkpoint.type == CheckpointType.NONE
        assert state.config.max_revision_retries == 3
        assert state.config.resonance_global_floor == 50

    def test_to_json_round_trip(self):
        state = PipelineState.default(project_dir="/tmp/novel")
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.skills_done = ["shenbi-worldbuilding"]
        state.chapter_loop.current_chapter = 5
        state.chapter_loop.current_step = "chapter-planning"

        json_str = state.to_json()
        restored = PipelineState.from_json(json_str)

        assert restored.phase == PipelinePhase.GENESIS
        assert restored.genesis.skills_done == ["shenbi-worldbuilding"]
        assert restored.chapter_loop.current_chapter == 5
        assert restored.chapter_loop.current_step == "chapter-planning"

    def test_checkpoint_round_trip(self):
        state = PipelineState.default(project_dir="/tmp/novel")
        state.pending_checkpoint = CheckpointData(
            type=CheckpointType.CHAPTER_MEMO,
            chapter=5,
            artifact="plans/chapter-5-plan.md",
            context="Review chapter memo",
            options=["approve", "modify", "reject"],
        )
        restored = PipelineState.from_json(state.to_json())
        assert restored.pending_checkpoint.type == CheckpointType.CHAPTER_MEMO
        assert restored.pending_checkpoint.chapter == 5
        assert restored.pending_checkpoint.artifact == "plans/chapter-5-plan.md"
```

```python
# tests/unit/pipeline/conftest.py
"""Shared fixtures for pipeline tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Temporary novel project directory."""
    project = tmp_path / "novel-project"
    project.mkdir()
    return project


@pytest.fixture
def sample_seed_content() -> str:
    """Minimal seed file content matching outline-example.md format."""
    return """# Test Novel

## Basic Info
- Genre: fantasy, adventure
- Era: medieval
- Core concept: A test novel
- Target word count: 200000
- Ending direction: Happy ending

## Protagonist
- Name: Test Hero
- Personality: brave, curious

## World Rules
- Rule 1: Magic exists
- Rule 2: Dragons are real

## Core Conflict
- Surface: Kingdom at war
- Personal: Hero seeks revenge
- Deep: Freedom vs duty

## Three-Act Structure
- Act 1: Hero discovers powers
- Act 2: Hero trains and fights
- Act 3: Hero saves kingdom

## Narrative Techniques
- Show/Tell ratio: 70/30
- Deep themes: courage, sacrifice
"""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.pipeline'`

- [ ] **Step 3: Write the implementation**

```python
# src/shenbi/pipeline/__init__.py
"""Pipeline orchestration package."""
```

```python
# src/shenbi/pipeline/state.py
"""Typed state vocabulary and dataclasses for the novel pipeline state machine.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class PipelinePhase(StrEnum):
    GENESIS = "genesis"
    CHAPTER_LOOP = "chapter-loop"
    CLOSURE = "closure"
    COMPLETED = "completed"
    FAILED = "failed"


class GenesisState(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    CHECKPOINT_PENDING = "checkpoint-pending"
    COMPLETED = "completed"


class ClosureState(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    CHECKPOINT_PENDING = "checkpoint-pending"
    COMPLETED = "completed"


class CheckpointType(StrEnum):
    NONE = "none"
    GENESIS_COMPLETE = "genesis-complete"
    CHAPTER_MEMO = "chapter-memo"
    STATE_SETTLE = "state-settle"
    ESCALATION = "escalation"
    PER_CHAPTER = "per-chapter"
    VOLUME_BOUNDARY = "volume-boundary"
    BOOK_CLOSURE = "book-closure"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    MODIFY = "modify"
    REJECT = "reject"


@dataclass
class PipelineConfig:
    genesis_review_required: bool = True
    chapter_memo_review_required: bool = True
    state_settle_review_required: bool = True
    per_chapter_review_enabled: bool = True
    volume_boundary_review_required: bool = True
    max_revision_retries: int = 3
    max_audit_retries: int = 3
    context_budget_override: int | None = None
    style_learning_interval: int = 12
    genre_config_update_on_drift: bool = True
    resonance_global_floor: int = 50
    snapshot_retention_chapters: int = 50


@dataclass
class CheckpointData:
    type: CheckpointType = CheckpointType.NONE
    chapter: int | None = None
    artifact: str | None = None
    context: str | None = None
    options: list[str] = field(default_factory=list)
    created_at: str | None = None


@dataclass
class GenesisStateData:
    state: GenesisState = GenesisState.PENDING
    current_step: int = 0
    skills_done: list[str] = field(default_factory=list)
    retry_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class ChapterState:
    steps_done: list[str] = field(default_factory=list)
    status: str = "pending"
    resonance_score: int | None = None
    audit_results: dict[str, Any] = field(default_factory=dict)
    revision_count: int = 0


@dataclass
class ChapterLoopStateData:
    current_chapter: int = 0
    current_step: str = ""
    step_index: int = 0
    chapter_states: dict[str, ChapterState] = field(default_factory=dict)
    per_chapter_review_enabled: bool = True
    retry_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class PipelineState:
    version: int = 1
    project_dir: str = ""
    phase: PipelinePhase = PipelinePhase.GENESIS
    genesis: GenesisStateData = field(default_factory=GenesisStateData)
    chapter_loop: ChapterLoopStateData = field(default_factory=ChapterLoopStateData)
    closure: ClosureState = ClosureState.PENDING
    pending_checkpoint: CheckpointData = field(default_factory=CheckpointData)
    checkpoint_history: list[dict[str, Any]] = field(default_factory=list)
    last_snapshot: dict[str, Any] = field(default_factory=dict)
    closure_step: int = 0  # tracks closure progress (persisted)
    config: PipelineConfig = field(default_factory=PipelineConfig)

    @classmethod
    def default(cls, project_dir: str) -> PipelineState:
        return cls(project_dir=project_dir)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "project_dir": self.project_dir,
            "phase": self.phase.value,
            "genesis": {
                "state": self.genesis.state.value,
                "current_step": self.genesis.current_step,
                "skills_done": self.genesis.skills_done,
                "retry_counts": self.genesis.retry_counts,
            },
            "chapter_loop": {
                "current_chapter": self.chapter_loop.current_chapter,
                "current_step": self.chapter_loop.current_step,
                "step_index": self.chapter_loop.step_index,
                "chapter_states": {
                    k: {"steps_done": v.steps_done, "status": v.status,
                        "resonance_score": v.resonance_score,
                        "audit_results": v.audit_results,
                        "revision_count": v.revision_count}
                    for k, v in self.chapter_loop.chapter_states.items()
                },
                "per_chapter_review_enabled": self.chapter_loop.per_chapter_review_enabled,
                "retry_counts": self.chapter_loop.retry_counts,
            },
            "closure": self.closure.value,
            "pending_checkpoint": {
                "type": self.pending_checkpoint.type.value,
                "chapter": self.pending_checkpoint.chapter,
                "artifact": self.pending_checkpoint.artifact,
                "context": self.pending_checkpoint.context,
                "options": self.pending_checkpoint.options,
                "created_at": self.pending_checkpoint.created_at,
            },
            "checkpoint_history": self.checkpoint_history,
            "last_snapshot": self.last_snapshot,
            "closure_step": self.closure_step,
            "config": {
                "genesis_review_required": self.config.genesis_review_required,
                "chapter_memo_review_required": self.config.chapter_memo_review_required,
                "state_settle_review_required": self.config.state_settle_review_required,
                "per_chapter_review_enabled": self.config.per_chapter_review_enabled,
                "volume_boundary_review_required": self.config.volume_boundary_review_required,
                "max_revision_retries": self.config.max_revision_retries,
                "max_audit_retries": self.config.max_audit_retries,
                "context_budget_override": self.config.context_budget_override,
                "style_learning_interval": self.config.style_learning_interval,
                "genre_config_update_on_drift": self.config.genre_config_update_on_drift,
                "resonance_global_floor": self.config.resonance_global_floor,
                "snapshot_retention_chapters": self.config.snapshot_retention_chapters,
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineState:
        gen_data = data.get("genesis", {})
        cl_data = data.get("chapter_loop", {})
        cp_data = data.get("pending_checkpoint", {})
        cfg_data = data.get("config", {})

        chapter_states: dict[str, ChapterState] = {}
        for k, v in cl_data.get("chapter_states", {}).items():
            chapter_states[k] = ChapterState(
                steps_done=v.get("steps_done", []),
                status=v.get("status", "pending"),
                resonance_score=v.get("resonance_score"),
                audit_results=v.get("audit_results", {}),
                revision_count=v.get("revision_count", 0),
            )

        return cls(
            version=data.get("version", 1),
            project_dir=data.get("project_dir", ""),
            phase=PipelinePhase(data.get("phase", "genesis")),
            genesis=GenesisStateData(
                state=GenesisState(gen_data.get("state", "pending")),
                current_step=gen_data.get("current_step", 0),
                skills_done=gen_data.get("skills_done", []),
                retry_counts=gen_data.get("retry_counts", {}),
            ),
            chapter_loop=ChapterLoopStateData(
                current_chapter=cl_data.get("current_chapter", 0),
                current_step=cl_data.get("current_step", ""),
                step_index=cl_data.get("step_index", 0),
                chapter_states=chapter_states,
                per_chapter_review_enabled=cl_data.get("per_chapter_review_enabled", True),
                retry_counts=cl_data.get("retry_counts", {}),
            ),
            closure=ClosureState(data.get("closure", "pending")),
            pending_checkpoint=CheckpointData(
                type=CheckpointType(cp_data.get("type", "none")),
                chapter=cp_data.get("chapter"),
                artifact=cp_data.get("artifact"),
                context=cp_data.get("context"),
                options=cp_data.get("options", []),
                created_at=cp_data.get("created_at"),
            ),
            checkpoint_history=data.get("checkpoint_history", []),
            last_snapshot=data.get("last_snapshot", {}),
            closure_step=data.get("closure_step", 0),
            config=PipelineConfig(**{
                k: v for k, v in cfg_data.items()
                if k in PipelineConfig.__dataclass_fields__
            }),
        )

    @classmethod
    def from_json(cls, json_str: str) -> PipelineState:
        return cls.from_dict(json.loads(json_str))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_state.py -v`
Expected: PASS (all tests green)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/__init__.py src/shenbi/pipeline/state.py tests/unit/pipeline/
git commit -m "feat: add pipeline state types and enums (wave1 task1)"
```

---

### Task 2: State Machine — Load, Save, Transitions

**Files:**
- Create: `src/shenbi/pipeline/machine.py`
- Create: `tests/unit/pipeline/test_machine.py`

**Interfaces:**
- Consumes: `PipelineState`, all enums from Task 1, `safe_write` from `shenbi.safe_write`
- Produces: `load_state(project_dir)`, `save_state(project_dir, state)`, `set_checkpoint(state, type, chapter, artifact)`, `clear_checkpoint(state, decision)`, `is_at_checkpoint(state)`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/pipeline/test_machine.py
"""Tests for pipeline state machine."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.machine import (
    clear_checkpoint,
    is_at_checkpoint,
    load_state,
    save_state,
    set_checkpoint,
)
from shenbi.pipeline.state import (
    CheckpointType,
    PipelinePhase,
    PipelineState,
    ReviewDecision,
)


class TestLoadSave:
    def test_save_and_load_round_trip(self, tmp_project: Path):
        state = PipelineState.default(project_dir=str(tmp_project))
        state.genesis.current_step = 3
        state.genesis.skills_done = ["a", "b"]

        save_state(tmp_project, state)
        loaded = load_state(tmp_project)

        assert loaded.genesis.current_step == 3
        assert loaded.genesis.skills_done == ["a", "b"]

    def test_load_missing_raises(self, tmp_project: Path):
        with pytest.raises(FileNotFoundError):
            load_state(tmp_project)

    def test_save_creates_state_file(self, tmp_project: Path):
        state = PipelineState.default(project_dir=str(tmp_project))
        save_state(tmp_project, state)
        assert (tmp_project / "pipeline-state.json").exists()

    def test_save_is_atomic(self, tmp_project: Path):
        """Verify state is saved atomically (no partial writes on crash)."""
        state = PipelineState.default(project_dir=str(tmp_project))
        save_state(tmp_project, state)
        content = (tmp_project / "pipeline-state.json").read_text()
        import json
        # Should be valid JSON (atomic write ensures no partial)
        json.loads(content)


class TestCheckpoint:
    def test_set_checkpoint(self):
        state = PipelineState.default(project_dir="/tmp/x")
        set_checkpoint(
            state,
            checkpoint_type=CheckpointType.CHAPTER_MEMO,
            chapter=5,
            artifact="plans/chapter-5-plan.md",
            context="Review memo",
        )
        assert state.pending_checkpoint.type == CheckpointType.CHAPTER_MEMO
        assert state.pending_checkpoint.chapter == 5
        assert state.pending_checkpoint.artifact == "plans/chapter-5-plan.md"
        assert is_at_checkpoint(state) is True

    def test_clear_checkpoint(self):
        state = PipelineState.default(project_dir="/tmp/x")
        set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=5, artifact="x")
        assert is_at_checkpoint(state)

        clear_checkpoint(state, ReviewDecision.APPROVE)
        assert state.pending_checkpoint.type == CheckpointType.NONE
        assert is_at_checkpoint(state) is False
        assert len(state.checkpoint_history) == 1
        assert state.checkpoint_history[0]["decision"] == "approve"

    def test_clear_checkpoint_records_history(self):
        state = PipelineState.default(project_dir="/tmp/x")
        set_checkpoint(state, CheckpointType.GENESIS_COMPLETE, artifact="genesis")
        clear_checkpoint(state, ReviewDecision.MODIFY)
        assert state.checkpoint_history[-1]["decision"] == "modify"
        assert state.checkpoint_history[-1]["type"] == "genesis-complete"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_machine.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/shenbi/pipeline/machine.py
"""State machine: load, save, and checkpoint management for pipeline-state.json.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from shenbi.cli_utils import emit_json
from shenbi.logging import get_logger
from shenbi.pipeline.state import (
    CheckpointData,
    CheckpointType,
    PipelineState,
    ReviewDecision,
)
from shenbi.safe_write import safe_write

log = get_logger(__name__)

STATE_FILENAME = "pipeline-state.json"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_state(project_dir: Path | str) -> PipelineState:
    """Load pipeline state from project_dir/pipeline-state.json."""
    project_dir = Path(project_dir)
    state_file = project_dir / STATE_FILENAME
    if not state_file.exists():
        raise FileNotFoundError(f"pipeline-state.json not found in {project_dir}")
    return PipelineState.from_json(state_file.read_text(encoding="utf-8"))


def save_state(project_dir: Path | str, state: PipelineState) -> None:
    """Atomically save pipeline state to project_dir/pipeline-state.json."""
    project_dir = Path(project_dir)
    state_file = project_dir / STATE_FILENAME
    safe_write(state_file, state.to_json())


def set_checkpoint(
    state: PipelineState,
    checkpoint_type: CheckpointType,
    chapter: int | None = None,
    artifact: str | None = None,
    context: str | None = None,
    options: list[str] | None = None,
) -> None:
    """Set the pending checkpoint on the state."""
    if options is None:
        options = ["approve", "modify", "reject"]
    state.pending_checkpoint = CheckpointData(
        type=checkpoint_type,
        chapter=chapter,
        artifact=artifact,
        context=context,
        options=options,
        created_at=_now_iso(),
    )


def clear_checkpoint(state: PipelineState, decision: ReviewDecision) -> None:
    """Clear the pending checkpoint and record it in history."""
    cp = state.pending_checkpoint
    state.checkpoint_history.append({
        "type": cp.type.value,
        "chapter": cp.chapter,
        "decision": decision.value,
        "resolved_at": _now_iso(),
    })
    state.pending_checkpoint = CheckpointData(type=CheckpointType.NONE)


def is_at_checkpoint(state: PipelineState) -> bool:
    """Check if the pipeline is currently waiting at a checkpoint."""
    return state.pending_checkpoint.type != CheckpointType.NONE
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_machine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/machine.py tests/unit/pipeline/test_machine.py
git commit -m "feat: add pipeline state machine load/save/checkpoint (wave1 task2)"
```

---

### Task 3: File Lock Utilities

**Files:**
- Create: `src/shenbi/pipeline/filelock_utils.py`
- Create: `tests/unit/pipeline/test_filelock_utils.py`
- Modify: `pyproject.toml` (add `filelock>=3.13.0` to dependencies)

**Interfaces:**
- Produces: `WriteLock` (context manager), `ReadLock` (context manager)

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/pipeline/test_filelock_utils.py
"""Tests for pipeline file locking utilities."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from shenbi.pipeline.filelock_utils import ReadLock, WriteLock


class TestWriteLock:
    def test_acquire_and_release(self, tmp_project: Path):
        lock = WriteLock(tmp_project)
        with lock:
            assert (tmp_project / "pipeline-state.json.lock").exists()
        # Lock file may persist (filelock behavior) but is unlocked

    def test_concurrent_writes_are_serialized(self, tmp_project: Path):
        """Two writers should not overlap."""
        results: list[str] = []
        barrier = threading.Barrier(2)

        def writer(name: str):
            barrier.wait()
            with WriteLock(tmp_project):
                results.append(f"{name}-start")
                results.append(f"{name}-end")

        t1 = threading.Thread(target=writer, args=("a",))
        t2 = threading.Thread(target=writer, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Each writer's start and end should be adjacent (no interleaving)
        for i in range(0, len(results), 2):
            name = results[i].split("-")[0]
            assert results[i + 1] == f"{name}-end"


class TestReadLock:
    def test_concurrent_reads_allowed(self, tmp_project: Path):
        """Multiple readers should be able to hold the lock simultaneously."""
        results: list[str] = []
        barrier = threading.Barrier(2)

        def reader(name: str):
            barrier.wait()
            with ReadLock(tmp_project):
                results.append(f"{name}-in")

        t1 = threading.Thread(target=reader, args=("a",))
        t2 = threading.Thread(target=reader, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(results) == 2  # both readers entered
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_filelock_utils.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Add filelock dependency**

Note:  is already a transitive dependency in . Adding it explicitly to  makes it a first-class dep rather than relying on transitive resolution. Run  to verify.

Add `filelock>=3.13.0` to `[project] dependencies` in `pyproject.toml`, then run `uv sync --group dev`.

- [ ] **Step 4: Write the implementation**

```python
# src/shenbi/pipeline/filelock_utils.py
"""Read/write lock separation for multi-user pipeline concurrency.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 2.4.

- WriteLock: exclusive, used by next/review/resume/rollback/init
- ReadLock: shared, used by status/chapters
"""

from __future__ import annotations

from pathlib import Path


class WriteLock:
    """Exclusive write lock. Uses fcntl.flock(LOCK_EX) on shared lockfile.

    Both WriteLock and ReadLock operate on the SAME lockfile
    (pipeline-state.json.lockfile) to guarantee mutual exclusion:
    - WriteLock acquires LOCK_EX (blocks all readers and writers)
    - ReadLock acquires LOCK_SH (allows concurrent readers, blocks writers)
    """

    def __init__(self, project_dir: Path | str, timeout: float = 300.0) -> None:
        self._lockfile = Path(project_dir) / "pipeline-state.json.lockfile"
        self._lockfile.parent.mkdir(parents=True, exist_ok=True)
        self._timeout = timeout
        self._fd: int | None = None

    def __enter__(self) -> WriteLock:
        import fcntl, os, time
        self._fd = os.open(str(self._lockfile), os.O_CREAT | os.O_RDONLY)
        deadline = time.monotonic() + self._timeout
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError):
                if time.monotonic() > deadline:
                    raise TimeoutError(f"WriteLock timeout on {self._lockfile}")
                time.sleep(0.05)
        return self

    def __exit__(self, *args: object) -> None:
        import fcntl, os
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


class ReadLock:
    """Shared read lock for status queries (multiple readers, non-exclusive).

    Uses fcntl.flock(LOCK_SH) for true shared locking on POSIX.
    Multiple ReadLock holders can coexist; WriteLock (LOCK_EX) blocks all readers.
    """

    def __init__(self, project_dir: Path | str, timeout: float = 30.0) -> None:
        self._lockfile = Path(project_dir) / "pipeline-state.json.lockfile"  # SAME file as WriteLock
        self._lockfile.parent.mkdir(parents=True, exist_ok=True)
        self._timeout = timeout
        self._fd: int | None = None

    def __enter__(self) -> ReadLock:
        import fcntl
        import time
        self._fd = __import__("os").open(str(self._lockfile), __import__("os").O_CREAT | __import__("os").O_RDONLY)
        deadline = time.monotonic() + self._timeout
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError):
                if time.monotonic() > deadline:
                    raise TimeoutError(f"ReadLock timeout on {self._lockfile}")
                time.sleep(0.05)
        return self

    def __exit__(self, *args: object) -> None:
        import fcntl
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            __import__("os").close(self._fd)
            self._fd = None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_filelock_utils.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/filelock_utils.py tests/unit/pipeline/test_filelock_utils.py pyproject.toml
git commit -m "feat: add pipeline read/write lock utilities (wave1 task3)"
```

---

### Task 4: Seed File Parser

**Files:**
- Create: `src/shenbi/pipeline/seed_parser.py`
- Create: `tests/unit/pipeline/test_seed_parser.py`

**Interfaces:**
- Produces: `parse_seed(seed_path) -> SeedData`, `SeedData` dataclass

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/pipeline/test_seed_parser.py
"""Tests for seed file parsing."""

from __future__ import annotations

import pytest

from shenbi.pipeline.seed_parser import SeedData, parse_seed


class TestParseSeed:
    def test_parse_basic_info(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert data.novel_json["genre"] == ["fantasy", "adventure"]
        assert data.novel_json["era"] == "medieval"
        assert data.novel_json["core_concept"] == "A test novel"
        assert data.novel_json["target_word_count"] == 200000
        assert data.novel_json["ending_direction"] == "Happy ending"

    def test_parse_protagonist(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert "Test Hero" in data.genesis_context["protagonist"]

    def test_parse_world_rules(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert "Magic exists" in data.genesis_context["world_rules"]
        assert "Dragons are real" in data.genesis_context["world_rules"]

    def test_parse_core_conflict(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert "Kingdom at war" in data.genesis_context["surface_conflict"]
        assert "Hero seeks revenge" in data.genesis_context["personal_conflict"]
        assert "Freedom vs duty" in data.genesis_context["deep_conflict"]

    def test_parse_three_act(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert "Hero discovers powers" in data.genesis_context["three_act"]

    def test_parse_narrative_techniques(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert data.genre_config.get("show_tell_ratio") == "70/30"
        assert "courage" in data.genre_config.get("deep_themes", "")

    def test_parse_does_not_set_total_chapters(self, sample_seed_content, tmp_path):
        """Seed parser must NOT set total_chapters -- that's volume-outlining's job."""
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert "total_chapters" not in data.novel_json

    def test_parse_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_seed(tmp_path / "nonexistent.md")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_seed_parser.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/shenbi/pipeline/seed_parser.py
"""Parse seed files (format: outline-example.md) into structured project data.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 4.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)

@dataclass
class SeedData:
    """Parsed seed file data."""

    novel_json: dict[str, object] = field(default_factory=dict)
    genre_config: dict[str, object] = field(default_factory=dict)
    genesis_context: dict[str, str] = field(default_factory=dict)


def _extract_section(text: str, section_name: str) -> str:
    """Extract content under a ## or ### heading until the next heading of same or higher level."""
    pattern = rf"^#{1,3}\s+{re.escape(section_name)}\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    # Find next heading
    next_heading = re.search(r"^#{1,3}\s", text[start:], re.MULTILINE)
    if next_heading:
        return text[start : start + next_heading.start()].strip()
    return text[start:].strip()


def _parse_list_items(section_text: str) -> list[str]:
    """Parse markdown list items (lines starting with - or *)."""
    items: list[str] = []
    for line in section_text.split("\n"):
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            items.append(line[2:].strip())
    return items


def parse_seed(seed_path: Path | str) -> SeedData:
    """Parse a seed file into SeedData.

    The seed file format matches outline-example.md structure:
    - ## Basic Info (genre, era, core concept, target word count, ending)
    - ## Protagonist (name, background, personality, arc)
    - ## World Rules / World Setting
    - ## Forces / Organizations
    - ## Core Conflict (surface, personal, deep)
    - ## Plot Lines
    - ## Chapter Outline (optional existing chapter summaries)
    - ## Three-Act Structure
    - ## Narrative Techniques (show/tell ratio, deep themes)
    """
    seed_path = Path(seed_path)
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_path}")

    text = seed_path.read_text(encoding="utf-8")

    # Parse Basic Info
    basic = _extract_section(text, "Basic Info|基本信息")
    basic_items = _parse_list_items(basic)
    novel_json: dict[str, object] = {}
    genre: list[str] = []
    for item in basic_items:
        # Try to match "key: value" or "key：value"
        if ":" in item:
            key, _, value = item.partition(":")
        elif "：" in item:
            key, _, value = item.partition("：")
        else:
            continue
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()

        if key in ("genre", "类型", "题材"):
            genre = [g.strip() for g in re.split(r"[,，]", value)]
            novel_json["genre"] = genre
        elif key in ("era", "时代背景", "时代"):
            novel_json["era"] = value
        elif key in ("core_concept", "核心概念"):
            novel_json["core_concept"] = value
        elif key in ("target_word_count", "目标字数"):
            # Extract number from value
            nums = re.findall(r"\d+", value)
            if nums:
                novel_json["target_word_count"] = int(nums[0])
        elif key in ("ending_direction", "故事结局方向", "结局"):
            novel_json["ending_direction"] = value

    # total_chapters is NOT set here -- volume-outlining (genesis step 6) computes it.
    # See spec section 4.2.
    novel_json["golden_opening_chapters"] = 3
    novel_json["language"] = "zh"

    # Parse genre config from Narrative Techniques
    narrative = _extract_section(text, "Narrative Techniques|叙事技巧")
    genre_config: dict[str, object] = {}
    for item in _parse_list_items(narrative):
        if ":" in item:
            key, _, value = item.partition(":")
        elif "：" in item:
            key, _, value = item.partition("：")
        else:
            continue
        key = key.strip().lower().replace(" ", "_").replace("/", "_")
        value = value.strip()
        if "show" in key and "tell" in key:
            genre_config["show_tell_ratio"] = value
        elif "theme" in key or "主题" in key:
            genre_config["deep_themes"] = value

    # Genesis context: raw text of each section for skill dispatch prompts
    genesis_context: dict[str, str] = {
        "protagonist": _extract_section(text, "Protagonist|主角设定|主角"),
        "world_rules": _extract_section(text, "World Rules|世界观设定|世界规则|World Setting"),
        "forces": _extract_section(text, "Forces|势力|组织|Factions"),
        "surface_conflict": "",
        "personal_conflict": "",
        "deep_conflict": "",
        "plot_lines": _extract_section(text, "Plot Lines|情节线"),
        "chapter_outline": _extract_section(text, "Chapter Outline|章节大纲"),
        "three_act": _extract_section(text, "Three-Act Structure|三幕结构"),
    }

    # Parse conflict three layers
    conflict = _extract_section(text, "Core Conflict|核心冲突")
    for item in _parse_list_items(conflict):
        if ":" in item:
            key, _, value = item.partition(":")
        elif "：" in item:
            key, _, value = item.partition("：")
        else:
            continue
        key_lower = key.strip().lower()
        value = value.strip()
        if "surface" in key_lower or "表层" in key:
            genesis_context["surface_conflict"] = value
        elif "personal" in key_lower or "个人" in key:
            genesis_context["personal_conflict"] = value
        elif "deep" in key_lower or "深层" in key:
            genesis_context["deep_conflict"] = value

    return SeedData(
        novel_json=novel_json,
        genre_config=genre_config,
        genesis_context=genesis_context,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_seed_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/seed_parser.py tests/unit/pipeline/test_seed_parser.py
git commit -m "feat: add seed file parser (wave1 task4)"
```

---

### Task 5: Checkpoint Staging Mechanism

**Files:**
- Create: `src/shenbi/pipeline/checkpoint.py`
- Create: `tests/unit/pipeline/test_checkpoint.py`

**Interfaces:**
- Consumes: `PipelineState`, `CheckpointType` from Task 1
- Produces: `staging_path(project_dir, target_path) -> Path`, `commit_staging(project_dir, staging_files) -> list[Path]`, `clear_staging(project_dir) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/pipeline/test_checkpoint.py
"""Tests for checkpoint staging mechanism."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.checkpoint import (
    clear_staging,
    commit_staging,
    staging_path,
)


class TestStaging:
    def test_staging_path_maps_target(self, tmp_project: Path):
        target = "plans/chapter-5-plan.md"
        sp = staging_path(tmp_project, target)
        assert "staging" in str(sp)
        assert sp.name == "chapter-5-plan.md"
        assert sp.parent == tmp_project / "staging" / "plans"

    def test_commit_staging_copies_files(self, tmp_project: Path):
        # Create a staging file
        sp = staging_path(tmp_project, "plans/chapter-1-plan.md")
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text("# Chapter 1 Plan", encoding="utf-8")

        # Commit
        committed = commit_staging(tmp_project, ["plans/chapter-1-plan.md"])

        assert len(committed) == 1
        target = tmp_project / "plans" / "chapter-1-plan.md"
        assert target.exists()
        assert target.read_text() == "# Chapter 1 Plan"

    def test_clear_staging_removes_all(self, tmp_project: Path):
        staging_dir = tmp_project / "staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        (staging_dir / "test.md").write_text("test")

        clear_staging(tmp_project)

        # Staging dir should be empty or removed
        assert not staging_dir.exists() or not any(staging_dir.iterdir())

    def test_commit_nonexistent_staging_raises(self, tmp_project: Path):
        with pytest.raises(FileNotFoundError):
            commit_staging(tmp_project, ["nonexistent.md"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_checkpoint.py -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```python
# src/shenbi/pipeline/checkpoint.py
"""Staging mechanism for checkpoint-gated skill outputs.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 2.7.

Checkpoint-gated skills (chapter-planning, state-settling) write to staging/
during dispatch. On review approve, pipeline commits staging to final paths.
On review reject, staging is cleared and the skill re-dispatches.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)


def staging_path(project_dir: Path | str, target_path: str) -> Path:
    """Map a target path to its staging location.

    Example: "plans/chapter-5-plan.md" -> project_dir/staging/plans/chapter-5-plan.md
    """
    project_dir = Path(project_dir)
    return project_dir / "staging" / target_path


def commit_staging(project_dir: Path | str, target_paths: list[str]) -> list[Path]:
    """Commit staging files to their final paths.

    Copies each staging file to its target location, creating parent dirs.
    Returns list of committed target paths.
    Raises FileNotFoundError if a staging file doesn't exist.
    """
    project_dir = Path(project_dir)
    committed: list[Path] = []
    for target_path in target_paths:
        source = staging_path(project_dir, target_path)
        if not source.exists():
            raise FileNotFoundError(f"Staging file not found: {source}")
        dest = project_dir / target_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(dest))
        committed.append(dest)
        log.info("staging_committed", target=target_path)
    return committed


def clear_staging(project_dir: Path | str) -> None:
    """Remove all staging files (used on review reject)."""
    project_dir = Path(project_dir)
    staging_dir = project_dir / "staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
        log.info("staging_cleared")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_checkpoint.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/checkpoint.py tests/unit/pipeline/test_checkpoint.py
git commit -m "feat: add checkpoint staging mechanism (wave1 task5)"
```

---

### Task 6: CLI Command Interface

**Files:**
- Create: `src/shenbi/pipeline/cli.py`
- Create: `tests/unit/pipeline/test_cli.py`
- Modify: `pyproject.toml` (add `pipeline = "shenbi.pipeline.cli:main"` to `[project.scripts]`)

**Interfaces:**
- Consumes: All previous tasks (state, machine, seed_parser, checkpoint, filelock_utils)
- Produces: `main()` CLI entry point with subcommands: init, next, status, review, resume, chapters, rollback

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/pipeline/test_cli.py
"""Tests for pipeline CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from shenbi.pipeline.cli import main


class TestInitCommand:
    def test_init_creates_project(self, tmp_path: Path, sample_seed_content):
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        rc = main(["init", str(seed_file), "--project-dir", str(project_dir)])

        assert rc == 0
        assert (project_dir / "pipeline-state.json").exists()
        assert (project_dir / "novel.json").exists()
        novel = json.loads((project_dir / "novel.json").read_text())
        assert novel["genre"] == ["fantasy", "adventure"]

    def test_init_idempotent_rejects_existing(self, tmp_path: Path, sample_seed_content):
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        main(["init", str(seed_file), "--project-dir", str(project_dir)])
        rc = main(["init", str(seed_file), "--project-dir", str(project_dir)])

        assert rc != 0  # Should fail on duplicate init


class TestStatusCommand:
    def test_status_returns_json(self, tmp_path: Path, sample_seed_content):
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"
        main(["init", str(seed_file), "--project-dir", str(project_dir)])

        rc = main(["status", str(project_dir)])

        assert rc == 0

    def test_status_missing_project(self, tmp_path: Path):
        rc = main(["status", str(tmp_path / "nonexistent")])
        assert rc != 0


class TestReviewCommand:
    def test_review_approve_without_checkpoint_fails(self, tmp_path: Path, sample_seed_content):
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"
        main(["init", str(seed_file), "--project-dir", str(project_dir)])

        rc = main(["review", str(project_dir), "approve"])
        assert rc != 0  # No pending checkpoint to approve
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```python
# src/shenbi/pipeline/cli.py
"""CLI entry point for the novel pipeline.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 2.2.

Commands:
    init <seed-file> [--project-dir <dir>]
    next <project-dir>
    status <project-dir>
    review <project-dir> approve|reject|modify [--feedback <file>]
    resume <project-dir>
    chapters <project-dir>
    rollback <project-dir> --chapter <N>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from shenbi.cli_utils import emit_json
from shenbi.logging import configure_logging, get_logger
from shenbi.pipeline.filelock_utils import ReadLock, WriteLock
from shenbi.pipeline.machine import (
    clear_checkpoint,
    is_at_checkpoint,
    load_state,
    save_state,
)
from shenbi.pipeline.seed_parser import parse_seed
from shenbi.pipeline.state import CheckpointType, GenesisState, PipelinePhase, PipelineState, ReviewDecision

log = get_logger(__name__)


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new novel project from a seed file."""
    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd() / "novel"

    if (project_dir / "pipeline-state.json").exists():
        emit_json({"status": "error", "message": "pipeline-state.json already exists"})
        return 1

    project_dir.mkdir(parents=True, exist_ok=True)

    seed_data = parse_seed(args.seed_file)

    # Write novel.json
    novel_json_path = project_dir / "novel.json"
    novel_json_path.write_text(
        json.dumps(seed_data.novel_json, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Write genre-config.json if we have data
    if seed_data.genre_config:
        gc = {"version": "1.0", **seed_data.genre_config}
        (project_dir / "genre-config.json").write_text(
            json.dumps(gc, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # Write genesis context for later skill dispatch
    ctx_dir = project_dir / "genesis-context"
    ctx_dir.mkdir(exist_ok=True)
    for key, value in seed_data.genesis_context.items():
        if value:
            (ctx_dir / f"{key}.md").write_text(value, encoding="utf-8")

    # Initialize pipeline state -- genesis starts IN_PROGRESS per spec section 3.1
    state = PipelineState.default(project_dir=str(project_dir))
    state.genesis.state = GenesisState.IN_PROGRESS
    with WriteLock(project_dir):
        save_state(project_dir, state)

    emit_json({
        "status": "ok",
        "project_dir": str(project_dir),
        "novel_json": str(novel_json_path),
        "total_chapters": seed_data.novel_json.get("total_chapters", "unknown"),
    })
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Query current pipeline state."""
    project_dir = Path(args.project_dir)

    try:
        with ReadLock(project_dir):
            state = load_state(project_dir)
    except FileNotFoundError:
        emit_json({"status": "error", "message": f"pipeline-state.json not found in {project_dir}"})
        return 1

    cp = state.pending_checkpoint
    result = {
        "phase": state.phase.value,
        "current_chapter": state.chapter_loop.current_chapter,
        "current_step": state.chapter_loop.current_step,
        "pending_checkpoint": cp.type.value if cp.type != CheckpointType.NONE else None,
        "checkpoint_chapter": cp.chapter,
        "checkpoint_artifact": cp.artifact,
    }
    emit_json(result)
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """Submit a review decision for a pending checkpoint."""
    project_dir = Path(args.project_dir)

    try:
        with WriteLock(project_dir):
            state = load_state(project_dir)
    except FileNotFoundError:
        emit_json({"status": "error", "message": "project not found"})
        return 1

    if not is_at_checkpoint(state):
        emit_json({"status": "error", "message": "no pending checkpoint to review"})
        return 1

    decision = ReviewDecision(args.decision)
    feedback = None
    if args.feedback:
        feedback = Path(args.feedback).read_text(encoding="utf-8")

    clear_checkpoint(state, decision)

    if feedback:
        state.checkpoint_history[-1]["feedback"] = feedback

    save_state(project_dir, state)

    emit_json({
        "status": "ok",
        "decision": decision.value,
        "checkpoint_type": state.checkpoint_history[-1]["type"],
    })
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    """Execute to the next checkpoint. Placeholder — orchestrators (Wave 3) implement this."""
    project_dir = Path(args.project_dir)

    try:
        with WriteLock(project_dir):
            state = load_state(project_dir)
    except FileNotFoundError:
        emit_json({"status": "error", "message": "project not found"})
        return 1

    if is_at_checkpoint(state):
        emit_json({
            "status": "blocked",
            "message": "pending checkpoint requires review",
            "checkpoint": state.pending_checkpoint.type.value,
        })
        return 1

    # Wave 3 will replace this with actual orchestration
    emit_json({
        "status": "not_implemented",
        "message": "Orchestrators not yet implemented (Wave 3). State machine is ready.",
        "phase": state.phase.value,
    })
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume after checkpoint review. Placeholder — same as next."""
    return cmd_next(args)


def cmd_chapters(args: argparse.Namespace) -> int:
    """Show chapter progress overview."""
    project_dir = Path(args.project_dir)

    try:
        with ReadLock(project_dir):
            state = load_state(project_dir)
    except FileNotFoundError:
        emit_json({"status": "error", "message": "project not found"})
        return 1

    chapters = []
    for ch_num_str, ch_state in sorted(state.chapter_loop.chapter_states.items()):
        chapters.append({
            "chapter": int(ch_num_str),
            "status": ch_state.status,
            "resonance_score": ch_state.resonance_score,
            "revision_count": ch_state.revision_count,
        })

    emit_json({
        "current_chapter": state.chapter_loop.current_chapter,
        "chapters": chapters,
    })
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    """Rollback to a chapter snapshot. Placeholder — needs snapshot integration (Wave 3)."""
    project_dir = Path(args.project_dir)
    emit_json({
        "status": "not_implemented",
        "message": "Rollback requires snapshot integration (Wave 3/4)",
    })
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    configure_logging()
    parser = argparse.ArgumentParser(prog="pipeline", description="Novel pipeline orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize novel project from seed file")
    p_init.add_argument("seed_file", type=str, help="Path to seed file")
    p_init.add_argument("--project-dir", type=str, default=None)
    p_init.set_defaults(func=cmd_init)

    p_next = sub.add_parser("next", help="Execute to next checkpoint")
    p_next.add_argument("project_dir", type=str)
    p_next.set_defaults(func=cmd_next)

    p_status = sub.add_parser("status", help="Query pipeline state")
    p_status.add_argument("project_dir", type=str)
    p_status.set_defaults(func=cmd_status)

    p_review = sub.add_parser("review", help="Submit checkpoint review")
    p_review.add_argument("project_dir", type=str)
    p_review.add_argument("decision", choices=["approve", "reject", "modify"])
    p_review.add_argument("--feedback", type=str, default=None)
    p_review.set_defaults(func=cmd_review)

    p_resume = sub.add_parser("resume", help="Resume after checkpoint review")
    p_resume.add_argument("project_dir", type=str)
    p_resume.set_defaults(func=cmd_resume)

    p_chapters = sub.add_parser("chapters", help="Show chapter progress")
    p_chapters.add_argument("project_dir", type=str)
    p_chapters.set_defaults(func=cmd_chapters)

    p_rollback = sub.add_parser("rollback", help="Rollback to chapter snapshot")
    p_rollback.add_argument("project_dir", type=str)
    p_rollback.add_argument("--chapter", type=int, required=True)
    p_rollback.set_defaults(func=cmd_rollback)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Add entry point to pyproject.toml**

Add to `[project.scripts]`:
```toml
pipeline = "shenbi.pipeline.cli:main"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/pipeline/test_cli.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/cli.py tests/unit/pipeline/test_cli.py pyproject.toml
git commit -m "feat: add pipeline CLI with init/status/review commands (wave1 task6)"
```

---

### Task 7: End-to-End Integration Test

**Files:**
- Create: `tests/unit/pipeline/test_e2e.py`

**Interfaces:**
- Consumes: All previous tasks

- [ ] **Step 1: Write the test**

```python
# tests/unit/pipeline/test_e2e.py
"""End-to-end integration test for Wave 1 foundation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.pipeline.cli import main
from shenbi.pipeline.machine import load_state


class TestWave1E2E:
    def test_init_then_status_flow(self, tmp_path: Path, sample_seed_content):
        """Full flow: init -> status -> review (no checkpoint yet)."""
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        # Step 1: init
        rc = main(["init", str(seed_file), "--project-dir", str(project_dir)])
        assert rc == 0

        # Step 2: status should show genesis phase
        rc = main(["status", str(project_dir)])
        assert rc == 0

        state = load_state(project_dir)
        assert state.phase.value == "genesis"
        assert state.genesis.state.value == "in-progress"

        # Step 3: init again should fail (idempotency)
        rc = main(["init", str(seed_file), "--project-dir", str(project_dir)])
        assert rc != 0

    def test_review_without_checkpoint_fails(self, tmp_path: Path, sample_seed_content):
        """Review should fail when no checkpoint is pending."""
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        main(["init", str(seed_file), "--project-dir", str(project_dir)])

        rc = main(["review", str(project_dir), "approve"])
        assert rc != 0

    def test_project_has_all_expected_files(self, tmp_path: Path, sample_seed_content):
        """After init, project should have novel.json, genre-config.json, genesis-context/, pipeline-state.json."""
        seed_file = tmp_path / "seed.md"
        seed_file.write_text(sample_seed_content, encoding="utf-8")
        project_dir = tmp_path / "novel"

        main(["init", str(seed_file), "--project-dir", str(project_dir)])

        assert (project_dir / "pipeline-state.json").exists()
        assert (project_dir / "novel.json").exists()
        assert (project_dir / "genre-config.json").exists()
        assert (project_dir / "genesis-context").is_dir()
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/unit/pipeline/test_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/unit/pipeline/test_e2e.py
git commit -m "test: add wave1 end-to-end integration test (wave1 task7)"
```

---

### Task 8: Update justfile and documentation

**Files:**
- Modify: `justfile`

- [ ] **Step 1: Add just recipes**

Add to `justfile` after the existing recipes:

```makefile
# Initialize a novel pipeline from a seed file
pipeline-init seed project_dir="":
    uv run pipeline init {{seed}} {{project_dir}}

# Check pipeline status
pipeline-status project_dir:
    uv run pipeline status {{project_dir}}

# Submit a checkpoint review
pipeline-review project_dir decision feedback="":
    uv run pipeline review {{project_dir}} {{decision}} {{feedback}}

# Resume pipeline execution
pipeline-resume project_dir:
    uv run pipeline resume {{project_dir}}
```

- [ ] **Step 2: Run just check to verify nothing breaks**

Run: `uv run pytest tests/unit/pipeline/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add justfile
git commit -m "chore: add pipeline commands to justfile (wave1 task8)"
```

---

## Self-Review

**1. Spec coverage:**
- Section 2.1 (three-layer separation): `pipeline/` package implements orchestrator layer. Wave 3 adds the phase runners. ✓
- Section 2.2 (command interface): Task 6 implements all 7 commands (next/resume/rollback are placeholders for Wave 3). ✓
- Section 2.4 (concurrency): Task 3 implements read/write lock separation + init idempotency. ✓
- Section 3.1 (state-transition table): Task 2 implements checkpoint logic. Full transition table needs Wave 3 orchestrators (they implement the actual transitions). ✓ (foundation ready)
- Section 3.3 (pipeline-state.json): Task 1 implements full serialization. ✓
- Section 4 (seed parsing): Task 4 implements full parser. ✓
- Section 2.7 (staging): Task 5 implements staging mechanism. ✓
- Section 9 (checkpoints): Task 2 + Task 5 cover checkpoint set/clear/staging. ✓

**2. Placeholder scan:**
- `cmd_next` and `cmd_resume` have `not_implemented` returns — intentional, Wave 3 fills them. ✓ (documented)
- `cmd_rollback` has `not_implemented` — intentional, needs snapshot integration. ✓
- No TBD/TODO in actual implementation code. ✓

**3. Type consistency:**
- `PipelineState` used consistently across all tasks. ✓
- `CheckpointType`, `ReviewDecision` enums used consistently. ✓
- `WriteLock`/`ReadLock` context managers consistent. ✓
- `staging_path`/`commit_staging`/`clear_staging` signatures match between definition and tests. ✓
