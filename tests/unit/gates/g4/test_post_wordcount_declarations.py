"""Spec #100 Task 1: single-source POST wordcount declaration parser.

Pins the helper contract shared by check_post_wordcount_precision (G4 WARN)
and the scene-split band feedback (rewind clause): all declared totals in
document order, zero values filtered, sum-form supported.
"""

from __future__ import annotations

import pytest

from shenbi.gates.g4.post_declarations import (
    check_post_wordcount_precision,
    parse_post_wordcount_declarations,
)


def _post(line: str) -> str:
    return f"<!--META-BEGIN-->\n## POST_WRITE_SELF_CHECK\n\n{line}\n<!--META-END-->\n"


@pytest.mark.unit
def test_two_declarations_in_document_order() -> None:
    content = _post(
        "- [x] 正文字数（逐段计数合计）: 场景1 1200；场景2 1158；总计 2358（2800–4000 带内）"
    ) + _post("- [x] 正文字数（逐段计数合计）: 场景1 1500；场景2 1600；总计 3100（2800–4000 带内）")
    assert parse_post_wordcount_declarations(content) == [2358, 3100]


@pytest.mark.unit
def test_sum_form_yields_total_not_first_addend() -> None:
    content = _post("- [x] 正文字数（逐段计数合计）: 场景1+场景2+场景3；总计 1029+1098+1060=3187")
    assert parse_post_wordcount_declarations(content) == [3187]


@pytest.mark.unit
def test_no_declaration_yields_empty_list() -> None:
    content = _post("- y")
    assert parse_post_wordcount_declarations(content) == []


@pytest.mark.unit
def test_zero_declaration_filtered() -> None:
    content = _post("- [x] 正文字数（逐段计数合计）: 总计 0")
    assert parse_post_wordcount_declarations(content) == []


@pytest.mark.unit
def test_precision_check_behavior_unchanged_per_declaration() -> None:
    """Refactor pin: every declaration still yields its own issue (not last-wins)."""
    content = _post("- [x] 正文字数（逐段计数合计）: 总计 3358（2800–4000 带内）") + _post(
        "- [x] 正文字数（逐段计数合计）: 总计 3100（2800–4000 带内）"
    )
    issues = check_post_wordcount_precision(content, 3511)
    assert len(issues) == 2
    assert all(i.startswith("cd.post_wordcount_precision:") for i in issues)
