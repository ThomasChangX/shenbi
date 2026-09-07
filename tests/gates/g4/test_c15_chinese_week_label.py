"""Chinese week-label regex branch coverage (F736, spec #53 C15).

The existing English-branch test ("第四周Saturday", test_title_check.py) never
reaches the 周[一二三四五六日] alternation; these tests drive it with real
Chinese weekday samples.
"""

from __future__ import annotations

import pytest

from shenbi.gates.g4.chapter_drafting import check_chapter_title


@pytest.mark.parametrize("weekday", list("一二三四五六日"))
def test_warns_each_chinese_weekday(weekday: str) -> None:
    issues = check_chapter_title(f"第2周周{weekday}", {})
    assert any("day_label_instead_of_thematic_name" in i for i in issues)


def test_warns_standalone_chinese_week_label() -> None:
    issues = check_chapter_title("第四周周三", {})
    assert any("day_label_instead_of_thematic_name" in i for i in issues)


def test_thematic_title_without_week_label_passes() -> None:
    issues = check_chapter_title("灰烬之城", {})
    assert issues == []
