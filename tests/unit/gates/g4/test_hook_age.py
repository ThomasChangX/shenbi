"""spec #82 T2 (Task 6): hook_age gate — truth-detail-block data source."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.g4.chapter_planning import (
    g4_chapter_planning,
    parse_last_reinforced,
    parse_relevant_hooks,
)

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec82"

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
        "hook_max_age": {"max": 8, "shadow": False},
        "hook_defer_budget": {"per_volume": 3},
    },
}

HOOKS = """# 伏笔池
## 总览
| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance(14) | 升级曲线 |
|------|------|------|------|------|------|------|------|
| MH03（火纹骨哨） | RELEVANT | 1 | 429 | GENUINE | 0.5 | 50 | RISING |
| MH02（红纸包） | PLANTED | 2 | 613 | GENUINE | 0.4 | 60 | STAIRCASE |
| MH06（无名小调） | RELEVANT | 3 | 616 | SIDE | 0.8 | 70 | STAIRCASE |

## MH03 火纹骨哨与持灯人交通网
- last_reinforced: 第 36 章
- last_reinforced: 第 21 章
- 证据: chapters/chapter-36.md L1

## MH02 红纸包与春天之约
- last_reinforced: 第 35 章

## MH06 无名小调
- 证据: （种植后零推进——无 last_reinforced bullet）
"""

PLAN = """plan_format: v4
emotion_tone: 悲
留存锚: 非锚章
**payoff 拍**: 类型｜轴(债)｜中兑现
章尾张力拍: 章｜『他数到第三遍，门被推开一半。』
章尾钩型: 悬念钩
"""


VM = "# 卷纲\n## 第一卷（第 1-36 章）\n## 第二卷（第 37-91 章）\n## 第三卷（第 92-146 章）\n#### KR1: 开卷\n2. KR2（第 105-120 章完成）：渡 4\n"


def _mk(tmp_path: Path, *, ch: int = 45, plan_extra: str = "", hooks: str = HOOKS) -> Path:
    (tmp_path / "plans").mkdir(exist_ok=True)
    (tmp_path / "truth").mkdir(exist_ok=True)
    (tmp_path / "outline").mkdir(exist_ok=True)
    (tmp_path / "plans" / f"chapter-{ch}-plan.md").write_text(PLAN + plan_extra, encoding="utf-8")
    (tmp_path / "truth" / "pending_hooks.md").write_text(hooks, encoding="utf-8")
    (tmp_path / "outline" / "volume_map.md").write_text(VM, encoding="utf-8")
    (tmp_path / "genre-config.json").write_text(
        json.dumps(GENRE, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path


def _mf(tmp_path: Path, ch: int) -> list[str]:
    out = g4_chapter_planning(
        [str(tmp_path / "plans" / f"chapter-{ch}-plan.md")], rd=None, project_dir=str(tmp_path)
    )
    return json.loads(out).get("must_fix", [])


@pytest.mark.unit
def test_parse_last_reinforced_max_per_hook() -> None:
    got = parse_last_reinforced(HOOKS)
    assert got["MH03"] == 36  # max of 36/21
    assert got["MH02"] == 35
    assert "MH06" not in got  # no bullet


@pytest.mark.unit
def test_parse_relevant_hooks_overview_filter() -> None:
    assert parse_relevant_hooks(HOOKS) == {"MH03", "MH06"}


@pytest.mark.unit
def test_overaged_untouched_hook_fails(tmp_path: Path) -> None:
    # MH03 last=36; ch45 → age 9 > 8; plan has no touch/defer for MH03
    _mk(tmp_path, ch=45)
    assert any("hook_age" in m and "MH03" in m for m in _mf(tmp_path, 45))


@pytest.mark.unit
def test_touched_hook_passes(tmp_path: Path) -> None:
    _mk(tmp_path, ch=45, plan_extra="- 钩账: MH03 本章推进（渡口夜哨声再响）\n")
    assert not any("hook_age" in m and "MH03" in m for m in _mf(tmp_path, 45))


@pytest.mark.unit
def test_defer_with_anchor_passes(tmp_path: Path) -> None:
    _mk(tmp_path, ch=45, plan_extra="- 挂起: MH03 至第三卷·KR1\n")
    assert not any("hook_age" in m and "MH03" in m for m in _mf(tmp_path, 45))


@pytest.mark.unit
def test_defer_without_anchor_fails(tmp_path: Path) -> None:
    _mk(tmp_path, ch=45, plan_extra="- 挂起: MH03\n")
    assert any("挂起缺有效清偿锚" in m and "MH03" in m for m in _mf(tmp_path, 45))


@pytest.mark.unit
def test_defer_budget_exceeded_fails(tmp_path: Path) -> None:
    extra = "".join(
        f"- 挂起: MH0{k} 至第三卷·KR1\n" for k in (2, 3, 4, 5)
    )  # 4 defers > per_volume 3
    _mk(tmp_path, ch=45, plan_extra=extra)
    assert any("hook_defer_budget" in m for m in _mf(tmp_path, 45))


@pytest.mark.unit
def test_within_age_passes(tmp_path: Path) -> None:
    _mk(tmp_path, ch=42)  # MH03 age 42-36=6 ≤ 8（MH06 零推进种植起算 39>8 属合法 FAIL——另测覆盖）
    assert not any("hook_age" in m and "MH03" in m for m in _mf(tmp_path, 42))


@pytest.mark.unit
def test_zero_bullet_hooks_age_from_plant_chapter(tmp_path: Path) -> None:
    """MH06 RELEVANT, no last_reinforced → age from 种植章 3: ch45 → 42 > 8 → FAIL."""
    _mk(tmp_path, ch=45)
    assert any("hook_age" in m and "MH06" in m for m in _mf(tmp_path, 45))


@pytest.mark.unit
def test_dangling_anchor_volume_not_in_map_fails(tmp_path: Path) -> None:
    """audit-T6/I1: dangling anchor -- cited volume 99 does not exist;
    fails even though KR1 hits (C1 composite: both legs must hit).
    """
    _mk(tmp_path, ch=45, plan_extra="- 挂起: MH03 至第99卷·KR1\n")
    assert any("挂起缺有效清偿锚" in m for m in _mf(tmp_path, 45))


@pytest.mark.unit
def test_real_pending_hooks_fixture_parses() -> None:
    """audit-T6/I1+M2: real truth-file copy (G0.9) anchors parser behavior."""
    real = (FIX / "pending_hooks.md").read_text(encoding="utf-8")
    got = parse_last_reinforced(real)
    assert got.get("MH03") == 36  # multi-bullet max
    assert got.get("MH02") == 35
    assert "MH01" in parse_relevant_hooks(real)
