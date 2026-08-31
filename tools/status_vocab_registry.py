"""Registry parse + symbol resolution for docs/framework/status-vocab.md.

Shared by tests/unit/tools/test_status_vocab_registry.py (spec #34 T1) and
tools/lint_status_strings.py's reconciliation face (spec #34 T3). The registry
is the single adjudication source for every status vocabulary domain — see
the doc's header for the format contract.
"""

from __future__ import annotations

import ast
import enum as _enum
import importlib
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "docs" / "framework" / "status-vocab.md"
N_COLUMNS = 5
MIN_PARTS = 3  # shenbi.<module>.<Symbol> at minimum


@dataclass(frozen=True)
class DomainRow:
    """One registry row: domain name, qualified symbol, declared values."""

    domain: str
    symbol: str  # e.g. shenbi.status.GateStatus / ...ownership.FileChange.status
    values: frozenset[str]


def parse_registry(path: Path = REGISTRY_PATH) -> list[DomainRow]:
    r"""Parse the 域清单 table rows (fixed 5-column, values '\|'-separated)."""
    rows: list[DomainRow] = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_table = line.startswith("## 域清单")
            continue
        if not in_table or not line.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if cells[0] == "域" or set(cells[0]) <= {"-", ":"}:
            continue  # header / separator
        if len(cells) != N_COLUMNS:
            msg = f"registry malformed row ({len(cells)} columns): {line[:80]}"
            raise ValueError(msg)
        domain, symbol, values, _writers, _readers = cells
        rows.append(
            DomainRow(
                domain=domain,
                symbol=symbol,
                values=frozenset(v for v in values.split("\\|") if v),
            )
        )
    return rows


def _enum_or_literal_values(obj: object) -> frozenset[str] | None:
    """Value set of a resolved object: Enum members or typing.Literal args."""
    if isinstance(obj, type) and issubclass(obj, _enum.Enum):
        return frozenset(str(m.value) for m in obj)
    args = getattr(obj, "__args__", None)
    if args:
        return frozenset(str(a) for a in args if isinstance(a, str))
    return None


def _resolve_via_import(parts: list[str]) -> frozenset[str] | None:
    """Resolve ``shenbi.<...>.<attr path>`` by progressive module import."""
    for split in range(len(parts) - 1, 1, -1):
        try:
            mod = importlib.import_module(".".join(parts[:split]))
        except ModuleNotFoundError:
            continue
        obj: object = mod
        for a in parts[split:]:
            obj = getattr(obj, a, None)
            if obj is None:
                break
        else:
            return _enum_or_literal_values(obj)
    return None


def _literal_values_from_subscript(node: ast.Subscript) -> frozenset[str] | None:
    vals = {sub.value for sub in ast.walk(node.slice) if isinstance(sub, ast.Constant)}
    return frozenset(str(v) for v in vals if isinstance(v, str)) or None


def _resolve_via_ast(parts: list[str]) -> frozenset[str] | None:
    """Resolve ``shenbi.<module...>.<Class>.<attr>`` field-annotation form.

    Handles dataclass fields (``status: Literal[...]``) that are not
    importable as module attributes.
    """
    field_parts = parts[1:]
    for depth in range(len(field_parts) - 2, 0, -1):
        src = REPO_ROOT / "src" / "shenbi" / Path(*field_parts[:depth]).with_suffix(".py")
        if not src.exists():
            continue
        try:
            tree = ast.parse(src.read_text(encoding="utf-8"))
        except SyntaxError:
            return None
        class_name, attr = field_parts[depth], field_parts[depth + 1]
        for node in ast.walk(tree):
            if not (isinstance(node, ast.ClassDef) and node.name == class_name):
                continue
            for stmt in node.body:
                if (
                    isinstance(stmt, ast.AnnAssign)
                    and getattr(stmt.target, "id", "") == attr
                    and isinstance(stmt.annotation, ast.Subscript)
                    and getattr(stmt.annotation.value, "id", "") == "Literal"
                ):
                    return _literal_values_from_subscript(stmt.annotation)
    return None


def resolve_symbol_values(symbol: str) -> frozenset[str] | None:
    """Resolve a registry symbol to its actual value set.

    Supported forms:
    - ``shenbi.<module...>.<Class>`` — StrEnum/Enum members, or a module-level
      ``Name = Literal[...]`` assignment
    - ``shenbi.<module...>.<Class>.<attr>`` — a dataclass/pydantic field
      annotated ``attr: Literal[...]``

    Returns None when the symbol cannot be located (reconciliation reports it).
    """
    parts = symbol.split(".")
    if parts[0] != "shenbi" or len(parts) < MIN_PARTS:
        return None
    return _resolve_via_import(parts) or _resolve_via_ast(parts)


def reconcile() -> list[str]:
    """Bidirectional reconcile: registry rows resolvable + value sets equal."""
    problems: list[str] = []
    for row in parse_registry():
        actual = resolve_symbol_values(row.symbol)
        if actual is None:
            problems.append(f"registry symbol unresolvable: {row.domain} -> {row.symbol}")
        elif actual != row.values:
            missing = sorted(row.values - actual)
            extra = sorted(actual - row.values)
            problems.append(f"registry value drift: {row.domain} missing={missing} extra={extra}")
    return problems
