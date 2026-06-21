"""Typed status vocabulary + typed result structures (spec §5.2, audit D3).

THE single definition of every status string in the framework. Emit sites use
enum members through typed result structures, so ``"status": "PASSED"`` is a
static type error (not merely a runtime risk) under mypy AND basedpyright.

Wire compatibility: each enum's value equals the string the framework already
serializes, so this module changes no on-disk state files or JSON contracts.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, TypedDict


class GateStatus(StrEnum):
    """Result of a gate check."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    WARN = "WARN"
    # Stub gates (shared.unimplemented) emit this. Lives here — not borrowed from
    # ScoringStatus — so a gate result envelope never carries a non-gate status
    # and ``GateResult.status: GateStatus`` is a truthful type.
    UNIMPLEMENTED = "UNIMPLEMENTED"


class PhaseState(StrEnum):
    """Phase state-machine states (values match existing phase-state/*.json)."""

    CREATED = "created"
    STARTED = "started"
    SKILLS_DONE = "skills_done"
    SCORED = "scored"
    FINALIZED = "finalized"


class CommandStatus(StrEnum):
    """phase_runner command outcome."""

    OK = "ok"
    BLOCKED = "blocked"
    ERROR = "error"


class ScoringStatus(StrEnum):
    """Scoring-pipeline outcome."""

    OK = "ok"
    REJECT = "REJECT"
    MARKER_MISSING = "MARKER_MISSING"
    UNIMPLEMENTED = "UNIMPLEMENTED"


class ScoreClassification(StrEnum):
    """classify() bucket for a final score."""

    PASS_EXCELLENT = "PASS (excellent)"
    PASS_ACCEPTABLE = "PASS (acceptable)"
    CONDITIONAL = "CONDITIONAL"
    FAIL = "FAIL"


class GateResult(TypedDict, total=False):
    """Typed envelope for a gate result. ``status`` carries a GateStatus member."""

    gate: str
    status: GateStatus
    timestamp: str
    checks: list[dict[str, Any]]
    blocked_action: str
    must_fix: list[str]


class CommandResult(TypedDict, total=False):
    """Typed envelope for a phase_runner command outcome."""

    status: CommandStatus
    phase: str
    skill: str
    action: str
    reads: list[str]
    writes: list[str]


# Every bare status string the framework emits. The lint in Task 3 forbids
# these as dict *values* outside this module, so a second source cannot land.
STATUS_STRING_LITERALS: frozenset[str] = frozenset(
    s.value
    for s in (
        *GateStatus,
        *PhaseState,
        *CommandStatus,
        *ScoringStatus,
        *ScoreClassification,
    )
)
