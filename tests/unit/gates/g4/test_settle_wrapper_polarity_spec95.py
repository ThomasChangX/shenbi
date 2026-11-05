"""Spec #95 维护批（audit-T10 M1）：组合 finding 极性一致性。

三段式模板（_format_drops）教「被丢行原样重发为基底行」；旧 wrapper
（hooks 面 "never re-emit the hook's stable lines"、matrix 面 "re-emit ONLY
this chapter's increment … do NOT reproduce"）极性相反——sweep 裁定新指令
为正确方（合并基底=staged 副本，丢行不自动恢复），wrapper 措辞收敛。本文件
锁死：组合 finding（三段式 detail + wrapper 后缀）不再携带反极措辞。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4.state_settling import _check_hooks_structure, _check_matrix_structure
from shenbi.pipeline.truth_io import hooks_stable_fields_hint

#: 旧 wrapper 反极措辞——组合 finding 中禁止再出现（audit-T10 M1）。
_BANNED_PHRASES = ("never re-emit", "re-emit ONLY", "do NOT reproduce")


def _stage_pair(tmp_path: Path, rel: str, live: str, staged: str) -> Path:
    project = tmp_path / "proj"
    live_path = project / rel
    live_path.parent.mkdir(parents=True, exist_ok=True)
    live_path.write_text(live, encoding="utf-8")
    staged_path = project / "staging" / rel
    staged_path.parent.mkdir(parents=True, exist_ok=True)
    staged_path.write_text(staged, encoding="utf-8")
    return staged_path


_LIVE_HOOKS = """---
type: truth
---

# 伏笔池

### MH-012 地脉衰竭
- type: GENUINE
- 埋设: 第1卷第10章
- trigger_condition: 塔群熔毁后地脉波形不再恢复
- resolve_condition: 第44章完整真相
- notes: 续接 H-003
"""


@pytest.mark.unit
def test_hooks_composite_finding_polarity(tmp_path: Path) -> None:
    """钩子基底行被丢 → 组合 finding=三段式（基底行重发）+ 对齐 wrapper。"""
    staged = _LIVE_HOOKS.replace("- trigger_condition: 塔群熔毁后地脉波形不再恢复\n", "")
    pf = _stage_pair(tmp_path, "truth/pending_hooks.md", _LIVE_HOOKS, staged)
    issues = _check_hooks_structure(pf)
    composite = "\n".join(issues)
    drop_findings = [i for i in issues if "content_dropped" in i]
    assert drop_findings, issues
    # 三段式核心指令在场（正确方）
    assert "作为基底行" in composite
    assert "原样保留于输出" in composite
    # 反极旧措辞绝迹（M1 收敛面）
    for phrase in _BANNED_PHRASES:
        assert phrase not in composite, phrase
    # 对齐 wrapper 注记合并基底语义 + 稳定字段清单保留
    assert "合并基底=staged 副本" in composite
    assert "不得改写" in composite
    assert hooks_stable_fields_hint() in composite


_LIVE_MATRIX = """---
type: truth
---

# 角色矩阵

## 冷
- 身份: 账房先生
- 当前目标: 查清米缸账目
- 口癖: 打算盘

## 灯
- 身份: 女主角
- 当前目标: 找到星槎台铭文
- 口癖: 念数字
"""


@pytest.mark.unit
def test_matrix_composite_finding_polarity(tmp_path: Path) -> None:
    """矩阵（matrix）面基底行被丢 → 组合 finding=三段式 + 对齐 wrapper（无 increment-only 反极）。"""
    staged = _LIVE_MATRIX.replace("- 当前目标: 查清米缸账目\n", "")
    pf = _stage_pair(tmp_path, "truth/character_matrix.md", _LIVE_MATRIX, staged)
    issues, _warns = _check_matrix_structure(pf)
    composite = "\n".join(issues)
    assert any("content_dropped" in i for i in issues), issues
    assert "作为基底行" in composite
    for phrase in _BANNED_PHRASES:
        assert phrase not in composite, phrase
    assert "合并基底=staged 副本" in composite
