"""G0 sub-check: genre-config / state-config internal coherence.

Spec: 2026-07-19 configuration-coherence-and-threshold-governance-design §3.1.

Detects three classes of configuration defect that previously allowed quality
degradation to pass undetected:

  * ``G0.cc.threshold_mismatch`` — the in-effect resonance floor (read from
    PipelineState, where it actually lives) differs from the single-source-of-
    truth default in :mod:`shenbi.config.thresholds`. E11.
  * ``G0.cc.critical_audit_disabled`` — a critical safety-net audit dimension
    (texture / antiAi / continuity) is disabled in genre-config.json. E34.
  * ``G0.cc.floor_too_low`` — the floor is below 60, allowing degraded
    chapters to pass without revision.

The function returns a list of issue strings (empty = coherent). It composes
with the other G0 sub-checks that return ``list[str]``.
"""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.config.thresholds import (
    AUDIT_SAFETY_MATRIX,
    DEFAULT_THRESHOLDS,
)
from shenbi.logging import get_logger

log = get_logger(__name__)

#: Audit dimensions that, if disabled, remove a quality safety net. The values
#: are the human-readable explanations emitted in the issue string.
_CRITICAL_DIMENSIONS: dict[str, str] = {
    dim: str(entry.get("detects", "an unknown quality dimension"))
    for dim, entry in AUDIT_SAFETY_MATRIX.items()
    if entry.get("critical")
}

#: Floor below which the "floor too low" rule fires.
_FLOOR_TOO_LOW = DEFAULT_THRESHOLDS.resonance_revision_trigger  # 60


def check_config_coherence(
    project_dir: Path,
    *,
    resonance_global_floor: int | None = None,
) -> list[str]:
    """Validate genre-config + state-config coherence.

    Args:
        project_dir: Project root containing ``genre-config.json``.
        resonance_global_floor: The in-effect resonance floor (read from
            ``PipelineState.config`` by the caller). ``None`` skips the
            threshold-mismatch / floor-reasonableness checks (e.g. when G0
            runs before any state exists).

    Returns:
        List of ``G0.cc.*`` issue strings; empty means coherent.
    """
    issues: list[str] = []

    # --- Check 1 & 2: floor coherence (only when a floor was supplied). ---
    if resonance_global_floor is not None:
        if resonance_global_floor != DEFAULT_THRESHOLDS.resonance_global_floor:
            lo, hi = sorted((resonance_global_floor, DEFAULT_THRESHOLDS.resonance_global_floor))
            issues.append(
                f"G0.cc.threshold_mismatch:resonance_floor "
                f"state={resonance_global_floor} vs "
                f"default={DEFAULT_THRESHOLDS.resonance_global_floor} — chapters "
                f"scoring {lo}-{hi - 1} will pass one gate but fail the other "
                f"silently"
            )
        if resonance_global_floor < _FLOOR_TOO_LOW:
            issues.append(
                f"G0.cc.floor_too_low:resonance_global_floor="
                f"{resonance_global_floor} — floors below {_FLOOR_TOO_LOW} allow "
                f"degraded chapters to pass without revision"
            )

    # --- Check 3: critical audit dimensions enabled. ---
    cfg_path = project_dir / "genre-config.json"
    if cfg_path.exists():
        try:
            config = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            config = {}
        audit_dims = config.get("auditDimensions", {}) if isinstance(config, dict) else {}
        for dim, detects in _CRITICAL_DIMENSIONS.items():
            # Default True if the key is absent (only flag explicit disabling).
            if audit_dims.get(dim, True) is False:
                cannot_disable = AUDIT_SAFETY_MATRIX[dim].get(
                    "cannot_disable_without", "explicit human approval"
                )
                issues.append(
                    f"G0.cc.critical_audit_disabled:{dim} — disabling this "
                    f"removes: {detects}. This is a quality safety net. "
                    f"Cannot disable without {cannot_disable}."
                )

    return issues
