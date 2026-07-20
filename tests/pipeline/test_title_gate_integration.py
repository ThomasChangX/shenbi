"""Test title gate integration into chapter loop post-drafting checks."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from shenbi.pipeline.chapter_loop import (
    _extract_chapter_title,
    _load_previous_titles,
    _run_g4_checks,
)


class TestExtractChapterTitle:
    """Tests for _extract_chapter_title helper."""

    def test_extracts_h1_title(self):
        """Title is extracted from first H1 heading."""
        with tempfile.TemporaryDirectory() as tmp:
            chapter_path = Path(tmp) / "chapter-1.md"
            chapter_path.write_text("# 废料场\n\nContent here.", encoding="utf-8")
            assert _extract_chapter_title(chapter_path) == "废料场"

    def test_extracts_title_with_chapter_prefix(self):
        """Title with chapter number prefix is extracted as-is."""
        with tempfile.TemporaryDirectory() as tmp:
            chapter_path = Path(tmp) / "chapter-1.md"
            chapter_path.write_text("# 第1章 废料场\n\nContent here.", encoding="utf-8")
            assert _extract_chapter_title(chapter_path) == "第1章 废料场"

    def test_returns_empty_for_no_h1(self):
        """Empty string when no H1 heading exists."""
        with tempfile.TemporaryDirectory() as tmp:
            chapter_path = Path(tmp) / "chapter-1.md"
            chapter_path.write_text("Just content, no heading.", encoding="utf-8")
            assert _extract_chapter_title(chapter_path) == ""

    def test_returns_empty_for_missing_file(self):
        """_extract_chapter_title raises FileNotFoundError if file missing.

        This is expected behavior — the caller must guard with .exists()
        before calling. No need to handle this inside the function.
        """
        import pytest

        with pytest.raises(FileNotFoundError):
            _extract_chapter_title(Path("/nonexistent/chapter-1.md"))


class TestLoadPreviousTitles:
    """Tests for _load_previous_titles helper."""

    def test_returns_empty_for_first_chapter(self):
        """Chapter 1 has no previous titles."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            chapters_dir = project_dir / "chapters"
            chapters_dir.mkdir()
            result = _load_previous_titles(project_dir, 1)
            assert result == {}

    def test_loads_previous_chapter_titles(self):
        """Loads titles from chapters before current."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            chapters_dir = project_dir / "chapters"
            chapters_dir.mkdir()
            (chapters_dir / "chapter-1.md").write_text("# 废料场\nContent", encoding="utf-8")
            (chapters_dir / "chapter-2.md").write_text("# 觉醒\nContent", encoding="utf-8")
            (chapters_dir / "chapter-3.md").write_text("# 试炼\nContent", encoding="utf-8")
            # Current is chapter 4, should see 1,2,3
            result = _load_previous_titles(project_dir, 4)
            assert result == {"废料场": 1, "觉醒": 2, "试炼": 3}

    def test_excludes_current_and_future_chapters(self):
        """Titles from current chapter and beyond are excluded."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            chapters_dir = project_dir / "chapters"
            chapters_dir.mkdir()
            (chapters_dir / "chapter-1.md").write_text("# 废料场\nContent", encoding="utf-8")
            (chapters_dir / "chapter-2.md").write_text("# 觉醒\nContent", encoding="utf-8")
            (chapters_dir / "chapter-3.md").write_text("# 试炼\nContent", encoding="utf-8")
            # Current is chapter 2, should only see chapter 1
            result = _load_previous_titles(project_dir, 2)
            assert result == {"废料场": 1}

    def test_handles_missing_chapters_dir(self):
        """Returns empty dict when chapters directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            result = _load_previous_titles(project_dir, 1)
            assert result == {}


class TestRunG4ChecksIntegration:
    """Tests for _run_g4_checks post-drafting gate function."""

    def test_returns_issues_list(self):
        """_run_g4_checks returns a list of issue strings."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            chapters_dir = project_dir / "chapters"
            chapters_dir.mkdir()
            plans_dir = project_dir / "plans"
            plans_dir.mkdir()
            (chapters_dir / "chapter-1.md").write_text("# 废料场\nContent", encoding="utf-8")
            (plans_dir / "chapter-1-plan.md").write_text("# Plan", encoding="utf-8")

            state = MagicMock()
            state.project_dir = str(project_dir)

            issues = _run_g4_checks(state, 1)
            assert isinstance(issues, list)

    def test_empty_for_missing_chapter(self):
        """Returns empty list when chapter file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            state = MagicMock()
            state.project_dir = str(project_dir)

            issues = _run_g4_checks(state, 1)
            assert issues == []

    def test_detects_chapter_number_in_title(self):
        """Title containing '第N章' is flagged as HARD fail."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            chapters_dir = project_dir / "chapters"
            chapters_dir.mkdir()
            plans_dir = project_dir / "plans"
            plans_dir.mkdir()
            (chapters_dir / "chapter-1.md").write_text(
                "# 第1章 废料场\n\nContent here.", encoding="utf-8"
            )
            (plans_dir / "chapter-1-plan.md").write_text("# Plan", encoding="utf-8")

            state = MagicMock()
            state.project_dir = str(project_dir)

            issues = _run_g4_checks(state, 1)
            assert any("contains_chapter_number" in i for i in issues), (
                f"Expected chapter number issue, got: {issues}"
            )

    def test_detects_duplicate_title(self):
        """Title already used in a previous chapter is flagged."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            chapters_dir = project_dir / "chapters"
            chapters_dir.mkdir()
            plans_dir = project_dir / "plans"
            plans_dir.mkdir()
            (chapters_dir / "chapter-1.md").write_text("# 废料场\nContent", encoding="utf-8")
            (chapters_dir / "chapter-2.md").write_text("# 废料场\nContent", encoding="utf-8")
            (plans_dir / "chapter-2-plan.md").write_text("# Plan", encoding="utf-8")

            state = MagicMock()
            state.project_dir = str(project_dir)

            issues = _run_g4_checks(state, 2)
            assert any("duplicate_of_ch1" in i for i in issues), (
                f"Expected duplicate title issue, got: {issues}"
            )

    def test_detects_day_label_in_title(self):
        """Title that is a day-of-week label is flagged as WARN."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            chapters_dir = project_dir / "chapters"
            chapters_dir.mkdir()
            plans_dir = project_dir / "plans"
            plans_dir.mkdir()
            (chapters_dir / "chapter-1.md").write_text("# Saturday\n\nContent.", encoding="utf-8")
            (plans_dir / "chapter-1-plan.md").write_text("# Plan", encoding="utf-8")

            state = MagicMock()
            state.project_dir = str(project_dir)

            issues = _run_g4_checks(state, 1)
            assert any("day_label" in i for i in issues), f"Expected day label issue, got: {issues}"

    def test_good_title_passes(self):
        """A thematic 1-4 character Chinese title produces no issues."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            chapters_dir = project_dir / "chapters"
            chapters_dir.mkdir()
            plans_dir = project_dir / "plans"
            plans_dir.mkdir()
            (chapters_dir / "chapter-1.md").write_text("# 废料场\n\nContent.", encoding="utf-8")
            (plans_dir / "chapter-1-plan.md").write_text("# Plan", encoding="utf-8")

            state = MagicMock()
            state.project_dir = str(project_dir)

            issues = _run_g4_checks(state, 1)
            assert len(issues) == 0, f"Expected no issues for good title, got: {issues}"

    def test_short_chinese_title_still_valid(self):
        """Single-character Chinese titles should be valid (1-20 char range)."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            chapters_dir = project_dir / "chapters"
            chapters_dir.mkdir()
            plans_dir = project_dir / "plans"
            plans_dir.mkdir()
            (chapters_dir / "chapter-1.md").write_text("# 沉\n\nContent.", encoding="utf-8")
            (plans_dir / "chapter-1-plan.md").write_text("# Plan", encoding="utf-8")

            state = MagicMock()
            state.project_dir = str(project_dir)

            title = _extract_chapter_title(chapters_dir / "chapter-1.md")
            assert 1 <= len(title) <= 20
