"""Typed state vocabulary and dataclasses for the novel pipeline state machine.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 3.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from shenbi.config.thresholds import DEFAULT_THRESHOLDS


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
    #: Resonance global floor (spec §6.3). Imported from the single source of
    #: truth in ``shenbi.config.thresholds`` so config / skills / gates can
    #: never drift apart again (root cause of E11).
    resonance_global_floor: int = DEFAULT_THRESHOLDS.resonance_global_floor
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
    retry_feedback: dict[str, str] = field(default_factory=dict)


@dataclass
class ChapterState:
    steps_done: list[str] = field(default_factory=list)
    status: str = "pending"
    resonance_score: int | None = None
    audit_results: dict[str, Any] = field(default_factory=dict)
    revision_count: int = 0
    audit_retry_count: int = 0  # tracks audit BLOCKING revision attempts


@dataclass
class SoftFailTracker:
    """Tracks SOFT G4 failures with a sliding window to prevent stale escalations."""

    check_id: str
    occurrences: list[int] = field(default_factory=list)
    window_size: int = 5
    escalation_threshold: int = 3

    def record(self, chapter: int) -> bool:
        """Record a soft failure occurrence and return True if escalation threshold met."""
        self.occurrences.append(chapter)
        self.occurrences = [ch for ch in self.occurrences if chapter - ch <= self.window_size]
        return len(self.occurrences) >= self.escalation_threshold

    def to_dict(self) -> dict[str, Any]:
        """Serialize tracker state for persistence."""
        return {
            "check_id": self.check_id,
            "occurrences": self.occurrences,
            "window_size": self.window_size,
            "escalation_threshold": self.escalation_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SoftFailTracker:
        """Deserialize tracker state from persistence."""
        return cls(
            check_id=data["check_id"],
            occurrences=data.get("occurrences", []),
            window_size=data.get("window_size", 5),
            escalation_threshold=data.get("escalation_threshold", 3),
        )


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
    # Observability: per-skill wall-clock timing (list of elapsed seconds per call).
    # Populated by run_chapter_step; summarized by _print_timing_summary at chapter
    # completion. Key is the skill name (e.g. "shenbi-chapter-drafting").
    step_timings: dict[str, list[float]] = field(default_factory=dict)


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
    closure_skills_done: list[str] = field(default_factory=list)  # closure skill history
    closure_retry_counts: dict[str, int] = field(default_factory=dict)  # closure per-skill retries
    pending_re_dispatches: list[dict[str, Any]] = field(default_factory=list)
    config: PipelineConfig = field(default_factory=PipelineConfig)
    last_trigger_failure: dict[str, Any] | None = None  # set by run_triggered_skills on failure
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
                "retry_feedback": self.genesis.retry_feedback,
            },
            "chapter_loop": {
                "current_chapter": self.chapter_loop.current_chapter,
                "current_step": self.chapter_loop.current_step,
                "step_index": self.chapter_loop.step_index,
                "chapter_states": {
                    k: {
                        "steps_done": v.steps_done,
                        "status": v.status,
                        "resonance_score": v.resonance_score,
                        "audit_results": v.audit_results,
                        "revision_count": v.revision_count,
                        "audit_retry_count": v.audit_retry_count,
                    }
                    for k, v in self.chapter_loop.chapter_states.items()
                },
                "per_chapter_review_enabled": self.chapter_loop.per_chapter_review_enabled,
                "retry_counts": self.chapter_loop.retry_counts,
                "retry_budget_consumed": self.chapter_loop.retry_budget_consumed,
                "modify_feedback": self.chapter_loop.modify_feedback,
                "retry_feedback": self.chapter_loop.retry_feedback,
                "soft_fail_trackers": {
                    k: v.to_dict() for k, v in self.chapter_loop.soft_fail_trackers.items()
                },
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
            "closure_skills_done": self.closure_skills_done,
            "closure_retry_counts": self.closure_retry_counts,
            "pending_re_dispatches": self.pending_re_dispatches,
            "last_trigger_failure": self.last_trigger_failure,
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
                audit_retry_count=v.get("audit_retry_count", 0),
            )

        soft_fail_trackers: dict[str, Any] = {}
        for k, v in cl_data.get("soft_fail_trackers", {}).items():
            soft_fail_trackers[k] = SoftFailTracker.from_dict(v)

        return cls(
            version=data.get("version", 1),
            project_dir=data.get("project_dir", ""),
            phase=PipelinePhase(data.get("phase", "genesis")),
            genesis=GenesisStateData(
                state=GenesisState(gen_data.get("state", "pending")),
                current_step=gen_data.get("current_step", 0),
                skills_done=gen_data.get("skills_done", []),
                retry_counts=gen_data.get("retry_counts", {}),
                retry_feedback=gen_data.get("retry_feedback", {}),
            ),
            chapter_loop=ChapterLoopStateData(
                current_chapter=cl_data.get("current_chapter", 0),
                current_step=cl_data.get("current_step", ""),
                step_index=cl_data.get("step_index", 0),
                chapter_states=chapter_states,
                per_chapter_review_enabled=cl_data.get("per_chapter_review_enabled", True),
                retry_counts=cl_data.get("retry_counts", {}),
                retry_budget_consumed=cl_data.get("retry_budget_consumed", {}),
                modify_feedback=cl_data.get("modify_feedback"),
                retry_feedback=cl_data.get("retry_feedback", {}),
                soft_fail_trackers=soft_fail_trackers,
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
            pending_re_dispatches=data.get("pending_re_dispatches", []),
            checkpoint_history=data.get("checkpoint_history", []),
            last_snapshot=data.get("last_snapshot", {}),
            closure_step=data.get("closure_step", 0),
            closure_skills_done=data.get("closure_skills_done", []),
            closure_retry_counts=data.get("closure_retry_counts", {}),
            last_trigger_failure=data.get("last_trigger_failure"),
            config=PipelineConfig(
                **{k: v for k, v in cfg_data.items() if k in PipelineConfig.__dataclass_fields__}
            ),
        )

    @classmethod
    def from_json(cls, json_str: str) -> PipelineState:
        """Deserialize from JSON string, with error handling for corrupt state."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as _e:
            from shenbi.logging import get_logger as _get_log

            _get_log(__name__).error("state_json_decode_error", error=str(_e))
            raise
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# 10d: Pipeline-state compaction
# ---------------------------------------------------------------------------


def _archive_chapter_state(
    project_dir: Path | str, chapter_key: str, chapter_state: ChapterState
) -> None:
    """Archive a single chapter state to a JSON file in state/archive/."""
    archive_dir = Path(project_dir) / "state" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"chapter-{chapter_key}.json"
    archive_data = {
        "chapter": chapter_key,
        "steps_done": chapter_state.steps_done,
        "status": chapter_state.status,
        "resonance_score": chapter_state.resonance_score,
        "audit_results": chapter_state.audit_results,
        "revision_count": chapter_state.revision_count,
        "audit_retry_count": chapter_state.audit_retry_count,
    }
    from shenbi.safe_write import safe_write

    safe_write(
        archive_path,
        json.dumps(archive_data, indent=2, ensure_ascii=False),
    )


def compact_pipeline_state(state: PipelineState) -> None:
    """Archive old chapter states and prune retry feedback.

    Reduces ~236KB (at 100 chapters) to ~80KB.
    """
    if not hasattr(state, "chapter_loop"):
        return

    cl = state.chapter_loop
    current = cl.current_chapter

    # Archive chapter states beyond last 10
    if hasattr(cl, "chapter_states"):
        keys_to_archive = [k for k in cl.chapter_states if k.isdigit() and int(k) < current - 10]
        for k in keys_to_archive:
            _archive_chapter_state(state.project_dir, k, cl.chapter_states.pop(k))

    # Prune retry_feedback to last 30 entries (dict order preserved, Python 3.7+)
    if hasattr(cl, "retry_feedback") and len(cl.retry_feedback) > 30:
        # Keep only the most recent 30 entries by insertion order
        items = list(cl.retry_feedback.items())
        cl.retry_feedback = dict(items[-30:])


# ---------------------------------------------------------------------------
# State machine healing: current_step corruption (Task 17-13)
# ---------------------------------------------------------------------------


def _heal_current_step(state: PipelineState, chapter_steps: list[Any]) -> None:
    """Heal current_step from step_index when current_step is empty.

    Fixes the known corruption bug: _advance sets step_index
    but not current_step, leaving it as "".

    Args:
        state: The pipeline state to heal.
        chapter_steps: Ordered list of ChapterStep objects defining the step
            sequence (imported from chapter_loop.CHAPTER_STEPS).
    """
    cl = state.chapter_loop
    if cl.current_step:
        return  # Already set, nothing to heal

    if cl.step_index <= 0:
        return  # Not yet started

    if cl.step_index < len(chapter_steps):
        cl.current_step = chapter_steps[cl.step_index].skill
    else:
        cl.current_step = "chapter_complete"

    from shenbi.logging import get_logger

    logger = get_logger(__name__)
    logger.warning(
        "healed_current_step",
        step_index=cl.step_index,
        new_current_step=cl.current_step,
    )


def _validate_state_consistency(state: PipelineState, chapter_steps: list[Any]) -> list[str]:  # pyright: ignore[reportUnusedFunction] -- called from cli.py on resume
    """Validate pipeline state consistency at resume. Heals if possible.

    Checks:
    - step_index > 0 but current_step is empty -> heal
    - step_index out of range -> clamp

    Args:
        state: The pipeline state to validate.
        chapter_steps: Ordered list of ChapterStep objects defining the step
            sequence.

    Returns:
        List of issue strings describing any problems found and actions taken.
        Empty list means state is consistent.
    """
    issues: list[str] = []
    cl = state.chapter_loop

    if not cl.current_step and cl.step_index > 0:
        issues.append(
            f"state_inconsistent: step_index={cl.step_index} but current_step='' -- auto-healing"
        )
        _heal_current_step(state, chapter_steps)

    if cl.step_index > len(chapter_steps):
        issues.append(
            f"step_index={cl.step_index} exceeds CHAPTER_STEPS length "
            f"({len(chapter_steps)}) -- clamping"
        )
        cl.step_index = len(chapter_steps)
        cl.current_step = "chapter_complete"

    return issues


# ---------------------------------------------------------------------------
# Single-writer merge helpers (Task 6 of Plan 18)
# ---------------------------------------------------------------------------


def _merge_step_result(state: PipelineState, result: Any) -> None:  # pyright: ignore[reportUnusedFunction]  -- called from chapter_loop.py
    """Merge a worker thread's result into PipelineState on the main thread.

    Single-writer (actor-model) pattern: only the main thread mutates state.
    Worker threads never touch PipelineState directly -- they return result
    objects. No lock required -- this runs only on the main thread.

    Args:
        state: The PipelineState to merge into.
        result: A DispatchResult or similar from a worker thread.
    """
    if getattr(result, "result", None):
        _apply_step_outputs(state, result.result)


def _apply_step_outputs(state: PipelineState, outputs: dict[str, Any]) -> None:
    """Apply step outputs to PipelineState on the main thread.

    Implementation depends on the result schema; e.g. update chapter_states,
    retry_feedback, etc. No lock required -- this runs only on the main thread.

    Args:
        state: The PipelineState to update.
        outputs: Dict of output fields from a worker thread result.
    """
    # Currently DispatchResult does not carry a structured result dict,
    # so this is a no-op. Future result types may pass structured data.
