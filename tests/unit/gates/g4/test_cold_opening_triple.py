"""Spec #95 T2 (R3): cold-triple shadow WARN + volume_opening_protocol landing.

Cold triple = emotion_tone==平 AND 金句位 non-hot (静) AND 章尾张力拍==微 co-present
in one plan memo -> G4.cp.cold_opening_triple finding; GATE_TO_SHADOW_KEY entry
(market_params.volume_opening_protocol) defaults it to WARN (shadow:true absent
key), shadow:false promotes HARD.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_planning import g4_chapter_planning
from shenbi.gates.g4.shadow import GATE_TO_SHADOW_KEY, apply_shadow


def _plan(tone: str, golden_line: str, tier: str) -> str:
    content = "# Plan\n\n"
    for i in range(1, 9):
        content += f"## {i}. Section {i}\n"
        if i == 1:
            content += "三面墙\nchapter_role: 推进\n"
            content += f"emotion_tone: {tone}\n"
            content += f"金句位: {golden_line}｜白描｜章尾\n"
            content += f"**章尾张力拍**: [{tier}｜递进]\n"
            content += "**payoff 拍**: [扮猪吃虎｜中兑现]\n"
        elif i == 2:
            content += "**留存锚**: [情感锤]\n"
        elif i == 5:
            content += "关键抉择\n"
        elif i == 7:
            content += "open advance\n"
        else:
            content += "content\n"
    return content


def _run(tmp_path: Path, plan_text: str) -> dict[str, Any]:
    d = tmp_path / "plans"
    d.mkdir(exist_ok=True)
    f = d / "chapter-1-plan.md"
    f.write_text(plan_text, encoding="utf-8")
    return json.loads(g4_chapter_planning([str(f)], rd=str(tmp_path)))


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")
    return tmp_path


@pytest.mark.unit
def test_cold_triple_fires_finding(project: Path) -> None:
    res = _run(project, _plan("平", "静", "微"))
    assert any("cold_opening_triple" in mf for mf in res.get("must_fix", []))


@pytest.mark.unit
def test_any_hot_arm_suppresses(project: Path) -> None:
    for tone, golden, tier in (("悲", "静", "微"), ("平", "燃", "微"), ("平", "静", "章")):
        res = _run(project, _plan(tone, golden, tier))
        assert not any("cold_opening_triple" in mf for mf in res.get("must_fix", [])), (
            tone,
            golden,
            tier,
        )


@pytest.mark.unit
def test_shadow_registry_defaults_warn(tmp_path: Path) -> None:
    assert GATE_TO_SHADOW_KEY["cp.cold_opening_triple"] == (
        "market_params",
        "volume_opening_protocol",
    )
    # key absent in config -> default shadow:true -> demoted
    (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")
    out = apply_shadow(tmp_path, "G4.cp.cold_opening_triple:plans/x.md:冷三连")
    assert out is not None and out.startswith("[shadow]")


@pytest.mark.unit
def test_shadow_false_promotes_hard_routing(tmp_path: Path) -> None:
    """audit-T5 I1: promotion must reach the HARD path end-to-end.

    apply_shadow None (no demotion) + G4_CHECK_MAP has no cold_opening_triple
    entry (unlisted -> conservative default HARD, cold_streak_window precedent)
    — the classifier runs AFTER shadow demotion, so a WARN map entry would
    misroute promoted items into warn_fails (log-only) and kill the promotion.
    """
    from shenbi.pipeline.chapter_loop import G4_CHECK_MAP, _classify_g4_failures

    item = "G4.cp.cold_opening_triple:plans/x.md: 冷三连同现"
    assert "cold_opening_triple" not in G4_CHECK_MAP  # 未列=保守默认 HARD
    hard, soft, warn = _classify_g4_failures([item])
    assert item in hard and not soft and not warn


@pytest.mark.unit
def test_shadow_false_promotes_hard(tmp_path: Path) -> None:
    cfg = {
        "market_params": {
            "payoff_density": {"window": 3, "min": 1},
            "hook_grading": {"max_consecutive_micro": 2},
            "volume_opening_protocol": {"shadow": False},
        }
    }
    (tmp_path / "genre-config.json").write_text(json.dumps(cfg), encoding="utf-8")
    assert apply_shadow(tmp_path, "G4.cp.cold_opening_triple:plans/x.md:冷三连") is None
