"""C30 R4 F1112: a step with a missing declared output is downgraded (not
recorded as done) with a WARN.
"""

from pathlib import Path

from shenbi.pipeline.chapter_loop import ChapterStep, _step_output_exists


def test_output_exists_true_for_real_file(tmp_path: Path) -> None:
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-1.md").write_text("x", encoding="utf-8")
    step = ChapterStep(
        4, "shenbi-chapter-drafting", "drafting", output_path="chapters/chapter-N.md"
    )
    assert _step_output_exists(tmp_path, step, 1) is True


def test_output_missing_false(tmp_path: Path) -> None:
    step = ChapterStep(
        4, "shenbi-chapter-drafting", "drafting", output_path="chapters/chapter-N.md"
    )
    assert _step_output_exists(tmp_path, step, 1) is False


def test_no_output_path_not_guarded(tmp_path: Path) -> None:
    step = ChapterStep(9, "shenbi-review-group-factual", "audit", is_audit=True)
    assert _step_output_exists(tmp_path, step, 1) is True


def test_staging_step_checked_in_staging(tmp_path: Path) -> None:
    step = ChapterStep(
        2,
        "shenbi-chapter-planning",
        "planning",
        uses_staging=True,
        output_path="plans/chapter-N-plan.md",
    )
    committed = tmp_path / "plans" / "chapter-1-plan.md"
    committed.parent.mkdir(parents=True)
    committed.write_text("committed only", encoding="utf-8")
    assert (
        _step_output_exists(tmp_path, step, 1) is False
    )  # committed copy is not the staged product
    staged = tmp_path / "staging" / "plans" / "chapter-1-plan.md"
    staged.parent.mkdir(parents=True)
    staged.write_text("staged", encoding="utf-8")
    assert _step_output_exists(tmp_path, step, 1) is True
