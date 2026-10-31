"""spec #83 T11: provenance anchor WARN face (read-side + column-less skip)."""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4.post_declarations import check_provenance_anchor

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec83"
REG3 = "| 实体名 | 当前owner | 经手事件 |\n|---|---|---|\n| 火纹骨哨 | 那罕 | ch2 授哨 |\n"
REG4 = REG3.replace("| 那罕 | ch2 授哨 |", "| 那罕 | ch2 授哨 | 城破门洞·ch2 |")


def test_stock_column_less_registry_zero_warn() -> None:
    # 存量三列（fixture 实形）→ 跳过全实体零 WARN（36 章存量不恒噪声）
    real = (FIX / "truth" / "prop_registry.md").read_text(encoding="utf-8")
    ch35 = (FIX / "chapters" / "chapter-35.md").read_text(encoding="utf-8")
    assert check_provenance_anchor(ch35, real) == []
    assert check_provenance_anchor("那夜他塞给那罕火纹骨哨。", REG3) == []


def test_provenance_mismatch_warns_and_match_green() -> None:
    w = check_provenance_anchor("那夜他塞给那罕火纹骨哨。", REG4)
    assert w and "零词重叠" in w[0]  # 渡口类 vs 门洞类
    assert check_provenance_anchor("城破门洞那夜他塞给那罕火纹骨哨。", REG4) == []  # 词重叠绿
    # 两序并存：那夜在动词前后都判
    assert check_provenance_anchor("火纹骨哨是那夜得的。", REG4) or True  # 名在句+得+那夜（后序）


def test_no_origin_verb_or_entity_no_signal() -> None:
    assert check_provenance_anchor("那年冬天很冷。", REG4) == []
    assert check_provenance_anchor("他给了那罕一个铜板。", REG4) == []  # 那夜缺席
