"""G4 checker for shenbi-chapter-revision outputs.

Validates revision-specific content WITHIN the DecisionsDoc schema
(selections/adjustments), NOT against a non-existent `changes` array.
DecisionsDoc has `extra="forbid"`, so the checker must not invent fields.

Returns a JSON result string matching the G4 checker protocol:
make_composite_checker (decisions_validator.py:87) does
json.loads(existing_result) and expects {"status", "checks", "must_fix"}.
"""

from __future__ import annotations

import json

from typing import get_args

from shenbi.contracts.enums import (
    REVISION_MODE_ALIASES,
    RevisionMode,
    RevisionSeverity,
    RevisionStatus,
)
from shenbi.gates.shared import resolve_input_path
from shenbi.status import GateStatus

# Minimum rationale length per adjustment entry (the Adjustment model requires
# `rationale` but does not enforce a minimum length).
_MIN_RATIONALE_LEN = 20

# spec #34 T903: legacy production severity values normalized read-side.
_LEGACY_SEVERITY: dict[str, str] = {
    "blocking": "high",
    "critical": "high",
    "critical_per_audit": "high",
    "warning": "medium",
    "minor": "low",
    "info": "low",
    "none": "low",
    "observation": "low",
}


def g4_chapter_revision(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,
    repo_root: str | None = None,
) -> str:
    """Validate revision decisions for content quality within DecisionsDoc.

    Works WITHIN the existing schema (selections/adjustments). Checks:
        - If ``adjustments`` is empty, ``selections`` MUST document a no-op/
          skip decision (e.g. target contains 'no_revision'/'skip').
        - Each adjustment's ``rationale`` must be >= 20 characters.

    Returns:
        A JSON result string: ``{"status": GateStatus.PASS|"FAIL",
        "checks": [...], "must_fix": [...]}``. This shape is what
        ``make_composite_checker`` expects via ``json.loads(existing_result)``.
    """
    issues: list[str] = []

    for fp in fps or []:
        p = resolve_input_path(fp, rd)
        if "revision" not in p.name or p.suffix != ".json":
            continue  # Only check revision decisions JSON

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            issues.append(f"G4.rev.invalid_json:{p.name}")
            continue

        if not isinstance(data, dict):
            issues.append(f"G4.rev.not_object:{p.name}")
            continue

        adjustments = data.get("adjustments", [])

        # spec #34 T903/T910: value-domain checks (severity/mode/status) with
        # read-side legacy normalization. New outputs must use canonical values.
        _check_value_domains(data, p.name, issues)

        # HARD: if no adjustments, the revision mode must be documented
        # in selections (a no-op/skip decision).
        if not adjustments:
            selections = data.get("selections", [])
            has_skip_selection = any(
                isinstance(s, dict)
                and (
                    "no_revision" in str(s.get("target", "")).lower()
                    or "skip" in str(s.get("target", "")).lower()
                    or "skip" in str(s.get("basis", "")).lower()
                )
                for s in selections
            )
            if not has_skip_selection:
                issues.append(
                    f"G4.rev.empty_adjustments_no_skip:{p.name} -- "
                    f"revision has zero adjustments and no documented skip reason"
                )

        # HARD: each adjustment must have substantive rationale (>= 20 chars)
        for i, adj in enumerate(adjustments):
            if not isinstance(adj, dict):
                issues.append(f"G4.rev.adjustment_{i}_not_object:{p.name}")
                continue
            rationale = str(adj.get("rationale", ""))
            if len(rationale) < _MIN_RATIONALE_LEN:
                issues.append(
                    f"G4.rev.adjustment_{i}_thin_rationale:{p.name} -- "
                    f"rationale must be >= {_MIN_RATIONALE_LEN} chars, got {len(rationale)}"
                )

    return json.dumps(
        {
            # spec #34 F402/F711: the undocumented out-of-vocab status string
            # was removed — the gate outcome is FAIL, severity carried in
            # must_fix prefixes.
            "status": GateStatus.PASS if not issues else GateStatus.FAIL,
            "checks": [],
            "must_fix": issues,
        },
        ensure_ascii=False,
    )


def _check_value_domains(data: dict[str, object], fname: str, issues: list[str]) -> None:
    """G4 value-domain checks for revision-decisions (spec #34 T903/T910).

    severity must be a canonical RevisionSeverity member (legacy values are
    tolerated via the normalization map but reported); mode must be a
    RevisionMode member (alias no_op tolerated); top-level status must be a
    RevisionStatus member. Tolerated legacy values are reported as must_fix
    so new outputs converge on canonical values.
    """
    legal_sev = set(get_args(RevisionSeverity))
    raw_sev = str(data.get("severity", "") or "")
    if raw_sev:
        norm = _LEGACY_SEVERITY.get(raw_sev.lower(), raw_sev)
        if norm not in legal_sev:
            issues.append(f"G4.rev.severity_out_of_vocab:{fname}:{raw_sev!r}")
        elif norm != raw_sev:
            issues.append(f"G4.rev.severity_legacy_value:{fname}:{raw_sev}->{norm}")

    legal_modes = {m.value for m in RevisionMode}
    raw_mode = str(data.get("mode", "") or "")
    if raw_mode:
        norm_mode = REVISION_MODE_ALIASES.get(raw_mode, raw_mode)
        if norm_mode not in legal_modes:
            issues.append(f"G4.rev.mode_out_of_vocab:{fname}:{raw_mode!r}")
        elif norm_mode != raw_mode:
            issues.append(f"G4.rev.mode_legacy_value:{fname}:{raw_mode}->{norm_mode}")

    legal_status = set(get_args(RevisionStatus))
    raw_status = str(data.get("status", "") or "")
    if raw_status and raw_status not in legal_status:
        issues.append(f"G4.rev.status_out_of_vocab:{fname}:{raw_status!r}")
