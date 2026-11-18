"""Spec #93 T5 — resonance_trend.md column contract single source."""

from __future__ import annotations

from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from shenbi.orchestration.escalation_bridge import parse_resonance_scores
from shenbi.pipeline._shared import (
    TREND_COLUMNS,
    TREND_CONFIDENCE_IDX,
    TREND_OVERALL_IDX,
)
from shenbi.pipeline.chapter_loop import build_resonance_trend_row

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_HEADER = REPO_ROOT / "skills" / "shenbi-review-resonance" / "SKILL.md"


def test_columns_match_skill_contract_header() -> None:
    # Cross-source reconciliation: constant <-> skill contract table header
    # (SKILL.md prose contract is the authoritative surface for column names).
    text = SKILL_HEADER.read_text(encoding="utf-8")
    header_line = next(ln for ln in text.splitlines() if ln.startswith("| chapter | chapter_role"))
    names = [c.strip() for c in header_line.strip("|").split("|")]
    assert tuple(names) == TREND_COLUMNS


def test_indices_pin_positions() -> None:
    assert TREND_OVERALL_IDX == 6
    assert TREND_CONFIDENCE_IDX == 7


def test_writer_row_exact_string() -> None:
    assert build_resonance_trend_row(55, 83) == "| 55 | - | - | - | - | - | 83 | - |  |"


@settings(
    max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(chapter=st.integers(1, 9999), overall=st.integers(0, 100))
def test_roundtrip_writer_to_bridge(tmp_path, chapter: int, overall: int) -> None:
    # Round-trip property: writer's row -> bridge parses the overall value
    # out at TREND_OVERALL_IDX (any column drift turns this red).
    trend = tmp_path / "resonance_trend.md"
    trend.write_text(
        "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        + build_resonance_trend_row(chapter, overall)
        + "\n",
        encoding="utf-8",
    )
    assert parse_resonance_scores(trend) == [float(overall)]
