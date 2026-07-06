"""Typed state vocabulary and dataclasses for the novel pipeline state machine.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
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
    audit_retry_count: int = 0  # tracks audit BLOCKING revision attempts


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
    closure_skills_done: list[str] = field(default_factory=list)  # closure skill history
    closure_retry_counts: dict[str, int] = field(default_factory=dict)  # closure per-skill retries
    pending_re_dispatches: list[dict[str, Any]] = field(default_factory=list)
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
            pending_re_dispatches=data.get("pending_re_dispatches", []),
            checkpoint_history=data.get("checkpoint_history", []),
            last_snapshot=data.get("last_snapshot", {}),
            closure_step=data.get("closure_step", 0),
            closure_skills_done=data.get("closure_skills_done", []),
            closure_retry_counts=data.get("closure_retry_counts", {}),
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
