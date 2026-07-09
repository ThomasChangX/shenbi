"""G4 checker for decisions.json schema validation (Layer A).

Schema version, required keys, and P2.5 rationale rules now live in
:class:`DecisionsDoc` (Task 5). This checker handles file I/O (skip non-JSON,
invalid-JSON, not-object) and delegates structural validation to the model,
mapping its ``ValidationError`` to ``G4.dec.{type}`` micro-failures via the
generic adapter.
"""

from __future__ import annotations

import json
from typing import Any
from collections.abc import Callable

from pydantic import ValidationError

from shenbi.contracts.schemas.adapt import pydantic_err_to_gate_failures
from shenbi.contracts.schemas.decisions import DecisionsDoc
from shenbi.gates.shared import fail, passed, resolve_input_path
from shenbi.status import GateStatus


def g4_decisions(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Validate decisions.json against shenbi-decisions-v1 schema + P2.5 rules.

    Only processes *.json files — non-JSON files (e.g., the main .md artifact
    passed by composite checkers) are silently skipped. This prevents crashes
    when g4_decisions is used as the decisions_checker in a composite that
    receives all skill outputs including markdown.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    for fp in fps or []:
        p = resolve_input_path(fp, rd)
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

        # Schema version, required keys, and P2.5 rationale (DecisionsDoc).
        try:
            DecisionsDoc.model_validate(data)
            c.append({"id": "G4.dec", "file": fp, "s": "PASS"})
        except ValidationError as e:
            # pydantic_err_to_gate_failures already produces "G4.dec.<type>" IDs
            # (prefix is passed as "G4.dec"). Use its output directly — do NOT
            # re-split/re-prefix the id, which double-prefixes to "G4.dec.dec.<type>".
            mf.extend(
                f"{f['id']}:{fp}:{f['r']}" for f in pydantic_err_to_gate_failures(e, fp, "G4.dec")
            )

    if not fps:
        c.append({"id": "G4.dec", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-decisions", c, "scoring", mf)
    return passed("G4-decisions", c)


# Type alias for G4 checker functions:
# (file_paths, round_dir, project_dir, repo_root) -> JSON result string.
# Required for basedpyright to accept the checker dict values in generic.py.
G4CheckerFn = Callable[[list[str], str | None, str | None, str | None], str]


def make_composite_checker(
    existing_checker: G4CheckerFn, decisions_checker: G4CheckerFn
) -> G4CheckerFn:
    """Create a composite G4 checker that runs both existing + decisions validation.

    Returns FAIL if either checker fails; aggregates all checks and must_fix items.
    Both checkers always run (even if the first fails) to collect all failures.
    """

    def composite(
        fps: list[str],
        rd: str | None = None,
        project_dir: str | None = None,
        repo_root: str | None = None,
    ) -> str:
        # Partition by extension: structural checkers parse markdown and have NO
        # .json guard, so feeding them a .json file fails (no expected sections
        # in JSON). The decisions checker already skips non-.json. Route each
        # checker only the file types it can handle. "other" (non-.md/.json)
        # files go to both so neither silently drops them.
        md_files = [fp for fp in fps if fp.endswith(".md")]
        json_files = [fp for fp in fps if fp.endswith(".json")]
        other_files = [fp for fp in fps if not fp.endswith((".md", ".json"))]

        existing_result = existing_checker(md_files + other_files, rd, project_dir, repo_root)
        decisions_result = decisions_checker(json_files + other_files, rd, project_dir, repo_root)

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
