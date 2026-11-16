# Spec #106 正向下限接线（resonance-floor-liveness）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把永不点火的静态 resonance floor 换成 trailing-20 P25 动态 floor（shadow 缺省、armed 才路由），接活 decide_revision 单测孤岛与 role 门阻断 verdict，并补齐 trend 数据卫生三件（卷界完整性聚合行/backfill 补评命令带无正文守卫/human_overridden override CLI）。

**Architecture:** 新模块 `pipeline/resonance_policy.py` 承载 floor 计算与事件发射（复用 compute_drift 的排除语义、TraceWriter 的 trace 形态）；chapter_loop `_route_revision_after_resonance` 增量接线（shadow 双落点持久化，armed 改写 route）；卷界 sink 落框架自有 `truth/resonance_shadow.md`（truth-files.yaml 登记 + drift-guidance reads 接线）；维护命令走 just + 既有 `pipeline` console-script 入口。全部 infra task——协调者亲自 TDD 实现。

**Tech Stack:** Python 3.11+ / dataclasses / statistics.quantiles / structlog（capsys 断言惯用法）/ pytest（-n auto -m "not last" 快速面）

**执行分支**：`fix/spec-106-resonance-floor-liveness`（GO 时已建——本 plan 全部 commit 落此分支；禁直推 main）。

## Global Constraints（spec 逐字复制）

- P25 = 线性插值分位（`statistics.quantiles(method='inclusive')` 口径——分位约定钉死进实现与测试，禁最近秩漂移）
- clamp [50, 80]
- 已评分行 <8 → 回落 `state.config.resonance_global_floor`（单源 65）——禁回落 `DEFAULT_RESONANCE_FLOOR=50`（E11 双常量复活+低于现状）
- override 饿死护栏：<8 由 override 排除导致 → 同回落 config 值 + WARN `resonance_window_starved`（带窗口/override 计数）——禁静默回落
- `resonance_policy: {mode: "shadow"|"armed", percentile: 25, window: 20, cap: 80}` 缺省 shadow；**无 static 模式**
- 数值阈值入 `config/thresholds.py` QualityThresholds 单源；mode 字面量入 `contracts/enums.py`（+ ALL_ENUMS + status-vocab.md 域行登记）；G0 config coherence 校验新键（mode ∈ 枚举、percentile∈(0,100)、cap∈[50,100]、window≥1）
- 两者（resonance/role-gate 路由）均 armed-only——shadow 期只发 would_route 事件不改 route
- would_route 双落点持久化：`cs.audit_results["resonance_would_route"]` + trace 通道——禁 ephemeral-only
- 完整性告警挂 drift-guidance 卷界聚合行（每卷一次带计数+章清单+束 follower 语境注记——禁逐章 WARN）
- backfill 无正文守卫：预检不过拒绝补评该章并报告，不写 trend 行；override 写 `human_overridden=true` 小写（消费面大小写不敏感，写小写双侧安全），富行 cell-patch 只翻 flag cell
- 毕业判据：触发率单独不构成毕业依据（#115 外部锚定）
- AC2 离线回放差分（禁付费续跑）；AC4 实弹随用户令（G3.4 挂账）
- 窗口口径：前序已评分行（章号 < 当前章，不含当前章）
- 域约束：真实 LLM dispatch 付费且写状态——SDD 全流程禁为验证触发（backfill/二次采样测试离线：monkeypatch `shenbi.pipeline.dispatch_helper.dispatch_skill`，两新模块以**函数级局部 import** 消费之——绑定在调用时解析，patch 源模块即生效）
- 框架代码无 print（ruff T20 零豁免，src/shenbi/）、structlog、pathlib、gate 幂等；tools/ 脚本 print 有先例（report_longitudinal.py）
- commit pathspec 保护：显式列文件路径，禁 git add -A / git add .

## 测试层级与 fixture 声明

- 全部 T1（unit）层：`uv run pytest tests/unit/...`；trend 表格属结构性输入——G0.9 允许 inline/tmp_path 构造（禁冒充真实技能产物）
- 回放 fixture 数值钉死 vol1 真值序列（ch1-13 已评分 `[78,74,76,78,79,79,80,79,81,79]`，inclusive Q1=78.0——合成序列 `[78,79,79,78,…]` 的 inclusive Q1=78.25 会反向奖励最近秩实现）
- G3.4 生成测试（AC4）：付费实弹，随用户令——plan 不含付费步骤；未获令时 AC4 以 T6 离线差分替代交付（挂账用户裁定）
- AC3 回放：`tools/resonance_floor_replay.py`（新，只读）对 `novel-xinghuo-vol1` 实跑（验收期证据）

## AC 覆盖表

| AC | task | 验证 |
|----|------|------|
| 1. T1-T3 判据全绿 | T1-T6 | 各 task 测试 + 阶段 7 门禁 |
| 2. shadow 期行为零变化（离线差分） | T6 | `tools/resonance_floor_replay.py --diff-route`（**同快照代码级差分**：对每可评估章以旧表达式 `route_chapter_revision(collect_audit_issues(...))` vs 新接线（shadow 模式）各算一遍 route，断言逐章相等——饿死审计产物对两侧是同一输入、只影响 would_route 事件字段，diff 恒 0 才是被测断言；**不对 pipeline-state.json 历史 route 对账**——复评覆写+饿死混杂会产生与 #106 无关的假 diff） |
| 3. 数据面回放四断言 | T6 | 同工具 `--replay`：冷启动八章零触发/ch14+ch16 点火/众数 79 不命中/2/24=8.3% |
| 4. T1 生成测试 ≥94 | 挂账（随令） | 实弹随用户令；T6 离线差分为未获令时的替代交付 |

---

### Task 1: 阈值单源 + 枚举登记 + config 三触点 + G0.cc 校验 + floor 计算模块

**Files:**
- Modify: `src/shenbi/config/thresholds.py:28-46`（QualityThresholds 加 4 字段）
- Modify: `src/shenbi/contracts/enums.py:24`（RevisionMode 后加 ResonancePolicyMode）+ `:81`（ALL_ENUMS 加条目）
- Modify: `docs/framework/status-vocab.md:35`（域清单加一行——`mode` 在 lint_status_strings STRICT_TREE_KEYS，state.json 落 `"mode": "shadow"` 前必须登记）
- Modify: `src/shenbi/pipeline/state.py:57-75`（PipelineConfig 加键）+ `:405-425`（to_dict）
- Modify: `src/shenbi/gates/g0_config_coherence.py:50-95`（新键校验）
- Modify: `src/shenbi/gates/g0.py:880-895`（传新键）
- Create: `src/shenbi/pipeline/resonance_policy.py`
- Test: `tests/unit/pipeline/test_resonance_policy.py`（新）
- Test: `tests/unit/gates/test_g0_config_coherence.py`（扩）

**Interfaces:**
- Consumes: `DEFAULT_THRESHOLDS`（thresholds.py）、`check_config_coherence(project_dir, *, resonance_global_floor=None)` 现签名
- Produces（后续 task 依赖，签名逐字）:
  ```python
  # contracts/enums.py
  class ResonancePolicyMode(StrEnum):
      SHADOW = "shadow"
      ARMED = "armed"
  # enums.py ALL_ENUMS 追加: "ResonancePolicyMode": ResonancePolicyMode,
  # status-vocab.md 域清单追加一行:
  # | ResonancePolicyMode | shenbi.contracts.enums.ResonancePolicyMode | shadow\|armed | pipeline/state.py config（resonance_policy.mode） | chapter_loop 路由面、g0_config_coherence |

  # config/thresholds.py QualityThresholds 新字段（resonance_revision_trigger 块后）
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
allowed; these are table layouts, not skill-output impersonation). Replay
values are PINNED to the real vol1 scored sequence (ch1-13) so the
interpolation convention is asserted against ground truth — a synthetic
sequence would reward the forbidden nearest-rank convention.
"""

from pathlib import Path

import pytest

from shenbi.config.thresholds import DEFAULT_THRESHOLDS
from shenbi.contracts.enums import ResonancePolicyMode
from shenbi.pipeline.resonance_policy import (
    effective_resonance_floor,
    resonance_policy_of,
    scored_trend_rows,
)

HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
    " | overall | confidence | human_overridden |"
)
SEP = (
    "|---------|--------------|---------|-----------|---------|---------"
    "|---------|-----------|------------------|"
)
#: vol1 truth: ch1-13 scored rows (ch6/8/10 missing; ch11/12/13 = 79/81/79)
VOL1_FIRST13 = [78, 74, 76, 78, 79, 79, 80, 79, 81, 79]


def _trend(tmp_path: Path, rows: list[str]) -> Path:
    p = tmp_path / "truth" / "resonance_trend.md"
    p.parent.mkdir(parents=True)
    p.write_text("\n".join([HEADER, SEP, *rows]) + "\n", encoding="utf-8")
    return p


def _row(ch: int, overall, ho: str = "") -> str:
    return f"| {ch} | 推进 | 21 | 20 | 21 | 15 | {overall} | mid | {ho} |"


def _config(**over):
    from shenbi.pipeline.state import PipelineConfig

    return PipelineConfig(**over) if over else PipelineConfig()


def test_scored_rows_parse_pending_and_override(tmp_path):
    _trend(tmp_path, [_row(1, 78), _row(2, "pending"), _row(3, 74, ho="true")])
    rows = scored_trend_rows(tmp_path)
    assert rows == [(1, 78.0, False), (3, 74.0, True)]  # pending 剔除；override 保留带旗


def test_floor_p25_linear_interpolation_vol1_truth(tmp_path):
    # vol1 ch1-13 前序 10 行 → inclusive Q1 = 78.0（ch14 实弹 floor 逐字复现）
    rows = [_row(ch, s) for ch, s in zip([1, 2, 3, 4, 5, 7, 9, 11, 12, 13], VOL1_FIRST13)]
    _trend(tmp_path, rows)
    fc = effective_resonance_floor(tmp_path, 14, _config())
    assert fc.floor == pytest.approx(78.0)
    assert fc.source == "p25" and fc.window_rows == 10


def test_floor_prior_rows_only_excludes_current(tmp_path):
    rows = [_row(i, 80) for i in range(1, 12)]  # 11 行含 ch11
    _trend(tmp_path, rows)
    fc = effective_resonance_floor(tmp_path, 11, _config())
    assert fc.window_rows == 10  # 前序 ch1-10 入窗；当前章 ch11 不入窗


def test_floor_cold_start_falls_back_to_config_65(tmp_path):
    _trend(tmp_path, [_row(1, 78)])  # 前序仅 1 行 <8
    fc = effective_resonance_floor(tmp_path, 2, _config())
    assert fc.floor == float(DEFAULT_THRESHOLDS.resonance_global_floor) == 65.0
    assert fc.source == "config_fallback"


def test_floor_override_starved_warns_not_silent(tmp_path, capsys):
    from shenbi.logging import configure_logging

    configure_logging()
    # 前序 10 行但 9 行 override → 非 override 已评分 1 行 <8：回落 65 + WARN
    rows = [_row(1, 78)] + [_row(i, 79, ho="true") for i in range(2, 11)]
    _trend(tmp_path, rows)
    fc = effective_resonance_floor(tmp_path, 12, _config())
    assert fc.floor == 65.0 and fc.source == "window_starved"
    assert fc.overridden_in_window == 9
    assert "resonance_window_starved" in capsys.readouterr().err


def test_floor_clamp_50_80(tmp_path):
    rows = [_row(i, 40) for i in range(1, 11)]  # P25=40 → clamp 下界 50
    _trend(tmp_path, rows)
    assert effective_resonance_floor(tmp_path, 12, _config()).floor == 50.0
    rows2 = [_row(i, 95) for i in range(1, 11)]  # P25=95 → cap 80
    _trend(tmp_path, rows2)
    assert effective_resonance_floor(tmp_path, 12, _config()).floor == 80.0


def test_policy_defaults_shadow_and_override():
    pol = resonance_policy_of(_config())
    assert pol["mode"] is ResonancePolicyMode.SHADOW
    assert pol["percentile"] == 25 and pol["window"] == 20 and pol["cap"] == 80
    pol2 = resonance_policy_of(_config(resonance_policy={"mode": "armed"}))
    assert pol2["mode"] is ResonancePolicyMode.ARMED
    # 非法 mode 值降级 shadow（fail-safe：绝不 armed by accident）
    pol3 = resonance_policy_of(_config(resonance_policy={"mode": "yolo"}))
    assert pol3["mode"] is ResonancePolicyMode.SHADOW
```

- [ ] **Step 2: 跑红测**

Run: `uv run pytest tests/unit/pipeline/test_resonance_policy.py -x -q --no-cov -p no:randomly`
Expected: FAIL with `ImportError: cannot import name 'ResonancePolicyMode'`（enums 先于 resonance_policy 命中）

- [ ] **Step 3: 实现**

`src/shenbi/contracts/enums.py`（RevisionMode 后）：

```python
class ResonancePolicyMode(StrEnum):
    """spec #106: dynamic resonance floor lifecycle modes. SHADOW computes and
    records would-route events without touching routing (default); ARMED lets
    the floor route (spot-fix). No static mode — shadow is the compatibility
    default and the strict-superset signal (r3 design ruling)."""

    SHADOW = "shadow"
    ARMED = "armed"
```
ALL_ENUMS（:81 dict）追加 `"ResonancePolicyMode": ResonancePolicyMode,`。

`docs/framework/status-vocab.md` 域清单表追加：
```
| ResonancePolicyMode | shenbi.contracts.enums.ResonancePolicyMode | shadow\|armed | pipeline/state.py config（resonance_policy.mode） | chapter_loop 路由面、g0_config_coherence |
```

`thresholds.py` QualityThresholds（resonance_revision_trigger 块后）：

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
#: Override-header family — same semantics as compute_drift._OVERRIDE_HEADERS
#: (spec #106 reuses its exclusion filter, values compared case-insensitively).
_OVERRIDE_HEADERS = ("human_overridden", "human_override", "overridden")


@dataclass(frozen=True)
class FloorComputation:
    floor: float
    source: str  # "p25" | "config_fallback" | "window_starved"
    window_rows: int
    overridden_in_window: int
```
（实现正文：`scored_trend_rows` 按表头定位 overall 列与 override 列，返回 `(chapter, overall, overridden)` 三元组——pending/非数值行剔除、override 行保留带旗（chapter 列解析为 int，非数值行整行跳过）；`effective_resonance_floor` 过滤 `chapter < 当前章` 的**非 override** 已评分行取 trailing `window` 条——行数 < `resonance_floor_cold_start_min` 时，若前序总行（含 override）≥ min 则 `source="window_starved"` + `log.warning("resonance_window_starved", window_rows=…, overridden_in_window=…)`，否则 `source="config_fallback"`，floor 均 = `float(config.resonance_global_floor)`；行数 ≥ min → `p25 = quantiles(window_vals, n=4, method="inclusive")[0]`，`floor = min(cap, max(_FLOOR_CLAMP_MIN, p25))`，`source="p25"`；`resonance_policy_of` 读 `config.resonance_policy or {}` 与 thresholds 缺省合并，mode 经 try `ResonancePolicyMode(v)` 构造、非法值 → SHADOW + WARN `resonance_policy_mode_invalid`；`emit_resonance_would_route_trace` 逐字仿 `gates/g4/shadow.py:105 emit_shadow_warn_trace`（TraceWriter append，actor="chapter-loop"，actor_role="SYSTEM"，action="WARN"，target=f"ch{chapter}"，gate="resonance"，payload 带 chapter/floor/score/reason/would_route，except Exception → log.warning `resonance_trace_emit_failed` 不阻塞）。）

- [ ] **Step 4: 跑绿测**

Run: `uv run pytest tests/unit/pipeline/test_resonance_policy.py -q --no-cov -p no:randomly`
Expected: 7 passed

- [ ] **Step 5: G0.cc 新键校验红测（扩 tests/unit/gates/test_g0_config_coherence.py）**

```python
class TestResonancePolicyCoherence:
    def test_mode_literal_validated(self, tmp_path):
        issues = check_config_coherence(
            tmp_path,
            resonance_policy={"mode": "static", "percentile": 25, "window": 20, "cap": 80},
        )
        assert any("G0.cc.resonance_policy_mode" in i for i in issues)  # static 已砍——非法字面量

    def test_numeric_ranges(self, tmp_path):
        issues = check_config_coherence(
            tmp_path,
            resonance_policy={"mode": "armed", "percentile": 0, "window": 0, "cap": 40},
        )
        assert any("G0.cc.resonance_policy_percentile" in i for i in issues)
        assert any("G0.cc.resonance_policy_window" in i for i in issues)
        assert any("G0.cc.resonance_policy_cap" in i for i in issues)

    def test_valid_policy_passes(self, tmp_path):
        issues = check_config_coherence(
            tmp_path,
            resonance_policy={"mode": "shadow", "percentile": 25, "window": 20, "cap": 80},
        )
        assert not any("resonance_policy" in i for i in issues)

    def test_none_skips(self, tmp_path):
        assert check_config_coherence(tmp_path, resonance_policy=None) == check_config_coherence(
            tmp_path
        )
```

Run: `uv run pytest tests/unit/gates/test_g0_config_coherence.py -x -q --no-cov -p no:randomly`
Expected: FAIL（`check_config_coherence() got an unexpected keyword argument 'resonance_policy'`）

- [ ] **Step 6: 实现 G0 面**

`g0_config_coherence.py`：`check_config_coherence(project_dir, *, resonance_global_floor=None, resonance_policy=None)` 新 kwarg；None 跳过；mode 不在 `{m.value for m in ResonancePolicyMode}` → `G0.cc.resonance_policy_mode:<v>`；percentile 非 int 或 ≤0 或 ≥100 → `G0.cc.resonance_policy_percentile:<v>`；window 非 int 或 <1 → `..._window`；cap 非 int 或 <50 或 >100 → `..._cap`。`g0.py:880-895` 同步读 `state_data["config"].get("resonance_policy")` 传入。

Run: `uv run pytest tests/unit/gates/test_g0_config_coherence.py tests/unit/pipeline/test_resonance_policy.py -q --no-cov -p no:randomly`
Expected: all passed（status-vocab 对账 lint 由 `just check` 阶段 7 全量兜底）

- [ ] **Step 7: Commit（pathspec）**

```bash
git add src/shenbi/config/thresholds.py src/shenbi/contracts/enums.py docs/framework/status-vocab.md src/shenbi/pipeline/state.py src/shenbi/pipeline/resonance_policy.py src/shenbi/gates/g0_config_coherence.py src/shenbi/gates/g0.py tests/unit/pipeline/test_resonance_policy.py tests/unit/gates/test_g0_config_coherence.py
git commit -m "feat: spec #106 T1 — 动态 floor 计算+阈值单源+enums/status-vocab 登记+config 三触点+G0.cc 校验"
```

### Task 2: chapter_loop 生产接线（decide_revision 孤岛接活 + role-gate + shadow 双落点 + armed + 二次采样护栏）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:3016-3033`（`_resonance_report_pending` 旁加 `_resonance_report_blocked`）
- Modify: `src/shenbi/pipeline/chapter_loop.py:3128-3222`（`_route_revision_after_resonance` 接线+删旧静态段 :3172-3182）
- Modify: `src/shenbi/pipeline/chapter_loop.py:73`（模块 import 块：`check_resonance` 删——删段后成孤儿，ruff F401）
- Modify: `src/shenbi/pipeline/revision_router.py:1-14`（模块 docstring 决策树改写）+ `:180-201`（decide_revision docstring 同步）
- Modify: `src/shenbi/pipeline/resonance_policy.py`（加 `resonance_cap_confirm_escalate`——双报告保全）
- Modify: `tests/unit/pipeline/test_parallel_wave_resonance.py:110-115`（既有 `resonance_below_floor` stderr 断言改为 would_route 事件断言）
- Test: `tests/unit/pipeline/test_resonance_routing.py`（新）

**Interfaces:**
- Consumes: Task 1 全部 Produces + `decide_revision(issues, blocking, resonance_score, resonance_floor=DEFAULT_RESONANCE_FLOOR) -> RevisionDecision`（revision_router.py:180，**接线处函数级局部 import**）、`RevisionDecision`（:42）、`extract_fence(text) -> str | None`（gates/g4/verdict_fence.py:57）、`_REVISION_ROUTE_KEY = "revision_route"`（chapter_loop.py:2953）、`RevisionRoute.SPOT_FIX.value == "spot-fix"`（连字符）
- Produces:
  ```python
  def _resonance_report_blocked(report_path: Path) -> bool
      # 围栏 verdict 含「阻断」且非 pending 且非否定形（无阻断）
  def resonance_cap_confirm_escalate(project_dir: Path | str, chapter: int, floor: float) -> bool | None
      # armed cap 护栏：先把首份 below 报告复制为 audits/chapter-N-resonance-first.md
      # （重派会覆写原报告——升级审阅须见双报告，spec「升级带双报告」），再函数级局部
      # import dispatch_skill 重派 review-resonance，解析新分与 floor 比较。
      # True=两次均 below（升级）；False=复评 ≥floor（pass）；None=派发失败（保守升级）
  # cs.audit_results 新键：["resonance_would_route"]（事件 dict）、
  #   ["resonance_route_reason"]（armed 写）、["resonance_cap_confirmed"]（一次性采样守卫）
  ```

- [ ] **Step 1: 写红测**

`tests/unit/pipeline/test_resonance_routing.py`：

```python
"""spec #106 T2 接线: shadow 不写 route / armed 写 route+reason /
role-gate armed-only / cap 二次采样两分支 / pending 语义不变。"""

from pathlib import Path
from types import SimpleNamespace

from shenbi.contracts.enums import RevisionMode
from shenbi.pipeline.chapter_loop import _route_revision_after_resonance
from shenbi.pipeline.state import ChapterState, PipelineConfig, PipelineState

TREND_HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
    " | overall | confidence | human_overridden |"
)
TREND_SEP = (
    "|---------|--------------|---------|-----------|---------|---------"
    "|---------|-----------|------------------|"
)
BLOCKED_REPORT = """# 共鸣评审

```verdict
判定: 阻断
共振: 88/100
```
"""


def _make_state(policy: dict | None = None) -> PipelineState:
    state = PipelineState(config=PipelineConfig(resonance_policy=policy))
    state.chapter_loop.chapter_states["14"] = ChapterState(resonance_score=42)
    return state


def _seed_project(tmp_path: Path, *, report: str | None, with_trend: bool = True) -> None:
    audits = tmp_path / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    if report is not None:
        (audits / "chapter-14-resonance.md").write_text(report, encoding="utf-8")
    if with_trend:
        truth = tmp_path / "truth"
        truth.mkdir(parents=True, exist_ok=True)
        rows = [
            f"| {c} | 推进 | 21 | 20 | 21 | 15 | {s} | mid |  |"
            for c, s in zip([1, 2, 3, 4, 5, 7, 9, 11, 12, 13],
                            [78, 74, 76, 78, 79, 79, 80, 79, 81, 79])
        ]
        (truth / "resonance_trend.md").write_text(
            "\n".join([TREND_HEADER, TREND_SEP, *rows]) + "\n", encoding="utf-8")


def _no_issues(monkeypatch):
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.collect_audit_issues", lambda *a, **k: ([], False)
    )


def test_shadow_mode_leaves_route_untouched(tmp_path, monkeypatch, capsys):
    from shenbi.logging import configure_logging

    configure_logging()
    _seed_project(tmp_path, report=None, with_trend=True)  # score=42 < floor 78.0
    state = _make_state(policy=None)  # 缺省 shadow
    _no_issues(monkeypatch)
    _route_revision_after_resonance(state, tmp_path, 14)
    cs = state.chapter_loop.chapter_states["14"]
    assert cs.audit_results["revision_route"] == RevisionMode.NO_REVISION.value
    event = cs.audit_results["resonance_would_route"]
    assert event["would_route"] is True and event["reason"] == "resonance"
    assert event["floor"] == 78.0
    assert "resonance_route_reason" not in cs.audit_results
    assert cs.revision_count == 0
    assert "resonance_would_route" in capsys.readouterr().err
    trace = tmp_path / "trace.jsonl"  # TraceWriter 落项目根（trace/writer.py:23 _TRACE_NAME）
    assert trace.exists() and "resonance" in trace.read_text(encoding="utf-8")


def test_armed_mode_routes_spot_fix_with_reason(tmp_path, monkeypatch):
    _seed_project(tmp_path, report=None, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    _no_issues(monkeypatch)
    _route_revision_after_resonance(state, tmp_path, 14)
    cs = state.chapter_loop.chapter_states["14"]
    assert cs.audit_results["revision_route"] == "spot-fix"  # 枚举实值（连字符）
    assert cs.audit_results["resonance_route_reason"] == "resonance"
    assert cs.revision_count == 1


def test_role_gate_blocked_shadow_records_event_only(tmp_path, monkeypatch):
    _seed_project(tmp_path, report=BLOCKED_REPORT, with_trend=True)
    state = _make_state(policy=None)  # shadow：score 88 过 floor，但 verdict 阻断
    _no_issues(monkeypatch)
    _route_revision_after_resonance(state, tmp_path, 14)
    cs = state.chapter_loop.chapter_states["14"]
    assert cs.audit_results["revision_route"] == RevisionMode.NO_REVISION.value
    event = cs.audit_results["resonance_would_route"]
    assert event["reason"] == "role_gate"


def test_role_gate_blocked_armed_routes(tmp_path, monkeypatch):
    _seed_project(tmp_path, report=BLOCKED_REPORT, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    _no_issues(monkeypatch)
    _route_revision_after_resonance(state, tmp_path, 14)
    cs = state.chapter_loop.chapter_states["14"]
    assert cs.audit_results["revision_route"] == "spot-fix"
    assert cs.audit_results["resonance_route_reason"] == "role_gate"


def test_negated_block_not_routed(tmp_path, monkeypatch):
    report = BLOCKED_REPORT.replace("判定: 阻断", "判定: 无阻断")
    _seed_project(tmp_path, report=report, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    state.chapter_loop.chapter_states["14"].resonance_score = 85  # 过 floor
    _no_issues(monkeypatch)
    _route_revision_after_resonance(state, tmp_path, 14)
    cs = state.chapter_loop.chapter_states["14"]
    event = cs.audit_results["resonance_would_route"]
    assert event["would_route"] is False


def test_cap_confirm_pass_restores_no_revision(tmp_path, monkeypatch):
    # armed + 已 2 次修订 + 第 3 次 resonance 路由 → cap 耗尽 → 二次采样复评 85 ≥ floor → pass
    _seed_project(tmp_path, report=None, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    cs = state.chapter_loop.chapter_states["14"]
    cs.revision_count = 2
    _no_issues(monkeypatch)
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper.dispatch_skill",
        lambda *a, **k: SimpleNamespace(success=True, returncode=0, stderr="", stdout=""),
    )
    (tmp_path / "audits" / "chapter-14-resonance.md").write_text(
        "```verdict\n判定: 通过\n共振: 85/100\n```\n", encoding="utf-8")
    _route_revision_after_resonance(state, tmp_path, 14)
    assert cs.audit_results["revision_route"] == RevisionMode.NO_REVISION.value  # pass 回退
    assert cs.revision_count == 2  # 增量已回退
    assert cs.audit_results["resonance_cap_confirmed"] is True


def test_cap_confirm_both_below_escalates_with_double_report(tmp_path, monkeypatch):
    _seed_project(tmp_path, report=None, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    cs = state.chapter_loop.chapter_states["14"]
    cs.revision_count = 2
    _no_issues(monkeypatch)
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper.dispatch_skill",
        lambda *a, **k: SimpleNamespace(success=True, returncode=0, stderr="", stdout=""),
    )
    (tmp_path / "audits" / "chapter-14-resonance.md").write_text(
        "```verdict\n判定: 通过\n共振: 40/100\n```\n", encoding="utf-8")
    escalated = []
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.dispatch_escalation",
        lambda *a, **k: escalated.append(1) or True,
    )
    _route_revision_after_resonance(state, tmp_path, 14)
    assert escalated, "两次均 below 必须升级"
    assert (tmp_path / "audits" / "chapter-14-resonance-first.md").exists()  # 双报告保全


def test_cap_confirm_dispatch_failure_conservative_escalation(tmp_path, monkeypatch):
    # confirmed is None（派发失败）→ 保守升级（噪声成本 < 漏放行）
    _seed_project(tmp_path, report=None, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    state.chapter_loop.chapter_states["14"].revision_count = 2
    _no_issues(monkeypatch)
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper.dispatch_skill",
        lambda *a, **k: SimpleNamespace(success=False, returncode=1, stderr="boom", stdout=""),
    )
    escalated = []
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.dispatch_escalation",
        lambda *a, **k: escalated.append(1) or True,
    )
    _route_revision_after_resonance(state, tmp_path, 14)
    assert escalated  # None → 保守升级


def test_docstring_matches_production():
    from shenbi.pipeline import revision_router

    doc = revision_router.__doc__ or ""
    assert "borderline -> escalation checkpoint" not in doc
    assert "不路由" in doc
```

- [ ] **Step 2: 跑红测**

Run: `uv run pytest tests/unit/pipeline/test_resonance_routing.py -x -q --no-cov -p no:randomly`
Expected: FAIL（ImportError `_resonance_report_blocked` 或事件键断言失败）

- [ ] **Step 3: 实现接线**

`chapter_loop.py` `_resonance_report_pending` 后加：

```python
_RESONANCE_BLOCKED_RE = re.compile(r"(?<!无)阻断")


def _resonance_report_blocked(report_path: Path) -> bool:
    """Verdict-scoped role-gate blocked detection (spec #106 T1): the skill's
    校准门 emits 阻断 when overall or a sub-floor is unmet. Fence-scoped like
    pending; prose 阻断 and the negated form 无阻断 never route."""
    if not report_path.exists():
        return False
    from shenbi.gates.g4.verdict_fence import extract_fence

    text = report_path.read_text(encoding="utf-8")
    fence = extract_fence(text)
    if fence is None:
        return False
    return bool(_RESONANCE_BLOCKED_RE.search(fence)) and not _RESONANCE_PENDING_RE.search(fence)
```

`_route_revision_after_resonance` 改造（锚：`cs = _get_chapter_state(state, chapter)` :3139 之后、`cs.audit_results[_REVISION_ROUTE_KEY] = route.value` :3140 之前插入——`cs` 需先在位）：

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
    from shenbi.pipeline.revision_router import RevisionDecision, decide_revision

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

旧静态段 **:3172-3182**（deferred 注释 3 行 + `resonance_ok = check_resonance(...)` + `if not resonance_ok and not issues:` log.warning 块）删除——None fail-open 披露由 decide_revision 内部 `check_resonance` 保留（revision_router.py:174-177），below 披露由 would_route 事件承接。模块 import 块 :73 的 `check_resonance` 同步删除（孤儿）。

cap 分支改造（:3152-3165 现块整体替换——**pass 路径禁写 `_CAP_ESCALATED_KEY`**，防一次性噪声 pass 永久压制该章后续真升级）：

```python
if revision_cap_exceeded(cs.revision_count):
    escalate_now = True
    confirmed: bool | None = None
    if (
        reason == "resonance"  # 本次 invocation 的 reason，禁读陈旧持久键（audit-T2 I-2）
        and not cs.audit_results.get("resonance_cap_confirmed")
    ):
        from shenbi.pipeline.resonance_policy import resonance_cap_confirm_escalate

        confirmed = resonance_cap_confirm_escalate(project_dir, chapter, fc.floor)
        cs.audit_results["resonance_cap_confirmed"] = True  # 一次性采样守卫（防重复付费）
        if confirmed is False:
            # 复评 ≥floor：首次 below 判为噪声——pass（不修订不升级）。
            # 回退本次 armed 改写（route/计数），绝不写 _CAP_ESCALATED_KEY。
            escalate_now = False
            cs.revision_count -= 1
            route = RevisionRoute.NO_REVISION
            cs.audit_results[_REVISION_ROUTE_KEY] = route.value
            cs.audit_results.pop("resonance_route_reason", None)  # M2：回退清键
            log.info("resonance_cap_confirm_passed", chapter=chapter)
    if escalate_now and not cs.audit_results.get(_CAP_ESCALATED_KEY):
        resonance_context = (
            f"revision cap exceeded for chapter {chapter} "
            f"(resonance double-below confirmed; reports: "
            f"chapter-{chapter}-resonance-first.md + chapter-{chapter}-resonance.md)"
            if reason == "resonance" and confirmed is True
            else f"revision cap exceeded for chapter {chapter}"
        )
        dispatch_escalation(project_dir, chapter, context=resonance_context)
        cs.audit_results[_CAP_ESCALATED_KEY] = True
```

`revision_router.py:7-14` 模块 docstring 决策树改写：

```
    audit complete
      +-- no BLOCKING + resonance >= floor  -> pass
      +-- no BLOCKING + resonance < floor   -> revision_routing (armed; shadow 记
                                               resonance_would_route 事件不路由, spec #106)
      +-- no BLOCKING + resonance borderline -> 不路由（见 resonance_would_route 事件；
                                               spec #106 r3——drift 信号面不新建）
      +-- BLOCKING -> revision -> re-audit (max 3) -> 3 failures -> escalation
```
（decide_revision docstring :186-196 补一行 armed/shadow 语义。）

`resonance_policy.py` 加：

```python
def resonance_cap_confirm_escalate(
    project_dir: Path | str, chapter: int, floor: float
) -> bool | None:
    """armed cap 护栏（spec #106 T1）。重派前先把首份 below 报告复制为
    ``audits/chapter-N-resonance-first.md``（重派会覆写原报告——升级审阅须见
    双报告），再重派 review-resonance 解析新分。True=两次均 below（升级）；
    False=复评 ≥floor（pass）；None=派发失败（保守升级——噪声成本 < 漏放行）。
    真实派发为付费调用——仅 armed 生产路径触达；测试 monkeypatch
    ``shenbi.pipeline.dispatch_helper.dispatch_skill``（本函数函数级局部 import）。"""
    import shutil

    # 函数级局部 import（F947：monkeypatch 源模块属性即生效）
    from shenbi.pipeline.chapter_loop import parse_resonance_score
    from shenbi.pipeline.dispatch_helper import dispatch_skill

    project_dir = Path(project_dir)
    report = project_dir / "audits" / f"chapter-{chapter}-resonance.md"
    if report.exists():
        shutil.copy2(report, project_dir / "audits" / f"chapter-{chapter}-resonance-first.md")
    result = dispatch_skill(
        "shenbi-review-resonance",
        project_dir,
        f"Re-evaluate chapter {chapter} resonance (cap guard).",
    )
    if not result.success:
        return None
    fresh = parse_resonance_score(report)
    if fresh is None:
        return None
    return fresh < floor
```
（派发是否需 path_context 以 dispatch_skill 实际签名为准——实现时 grep 其调用先例后落码；不需要即省略该参。）

- [ ] **Step 4: 跑绿测 + 邻接回归（含既有波测试改造）**

Run: `uv run pytest tests/unit/pipeline/test_resonance_routing.py tests/unit/pipeline/test_revision_router.py tests/unit/pipeline/test_parallel_wave_resonance.py -q --no-cov -p no:randomly`
Expected: all passed（`test_parallel_wave_resonance.py:110-115` 的 `resonance_below_floor` 断言已改为 `resonance_would_route` 事件断言——语义延续「低分必披露」）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/revision_router.py src/shenbi/pipeline/resonance_policy.py tests/unit/pipeline/test_resonance_routing.py tests/unit/pipeline/test_parallel_wave_resonance.py
git commit -m "feat: spec #106 T2 — decide_revision 孤岛接活+role-gate 路由（armed-only）+shadow 双落点持久化+cap 二次采样护栏（双报告保全+pass 回退不压安全网）"
```

### Task 3: 卷界 hygiene sink（would-route 汇总 + completeness 聚合行 + 注册/接线）

**Files:**
- Modify: `src/shenbi/pipeline/resonance_policy.py`（加 `check_trend_completeness` + `write_volume_resonance_summary`）
- Modify: `src/shenbi/pipeline/chapter_loop.py:2245-2270`（`_check_world_file_freshness` 旁：新函数 `_write_resonance_shadow_summary(state, project_dir, chapter)`，内部 `is_volume_boundary` 判定后调 Task 3 函数；grep `is_volume_boundary` 全部生产调用点，在章收尾路径追加调用）
- Modify: `docs/framework/truth-files.yaml:45`（resonance_trend 行旁加 `- {name: truth/resonance_shadow.md, kind: truth, producer: pipeline}`——「Adding a genuinely new file = ONE edit here」）
- Modify: `skills/shenbi-drift-guidance/SKILL.md:8-16`（contract reads 加 `- truth/resonance_shadow.md`；散文 Reads 行 :35 同步）
- Test: `tests/unit/pipeline/test_resonance_volume_summary.py`（新）

**Interfaces:**
- Consumes: Task 1 `scored_trend_rows`；Task 2 事件键 `resonance_would_route`；`write_truth_file(project_dir, rel, content, mode="replace")`（truth_io.py:183——replace 对不存在文件直接创建；frontmatter 已存在则原样保留）
- Produces:
  ```python
  def check_trend_completeness(project_dir: Path | str) -> dict[str, Any]
      # {"pending": [ch...], "missing": [ch...], "max_chapter": int} — 只算不写不逐章 WARN
  def write_volume_resonance_summary(project_dir: Path | str, state: PipelineState, chapter: int) -> None
      # 卷界：汇总本卷 would_route 计数/分布 + completeness 聚合行 → truth/resonance_shadow.md
      #（框架单写者，mode="replace"=current-state 快照——每卷界全文件重写为当前卷
      #  状态，多卷不留史（历史查 trace.jsonl 事件流）；同卷重写=同输出幂等。
      #  本卷范围=与 is_volume_boundary 同源的卷界结构解析的当前卷章区间，
      #  chapter_states 按章过滤；解析失败降级「全部带事件章」+ 注记行）
  ```

- [ ] **Step 1: 写红测**

`tests/unit/pipeline/test_resonance_volume_summary.py`：

```python
"""spec #106 T3a: volume-boundary resonance shadow sink + trend completeness."""

from pathlib import Path

from shenbi.pipeline.resonance_policy import (
    check_trend_completeness,
    write_volume_resonance_summary,
)
from shenbi.pipeline.state import ChapterState, PipelineState

HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
    " | overall | confidence | human_overridden |"
)
SEP = (
    "|---------|--------------|---------|-----------|---------|---------"
    "|---------|-----------|------------------|"
)


def _seed_trend(tmp_path: Path, rows: list[str]) -> None:
    truth = tmp_path / "truth"
    truth.mkdir(parents=True, exist_ok=True)
    (truth / "resonance_trend.md").write_text(
        "\n".join([HEADER, SEP, *rows]) + "\n", encoding="utf-8"
    )


def test_completeness_reports_pending_and_missing(tmp_path):
    # ch1/5 已评分、ch8 pending → missing ⊇ {2,3,4,6,7}，pending == [8]
    _seed_trend(
        tmp_path,
        [
            "| 1 | 推进 | 21 | 20 | 21 | 15 | 78 | mid |  |",
            "| 5 | 推进 | 21 | 20 | 21 | 15 | 79 | mid |  |",
            "| 8 | 未声明 | - | - | - | - | pending | low |  |",
        ],
    )
    result = check_trend_completeness(tmp_path)
    assert result["pending"] == [8]
    assert set(result["missing"]) >= {2, 3, 4, 6, 7}


def test_volume_summary_written_with_context_note(tmp_path):
    _seed_trend(
        tmp_path,
        [
            f"| {c} | 推进 | 21 | 20 | 21 | 15 | {s} | mid |  |"
            for c, s in [(1, 78), (2, 74), (3, 76)]
        ],
    )
    state = PipelineState()
    for ch, would in [(1, True), (2, True), (3, False)]:
        cs = ChapterState()
        cs.audit_results["resonance_would_route"] = {
            "floor": 78.0,
            "score": 74,
            "reason": "resonance" if would else None,
            "would_route": would,
            "source": "p25",
            "window_rows": 10,
        }
        state.chapter_loop.chapter_states[str(ch)] = cs
    write_volume_resonance_summary(tmp_path, state, 3)
    sink = tmp_path / "truth" / "resonance_shadow.md"
    assert sink.exists()
    text = sink.read_text(encoding="utf-8")
    assert "would_route" in text and "2/3" in text  # 计数行
    assert "pending" in text and "missing" in text  # completeness 聚合行
    assert "双章束" in text  # 束 follower 语境注记
    # 幂等：同卷重写不重复
    write_volume_resonance_summary(tmp_path, state, 3)
    assert sink.read_text(encoding="utf-8") == text


def test_summary_never_touches_route(tmp_path):
    _seed_trend(tmp_path, [])
    state = PipelineState()
    cs = ChapterState()
    cs.audit_results["revision_route"] = "no-revision"
    state.chapter_loop.chapter_states["1"] = cs
    write_volume_resonance_summary(tmp_path, state, 1)
    assert cs.audit_results["revision_route"] == "no-revision"
```

- [ ] **Step 2: 跑红测** — Run: `uv run pytest tests/unit/pipeline/test_resonance_volume_summary.py -x -q --no-cov -p no:randomly` — Expected: FAIL（`ImportError`）

- [ ] **Step 3: 实现**

`check_trend_completeness`：姊妹解析——保留 pending 行章号集与已出现章号集，`missing = 1..max(已出现章号) 中未出现者`；`write_volume_resonance_summary(project_dir, state, chapter)`：扫 `state.chapter_loop.chapter_states` 中带 `resonance_would_route` 键者，计数 `would_route=True`/总数；经 `write_truth_file(project_dir, "resonance_shadow.md", content, mode="replace")` 写 markdown：frontmatter（`type: truth / category: state / status: active`——**不带 produced_at**：current-state 快照逐写刷新，带逐次时间戳会破坏同卷幂等的字节比较——轮 3 复审 N5 残留修复）+ would-route 汇总表 + completeness 聚合行 + 束 follower 语境注记行（「偶数章 pending 多为 #72 双章束 follower 形态——#109 机制件未落地前的制度性状态」）。chapter_loop 挂点（`_check_world_file_freshness` 旁新增）：

```python
def _write_resonance_shadow_summary(state: PipelineState, project_dir: Path, chapter: int) -> None:
    """spec #106 T3a: volume-boundary resonance shadow sink (would-route
    summary + trend completeness aggregate row). Fire-and-forget."""
    from shenbi.pipeline.triggers import is_volume_boundary

    if not is_volume_boundary(chapter, project_dir):
        return
    from shenbi.pipeline.resonance_policy import write_volume_resonance_summary

    try:
        write_volume_resonance_summary(project_dir, state, chapter)
    except OSError:
        log.warning("resonance_shadow_summary_failed", chapter=chapter)
```
`truth-files.yaml` 与 drift-guidance SKILL.md reads 按上述落改。

- [ ] **Step 4: 契约同步 + 跑绿**

Run: `just generate && just lint-contracts`
Expected: 生成物幂等 diff 空、lint 绿（truth-files.yaml 新行 + SKILL.md reads 过 prose lint）
Run: `uv run pytest tests/unit/pipeline/test_resonance_volume_summary.py -q --no-cov -p no:randomly`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/resonance_policy.py src/shenbi/pipeline/chapter_loop.py docs/framework/truth-files.yaml skills/shenbi-drift-guidance/SKILL.md tests/unit/pipeline/test_resonance_volume_summary.py
git commit -m "feat: spec #106 T3a — 卷界 would-route 汇总+trend 完整性聚合行（truth/resonance_shadow.md 单写者+truth-files.yaml 登记+drift-guidance reads 接线）"
```

### Task 4: resonance-backfill 维护命令（双面守卫）

**Files:**
- Create: `src/shenbi/pipeline/resonance_backfill.py`
- Modify: `justfile:147` 后（release-split 配方后加 resonance-backfill）
- Test: `tests/unit/pipeline/test_resonance_backfill.py`（新）

**Interfaces:**
- Consumes: `missing_audit_reads(project_dir: Path | str, skill: str, chapter: int | None) -> list[str]`（src/shenbi/**pipeline**/audit_layer.py:299）、`dispatch_skill`（**函数级局部 import**，F947）、`match_score_scoped(text) -> int | None` / `extract_fence`（gates/g4/verdict_fence.py）、`write_truth_file(..., mode="insert_markdown_row", key_field="chapter")`、`build_resonance_trend_row(chapter: int, overall: int) -> str`（chapter_loop.py:2837）
- Produces:
  ```python
  def backfill_resonance(project_dir: Path | str, chapters: list[int] | None) -> dict[str, Any]
      # {"filled": [ch...], "refused_missing_text": [ch...], "refused_bad_product": [ch...]}
  _STARVED_FORM_RE = re.compile(r"待补|不适用|附条件")  # #109 T4 饿死词族子集（产物侧判据）
  ```

- [ ] **Step 1: 写红测**

`tests/unit/pipeline/test_resonance_backfill.py`：

```python
"""spec #106 T3b: resonance backfill with no-text + starved-product guards."""

from pathlib import Path
from types import SimpleNamespace

from shenbi.pipeline.resonance_backfill import backfill_resonance

HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
    " | overall | confidence | human_overridden |"
)
SEP = (
    "|---------|--------------|---------|-----------|---------|---------"
    "|---------|-----------|------------------|"
)


def _seed(tmp_path: Path, *, chapter_file: bool, report_text: str | None) -> None:
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "truth" / "resonance_trend.md").write_text(
        "\n".join([HEADER, SEP, "| 26 | 未声明 | - | - | - | - | pending | low |  |"]) + "\n",
        encoding="utf-8",
    )
    if chapter_file:
        ch_dir = tmp_path / "chapters"
        ch_dir.mkdir(exist_ok=True)
        (ch_dir / "chapter-26.md").write_text("# 第二十六章\n\n正文。", encoding="utf-8")
        # 契约预检 seed（N3）：missing_audit_reads 按 review-resonance 契约 6 条
        # reads 严格判（plans/style/anchors/audit_drift 不在 OPTIONAL_READS）
        (tmp_path / "plans").mkdir(exist_ok=True)
        (tmp_path / "plans" / "chapter-26-plan.md").write_text("## 1. 当前任务\n", encoding="utf-8")
        (tmp_path / "style").mkdir(exist_ok=True)
        (tmp_path / "style" / "style_profile.md").write_text(
            "# style\n## 11. 综合画像\n## 6. 修辞模式\n", encoding="utf-8"
        )
        (tmp_path / "benchmarks" / "anchors").mkdir(parents=True, exist_ok=True)
        (tmp_path / "truth" / "audit_drift.md").write_text("# drift\n", encoding="utf-8")
    audits = tmp_path / "audits"
    audits.mkdir(exist_ok=True)
    if report_text is not None:
        (audits / "chapter-26-resonance.md").write_text(report_text, encoding="utf-8")


def _ok_dispatch(monkeypatch, seen=None):
    def fake(*a, **k):
        if seen is not None:
            seen.append(1)
        return SimpleNamespace(success=True, returncode=0, stderr="", stdout="")

    monkeypatch.setattr("shenbi.pipeline.dispatch_helper.dispatch_skill", fake)


def test_backfill_refuses_missing_chapter_text(tmp_path, monkeypatch):
    _seed(tmp_path, chapter_file=False, report_text=None)
    seen = []
    _ok_dispatch(monkeypatch, seen)
    result = backfill_resonance(tmp_path, [26])
    assert result["refused_missing_text"] == [26] and not seen
    assert "pending" in (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")


def test_backfill_refuses_starved_product(tmp_path, monkeypatch):
    _seed(tmp_path, chapter_file=True, report_text="```verdict\n判定: 待补（正文未提供）\n```\n")
    _ok_dispatch(monkeypatch)
    result = backfill_resonance(tmp_path, [26])
    assert result["refused_bad_product"] == [26]
    assert "pending" in (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")


def test_backfill_success_upserts_row(tmp_path, monkeypatch):
    _seed(tmp_path, chapter_file=True, report_text="```verdict\n判定: 通过\n共振: 81/100\n```\n")
    _ok_dispatch(monkeypatch)
    result = backfill_resonance(tmp_path, [26])
    assert result["filled"] == [26]
    row = (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
    assert "| 26 |" in row and "81" in row and "pending" not in row


def test_backfill_default_targets_pending(tmp_path, monkeypatch):
    _seed(tmp_path, chapter_file=True, report_text="```verdict\n判定: 通过\n共振: 81/100\n```\n")
    _ok_dispatch(monkeypatch)
    result = backfill_resonance(tmp_path, None)  # None → 自动取 pending 行章
    assert result["filled"] == [26]
```

- [ ] **Step 2: 跑红测** — Run: `uv run pytest tests/unit/pipeline/test_resonance_backfill.py -x -q --no-cov -p no:randomly` — Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 实现**

`resonance_backfill.py`：argparse `main(argv: list[str] | None = None) -> int`（`<dir> [--chapters a-b|c,d]`，解析形如 backfill-context 先例）；目标章 = 显式列表或 trend pending 行章；每章三步守卫：①`chapters/chapter-N.md` 在盘 且 `missing_audit_reads(project_dir, "shenbi-review-resonance", ch) == []` → 否则 `refused_missing_text`；②函数级局部 import `dispatch_skill` 派发（付费——维护命令语义，随用户令运行）；③产物校验：`match_score_scoped(report_text)` 非 None ∧ verdict 非 pending ∧ 正文无 `_STARVED_FORM_RE` 命中 → `write_truth_file(project_dir, "resonance_trend.md", build_resonance_trend_row(ch, score), mode="insert_markdown_row", key_field="chapter")` upsert；任一不过 → `refused_bad_product`。**派发失败（success=False）→ 该章记 `refused_bad_product` 并继续**（维护命令不熔断）。输出走 `shenbi.cli_utils.echo`（禁 print）。justfile：

```just
# Resonance backfill: re-dispatch review-resonance for pending trend rows (spec #106 T3, 维护命令)
resonance-backfill *args:
    uv run python -m shenbi.pipeline.resonance_backfill "$@"
```

- [ ] **Step 4: 跑绿测** — Run: `uv run pytest tests/unit/pipeline/test_resonance_backfill.py -q --no-cov -p no:randomly` — Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/resonance_backfill.py justfile tests/unit/pipeline/test_resonance_backfill.py
git commit -m "feat: spec #106 T3b — just resonance-backfill 补评命令（无正文守卫+饿死词族产物校验）"
```

### Task 5: pipeline override-resonance 子命令（cell-patch / 全行写 / 排除面激活）

**Files:**
- Modify: `src/shenbi/pipeline/cli.py:1785-1850`（子命令表：`p_override = sub.add_parser("override-resonance", ...)`——**既有 `pipeline` console-script 入口**，pyproject.toml:65；不新建 `shenbi-pipeline` 入口）
- Modify: `src/shenbi/pipeline/resonance_policy.py`（加 `apply_resonance_override`）
- Test: `tests/unit/pipeline/test_resonance_override_cli.py`（新）

**Interfaces:**
- Consumes: `write_truth_file(project_dir, rel, content, mode="upsert_markdown_row", key_field=…)`（truth_io.py:183——**cell-patch 钉死为读-改-写 + upsert_markdown_row 整行替换**：先读原文定位行、校验 overall、仅改末列后整行写回，不引入 replace 全文重写的第二路径）；`compute_drift.parse_trend(path, dims) -> dict[str, list[tuple[float, bool]]]`（排除面验证）
- Produces:
  ```python
  def apply_resonance_override(project_dir: Path | str, chapter: int, overall: int,
                               dims: dict[str, int] | None = None, note: str | None = None) -> str
      # 返回落盘行。富行存在（overall 已数值）→ --overall 必须与现值相等（防误改分），
      # 仅翻 human_overridden cell（"true" 小写）；pending/缺行 → 9 列全行写
      # （role "未声明"、未给维 "-"、confidence "human"——confidence 列无下游消费面
      # （compute_drift/report_longitudinal 只按表头绑 chapter/overall/human_overridden），新词面安全）
  ```

- [ ] **Step 1: 写红测**

`tests/unit/pipeline/test_resonance_override_cli.py`：

```python
"""spec #106 T3c: pipeline override-resonance (cell-patch semantics)."""

from pathlib import Path

import pytest

from shenbi.pipeline.resonance_policy import apply_resonance_override

HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
    " | overall | confidence | human_overridden |"
)
SEP = (
    "|---------|--------------|---------|-----------|---------|---------"
    "|---------|-----------|------------------|"
)


def _seed(tmp_path: Path, rows: list[str]) -> Path:
    truth = tmp_path / "truth"
    truth.mkdir(parents=True, exist_ok=True)
    trend = truth / "resonance_trend.md"
    trend.write_text("\n".join([HEADER, SEP, *rows]) + "\n", encoding="utf-8")
    return trend


def test_override_rich_row_flips_flag_only(tmp_path):
    _seed(tmp_path, ["| 3 | 推进 | 21 | 19 | 20 | 16 | 76 | high |  |"])
    apply_resonance_override(tmp_path, 3, 76)
    text = (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
    assert "| 3 | 推进 | 21 | 19 | 20 | 16 | 76 | high | true |" in text


def test_override_rich_row_score_mismatch_refuses(tmp_path):
    _seed(tmp_path, ["| 3 | 推进 | 21 | 19 | 20 | 16 | 76 | high |  |"])
    with pytest.raises(ValueError, match="76"):
        apply_resonance_override(tmp_path, 3, 99)
    assert "true" not in (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")


def test_override_pending_row_writes_full_row(tmp_path):
    _seed(tmp_path, ["| 26 | 未声明 | - | - | - | - | pending | low |  |"])
    apply_resonance_override(tmp_path, 26, 70, dims={"情感落地": 18})
    text = (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
    assert "| 26 | 未声明 | 18 | - | - | - | 70 | human | true |" in text


def test_override_row_visible_to_compute_drift_exclusion(tmp_path):
    _seed(tmp_path, ["| 3 | 推进 | 21 | 19 | 20 | 16 | 76 | high |  |"])
    apply_resonance_override(tmp_path, 3, 76)
    from shenbi.skill_utils.drift_detection.compute_drift import parse_trend

    pairs = parse_trend(tmp_path / "truth" / "resonance_trend.md", ["overall"])
    assert (76.0, True) in pairs["overall"]
```

- [ ] **Step 2: 跑红测** — Run: `uv run pytest tests/unit/pipeline/test_resonance_override_cli.py -x -q --no-cov -p no:randomly` — Expected: FAIL（ImportError）

- [ ] **Step 3: 实现**

`apply_resonance_override`：读 trend 文本，`_split_row` 语义定位章行；富行 → overall 校验相等（不等 `raise ValueError(f"chapter {chapter} existing overall is {cur}, refusing rewrite to {overall}")`）→ 重组该行仅置末列 `" true "`（保持 9 列间距形态）→ `write_truth_file(..., 新行文本, mode="upsert_markdown_row", key_field="chapter")` 整行替换；pending/缺行 → `f"| {chapter} | 未声明 | {dims.get('情感落地', '-')} | … | {overall} | human | true |"` 9 列行同 upsert（key_field=chapter 自动落位）。cli.py 子命令（argparse 形如既有 7 子命令）：

```python
    p_override = sub.add_parser(
        "override-resonance",
        help="Mark a chapter's resonance trend row human_overridden (spec #106 T3)",
    )
    p_override.add_argument("project_dir", type=str)
    p_override.add_argument("chapter", type=int)
    p_override.add_argument("--overall", type=int, required=True)
    p_override.add_argument("--dims", type=str, default=None, help="逗号分隔 维=分")
    p_override.add_argument("--note", type=str, default=None)
```
（handler 解析 --dims `情感落地=18,场景临场感=19` 形态，调 `apply_resonance_override`，`cli_utils.echo` 落盘行。）

- [ ] **Step 4: 跑绿测** — Run: `uv run pytest tests/unit/pipeline/test_resonance_override_cli.py -q --no-cov -p no:randomly` — Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/cli.py src/shenbi/pipeline/resonance_policy.py tests/unit/pipeline/test_resonance_override_cli.py
git commit -m "feat: spec #106 T3c — pipeline override-resonance（富行 cell-patch+pending 全行写+compute_drift 排除面激活）"
```

### Task 6: AC2/AC3 离线回放工具 + 文档面收尾

**Files:**
- Create: `tools/resonance_floor_replay.py`（只读回放）
- Modify: `AGENTS.md`（Key Commands 加 `just resonance-backfill <dir> [--chapters a-b|c,d]` 与 `pipeline override-resonance <dir> <chapter> --overall N` 两行——M4 钉）
- Test: `tests/unit/pipeline/test_resonance_replay_tool.py`（新）

**Interfaces:**
- Consumes: `effective_resonance_floor`、`scored_trend_rows`、`decide_revision`、`collect_audit_issues`/`route_chapter_revision`（route 重算）
- Produces: 验收期证据命令 `uv run python tools/resonance_floor_replay.py novel-xinghuo-vol1 --replay` 与 `--diff-route`

- [ ] **Step 1: 写红测**

`tests/unit/pipeline/test_resonance_replay_tool.py`：

```python
"""spec #106 T6: offline replay tool (AC2/AC3 evidence)."""

from pathlib import Path

from tools.resonance_floor_replay import replay_floors

VOL1_SCORED = {
    1: 78,
    2: 74,
    3: 76,
    4: 78,
    5: 79,
    7: 79,
    9: 80,
    11: 79,
    12: 81,
    13: 79,
    14: 77,
    15: 80,
    16: 77,
    17: 79,
    18: 81,
    19: 86,
}


def _seed(tmp_path: Path) -> None:
    truth = tmp_path / "truth"
    truth.mkdir(parents=True)
    rows = [f"| {c} | 推进 | 21 | 20 | 21 | 15 | {s} | mid |  |" for c, s in VOL1_SCORED.items()]
    header = (
        "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
        " | overall | confidence | human_overridden |"
    )
    sep = (
        "|---------|--------------|---------|-----------|---------|---------"
        "|---------|-----------|------------------|"
    )
    (truth / "resonance_trend.md").write_text(
        "\n".join([header, sep, *rows]) + "\n", encoding="utf-8"
    )


def test_replay_ignites_ch14_ch16_and_respects_cold_start(tmp_path):
    _seed(tmp_path)
    rows = replay_floors(tmp_path)
    ignited = [r["chapter"] for r in rows if r["would_route"]]
    assert ignited == [14, 16]
    assert all(not r["would_route"] for r in rows if r["chapter"] <= 11)  # 冷启动边界
    by_ch = {r["chapter"]: r for r in rows}
    assert by_ch[14]["floor"] == 78.0
    assert by_ch[16]["floor"] == 77.75
    assert (
        by_ch[17]["floor"] == 77.0 and by_ch[17]["would_route"] is False
    )  # 众数 79 章不命中（AC3c）
    assert by_ch[19]["would_route"] is False  # 高分带不命中
```

- [ ] **Step 2: 跑红测** — Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现工具**（`replay_floors(project_dir) -> list[dict]`：对每已评分章算 `effective_resonance_floor` + `would_route = score < floor`；`main()` argparse `--replay`（逐章打印 `ch | score | floor | source | would_route` + 点火率 `n/m`）与 `--diff-route`（**同快照代码级差分**：对每可评估章先以旧表达式 `route_chapter_revision(*collect_audit_issues(project_dir, ch))` 算 baseline route，再模拟新接线 shadow 模式（mode=shadow 时 route 不变）断言逐章相等，输出 `route-diff: 0`，非零则打印逐章明细。**不对 pipeline-state.json 历史 route 对账**——复评覆写+饿死混杂会产生与 #106 无关的假 diff，此理由作为工具 docstring 首段落盘）。tools/ 下 print 允许（report_longitudinal.py 先例）。）

- [ ] **Step 4: 跑绿测 + 对 vol1 实跑（只读验收证据）**

Run: `uv run pytest tests/unit/pipeline/test_resonance_replay_tool.py -q --no-cov -p no:randomly` — Expected: passed
Run: `uv run python tools/resonance_floor_replay.py novel-xinghuo-vol1 --replay` — Expected: 点火 ch14/ch16、前 8 已评分章（ch1/2/3/4/5/7/9/11）零触发、2/24=8.3%
Run: `uv run python tools/resonance_floor_replay.py novel-xinghuo-vol1 --diff-route` — Expected: `route-diff: 0`

- [ ] **Step 5: Commit**

```bash
git add tools/resonance_floor_replay.py AGENTS.md tests/unit/pipeline/test_resonance_replay_tool.py
git commit -m "feat: spec #106 T6 — AC2/AC3 离线回放工具（同快照差分钉死）+AGENTS.md 命令登记"
```

---

## Self-Review（修复轮 1 后自检记录）

1. **Spec coverage**：T1 判据 → Task 1+2；T2 判据（持久键+trace/不改写 route/drift-guidance reads/lint-contracts+generate）→ Task 2+3；T3 判据三件 → Task 3/4/5；验收 2/3 → Task 6（AC 表含 AC4 未获令时替代交付链接）；验收 1 → 阶段 7；验收 4 → 挂账（随令）。无缺口。
2. **Placeholder scan**：无 TBD/「适当处理」/「二选一未定」（T5 cell-patch 已钉死 read-modify-write+upsert_markdown_row）；T1-T6 红测全部为真实可跑代码；T2 Step 3 唯一一处「以实际签名为准」（dispatch path_context）属落码期核验义务注记，非占位。
3. **Type consistency**：`effective_resonance_floor(project_dir, chapter, config) -> FloorComputation`（T1 产/T2 消）；`resonance_policy_of(config) -> dict`（T1/T2）；`write_volume_resonance_summary(project_dir, state, chapter)`（T3 Produces=挂点 wrapper 调用统一——I12 修复）；`apply_resonance_override`/`backfill_resonance`（T4/T5）；`ResonancePolicyMode` shadow|armed 全文一致；`"spot-fix"` 连字巻实值。
4. **leaf/infra**：六 task 全 infra（pipeline/contracts/gates/config 多文件+被 3+ 消费方 import）——协调者亲实现+TDD，每 task 后 fresh-context 审查子 agent 产 audit-T<N>.md。
5. **阶段 5 首审 4C+9I+7M 全数吸收**：C1（vol1 真值序列钉死，合成序列 Q1=78.25 反向奖励最近秩的陷阱已除）/C2（pipeline 既有入口+spec 同步改）/C3（pass 回退 route+计数回退+禁写 _CAP_ESCALATED_KEY+一次性采样守卫键）/C4（truth-files.yaml 登记）/I5（删除锚 :3172-3182 精确）/I6（插入锚 :3139 后+局部 import 含 decide_revision+check_resonance 孤儿清理+test_parallel_wave 改造入 Files）/I7（or True 删除+capsys 惯用法+签名占位修复+ImportError 期望修正 M16）/I8（cell-patch 钉死）/I9（status-vocab 域行+ALL_ENUMS）/I10（resonance-first 双报告+escalation context 指认）/I11（函数级局部 import 消费 dispatch_skill）/I12（函数名统一）/I13（--diff-route 同快照语义+不对历史对账理由落 docstring）/M14（锚 2837）/M15（连字巻）/M17（无阻断否定尾巴 (?<!无)）/M18（AC3c 高分带断言+AC4 链接）/M19（执行分支声明）/M20（confidence human 无消费面注记）。
