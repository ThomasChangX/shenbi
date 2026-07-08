"""G4 checker for decisions.json schema validation (Layer A)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from collections.abc import Callable

from shenbi.gates.shared import fail, passed
from shenbi.status import GateStatus
from shenbi.gates.g4._decisions_schema import (
    DECISIONS_SCHEMA_VERSION,
    validate_selection_rationale,
    validate_adjustment_rationale,
)


def g4_decisions(fps: list[str], rd: str | None = None) -> str:
    """Validate decisions.json against shenbi-decisions-v1 schema + P2.5 rules.

    Only processes *.json files — non-JSON files (e.g., the main .md artifact
    passed by composite checkers) are silently skipped. This prevents crashes
    when g4_decisions is used as the decisions_checker in a composite that
    receives all skill outputs including markdown.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    base = Path(rd) if rd else Path.cwd()

    for fp in fps or []:
        p = base / fp if not Path(fp).is_absolute() else Path(fp)
        if not p.exists():
            mf.append(f"G4.dec.not_found:{fp}")
            continue

        # CRITICAL: skip non-JSON files — the composite checker passes ALL skill
        # outputs (including .md artifacts). json.loads() on markdown would crash.
        if not fp.endswith(".json"):
            continue  # skip .md and other non-decisions files

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            mf.append(f"G4.dec.invalid_json:{fp}")
            continue

        if not isinstance(data, dict):
            mf.append(f"G4.dec.not_object:{fp}:got {type(data).__name__}")
            continue

        # Schema version
        if data.get("$schema") != DECISIONS_SCHEMA_VERSION:
            mf.append(f"G4.dec.schema_version:{fp}:{data.get('$schema')}")

        # Required keys
        required = {"skill", "chapter", "selections", "produced_at"}
        missing = required - data.keys()
        if missing:
            mf.append(f"G4.dec.missing_keys:{fp}:{missing}")

        # Validate selections (P2.5)
        for i, sel in enumerate(data.get("selections", [])):
            if not isinstance(sel, dict):
                mf.append(f"G4.dec.selection[{i}]:{fp}:not a dict ({type(sel).__name__})")
                continue
            errors = validate_selection_rationale(
                basis=sel.get("basis", ""),
                severity=sel.get("severity", "low"),
                rationale=sel.get("rationale"),
            )
            for err in errors:
                mf.append(f"G4.dec.selection[{i}]:{fp}:{err}")

        # Validate adjustments (always require rationale)
        for i, adj in enumerate(data.get("adjustments", [])):
            if not isinstance(adj, dict):
                mf.append(f"G4.dec.adjustment[{i}]:{fp}:not a dict ({type(adj).__name__})")
                continue
            errors = validate_adjustment_rationale(adj.get("rationale"))
            for err in errors:
                mf.append(f"G4.dec.adjustment[{i}]:{fp}:{err}")

        c.append({"id": "G4.dec", "file": fp, "s": "PASS"})

    if not fps:
        c.append({"id": "G4.dec", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-decisions", c, "scoring", mf)
    return passed("G4-decisions", c)


# Type alias for G4 checker functions: (file_paths, round_dir) -> JSON result string.
# Required for basedpyright to accept the checker dict values in generic.py.
G4CheckerFn = Callable[[list[str], str | None], str]


def make_composite_checker(
    existing_checker: G4CheckerFn, decisions_checker: G4CheckerFn
) -> G4CheckerFn:
    """Create a composite G4 checker that runs both existing + decisions validation.

    Returns FAIL if either checker fails; aggregates all checks and must_fix items.
    Both checkers always run (even if the first fails) to collect all failures.
    """

    def composite(fps: list[str], rd: str | None = None) -> str:
        # Partition by extension: structural checkers parse markdown and have NO
        # .json guard, so feeding them a .json file fails (no expected sections
        # in JSON). The decisions checker already skips non-.json. Route each
        # checker only the file types it can handle. "other" (non-.md/.json)
        # files go to both so neither silently drops them.
        md_files = [fp for fp in fps if fp.endswith(".md")]
        json_files = [fp for fp in fps if fp.endswith(".json")]
        other_files = [fp for fp in fps if not fp.endswith((".md", ".json"))]

        existing_result = existing_checker(md_files + other_files, rd)
        decisions_result = decisions_checker(json_files + other_files, rd)

        # Parse both results and aggregate.
        # CRITICAL: fail() emits key "must_fix" (not "failures") — see shared.py:113.
        existing_data: dict[str, Any] = {}
        decisions_data: dict[str, Any] = {}
        try:
            existing_data = json.loads(existing_result)
        except (json.JSONDecodeError, TypeError):
            existing_data = {"status": GateStatus.FAIL, "checks": [], "must_fix": ["unparseable"]}
        try:
            decisions_data = json.loads(decisions_result)
        except (json.JSONDecodeError, TypeError):
            decisions_data = {"status": GateStatus.FAIL, "checks": [], "must_fix": ["unparseable"]}

        combined_checks = existing_data.get("checks", []) + decisions_data.get("checks", [])
        combined_must_fix = existing_data.get("must_fix", []) + decisions_data.get("must_fix", [])

        if combined_must_fix:
            return fail(
                f"G4-composite-{existing_checker.__name__}",
                combined_checks,
                "scoring",
                combined_must_fix,
            )
        return passed(f"G4-composite-{existing_checker.__name__}", combined_checks)

    return composite
