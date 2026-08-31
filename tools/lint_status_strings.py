#!/usr/bin/env python3
"""Lint: status-vocabulary single-source enforcement (spec #34 T3, inverted).

Three faces, all anchored to the repo root via ``__file__`` (T905 CWD blind
spot fixed):

1. **src strict face** — in ``src/shenbi/**/*.py`` (status.py/enums.py
   exempt), any *bare string constant* on the result-envelope keys
   ``s/status/state/classification`` is a violation. Only enum-member
   expressions are legal (the whitelist inversion: previously the lint only
   caught in-vocabulary literals, so out-of-vocab values escaped by
   construction — F447).
2. **tests out-of-vocab face** — in ``tests/**/*.py`` (fixtures/ and
   coverage/ excluded), bare literals on the same keys are violations only
   when the value is not in the union of all registered vocabularies (test
   assertions legitimately compare against plain strings).
3. **registry reconciliation face** — every row of
   ``docs/framework/status-vocab.md`` must resolve to a real symbol with an
   exactly equal value set (``tools/status_vocab_registry.reconcile``).
   Unresolvable/drifted rows and code-defined status domains missing from
   the registry are both violations (T901 registration gate).

Additionally ``--scan-tree DIR`` adds face 4: recursively read ``*.json``
under DIR. ``severity``/``mode`` values are checked strictly against the
union of all registered vocabularies (after the consumer-side legacy alias
maps). ``status``/``state``/``classification`` are free-text in several
production doc families (chapter decisions p0/p1 prose fields), so the tree
face flags them only on case-insensitive near-misses of registered values or
known legacy forms (e.g. ``DONE``/``Completed``) — full per-file-family
schemas are out of spec #34 scope. ``--scan-tree novel-output`` is AC1's
entry point.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shenbi.contracts.enums import REVISION_MODE_ALIASES
from tools.status_vocab_registry import parse_registry, reconcile

REPO_ROOT = Path(__file__).resolve().parents[1]
EXEMPT_NAMES = {"status.py", "enums.py"}
STATUS_KEYS = frozenset({"status", "state", "classification", "s"})
# Keys whose JSON values are checked by the tree-scan face.
TREE_KEYS = frozenset({"status", "state", "classification", "severity", "mode"})
STRICT_TREE_KEYS = frozenset({"severity", "mode"})
# Consumer-side legacy aliases (registry 消费侧容错映射 summary).
_LEGACY_ALIASES: dict[str, str] = {
    **REVISION_MODE_ALIASES,
    "blocking": "high",
    "critical": "high",
    "critical_per_audit": "high",
    "warning": "medium",
    "minor": "low",
    "info": "low",
    "none": "low",
    "observation": "low",
    "DONE": "done",
    "completed": "complete",
}


def _registry_union() -> frozenset[str]:
    return frozenset().union(*(row.values for row in parse_registry()))


def _bare_constants(node: ast.AST) -> list[ast.Constant]:
    """Bare string constants in an expression, except lookup keys in calls.

    ``{"status": rec.get("status")}`` — the constant inside ``.get(...)`` is a
    lookup key, not an emit. Enum members are attribute refs, never constants.
    """
    out: list[ast.Constant] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            if not sub.value:
                continue  # empty string is not a status
            out.append(sub)
    # drop constants that appear as an argument of any Call whose value equals
    # a STATUS_KEY (lookup-key pattern); walk-level detection
    lookup_ids: set[int] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            for arg in sub.args:
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and arg.value in STATUS_KEYS
                ):
                    lookup_ids.add(id(arg))
    return [c for c in out if id(c) not in lookup_ids]


class _Visitor(ast.NodeVisitor):
    def __init__(
        self,
        filename: str,
        strict: bool,
        vocab_union: frozenset[str],
        lines: list[str] | None = None,
    ) -> None:
        self.filename = filename
        self.strict = strict
        self.vocab_union = vocab_union
        self.lines = lines or []
        self.violations: list[str] = []

    def _check_value(self, key: str, value: ast.AST, lineno: int, line_text: str = "") -> None:
        if "vocab-ok:" in line_text:
            return  # explicit inline exemption (negative tests), reason required
        for lit in _bare_constants(value):
            if not self.strict and (lit.value in self.vocab_union or lit.value in _LEGACY_ALIASES):
                continue
            self.violations.append(
                f"{self.filename}:{lit.lineno or lineno}: bare status string "
                f"{lit.value!r} on key {key!r} (use a registered enum member)"
            )

    def visit_Dict(self, node: ast.Dict) -> None:
        line_text = self.lines[lit_line] if (lit_line := node.lineno - 1) < len(self.lines) else ""
        for k, v in zip(node.keys, node.values, strict=False):
            if isinstance(k, ast.Constant) and k.value in STATUS_KEYS:
                self._check_value(k.value, v, node.lineno, line_text)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for tgt in node.targets:
            if (
                isinstance(tgt, ast.Subscript)
                and isinstance(tgt.slice, ast.Constant)
                and tgt.slice.value in STATUS_KEYS
            ):
                self._check_value(tgt.slice.value, node.value, node.lineno)
        self.generic_visit(node)


def scan_face(violations: list[str], strict: bool, vocab_union: frozenset[str]) -> None:
    """Run the AST face over src/shenbi (strict) or tests (out-of-vocab)."""
    base = "src/shenbi" if strict else "tests"
    for py in sorted((REPO_ROOT / base).rglob("*.py")):
        rel = f"{base}/{py.relative_to(REPO_ROOT / base)}"
        if py.name in EXEMPT_NAMES:
            continue
        if not strict and ("fixtures/" in rel or "coverage/" in rel):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        src_lines = py.read_text(encoding="utf-8").splitlines()
        v = _Visitor(rel, strict, vocab_union, src_lines)
        v.visit(tree)
        violations.extend(v.violations)


def _iter_json_docs(text: str) -> list[object]:
    docs: list[object] = []
    dec = json.JSONDecoder()
    idx = 0
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        try:
            obj, end = dec.raw_decode(text, idx)
        except json.JSONDecodeError:
            return docs
        docs.append(obj)
        idx = end
    return docs


def _walk_json_values(node: object, out: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and k in TREE_KEYS:
                out.append((k, v))
            else:
                _walk_json_values(v, out)
    elif isinstance(node, list):
        for item in node:
            _walk_json_values(item, out)


def tree_face(violations: list[str], tree: Path, vocab_union: frozenset[str]) -> None:
    """Run the JSON value face over every *.json under *tree*."""
    for fp in sorted(tree.rglob("*.json")):
        try:
            text = fp.read_text(encoding="utf-8")
        except OSError:
            continue
        pairs: list[tuple[str, str]] = []
        docs = _iter_json_docs(text)
        if docs:
            for doc in docs:
                _walk_json_values(doc, pairs)
        else:
            for m in re.finditer(
                r'"(status|state|classification|severity|mode|decision)":\s*"([^"]+)"', text
            ):
                pairs.append((m.group(1), m.group(2)))
        lowered = {v.casefold() for v in vocab_union}
        for key, value in pairs:
            norm = _LEGACY_ALIASES.get(value, value)
            if value in vocab_union or norm in vocab_union:
                continue
            if key in STRICT_TREE_KEYS:
                violations.append(
                    f"{fp}: out-of-vocab {key}={value!r} (not in any registered domain)"
                )
            elif value in _LEGACY_ALIASES or value.casefold() in lowered:
                violations.append(
                    f"{fp}: case/legacy drift {key}={value!r} (canonical form required)"
                )


_DOMAIN_SUFFIX_RE = r"(Status|State|Mode|Verdict|Severity|Decision|Zone|Role)$"


def _unregistered_code_domains(violations: list[str]) -> None:
    """T901 registration gate: every status-like domain in code is registered.

    A domain is "status-like" when its name matches the status vocabulary
    naming families (Status/State/Mode/Verdict/Severity/Decision/Zone/Role).
    Definitions live in Literal assignments or StrEnum classes.
    """
    registered = {row.symbol for row in parse_registry()}
    for py in sorted((REPO_ROOT / "src" / "shenbi").rglob("*.py")):
        rel = f"src/shenbi/{py.relative_to(REPO_ROOT / 'src' / 'shenbi')}"
        if "tests" in rel:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        module = "shenbi." + ".".join(
            py.relative_to(REPO_ROOT / "src" / "shenbi").with_suffix("").parts
        )
        for node in ast.walk(tree):
            name: str | None = None
            if isinstance(node, ast.ClassDef) and any(
                getattr(b, "id", "").endswith("Enum") for b in node.bases
            ):
                name = node.name
            elif isinstance(node, ast.Assign) and len(node.targets) == 1:
                t = node.targets[0]
                if (
                    isinstance(t, ast.Name)
                    and isinstance(node.value, ast.Call)
                    and getattr(node.value.func, "id", "") == "Literal"
                ):
                    name = t.id
            _is_domain = name is not None and re.search(_DOMAIN_SUFFIX_RE, name)
            if _is_domain and f"{module}.{name}" not in registered:
                violations.append(
                    f"{rel}: status-like domain {name} not registered in status-vocab.md (T901)"
                )


def main(argv: Iterable[str] | None = None) -> int:
    """Print every violation; exit 1 if any face found one."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan-tree", type=Path, default=None, help="JSON value face root")
    ns = parser.parse_args(list(argv) if argv is not None else None)

    vocab_union = _registry_union()
    violations: list[str] = []
    scan_face(violations, strict=True, vocab_union=vocab_union)
    scan_face(violations, strict=False, vocab_union=vocab_union)
    violations.extend(reconcile())
    _unregistered_code_domains(violations)
    if ns.scan_tree is not None:
        tree_face(violations, ns.scan_tree, vocab_union)
    for v in violations:
        print(v)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
