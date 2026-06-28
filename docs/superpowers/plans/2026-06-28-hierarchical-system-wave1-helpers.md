# 分层系统 Wave 1：基础 Helpers 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 4 个确定性 helper + 1 个测试基建修复，为 Wave 2-4（记忆/评分/闭环）提供无外部依赖的确定性基座。

**Architecture:** 遵循现有 skill_utils 模式（`src/shenbi/skill_utils/<name>/` 下 logic.py + __main__.py + __init__.py）。纯函数，dataclass 输入，CLI 输出 JSON。scoring.py 直接扩展。lock-tool-hashes.sh 改为全树扫描。

**Tech Stack:** Python 3.11+，pathlib.Path，pytest，dataclasses，无外部依赖。

**Spec:** `docs/superpowers/specs/2026-06-28-hierarchical-memory-scoring-system-design.md` v1.4.0
- §5.2 诊断 schema + route_revision
- §5.3 verify_preservation
- §5.5 scoring.py 扩展（双评员一致性 + 塍缩检测）
- §6.2-6.3 escalation_check
- §3.6 foreshadowing_recall
- §9.4 lock-tool-hashes.sh 全树扫描
- §11.4-11.5 接缝契约（revision 读评分诊断 + preserve 组装）

## Global Constraints

- Python 3.11+，`from __future__ import annotations`，dataclass(frozen=True)，pathlib.Path
- 无 `print()` 在 framework 代码；helper 用 CLI argparse + JSON stdout
- 测试标记：`@pytest.mark.unit`
- Conventional Commits：`feat:`, `test:`, `fix:`, `chore:`
- helper 纯函数：同输入同输出（确定性），无副作用
- 修改 src/shenbi/ 任何代码后必须运行 `bash tests/lock-tool-hashes.sh`
- G0.10 的硬编码 `59` 不在本波（波2），本波不动 g0.py

## File Structure

| 文件 | 职责 |
|------|------|
| `src/shenbi/skill_utils/revision_routing/__init__.py` | 包标记 |
| `src/shenbi/skill_utils/revision_routing/route.py` | route_revision：诊断→路由分类 |
| `src/shenbi/skill_utils/revision_routing/preserve_check.py` | verify_preservation：重生保留核验 |
| `src/shenbi/skill_utils/revision_routing/__main__.py` | CLI runner |
| `src/shenbi/skill_utils/escalation/__init__.py` | 包标记 |
| `src/shenbi/skill_utils/escalation/check.py` | escalation_check + 线性回归斜率 |
| `src/shenbi/skill_utils/escalation/__main__.py` | CLI runner |
| `src/shenbi/skill_utils/foreshadowing_recall/__init__.py` | 包标记 |
| `src/shenbi/skill_utils/foreshadowing_recall/recall.py` | recall_overdue_hooks：确定性阈值过滤 |
| `src/shenbi/skill_utils/foreshadowing_recall/__main__.py` | CLI runner |
| `src/shenbi/scoring.py` | 扩展 check_scorer_agreement + flag_score_collapse |
| `tests/lock-tool-hashes.sh` | 改为全树扫描 |
| `tests/unit/skill_utils/test_revision_routing.py` | route + preserve 测试 |
| `tests/unit/skill_utils/test_escalation.py` | 升级触发测试 |
| `tests/unit/skill_utils/test_foreshadowing_recall.py` | 召回测试 |
| `tests/unit/test_scoring_anti_collapse.py` | 双评员 + 塍缩测试 |

---

### Task 1: revision_routing — route_revision

**Files:**
- Create: `src/shenbi/skill_utils/revision_routing/__init__.py`
- Create: `src/shenbi/skill_utils/revision_routing/route.py`
- Create: `src/shenbi/skill_utils/revision_routing/__main__.py`
- Test: `tests/unit/skill_utils/test_revision_routing.py`

**Interfaces:**
- Consumes: 评分诊断 dict（spec §5.2 schema: `{"issues": [{"category", "id", "evidence", "severity"}]}`）
- Produces: `route_revision(diagnosis: dict) -> str` 返回 `"spot-fix" | "regenerate" | "constrained-regenerate"`（Wave 4 的 chapter-revision 消费此返回值）

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/skill_utils/test_revision_routing.py
"""Unit tests for skill_utils/revision_routing/route.py (spec §5.2)."""

from __future__ import annotations

import pytest

from shenbi.skill_utils.revision_routing.route import route_revision


@pytest.mark.unit
def test_pure_craft_issues_route_to_spot_fix() -> None:
    diagnosis = {"issues": [
        {"category": "craft", "id": "craft-ai-tell-L23", "evidence": "ch5.md L23", "severity": "CRITICAL"},
    ]}
    assert route_revision(diagnosis) == "spot-fix"


@pytest.mark.unit
def test_unmet_blocking_goal_routes_to_regenerate() -> None:
    diagnosis = {"issues": [
        {"category": "unmet_goal", "id": "goal-H01-advance", "evidence": "ch5.md", "severity": "BLOCKING"},
    ]}
    assert route_revision(diagnosis) == "regenerate"


@pytest.mark.unit
def test_unmet_blocking_plus_craft_routes_to_constrained_regenerate() -> None:
    diagnosis = {"issues": [
        {"category": "unmet_goal", "id": "goal-H01-advance", "evidence": "ch5.md", "severity": "BLOCKING"},
        {"category": "craft", "id": "craft-fatigue-L40", "evidence": "ch5.md L40", "severity": "MINOR"},
    ]}
    assert route_revision(diagnosis) == "constrained-regenerate"


@pytest.mark.unit
def test_unmet_non_blocking_goal_routes_to_spot_fix() -> None:
    diagnosis = {"issues": [
        {"category": "unmet_goal", "id": "goal-soft", "evidence": "ch5.md", "severity": "MINOR"},
    ]}
    assert route_revision(diagnosis) == "spot-fix"


@pytest.mark.unit
def test_empty_diagnosis_routes_to_spot_fix() -> None:
    assert route_revision({"issues": []}) == "spot-fix"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/skill_utils/test_revision_routing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.skill_utils.revision_routing'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/skill_utils/revision_routing/__init__.py
"""revision_routing package."""
```

```python
# src/shenbi/skill_utils/revision_routing/route.py
"""route.py — diagnosis routing for revision mode selection (spec §5.2).

Classifies a structured diagnosis from the scoring subagent into one of
three revision modes. The routing is deterministic: BLOCKING unmet-goal
issues demand regeneration (the chapter failed its stated goals); craft-
only issues can be spot-fixed. When both are present, regeneration runs
under craft constraints so the rewrite does not reintroduce AI tells.

Diagnosis schema (spec §5.1):
    {"issues": [
        {"category": "unmet_goal" | "craft",
         "id": str,
         "evidence": str,
         "severity": "BLOCKING" | "CRITICAL" | "MINOR"}
    ]}
"""

from __future__ import annotations

from enum import StrEnum


class RevisionMode(StrEnum):
    SPOT_FIX = "spot-fix"
    REGENERATE = "regenerate"
    CONSTRAINED_REGENERATE = "constrained-regenerate"


def route_revision(diagnosis: dict) -> str:
    """Classify diagnosis into revision mode (spec §5.2).

    Returns one of RevisionMode values as a plain string.
    """
    issues = diagnosis.get("issues", [])
    has_unmet_blocking = any(
        i.get("category") == "unmet_goal" and i.get("severity") == "BLOCKING"
        for i in issues
    )
    has_craft = any(i.get("category") == "craft" for i in issues)
    if has_unmet_blocking and has_craft:
        return RevisionMode.CONSTRAINED_REGENERATE
    if has_unmet_blocking:
        return RevisionMode.REGENERATE
    return RevisionMode.SPOT_FIX
```

```python
# src/shenbi/skill_utils/revision_routing/__main__.py
"""Standalone runner: python -m shenbi.skill_utils.revision_routing"""

from shenbi.skill_utils.revision_routing.route import route_revision
import json
import sys


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(prog="revision_routing", description="Route a diagnosis to revision mode (spec §5.2).")
    parser.add_argument("--diagnosis", required=True, help="JSON diagnosis string.")
    args = parser.parse_args()
    diagnosis = json.loads(args.diagnosis)
    print(json.dumps({"mode": route_revision(diagnosis)}))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/skill_utils/test_revision_routing.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/skill_utils/revision_routing/ tests/unit/skill_utils/test_revision_routing.py
git commit -m "feat: add revision_routing route_revision helper (spec §5.2)"
```

---

### Task 2: revision_routing — verify_preservation

**Files:**
- Create: `src/shenbi/skill_utils/revision_routing/preserve_check.py`
- Modify: `tests/unit/skill_utils/test_revision_routing.py` (append tests)

**Interfaces:**
- Consumes: `original` dict（重生前组装，spec §11.5）+ `regenerated` dict（重生后 state-settling 重跑输出）
  - schema: `{"chapter": int, "hooks_advanced": [str], "changes_realized": [str], "state_changes": [str]}`
- Produces: `verify_preservation(original: dict, regenerated: dict) -> tuple[bool, list[str]]`（Wave 4 chapter-revision 调用）

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/skill_utils/test_revision_routing.py`:

```python
from shenbi.skill_utils.revision_routing.preserve_check import verify_preservation


@pytest.mark.unit
def test_preservation_pass_when_all_items_retained() -> None:
    original = {
        "chapter": 5,
        "hooks_advanced": ["H01", "H03"],
        "changes_realized": ["信息: 得知反派寻找玉佩"],
        "state_changes": ["林轩: 紧张→自信"],
    }
    regenerated = {
        "chapter": 5,
        "hooks_advanced": ["H01", "H03", "H04"],  # superset OK
        "changes_realized": ["信息: 得知反派寻找玉佩"],
        "state_changes": ["林轩: 紧张→自信"],
    }
    ok, violations = verify_preservation(original, regenerated)
    assert ok
    assert violations == []


@pytest.mark.unit
def test_preservation_fails_when_hook_lost() -> None:
    original = {
        "chapter": 5,
        "hooks_advanced": ["H01", "H03"],
        "changes_realized": [],
        "state_changes": [],
    }
    regenerated = {
        "chapter": 5,
        "hooks_advanced": ["H01"],  # H03 lost
        "changes_realized": [],
        "state_changes": [],
    }
    ok, violations = verify_preservation(original, regenerated)
    assert not ok
    assert any("H03" in v for v in violations)


@pytest.mark.unit
def test_preservation_fails_when_change_lost() -> None:
    original = {
        "chapter": 5,
        "hooks_advanced": [],
        "changes_realized": ["权力: 升入内门"],
        "state_changes": [],
    }
    regenerated = {
        "chapter": 5,
        "hooks_advanced": [],
        "changes_realized": [],  # change lost
        "state_changes": [],
    }
    ok, violations = verify_preservation(original, regenerated)
    assert not ok
    assert len(violations) == 1


@pytest.mark.unit
def test_preservation_fails_when_state_change_reverted() -> None:
    original = {
        "chapter": 5,
        "hooks_advanced": [],
        "changes_realized": [],
        "state_changes": ["苏晴: 观望→认可"],
    }
    regenerated = {
        "chapter": 5,
        "hooks_advanced": [],
        "changes_realized": [],
        "state_changes": [],  # reverted
    }
    ok, violations = verify_preservation(original, regenerated)
    assert not ok
    assert len(violations) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/skill_utils/test_revision_routing.py::test_preservation_pass_when_all_items_retained -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/skill_utils/revision_routing/preserve_check.py
"""preserve_check.py — regeneration preservation verification (spec §5.3, §11.5).

After a chapter is regenerated (not spot-fixed), the regenerated version
must retain every key outcome the original already achieved: advanced/
resolved hooks, realized §6 changes, and character state changes. This
function compares the original-item dict (assembled before regeneration)
against the regenerated dict (from rerun state-settling) and reports
violations.

Dict schema (spec §11.5):
    {"chapter": int,
     "hooks_advanced": [str],       # hook_ids advanced/resolved in original
     "changes_realized": [str],     # §6 changes that occurred in original
     "state_changes": [str]}        # character matrix deltas in original
"""

from __future__ import annotations


def verify_preservation(original: dict, regenerated: dict) -> tuple[bool, list[str]]:
    """Verify regenerated chapter retains all original key outcomes.

    Returns (all_preserved, violations). A violation is a human-readable
    string naming what was lost.
    """
    violations: list[str] = []

    original_hooks = set(original.get("hooks_advanced", []))
    regen_hooks = set(regenerated.get("hooks_advanced", []))
    for hook_id in original_hooks - regen_hooks:
        violations.append(f"hook {hook_id} advanced in original but lost in regeneration")

    original_changes = original.get("changes_realized", [])
    regen_changes = set(regenerated.get("changes_realized", []))
    for change in original_changes:
        if change not in regen_changes:
            violations.append(f"§6 change lost: {change}")

    original_states = original.get("state_changes", [])
    regen_states = set(regenerated.get("state_changes", []))
    for state in original_states:
        if state not in regen_states:
            violations.append(f"state change reverted: {state}")

    return (len(violations) == 0, violations)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/skill_utils/test_revision_routing.py -v`
Expected: 9 passed (5 from Task 1 + 4 new)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/skill_utils/revision_routing/preserve_check.py tests/unit/skill_utils/test_revision_routing.py
git commit -m "feat: add verify_preservation for regeneration retention check (spec §5.3, §11.5)"
```

---

### Task 3: scoring.py — check_scorer_agreement + flag_score_collapse

**Files:**
- Modify: `src/shenbi/scoring.py` (append two functions before `main()`)
- Create: `tests/unit/test_scoring_anti_collapse.py`

**Interfaces:**
- Consumes: 两个评分员的 dimension scores（`dict[int, float]`）+ 单评员 scores
- Produces: `check_scorer_agreement(scores_a, scores_b, threshold) -> dict` + `flag_score_collapse(scores) -> dict`（Wave 3 评分 skill dispatch 后调用）

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_scoring_anti_collapse.py
"""Unit tests for scoring.py anti-collapse extensions (spec §5.5)."""

from __future__ import annotations

import pytest

from shenbi.scoring import check_scorer_agreement, flag_score_collapse


@pytest.mark.unit
def test_agreement_pass_when_within_threshold() -> None:
    a = {1: 90, 2: 88, 3: 92}
    b = {1: 92, 2: 90, 3: 95}
    result = check_scorer_agreement(a, b, threshold=5)
    assert result["agreed"] is True
    assert result["max_diff"] == 3


@pytest.mark.unit
def test_agreement_fails_when_diff_exceeds_threshold() -> None:
    a = {1: 90, 2: 70, 3: 92}  # dim 2 diff = 25
    b = {1: 92, 2: 95, 3: 95}
    result = check_scorer_agreement(a, b, threshold=5)
    assert result["agreed"] is False
    assert result["max_diff"] == 25
    assert 2 in result["disputed_dimensions"]


@pytest.mark.unit
def test_collapse_flagged_when_all_exactly_95() -> None:
    scores = {1: 95, 2: 95, 3: 95, 4: 95}
    result = flag_score_collapse(scores)
    assert result["collapse_suspected"] is True
    assert "all_identical" in result["signals"]


@pytest.mark.unit
def test_collapse_not_flagged_when_scores_vary() -> None:
    scores = {1: 88, 2: 92, 3: 85, 4: 90}
    result = flag_score_collapse(scores)
    assert result["collapse_suspected"] is False


@pytest.mark.unit
def test_collapse_flagged_when_majority_95() -> None:
    scores = {1: 95, 2: 95, 3: 95, 4: 88}  # 3/4 = 75% at 95
    result = flag_score_collapse(scores)
    assert result["collapse_suspected"] is True
    assert any("majority_at_single_value" in s for s in result["signals"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_scoring_anti_collapse.py -v`
Expected: FAIL with `ImportError: cannot import name 'check_scorer_agreement'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/shenbi/scoring.py` before `def main()`:

```python


def check_scorer_agreement(
    scores_a: dict[int, Any], scores_b: dict[int, Any], threshold: float = 5.0
) -> dict[str, Any]:
    """Compare two scorers' per-dimension scores (spec §5.5 补丁2).

    Returns dict with:
      - agreed: bool (all dimensions within threshold)
      - max_diff: float (largest per-dimension difference)
      - disputed_dimensions: list[int] (dimensions exceeding threshold)
    """
    disputed: list[int] = []
    max_diff: float = 0.0
    all_dims = set(scores_a.keys()) | set(scores_b.keys())
    for dim in all_dims:
        a = float(scores_a.get(dim, 0))
        b = float(scores_b.get(dim, 0))
        diff = abs(a - b)
        if diff > max_diff:
            max_diff = diff
        if diff > threshold:
            disputed.append(dim)
    return {
        "agreed": len(disputed) == 0,
        "max_diff": round(max_diff, 2),
        "disputed_dimensions": sorted(disputed),
    }


def flag_score_collapse(scores: dict[int, Any]) -> dict[str, Any]:
    """Detect score-collapse signals like all-95 (spec §5.5 补丁3).

    Returns dict with:
      - collapse_suspected: bool
      - signals: list[str] (which collapse pattern was detected)
    """
    signals: list[str] = []
    values = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    if not values:
        return {"collapse_suspected": False, "signals": []}

    if len(set(values)) == 1:
        signals.append("all_identical")

    from collections import Counter
    counts = Counter(values)
    most_common_val, most_common_n = counts.most_common(1)[0]
    if most_common_n / len(values) > 0.6 and len(values) >= 3:
        signals.append(f"majority_at_single_value({most_common_val})")

    return {
        "collapse_suspected": len(signals) > 0,
        "signals": signals,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_scoring_anti_collapse.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/scoring.py tests/unit/test_scoring_anti_collapse.py
git commit -m "feat: add check_scorer_agreement + flag_score_collapse to scoring.py (spec §5.5)"
```

---

### Task 4: escalation — check_escalation + 线性回归斜率

**Files:**
- Create: `src/shenbi/skill_utils/escalation/__init__.py`
- Create: `src/shenbi/skill_utils/escalation/check.py`
- Create: `src/shenbi/skill_utils/escalation/__main__.py`
- Create: `tests/unit/skill_utils/test_escalation.py`

**Interfaces:**
- Consumes: resonance_trend overall 分数序列 + audit 报告（通过函数参数，非文件 I/O，保持纯函数）
- Produces: `detect_score_decline(scores, window, slope_threshold) -> bool` + `check_escalation(signals_input) -> list[EscalationSignal]`（Wave 4 escalation-review 消费）

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/skill_utils/test_escalation.py
"""Unit tests for skill_utils/escalation/check.py (spec §6.2-6.3)."""

from __future__ import annotations

import pytest

from shenbi.skill_utils.escalation.check import (
    EscalationSignal,
    detect_score_decline,
    check_escalation,
)


@pytest.mark.unit
def test_decline_detected_with_clear_downward_trend() -> None:
    # 90, 88, 86, 84, 82 — slope ≈ -2.0 per chapter
    scores = [90.0, 87.0, 84.0, 81.0, 78.0]
    assert detect_score_decline(scores, window=5, slope_threshold=-2.0) is True


@pytest.mark.unit
def test_no_decline_when_scores_stable() -> None:
    scores = [88.0, 90.0, 89.0, 91.0, 88.0]
    assert detect_score_decline(scores, window=5, slope_threshold=-2.0) is False


@pytest.mark.unit
def test_no_decline_when_insufficient_samples() -> None:
    scores = [90.0, 80.0]  # only 2 samples, need 5
    assert detect_score_decline(scores, window=5, slope_threshold=-2.0) is False


@pytest.mark.unit
def test_check_escalation_returns_signal_for_decline() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 87.0, 84.0, 81.0, 78.0],
        sensitivity_blocking=False,
        volume_objective_met=True,
        regeneration_attempts=1,
    )
    assert any(s.trigger == "score_decline" for s in signals)


@pytest.mark.unit
def test_check_escalation_returns_signal_for_sensitivity_blocking() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0],
        sensitivity_blocking=True,
        volume_objective_met=True,
        regeneration_attempts=0,
    )
    assert any(s.trigger == "sensitivity_blocking" for s in signals)


@pytest.mark.unit
def test_check_escalation_returns_signal_for_volume_objective_missed() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0],
        sensitivity_blocking=False,
        volume_objective_met=False,
        regeneration_attempts=0,
    )
    assert any(s.trigger == "volume_objective_missed" for s in signals)


@pytest.mark.unit
def test_check_escalation_returns_signal_for_regeneration_loop() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0],
        sensitivity_blocking=False,
        volume_objective_met=True,
        regeneration_attempts=3,
    )
    assert any(s.trigger == "regeneration_loop_exhausted" for s in signals)


@pytest.mark.unit
def test_check_escalation_returns_signal_for_arc_score_below_70() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0],
        sensitivity_blocking=False,
        volume_objective_met=True,
        regeneration_attempts=0,
        arc_score=65.0,
    )
    assert any(s.trigger == "arc_score_below_threshold" for s in signals)


@pytest.mark.unit
def test_check_escalation_returns_signal_for_stratum_axis_drift() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0],
        sensitivity_blocking=False,
        volume_objective_met=True,
        regeneration_attempts=0,
        stratum_axis_drift=True,
    )
    assert any(s.trigger == "stratum_axis_drift" for s in signals)


@pytest.mark.unit
def test_check_escalation_no_signals_when_all_healthy() -> None:
    signals = check_escalation(
        resonance_scores=[90.0, 90.0, 90.0, 90.0, 90.0],
        sensitivity_blocking=False,
        volume_objective_met=True,
        regeneration_attempts=0,
    )
    assert signals == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/skill_utils/test_escalation.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/skill_utils/escalation/__init__.py
"""escalation package."""
```

```python
# src/shenbi/skill_utils/escalation/check.py
"""check.py — human-escalation trigger detection (spec §6.2-6.3).

Deterministic helper that evaluates escalation conditions for the
auto-approve system. When any condition fires, the orchestrator must
summon human review instead of continuing auto-batch. All triggers are
deterministic: linear-regression slope on raw scores, boolean audit
flags, integer loop counters.

Usage (CLI):
  python -m shenbi.skill_utils.escalation \\
      --resonance-scores 90,88,86,84,82 \\
      --sensitivity-blocking false \\
      --volume-objective-met true \\
      --regeneration-attempts 1
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class EscalationSignal:
    trigger: str
    detail: str


def detect_score_decline(
    scores: list[float], window: int = 5, slope_threshold: float = -2.0
) -> bool:
    """Linear regression slope on last `window` overall scores.

    Returns True if the slope (points per chapter) is steeper downward
    than slope_threshold (i.e. slope < slope_threshold, both negative).
    Requires at least `window` samples; fewer → no trigger.
    """
    recent = scores[-window:]
    if len(recent) < window:
        return False
    n = len(recent)
    x_mean = (n - 1) / 2  # x = 0,1,...,n-1
    y_mean = sum(recent) / n
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return False
    slope = numerator / denominator
    return slope < slope_threshold


def check_escalation(
    resonance_scores: list[float],
    sensitivity_blocking: bool,
    volume_objective_met: bool,
    regeneration_attempts: int,
    arc_score: float | None = None,
    stratum_axis_drift: bool = False,
    window: int = 5,
    slope_threshold: float = -2.0,
    regen_loop_limit: int = 3,
    arc_threshold: float = 70.0,
) -> list[EscalationSignal]:
    """Evaluate all escalation conditions (spec §6.2).

    Returns a list of fired EscalationSignals. Empty list = no escalation.
    """
    signals: list[EscalationSignal] = []

    if detect_score_decline(resonance_scores, window, slope_threshold):
        recent = resonance_scores[-window:]
        signals.append(EscalationSignal(
            trigger="score_decline",
            detail=f"linear regression slope on last {window} scores < {slope_threshold}: {recent}",
        ))

    if sensitivity_blocking:
        signals.append(EscalationSignal(
            trigger="sensitivity_blocking",
            detail="sensitivity audit reported BLOCKING severity",
        ))

    if not volume_objective_met:
        signals.append(EscalationSignal(
            trigger="volume_objective_missed",
            detail="volume Objective not achieved (score-volume binary check)",
        ))

    if regeneration_attempts >= regen_loop_limit:
        signals.append(EscalationSignal(
            trigger="regeneration_loop_exhausted",
            detail=f"same goal unmet after {regeneration_attempts} regeneration attempts (limit {regen_loop_limit})",
        ))

    if arc_score is not None and arc_score < arc_threshold:
        signals.append(EscalationSignal(
            trigger="arc_score_below_threshold",
            detail=f"arc score {arc_score} < {arc_threshold} (spec §6.2)",
        ))

    if stratum_axis_drift:
        signals.append(EscalationSignal(
            trigger="stratum_axis_drift",
            detail="protagonist arc drifted from declared ending (score-stratum detected, spec §6.2)",
        ))

    return signals


def main() -> None:
    """CLI: print escalation signals as JSON."""
    parser = argparse.ArgumentParser(prog="escalation", description="Detect human-escalation triggers (spec §6.2).")
    parser.add_argument("--resonance-scores", required=True, help="Comma-separated overall scores.")
    parser.add_argument("--sensitivity-blocking", default="false", help="true/false.")
    parser.add_argument("--volume-objective-met", default="true", help="true/false.")
    parser.add_argument("--regeneration-attempts", type=int, default=0)
    args = parser.parse_args()

    scores = [float(x) for x in args.resonance_scores.split(",")]
    signals = check_escalation(
        resonance_scores=scores,
        sensitivity_blocking=args.sensitivity_blocking.lower() == "true",
        volume_objective_met=args.volume_objective_met.lower() == "true",
        regeneration_attempts=args.regeneration_attempts,
    )
    print(json.dumps([{"trigger": s.trigger, "detail": s.detail} for s in signals], ensure_ascii=False))
```

```python
# src/shenbi/skill_utils/escalation/__main__.py
"""Standalone runner: python -m shenbi.skill_utils.escalation"""

from shenbi.skill_utils.escalation.check import main

main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/skill_utils/test_escalation.py -v`
Expected: 10 passed (8 original + 2 new escalation triggers)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/skill_utils/escalation/ tests/unit/skill_utils/test_escalation.py
git commit -m "feat: add escalation_check with linear-regression decline detection (spec §6.2-6.3)"
```

---

### Task 5: foreshadowing_recall — recall_overdue_hooks

**Files:**
- Create: `src/shenbi/skill_utils/foreshadowing_recall/__init__.py`
- Create: `src/shenbi/skill_utils/foreshadowing_recall/recall.py`
- Create: `src/shenbi/skill_utils/foreshadowing_recall/__main__.py`
- Create: `tests/unit/skill_utils/test_foreshadowing_recall.py`

**Interfaces:**
- Consumes: hook 列表（`list[dict]`，每个含 id/last_reinforced/max_distance）
- Produces: `recall_overdue_hooks(hooks, current_chapter) -> list[str]`（Wave 2 foreshadowing-recall skill + review-foreshadowing 改造调用）

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/skill_utils/test_foreshadowing_recall.py
"""Unit tests for skill_utils/foreshadowing_recall/recall.py (spec §3.6)."""

from __future__ import annotations

import pytest

from shenbi.skill_utils.foreshadowing_recall.recall import recall_overdue_hooks


@pytest.mark.unit
def test_overdue_hook_returned() -> None:
    hooks = [
        {"id": "H01", "last_reinforced": 60, "max_distance": 20},  # silence=6 < 20, NOT overdue
        {"id": "H02", "last_reinforced": 50, "max_distance": 15},  # silence=16 > 15, overdue
    ]
    overdue = recall_overdue_hooks(hooks, current_chapter=66)
    assert "H02" in overdue
    assert "H01" not in overdue


@pytest.mark.unit
def test_non_overdue_hooks_excluded() -> None:
    hooks = [
        {"id": "H01", "last_reinforced": 60, "max_distance": 20},  # 66-60=6 < 20
        {"id": "H02", "last_reinforced": 55, "max_distance": 20},  # 66-55=11 < 20
    ]
    assert recall_overdue_hooks(hooks, current_chapter=66) == []


@pytest.mark.unit
def test_resolved_hooks_excluded() -> None:
    hooks = [
        {"id": "H01", "last_reinforced": 3, "max_distance": 20, "state": "RESOLVED"},
    ]
    assert recall_overdue_hooks(hooks, current_chapter=66) == []


@pytest.mark.unit
def test_multiple_overdue_returned() -> None:
    hooks = [
        {"id": "H01", "last_reinforced": 1, "max_distance": 10},
        {"id": "H02", "last_reinforced": 40, "max_distance": 15},
        {"id": "H03", "last_reinforced": 60, "max_distance": 20},
    ]
    overdue = recall_overdue_hooks(hooks, current_chapter=66)
    assert set(overdue) == {"H01", "H02"}


@pytest.mark.unit
def test_empty_hooks_returns_empty() -> None:
    assert recall_overdue_hooks([], current_chapter=100) == []


@pytest.mark.unit
def test_hook_without_max_distance_skipped() -> None:
    hooks = [{"id": "H01", "last_reinforced": 1}]  # no max_distance
    assert recall_overdue_hooks(hooks, current_chapter=100) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/skill_utils/test_foreshadowing_recall.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/skill_utils/foreshadowing_recall/__init__.py
"""foreshadowing_recall package."""
```

```python
# src/shenbi/skill_utils/foreshadowing_recall/recall.py
"""recall.py — deterministic overdue-hook filtering (spec §3.6).

This helper wraps the RAG recall layer's final deterministic filter.
The RAG layer (benchmarks/index/) retrieves candidate hooks by semantic
similarity; this function applies the deterministic max_distance
threshold to decide which are genuinely overdue. The threshold check
is pure arithmetic: (current_chapter - last_reinforced) > max_distance.
This keeps the final judgment deterministic regardless of embedding
fluctuations.

Hook dict schema:
    {"id": str,
     "last_reinforced": int,
     "max_distance": int,
     "state": str (optional, e.g. "PLANTED"/"RELEVANT"/"RESOLVED")}

Usage (CLI):
  python -m shenbi.skill_utils.foreshadowing_recall \\
      --hooks-json '[{"id":"H01","last_reinforced":3,"max_distance":20}]' \\
      --current-chapter 66
"""

from __future__ import annotations

import argparse
import json


def recall_overdue_hooks(hooks: list[dict], current_chapter: int) -> list[str]:
    """Return hook_ids whose silence exceeds max_distance (spec §3.6).

    Excludes RESOLVED hooks and hooks without max_distance.
    """
    overdue: list[str] = []
    for hook in hooks:
        state = hook.get("state", "PLANTED")
        if state == "RESOLVED":
            continue
        last_reinforced = hook.get("last_reinforced")
        max_distance = hook.get("max_distance")
        if last_reinforced is None or max_distance is None:
            continue
        silence = current_chapter - last_reinforced
        if silence > max_distance:
            overdue.append(hook["id"])
    return overdue


def main() -> None:
    """CLI: print overdue hook IDs as JSON."""
    parser = argparse.ArgumentParser(prog="foreshadowing_recall", description="Filter overdue hooks (spec §3.6).")
    parser.add_argument("--hooks-json", required=True, help="JSON array of hook dicts.")
    parser.add_argument("--current-chapter", type=int, required=True)
    args = parser.parse_args()
    hooks = json.loads(args.hooks_json)
    overdue = recall_overdue_hooks(hooks, args.current_chapter)
    print(json.dumps(overdue))
```

```python
# src/shenbi/skill_utils/foreshadowing_recall/__main__.py
"""Standalone runner: python -m shenbi.skill_utils.foreshadowing_recall"""

from shenbi.skill_utils.foreshadowing_recall.recall import main

main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/skill_utils/test_foreshadowing_recall.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/skill_utils/foreshadowing_recall/ tests/unit/skill_utils/test_foreshadowing_recall.py
git commit -m "feat: add recall_overdue_hooks deterministic filter (spec §3.6)"
```

---

### Task 6: lock-tool-hashes.sh — 全树扫描

**Files:**
- Modify: `tests/lock-tool-hashes.sh` (替换 tool_paths 列举为全树扫描)

- [ ] **Step 1: Run current lock script to capture baseline**

Run: `bash tests/lock-tool-hashes.sh`
Expected: prints 5 hashes, "Done."

- [ ] **Step 2: Modify script to scan full tree**

Replace the `tool_paths = [...]` block in `tests/lock-tool-hashes.sh` with a full-tree scan:

```bash
# In the first python -c block, replace:
#   tool_paths = ['src/shenbi/gates/cli.py', ...]
# with:
tool_paths = [
    str(p.relative_to(project))
    for p in (project / 'src' / 'shenbi').rglob('*.py')
    if '__pycache__' not in str(p)
]
```

- [ ] **Step 3: Run modified script**

Run: `bash tests/lock-tool-hashes.sh`
Expected: prints hashes for ALL .py files under src/shenbi/ (including new skill_utils/* helpers), "Done."

- [ ] **Step 4: Verify deps.json updated correctly**

Run: `python3 -c "import json; d=json.load(open('tests/tiers/deps.json')); print(len(d['_tool_hashes']), 'files locked'); print('revision_routing' in str(d['_tool_hashes']))"`
Expected: count > 5 (includes new helpers), True

- [ ] **Step 5: Verify deps.json updated correctly**

`_tool_hashes` is a committed-state lock with **no runtime gate** (G0.13 is the independence-marker check, G0.14 is calibration hashes — neither verifies tool hashes). The lock's enforcement is `just check` (which runs tests that read deps.json) and `git diff` inspection. Verify the file is valid JSON:

Run: `python3 -c "import json; d=json.load(open('tests/tiers/deps.json')); print(len(d['_tool_hashes']), 'files locked')"`
Expected: count includes new helper files (revision_routing, escalation, foreshadowing_recall, scoring.py)

- [ ] **Step 6: Commit**

```bash
git add tests/lock-tool-hashes.sh tests/tiers/deps.json
git commit -m "chore: lock-tool-hashes.sh scans full src/shenbi tree (spec §9.4)"
```

---

### Task 7: 全量验证 + 覆盖率

- [ ] **Step 1: Run all new unit tests**

Run: `uv run pytest tests/unit/skill_utils/test_revision_routing.py tests/unit/skill_utils/test_escalation.py tests/unit/skill_utils/test_foreshadowing_recall.py tests/unit/test_scoring_anti_collapse.py -v`
Expected: all passed (5+4+8+6+5 = 28 tests)

- [ ] **Step 2: Run fast test suite**

Run: `just test`
Expected: all passed, no regressions

- [ ] **Step 3: Run full check suite**

Run: `just check`
Expected: all passed (lint, type-check, coverage ≥90%)

- [ ] **Step 4: Verify CLI runners work**

Run:
```bash
echo '{"issues":[]}' | python3 -c "import sys,json; from shenbi.skill_utils.revision_routing.route import route_revision; print(route_revision(json.load(sys.stdin)))"
uv run python -m shenbi.skill_utils.escalation --resonance-scores 90,85,80,75,70 --sensitivity-blocking false --volume-objective-met true --regeneration-attempts 0
uv run python -m shenbi.skill_utils.foreshadowing_recall --hooks-json '[{"id":"H01","last_reinforced":1,"max_distance":10}]' --current-chapter 50
```
Expected: `spot-fix`; JSON array with score_decline signal; `["H01"]`

- [ ] **Step 5: Re-lock hashes after all changes**

Run: `bash tests/lock-tool-hashes.sh`
Expected: Done, all src/shenbi/*.py files locked

- [ ] **Step 6: Commit lock update**

```bash
git add tests/tiers/deps.json
git commit -m "chore: re-lock tool hashes after Wave 1 helper additions"
```

---

## Wave 2-4 预告（后续计划）

本计划仅覆盖 Wave 1（基础 helpers）。后续波次的计划文件：

- `2026-06-28-hierarchical-system-wave2-memory.md`：book-spine-init, memory-distill, context-composing 改造, foreshadowing-recall skill, G0.10 动态化
- `2026-06-28-hierarchical-system-wave3-scoring.md`：anchor-curate, review-resonance 改造, score-arc, score-volume, score-stratum
- `2026-06-28-hierarchical-system-wave4-loop-approval.md`：chapter-revision 改造（重生路由 + preserve_check）, 审批节点改造, escalation-review skill

每个后续波次依赖前一波的产出（接口在本计划的 Task "Interfaces" 块中声明）。
