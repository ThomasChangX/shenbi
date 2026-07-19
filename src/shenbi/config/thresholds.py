"""Single source of truth for all quality thresholds and audit-dimension safety rules.

Spec: 2026-07-19 configuration-coherence-and-threshold-governance-design §3.2 / §3.3.

Why this module exists: numeric thresholds were previously duplicated across
``pipeline/state.py`` (PipelineConfig.resonance_global_floor), skill prompts, and
gate code, and they drifted — e.g. state default 50 vs. the audit skill's
internal 65 floor (E11). Importing thresholds from here is the canonical path;
every consumer (state defaults, G0 coherence check, gate checkers) reads the
same value.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityThresholds:
    """Single source of truth for all quality thresholds.

    Attributes mirror the fields previously scattered across config / skills /
    gate code. Override per-project by constructing a custom instance; the
    ``DEFAULT_THRESHOLDS`` singleton below is what framework code imports.
    """

    # Resonance (overall prose resonance) — used by BOTH state routing AND audit
    # skill pass/fail. The state-config override is validated against this
    # default by the G0 coherence checker.
    resonance_global_floor: int = 65
    # Below this → force revision even if the floor is otherwise met.
    resonance_revision_trigger: int = 60
    # Minimum CJK characters per chapter (matches G4 chapter-word checks).
    word_count_floor: int = 3000
    # Minimum protagonist name mentions per chapter.
    protagonist_mention_floor: int = 3
    # System-term density, per mille. warn → G4 WARN, hard → G4 FAIL.
    system_term_density_warn: int = 30
    system_term_density_hard: int = 50


#: Canonical default thresholds. Import this rather than re-hardcoding numbers.
DEFAULT_THRESHOLDS = QualityThresholds()


#: Which audit dimensions are quality safety nets that cannot be disabled
#: without an explicit rationale. Keys mirror ``genre-config.json ->
#: auditDimensions``. A dimension absent from this matrix is treated as
#: non-critical (can be freely disabled).
AUDIT_SAFETY_MATRIX: dict[str, dict[str, object]] = {
    "texture": {
        "critical": True,
        "detects": "prose degradation, sensory detail loss, scene concreteness collapse",
        "cannot_disable_without": (
            "explicit human approval + an alternative detection mechanism for "
            "sensory/scene texture loss"
        ),
    },
    "antiAi": {
        "critical": True,
        "detects": "AI-generated text patterns, system-term leakage",
        "cannot_disable_without": "explicit human approval",
    },
    "continuity": {
        "critical": True,
        "detects": "narrative continuity tracking (character/object/plot consistency)",
        "cannot_disable_without": "explicit human approval + manual continuity review",
    },
    "dialogue": {
        "critical": False,
        "detects": "dialogue quality and naturalness",
        "can_disable": True,
    },
    "character": {
        "critical": False,
        "detects": "character voice and behaviour consistency",
        "can_disable": True,
    },
    "pacing": {
        "critical": False,
        "detects": "chapter pacing rhythm",
        "can_disable": True,
    },
}


def is_critical_audit_dimension(dim: str) -> bool:
    """Return True iff *dim* is a critical safety-net audit dimension."""
    entry = AUDIT_SAFETY_MATRIX.get(dim)
    return bool(entry and entry.get("critical"))
