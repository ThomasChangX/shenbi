"""Spec #100 Task 2: scene-split band feedback carries the POST self-check
contradiction clause (only when declared in band AND actual < floor).

Five cases pin F1's both halves plus the zero-new-issue-line minimality and
the empty-declaration guard (C1: a short chapter without a declaration line
must not crash validate_split).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4.post_declarations import check_post_wordcount_precision
from shenbi.gates.shared import total_chars_md_text
from shenbi.pipeline.scene_splitter import SplitChapter, split_bundle

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "spec100"
BAND = (2800, 4000)


def _bundle_chapters() -> dict[int, SplitChapter]:
    """首派 bundle（00248）解包件——ch47 声明 3210/实测 2288、ch48 3250/1646。"""
    text = (FIX / "ch47-48-first-pass-bundle.md").read_text(encoding="utf-8")
    return {ch.number: ch for ch in split_bundle(text).chapters}


def _word_band_issue(issues: list[str]) -> str | None:
    return next((i for i in issues if i.startswith("word_band:")), None)


def _inline_chapter(number: int, body_lines: list[str], scenes: int = 3) -> SplitChapter:
    """构造性输入（G0.9 允许）：无 SCENE 标记，按字数均分造 SceneSpan——
    仅用于负例判定（不作为场景域/合规断言的依据）。
    """
    from shenbi.pipeline.scene_splitter import SceneSpan

    body = "\n".join(body_lines)
    size = max(1, total_chars_md_text(body) // scenes)
    spans = tuple(SceneSpan(index=i, size=size, last_line="尾句。") for i in range(scenes))
    return SplitChapter(number=number, title="", body=body, scenes=spans)


@pytest.mark.unit
def test_false_in_band_claim_appends_clause_and_keeps_issue_ids() -> None:
    """① ch47 首派：声明 3210（在带）实测 2288<2800 → word_band 行尾追加反驳句；
    且 issue 前缀集合与无声明时一致（零新 id/零新行——I8）。
    """
    from shenbi.pipeline.scene_splitter import validate_split

    ch = _bundle_chapters()[47]
    issues = validate_split(ch, BAND)
    wb = _word_band_issue(issues)
    assert wb is not None
    assert "POST自检申报 3210" in wb
    assert "实测 2288" in wb and "2800" in wb
    assert "补足缺口" in wb and "改声明一行" not in wb
    # 零新 issue 行/id：全部行都以既有前缀开头
    prefixes = {i.split(":", 1)[0] for i in issues}
    assert prefixes <= {"word_band", "scene_count", "scene_domain", "composition", "chapter_band"}
    # M6: 只有一条 word_band 行（子句不得新开行）
    assert len([i for i in issues if i.startswith("word_band:")]) == 1


@pytest.mark.unit
def test_in_band_actual_no_clause() -> None:
    """② final ch48（声明 3006/实测 3093，均在带）→ 无 word_band、无子句；
    checker 层 WARN 仍产出（gate 接线由既有 test_spec83 覆盖）。
    """
    from shenbi.pipeline.scene_splitter import validate_split

    body = (FIX / "chapter-48-final.md").read_text(encoding="utf-8")
    ch = _inline_chapter(48, [body])
    issues = validate_split(ch, BAND)
    assert _word_band_issue(issues) is None
    assert not any("POST自检申报" in i for i in issues)
    # checker 行为（2.9% > 2% → WARN 串仍在，只是不进 issues）
    assert check_post_wordcount_precision(body, total_chars_md_text(body))


@pytest.mark.unit
def test_over_band_actual_no_clause() -> None:
    """③ over-band false claim 不在本批域（r4 收窄）：actual 4100 → 无子句。"""
    from shenbi.pipeline.scene_splitter import validate_split

    filler = "这是一段用于字数构造的叙述文字。" * 258
    filler = filler[:4100]
    body = (
        "<!--META-BEGIN-->\n## POST_WRITE_SELF_CHECK\n\n"
        "- [x] 正文字数（逐段计数合计）: 总计 3200（2800–4000 带内）\n"
        "<!--META-END-->\n" + filler
    )
    ch = _inline_chapter(48, [body])
    assert total_chars_md_text(ch.body) == 4100  # M12: 构造有效性（精确值）
    issues = validate_split(ch, BAND)
    assert _word_band_issue(issues) is not None
    assert not any("POST自检申报" in i for i in issues)


@pytest.mark.unit
def test_declared_out_of_band_no_clause() -> None:
    """④ F1 第二半唯一判别：actual 短但 declared 本就出带（ch44 首派形 2373/1788）
    → 无子句（模型没虚报，只是写短了）。
    """
    from shenbi.pipeline.scene_splitter import validate_split

    filler = "叙述。" * 400
    body = (
        "<!--META-BEGIN-->\n## POST_WRITE_SELF_CHECK\n\n"
        "- [x] 正文字数（逐段计数合计）: 总计 2373（2800–4000 带内）\n"
        "<!--META-END-->\n" + filler
    )
    ch = _inline_chapter(48, [body])
    wb = _word_band_issue(validate_split(ch, BAND))
    assert wb is not None
    assert "POST自检申报" not in wb


@pytest.mark.unit
def test_missing_declaration_no_crash() -> None:
    """⑤ C1 空守卫：短章无声明行（既有 test_length_feedback_scenes 形状）→
    word_band 正常产出、无子句、不抛 IndexError。
    """
    from shenbi.pipeline.scene_splitter import validate_split

    ch = _inline_chapter(48, ["## POST_WRITE_SELF_CHECK\n\n- y\n" + "短。" * 100])
    issues = validate_split(ch, BAND)  # 不得抛异常
    wb = _word_band_issue(issues)
    assert wb is not None and "POST自检申报" not in wb
