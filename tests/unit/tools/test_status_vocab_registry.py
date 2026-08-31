"""spec #34 T1: registry doc parses and every row resolves to a real symbol.

The reconciliation here is the seed of lint_status_strings' registry face
(spec #34 T3) — tools/status_vocab_registry.py is shared.
"""

from __future__ import annotations

from tools.status_vocab_registry import parse_registry, reconcile, resolve_symbol_values


def test_registry_has_full_domain_count() -> None:
    rows = parse_registry()
    # T9 matrix: 36 declared domains + ownerless production domains consolidated.
    # Exact count pins the registry against silent row loss.
    assert len(rows) == 43, f"registry row count changed: {len(rows)}"


def test_every_row_resolves_with_equal_values() -> None:
    problems = reconcile()
    assert problems == [], "\n".join(problems)


def test_known_domains_sample() -> None:
    assert resolve_symbol_values("shenbi.status.GateStatus") == frozenset(
        {"PASS", "FAIL", "SKIP", "WARN", "UNIMPLEMENTED"}
    )
    assert resolve_symbol_values("shenbi.contracts.enums.RevisionMode") == frozenset(
        {"spot-fix", "regenerate", "constrained-regenerate", "reconstruction", "no-revision"}
    )
    assert resolve_symbol_values("shenbi.contracts.ownership.FileChange.status") == frozenset(
        {"added", "deleted", "modified", "unchanged"}
    )
