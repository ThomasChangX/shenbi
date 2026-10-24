"""spec #71 T1: prose primitives single-source in gates/shared.py."""

from __future__ import annotations

import pytest

from shenbi.gates.shared import QUOTE_PAIR, count_similes, segment_sentences

pytestmark = pytest.mark.unit


def test_segment_sentences_migration_anchor() -> None:
    """迁移行为锚：与 compute_stats 时代逐字一致（含 F668 引号内不切/F628 ；切分）。

    char_count 含句末标点（非空白字符数口径）：「然后走了。」= 5。
    """
    text = "他说「今天不错。真的。」然后走了。\n新起一行。"
    sents = segment_sentences(text)
    # 引号内句号不切分 → 「今天不错。真的。」整体一句（12 非空白含引号）
    # + "然后走了。"（5，含句号）+ "新起一行。"（5，含句号）
    assert [c for _, c in sents] == [12, 5, 5]


def test_segment_sentences_reexport_from_compute_stats() -> None:
    """re-export 兼容：既有外部 import 方（test_compute_stats.py）不破。"""
    from shenbi.skill_utils.style_learning import compute_stats

    assert compute_stats.segment_sentences is segment_sentences
    assert compute_stats.QUOTE_PAIR is QUOTE_PAIR


def test_count_similes_basic_and_domain() -> None:
    """计数于非对白域 + strip_narrative_body 域：对白内喻词不计、PRE 自检行不喂饱。"""
    prose = (
        "剑光像一匹扯开的白绢。\n\n「你别管，这事就像天塌了。」他说。\n\n远处的山宛如一头伏兽。\n"
    )
    result = count_similes(prose)
    # 对白句（引号内）的「像」不计：只计 剑光像 + 宛如 = 2
    assert result["count"] == 2
    # non_dialogue_chars = 剥引号后非空白（含 H1/标点）——「你别管，这事就像天塌了。」整句剥除
    assert result["non_dialogue_chars"] > 0
    assert result["per_1000"] == round(2 * 1000 / result["non_dialogue_chars"], 1)


def test_count_similes_strips_post_checklist() -> None:
    """R3-C1 回归锚：裸 H2 POST 摘录行（喻词密度最高文本）不得进分子。"""
    content = (
        "## POST_WRITE_SELF_CHECK\n\n"
        "- [ ] 金句位: 他像一棵被雷劈过的树站在那里。\n\n"
        "# 第1章 题目\n\n他像一棵被雷劈过的树站在那里。\n"
    )
    result = count_similes(content)
    # POST 节剥除 → 只数正文 1 处「像」（若不剥 = 2）
    assert result["count"] == 1


def test_count_similes_empty_and_boundaries() -> None:
    assert count_similes("")["count"] == 0
    assert count_similes("")["per_1000"] == 0.0
    # 全对白文本：非对白域 0 字 → per_1000 = 0.0（防除零）
    assert count_similes("「像不像？」")["per_1000"] == 0.0
