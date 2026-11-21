"""Spec #119 T1: pure-chapter whitelist predicate, single source (chapter-NN digits-exact)."""

import pytest

from shenbi.gates.shared import is_pure_chapter


@pytest.mark.parametrize(
    ("stem", "want"),
    [
        ("chapter-1", True),
        ("chapter-50", True),
        ("chapter-030", True),  # 零填充同纯形（B5 跨书注记——命名碰撞面由管道控制）
        ("chapter-1-pre-rev", False),  # 管道修订备份=历史层，白名单外
        ("chapter-1-duplicated", False),
        ("chapter-1-decisions", False),
        ("chapter", False),
        ("chapter-", False),
        ("prologue", False),
    ],
)
def test_is_pure_chapter_whitelist_form(stem: str, want: bool) -> None:
    assert is_pure_chapter(stem) is want
