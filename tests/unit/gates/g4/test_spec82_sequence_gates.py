"""spec #82 T1 (Task 4): cross-chapter sequence gates on the T0 snapshot.

Four market_params keys drive four G4.cp checks reading the completion-time
snapshot (never the mutable plan): cold_streak_cap (FAIL), hot_hook_floor
(FAIL), payoff_magnitude_floor (FAIL), temperature_profile (WARN). The cold
predicate is the shared ordered-branch constant (recall_weight.cold_chapter).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_planning import g4_chapter_planning
from shenbi.text.recall_weight import cold_chapter

GENRE = {
    "version": "1",
    "approval": {"decision": "approved"},
    "auditDimensions": {f"d{i}": True for i in range(5)},
    "chapterTypes": {f"t{i}": True for i in range(6)},
    "customRules": [],
    "fatigueWords": {"禁用": []},
    "pacing": {},
    "updated": "",
    "market_params": {
        "payoff_density": {"window": 3, "min": 1},
        "hook_grading": {"max_consecutive_micro": 2},
        "cold_streak_cap": {"max": 3, "shadow": False},
        "hot_hook_floor": {"window": 10, "min": 1, "shadow": False},
        "payoff_magnitude_floor": {"window": 6, "min": "中", "shadow": False},
        "temperature_profile": {"window": 10, "hot_ratio_min": 0.2},
    },
}

PLAN_T = "plan_format: v4\nemotion_tone: {tone}\n留存锚: 非锚章\n**payoff 拍**: 类型｜轴(债)｜{payoff}兑现\n章尾张力拍: {tier}｜『他数到第三遍，门被推开一半。』\n章尾钩型: 悬念钩\n"


def _mk(
    tmp_path: Path,
    *,
    tone: str = "悲",
    tier: str = "章",
    payoff: str = "中",
    ch: int = 37,
    history: dict[int, dict[str, Any]] | None = None,
    genre: dict[str, Any] | None = None,
) -> Path:
    (tmp_path / "plans").mkdir(exist_ok=True)
    (tmp_path / "plans" / f"chapter-{ch}-plan.md").write_text(
        PLAN_T.format(tone=tone, tier=tier, payoff=payoff), encoding="utf-8"
    )
    (tmp_path / "genre-config.json").write_text(
        json.dumps(genre or GENRE, ensure_ascii=False), encoding="utf-8"
    )
    if history:
        state = {
            "project_dir": str(tmp_path),
            "chapter_loop": {
                "current_chapter": ch,
                "chapter_states": {
                    str(n): {"declared": d, "status": "complete"} for n, d in history.items()
                },
            },
        }
        (tmp_path / "pipeline-state.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )
    return tmp_path


def _run(tmp_path: Path, ch: int = 37) -> str:
    return g4_chapter_planning(
        [str(tmp_path / "plans" / f"chapter-{ch}-plan.md")],
        rd=None,
        project_dir=str(tmp_path),
    )


def _must_fix(out: str) -> list[str]:
    return json.loads(out).get("must_fix", [])


@pytest.mark.unit
def test_cold_chapter_ordered_branches() -> None:
    assert cold_chapter("安", False) is True  # ① wordlist-external → cold
    assert cold_chapter("安", True) is True  # ① takes priority over golden
    assert cold_chapter("悲", False) is True  # ② cold set, not golden
    assert cold_chapter("悲", True) is False  # ② golden exception
    assert cold_chapter("惧", False) is True
    assert cold_chapter("喜", False) is False  # ③ warm
    assert cold_chapter("怒", True) is False


@pytest.mark.unit
def test_four_cold_run_fails(tmp_path: Path) -> None:
    hist = {
        n: {"emotion_tone": t, "金句位燃": False}
        for n, t in zip(range(33, 37), ["悲", "惧", "平", "悲"], strict=True)
    }
    _mk(tmp_path, tone="悲", history=hist)  # current cold → run of 5
    out = _run(tmp_path)
    assert "G4.cp.cold_streak_window" in out


@pytest.mark.unit
def test_three_cold_plus_warm_passes(tmp_path: Path) -> None:
    hist = {
        n: {"emotion_tone": t, "金句位燃": False}
        for n, t in zip(range(33, 37), ["悲", "悲", "惧", "喜"], strict=True)
    }
    _mk(tmp_path, tone="悲", history=hist)  # current cold → run of 2 after warm
    out = _run(tmp_path)
    assert "G4.cp.cold_streak_window" not in out


@pytest.mark.unit
def test_ten_window_no_big_hook_fails(tmp_path: Path) -> None:
    hist = {n: {"张力拍档位": "微"} for n in range(27, 37)}
    _mk(tmp_path, tier="章", history=hist)  # no 大 in window
    out = _run(tmp_path)
    assert "G4.cp.hot_hook_window" in out


@pytest.mark.unit
def test_six_window_all_small_payoff_fails(tmp_path: Path) -> None:
    hist = {n: {"payoff档": "小"} for n in range(31, 37)}
    _mk(tmp_path, payoff="小", history=hist)
    out = _run(tmp_path)
    assert "G4.cp.payoff_magnitude" in out


@pytest.mark.unit
def test_hot_ratio_warn_only(tmp_path: Path) -> None:
    hist = {n: {"emotion_tone": "平", "张力拍档位": "微"} for n in range(27, 37)}
    _mk(tmp_path, tone="悲", tier="微", history=hist)
    out = _run(tmp_path)
    assert "temperature_profile" in out  # WARN-level emission


@pytest.mark.unit
def test_first_three_chapters_exempt(tmp_path: Path) -> None:
    hist = {1: {"emotion_tone": "悲"}, 2: {"emotion_tone": "悲"}}
    _mk(tmp_path, tone="悲", ch=3, history=hist)
    out = _run(tmp_path, ch=3)
    assert "G4.cp.cold_streak_window" not in out


@pytest.mark.unit
def test_config_absent_degrades_to_warn(tmp_path: Path) -> None:
    genre = json.loads(json.dumps(GENRE))
    del genre["market_params"]["cold_streak_cap"]
    hist = {
        n: {"emotion_tone": t} for n, t in zip(range(33, 37), ["悲", "惧", "平", "悲"], strict=True)
    }
    _mk(tmp_path, tone="悲", history=hist, genre=genre)
    out = _run(tmp_path)
    assert not any("cold_streak_window" in m for m in _must_fix(out))  # absent → WARN row only


@pytest.mark.unit
def test_bootstrap_window_shorter_than_window_no_floor(tmp_path: Path) -> None:
    # ch38 planning: only ch37 exists in snapshot (1 < window 10)
    hist = {37: {"张力拍档位": "微"}}
    _mk(tmp_path, tier="微", ch=38, history=hist)
    out = _run(tmp_path, ch=38)
    assert "G4.cp.hot_hook_window" not in out  # bootstrap: window not full → no floor


@pytest.mark.unit
def test_min_key_is_consumed(tmp_path: Path) -> None:
    """Payoff floor reads `min` (anti payoff_density precedent)."""
    hist = {n: {"payoff档": "小"} for n in range(31, 37)}
    _mk(tmp_path, payoff="中", history=hist)  # current 中 satisfies min=中
    out = _run(tmp_path)
    assert "G4.cp.payoff_magnitude" not in out


@pytest.mark.unit
def test_volume_boundary_excludes_previous_volume(tmp_path: Path) -> None:
    """audit-T4/C1: 回卷窗口跨卷界只取本卷已生成章.

    vol2=ch37-91, vol3=ch92+: planning ch92 (first chapter of vol3) with a
    four-cold tail in vol2 snapshots must NOT fail — the run restarts at the
    volume boundary (run=1, the current chapter only).
    """
    hist = {
        n: {"emotion_tone": t} for n, t in zip(range(88, 92), ["悲", "惧", "平", "悲"], strict=True)
    }
    _mk(tmp_path, tone="悲", ch=92, history=hist)
    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        "# 卷纲\n## 第一卷（第 1-36 章）\n## 第二卷（第 37-91 章）\n## 第三卷（第 92-146 章）\n",
        encoding="utf-8",
    )
    out = _run(tmp_path, ch=92)
    assert not any("cold_streak_window" in m for m in _must_fix(out))


@pytest.mark.unit
def test_hot_ratio_warn_not_in_must_fix(tmp_path: Path) -> None:
    """audit-T4/I2: WARN-level emission goes to checks, never must_fix."""
    hist = {n: {"emotion_tone": "平", "张力拍档位": "微"} for n in range(27, 37)}
    _mk(tmp_path, tone="悲", tier="微", history=hist)
    out = _run(tmp_path)
    assert not any("temperature_profile" in m for m in _must_fix(out))  # never HARD
    checks = json.loads(out).get("checks", [])
    assert any(
        "temperature_profile" in str(chk.get("id", "")) for chk in checks
    )  # WARN row present


@pytest.mark.unit
def test_config_absent_warn_row_present(tmp_path: Path) -> None:
    """audit-T4/I2: absent key emits a WARN row (not silent skip)."""
    genre = json.loads(json.dumps(GENRE))
    del genre["market_params"]["cold_streak_cap"]
    _mk(tmp_path, genre=genre)
    out = _run(tmp_path)
    checks = json.loads(out).get("checks", [])
    assert any("cold_streak_window" in str(chk.get("id", "")) for chk in checks)


@pytest.mark.unit
def test_hot_hook_min_two_consumed(tmp_path: Path) -> None:
    """audit-T4/M2: hot_hook_floor.min=2 with exactly one 大 in window → FAIL."""
    genre = json.loads(json.dumps(GENRE))
    genre["market_params"]["hot_hook_floor"] = {"window": 10, "min": 2, "shadow": False}
    hist = {n: {"张力拍档位": "微"} for n in range(27, 37)}
    hist[30]["张力拍档位"] = "大"  # exactly one 大 in window
    _mk(tmp_path, tier="微", history=hist, genre=genre)
    out = _run(tmp_path)
    assert any("hot_hook_window" in m and "1<2" in m for m in _must_fix(out))
