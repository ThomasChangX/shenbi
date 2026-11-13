#!/usr/bin/env python3
r"""Generate tests/fixtures/g4-id-inventory.json (spec #88 T3).

Three sources (plan M2), one ``enumerate_ids()`` function consumed by both
``--write`` and the property test (tests/property/gates/test_g4_id_inventory.py):

1. AST constant extraction: ``mf.append/extend`` emission sites in
   ``src/shenbi/gates/g4/*.py`` whose first constant segment starts ``G4.``
   (id = text between ``G4.`` and the first ``:``; trailing-dot family
   fragments are skipped — they are prefixes, not ids). The xc (id, detail)
   tuple family rides source 2 (helper-internal appends are scan-blind).
2. Explicit supplement: ids invisible to static extraction — layered-contract
   helper returns (composed at runtime via ``f"G4.{issue}"``), variable-prefix
   forms (cd.post_transition_cross :814 etc.), and registry-produced ids
   (G4.dec.<type> via pydantic_err_to_gate_failures). Source anchors in comments.
3. The two retained severity keys (transition/fatigue) — asserted present.

Read-only unless ``--write``.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_DIR = REPO_ROOT / "src" / "shenbi" / "gates" / "g4"

MF_RECEIVER = "mf"
EMIT_METHODS = {"append", "extend"}
_ID_RE = re.compile(r"G4\.([a-zA-Z0-9_.]+)")

# --- Source 2: explicit supplement (static-invisible live ids) -------------
# Layered-contract helper returns composed at runtime via f"G4.{issue}":
_SUPPLEMENT: tuple[str, ...] = (
    # chapter_drafting check_prop_handoffs helper (:207-211)
    "cd.prop_handoff",
    # chapter_drafting counter family (check_counter_reconciliation arms)
    "cd.counter.plan_conflict",
    "cd.counter.base_mismatch",
    "cd.counter.prose_mismatch",
    "cd.counter",
    # variable-prefix composed at call sites (post_declarations helpers)
    "cd.post_quote_verbatim",
    "cd.post_transition_cross",
    "rev.prop_purged",
    "cd.balance_value_drift",
    "cd.balance_value_drift.bundle",
    # registry-produced (decisions_validator via pydantic_err_to_gate_failures)
    "G4.dec".removeprefix("G4."),
    # ss. family via helper-mediated extend (state_settling issues lists)
    "ss.facts_ops",
    "ss.prop_row_match",
    "ss.identity_row_match",
    "ss.stale_declarations",
    "ss.matrix_structure.diff_area",
    # XC.narration_name via check_narration_name (inner-prefix strings)
    "XC.narration_name",
    # spec #88 T1c xc ids: built via helper ``issues.append((id, detail))``
    # (cross_chapter check_cross_chapter) then composed at the mf wrapper —
    # helper-internal appends are outside the mf scan position, so listed.
    "XC.pronoun_mismatch",
    "XC.org_drift",
    "XC.residence_drift",
    "XC.title_violation",
    "XC.reserved_name_hijack",
    "XC.prop_chain_origin",
    "XC.prop_undeclared",
    "XC.pov_break",
    "XC.timeline_rollback",
    "XC.balance_jump",
)
# Retained severity keys must be present (assertion in main).
_REQUIRED = ("transition", "fatigue")


def _is_mf_emit(node: ast.AST) -> bool:
    """mf.append/extend call with at least one positional argument."""
    if not isinstance(node, ast.Call) or not node.args:
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr in EMIT_METHODS
        and isinstance(func.value, ast.Name)
        and func.value.id == MF_RECEIVER
    )


def _first_constant(expr: ast.expr) -> str | None:
    """First constant segment of an emission argument (JoinedStr/Str/genexp)."""
    if isinstance(expr, ast.GeneratorExp):
        expr = expr.elt
    if isinstance(expr, ast.JoinedStr) and expr.values:
        expr = expr.values[0]
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    return None


def _iter_emission_ids(tree: ast.Module) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if not _is_mf_emit(node):
            continue
        arg = node.args[0]
        # constant first segment starting G4. (xc family ids ride the
        # explicit supplement — helper-internal tuple appends are blind)
        head = _first_constant(arg)
        if head:
            m = _ID_RE.match(head)
            if m and not m.group(1).endswith("."):  # skip family-prefix fragments
                out.add(m.group(1))
    return out


def enumerate_ids() -> list[str]:
    """Return the full live id roster (AST constants + supplements)."""
    ids: set[str] = set(_SUPPLEMENT)
    for path in sorted(SCAN_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        ids |= _iter_emission_ids(tree)
    return sorted(ids)


def main(argv: list[str] | None = None) -> int:
    """CLI: enumerate (default) or --write the inventory fixture."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write the fixture")
    args = parser.parse_args(argv)

    ids = enumerate_ids()
    missing = [k for k in _REQUIRED if k not in ids]
    if missing:
        raise SystemExit(f"required keys missing from enumeration: {missing}")

    if args.write:
        fixture = REPO_ROOT / "tests" / "fixtures" / "g4-id-inventory.json"
        fixture.write_text(
            json.dumps(
                {
                    "ids": ids,
                    "generated_at": datetime.now(UTC).isoformat(),
                    "generator": "tools/gen_g4_id_inventory.py",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {len(ids)} ids to {fixture}")
    else:
        for i in ids:
            print(i)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
