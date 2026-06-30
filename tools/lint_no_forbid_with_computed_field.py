#!/usr/bin/env python3
"""N7 guard: models with @computed_field cannot set extra='forbid'.

Usage: python tools/lint_no_forbid_with_computed_field.py <path>
exit 0 = pass; exit 1 = violation found.

Limitation: only checks model_config within the same class body as @computed_field.
Inherited extra='forbid' from a parent class is not detected.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def _has_computed_field(class_body: list[ast.stmt]) -> bool:
    for item in class_body:
        if isinstance(item, ast.FunctionDef):
            for dec in item.decorator_list:
                if "computed_field" in ast.unparse(dec):
                    return True
    return False


def _has_forbid_config(class_body: list[ast.stmt]) -> bool:
    for item in class_body:
        if isinstance(item, ast.Assign):
            for t in item.targets:
                if (
                    isinstance(t, ast.Name)
                    and t.id == "model_config"
                    and "forbid" in ast.unparse(item.value)
                ):
                    return True
        if (
            isinstance(item, ast.AnnAssign)
            and isinstance(item.target, ast.Name)
            and item.target.id == "model_config"
            and item.value
            and "forbid" in ast.unparse(item.value)
        ):
            return True
    return False


def lint_dir(root: Path) -> list[str]:
    """Walk all .py files under root, return violation messages."""
    violations: list[str] = []
    for py in root.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ClassDef)
                and _has_computed_field(node.body)
                and _has_forbid_config(node.body)
            ):
                violations.append(
                    f"{py}:{node.lineno}: {node.name} has computed_field but sets extra=forbid (N7)"
                )
    return violations


EXPECTED_ARGS = 2


def main() -> int:
    """CLI entry point: lint a directory, exit 0=pass / 1=violation."""
    if len(sys.argv) != EXPECTED_ARGS:
        print("usage: lint_no_forbid_with_computed_field.py <path>", file=sys.stderr)
        return 2
    vs = lint_dir(Path(sys.argv[1]))
    for v in vs:
        print(v, file=sys.stderr)
    return 1 if vs else 0


if __name__ == "__main__":
    sys.exit(main())
