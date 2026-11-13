#!/usr/bin/env python3
r"""AST lint: must_fix emission strings stay ``G4.<id>``-first (spec #88 T1).

Scans ``src/shenbi/gates/g4/*.py`` for ``mf.append(...)`` / ``mf.extend(...)``
calls (``mf`` is the repo-wide must_fix list convention, ~213 sites) and
asserts the emitted strings originate in legal id-first form.

Legal grammar (spec #88 §2 T1, r2.8):
- ``finding(...)`` calls (the shared emitter, gates/shared.py);
- string constants starting with ``"G4."``;
- JoinedStr (f-string) whose FIRST constant segment starts with ``"G4."``
  (the layered-contract shape ``mf.extend(f"G4.{issue}")`` is legal);
- GeneratorExp elements judged by the same rules
  (``mf.extend(f"G4.XC.x:{n}:{i}" for ...)``).

Registered blind spots (NOT judged — declared residual risk, mirroring the
lint_truth_format_single_source house style; runtime depth is provided by
the spec #88 T5 parameterized check_id assertions):
- cross-function indirection: bare ``Name`` arguments
  (``mf.extend(_issues)`` — 8 sites: protagonist_issues/archetype_issues x2/
  _mx_fails/matrix_issues/_issues x2/tmpl_mf) and non-``finding()`` call
  arguments (``mf.extend(_check_hooks_structure(...))`` — 5 sites);
- ``BinOp`` concatenation and ``str.format()``/``%`` built patterns
  (1 BinOp site today, chapter_planning:704).

Known residual charset shapes (lint-legal but outside the id charset
contract — registered in spec #88 §1, rewrite deferred to a later batch):
genre_config ``G4.gc.{filename}``, volume_outlining ``G4.vo.*[{卷头}]``,
pacing_design ``G4.pd.{loc}``; character_design archetype ids transit
``local_failures`` (out of scan scope entirely).
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_GLOB = REPO_ROOT / "src" / "shenbi" / "gates" / "g4" / "*.py"

FINDING_FUNC = "finding"
PREFIX = "G4."
MF_RECEIVER = "mf"
EMIT_METHODS = {"append", "extend"}


def is_legal_argument(expr: ast.expr) -> bool:
    """Pure predicate: does *expr* produce must_fix strings in legal form?

    Blind-spot shapes (Name / non-finding Call / BinOp / str.format / %)
    return True — they are registered residuals, not violations.
    """
    if isinstance(expr, ast.Call | ast.Name | ast.BinOp):
        # finding(...) calls are legal by grammar; helper-produced-list calls
        # and bare variables are cross-function indirection, BinOp is
        # concatenation — all registered blind spots, all not judged.
        return True
    if isinstance(expr, ast.JoinedStr):
        first = expr.values[0] if expr.values else None
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value.startswith(PREFIX)
        return False  # first segment is an expression (path/variable prefix)
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value.startswith(PREFIX)
    if isinstance(expr, ast.GeneratorExp):
        return is_legal_argument(expr.elt)
    return True  # unknown shapes (str.format/%): registered blind spot


def _iter_violations(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr not in EMIT_METHODS:
            continue
        if not isinstance(func.value, ast.Name) or func.value.id != MF_RECEIVER:
            continue
        if not node.args:
            continue
        if not is_legal_argument(node.args[0]):
            out.append((f"{path.relative_to(REPO_ROOT)}:{node.lineno}", node.lineno))
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entry: check mode (exit 1 on violations) or --list enumeration."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--list",
        action="store_true",
        help="print every violating site (the authoritative red list)",
    )
    args = parser.parse_args(argv)

    violations: list[str] = []
    for path in sorted(SCAN_GLOB.parent.glob(SCAN_GLOB.name)):
        violations.extend(site for site, _ in _iter_violations(path))

    if args.list:
        # Enumeration mode: authoritative red list to stdout, exit 0 —
        # consumed by plan Task 2 Step 5 reconciliation redirects.
        for site in violations:
            print(site)
        return 0

    if violations:
        for site in violations:
            print(f"must_fix emission contract violation: {site}", file=sys.stderr)
        print(
            f"spec #88 T1: {len(violations)} illegal must_fix emission site(s); "
            "rewrite to finding()/id-first form",
            file=sys.stderr,
        )
        return 1
    print("OK: all mf emission sites are id-first (spec #88 T1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
