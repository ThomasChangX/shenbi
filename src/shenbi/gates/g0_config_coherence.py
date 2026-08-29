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
from typing import Any

from shenbi.config.thresholds import (
    AUDIT_SAFETY_MATRIX,
    DEFAULT_THRESHOLDS,
    resolve_audit_dimensions,
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
    resonance_global_floor: int | float | None = None,
) -> list[str]:
    """Validate genre-config + state-config coherence.

    Args:
        project_dir: Project root containing ``genre-config.json``.
        resonance_global_floor: The in-effect resonance floor (read from
            ``PipelineState.config`` by the caller). ``None`` skips the
            threshold-mismatch / floor-reasonableness checks (e.g. when G0
            runs before any state exists). Non-numeric values are flagged
            as ``floor_invalid_type`` (never crash, F606 read side).

    Returns:
        List of ``G0.cc.*`` issue strings; empty means coherent.
    """
    issues: list[str] = []

    # --- Check 1 & 2: floor coherence (only when a floor was supplied). ---
    if resonance_global_floor is not None:
        # Defensive runtime guard: untyped callers may pass str/None-like values
        # despite the declared signature (pyright: the isinstance is load-bearing).
        if isinstance(resonance_global_floor, bool) or not isinstance(
            resonance_global_floor,
            (int, float),  # pyright: ignore[reportUnnecessaryIsInstance]
        ):
            issues.append(
                f"G0.cc.floor_invalid_type:resonance_global_floor="
                f"{resonance_global_floor!r} ({type(resonance_global_floor).__name__}) — "
                f"expected int/float"
            )
        else:
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
            config: Any = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            config = {}
        # Top-level non-dict (e.g. a JSON list) is malformed too — loud FAIL,
        # never an AttributeError escaping the narrow g0.py except (F666 class).
        if not isinstance(config, dict):
            malformed = True
            audit_dims: dict[str, object] = {}
        else:
            audit_dims, malformed = resolve_audit_dimensions(config)
        if malformed:
            issues.append(
                "G0.cc.malformed_audit_dimensions — auditDimensions must be an "
                "object mapping dimension -> bool; got a scalar/list value. "
                "All genre audits are effectively disabled by this shape."
            )
        else:
            for dim, detects in _CRITICAL_DIMENSIONS.items():
                # Key absent = enabled (criticality-split semantics); any
                # present-but-not-True value counts as disabling (0/null/""/1).
                if dim in audit_dims and audit_dims[dim] is not True:
                    cannot_disable = AUDIT_SAFETY_MATRIX[dim].get(
                        "cannot_disable_without", "explicit human approval"
                    )
                    issues.append(
                        f"G0.cc.critical_audit_disabled:{dim} — disabling this "
                        f"removes: {detects}. This is a quality safety net. "
                        f"Cannot disable without {cannot_disable}."
                    )

    return issues
