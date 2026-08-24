"""Spec #9 R4 (F115): per-dim-row applicability tables must not be a no-op.

Rubrics using the header `| # | Dimension | <Type> Standard | ...` were
silently unfiltered by load_applicability (it only recognized
`| Dimension scope |`), so e.g. worldbuilding bug-hunt kept the N/A-exempt
Prose-quality dimension.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from shenbi.scoring import (
    Dimension,
    filter_dimensions_by_test_type,
    load_applicability,
)

REPO = Path(__file__).resolve().parents[2]
WORLDBUILDING = REPO / "tests/tiers/t1-skill/shenbi-worldbuilding/rubric.md"


def _write_rubric(tmp_path: Path, applicability: str) -> str:
    body = f"# r\n\n## Dimensions\n\n{applicability}\n"
    p = tmp_path / "rubric.md"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return str(p)


PER_DIM_TABLE = """## Dimension Applicability

| # | Dimension | Bug-hunt Standard | Clean Standard |
|---|---|---|---|
| 1 | World depth | standard | standard |
| 4 | Prose quality | N/A — exempted | standard |
"""

LEGACY_TABLE = """## Dimension Applicability

| Dimension scope | bug-hunt | clean | generative |
|---|---|---|---|
| dim 2 | No | Yes | Yes |
"""

BOTH_TABLES = LEGACY_TABLE + "\n" + PER_DIM_TABLE


class TestPerDimRowApplicability:
    @pytest.mark.unit
    def test_real_worldbuilding_bug_hunt_excludes_dim4(self) -> None:
        dims = [
            Dimension(num=1, name="A", weight=20),
            Dimension(num=4, name="B", weight=20),
        ]
        out = filter_dimensions_by_test_type(dims, str(WORLDBUILDING), "bug-hunt")
        assert [d["num"] for d in out] == [1]

    @pytest.mark.unit
    def test_synthetic_per_dim_header_parsed(self, tmp_path: Path) -> None:
        app = load_applicability(_write_rubric(tmp_path, PER_DIM_TABLE))
        assert app["bug-hunt"]["dim 4"] is False
        assert app["bug-hunt"]["dim 1"] is True
        assert app["clean"]["dim 4"] is True

    @pytest.mark.unit
    def test_no_applicability_section_exempt(self, tmp_path: Path) -> None:
        app = load_applicability(_write_rubric(tmp_path, "| # | Dimension |\n|---|---|\n| 1 | A |"))
        assert app == {}

    @pytest.mark.unit
    def test_legacy_dimension_scope_still_parsed(self, tmp_path: Path) -> None:
        app = load_applicability(_write_rubric(tmp_path, LEGACY_TABLE))
        assert app["bug-hunt"]["dim 2"] is False

    @pytest.mark.unit
    def test_legacy_then_per_dim_both_parsed(self, tmp_path: Path) -> None:
        app = load_applicability(_write_rubric(tmp_path, BOTH_TABLES))
        assert app["bug-hunt"]["dim 2"] is False  # legacy table
        assert app["bug-hunt"]["dim 4"] is False  # per-dim table
