"""T6: F15——叙事名回退拦截（spec #80 §4 F15；ch19/20 林烽×12 伤口）。"""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.gates.g4.cross_chapter import (
    check_narration_name,
    g4_cross_chapter,
    strip_dialogue,
)

FIXTURE = Path("tests/fixtures/invariant-mutants/ch20-name-swap-prop-break.md")
GREEN = Path("tests/fixtures/invariant-mutants/ch20-fixed-green.md")
IDENTITY = {"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]}


def test_stripped_dialogue_still_has_narration_hits():
    text = FIXTURE.read_text(encoding="utf-8")
    assert "林烽" in strip_dialogue(text)  # ≈7 处叙述段命中，剥对白后仍在


def test_dialogue_content_removed():
    assert strip_dialogue("「我是林烽。」那罕说。") == "那罕说。"


def test_alias_in_narration_fails():
    issues = check_narration_name(FIXTURE.read_text(encoding="utf-8"), IDENTITY, memo_text="")
    assert any(i.startswith("XC.narration_name:") for i in issues)


def test_fixed_chapter_clean():
    issues = check_narration_name(GREEN.read_text(encoding="utf-8"), IDENTITY, memo_text="")
    assert issues == []


def test_flashback_marker_exempts():
    memo = "- [旧名回溯] 本章闪回段用旧名"
    issues = check_narration_name(
        "林烽翻过驿务条。", IDENTITY, memo, chapter=20
    )  # chapter 显式传参——隔离 memo 标记豁免（不被 from_ch 边界混淆）
    assert issues == []


def test_before_from_ch_old_name_legal():
    # M5 合法改名路径：ch2（< from_ch=3）用旧名林烽不判红
    issues = check_narration_name("林烽在星象局抄录。", IDENTITY, memo_text="", chapter=2)
    assert issues == []


def test_after_from_ch_old_name_fails():
    issues = check_narration_name("林烽在星象局抄录。", IDENTITY, memo_text="", chapter=20)
    assert any(i.startswith("XC.narration_name:") for i in issues)


def _seed_identity(tmp_path: Path) -> None:
    facts_dir = tmp_path / "truth" / "facts"
    facts_dir.mkdir(parents=True, exist_ok=True)
    (facts_dir / "identity.json").write_text(
        json.dumps(
            {
                "$schema": "shenbi-facts-v1",
                "dim": "identity",
                "facts": {"主角": IDENTITY},
                "ops_log": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_g4_facts_absent_warns(tmp_path: Path):
    ch = tmp_path / "chapters"
    ch.mkdir()
    (ch / "chapter-20.md").write_text("林烽抬头。", encoding="utf-8")
    out = g4_cross_chapter([str(ch / "chapter-20.md")], project_dir=str(tmp_path))
    assert "narration_name" in out  # WARN no_facts 可见（非静默、非 FAIL）


def test_g4_snapshot_files_exempt(tmp_path: Path):
    _seed_identity(tmp_path)
    ch = tmp_path / "chapters"
    ch.mkdir()
    snap = ch / "chapter-1-pre-rev.md"
    snap.write_text("林烽抬头。", encoding="utf-8")  # pre-rev 快照=修复前正史
    out = g4_cross_chapter([str(snap)], project_dir=str(tmp_path))
    assert "XC.narration_name" not in out or "林烽" not in out.split("r")[-1]
