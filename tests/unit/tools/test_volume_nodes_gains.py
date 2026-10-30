"""spec #82 T3 (Task 8): KR gains column + victory budget + vol-2 backfill lint."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.lint_volume_nodes import lint

VM_NO_GAINS = """# 卷纲
## 第一卷：雪与账（第 1-36 章）
| 章节 | 节点角色 | 具体定位 |
|------|------|------|
| 第1章 | 开篇 | 城破 |
| 第2章 | 承接 | 遗物 |
| 第3章 | 承接 | 首账 |
"""

VM_GAINS_OK = """# 卷纲
## 第一卷：雪与账（第 1-36 章）
胜利预算：本卷 4 次实质获得（≥1 大），量级递增
主角自选目标：开春替萤把整张饼吃回来——南下第一站+船票钱 X 文
| 章节 | 节点角色 | 具体定位 | 本章主角获得 |
|------|------|------|------|
| 第1章 | 开篇 | 城破 | 骨哨（关系·小） |
| 第2章 | 承接 | 遗物 | 红纸包（情感·小） |
| 第3章 | 承接 | 首账 | 记账法（信息·中） |
| 第4章 | 转折 | 立账 | 名字（地位·大） |
"""

VM_GAINS_STREAK = (
    VM_GAINS_OK.replace(
        "| 第2章 | 承接 | 遗物 | 红纸包（情感·小） |",
        "| 第2章 | 承接 | 遗物 | （无获得——承接章） |",
    )
    .replace(
        "| 第3章 | 承接 | 首账 | 记账法（信息·中） |",
        "| 第3章 | 承接 | 首账 | （无获得——承接章） |",
    )
    .replace(
        "| 第4章 | 转折 | 立账 | 名字（地位·大） |",
        "| 第4章 | 承接 | 过渡 | （无获得——承接章） |",
    )
)  # ch2-4 三连无获得 > 允许值 2


def _mk(tmp_path: Path, vm: str) -> Path:
    (tmp_path / "outline").mkdir(parents=True)
    (tmp_path / "outline" / "volume_map.md").write_text(vm, encoding="utf-8")
    return tmp_path


@pytest.mark.unit
def test_missing_gains_column_finds_gaps(tmp_path: Path) -> None:
    findings = lint(_mk(tmp_path, VM_NO_GAINS), 1, window=10)
    assert any("获得槽" in f for f in findings)
    assert any("胜利预算" in f for f in findings)


@pytest.mark.unit
def test_gains_ok_no_findings(tmp_path: Path) -> None:
    findings = lint(_mk(tmp_path, VM_GAINS_OK), 1, window=10)
    assert not any("获得槽" in f or "胜利预算" in f or "连续无获得" in f for f in findings)


@pytest.mark.unit
def test_three_consecutive_no_gain_fails(tmp_path: Path) -> None:
    findings = lint(_mk(tmp_path, VM_GAINS_STREAK), 1, window=10)
    assert any("连续无获得" in f for f in findings)
