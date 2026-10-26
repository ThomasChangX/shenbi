"""spec #72 T6: G4.cd scene checks + G4.cp packability precheck (G0.9 §4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting
from shenbi.gates.g4.chapter_planning import g4_chapter_planning
from shenbi.gates.shared import parse_scene_declarations

CW = json.dumps({"chapter_word": {"default": 3200, "min": 2800, "max": 4000}})
HOOK1 = "他把数目又数了一遍？"
HOOK2 = "门在身后合上了，他为什么没回头？"


def _chapter(tmp_path: Path, n: int, scenes: list[tuple[int, str]]) -> Path:
    d = tmp_path / "chapters"
    d.mkdir(exist_ok=True)
    parts = ["## PRE_WRITE_CHECK", "", "- x", "", f"# 第{n}章", f"# 章题{n}", ""]
    for size, hook in scenes:
        parts += ["<!--SCENE-->", "灯" * size, hook, ""]
    parts += ["## POST_WRITE_SELF_CHECK", "", "- y", ""]
    f = d / f"chapter-{n}.md"
    f.write_text("\n".join(parts), encoding="utf-8")
    return f


def _plan(tmp_path: Path, n: int, decls: list[tuple[int, str, str]]) -> Path:
    """decls: [(字数, 型别, 钩原文)]"""
    d = tmp_path / "plans"
    d.mkdir(exist_ok=True)
    lines = [f"# 第{n}章备忘", ""]
    for i in range(1, 9):
        lines += [f"## {i}. 节{i}", f"- 内容{i}", ""]
    lines += ["### 场景预算与收束钩（#72 粒度契约）", ""]
    for i, (size, kind, hook) in enumerate(decls, 1):
        lines.append(f"- 场景{i}: {size}字｜{kind}｜收束钩：{hook}")
    lines.append(f"- 章尾钩：{decls[-1][2]}")
    f = d / f"chapter-{n}-plan.md"
    f.write_text("\n".join(lines), encoding="utf-8")
    return f


@pytest.mark.unit
def test_parse_decl_roundtrip() -> None:
    memo = (
        _plan(Path("/tmp/unused"), 1, [(1900, "独立型", HOOK1)]).read_text(encoding="utf-8")
        if False
        else (
            "### 场景预算与收束钩（#72 粒度契约）\n"
            f"- 场景1: 1900字｜独立型｜收束钩：{HOOK1}\n"
            f"- 场景2: 1350字｜配对型｜收束钩：{HOOK2}\n"
            "- 章尾钩：x\n"
        )
    )
    decls = parse_scene_declarations(memo)
    assert decls == [(1, 1900, "独立型", HOOK1), (2, 1350, "配对型", HOOK2)]


@pytest.mark.unit
def test_scene_count_check(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    ok = _chapter(tmp_path, 1, [(1900, HOOK1), (1900, HOOK2)])
    result = g4_chapter_drafting([str(ok)], project_dir=str(tmp_path))
    assert "G4.cd.scene_count:" not in result  # mf 形态带冒号；PASS 不带
    bad = _chapter(tmp_path, 2, [(1900, HOOK1)])
    result = g4_chapter_drafting([str(bad)], project_dir=str(tmp_path))
    assert "G4.cd.scene_count:" in result


@pytest.mark.unit
def test_scene_hook_match_verbatim(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    _plan(tmp_path, 1, [(1900, "独立型", HOOK1), (1900, "独立型", HOOK2)])
    ch = _chapter(tmp_path, 1, [(1900, HOOK1), (1900, HOOK2)])
    result = g4_chapter_drafting([str(ch)], project_dir=str(tmp_path))
    assert "G4.cd.scene_hook_match:" not in result


@pytest.mark.unit
def test_scene_hook_match_drift(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    # 备忘声明钩 vs 章文件末行漂移
    _plan(tmp_path, 1, [(1900, "独立型", "声明里的钩原句？")])
    ch = _chapter(tmp_path, 1, [(1900, "完全不同的收束句？"), (1900, HOOK2)])
    result = g4_chapter_drafting([str(ch)], project_dir=str(tmp_path))
    assert "G4.cd.scene_hook_match:" in result


@pytest.mark.unit
def test_marker_lines_excluded_from_prose_surface(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    # 标记行不得成为「末段」污染章尾钩窗口（canary #12 同型）
    ch = _chapter(tmp_path, 1, [(1900, HOOK1), (1900, HOOK2)])
    text = ch.read_text(encoding="utf-8")
    # 末场景钩后插一段标记行（构造污染尝试）
    ch.write_text(text.replace(HOOK2, HOOK2 + "\n\n<!--SCENE-->"), encoding="utf-8")
    # scene_count 变 3 但 hook 匹配仍按场景末行（最后场景末行=HOOK2）
    result = g4_chapter_drafting([str(ch)], project_dir=str(tmp_path))
    assert "G4.cd.scene_hook_match:" not in result


# ---- G4.cp precheck ----


def _cp_result(tmp_path: Path, n: int) -> str:
    plan = tmp_path / "plans" / f"chapter-{n}-plan.md"
    return g4_chapter_planning([str(plan)], project_dir=str(tmp_path))


@pytest.mark.unit
def test_cp_gray_zone_fails(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    _plan(tmp_path, 1, [(1450, "独立型", HOOK1), (1450, "配对型", HOOK2)])
    assert "G4.cp.scene_budget" in _cp_result(tmp_path, 1)
    assert "灰域" in _cp_result(tmp_path, 1)


@pytest.mark.unit
def test_cp_domain_kind_mismatch(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    # 声明独立型但字数落配对域 → 违例
    _plan(tmp_path, 1, [(1000, "独立型", HOOK1), (1000, "独立型", HOOK2)])
    result = _cp_result(tmp_path, 1)
    assert "G4.cp.scene_budget:" in result


@pytest.mark.unit
def test_cp_composition_violation(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    # 2 场景章须两独立型：1300×2 → 组合违例
    _plan(tmp_path, 1, [(1300, "配对型", HOOK1), (1300, "配对型", HOOK2)])
    result = _cp_result(tmp_path, 1)
    assert "G4.cp.scene_budget:" in result
    assert "2 场景" in result


@pytest.mark.unit
def test_cp_scene_count_upper_bound(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    # T5 审查转记：场景数 2-3 上限执法——4 场景违例
    _plan(
        tmp_path,
        1,
        [
            (950, "配对型", HOOK1),
            (950, "配对型", HOOK2),
            (950, "配对型", HOOK1),
            (950, "配对型", HOOK2),
        ],
    )
    result = _cp_result(tmp_path, 1)
    assert "G4.cp.scene_budget:" in result


@pytest.mark.unit
def test_cp_cross_chapter_unpackable(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    # 前章（章文件）尾场景 950 + 本章首声明 1950：950+1950=2900 > 2800 → FAIL
    _chapter(tmp_path, 1, [(950, HOOK1), (950, HOOK2), (950, HOOK1)])
    _plan(tmp_path, 2, [(1950, "独立型", HOOK2), (1900, "独立型", HOOK1)])
    result = _cp_result(tmp_path, 2)
    assert "G4.cp.scene_budget:" in result


@pytest.mark.unit
def test_cp_first_bundle_skips_cross_chapter(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    # 章 1 无前章文件 → 跳过跨章段，仅本备忘自洽（3B 950×3=2850 ✓ 可打包）
    _plan(
        tmp_path,
        1,
        [(950, "配对型", HOOK1), (950, "配对型", HOOK2), (950, "配对型", HOOK1)],
    )
    result = _cp_result(tmp_path, 1)
    assert "G4.cp.scene_budget:" not in result


@pytest.mark.unit
def test_cp_no_scene_block_skips(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    # 旧式备忘（无场景块）→ 检查跳过（存量兼容）
    d = tmp_path / "plans"
    d.mkdir(exist_ok=True)
    (d / "chapter-1-plan.md").write_text("# 旧备忘\n\n## 1. 节\n- x\n", encoding="utf-8")
    assert "G4.cp.scene_budget" not in _cp_result(tmp_path, 1)


@pytest.mark.unit
def test_cp_relative_staging_path(tmp_path: Path, monkeypatch) -> None:
    """R1 regression: relative staging/ paths still detected when CWD != project."""
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    staging = tmp_path / "staging" / "plans"
    staging.mkdir(parents=True)
    _plan(tmp_path, 1, [(1900, "独立型", HOOK1), (1900, "独立型", HOOK2)])
    src = tmp_path / "plans" / "chapter-1-plan.md"
    (staging / "chapter-1-plan.md").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    # 灰域版
    bad_text = src.read_text(encoding="utf-8").replace("场景1: 1900字", "场景1: 1450字")
    (staging / "chapter-1-plan.md").write_text(bad_text, encoding="utf-8")
    monkeypatch.chdir("/")  # CWD 与 project 无关
    result = g4_chapter_planning(
        ["staging/plans/chapter-1-plan.md"], rd=str(tmp_path), project_dir=str(tmp_path)
    )
    assert "G4.cp.scene_budget:" in result
    assert "灰域" in result


@pytest.mark.unit
def test_cp_bundle_seam_joint_packing(tmp_path: Path) -> None:
    """R2 regression: leader open-tail + follower first-independent seam packing."""
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    # leader 3×950（开尾）+ follower 首 1950：950+1950=2900 > 2800 → FAIL
    _plan(
        tmp_path,
        1,
        [(950, "配对型", HOOK1), (950, "配对型", HOOK2), (950, "配对型", HOOK1)],
    )
    _plan(tmp_path, 2, [(1950, "独立型", HOOK2), (1900, "独立型", HOOK1)])
    result = _cp_result(tmp_path, 1)
    assert "G4.cp.scene_budget:" in result


@pytest.mark.unit
def test_cp_prev_full_sequence_no_false_positive(tmp_path: Path) -> None:
    """Y1 regression: prev [1900,950,950] + own first 1900 must NOT false-positive."""
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    _chapter(tmp_path, 1, [(1900, HOOK1), (950, HOOK2), (950, HOOK1)])
    _plan(tmp_path, 2, [(1900, "独立型", HOOK2), (1900, "独立型", HOOK1)])
    result = _cp_result(tmp_path, 2)
    assert "G4.cp.scene_budget:" not in result


# ---------------------------------------------------------------------------
# regen v3 F9 (2026-10-27): packing failures must carry a legalization hint
# ---------------------------------------------------------------------------
def test_packing_failure_appends_legalization_hint() -> None:
    """The packer sees the cross-chapter stream (prev actual + this decl +
    sibling decl) that the model cannot; a bare 'adjust the combination'
    sent three planning dispatches into blind re-rolls (regen v3 ch5). The
    failure must append the two concrete legalization routes.
    """
    from shenbi.gates.g4.chapter_planning import _packing_hint

    hint = _packing_hint()
    assert "配对型" in hint and "2800" in hint and "900" in hint
