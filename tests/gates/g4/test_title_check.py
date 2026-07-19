"""Test G4.cd.title chapter title quality enforcement."""

from shenbi.gates.g4.chapter_drafting import check_chapter_title


class TestChapterTitleValidation:
    def test_rejects_chapter_number_in_title(self):
        issues = check_chapter_title("第40章 废料场", {})
        assert any("contains_chapter_number" in i for i in issues)

    def test_rejects_duplicate_title(self):
        previous = {"废料场": 3, "痕迹": 5}
        issues = check_chapter_title("痕迹", previous)
        assert any("duplicate_of_ch5" in i for i in issues)

    def test_warns_day_of_week_label(self):
        issues = check_chapter_title("Saturday", {})
        assert any("day_label_instead_of_thematic_name" in i for i in issues)

    def test_warns_chinese_week_label(self):
        issues = check_chapter_title("第四周Saturday", {})
        assert any("day_label_instead_of_thematic_name" in i for i in issues)

    def test_passes_poetic_single_character(self):
        issues = check_chapter_title("沉", {})
        assert len(issues) == 0

    def test_passes_poetic_two_character(self):
        issues = check_chapter_title("废料场", {"晨": 1})
        assert len(issues) == 0

    def test_handles_empty_previous_titles(self):
        issues = check_chapter_title("雾", {})
        assert len(issues) == 0
