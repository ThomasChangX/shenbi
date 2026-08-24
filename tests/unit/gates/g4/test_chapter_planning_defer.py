"""G4 chapter_planning defer-silence rule (spec #9 R2 / F201).

Was dead-wired in contracts.skills.chapter_planning.ChapterPlanning
._defer_silence_warning (model had zero consumers). SKILL.md section 7
template declares the rule 可自动检查: 操作=defer 且 沉默章数 ≥ 4 ->
section 7 must carry 激活方案 or ABANDON annotation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_planning import g4_chapter_planning

HOOK_TABLE = """| ID | 操作 | 推进方式 | 沉默章数 |
|----|------|---------|---------|
| H01 | defer | 延迟原因 | {silent} |
"""


def _plan(silent: int, tail: str = "") -> str:
    # Sections 1-6, then section 7 (hook table), then a SINGLE section 8:
    # the s7 extraction regex stops at the FIRST "## 8." heading.
    head = "\n".join(f"## {i}. s\ncontent\n" for i in range(1, 7))
    s7 = f"## 7. 本章 hook 账\n{HOOK_TABLE.format(silent=silent)}\n{tail}"
    s8 = "## 8. 不要做\n无"
    return f"# Plan\n\n{head}\n{s7}\n{s8}\n"


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_chapter_planning(fps, rd))


class TestDeferSilence:
    @pytest.mark.unit
    def test_defer_silent4_without_activation_fails(self, tmp_path: Path) -> None:
        f = tmp_path / "chapter-005-plan.md"
        f.write_text(_plan(4), encoding="utf-8")
        result = _run([str(f)])
        assert any("G4.cp.s7_defer_silence" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_defer_silent4_with_activation_passes(self, tmp_path: Path) -> None:
        f = tmp_path / "chapter-005-plan.md"
        f.write_text(_plan(4, tail="激活方案：第 6 章通过对话揭示。"), encoding="utf-8")
        result = _run([str(f)])
        assert not any("G4.cp.s7_defer_silence" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_defer_silent3_not_flagged(self, tmp_path: Path) -> None:
        f = tmp_path / "chapter-005-plan.md"
        f.write_text(_plan(3), encoding="utf-8")
        result = _run([str(f)])
        assert not any("G4.cp.s7_defer_silence" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_abandon_annotation_passes(self, tmp_path: Path) -> None:
        f = tmp_path / "chapter-005-plan.md"
        f.write_text(_plan(4, tail="ABANDON：放弃此伏笔"), encoding="utf-8")
        result = _run([str(f)])
        assert not any("G4.cp.s7_defer_silence" in mf for mf in result["must_fix"])
