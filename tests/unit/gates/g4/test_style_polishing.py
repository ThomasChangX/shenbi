"""Bespoke error-path tests for g4_style_polishing.

spec #95 维护批（audit-T13 F4）：merge_prose 合并章面——旧「润色说明在章内」
检查退役，章内不变量=±15% 字数比（vs .bak）。word_count_md only counts CJK
ideographs (一-鿿), so test content uses Chinese chars.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.style_polishing import g4_style_polishing


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_style_polishing(fps, rd))


@pytest.mark.unit
def test_reportless_merged_chapter_without_bak_passes(tmp_path: Path) -> None:
    """merge_prose 合并章（润色说明移出章文件）+ 无 .bak 基线 → PASS。

    旧断言（无 ## 润色说明 → FAIL G4.sp.no_report）随报告移出章文件退役：
    报告进场景段会被 applier 吸收为章正文污染。
    """
    f = tmp_path / "ch.md"
    f.write_text("# 章节\n\n正文内容。\n", encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS", result["must_fix"]


@pytest.mark.unit
def test_fails_when_word_ratio_out_of_range(tmp_path: Path) -> None:
    """.bak file with much less CJK content -> ratio > 1.15 -> FAIL G4.sp.word_ratio."""
    f = tmp_path / "ch.md"
    f.write_text(
        "# 章节\n\n正文" + ("长内容很长" * 200) + "\n## 润色说明\n已经润色。\n", encoding="utf-8"
    )
    bak = tmp_path / "ch.md.bak"
    bak.write_text("# 章节\n\n" + "短" * 10 + "\n", encoding="utf-8")
    result = _run([str(f)])
    assert any("G4.sp.word_ratio" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_when_word_ratio_in_range(tmp_path: Path) -> None:
    """.bak present with similar CJK content -> ratio in [0.85, 1.15] -> PASS."""
    body = "这是中文测试。\n" * 5
    f = tmp_path / "ch.md"
    f.write_text("# 章节\n\n" + body + "\n## 润色说明\n润色后。\n", encoding="utf-8")
    bak = tmp_path / "ch.md.bak"
    bak.write_text("# 章节\n\n" + body + "\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.sp.word_ratio" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_fails_when_file_not_found(tmp_path: Path) -> None:
    """Missing file -> FAIL G4.sp.not_found."""
    result = _run([str(tmp_path / "nonexistent.md")])
    assert result["status"] == "FAIL"
    assert any("G4.sp.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_skips_on_empty_fps(tmp_path: Path) -> None:
    """Empty fps list -> SKIP."""
    result = _run([])
    assert any(c["id"] == "G4.sp" and c["s"] == "SKIP" for c in result["checks"])
