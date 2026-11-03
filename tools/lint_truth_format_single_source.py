#!/usr/bin/env python3
r"""AST lint: truth-file format regexes stay single-sourced (spec #85).

Scans ``src/shenbi`` + ``tools`` for hook/thread dialect regex literals at
THREE scan positions (spec acceptance 3, r9/r11 caliber):

1. ``re`` call-site arguments (compile/match/search/findall/finditer/
   fullmatch/sub/subn/split);
2. module-level ``_*RE = re.compile(...)`` assignment values;
3. module-level bare string constants whose VALUE carries a dialect form
   (the ``_THREAD_ID_TOKEN`` recurrence vector).

Exemptions (AST-shape based, NO line anchors):
- ``src/shenbi/truth_format.py`` (the single source itself);
- composite points whose f-string/JoinedStr references
  ``hook_family_source(...)`` or ``THREAD_ID_RE.pattern``/``HOOK_*.pattern``
  AND whose constant segments carry no dialect literal;
- named whitelist: ``review_checklist.py``'s dead ``hook_pattern`` (removed
  with #86 T2 — the whitelist entry dies with it);
- BinOp concatenation and ``str.format()``/``%`` built patterns
  (residual risk ③, registered — zero instances on the current tree);
- generic-charclass blind spot (residual risk ①, registered): patterns like
  ``[A-Z]{2,4}-\\d+`` do not match the dialect detector.

Non-regex positions (error copy / prompt examples / docstrings / word-list
data / enums) never hit: only the three scan positions above are visited.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOTS = [REPO_ROOT / "src" / "shenbi", REPO_ROOT / "tools"]
SINGLE_SOURCE = "truth_format.py"

#: Dialect detector forms (spec acceptance 3). Hook families + thread
#: charset forms; value-level matching (so a bare constant with a dialect
#: value is caught even without a re.compile wrapper).
#: Value-level detectors (match the regex SOURCE text as stored in the
#: string value, e.g. ``MH\\d+`` / ``CP-?\\d`` / ``P\\d*-`` / ``[HM]\\d``).
#: Both spellings are dialect evidence: the optional-hyphen pattern form
#: (``MH-?\\d``) and the canonical source-string literal form where ``?``
#: is a literal VALUE character (``MH-?\\d{1,4}`` — audit-T9 C1: verbatim
#: copies of truth_format's family source are the top recurrence vector).
#: P quantifier variants covered (M5).
_HOOK_DIALECT = re.compile(r"MH-?\??\\d|CP-?\??\\d|H-?\??\\d|P\\d[+*]?[\{]?[0-9,]*\}?-|\[HM\]\\d")
_THREAD_DIALECT = re.compile(r"\[ABC\]\\d|\[A-Za-z\]\+\\d|\[a-zA-Z\]\+\\d")

#: Named whitelist (spec r8 timing clause): dead code scheduled for removal.
NAMED_WHITELIST: dict[str, str] = {
    # dead code; the entry dies with the #86 T2 removal
    "src/shenbi/pipeline/review_checklist.py": "hook_pattern",
}

_RE_CALL_FUNCS = {
    "compile",
    "match",
    "search",
    "findall",
    "finditer",
    "fullmatch",
    "sub",
    "subn",
    "split",
}

#: Composite-point exemption markers (AST Name / attribute references).
_EXEMPT_REFERENCES = {"hook_family_source", "THREAD_ID_RE", "HOOK_ID_RE", "HOOK_HEADING_RE"}


def _dialect_hits(value: str) -> list[str]:
    hits: list[str] = []
    if _HOOK_DIALECT.search(value):
        hits.append("hook")
    if _THREAD_DIALECT.search(value):
        hits.append("thread")
    return hits


def _string_of(node: ast.expr) -> str | None:
    """Constant string value (None for non-plain strings)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _joined_parts(node: ast.expr) -> tuple[list[str], list[ast.expr]] | None:
    """Constant segments + interpolation exprs of an f-string (or plain str)."""
    if isinstance(node, ast.JoinedStr):
        consts: list[str] = []
        exprs: list[ast.expr] = []
        for part in node.values:
            if isinstance(part, ast.Constant):
                consts.append(str(part.value))
            elif isinstance(part, ast.FormattedValue):
                exprs.append(part.value)
        return consts, exprs
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value], []
    return None


def _references_exempt(expr: ast.expr) -> bool:
    """True when the expression references a truth_format single-source name."""
    for n in ast.walk(expr):
        if isinstance(n, ast.Name) and n.id in _EXEMPT_REFERENCES:
            return True
        if (
            isinstance(n, ast.Attribute)
            and n.attr == "pattern"
            and isinstance(n.value, ast.Name)
            and n.value.id in _EXEMPT_REFERENCES
        ):
            return True  # single-source .pattern derivation (spec-caliber names)
        if isinstance(n, ast.Call):
            for sub in ast.walk(n.func):
                if isinstance(sub, ast.Name) and sub.id in _EXEMPT_REFERENCES:
                    return True
    return False


def _check_re_call(node: ast.Call, rel: str, findings: list[str]) -> None:
    """Scan position 1: re.<func>(PATTERN, ...) call-site arguments."""
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr in _RE_CALL_FUNCS):
        return
    if isinstance(func.value, ast.Name) and func.value.id == "re" and node.args:
        parts = _joined_parts(node.args[0])
        if parts is None:
            return
        consts, exprs = parts
        if exprs and all(_references_exempt(e) for e in exprs):
            if not any(_dialect_hits(c) for c in consts):
                return  # composite exemption: derived source + clean constants
        joined = "".join(consts)
        for fam in _dialect_hits(joined):
            findings.append(
                f"{rel}:{node.lineno}: re.{func.attr} carries {fam}-family dialect literal"
            )


def _check_module_assign(stmt: ast.Assign, rel: str, findings: list[str]) -> None:
    """Scan positions 2+3: module-level ``X = re.compile(...)`` / bare strings."""
    if not isinstance(stmt.value, (ast.Call, ast.Constant, ast.JoinedStr)):
        return
    value = stmt.value
    # re.compile assignment
    if isinstance(value, ast.Call):
        func = value.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "compile"
            and isinstance(func.value, ast.Name)
            and func.value.id == "re"
            and value.args
        ):
            return
        parts = _joined_parts(value.args[0])
        if parts is None:
            return
        consts, exprs = parts
        if exprs and all(_references_exempt(e) for e in exprs):
            if not any(_dialect_hits(c) for c in consts):
                return
        joined = "".join(consts)
        names = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
        is_private_re = any(n.endswith(("RE", "_RE")) for n in names)
        for fam in _dialect_hits(joined):
            kind = "regex assignment" if is_private_re else "regex assignment (non-RE name)"
            findings.append(
                f"{rel}:{stmt.lineno}: module-level {kind} carries {fam}-family dialect"
            )
        return
    # bare string constant (position 3)
    if isinstance(value, (ast.Constant, ast.JoinedStr)):
        parts = _joined_parts(value)
        if parts is None:
            return
        consts, exprs = parts
        if exprs and all(_references_exempt(e) for e in exprs):
            if not any(_dialect_hits(c) for c in consts):
                return
        joined = "".join(consts)
        for fam in _dialect_hits(joined):
            findings.append(
                f"{rel}:{stmt.lineno}: bare constant carries {fam}-family dialect"
                " (token recurrence vector)"
            )


def lint_tree(rel: str, tree: ast.Module, findings: list[str]) -> None:
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            _check_module_assign(stmt, rel, findings)
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            _check_module_assign(ast.Assign(targets=[stmt.target], value=stmt.value), rel, findings)
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            _check_re_call(stmt.value, rel, findings)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            _check_re_call(node, rel, findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="exit code only")
    args = parser.parse_args(argv)

    findings: list[str] = []
    for root in SCAN_ROOTS:
        for py in sorted(root.rglob("*.py")):
            rel = str(py.relative_to(REPO_ROOT))
            if py.name == SINGLE_SOURCE:
                continue
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            except SyntaxError as exc:  # pragma: no cover - defensive
                findings.append(f"{rel}: unparseable ({exc})")
                continue
            if rel in NAMED_WHITELIST:
                # Mechanical staleness check (lint_dead_code_allowlist
                # precedent): the exempted name must still exist in the
                # file, else the entry outlived its removal promise.
                names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
                attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
                if NAMED_WHITELIST[rel] not in names | attrs:
                    findings.append(
                        f"{rel}: stale whitelist entry {NAMED_WHITELIST[rel]!r}"
                        " (name gone — remove the entry; spec #85 r8)"
                    )
                continue
            lint_tree(rel, tree, findings)

    # Deduplicate (re-call scan may double-visit module-level Expr calls)
    def _dedupe_key(f: str) -> tuple[str, str]:
        head = f.split(" ", 1)[0]
        fam = "hook" if "hook-family" in f else "thread" if "thread-family" in f else f
        return head, fam

    findings = sorted(set(findings))
    seen: set[tuple[str, str]] = set()
    deduped: list[str] = []
    for f in findings:
        k = _dedupe_key(f)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(f)
    findings = deduped
    if findings and not args.quiet:
        for f in findings:
            print(f, file=sys.stderr)
        print(f"[truth-format-single-source] {len(findings)} violation(s)", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
