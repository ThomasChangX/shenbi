"""Bespoke error-path tests for g4_chapter_planning.

chapter_planning checks each input file for 8 sections, golden-3 rules,
section 5 choice, and section 7 hook ops.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_planning import g4_chapter_planning


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_chapter_planning(fps, rd))


@pytest.mark.unit
def test_fails_when_less_than_8_sections(tmp_path: Path) -> None:
    """Plan file with < 8 numbered sections -> FAIL G4.cp.sections."""
    f = tmp_path / "chapter-001-plan.md"
    f.write_text("# Plan\n\n## 1. Intro\n## 2. Body\n", encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.cp.sections" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_all_8_sections(tmp_path: Path) -> None:
    """Plan file with all 8 sections -> PASS G4.cp.sections."""
    f = tmp_path / "chapter-001-plan.md"
    sections = "\n".join(f"## {i}. Section {i}\ncontent\n" for i in range(1, 9))
    f.write_text("# Plan\n\n" + sections, encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.cp.sections" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_golden_3_checks_chapter_1_three_walls(tmp_path: Path) -> None:
    """Chapter 1 plan missing '三面墙' -> WARN G4.cp.golden_1 (relaxed from FAIL)."""
    f = tmp_path / "chapter-1-plan.md"
    f.write_text(
        "# Plan\n\n## 1. Start\n## 2. Middle\n## 3. End\n## 4. Choice\n## 5. Key\n## 6. Turn\n## 7. Hook\n## 8. Close\n",
        encoding="utf-8",
    )
    result = _run([str(f)])
    # Golden rules are now aspirational quality targets → WARN only
    assert any(
        c["id"] == "G4.cp.golden_1" and c["s"] == "WARN" for c in result.get("checks", [])
    ), f"Expected G4.cp.golden_1 WARN in checks, got {result.get('checks', [])}"


@pytest.mark.unit
def test_fails_when_s5_choice_missing(tmp_path: Path) -> None:
    """Section 5 without 关键抉择 -> WARN G4.cp.s5_choice (relaxed from FAIL)."""
    sections = "\n".join(f"## {i}. Section {i}\ncontent\n" for i in range(1, 9))
    f = tmp_path / "chapter-001-plan.md"
    f.write_text("# Plan\n\n" + sections, encoding="utf-8")
    result = _run([str(f)])
    # Section 5 关键抉择 is now a quality bonus → WARN only
    assert any(
        c["id"] == "G4.cp.s5_choice" and c["s"] == "WARN" for c in result.get("checks", [])
    ), f"Expected G4.cp.s5_choice WARN in checks, got {result.get('checks', [])}"


@pytest.mark.unit
def test_skips_golden_for_non_123_chapters(tmp_path: Path) -> None:
    """Chapter N with N>3 -> golden check SKIPs."""
    sections = "\n".join(f"## {i}. Section {i}\ncontent\n" for i in range(1, 9))
    f = tmp_path / "chapter-005-plan.md"
    f.write_text("# Plan\n\n" + sections, encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.cp.golden" and c["s"] == "SKIP" for c in result["checks"])


@pytest.mark.unit
def test_fails_when_file_not_found(tmp_path: Path) -> None:
    """Missing file -> FAIL G4.cp.not_found."""
    result = _run([str(tmp_path / "nonexistent.md")])
    assert result["status"] == "FAIL"
    assert any("G4.cp.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_skips_on_empty_fps(tmp_path: Path) -> None:
    """Empty fps list -> SKIP."""
    result = _run([])
    assert any(c["id"] == "G4.cp" and c["s"] == "SKIP" for c in result["checks"])


@pytest.mark.unit
def test_passes_when_all_conditions_met(tmp_path: Path) -> None:
    """Valid plan with all 8 sections, golden content, s5 choice, s7 hooks -> PASS."""
    content = "# Plan\n\n"
    for i in range(1, 9):
        content += f"## {i}. Section {i}\n"
        if i == 1:
            content += "三面墙\n"
            content += "chapter_role: 高潮\n"
            content += "emotion_tone: 悲\n"
            content += "**payoff 拍**: [扮猪吃虎｜中兑现]\n"
        elif i == 2:
            content += "**留存锚**: [情感锤]\n"
        elif i == 5:
            content += "关键抉择\n"
        elif i == 7:
            content += "open advance\n"
        else:
            content += "content\n"
    f = tmp_path / "chapter-001-plan.md"
    f.write_text(content, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS"


def test_g4_cp_hard_fails_english_chapter_heading_residue(tmp_path):
    """#27 (probe17 adjudications #003→#005): the '# Chapter N:' English
    heading is banned by the skill contract; two prose re-pins failed to
    eliminate it because the write-path injector was RE-ADDING it after
    every compliant model output (#28 fixed the injector). With written
    plans now equal to model output, the gate enforces the ban machine-side
    — no third prose re-pin.
    """
    import json

    from shenbi.gates.g4.chapter_planning import g4_chapter_planning

    body = "# 第1章 章节备忘\n\n## 1. 当前任务\nchapter_role: 过渡/铺垫\n"
    for i in range(2, 9):
        body += f"\n## {i}. 段落{i}内容。\n"

    clean = tmp_path / "plans"
    clean.mkdir()
    f1 = clean / "chapter-1-plan.md"
    f1.write_text(body, encoding="utf-8")
    ok = json.loads(g4_chapter_planning([str(f1)], rd=str(tmp_path)))
    assert not any("english_heading" in m for m in ok.get("must_fix", []))

    dirty = tmp_path / "plans2"
    dirty.mkdir()
    f2 = dirty / "chapter-1-plan.md"
    f2.write_text("# Chapter 1:\n\n" + body, encoding="utf-8")
    bad = json.loads(g4_chapter_planning([str(f2)], rd=str(tmp_path)))
    assert any("G4.cp.english_heading" in m for m in bad.get("must_fix", [])), bad.get("must_fix")


#: #18-2 (probe23 adjudication #007): the ch3 memo invented MH11/MH12 —
#: book_spine caps at MH10 and pending_hooks never registered them. Two
#: human reject rounds carried explicit delete instructions; the retry memo
#: still shipped MH11 and the approve missed it. The machine gate owns hook
#: authenticity: every MH-prefixed ID in §7 must exist in the spine or the
#: pool; genuinely new plants go through the lifecycle's CP-NNN namespace.
def _plan_with_hooks(hook_rows: str) -> str:
    sections = "\n".join(f"## {i}. Section {i}\ncontent\n" for i in range(1, 7))
    return (
        "# 第3章 章节备忘\n\n" + sections + "\n## 7. Section 7\n\n"
        "| ID | 操作 | 推进方式 | 沉默章数 |\n"
        "|----|------|---------|---------|\n" + hook_rows + "\n## 8. Section 8\ncontent\n"
    )


_SPINE = "# 书脊\n\n## 主线钩子\n\n- MH01: 铜牌的纹（ITEM）\n- MH07: 「零」的那一栏（CHARACTER）\n"
_POOL = (
    "---\ntype: truth\n---\n\n# 伏笔池\n\n"
    "| Hook ID（钩子名） | 当前生命周期 |\n"
    "|------|------|\n"
    "| MH01（铜牌的纹） | RELEVANT |\n"
    "| MH07（「零」的那一栏） | RELEVANT |\n"
)


@pytest.mark.unit
def test_fails_on_unregistered_mh_hook(tmp_path: Path) -> None:
    (tmp_path / "truth").mkdir()
    (tmp_path / "truth" / "book_spine.md").write_text(_SPINE, encoding="utf-8")
    (tmp_path / "truth" / "pending_hooks.md").write_text(_POOL, encoding="utf-8")
    f = tmp_path / "chapter-003-plan.md"
    f.write_text(
        _plan_with_hooks("| MH01 | advance | 停顿一息 | 0 |\n| MH11 | open | 新植 | — |\n"),
        encoding="utf-8",
    )
    result = json.loads(g4_chapter_planning([str(f)], project_dir=str(tmp_path)))
    assert result["status"] == "FAIL"
    assert any("G4.cp.hook_refs" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_on_registered_mh_hooks(tmp_path: Path) -> None:
    (tmp_path / "truth").mkdir()
    (tmp_path / "truth" / "book_spine.md").write_text(_SPINE, encoding="utf-8")
    (tmp_path / "truth" / "pending_hooks.md").write_text(_POOL, encoding="utf-8")
    f = tmp_path / "chapter-002-plan.md"
    f.write_text(
        _plan_with_hooks(
            "| MH07 | open | 主角自称「零」 | — |\n| MH01 | advance | 停顿一息 | 0 |\n"
        ),
        encoding="utf-8",
    )
    result = json.loads(g4_chapter_planning([str(f)], project_dir=str(tmp_path)))
    assert any(c["id"] == "G4.cp.hook_refs" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_cp_namespace_hooks_are_not_gated(tmp_path: Path) -> None:
    """New plants use the lifecycle's CP-NNN namespace — outside the MH
    registry check (SKILL.md flowchart: Assign ID at plant time).
    """
    (tmp_path / "truth").mkdir()
    (tmp_path / "truth" / "book_spine.md").write_text(_SPINE, encoding="utf-8")
    (tmp_path / "truth" / "pending_hooks.md").write_text(_POOL, encoding="utf-8")
    f = tmp_path / "chapter-004-plan.md"
    f.write_text(
        _plan_with_hooks("| MH01 | advance | 停顿一息 | 0 |\n| CP-001 | open | 新植 | — |\n"),
        encoding="utf-8",
    )
    result = json.loads(g4_chapter_planning([str(f)], project_dir=str(tmp_path)))
    assert not any("G4.cp.hook_refs" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_skips_when_registry_files_absent(tmp_path: Path) -> None:
    """Phase 1: neither the spine nor the pool exists — nothing to check
    against (SKILL.md L139 phase-1 placeholder branch).
    """
    f = tmp_path / "chapter-001-plan.md"
    f.write_text(_plan_with_hooks("| MH01 | advance | 停顿一息 | 0 |\n"), encoding="utf-8")
    result = json.loads(g4_chapter_planning([str(f)], project_dir=str(tmp_path)))
    assert any(c["id"] == "G4.cp.hook_refs" and c["s"] == "SKIP" for c in result["checks"])


# ---------- spec #75 G4.cp.declarations: 三声明行硬闸 ----------


def _plan_shell(body: str) -> str:
    """Minimal plan skeleton with all 8 numbered sections (other checks need them)."""
    sections = "\n\n".join(f"## {i}." for i in range(1, 9))
    return sections + "\n\n" + body


@pytest.mark.unit
def test_g4cp_new_format_missing_declaration_fails(tmp_path: Path) -> None:
    """New-format memo (scene-budget block) missing any 三声明行 → FAIL."""
    plan = tmp_path / "chapter-3-plan.md"
    plan.write_text(
        _plan_shell(
            "### 场景预算与收束钩（#72 粒度契约）\n"
            "- 场景1: 1900字｜独立型｜收束钩：x\n"
            "- 章尾钩：y\n"
            "- 时间锚: 腊月初十\n"
            # 余额 + POV lines MISSING
        ),
        encoding="utf-8",
    )
    result = json.loads(g4_chapter_planning([str(plan)], rd=str(tmp_path)))
    assert result["status"] == "FAIL"
    assert any("G4.cp.declarations" in m and "余额" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_g4cp_new_format_complete_passes(tmp_path: Path) -> None:
    plan = tmp_path / "chapter-3-plan.md"
    plan.write_text(
        _plan_shell(
            "### 场景预算与收束钩（#72 粒度契约）\n"
            "- 场景1: 1900字｜独立型｜收束钩：x\n"
            "- 章尾钩：y\n"
            "- 时间锚: 腊月初十\n"
            "- 余额: 一百九十二文\n"
            "- POV: 他\n"
        ),
        encoding="utf-8",
    )
    result = json.loads(g4_chapter_planning([str(plan)], rd=str(tmp_path)))
    decl = [c for c in result["checks"] if c["id"] == "G4.cp.declarations"]
    assert decl and decl[0]["s"] == "PASS"


@pytest.mark.unit
def test_g4cp_legacy_format_warns_not_fails(tmp_path: Path) -> None:
    """Legacy memo without the scene-budget block → WARN exemption, never FAIL."""
    plan = tmp_path / "chapter-3-plan.md"
    plan.write_text(_plan_shell("旧式备忘，无场景预算块。\n"), encoding="utf-8")
    result = json.loads(g4_chapter_planning([str(plan)], rd=str(tmp_path)))
    decl = [c for c in result["checks"] if c["id"] == "G4.cp.declarations"]
    assert decl and decl[0]["s"] == "WARN"
