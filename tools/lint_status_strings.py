#!/usr/bin/env python3
"""Lint: no bare status-vocab string literal on a result-envelope key outside status.py.

Enforces spec D3's "no bare status string-literals outside status.py" rule on the
three result-envelope keys that carry status vocabulary — ``"status"``, ``"state"``,
and ``"classification"`` (STATUS_KEYS). Values are scanned recursively, so bare
literals inside ternaries / bool-op expressions (e.g. ``{"status": "PASS" if ok
else "FAIL"}``) are caught too. This avoids false positives on check-item dicts
like ``{"id": "G3.1", "s": "PASS"}`` (key "s") and on read-comparisons
(``x == "FAIL"``), which are not emit sites.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shenbi.status import STATUS_STRING_LITERALS

EXEMPT = "status.py"
# The three keys the audit (D3) identifies as overloading status vocabulary.
STATUS_KEYS = frozenset({"status", "state", "classification"})
TARGET_GLOBS = ("src/shenbi/**/*.py",)


def _is_status_value(s: object) -> bool:
    return isinstance(s, str) and s in STATUS_STRING_LITERALS


def _is_status_key(node: object) -> bool:
    return isinstance(node, ast.Constant) and node.value in STATUS_KEYS


def _status_literals(node: ast.AST) -> list[ast.Constant]:
    """Collect bare status-vocab Constant literals anywhere in an expression.

    Recursive so ternaries (``"PASS" if ok else "FAIL"``) and bool-op
    expressions are covered — the value is already gated on the key being a
    status/state/classification emit site, so every literal in it is an emit.
    """
    return [
        sub
        for sub in ast.walk(node)
        if isinstance(sub, ast.Constant) and _is_status_value(sub.value)
    ]


class _Visitor(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[str] = []

    def visit_Dict(self, node: ast.Dict) -> None:
        # node.keys may contain None (for ** unpacks); pair with values by index.
        for k, v in zip(node.keys, node.values, strict=False):
            if _is_status_key(k):
                for lit in _status_literals(v):
                    self.violations.append(
                        f"{self.filename}:{lit.lineno}: bare status string {lit.value!r}"
                    )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # d["status"] = "PASS"  →  Subscript target keyed by "status"
        for tgt in node.targets:
            if isinstance(tgt, ast.Subscript) and _is_status_key(tgt.slice):
                for lit in _status_literals(node.value):
                    self.violations.append(
                        f"{self.filename}:{lit.lineno}: bare status string {lit.value!r}"
                    )
        self.generic_visit(node)


def find_violations(filename: str, tree: ast.AST) -> list[str]:
    """Return bare-status-string violations in *tree*; status.py is always exempt."""
    # status.py is THE canonical source of these strings — always exempt.
    if Path(filename).name == EXEMPT:
        return []
    v = _Visitor(filename)
    v.visit(tree)
    return v.violations


def scan(roots: Iterable[str]) -> list[str]:
    """Scan src/shenbi/**/*.py (except status.py) for bare-status-string violations."""
    out: list[str] = []
    for pattern in TARGET_GLOBS:
        for py in Path().glob(pattern):
            if py.name == EXEMPT:
                continue
            out.extend(find_violations(str(py), ast.parse(py.read_text(encoding="utf-8"))))
    return out


def main() -> int:
    """Print every violation and exit non-zero if any were found."""
    vios = scan(TARGET_GLOBS)
    for v in vios:
        print(v)
    return 1 if vios else 0


if __name__ == "__main__":
    sys.exit(main())
