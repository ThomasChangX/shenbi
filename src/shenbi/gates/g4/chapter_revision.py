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
from pathlib import Path

from shenbi.status import GateStatus

# Minimum rationale length per adjustment entry (the Adjustment model requires
# `rationale` but does not enforce a minimum length).
_MIN_RATIONALE_LEN = 20


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
        A JSON result string: ``{"status": "PASS"|"HARD_FAIL",
        "checks": [...], "must_fix": [...]}``. This shape is what
        ``make_composite_checker`` expects via ``json.loads(existing_result)``.
    """
    issues: list[str] = []

    for fp in fps or []:
        p = Path(fp)
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

    # Return a JSON result string matching the G4 checker protocol.
    # make_composite_checker (decisions_validator.py:87) does
    # json.loads(existing_result) and expects {"status","checks","must_fix"}.
    return json.dumps(
        {
            "status": GateStatus.PASS if not issues else "HARD_FAIL",
            "checks": issues,
            "must_fix": issues,
        },
        ensure_ascii=False,
    )
