"""Bespoke error-path tests for g4_anti_detect.

spec #95 维护批（audit-T13 F4）：merge_prose 合并章面——旧「改写报告在章内」
检查退役，新面=场景标记保全（vs .bak 基线）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.anti_detect import g4_anti_detect


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_anti_detect(fps, rd))


def _chapter(marker_n: int, scene_chars: int = 40) -> str:
    parts = ["# 章节\n"]
    for i in range(marker_n):
        parts.append(f"<!--SCENE-->\n场景{i}正文。{('细节描写' * 8)}第{i}段收束。\n")
    return "".join(parts)


@pytest.mark.unit
def test_reportless_merged_chapter_passes(tmp_path: Path) -> None:
    """merge_prose 合并章（报告在回复面、不进章文件）——无 .bak 时 PASS。

    旧断言（无 ## 改写报告 → FAIL G4.ad.no_report）随报告移出章文件退役：
    报告进场景段会被 applier 吸收为章正文污染。
    """
    f = tmp_path / "ch.md"
    f.write_text(_chapter(2), encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS", result["must_fix"]


@pytest.mark.unit
def test_scene_marker_loss_vs_bak_flagged(tmp_path: Path) -> None:
    """.bak 基线 3 标记、staged 只剩 2 → FAIL G4.ad.scene_marker_loss。"""
    f = tmp_path / "ch.md"
    f.write_text(_chapter(2), encoding="utf-8")
    (tmp_path / "ch.md.bak").write_text(_chapter(3), encoding="utf-8")
    result = _run([str(f)])
    assert any("G4.ad.scene_marker_loss" in mf for mf in result["must_fix"])
    assert any("2!=3" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_scene_marker_preserved_vs_bak_passes(tmp_path: Path) -> None:
    """标记数与 .bak 一致 → PASS + G4.ad.scene_markers PASS check。"""
    f = tmp_path / "ch.md"
    f.write_text(_chapter(3), encoding="utf-8")
    (tmp_path / "ch.md.bak").write_text(_chapter(3), encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS", result["must_fix"]
    assert any(c.get("id") == "G4.ad.scene_markers" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_markerless_base_skips_marker_check(tmp_path: Path) -> None:
    """基线本无场景标记（未分章手工面）→ 跳过标记检查，不误报。"""
    f = tmp_path / "ch.md"
    f.write_text("# 章节\n无标记正文。\n", encoding="utf-8")
    (tmp_path / "ch.md.bak").write_text("# 章节\n无标记基线。\n", encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS", result["must_fix"]


@pytest.mark.unit
def test_fails_when_file_not_found(tmp_path: Path) -> None:
    """Missing file -> FAIL."""
    result = _run([str(tmp_path / "nonexistent.md")])
    assert any("G4.ad.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_skips_on_empty_fps(tmp_path: Path) -> None:
    """Empty fps -> SKIP."""
    result = _run([])
    assert any(c["id"] == "G4.ad" and c["s"] == "SKIP" for c in result["checks"])
