"""Tests for g4_pacing_design (rewritten: structured Pydantic validation)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.pacing_design import g4_pacing_design


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"
    sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True)
    marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


@pytest.mark.unit
def test_fails_when_rhythm_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir()
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "FAIL"


@pytest.mark.unit
def test_fails_when_beats_missing(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "# Rhythm\nno beat data here\n", encoding="utf-8"
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "FAIL"


@pytest.mark.unit
def test_fails_without_three_lines(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "铺垫 25% 升级 25% 爆发 25% 余波 25%\nQUEST FIRE\n",
        encoding="utf-8",
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "FAIL"
    assert any(
        "CONSTELLATION" in mf or "narrative lines" in mf for mf in result.get("must_fix", [])
    )


@pytest.mark.unit
def test_fails_when_beat_sum_wrong(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "铺垫 20% 升级 20% 爆发 20% 余波 20%\nQUEST 40% FIRE 35% CONSTELLATION 25%\n",
        encoding="utf-8",
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "FAIL"


@pytest.mark.unit
def test_passes_with_complete_rhythm(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        "铺垫 25% 升级 30% 爆发 25% 余波 20%\n"
        "QUEST 40% FIRE 35% CONSTELLATION 25%\n"
        "战斗 对话 日常 探索 修炼 阴谋 逃亡 揭示\n",
        encoding="utf-8",
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "PASS"


# ---------------------------------------------------------------------------
# Canonical EXACT-template table parsing (canary escalation #2, 2026-09-28):
# the tight-only regex could not read the SKILL.md template's own table
# shapes, so a letter-perfect template output failed G4.
# ---------------------------------------------------------------------------

_CANONICAL_RHYTHM = """# 节奏原则

## 四拍循环

| 拍 | 目标占比 | 允许范围 | 超范围后果 |
|----|---------|---------|----------|
| 铺垫 (buildup) | 30% | 20-40% | 拖沓 |
| 升级 (escalation) | 35% | 30-45% | 疲软 |
| 爆发 (explosion) | 15% | 10-20% | 堆叠 |
| 余波 (aftermath) | 20% | 15-25% | 冗长 |

## 三线比例

| 卷 | QUEST% | FIRE% | CONSTELLATION% | 检查结果 |
|----|--------|-------|---------------|---------|
| 1 | 45% | 25% | 30% | PASS |
| 2 | 52% | 27% | 21% | PASS |

## 场景类型

| 编号 | 类型 | 标志 | 在循环中的位置 | 单调性警告阈值 |
|------|------|------|--------------|--------------|
| 1 | 战斗（battle） | 高强度冲突 | 升级/爆发 | ≤ 2 章连续 |
| 2 | 对话（dialogue） | 信息/情感交流 | 铺垫/余波 | ≤ 3 章连续 |
| 3 | 说明（exposition） | 制度交代 | 铺垫 | ≤ 3 章连续 |
| 4 | 核账/调查（investigation） | 查台账 | 升级/爆发 | ≤ 3 章连续 |
| 5 | 行走（travel） | 地点转移 | 铺垫/升级 | ≤ 2 章连续 |
| 6 | 记忆代价（memoryCost） | 等重支付 | 爆发/余波 | ≤ 1 章连续 |
| 7 | 公事/权谋（politics） | 制度博弈 | 升级 | ≤ 2 章连续 |
| 8 | 试错/演示（training） | 能力演示 | 铺垫 | ≤ 2 章连续 |

## 卷节奏分配

| 卷 | 铺垫段(章节) | 铺垫% | 上升段(章节) | 上升% | 爆发段(章节) | 爆发% | 余波段(章节) | 余波% | 偏差理由/跨卷补偿 |
|----|------------|-------|------------|-------|------------|-------|------------|-------|-----------------|
| 1 | 第1-6章 | 25% | 第7-14章 | 33.3% | 第15-20章 | 25% | 第21-24章 | 16.7% | — |
| 2 | 第25-29章 | 20.8% | 第30-37章 | 33.3% | 第38-44章 | 29.2% | 第45-48章 | 16.7% | — |
"""


@pytest.mark.unit
def test_passes_with_canonical_template_tables(tmp_path: Path) -> None:
    """SKILL.md's own EXACT table shapes parse and validate end-to-end."""
    project_dir, marker = _setup(tmp_path)
    (project_dir / "outline").mkdir(parents=True)
    (project_dir / "outline" / "rhythm_principles.md").write_text(
        _CANONICAL_RHYTHM, encoding="utf-8"
    )
    result = _result(g4_pacing_design([str(marker)]))
    assert result["status"] == "PASS", result.get("must_fix")


@pytest.mark.unit
def test_scene_type_scan_stops_at_next_table_header(tmp_path: Path) -> None:
    """Volume-table rows (numeric first cell) after the scene table don't inflate the count."""
    from shenbi.contracts.skills.pacing_design import PacingDesign

    model = PacingDesign.from_markdown(_CANONICAL_RHYTHM)
    assert len(model.scene_types) == 8
    assert model.beats == {"铺垫": 30.0, "升级": 35.0, "爆发": 15.0, "余波": 20.0}
    assert model.line_ratios == {"QUEST": 45.0, "FIRE": 25.0, "CONSTELLATION": 30.0}
