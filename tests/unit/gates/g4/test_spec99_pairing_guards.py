"""Spec #99 pairing guards (Task 4 Step 5): mechanical lock for the ①③④⑤ batch.

Pairing matrix (spec r4.2 T1 item 4 pairing obligation):
- (a) tolerant regex present => quote dual-line example + SKILL iron-law 0
  own-block exclusion clause present
- (b) bundle twin exemption present <=> dual-chapter injection clause present

Assertions probe the REAL implementations (the tolerance check calls the
truth_io helper), so a "half fix" -- regex landed while ①③⑤ missing --
turns this file red.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
SKILL = REPO / "skills" / "shenbi-state-settling" / "SKILL.md"
INJ_SRC = REPO / "src" / "shenbi" / "pipeline" / "dispatch_helper.py"
GATE_SRC = REPO / "src" / "shenbi" / "gates" / "g4" / "state_settling.py"


@pytest.mark.unit
def test_tolerant_regex_implies_quote_example_and_exclusion_clause() -> None:
    """(a) tolerant regex (live helper form) present => quote example + clause."""
    from shenbi.gates.g4.state_settling import _format_drops
    from shenbi.pipeline.truth_io import increment_heading_re

    # ④ 的容错语法以真实现探针验证（数字两侧空格命中）
    assert increment_heading_re(47).match("## 第 47 章状态增量"), "④ 容错正则退化为严格形"

    fb = _format_drops(["| a | 1 |"], samples=1)[0]
    assert "引语行正例" in fb and "自陈补全（第N章原句）" in fb, "③ 报文引语双行正例缺席"

    skill = SKILL.read_text(encoding="utf-8")
    assert "排除条款" in skill and "keyed-upsert 可整体替换单元" in skill, (
        "① 铁律 0 own-block 排除条款缺席（SKILL.md）"
    )
    assert "自陈补全（第N章原句）" in skill, "① SKILL 引语双行正例缺席"


@pytest.mark.unit
def test_bundle_exemption_iff_dual_chapter_injection() -> None:
    """(b) symmetric: gate twin exemption present <=> injection dual-chapter."""
    gate = GATE_SRC.read_text(encoding="utf-8")
    bundle_in_gate = "bundle_chapters" in gate and "_bundle_exempt_chapters" in gate

    inj = INJ_SRC.read_text(encoding="utf-8")
    # 源字符串按行连接拆行——分段断言（渲染后的整句由
    # test_append_dedup_increment_injection 的 user-prompt 断言覆盖）
    dual_in_injection = "block per chapter" in inj and "twin N+1" in inj

    assert bundle_in_gate == dual_in_injection, (
        "④ 孪生豁免与⑤ 双章口径必须同批在场/同批缺席——单边即配对破裂："
        f"gate={bundle_in_gate}, injection={dual_in_injection}"
    )
    assert bundle_in_gate, "配对两成员当前均缺席（④⑤ 未落地）"
