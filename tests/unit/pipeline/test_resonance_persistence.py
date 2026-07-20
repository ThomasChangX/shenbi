"""Tests for resonance score persistence to resonance_trend.md.

Verifies the persisted row matches the format parse_resonance_scores
(src/shenbi/orchestration/escalation_bridge.py:15-17) consumes:
lines starting with "|", split on "|", requires >=7 cells, reads cells[6]
(7th column) as the overall score.
"""

import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import _build_resonance_trend_row


def test_trend_row_has_seven_columns_with_overall_in_column_7():
    """Row has >=7 | cells; overall score in cells[6] (7th column)."""
    row = _build_resonance_trend_row(chapter=5, overall=70)
    # Must start with | so parse_resonance_scores picks it up
    assert row.startswith("|")
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    assert len(cells) >= 7, f"Expected >=7 cells, got {len(cells)}: {row}"
    # cells[0] is the chapter key (Ch5), cells[6] is overall (column 7)
    assert cells[0] == "Ch5"
    assert cells[6] == "70"


def test_trend_row_key_column_is_chapter_number():
    """Key column (cells[0]) is Ch{N} for key-based dedup."""
    row = _build_resonance_trend_row(chapter=12, overall=55)
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    assert cells[0] == "Ch12"


def test_trend_row_has_placeholder_columns_for_missing_dims():
    """Columns without available data use '-' placeholders (not omitted)."""
    row = _build_resonance_trend_row(chapter=3, overall=42)
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    # Columns 1-5 (indices) are placeholders; overall is at index 6
    for idx in range(1, 6):
        assert cells[idx] == "-", f"cell {idx} should be '-' placeholder, got {cells[idx]}"
    assert cells[6] == "42"


def test_persist_via_write_truth_file_round_trips_through_reader():
    """Writing the row then parsing it yields the overall score back.

    Simulates what parse_resonance_scores (escalation_bridge.py:15-17) does:
    scan lines starting with '|', split on '|', require >=7 cells, read cells[6].
    """
    from shenbi.pipeline.truth_io import write_truth_file

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "truth").mkdir()

        write_truth_file(
            project_dir,
            "resonance_trend.md",
            _build_resonance_trend_row(chapter=7, overall=88),
            mode="upsert_markdown_row",
            key_field="chapter",
        )

        text = (project_dir / "truth" / "resonance_trend.md").read_text()
        scores = []
        for line in text.splitlines():
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 7:
                    try:
                        scores.append(float(cells[6]))
                    except ValueError:
                        pass
        assert scores == [88.0]


def test_re_persist_same_chapter_replaces_row_in_place():
    """Key-based dedup: re-persisting the same chapter replaces, not duplicates."""
    from shenbi.pipeline.truth_io import write_truth_file

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "truth").mkdir()

        write_truth_file(
            project_dir,
            "resonance_trend.md",
            _build_resonance_trend_row(chapter=9, overall=60),
            mode="upsert_markdown_row",
            key_field="chapter",
        )
        write_truth_file(
            project_dir,
            "resonance_trend.md",
            _build_resonance_trend_row(chapter=9, overall=65),
            mode="upsert_markdown_row",
            key_field="chapter",
        )

        text = (project_dir / "truth" / "resonance_trend.md").read_text()
        assert text.count("| Ch9") == 1
        assert "65" in text
