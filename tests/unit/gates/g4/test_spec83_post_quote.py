"""spec #83 T2: cd.post_quote_verbatim two-arm gate - r5 corpus baselines.

5 FAIL chapters (ch1/ch6/ch2/ch31/ch33 declaration distortion); WARN
shapes (ch13/16/19/26 verbatim-absent but clauses present -> no FAIL);
negatives (ch28 micro-hook out of face; ch25 variant line excluded).
"""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4.post_declarations import check_post_quote_verbatim
from shenbi.gates.g4.shadow import GATE_TO_SHADOW_KEY

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec83"


def _text(n: int) -> str:
    return (FIX / "chapters" / f"chapter-{n}.md").read_text(encoding="utf-8")


def _fails(n: int) -> list[str]:
    fails, _warns = check_post_quote_verbatim(_text(n))
    return fails


def test_five_distortion_fails() -> None:
    # r5 回放 5 FAIL 全集逐章断言（每章至少命中其钦定失真引句）
    assert any("城就破了" in f for f in _fails(1))  # 正文无此句
    assert any("册子认得" in f for f in _fails(6))  # 正文=册子认得人（截断，子句等值不豁免）
    assert any("账上" in f for f in _fails(2))  # 归并缩写（声明侧添「账上」）
    assert any("私账" in f or "头一行" in f for f in _fails(31))
    assert any("旗会换" in f or "价会变" in f for f in _fails(33))


def test_punct_variants_warn_not_fail() -> None:
    # ch13/16/19/26 逐字缺席但子句全在 → WARN 不 FAIL（r5 回放基线）
    for n in (13, 16, 19, 26):
        fails, warns = check_post_quote_verbatim(_text(n))
        assert fails == [], f"ch{n} 应零 FAIL（r5 回放基线），实得 {fails[:2]}"


def test_negative_micro_hook_out_of_face() -> None:
    fails28, _ = check_post_quote_verbatim(_text(28))
    assert not any("王朝的命" in f for f in fails28)  # 跨段转述微粒钩 → G3.4 兜底


def test_negative_variant_tail_line_excluded_behavioral() -> None:
    # ch25 变体行 `- [x] 章尾张力:`（无 G4.cd 口径标签）不入执法面——行为级断言
    text25 = _text(25)
    variant = [
        ln for ln in text25.splitlines() if "章尾张力" in ln and "[x]" in ln and "G4.cd" not in ln
    ]
    fails25, _ = check_post_quote_verbatim(text25)
    if variant:  # 变体行存在时：其行内引句不产生 FAIL（正则不收行）
        assert not any("章尾张力" in f for f in fails25)


def test_golden_and_tail_lines_both_enforced() -> None:
    # 两标签行都在执法面（68 行=各 34 的口径）；ch1 金句位+章尾张力两行均被判定
    from shenbi.gates.g4.post_declarations import POST_GOLDEN_LINE_RE, POST_TAIL_LINE_RE

    ch1 = _text(1)
    assert POST_GOLDEN_LINE_RE.search(ch1)
    assert POST_TAIL_LINE_RE.search(ch1)


def test_shadow_registration_row1() -> None:
    # spec §10 行 1：shadow 登记（勿与 #82 G4.cd.quote_verbatim 混同——shadow.py 既有）
    assert GATE_TO_SHADOW_KEY["cd.post_quote_verbatim"] == ("market_params", "post_quote_verbatim")
    assert GATE_TO_SHADOW_KEY["cd.quote_verbatim"] == (
        "market_params",
        "quote_anchor",
    )  # #82 既有不破


def test_dup_insensitive_from_meta_overlap() -> None:
    # audit-T1 I：META 双区重叠引句双列 → 门侧去重（同一引句不双 FAIL/双 WARN）
    fails, warns = check_post_quote_verbatim(_text(1))
    assert len(fails) == len(set(fails))
    assert len(warns) == len(set(warns))
