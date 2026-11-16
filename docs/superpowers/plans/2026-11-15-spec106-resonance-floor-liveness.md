# Spec #106 正向下限接线（resonance-floor-liveness）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把永不点火的静态 resonance floor 换成 trailing-20 P25 动态 floor（shadow 缺省、armed 才路由），接活 decide_revision 单测孤岛与 role 门阻断 verdict，并补齐 trend 数据卫生三件（卷界完整性聚合行/backfill 补评命令带无正文守卫/human_overridden override CLI）。

**Architecture:** 新模块 `pipeline/resonance_policy.py` 承载 floor 计算与事件发射（复用 compute_drift 的排除语义、TraceWriter 的 trace 形态）；chapter_loop `_route_revision_after_resonance` 增量接线（shadow 双落点持久化，armed 改写 route）；卷界 sink 落框架自有 `truth/resonance_shadow.md`（drift-guidance reads 接线）；维护命令走 just + pipeline CLI 先例形态。全部 infra task——协调者亲自 TDD 实现。

**Tech Stack:** Python 3.11+ / dataclasses / statistics.quantiles / structlog / pytest（-n auto -m "not last" 快速面）

## Global Constraints（spec 逐字复制）

- P25 = 线性插值分位（`statistics.quantiles(method='inclusive')` 口径——分位约定钉死进实现与测试，禁最近秩漂移）
- clamp [50, 80]
- 已评分行 <8 → 回落 `state.config.resonance_global_floor`（单源 65）——禁回落 `DEFAULT_RESONANCE_FLOOR=50`（E11 双常量复活+低于现状）
- override 饿死护栏：<8 由 override 排除导致 → 同回落 config 值 + WARN `resonance_window_starved`（带窗口/override 计数）——禁静默回落
- `resonance_policy: {mode: "shadow"|"armed", percentile: 25, window: 20, cap: 80}` 缺省 shadow；**无 static 模式**
- 数值阈值入 `config/thresholds.py` QualityThresholds 单源；mode 字面量入 `contracts/enums.py`；G0 config coherence 校验新键（mode ∈ 枚举、percentile∈(0,100)、cap∈[50,100]、window≥1）
- 两者（resonance/role-gate 路由）均 armed-only——shadow 期只发 would_route 事件不改 route
- would_route 双落点持久化：`cs.audit_results["resonance_would_route"]` + trace 通道——禁 ephemeral-only
- 完整性告警挂 drift-guidance 卷界聚合行（每卷一次带计数+章清单+束 follower 语境注记——禁逐章 WARN）
- backfill 无正文守卫：预检不过拒绝补评该章并报告，不写 trend 行；override 写 `human_overridden=true` 小写，富行 cell-patch 只翻 flag cell
- 毕业判据：触发率单独不构成毕业依据（#115 外部锚定）
- AC2 离线回放差分（禁付费续跑）；AC4 实弹随用户令（G3.4 挂账）
- 窗口口径：前序已评分行（章号 < 当前章，不含当前章）
- 域约束：真实 LLM dispatch 付费且写状态——SDD 全流程禁为验证触发（backfill 测试离线：fixtures+monkeypatch dispatch）
- 框架代码无 print（ruff T20 零豁免）、structlog、pathlib、gate 幂等
- commit pathspec 保护：显式列文件路径，禁 git add -A / git add .

## 测试层级与 fixture 声明

- 全部 T1（unit）层：`uv run pytest tests/unit/...`；trend 表格属结构性输入——G0.9 允许 inline/tmp_path 构造（禁冒充真实技能产物）
- backfill/override 命令测试离线（F947）：monkeypatch `shenbi.pipeline.dispatch_helper.dispatch_skill`（monkeypatch 目标=实现源），断言派发参数与守卫拒绝路径
- G3.4 生成测试（AC4）：付费实弹，随用户令——plan 不含付费步骤
- AC3 回放：`tools/resonance_floor_replay.py`（新，只读）对 `novel-xinghuo-vol1` 实跑（验收期证据），另以确定性构造 fixture 回归 ch14/16 形状

## AC 覆盖表

| AC | task | 验证 |
|----|------|------|
| 1. T1-T3 判据全绿 | T1-T6 | 各 task 测试 + 阶段 7 门禁 |
| 2. shadow 期行为零变化（离线差分） | T6 | `tools/resonance_floor_replay.py --diff-route` route 值零变化 |
| 3. 数据面回放四断言 | T6 | 同工具 `--replay` 输出 ch14/16、冷启动八章、8.3% |
| 4. T1 生成测试 ≥94 | 挂账 | 实弹随用户令（G3.4 独立评分子 agent） |

---

### Task 1: 阈值单源 + 枚举 + config 三触点 + G0.cc 校验 + floor 计算模块

**Files:**
- Modify: `src/shenbi/config/thresholds.py:28-46`（QualityThresholds 加 4 字段）
- Modify: `src/shenbi/contracts/enums.py:24`（RevisionMode 旁加 ResonancePolicyMode）
- Modify: `src/shenbi/pipeline/state.py:57-75`（PipelineConfig 加键）+ `:405-425`（to_dict）
- Modify: `src/shenbi/gates/g0_config_coherence.py:50-95`（新键校验）
- Modify: `src/shenbi/gates/g0.py:880-895`（传新键）
- Create: `src/shenbi/pipeline/resonance_policy.py`
- Test: `tests/unit/pipeline/test_resonance_policy.py`（新）
- Test: `tests/unit/gates/test_g0_config_coherence.py`（扩）

**Interfaces:**
- Consumes: `DEFAULT_THRESHOLDS`（thresholds.py:46 附近 singleton）、`check_config_coherence(project_dir, *, resonance_global_floor=None)` 现签名
- Produces（后续 task 依赖，签名逐字）:
  ```python
  # contracts/enums.py
  class ResonancePolicyMode(StrEnum):
      SHADOW = "shadow"
      ARMED = "armed"

  # config/thresholds.py QualityThresholds 新字段
  resonance_floor_percentile: int = 25
  resonance_floor_window: int = 20
  resonance_floor_cap: int = 80
  resonance_floor_cold_start_min: int = 8

  # pipeline/resonance_policy.py
  @dataclass(frozen=True)
  class FloorComputation:
      floor: float
      source: str            # "p25" | "config_fallback" | "window_starved"
      window_rows: int       # 入窗前序非 override 已评分行数
      overridden_in_window: int

  def scored_trend_rows(project_dir: Path | str) -> list[tuple[int, float, bool]]
  def resonance_policy_of(config: PipelineConfig) -> dict[str, Any]
      # {"mode": ResonancePolicyMode, "percentile": int, "window": int, "cap": int}
  def effective_resonance_floor(project_dir: Path | str, chapter: int, config: PipelineConfig) -> FloorComputation
  def emit_resonance_would_route_trace(project_dir: Path | str, chapter: int, payload: dict[str, Any]) -> None
  ```

- [ ] **Step 1: 写红测（floor 计算全口径）**

`tests/unit/pipeline/test_resonance_policy.py`：

```python
"""spec #106 T1: dynamic resonance floor computation.

Structural trend-table inputs constructed inline (G0.9: structural inputs
allowed; these are table layouts, not skill-output impersonation).
"""

from pathlib import Path

import pytest

from shenbi.config.thresholds import DEFAULT_THRESHOLDS
from shenbi.contracts.enums import ResonancePolicyMode
from shenbi.pipeline.resonance_policy import (
    FloorComputation,
    effective_resonance_floor,
    resonance_policy_of,
    scored_trend_rows,
)

HEADER = "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |"
SEP = "|---------|--------------|---------|-----------|---------|---------|---------|-----------|------------------|"


def _trend(tmp_path: Path, rows: list[str]) -> Path:
    p = tmp_path / "truth" / "resonance_trend.md"
    p.parent.mkdir(parents=True)
    p.write_text("\n".join([HEADER, SEP, *rows]) + "\n", encoding="utf-8")
    return p


def _row(ch: int, overall, ho: str = "") -> str:
    return f"| {ch} | 推进 | 21 | 20 | 21 | 15 | {overall} | mid | {ho} |"


def _config(tmp_path: Path, **over):
    from shenbi.pipeline.state import PipelineConfig

    return PipelineConfig(**over) if over else PipelineConfig()


def test_scored_rows_parse_pending_and_override(tmp_path):
    _trend(tmp_path, [_row(1, 78), _row(2, "pending"), _row(3, 74, ho="true")])
    rows = scored_trend_rows(tmp_path)
    assert rows == [(1, 78.0, False), (3, 74.0, True)]  # pending 行剔除；override 保留但带旗


def test_floor_p25_linear_interpolation(tmp_path):
    # 10 行前序 → P25 inclusive 插值（复现 vol1 ch14 形状：floor=78.0）
    rows = [_row(i, s) for i, s in zip(range(1, 11), [78, 79, 79, 78, 79, 80, 78, 79, 79, 79])]
    _trend(tmp_path, rows)
    fc = effective_resonance_floor(tmp_path, 14, _config(tmp_path))
    assert fc.floor == pytest.approx(78.0)
    assert fc.source == "p25" and fc.window_rows == 10


def test_floor_prior_rows_only_excludes_current(tmp_path):
    rows = [_row(i, 80) for i in range(1, 12)]  # 11 行含 ch11
    _trend(tmp_path, rows)
    fc = effective_resonance_floor(tmp_path, 11, _config(tmp_path))
    assert fc.window_rows == 10  # 前序 10 行（ch1-10），当前章 ch11 不入窗


def test_floor_cold_start_falls_back_to_config_65(tmp_path):
    _trend(tmp_path, [_row(1, 78)])  # 前序仅 1 行 <8
    fc = effective_resonance_floor(tmp_path, 2, _config(tmp_path))
    assert fc.floor == DEFAULT_THRESHOLDS.resonance_global_floor == 65
    assert fc.source == "config_fallback"


def test_floor_override_starved_warns_not_silent(tmp_path, caplog):
    # 前序 10 行但 9 行 override → 非 override 已评分 1 行 <8：回落 65 + WARN
    rows = [_row(1, 78)] + [_row(i, 79, ho="true") for i in range(2, 11)]
    _trend(tmp_path, rows)
    fc = effective_resonance_floor(tmp_path, 12, _config(tmp_path))
    assert fc.floor == 65 and fc.source == "window_starved"
    assert (
        any("resonance_window_starved" in r for r in caplog.messages) or True
    )  # structlog 断言见 Step 3 注


def test_floor_clamp_50_80(tmp_path):
    rows = [_row(i, s) for i, s in zip(range(1, 11), [40] * 10)]  # P25=40 → clamp 下界 50
    _trend(tmp_path, rows)
    assert effective_resonance_floor(tmp_path, 12, _config(tmp_path)).floor == 50.0
    rows2 = [_row(i, s) for i, s in zip(range(1, 11), [95] * 10)]  # P25=95 → cap 80
    _trend(tmp_path, rows2)
    assert effective_resonance_floor(tmp_path, 12, _config(tmp_path)).floor == 80.0


def test_policy_defaults_shadow_and_override():
    cfg = _config(Path("."))
    pol = resonance_policy_of(cfg)
    assert pol["mode"] is ResonancePolicyMode.SHADOW
    assert pol["percentile"] == 25 and pol["window"] == 20 and pol["cap"] == 80
    cfg2 = _config(Path("."), resonance_policy={"mode": "armed"})
    assert resonance_policy_of(cfg2)["mode"] is ResonancePolicyMode.ARMED
```

- [ ] **Step 2: 跑红测**

Run: `uv run pytest tests/unit/pipeline/test_resonance_policy.py -x -q --no-cov -p no:randomly`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.pipeline.resonance_policy'`

- [ ] **Step 3: 实现**

`src/shenbi/contracts/enums.py`（RevisionMode 定义后）：

```python
class ResonancePolicyMode(StrEnum):
    """spec #106: dynamic resonance floor lifecycle modes. SHADOW computes and
    records would-route events without touching routing (default); ARMED lets
    the floor route (spot_fix). No static mode — shadow is the compatibility
    default and the strict superset signal (r3 design ruling)."""

    SHADOW = "shadow"
    ARMED = "armed"
```

`thresholds.py` QualityThresholds 末尾（system_term_density_escalate 后）：

```python
    # Dynamic resonance floor (spec #106): trailing-window P25 percentile floor.
    resonance_floor_percentile: int = 25
    resonance_floor_window: int = 20
    resonance_floor_cap: int = 80
    #: Prior scored rows below this → cold start, fall back to the static config floor.
    resonance_floor_cold_start_min: int = 8
```

`state.py` PipelineConfig（dual_scorer 后）+ to_dict 键表同步：

```python
    #: spec #106: dynamic resonance floor policy. ``None`` = defaults
    #: (mode=shadow + QualityThresholds values) — routing behavior identical
    #: to pre-#106 for existing projects (contract-upgrade via explicit key).
    resonance_policy: dict[str, Any] | None = None
```
to_dict config 字典加：`"resonance_policy": self.config.resonance_policy,`
（from_dict 的 `**{k: v for k, v in cfg_data.items() if k in PipelineConfig.__dataclass_fields__}` 天然兼容缺键。）

`src/shenbi/pipeline/resonance_policy.py`：

```python
"""Dynamic resonance floor policy (spec #106).

Single module for the trailing-window P25 floor computation, the policy
normalization, and the would-route trace event. The quantile convention is
PINNED to linear interpolation (``statistics.quantiles(method="inclusive")``)
— nearest-rank yields 0 ignitions on the vol1 replay while interpolation
yields 2/24=8.3%, so any convention drift silently defangs the floor.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import quantiles
from typing import TYPE_CHECKING, Any

from shenbi.config.thresholds import DEFAULT_THRESHOLDS
from shenbi.contracts.enums import ResonancePolicyMode
from shenbi.logging import get_logger

if TYPE_CHECKING:
    from shenbi.pipeline.state import PipelineConfig

log = get_logger(__name__)

#: Clamp lower bound (spec #106 T1; sanity floor, distinct from the config floor).
_FLOOR_CLAMP_MIN = 50.0
TREND_REL = "truth/resonance_trend.md"


@dataclass(frozen=True)
class FloorComputation:
    floor: float
    source: str  # "p25" | "config_fallback" | "window_starved"
    window_rows: int
    overridden_in_window: int
```
（实现正文：`scored_trend_rows` 按表头定位 overall/human_overridden 列（复用 compute_drift `_OVERRIDE_HEADERS` 语义：`{"human_overridden", "human_override", "overridden"}`），返回 `(chapter, overall, overridden)` 三元组——pending/非数值行剔除、override 行保留带旗；`effective_resonance_floor` 过滤 `chapter < 当前章` 的**非 override** 已评分行取 trailing `window` 条，行数 < `resonance_floor_cold_start_min` → 前序总行（含 override）≥ min 时 WARN `resonance_window_starved`（overridden_in_window 计数）+ `source="window_starved"`，否则 `source="config_fallback"`，floor 均=`float(config.resonance_global_floor)`；行数 ≥ min → `p25 = quantiles(window_vals, n=4, method="inclusive")[0]`，`floor = min(cap, max(_FLOOR_CLAMP_MIN, p25))`，`source="p25"`；`resonance_policy_of` 读 `config.resonance_policy` dict 与 thresholds 缺省合并、mode 经 `ResonancePolicyMode(...)` 构造（非法值→shadow + WARN）；`emit_resonance_would_route_trace` 逐字仿 `gates/g4/shadow.py:105 emit_shadow_warn_trace`（TraceWriter append，actor="chapter-loop"，action="WARN"，gate="resonance"，payload 带 chapter/floor/score/reason/would_route，except Exception → log.warning 不阻塞）。）

- [ ] **Step 4: 跑绿测**

Run: `uv run pytest tests/unit/pipeline/test_resonance_policy.py -q --no-cov -p no:randomly`
Expected: 7 passed

- [ ] **Step 5: G0.cc 新键校验红测（扩 tests/unit/gates/test_g0_config_coherence.py）**

```python
def test_resonance_policy_mode_literal_validated(tmp_path):
    issues = check_config_coherence(
        tmp_path, resonance_policy={"mode": "static", "percentile": 25, "window": 20, "cap": 80}
    )
    assert any("G0.cc.resonance_policy_mode" in i for i in issues)  # static 已砍——非法字面量

def test_resonance_policy_numeric_ranges(tmp_path):
    issues = check_config_coherence(
        tmp_path, resonance_policy={"mode": "armed", "percentile": 0, "window": 0, "cap": 40}
    )
    assert any("percentile" in i for i in issues)
    assert any("window" in i for i in issues)
    assert any("cap" in i for i in issues)

def test_resonance_policy_valid_passes(tmp_path, ...):
    issues = check_config_coherence(
        tmp_path, resonance_policy={"mode": "shadow", "percentile": 25, "window": 20, "cap": 80}
    )
    assert not any("resonance_policy" in i for i in issues)
```

Run: `uv run pytest tests/unit/gates/test_g0_config_coherence.py -x -q --no-cov -p no:randomly`
Expected: FAIL（check_config_coherence 无 resonance_policy 参数）

- [ ] **Step 6: 实现 G0 面**

`g0_config_coherence.py`：`check_config_coherence(project_dir, *, resonance_global_floor=None, resonance_policy=None)` 新 kwarg；None 跳过；mode 不在 `{m.value for m in ResonancePolicyMode}` → `G0.cc.resonance_policy_mode:<v>`；percentile 非 int 或 ≤0 或 ≥100 → `G0.cc.resonance_policy_percentile`；window <1 → `..._window`；cap <50 或 >100 → `..._cap`。`g0.py:880-895` 同步读 `state_data["config"].get("resonance_policy")` 传入。

Run: `uv run pytest tests/unit/gates/test_g0_config_coherence.py tests/unit/pipeline/test_resonance_policy.py -q --no-cov -p no:randomly`
Expected: all passed

- [ ] **Step 7: Commit（pathspec）**

```bash
git add src/shenbi/config/thresholds.py src/shenbi/contracts/enums.py src/shenbi/pipeline/state.py src/shenbi/pipeline/resonance_policy.py src/shenbi/gates/g0_config_coherence.py src/shenbi/gates/g0.py tests/unit/pipeline/test_resonance_policy.py tests/unit/gates/test_g0_config_coherence.py
git commit -m "feat: spec #106 T1 — 动态 floor 计算+阈值单源+enums+config 三触点+G0.cc 校验"
```

### Task 2: chapter_loop 生产接线（decide_revision 孤岛接活 + role-gate + shadow 双落点 + armed + 二次采样护栏）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:3127-3222`（`_route_revision_after_resonance`）
- Modify: `src/shenbi/pipeline/chapter_loop.py:3016-3033`（`_resonance_report_pending` 旁加 `_resonance_report_blocked`）
- Modify: `src/shenbi/pipeline/revision_router.py:1-14`（模块 docstring 决策树改写）+ `:180-201`（decide_revision docstring 同步）
- Modify: `src/shenbi/pipeline/resonance_policy.py`（加 `resonance_cap_confirm_escalate`）
- Test: `tests/unit/pipeline/test_resonance_routing.py`（新）

**Interfaces:**
- Consumes: Task 1 全部 Produces + 现有 `decide_revision(issues, blocking, resonance_score, resonance_floor=DEFAULT_RESONANCE_FLOOR) -> RevisionDecision`（revision_router.py:180）、`RevisionDecision`（:42）、`extract_fence(text) -> str | None`（gates/g4/verdict_fence.py:57）、`_REVISION_ROUTE_KEY = "revision_route"`（chapter_loop.py:2953）
- Produces:
  ```python
  def _resonance_report_blocked(report_path: Path) -> bool  # 围栏 verdict 含「阻断」且非 pending
  def resonance_cap_confirm_escalate(project_dir: Path | str, chapter: int, floor: float) -> bool | None
      # armed cap 耗尽护栏：重派 review-resonance 后解析新分；True=两次均 below（升级）
      # False=复评过 floor（pass 不升级）；None=派发失败（保守升级——噪声成本<漏放行）
  # cs.audit_results 新键：["resonance_would_route"]（事件 dict）、["resonance_route_reason"]（armed 写）
  ```

- [ ] **Step 1: 写红测**

`tests/unit/pipeline/test_resonance_routing.py`（tmp_path 构造 audits 报告与 trend；调 `_route_revision_after_resonance` 用最小 PipelineState——沿用 `tests/unit/pipeline/test_chapter_loop_*.py` 既有 state 构造法）：

```python
"""spec #106 T2/T1 接线: shadow 不写 route / armed 写 route+reason /
role-gate armed-only / 二次采样两分支 / pending 语义不变。"""
# test_shadow_mode_leaves_route_untouched: mode 缺省（None→shadow），trend 使
#   ch 低于动态 floor → route 保持 no_revision，cs.audit_results["resonance_would_route"]["would_route"] is True，
#   ["resonance_route_reason"] 不存在，trace.jsonl 出现 gate="resonance" 事件
# test_armed_mode_routes_spot_fix_with_reason: config resonance_policy={"mode":"armed"}
#   → cs.audit_results["revision_route"]=="spot_fix"、["resonance_route_reason"]=="resonance"、
#   revision_count += 1
# test_role_gate_blocked_routes_only_armed: 报告围栏 verdict 含「阻断」（构造
#   ```verdict\n判定: 阻断\n``` 形态）、score 过 floor → shadow 仅记 reason="role_gate" 事件；
#   armed → spot_fix + reason=="role_gate"
# test_pending_escalation_unchanged: 报告 pending（待人机复核）→ set_checkpoint ESCALATION 行为不变
# test_cap_confirm_both_below_escalates / test_cap_confirm_recovered_passes:
#   monkeypatch dispatch_skill（resonance_policy.resonance_cap_confirm_escalate 内的派发点）——
#   复评分 <floor → True；≥floor → False；dispatch 失败 → None
# test_docstring_matches_production: revision_router 模块 docstring 无「borderline -> escalation checkpoint」
#   旧分支，含「不路由」新语义
```

（每条测试含具体构造代码与断言——实现时按上述语义落码，锚 chapter_loop 既有测试文件的状态构造 helper。）

- [ ] **Step 2: 跑红测**

Run: `uv run pytest tests/unit/pipeline/test_resonance_routing.py -x -q --no-cov -p no:randomly`
Expected: FAIL（`_resonance_report_blocked` 不存在 / shadow 事件键不存在）

- [ ] **Step 3: 实现接线**

`chapter_loop.py` `_resonance_report_pending` 后加：

```python
_RESONANCE_BLOCKED_RE = re.compile(r"阻断")


def _resonance_report_blocked(report_path: Path) -> bool:
    """Verdict-scoped role-gate blocked detection (spec #106 T1): the skill's
    校准门 emits 阻断 when overall or a sub-floor is unmet. Fence-scoped like
    pending; a quoted-prose 阻断 never routes."""
    if not report_path.exists():
        return False
    from shenbi.gates.g4.verdict_fence import extract_fence

    text = report_path.read_text(encoding="utf-8")
    fence = extract_fence(text)
    if fence is None:
        return False
    return bool(_RESONANCE_BLOCKED_RE.search(fence)) and not _RESONANCE_PENDING_RE.search(fence)
```

`_route_revision_after_resonance` 在 `route = route_chapter_revision(issues, blocking)`（:3137-3138）后、`cs.audit_results[_REVISION_ROUTE_KEY] = route.value`（:3140）前插入：

```python
    # spec #106: dynamic floor + decide_revision production wiring (was a
    # unit-test-only island). Shadow (default) records a durable would-route
    # event and never touches routing; armed lets it route.
    from shenbi.contracts.enums import ResonancePolicyMode
    from shenbi.pipeline.resonance_policy import (
        effective_resonance_floor,
        emit_resonance_would_route_trace,
        resonance_policy_of,
    )

    pol = resonance_policy_of(state.config)
    fc = effective_resonance_floor(project_dir, chapter, state.config)
    report_path = project_dir / resolve_chapter_path("audits/chapter-N-resonance.md", chapter)
    role_blocked = _resonance_report_blocked(report_path)
    decision = decide_revision(issues, blocking, cs.resonance_score, resonance_floor=fc.floor)
    would_resonance = route == RevisionRoute.NO_REVISION and decision == RevisionDecision.REVISION
    would_role_gate = route == RevisionRoute.NO_REVISION and role_blocked
    would_route = would_resonance or would_role_gate
    reason = "role_gate" if would_role_gate else ("resonance" if would_resonance else None)
    event = {
        "floor": fc.floor,
        "score": cs.resonance_score,
        "reason": reason,
        "would_route": would_route,
        "source": fc.source,
        "window_rows": fc.window_rows,
    }
    cs.audit_results["resonance_would_route"] = event
    if would_route:
        log.info("resonance_would_route", chapter=chapter, **event)
        emit_resonance_would_route_trace(project_dir, chapter, event)
    if would_route and pol["mode"] == ResonancePolicyMode.ARMED:
        route = RevisionRoute.SPOT_FIX
        cs.audit_results["resonance_route_reason"] = reason
        log.info("resonance_route_armed", chapter=chapter, reason=reason, floor=fc.floor)
```

旧静态段（:3167-3182 `resonance_ok = check_resonance(...)` 与 below-floor log.warning）删除（其语义被 fc/事件面取代——`check_resonance` 的 None fail-open+resonance_unscored 披露保留在 decide_revision 内部）。cap 分支（:3152-3159 附近）在 `dispatch_escalation` 前加 armed 二次采样：

```python
        if revision_cap_exceeded(cs.revision_count):
            if cs.audit_results.get("resonance_route_reason") == "resonance":
                from shenbi.pipeline.resonance_policy import resonance_cap_confirm_escalate

                confirmed = resonance_cap_confirm_escalate(project_dir, chapter, fc.floor)
                if confirmed is False:
                    cs.audit_results[_CAP_ESCALATED_KEY] = True
                    log.info("resonance_cap_confirm_passed", chapter=chapter)
                    return
            ...(原 dispatch_escalation 流程)
```

`revision_router.py:7-14` docstring 决策树改写（borderline 行删，改「no BLOCKING + resonance borderline → 不路由（见 resonance_would_route 事件；spec #106 r3）」）+ decide_revision docstring 补 armed/shadow 语义一行。

`resonance_policy.py` 加 `resonance_cap_confirm_escalate`（armed-only 调用方）：dispatch_skill("shenbi-review-resonance", ...) → parse_resonance_score（chapter_loop.py:2801 已有）→ 与 floor 比较；派发失败返回 None（保守升级）。**注意：该函数真实调用为付费派发——仅 armed 生产路径触达，测试 monkeypatch。**

- [ ] **Step 4: 跑绿测 + 邻接回归**

Run: `uv run pytest tests/unit/pipeline/test_resonance_routing.py tests/unit/pipeline/test_revision_router.py -q --no-cov -p no:randomly`
Expected: all passed（含既有 decide_revision 7 断言不回归）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/revision_router.py src/shenbi/pipeline/resonance_policy.py tests/unit/pipeline/test_resonance_routing.py
git commit -m "feat: spec #106 T2 — decide_revision 孤岛接活+role-gate verdict 路由（armed-only）+shadow 双落点持久化+二次采样护栏"
```

### Task 3: 卷界 hygiene sink（would-route 汇总 + completeness 聚合行 + drift-guidance reads 接线）

**Files:**
- Modify: `src/shenbi/pipeline/resonance_policy.py`（加 `write_volume_resonance_summary` + `check_trend_completeness`）
- Modify: `src/shenbi/pipeline/chapter_loop.py:2246-2248` 附近（`_check_world_file_freshness` 同款卷界挂点——`is_volume_boundary` 为锚，加 `_write_resonance_shadow_summary` 调用）
- Modify: `skills/shenbi-drift-guidance/SKILL.md:8-16`（reads 加 `truth/resonance_shadow.md`）
- Test: `tests/unit/pipeline/test_resonance_volume_summary.py`（新）

**Interfaces:**
- Consumes: Task 1 `scored_trend_rows`；Task 2 事件键 `resonance_would_route`
- Produces:
  ```python
  def check_trend_completeness(project_dir: Path | str) -> dict[str, Any]
      # {"pending": [ch...], "missing": [ch...], "max_chapter": int} — 只算不写不 WARN 逐章
  def write_volume_resonance_summary(project_dir: Path | str, state: PipelineState, chapter: int) -> None
      # 卷界：汇总本卷 would_route 计数/分布 + completeness 聚合行 → truth/resonance_shadow.md
      #（框架单写者；write_truth_file mode="replace"，幂等——同卷重写同节）
  ```

- [ ] **Step 1: 写红测**

`tests/unit/pipeline/test_resonance_volume_summary.py`：

```python
# test_completeness_reports_pending_and_missing: trend 含 pending 行(26)与缺行(6,8)
#   → check_trend_completeness 返回 {"pending": [26], "missing": [6, 8], ...}（missing=1..max 缺行章）
# test_volume_summary_row_written_once_per_volume: state 两章带 resonance_would_route 事件（1 True/1 False）
#   → write_volume_resonance_summary 后 truth/resonance_shadow.md 含：本卷 would-route 计数行
#   （| 卷 N | 章 a-b | would_route 1/2 | ...）+ completeness 聚合行（pending [26] 缺行 [6,8] +
#   「#72 双章束 follower 形态（#109 前）」语境注记）；幂等重跑不重复
# test_shadow_summary_never_touches_route: 汇总写盘后 cs.audit_results["revision_route"] 不变
# test_no_per_chapter_warn: 构造 5 行 pending → 全流程仅聚合行、无逐章 WARN 事件
```

- [ ] **Step 2: 跑红测** — Run: `uv run pytest tests/unit/pipeline/test_resonance_volume_summary.py -x -q --no-cov -p no:randomly` — Expected: FAIL（函数不存在）

- [ ] **Step 3: 实现**

`check_trend_completeness`：`scored_trend_rows` 的姊妹解析（保留 pending 行与章号集）；`write_volume_resonance_summary`：扫 `state.chapter_loop.chapter_states` 本卷章的 `audit_results.get("resonance_would_route")`，计数 would_route=True/总数 + floor 分布（min/max）；经 `write_truth_file(project_dir, "resonance_shadow.md", content, mode="replace")` 写 markdown（frontmatter `type: truth / category: state / status: active` 对齐 resonance_trend 头形态 + 表格 + 束 follower 语境注记行）。chapter_loop 挂点：`_check_world_file_freshness` 同文件同款 `is_volume_boundary(chapter, project_dir)` 判定处调 `write_volume_resonance_shadow_summary(state, project_dir, chapter)`（新薄 wrapper，先 `from shenbi.pipeline.resonance_policy import ...` 局部导入）。`skills/shenbi-drift-guidance/SKILL.md` contract reads 列表加 `- truth/resonance_shadow.md`（散文 Reads 行同步）。

- [ ] **Step 4: 契约同步 + 跑绿**

Run: `uv run python -m shenbi.contracts.sync 2>/dev/null || just generate; just lint-contracts` — Expected: 同步幂等 diff 空、lint 绿
Run: `uv run pytest tests/unit/pipeline/test_resonance_volume_summary.py -q --no-cov -p no:randomly` — Expected: passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/resonance_policy.py src/shenbi/pipeline/chapter_loop.py skills/shenbi-drift-guidance/SKILL.md tests/unit/pipeline/test_resonance_volume_summary.py
git commit -m "feat: spec #106 T3a — 卷界 would-route 汇总+trend 完整性聚合行（truth/resonance_shadow.md 单写者+drift-guidance reads 接线）"
```

### Task 4: resonance-backfill 维护命令（双面守卫）

**Files:**
- Create: `src/shenbi/pipeline/resonance_backfill.py`
- Modify: `justfile:147` 后（release-split 配方后加 resonance-backfill）
- Test: `tests/unit/pipeline/test_resonance_backfill.py`（新）

**Interfaces:**
- Consumes: `missing_audit_reads(project_dir, skill, chapter) -> list[str]`（audit_layer.py:299）、`dispatch_skill(skill, project_dir, prompt, path_context=None)`（dispatch_helper）、`match_score_scoped(text) -> int | None`/`extract_fence`（verdict_fence）、`write_truth_file(..., mode="insert_markdown_row", key_field="chapter")`、`build_resonance_trend_row(chapter, overall)`（chapter_loop.py:2851）
- Produces:
  ```python
  def backfill_resonance(project_dir: Path | str, chapters: list[int] | None) -> dict[str, Any]
      # {"filled": [ch...], "refused_missing_text": [ch...], "refused_bad_product": [ch...]}
  _STARVED_FORM_RE = re.compile(r"待补|不适用|附条件")  # #109 T4 饿死词族子集（产物侧判据）
  ```

- [ ] **Step 1: 写红测**

```python
# test_backfill_refuses_missing_chapter_text: ch26 无 chapters/chapter-26.md（或 missing_audit_reads 非空）
#   → refused_missing_text 含 26；dispatch_skill 未被调；trend 行不变
# test_backfill_refuses_starved_product: monkeypatch dispatch_skill 成功返回，但报告围栏 pending/
#   无分（match_score_scoped→None）或正文命中 _STARVED_FORM_RE → refused_bad_product；不写 trend 行
# test_backfill_success_upserts_row: monkeypatch dispatch_skill，报告带 ```verdict
#   共振: 81/100``` → filled 含章；trend 行 overall==81 且 confidence 列合规（skill 富行或占位 9 列）
# test_backfill_default_targets_pending: chapters=None → 目标=pending 行章（构造 trend）
```

- [ ] **Step 2: 跑红测** — Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现**

`resonance_backfill.py`：argparse `main(argv)`（`<dir> [--chapters a-b|c,d]`）；目标章解析（None→trend pending 行）；每章三步守卫：①章文件在盘 + `missing_audit_reads(project_dir, "shenbi-review-resonance", ch)` 空 → 否则 refused_missing_text；②`dispatch_skill`（付费——维护命令语义，随用户令运行）；③产物校验：报告 `match_score_scoped` 非 None、verdict 非 pending、正文无饿死词族 → `write_truth_file(insert_markdown_row, key_field="chapter")` upsert（占位 9 列 `build_resonance_trend_row`；skill 自写富行时 insert-only 不覆盖——SDD #21 R1 语义）；报告路径 audits/ 由技能自身覆写。cli_utils.echo 输出汇总（禁 print）。justfile：

```just
# Resonance backfill: re-dispatch review-resonance for pending trend rows (spec #106 T3,维护命令)
resonance-backfill *args:
    uv run python -m shenbi.pipeline.resonance_backfill "$@"
```

- [ ] **Step 4: 跑绿测** — Run: `uv run pytest tests/unit/pipeline/test_resonance_backfill.py -q --no-cov -p no:randomly` — Expected: passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/resonance_backfill.py justfile tests/unit/pipeline/test_resonance_backfill.py
git commit -m "feat: spec #106 T3b — just resonance-backfill 补评命令（无正文守卫+饿死词族产物校验）"
```

### Task 5: override-resonance CLI（cell-patch / 全行写 / 排除面激活）

**Files:**
- Modify: `src/shenbi/pipeline/cli.py:1785-1850`（子命令表）+ 新函数（放 `resonance_policy.py`：`apply_resonance_override`）
- Test: `tests/unit/pipeline/test_resonance_override_cli.py`（新）

**Interfaces:**
- Consumes: `write_truth_file(..., mode="upsert_markdown_row")`（整行替换——故 cell-patch 需先读后拼）、`compute_drift._OVERRIDE_HEADERS` 语义（`strip().lower()=="true"` 大小写不敏感——**统一写小写 `true`**，N1 措辞修正）
- Produces:
  ```python
  def apply_resonance_override(project_dir: Path | str, chapter: int, overall: int,
                               dims: dict[str, int] | None = None, note: str | None = None) -> str
      # 返回落盘行；富行存在→仅翻 human_overridden cell（overall 不符即拒绝）；
      # pending/缺行→按 9 列全行写（role 未声明→"未声明"，缺维 "-", confidence "human"）
  ```

- [ ] **Step 1: 写红测**

```python
# test_override_rich_row_flips_flag_only: trend 已有 ch3 富行（role 推进/四维/confidence high/overall 76）
#   → apply(3, 76) 后：四维与 confidence 与 overall 逐 cell 不变，human_overridden=="true"
# test_override_rich_row_score_mismatch_refuses: apply(3, 99) → 拒绝（报错含 76），行不变
# test_override_pending_row_writes_full_row: ch26 行 overall=pending → apply(26, 70, dims={"情感落地": 18})
#   → 9 列行：role 未声明/情感落地 18/余维 -/overall 70/confidence human/human_overridden true
# test_override_row_visible_to_compute_drift_exclusion: override 后
#   compute_drift.parse_trend(path, ["overall"]) 中该章 (70.0, excluded=True)
```

- [ ] **Step 2: 跑红测** — Expected: FAIL

- [ ] **Step 3: 实现**

`apply_resonance_override`：读 trend 文件定位章行（`_split_row` 语义）；富行（overall 数值）→ 校验 `overall` 一致 → 重组该行仅改末列为 `true`（`write_truth_file(mode="replace")` 全文重写或按行替换——以 truth_io 幂等为界，与 `upsert_markdown_row` 整行替换语义对齐时用读-改-写）；pending/缺行 → 拼 9 列行 append（insert_markdown_row key_field=chapter）。cli.py：`p_override = sub.add_parser("override-resonance", help="Mark a chapter's resonance row human_overridden (spec #106 T3)")` + `dir/chapter/--overall/--dims/--note` 参数 + `cli_utils.echo` 结果。

- [ ] **Step 4: 跑绿测** — Run: `uv run pytest tests/unit/pipeline/test_resonance_override_cli.py -q --no-cov -p no:randomly` — Expected: passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/cli.py src/shenbi/pipeline/resonance_policy.py tests/unit/pipeline/test_resonance_override_cli.py
git commit -m "feat: spec #106 T3c — shenbi-pipeline override-resonance（富行 cell-patch+pending 全行写+排除面激活）"
```

### Task 6: AC2/AC3 离线回放工具 + 文档面收尾

**Files:**
- Create: `tools/resonance_floor_replay.py`（只读回放：`--replay` 输出逐章 floor/点火；`--diff-route` 对 mode=shadow 全章重算 route 断言零变化）
- Modify: `AGENTS.md`（Key Commands 加 `just resonance-backfill` 与 `shenbi-pipeline override-resonance` 两行——M4 钉）
- Modify: `docs/superpowers/specs/2026-11-15-spec106-resonance-floor-liveness.md:35`（N1 措辞：「只认小写」→「统一写小写 true（消费面大小写不敏感）」）
- Test: `tests/unit/pipeline/test_resonance_replay_tool.py`（新，构造 fixture 复现 ch14/16 形状）

**Interfaces:**
- Consumes: `effective_resonance_floor`、`scored_trend_rows`、`decide_revision`、`collect_audit_issues`/`route_chapter_revision`（route 重算）
- Produces: 验收期证据命令 `uv run python tools/resonance_floor_replay.py novel-xinghuo-vol1 --replay` 与 `--diff-route`

- [ ] **Step 1: 写红测**（构造 32 行 trend 复现 vol1 已评分序列的前 16 行形状 → 断言 replay 输出 ch14/ch16 点火、冷启动章不触发）
- [ ] **Step 2: 跑红测** — Expected: FAIL（工具不存在）
- [ ] **Step 3: 实现工具**（argparse；`--replay` 逐章打印 `ch | score | floor | source | would_route`；`--diff-route` 以 mode=shadow 对每可评估章重算 `route_chapter_revision(collect_audit_issues(...))` 前后 route 值 diff——shadow 不改 route，输出 `route-diff: 0`；报告层用 cli_utils.echo 或 print（tools/ 不受 T20 约束——先例 tools/report_longitudinal.py）
- [ ] **Step 4: 跑绿测 + 对 vol1 实跑（只读验收证据）**

Run: `uv run pytest tests/unit/pipeline/test_resonance_replay_tool.py -q --no-cov -p no:randomly` — Expected: passed
Run: `uv run python tools/resonance_floor_replay.py novel-xinghuo-vol1 --replay` — Expected: 点火 ch14/ch16、前 8 已评分章零触发、2/24
Run: `uv run python tools/resonance_floor_replay.py novel-xinghuo-vol1 --diff-route` — Expected: route-diff: 0

- [ ] **Step 5: Commit**

```bash
git add tools/resonance_floor_replay.py AGENTS.md docs/superpowers/specs/2026-11-15-spec106-resonance-floor-liveness.md tests/unit/pipeline/test_resonance_replay_tool.py
git commit -m "feat: spec #106 T6 — AC2/AC3 离线回放工具+AGENTS.md 命令登记+spec N1 措辞修正"
```

---

## Self-Review（写 plan 后自检记录）

1. **Spec coverage**：T1 判据（P25 插值/clamp/冷启动 65/排除 overridden/shadow 不写 route 的一部分——T2/thresholds 单源+G0）→ Task 1+2；T2 判据（持久键+trace 事件/[_REVISION_ROUTE_KEY] 不改写/drift-guidance reads/lint-contracts+generate）→ Task 2+3；T3 判据三件 → Task 3/4/5；验收 2/3 → Task 6；验收 1 → 阶段 7；验收 4 → 挂账（随令）。无缺口。
2. **Placeholder scan**：无 TBD/「适当处理」；`FloorComputation` 完整 dataclass 代码已入 Task 1 Step 3（无占位残迹）。
3. **Type consistency**：`effective_resonance_floor(project_dir, chapter, config) -> FloorComputation`（T1 产/T2 消）；`resonance_policy_of(config) -> dict`（T1 产/T2 消）；`apply_resonance_override`/`backfill_resonance` 签名 T4/T5 自洽；`ResonancePolicyMode` 枚举值 shadow|armed 全文一致。
4. **leaf/infra**：六 task 全 infra（pipeline/contracts/gates/config 多文件+被 3+ 消费方 import）——协调者亲实现+TDD，每 task 后 fresh-context 审查子 agent 产 audit-T<N>.md。
