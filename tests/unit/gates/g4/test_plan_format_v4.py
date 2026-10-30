"""spec #82 Task 1: plan_format v4 compatibility (version-set constants).

v4 ⊇ v3 ⊇ v2. The six version-condition sites must activate for v4 memos:
scene_budget (:123), legal token list (:247), voice_line duty (:251),
tension/payoff-axis duty (:259), drafting v2-family (:920) and v3 (:925).
Regression guard: v3 gates keep firing, v2 density checks keep firing.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.contracts.enums import PF_GE_V2, PF_GE_V3, PF_LEGAL
from shenbi.gates.g4.chapter_planning import g4_chapter_planning

V4_BODY = """plan_format: v4
emotion_tone: 悲
留存锚: 非锚章
**payoff 拍**: 类型｜轴(债)｜量
章尾张力拍: 章｜『他数到第三遍，门被推开一半。』
章尾钩型: 悬念钩
"""


def _run(tmp_path: Path, body: str) -> str:
    p = tmp_path / "plans" / "chapter-37-plan.md"
    p.parent.mkdir(parents=True)
    p.write_text(body, encoding="utf-8")
    return g4_chapter_planning([str(p)], rd=None, project_dir=str(tmp_path))


def test_version_set_constants() -> None:
    assert PF_LEGAL == ("v1", "v2", "v3", "v4")
    assert frozenset({"v2", "v3", "v4"}) == PF_GE_V2
    assert frozenset({"v3", "v4"}) == PF_GE_V3


def test_v4_is_legal_token(tmp_path: Path) -> None:
    out = _run(tmp_path, V4_BODY)
    assert "invalid_token" not in out


def test_v4_memo_scene_budget_still_enforced(tmp_path: Path) -> None:
    out = _run(tmp_path, V4_BODY)  # no 场景预算 section
    assert (
        "G4.cp.scene_budget" in out
    )  # 检查 id 前缀（audit-T1/C1：裸子串会被 tmp_path 目录名污染成永真）


def test_v4_memo_voice_line_required(tmp_path: Path) -> None:
    out = _run(tmp_path, V4_BODY)  # no 声口要求行
    assert "G4.cp.voice_line" in out  # audit-T1/C1 同款防污染


def test_v4_memo_payoff_axis_required(tmp_path: Path) -> None:
    body = V4_BODY.replace("**payoff 拍**: 类型｜轴(债)｜量\n", "**payoff 拍**: 类型\n")
    out = _run(tmp_path, body)
    assert "G4.cp.payoff_axis" in out  # audit-T1/C1 同款防污染


def test_v3_memo_still_enforced(tmp_path: Path) -> None:
    body = V4_BODY.replace("plan_format: v4", "plan_format: v3")
    body = body.replace(
        "章尾张力拍: 章｜『他数到第三遍，门被推开一半。』\n", "章尾张力拍: 章＋形态\n"
    )
    body = body.replace("章尾钩型: 悬念钩\n", "")
    out = _run(tmp_path, body)  # no 场景预算 → v3 FAIL must keep firing
    assert "G4.cp.scene_budget" in out


def test_v4_drafting_v2_family_density_fires(tmp_path: Path) -> None:
    """audit-T1/I4: drafting regexes :920 v2-gate / :925 v3-gate regression net.

    v4 memo + thin-voice chapter -> G4.cd.voice_density FAIL fires live:
    v4 must enter the #76 v2 family per v[2-9].
    """
    import json

    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    d = tmp_path
    (d / "plans").mkdir()
    (d / "chapters").mkdir()
    (d / "plans" / "chapter-1-plan.md").write_text(
        "plan_format: v4\n声口要求: 账房腔+自嘲反问\n金句位: 静｜章首复述｜一页眉批\n",
        encoding="utf-8",
    )
    (d / "chapters" / "chapter-1.md").write_text(
        "# 第一章\n<!--SCENE-->\n他把册子翻到那一页，又翻了回来。\n<!--SCENE-->\n灯芯挑了一下，账上添一笔。\n",
        encoding="utf-8",
    )
    result = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-1.md")], rd=str(d), project_dir=str(d))
    )
    assert any(m.startswith("G4.cd.voice_density") for m in result["must_fix"])
