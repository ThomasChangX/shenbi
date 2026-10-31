"""spec #83 T3: transition-word complement dedup + cd.post_transition_cross
+ wordcount precision WARN.

Real declaration forms (anchor replay): ch1:229
`- [ ] 转折词密度: 0 / 3625字 = 0 (≤ 1/3000)`; wordcount ch1:233
wordcount decl label `正文字数` + `总计 N` / `总计 a+b=N` forms (ch1:233, ch28:241).
"""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4.post_declarations import (
    check_post_transition_cross,
    check_post_wordcount_precision,
)
from shenbi.gates.g4.shadow import GATE_TO_SHADOW_KEY
from shenbi.gates.shared import count_transition_words

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec83"


def test_transition_complement_form_dedup() -> None:
    # ch17:79 算不过来的账（补语潜在形非转折）+ ch17:186 忽然说（非计数例）
    assert count_transition_words("算不过来的账，忽然说了一句") == 0
    assert count_transition_words("看不过去的账") == 0
    assert count_transition_words("不过他还是走了") == 1  # 真转折不减


def test_post_transition_cross_real_decl_form() -> None:
    real_decl = "- [ ] 转折词密度: 0 / 3625字 = 0 (≤ 1/3000)"
    # 真实章形态：正文在前、POST 节居末（POST 后的散文会被 strip_narrative_body 归入节内）
    content = f"正文不过如此，他终于明白了。\n\n## POST_WRITE_SELF_CHECK\n{real_decl}\n"
    assert check_post_transition_cross(content) != []
    # 负例：非 0 声明不触发
    ok = "正文。\n\n## POST_WRITE_SELF_CHECK\n- [ ] 转折词密度: 1 / 3187 字 = 1\n"
    assert check_post_transition_cross(ok) == []
    # ch23 变体形 `0（正文零显式转折词）` 兼收（轮 8 M2）
    variant = (
        "正文不过如此。\n\n## POST_WRITE_SELF_CHECK\n- [ ] 转折词密度: 0（正文零显式转折词）\n"
    )
    assert check_post_transition_cross(variant) != []


def test_post_wordcount_precision_warn() -> None:
    decl = "- [ ] 正文字数（逐段计数合计）: 场景1: 8+72=80；总计 80"
    warns = check_post_wordcount_precision(
        f"## POST_WRITE_SELF_CHECK\n{decl}\n", actual_chars=70
    )  # 差 12.5%
    assert warns != []
    assert (
        check_post_wordcount_precision(f"## POST_WRITE_SELF_CHECK\n{decl}\n", actual_chars=79) == []
    )  # 1.2% 带内
    # ch28 真实形：总计 1029+1098+1060=3187（= 后取数）
    decl28 = "- [ ] 正文字数（逐段计数合计）: 场景1: 38+38=76；总计 1029+1098+1060=3187"
    warns28 = check_post_wordcount_precision(
        f"## POST_WRITE_SELF_CHECK\n{decl28}\n", actual_chars=3171
    )  # 0.5% 带内（r5.5 校准锚：ch28 total_chars 实测 3171）
    assert warns28 == []


def test_corpus_calibration_anchor() -> None:
    # 轮 3 M8 校准锚：ch28 0.5% 带内 / ch1 5.5% 真阳 WARN（写手自计偏差——虚假精度本意）
    from shenbi.gates.shared import total_chars_md_text

    ch1 = (FIX / "chapters" / "chapter-1.md").read_text(encoding="utf-8")
    warns1 = check_post_wordcount_precision(ch1, total_chars_md_text(ch1))
    assert any("3625" in w for w in warns1)  # ch1 真阳（5.5%）
    ch28 = (FIX / "chapters" / "chapter-28.md").read_text(encoding="utf-8")
    warns28 = check_post_wordcount_precision(ch28, total_chars_md_text(ch28))
    assert not any("3187" in w for w in warns28)  # ch28 带内
    ch26 = (FIX / "chapters" / "chapter-26.md").read_text(encoding="utf-8")
    assert any(
        "3.5%" in w for w in check_post_wordcount_precision(ch26, total_chars_md_text(ch26))
    )  # ch26 真阳（plan 三例校准锚补钉）


def test_wordcount_tail_note_form_parsed() -> None:
    # audit-T3 I1：尾注形 `总计 3760（≥2800，≤4000）`（ch6/16/17/31/33 形）入检测面
    decl = "- [ ] 正文字数（逐段计数合计）: 场景1: 80；总计 80（≥70，≤90）"
    warns = check_post_wordcount_precision(f"## POST\n{decl}\n", actual_chars=70)
    assert warns != []  # 12.5% 漂移可检（此前该形漏检）


def test_shadow_registration_row2() -> None:
    assert GATE_TO_SHADOW_KEY["cd.post_transition_cross"] == (
        "market_params",
        "post_transition_cross",
    )
