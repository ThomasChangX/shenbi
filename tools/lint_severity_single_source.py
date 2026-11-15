#!/usr/bin/env python3
r"""Spec #105 T1c: severity-alternation re.* literal single-source lint (AST judge).

Single allowed site: ``src/shenbi/contracts/severity.py``. Any other
``re.*`` call in the scan domains (``src/shenbi/pipeline``,
``src/shenbi/contracts``, ``tools``) whose pattern string carries an
alternation of >= 2 severity vocabulary words turns red.

#88 check_id single-source / #89 chapter-num lint conventions: the
``_pattern_arg`` judge only recognizes ``ast.Constant`` strings (positional
or ``pattern=`` keyword) — composed patterns (``"|".join(...)``) are
invisible by design, which is exactly the sanctioned composition style.

Self-reference note (plan r5-M3): this lint's own detection is a plain
string check against a tuple-joined needle — never a ``re.*`` call carrying
the literal alternation, so the lint cannot flag itself.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCAN_DIRS = (
    REPO / "src" / "shenbi" / "pipeline",
    REPO / "src" / "shenbi" / "contracts",
    REPO / "tools",
)
ALLOWED_FILE = "severity.py"
SEV_WORDS = ("BLOCKING", "CRITICAL", "MINOR", "WARNING", "ERROR")
#: >=2 severity words joined by "|" anywhere in the pattern (the needle is
#: composed, not a literal alternation — self-reference safe; a TUPLE so the
#: membership scan is reusable across calls).
_NEEDLE_PAIRS = tuple("|".join((a, b)) for a in SEV_WORDS for b in SEV_WORDS if a != b)
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


def _is_severity_alternation(pattern: str) -> bool:
    """True when the pattern text contains a |-joined pair of severity words."""
    return any(needle in pattern for needle in _NEEDLE_PAIRS)


def check_tree(tree: ast.Module, rel_name: str) -> list[str]:
    """Return violation strings for one parsed module."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in RE_FUNCS or not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "re":
            continue
        pattern = _pattern_arg(node)
        if pattern is not None and _is_severity_alternation(pattern):
            violations.append(
                f"{rel_name}:{node.lineno}: severity alternation literal {pattern[:60]!r}"
            )
    return violations


def main() -> int:
    """Scan the three domains; exit 1 listing any violation."""
    violations: list[str] = []
    for scan_dir in SCAN_DIRS:
        for py in sorted(scan_dir.rglob("*.py")):
            if py.name == ALLOWED_FILE:
                continue
            rel = py.relative_to(REPO)
            violations.extend(check_tree(ast.parse(py.read_text(encoding="utf-8")), str(rel)))
    if violations:
        print("severity alternation literals outside the single source:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
