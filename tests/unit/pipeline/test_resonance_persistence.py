"""Tests for resonance score persistence to resonance_trend.md.

Verifies the persisted row matches the format parse_resonance_scores
(src/shenbi/orchestration/escalation_bridge.py:15-17) consumes:
lines starting with "|", split on "|", requires >=7 cells, reads cells[6]
(7th column) as the overall score.

SDD #21 R1: the framework placeholder row is 9-column with a bare ``{N}``
key matching the shenbi-review-resonance skill contract, and is persisted
with mode="insert_markdown_row" so a skill-written rich row for the same
chapter is never replaced.
"""

import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import _build_resonance_trend_row

SKILL_RICH_ROW_55 = "| 55 | 推进/转折 | 18 | 12 | 23 | 17 | 70 | mid |  |"


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def test_trend_row_has_nine_columns_with_overall_in_column_7():
    """Row has exactly 9 cells; overall score in cells[6] (7th column)."""
    row = _build_resonance_trend_row(chapter=5, overall=70)
    assert row.startswith("|")
    cells = _cells(row)
    assert len(cells) == 9, f"Expected 9 cells, got {len(cells)}: {row}"
    # cells[0] is the bare chapter key ({N}, skill-contract format)
    assert cells[0] == "5"
    assert cells[6] == "70"


def test_trend_row_key_column_is_bare_chapter_number():
    """Key column (cells[0]) is {N} — matches the skill contract key."""
    row = _build_resonance_trend_row(chapter=12, overall=55)
    assert _cells(row)[0] == "12"


def test_trend_row_has_placeholder_columns_for_missing_dims():
    """Columns without available data use '-' placeholders (not omitted)."""
    row = _build_resonance_trend_row(chapter=3, overall=42)
    cells = _cells(row)
    for idx in range(1, 6):
        assert cells[idx] == "-", f"cell {idx} should be '-' placeholder, got {cells[idx]}"
    assert cells[6] == "42"
    assert cells[7] == "-"  # confidence placeholder
    assert cells[8] == ""  # human_overridden blank


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
            mode="insert_markdown_row",
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
                        continue
        assert scores == [88.0]


def test_insert_mode_does_not_replace_existing_row():
    """insert_markdown_row: a second insert of the same key is skipped."""
    from shenbi.pipeline.truth_io import write_truth_file

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "truth").mkdir()

        write_truth_file(
            project_dir,
            "resonance_trend.md",
            _build_resonance_trend_row(chapter=9, overall=60),
            mode="insert_markdown_row",
            key_field="chapter",
        )
        write_truth_file(
            project_dir,
            "resonance_trend.md",
            _build_resonance_trend_row(chapter=9, overall=65),
            mode="insert_markdown_row",
            key_field="chapter",
        )

        text = (project_dir / "truth" / "resonance_trend.md").read_text()
        assert text.count("| 9 ") == 1
        assert "65" not in text  # second placeholder insert skipped, first kept


def test_framework_placeholder_never_clobbers_skill_rich_row():
    """SDD #21 R1 core acceptance: skill writes its rich row, framework's
    placeholder insert afterwards leaves the rich row untouched — one row,
    dimension scores/role/confidence preserved.
    """
    from shenbi.pipeline.truth_io import write_truth_file

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "truth").mkdir()

        # skill writer (via dispatch append_dedup route) writes the rich row
        write_truth_file(
            project_dir,
            "resonance_trend.md",
            SKILL_RICH_ROW_55,
            mode="upsert_markdown_row",
            key_field="chapter",
        )
        # framework writer then inserts its placeholder for the same chapter
        write_truth_file(
            project_dir,
            "resonance_trend.md",
            _build_resonance_trend_row(chapter=55, overall=70),
            mode="insert_markdown_row",
            key_field="chapter",
        )

        text = (project_dir / "truth" / "resonance_trend.md").read_text()
        data_rows = [ln for ln in text.splitlines() if ln.startswith("| 55")]
        assert len(data_rows) == 1, f"expected exactly one row for ch55, got {data_rows}"
        assert "推进/转折" in data_rows[0]
        assert "mid" in data_rows[0]
