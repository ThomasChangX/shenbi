"""Spec #91 T1: gate-status comparison guard (comparison-side AST lint).

lint_status_strings guards the EMIT side (bare status strings in dict
literals). This lint guards the COMPARE side: inside its domain, a gate
result's status must be judged through ``shenbi.status.gate_passed`` (the
single source), never by comparing against PASS/SKIP literals directly.
Also forbids re-introducing private ``def *_gate_passed`` copies.

Known residuals (spec r2.3c, deliberately out of scope):
- inverted compares (``== "FAIL"`` / ``!= GateStatus.FAIL``)
- indirect compares through an intermediate variable
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

DOMAIN: list[Path] = [
    Path("src/shenbi/pipeline"),
    Path("src/shenbi/phase_runner.py"),
]

STATUS_KEYS = frozenset({"status", "state", "classification", "s"})
PASS_LITERALS = frozenset({"PASS", "SKIP"})
GATE_STATUS_ENUM = "GateStatus"


def _is_status_read(node: ast.AST) -> bool:
    """True for ``x.get("status", ...)`` or ``x["status"]`` shaped reads."""
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "get":
            args = node.args
            if args and isinstance(args[0], ast.Constant) and args[0].value in STATUS_KEYS:
                return True
    if isinstance(node, ast.Subscript):
        sl = node.slice
        if isinstance(sl, ast.Constant) and sl.value in STATUS_KEYS:
            return True
    return False


def _is_pass_literal(node: ast.AST) -> bool:
    """True for ``"PASS"``/``"SKIP"`` constants or GateStatus.PASS/SKIP attrs."""
    if isinstance(node, ast.Constant) and node.value in PASS_LITERALS:
        return True
    if (
        isinstance(node, ast.Attribute)
        and node.attr in PASS_LITERALS
        and isinstance(node.value, ast.Name)
        and node.value.id == GATE_STATUS_ENUM
    ):
        return True
    if isinstance(node, ast.Tuple):
        return any(_is_pass_literal(elt) for elt in node.elts)
    return False


def scan_file(text: str, path: str) -> list[str]:
    """Return violation strings for one Python source file."""
    violations: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [f"{path}: unparseable (skipped)"]
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name.endswith("_gate_passed"):
                violations.append(
                    f"{path}:{node.lineno}: private gate-status judge "
                    f"`{node.name}` — route through shenbi.status.gate_passed"
                )
        elif isinstance(node, ast.Compare):
            sides: list[ast.AST] = [node.left, *node.comparators]
            status_side = any(_is_status_read(side) for side in sides)
            if not status_side:
                continue
            if any(_is_pass_literal(side) for side in sides):
                violations.append(
                    f"{path}:{node.lineno}: bare PASS/SKIP compare on a gate "
                    "status — use shenbi.status.gate_passed (spec #91 T1)"
                )
    return violations


def scan(roots: list[Path] | None = None) -> list[str]:
    """Scan the default domain (pipeline/ + phase_runner.py) or given roots."""
    targets = roots if roots is not None else DOMAIN
    violations: list[str] = []
    for root in targets:
        files = sorted(root.rglob("*.py")) if root.is_dir() else [root]
        for py in files:
            if not py.exists():
                continue
            violations.extend(scan_file(py.read_text(encoding="utf-8"), str(py)))
    return violations


def main(argv: list[str] | None = None) -> int:
    """Print every violation; exit 1 if any found."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(list(argv) if argv is not None else None)
    violations = scan()
    for v in violations:
        print(v)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
