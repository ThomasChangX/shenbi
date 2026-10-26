"""Unit tests for tools/lint_volume_nodes.py (spec #74 T4).

Structural cases constructed inline (G0.9 exemption: structural inputs,
not impersonations of real skill outputs). Each test's table is exact —
no incidental blanks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.lint_volume_nodes import lint


def _mk(tmp_path: Path, rows: str, end: int = 20) -> Path:
    out = tmp_path / "outline"
    out.mkdir(parents=True, exist_ok=True)
    (out / "volume_map.md").write_text(
        f"---\ntotal_chapters: {end}\n---\n\n## 第一卷：测试（第1—{end}章）\n\n"
        "#### KR1: 测试\n\n- **章节节点**:\n"
        "  | 章节 | 节点角色 | 具体定位 |\n  |------|---------|---------|\n"
        f"{rows}\n\n## 第二卷：后（第{end + 1}—40章）\n",
        encoding="utf-8",
    )
    return tmp_path


def _row(c: int, role: str = "承接", detail: str = "拍") -> str:
    return f"  | 第{c}章 | {role} | {detail} |\n"


# 触点链 2,6,8,10,12,14（间隔≤8）；◆ 双槽在前 5；收官=20（总量对）
_BASE = (
    _row(1, "开篇", "双钩 智力爽◆")
    + _row(2, "回触", "萤回触")
    + _row(3, "承接", "变现◆")
    + _row(4)
    + _row(5)
    + _row(6, "回触", "萤回触 灰烬◆——「下辈子再见」定约")
    + _row(7)
    + _row(8, "回触", "萤回触")
    + _row(9)
    + _row(10, "回触", "萤回触")
    + _row(11)
    + _row(12, "回触", "萤回触")
    + _row(14, "回触", "萤回触")
    + _row(20, "收官", "四轴")
)


@pytest.mark.unit
def test_clean_table_passes(tmp_path: Path) -> None:
    assert lint(_mk(tmp_path, _BASE), 1, 12) == []


@pytest.mark.unit
def test_consecutive_blank_pair_fails(tmp_path: Path) -> None:
    # 第4、5 两章连续空白（_BASE 中 4/5 原有占位——此变体抹掉）
    rows = _BASE.replace(_row(4), "").replace(_row(5), "")
    findings = lint(_mk(tmp_path, rows), 1, 12)
    assert any("density" in f and "第4-5章" in f for f in findings), findings


@pytest.mark.unit
def test_slot_deadline_breach_fails(tmp_path: Path) -> None:
    # 智力爽◆ 后移到第6章（截止第5）；变现◆ 消失
    rows = _BASE.replace(_row(1, "开篇", "双钩 智力爽◆"), _row(1, "开篇", "双钩"))
    rows = rows.replace(_row(3, "承接", "变现◆"), _row(6, "回触", "萤回触 智力爽◆").rstrip("\n"))
    findings = lint(_mk(tmp_path, rows), 1, 12)
    assert any("slot" in f and "智力爽◆" in f and "deadline" in f for f in findings), findings
    assert any("slot" in f and "变现◆" in f and "no rows" in f for f in findings), findings


@pytest.mark.unit
def test_ash_slot_deadline_fails(tmp_path: Path) -> None:
    # spec #79 criterion 3: 灰烬◆ first occurrence must land <= 第12章 (vol-1)
    rows = _BASE.replace(
        _row(6, "回触", "萤回触 灰烬◆——「下辈子再见」定约"),
        _row(14, "回触", "萤回触 灰烬◆——「下辈子再见」定约"),
    )
    findings = lint(_mk(tmp_path, rows), 1, 12)
    assert any("slot" in f and "灰烬◆" in f for f in findings), findings


@pytest.mark.unit
def test_total_mismatch_fails(tmp_path: Path) -> None:
    rows = _BASE.replace(_row(20, "收官", "四轴"), _row(18, "收官", "四轴"))
    findings = lint(_mk(tmp_path, rows), 1, 12)
    assert any("total" in f and "第18章" in f and "第20章" in f for f in findings), findings


@pytest.mark.unit
def test_touch_gap_fails(tmp_path: Path) -> None:
    rows = _BASE.replace(_row(14, "回触", "萤回触"), _row(23 and 14 + 9, "回触", "萤回触"))
    # 直接构造：触点 12 → 22（间隔 10 > 8）
    rows = _BASE.replace(_row(14, "回触", "萤回触"), _row(22, "回触", "萤回触"))
    rows = rows.replace(_row(20, "收官", "四轴"), _row(20, "收官", "四轴"))
    findings = lint(_mk(tmp_path, rows, end=22), 1, 12)
    assert any("touch" in f and "gap" in f for f in findings), findings


@pytest.mark.unit
def test_monotonicity_fails(tmp_path: Path) -> None:
    rows = _BASE + _row(8, "承接", "乱序插行")
    assert any("monotonicity" in f for f in lint(_mk(tmp_path, rows), 1, 12))


@pytest.mark.unit
def test_touch_chain_must_span_volume(tmp_path: Path) -> None:
    """Phase-7 review probe: an early-stopping chain must fail — first touch
    late or last touch far from span end are both coverage violations.
    """
    rows = (
        _row(1, "开篇", "双钩 智力爽◆")
        + _row(2, "承接", "变现◆")
        + _row(3, "承接", "x")
        + _row(4)
        + _row(5)
        + _row(6)
        + _row(7)
        + _row(8)
        + _row(9)
        + _row(10, "回触", "萤回触")
        + _row(11, "回触", "萤回触")
        + _row(20, "收官", "四轴")
    )
    findings = lint(_mk(tmp_path, rows), 1, 12)
    assert any("first touch" in f for f in findings), findings
    assert any("uncovered" in f for f in findings), findings
