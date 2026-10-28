"""spec #80 T10: invariant census document shape guard.

docs/framework/invariants.md is the 13-dim x four-slot census table. The
shape contract (spec #2, rev3 R2-M3 / rev4 R3-M9 / R3-I1):

- exactly 13 dimension rows; columns = # + 7 named slots (维度/载体/声明/门检/审计/期相/mutant 义务)
- 期相 column P1|P2|P3; a P1 row must have all four slots (载体/声明/门检/审计)
  non-empty — CURRENT_PHASE starts at P1, so P1 rows with holes are lint-red
  (tools/lint_invariant_coverage.py is the runtime face, T12)
- mutant obligation only on F15+-family / facts-backed dims (exactly the
  P1 facts trio); XC-gated dims document coverage via red-test notes instead

This test is the doc-side half; T12's lint reuses the same parse.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DOC = Path("docs/framework/invariants.md")
COLUMNS = ("维度", "载体", "声明", "门检", "审计", "期相", "mutant 义务")
FOUR_SLOTS = ("载体", "声明", "门检", "审计")
HOLE_TOKENS = {"", "—", "—（", "TBD", "TODO"}


def _parse_census() -> tuple[list[str], list[dict[str, str]]]:
    text = DOC.read_text("utf-8")
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue  # separator row
        if header is None:
            header = cells
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    assert header is not None, "census table header not found"
    return header, rows


@pytest.mark.unit
def test_census_doc_exists_with_exact_header() -> None:
    assert DOC.exists(), "docs/framework/invariants.md missing"
    header, _rows = _parse_census()
    assert header[:2] == ["#", "维度"]
    for col in COLUMNS[1:]:
        assert col in header, f"column {col!r} missing: {header}"


@pytest.mark.unit
def test_census_has_thirteen_dimension_rows() -> None:
    _header, rows = _parse_census()
    assert len(rows) == 13, f"expected 13 dims, got {len(rows)}"


@pytest.mark.unit
def test_phase_column_wellformed() -> None:
    _header, rows = _parse_census()
    for row in rows:
        assert row["期相"] in {"P1", "P2", "P3"}, f"bad 期相 in {row['维度']}: {row['期相']!r}"


@pytest.mark.unit
def test_p1_rows_have_all_four_slots_filled() -> None:
    _header, rows = _parse_census()
    for row in rows:
        if row["期相"] != "P1":
            continue
        for slot in FOUR_SLOTS:
            v = row[slot]
            assert v and v not in HOLE_TOKENS and not v.startswith("—"), (
                f"P1 dim {row['维度']} slot {slot} is a documented hole: {v!r}"
            )


@pytest.mark.unit
def test_mutant_obligation_only_f15_family_dims() -> None:
    """R3-I1 predicate: obligation hangs only on F15+-family / facts-backed
    dims — the P1 facts trio plus 能力活性 (F18 introduces its check id at P2).
    XC-gated dims document red-test coverage instead (their mutants are P2
    synthetic deliveries, not census obligations).
    """
    _header, rows = _parse_census()
    obligated = {row["维度"] for row in rows if row["mutant 义务"].startswith("Yes")}
    assert obligated == {
        "恒等 identity",
        "持有与经手 props",
        "枚举计数 counters",
        "能力活性",
    }, obligated


@pytest.mark.unit
def test_literal_sets_are_referenced_not_defined() -> None:
    """R3-I3: the census must point at status-vocab for literal value sets.
    Full-set restatements (audit-T10 I-1) drift silently when a StrEnum gains
    a member — lint_status_strings only reconciles StrEnum↔status-vocab.
    """
    text = DOC.read_text("utf-8")
    assert "status-vocab.md" in text
    # ... and must NOT restate any complete op value set (pipe or slash form)
    for pattern in (
        r"transfer\s*[|｜/]\s*acquire",
        r"rename\s*[|｜/]\s*set_alias",
        r"increment\s*[|｜/]\s*set\b",
    ):
        assert not re.search(pattern, text), pattern
