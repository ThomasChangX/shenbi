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
import re
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


#: plan 判据: 全串提取的交替词数 >= 2 (audit-T1c M-1: 相邻对包含判定漏判
#: 非相邻交替如 (?:BLOCKING|FAIL|CRITICAL) — 按段计数实现).
_MIN_ALT_WORDS = 2


def _is_severity_alternation(pattern: str) -> bool:
    """True when >= 2 distinct severity words appear across |-split segments."""
    seen = {
        m.group(0)
        for seg in pattern.split("|")
        for m in re.finditer(r"[A-Z]+", seg)
        if m.group(0) in SEV_WORDS
    }
    return len(seen) >= _MIN_ALT_WORDS


def _re_aliases(tree: ast.Module) -> tuple[set[str], set[str]]:
    """Names bound to the ``re`` module / its functions (audit-S8 I-2).

    Returns (module_aliases, function_aliases): ``import re as _re`` puts
    ``_re`` in the first set (attribute calls); ``from re import compile as
    _c`` puts ``_c`` in the second (direct Name calls).
    """
    module_aliases: set[str] = {"re"}
    function_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "re" and alias.asname:
                    module_aliases.add(alias.asname)
        elif isinstance(node, ast.ImportFrom) and node.module == "re":
            for alias in node.names:
                if alias.name in RE_FUNCS:
                    function_aliases.add(alias.asname or alias.name)
    return module_aliases, function_aliases


def check_tree(tree: ast.Module, rel_name: str) -> list[str]:
    """Return violation strings for one parsed module."""
    violations: list[str] = []
    module_aliases, function_aliases = _re_aliases(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        is_re_call = False
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            is_re_call = node.func.attr in RE_FUNCS and node.func.value.id in module_aliases
        elif isinstance(node.func, ast.Name):
            # ``from re import compile as _c`` — direct Name call.
            is_re_call = node.func.id in function_aliases
        if not is_re_call:
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
