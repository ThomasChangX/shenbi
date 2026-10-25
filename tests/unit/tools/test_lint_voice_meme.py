"""Unit tests for tools/lint_voice_meme.py (spec #76 T3).

Constructed structural inputs (G0.9 exemption).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.lint_voice_meme import _meme_list, lint_blind, lint_chapter, lint_volume


def _mk_project(tmp_path: Path) -> Path:
    (tmp_path / "outline").mkdir()
    (tmp_path / "chapters").mkdir()
    (tmp_path / "characters").mkdir()
    (tmp_path / "characters" / "major").mkdir()
    (tmp_path / "plans").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        "## 第一卷：测试（第1—6章）\n\n**金句、母题物象与梗位**: 梗位复用：「班味的内核全球统一」、记账式吐槽｜金句：x\n\n"
        "  | 第1章 | 开篇 | 双钩 |\n  | 第3章 | 转折 | 老驼 |\n\n## 第二卷：后（第7—20章）\n",
        encoding="utf-8",
    )
    (tmp_path / "genre-config.json").write_text(
        '{"market_params": {"voice_density_min": {"min_per_chapter": 2}, '
        '"meme_quota": {"per_volume": 3}, "payoff_density": {"window": 3, "min": 1}, '
        '"emotion_band": {"window": 1, "min": 1}, "hook_grading": {"max_consecutive_micro": 2}}}',
        encoding="utf-8",
    )
    (tmp_path / "characters" / "protagonist.md").write_text(
        "---\nname: 林烽\nvoice_profile:\n  catchphrases:\n    - 这笔我先记下。\n---\n卡。\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.unit
def test_meme_list_extraction(tmp_path: Path) -> None:
    d = _mk_project(tmp_path)
    assert _meme_list(d / "outline" / "volume_map.md", 1) == ["班味的内核全球统一"]


@pytest.mark.unit
def test_volume_meme_deficit_warn(tmp_path: Path) -> None:
    d = _mk_project(tmp_path)
    (d / "chapters" / "chapter-1.md").write_text("正文。", encoding="utf-8")
    rows = lint_volume(d, 1)
    assert any("班味的内核全球统一" in r and "0/3" in r and "补触" in r for r in rows), rows


@pytest.mark.unit
def test_chapter_density_v1_warn_domain(tmp_path: Path) -> None:
    d = _mk_project(tmp_path)
    (d / "chapters" / "chapter-1.md").write_text("他推门。", encoding="utf-8")
    rows = lint_chapter(d, 1)
    assert any("v1" in r and "WARN" in r for r in rows), rows


@pytest.mark.unit
def test_chapter_density_v2_fail_domain(tmp_path: Path) -> None:
    d = _mk_project(tmp_path)
    (d / "chapters" / "chapter-1.md").write_text("他推门。", encoding="utf-8")
    (d / "plans" / "chapter-1-plan.md").write_text(
        "# 第1章 章节备忘\nplan_format: v2\n", encoding="utf-8"
    )
    rows = lint_chapter(d, 1)
    assert any("v2" in r and "FAIL 域" in r for r in rows), rows


@pytest.mark.unit
def test_file_predicate_excludes_pre_rev(tmp_path: Path) -> None:
    d = _mk_project(tmp_path)
    (d / "chapters" / "chapter-1.md").write_text("「班味的内核全球统一」出现了。", encoding="utf-8")
    (d / "chapters" / "chapter-1-pre-rev.md").write_text(
        "「班味的内核全球统一」「班味的内核全球统一」「班味的内核全球统一」", encoding="utf-8"
    )
    rows = lint_volume(d, 1)
    # pre-rev 双份不计——仍 1/3 缺额（若计入则 4/3 达标）
    assert any("1/3" in r for r in rows), rows


@pytest.mark.unit
def test_blind_rollup_five_chars() -> None:
    correct, total, details = lint_blind()
    assert total == 5
    assert correct >= 4, details
    # 平票/零标记行以无归属披露
    assert any("no-attribution" in d for d in details)


@pytest.mark.unit
def test_catchphrase_window_appearance_conditioned(tmp_path: Path) -> None:
    """Appearance-conditioned window: present + zero catchphrase = WARN."""
    d = _mk_project(tmp_path)
    (d / "characters" / "major" / "lao-tuo.md").write_text(
        "---\nname: 老驼\nvoice_profile:\n  catchphrases:\n    - 别烂在肚里。\n---\n卡。\n",
        encoding="utf-8",
    )
    (d / "outline" / "volume_map.md").write_text(
        "## 第一卷：测试（第1—6章）\n\n**金句、母题物象与梗位**: 梗位复用：「班味的内核全球统一」｜金句：x\n\n"
        "  | 第1章 | 开篇 | 双钩 |\n  | 第3章 | 转折 | 老驼客串 |\n\n## 第二卷：后（第7—20章）\n  | 第9章 | 承接 | 老驼 |\n",
        encoding="utf-8",
    )
    (d / "chapters" / "chapter-1.md").write_text("正文。", encoding="utf-8")
    rows = lint_volume(d, 1)
    assert any("老驼" in r and "口癖 0 次" in r for r in rows), rows
    # 未登场卡（名不在本卷节点行、口癖不在正文）不检
    (d / "characters" / "major" / "bai-shuang.md").write_text(
        "---\nname: 白霜\nvoice_profile:\n  catchphrases:\n    - 体面得像账目。\n---\n卡。\n",
        encoding="utf-8",
    )
    rows2 = lint_volume(d, 1)
    assert not any("白霜" in r for r in rows2), rows2
