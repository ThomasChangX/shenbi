#!/usr/bin/env python3
r"""Spec #89 T2: gates/ chapter-(\d+) inline-regex zero lint (AST judge).

Single allowed site: CHAPTER_NUM_RE in src/shenbi/gates/shared.py (its
re.compile definition Assign is exempt; any other re.* call carrying the
literal turns red). Aligns with #85 lint_truth_format_single_source and
#88 lint_mustfix_emission conventions.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATES = REPO / "src" / "shenbi" / "gates"
ALLOWED_FILE = "shared.py"
PATTERN = "chapter-(\\d+)"
RE_FUNCS = ("compile", "search", "match", "fullmatch", "findall", "sub", "subn", "split")


def _pattern_arg(node: ast.Call) -> str | None:
    """The string pattern of a re.* call: positional or keyword ``pattern=``."""
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    for kw in node.keywords:
        if (
            kw.arg == "pattern"
            and isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, str)
        ):
            return kw.value.value
    return None


def _is_definition(node: ast.Call, pattern: str) -> bool:
    """True only for ``re.compile(PATTERN)`` — the exact single-source definition.

    Exact equality (not containment) so a second compile embedding the
    pattern still reds; ``re`` module check so ``foo.compile`` never exempts.
    """
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    return (
        func.attr == "compile"
        and pattern == PATTERN
        and isinstance(func.value, ast.Name)
        and func.value.id == "re"
    )


def lint_tree(
    tree: ast.AST, rel: str, hits: list[tuple[str, int]], *, allow_definition: bool
) -> None:
    """Collect re.* call sites whose string constant embeds PATTERN."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in RE_FUNCS:
            continue
        pattern = _pattern_arg(node)
        if pattern is None or PATTERN not in pattern:
            continue
        if allow_definition and _is_definition(node, pattern):
            continue
        hits.append((rel, node.lineno))


def main() -> int:
    """Lint all gates/ files; exit 1 with the red list when hits exist."""
    hits: list[tuple[str, int]] = []
    for py in sorted(GATES.rglob("*.py")):
        rel = str(py.relative_to(REPO))
        tree = ast.parse(py.read_text(encoding="utf-8"))
        lint_tree(tree, rel, hits, allow_definition=py.name == ALLOWED_FILE)
    if hits:
        print(
            f"lint_chapter_num_single_source: {len(hits)} inline "
            f"chapter-(\\d+) site(s) outside {ALLOWED_FILE} definition:"
        )
        for rel, ln in hits:
            print(f"  {rel}:{ln}")
        print("Replace with chapter_no() from shenbi.gates.shared (spec #89 T2).")
        raise SystemExit(1)
    print("OK: gates/ chapter-number regex is single-sourced (spec #89 T2)")
    return 0


if __name__ == "__main__":
    main()
