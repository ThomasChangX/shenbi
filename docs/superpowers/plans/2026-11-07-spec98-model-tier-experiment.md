# Spec #98 模型分档实验 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 spec #98 的 T0（档位连通行探测+thinking 政策预注册）与 T1（pricing/estimate 双表主备两档接线），T2/T3 实弹窗与判定**待用户实弹令**（本 plan 不含、不出分支）。

**Architecture:** 运行侧实验的最小代码面——`SHENBI_LLM_MODEL` 环境变量既有单点消费（dispatch_helper.py:3906）不动；唯一 src 面=两处 model-keyed 常量表加键（`cost/pricing.py PRICING`、`cost/estimate.py MODEL_CONTEXT_LIMITS`）；executor_config 仅在 T0 预注册口径要求时做条件适配（全局共享面，T3 附回滚条款）。

**Tech Stack:** Python 3.11+/pathlib/json（无新依赖）；探测用 curl/python3 stdlib 直调 provider OpenAI 兼容端点；测试 pytest（`uv run` 同构）。

**对应 spec**：`docs/superpowers/specs/2026-11-06-spec98-model-tier-experiment.md`（r2.4 版，commit 40162ea4）

## Global Constraints

- spec r2.1：**主档=提供方谱系最高档**（按定价/产品定位排序非营销名）；锁定 1 主 1 备。
- spec r2.2：**主+备两档同批入表**（PRICING+MODEL_CONTEXT_LIMITS+test_pricing 用例）。
- spec r2.1：thinking 政策**预注册**——两口径皆可用时默认**启用（容量满配=provider 默认，effort high）**；disabled 系 flash 特有成本调优。
- T0 探针预算 **≤$0.5**（spec §2；探测不过回用户重定档）。
- 验证命令一律 `just`/`uv run`（与 CI `uv run --frozen` 同构）；系统 python 结果不算证据。
- `src/shenbi/` 无 print、pathlib、常量表加键不引入新状态字符串（模型名是配置键非状态面）。
- commit 显式列文件路径（pathspec），禁 `git add -A`；conventional commits。
- **核心原则 8**：T0 探针是 spec 交付物本体（预算内授权）；除此外零真实 dispatch。

## T2/T3 边界声明（本 plan 之外）

spec T2（`SHENBI_LLM_MODEL=<高档>` resume ch47/48 实弹窗）与 T3（判定分叉+判定书）**需用户新实弹令**——precedent：spec #95 的束4 生产验收窗同为合并后待令。本 plan 交付到 T1 合并即止；T2/T3 由后续会话在用户令下执行（判据/三结局/kill 臂/诊断段口径全部已预注册于 spec r2.1-r2.4，届时直接引用）。

---

### Task 0: Re-anchor + 基线

**Files:**
- Read: `src/shenbi/cost/pricing.py`（全文 61 行）
- Read: `src/shenbi/cost/estimate.py:16-40`
- Read: `src/shenbi/pipeline/dispatch_helper.py:100-115, 284-318, 3895-3960`
- Read: `executor_config.toml:1-45, 210-230`
- Read: `tests/unit/cost/test_pricing.py`、`tests/unit/test_pricing_fail_loud.py`
- Test: 基线=`uv run pytest tests/unit/cost/ tests/unit/test_pricing_fail_loud.py -q`

**Interfaces:**
- Consumes: 无（首任务）
- Produces: 锚核对记录（进 `.superpowers/sdd/progress.md` 阶段 6 ledger Task 0 行）——本 plan 下述行号以 2026-11-07 树为准，若 Task 0 核对发现漂移 → 修正本 plan 后续 task 引用并记 deviation

- [ ] **Step 1: 锚核对**（逐条打开，±3 容差）：
  - `pricing.py:22-24` PRICING 单键 `deepseek-v4-flash`；`:51-56` unknown ValueError
  - `estimate.py:18-20` MODEL_CONTEXT_LIMITS 单键 1_048_576；`:34` `_DEFAULT_CONTEXT_LIMIT=131_072`；`:56-65` 回退+一次性 WARN
  - `dispatch_helper.py:102` `_ENV_LLM_MODEL="SHENBI_LLM_MODEL"`；`:106` `_DEFAULT_MODEL="deepseek-v4-flash"`；`:287` `_THINKING_VALUES=("disabled","low")`；`:308-314` `_thinking_kwargs`（disabled→`extra_body {"thinking":{"type":"disabled"}}`，low→`reasoning_effort:"low"`，None→`{}`=provider 默认）；`:3906` 模型解析单点；`:3911` `api_timeout=_compute_dispatch_timeout(...)`
  - `executor_config.toml` `[default]` 节**无 thinking 键**（删 override 后 fallthrough=provider 默认）；`[overrides."shenbi-chapter-planning"] thinking="disabled"` @ :221-222；session30 注释块 @ :215-219
  - `tests/unit/test_pricing_fail_loud.py:21` 夹具 `model="deepseek-v4-pro"`
- [ ] **Step 2: 基线绿**：`uv run pytest tests/unit/cost/ tests/unit/test_pricing_fail_loud.py -q` → 全 PASS（记录数字；Task 2 完成后复跑同一命令对照）
- [ ] **Step 3: Commit**（如有 plan 行号修正）：`git add docs/superpowers/plans/2026-11-07-spec98-model-tier-experiment.md && git commit -m "docs: spec98 plan task0 re-anchor"`（无修正则跳过本 commit，仅记录）
- [ ] **Step 4: audit-T0.md**（fresh-context 子 agent 审本 task 产物）

**复杂度: infra（协调者亲做）** ｜ **test_kind: characterization（基线钉死）** ｜ 测试层级: T1 单元

---

### Task 1: T0 档位探测（spec T0）

**Files:**
- Create: `docs/research/2026-11-07-spec98-t0-tier-probe.md`（探测报告+预注册决议+锁定档位表+脚本附录）
- 临时（不入库）: `/tmp/spec98-probe/`（脚本与原始响应）

**Interfaces:**
- Consumes: `SHENBI_LLM_API_KEY`、`SHENBI_LLM_BASE_URL`（缺省 `https://api.deepseek.com/v1`，dispatch_helper.py:104-105 同源；`.env` 有值则 `export`——`source .env` 不注入 `uv run` 子进程，直接 shell export）
- Produces: 报告 §锁定档位表（`主档名/备档名/input rate/output rate/context limit` 五列，供 Task 2 直接抄录）；§预注册决议（thinking 口径三选一+依据）；§夹具撞名判定

**纪律**: 探针预算 ≤$0.5——每个 completion 探针 max_tokens ≤ 512、prompt ≤ 200 tokens（**例外见 Step 3 stream 探针——以流式首块为接受信号，不产生完整 completion 成本**）；每次探针的 usage payload（含 reasoning/content token 拆分若有）逐条记录入报告 §成本表并求和；发送前按主档 rate 预算最坏情形（单探针预期 >$0.1 的不发）；超 $0.5 立即停。**`SHENBI_LLM_API_KEY` 缺失（`.env` 导出后仍空）→ 直接 BLOCKED 出口回用户**，不进 Step 1。

- [ ] **Step 1: 目录探测**：`curl -s -H "Authorization: Bearer $SHENBI_LLM_API_KEY" $SHENBI_LLM_BASE_URL/models` → 候选清单全录（json 原文入附录）。按 spec r2.1 判定谱系最高档=主档、次档=备档（判定依据=provider 定价页/文档的产品定位排序，URL 记入报告；若 /models 不分档，用 provider 官方 pricing 页排序）。
- [ ] **Step 2: thinking 行为探测**（对主档，每形一探针，三形）：
  - (a) 无 thinking 参数（provider 默认）→ 200? content 非空? reasoning 耗量（usage 字段）?
  - (b) `extra_body {"thinking":{"type":"disabled"}}` → 200/400?（MiniMax 教训面）
  - (c) `reasoning_effort:"low"` → 200/400?——**若 (c) 单独被拒而 (a)(b) 通过**：记录在案并在报告预注册 T2 回退=spec §4 降级模式（只测规划步；草写/修订链[thinking=low 档]可选），不阻塞定档。
  - **session30 病理判定（区分度要求）**：≤512 小预算下 content 空对健康模型也是预期（reasoning 与 content 共享 completion 预算）——**病理触发条件=content 空 且 usage 显示 reasoning 钉死预算（pinned-at-cap）**；命中则以 `max_tokens: 4096` 重探 (a) 形一次（预算内）；重探仍 pinned-empty 才判病理成立；仅小预算空 content=**不确定 → 按 spec r2.1 默认启用口径**。报告注明「生产 45K prompt 行为可能不同，T2 观察点兜底」。
- [ ] **Step 3: max_tokens/超时面探测**（**stream 形——不产生完整 completion 成本**）：主档请求 `max_tokens: 65536, stream: true`，收到首个 SSE chunk 即断开——接受信号=HTTP 200+流打开（非完整补全）；观察响应是否声明钳制；记录首 token 延迟（900s base 超时风险评估，spec §4 风险行）。若 provider 对 stream 报 400：降级为 `max_tokens: 512` 非 stream 探针并只记录「512 接受，65536 未测」——**禁发起非流式 65536 完整补全**（最坏情形单发可击穿 $0.5 上限）。
- [ ] **Step 4: 夹具撞名判定**：锁定档位名 vs `deepseek-v4-pro`（test_pricing_fail_loud.py:21）——撞名→Task 2 Step 5 改夹具；不撞→不动。判定写入报告。
- [ ] **Step 5: 预注册决议**（报告 §预注册，三选一并附依据）：
  - 默认路径：高档三形全 200 且默认形 content 非空 → **启用（容量满配）**：Task 2 删 planning override 节（fallthrough provider 默认；`[default]` 无 thinking 键已核）
  - 高档默认 thinking 复现空正文病理 → **disabled 口径**（executor_config 不动，报告记病理证据）
  - 高档拒 thinking 参数（400）→ **删 override 节+实验注记**（flash 侧无生产派发在途——卷二停机面；T3 回滚条款钉住）
- [ ] **Step 6: 汇总成本** ≤$0.5 核对；探测不过（连通失败/全 400/无更高档）→ **停：回用户重定档**（spec §2 T0 出口，本 task 以 BLOCKED 记 spec-deviations 终止）。
- [ ] **Step 7: Commit**: `git add docs/research/2026-11-07-spec98-t0-tier-probe.md && git commit -m "docs: spec98 T0 档位探测报告——锁定主备两档+thinking 政策预注册"`
- [ ] **Step 8: audit-T1.md**（fresh-context 子 agent：报告锚可复核性/预算合规/预注册决议与 spec r2.1 准则一致性）

**复杂度: infra（协调者亲做——需密钥与判断）** ｜ **test_kind: N/A（研究任务，产物=报告）** ｜ 测试层级: N/A

---

### Task 2: T1 接线小批（spec T1）

**Files:**
- Modify: `src/shenbi/cost/pricing.py:22-24`（PRICING 加两键）
- Modify: `src/shenbi/cost/estimate.py:18-20`（MODEL_CONTEXT_LIMITS 加两键）
- Modify: `executor_config.toml:221-222`（**仅当** Task 1 预注册决议=启用/删 override 路径）
- Test: `tests/unit/cost/test_pricing.py`（扩展）、`tests/unit/cost/test_estimate.py`（扩展）、`tests/unit/test_pricing_fail_loud.py`（**仅当** Task 1 判定撞名）

**Interfaces:**
- Consumes: Task 1 报告 §锁定档位表（五列值逐一抄录，报告 commit SHA 记入 commit message）
- Produces: `PRICING: dict[str, dict[str, float]]` 含三键；`MODEL_CONTEXT_LIMITS: dict[str, int]` 含三键

- [ ] **Step 1: 写红测**（`tests/unit/cost/test_pricing.py` 追加；档位名以 Task 1 锁定为准——下例用 `deepseek-v4`/`deepseek-v4-pro` 占位展示形，Task 1 若名异则同步替换，guard 断言保证一致性）：

```python
class TestExperimentTiers:
    """spec #98 T1: 主+备两档接线（档位名以 T0 报告 §锁定档位表为准）。"""

    TIER_MAIN = "deepseek-v4"  # T0 锁定后若名异则替换
    TIER_BACKUP = "deepseek-v4-pro"  # 同上

    def test_pricing_has_both_experiment_tiers(self):
        from shenbi.cost.pricing import PRICING

        assert self.TIER_MAIN in PRICING
        assert self.TIER_BACKUP in PRICING

    def test_estimate_cost_positive_both_tiers(self):
        from shenbi.cost.pricing import estimate_cost

        usage = {"prompt_tokens": 100_000, "completion_tokens": 10_000}
        for tier in (self.TIER_MAIN, self.TIER_BACKUP):
            assert estimate_cost(usage, tier) > 0.0

    def test_flash_default_pricing_unchanged(self):
        from shenbi.cost.pricing import PRICING

        assert PRICING["deepseek-v4-flash"] == {
            "input": 0.14 / 1_000_000,
            "output": 0.28 / 1_000_000,
        }
```

`tests/unit/cost/test_estimate.py` 追加：

```python
class TestExperimentTierLimits:
    """spec #98 T1: MODEL_CONTEXT_LIMITS 主+备两档（防 F523 128K 保守回退失真）。"""

    TIER_MAIN = "deepseek-v4"  # 与 test_pricing.TestExperimentTiers 同名常量人工同步
    TIER_BACKUP = "deepseek-v4-pro"

    def test_limits_cover_both_tiers(self):
        from shenbi.cost.estimate import MODEL_CONTEXT_LIMITS

        for tier in (self.TIER_MAIN, self.TIER_BACKUP):
            # 不低于 128K（provider "128K" 档字面值也须过——不假设 ≥131_072）
            assert MODEL_CONTEXT_LIMITS[tier] >= 128_000

    def test_pricing_and_limits_keys_parity(self):
        """跨表一致性真 guard：可计价模型集 == 有上下文限模型集。"""
        from shenbi.cost.estimate import MODEL_CONTEXT_LIMITS
        from shenbi.cost.pricing import PRICING

        assert set(PRICING.keys()) == set(MODEL_CONTEXT_LIMITS.keys())
```

（既有 `test_estimate.py` 已覆盖 unknown 回退保守值语义，不重复添加。）

- [ ] **Step 2: 跑红**：`uv run pytest tests/unit/cost/test_pricing.py::TestExperimentTiers tests/unit/cost/test_estimate.py::TestExperimentTierLimits -v` → 预期 FAIL（KeyError/AssertionError）
- [ ] **Step 3: 实现**（值从 Task 1 报告 §锁定档位表逐字抄录；报告若标注 rates 系保守估计则照抄并保留行内 `# conservative until confirmed` 注记——护栏向高估方向安全）：

```python
# pricing.py
PRICING: dict[str, dict[str, float]] = {
    "deepseek-v4-flash": {"input": 0.14 / 1_000_000, "output": 0.28 / 1_000_000},
    "deepseek-v4": {"input": <主档 input USD/M> / 1_000_000, "output": <主档 output USD/M> / 1_000_000},
    "deepseek-v4-pro": {"input": <备档 input> / 1_000_000, "output": <备档 output> / 1_000_000},
}

# estimate.py
MODEL_CONTEXT_LIMITS: dict[str, int] = {
    "deepseek-v4-flash": 1_048_576,
    "deepseek-v4": <主档 context 限>,
    "deepseek-v4-pro": <备档 context 限>,
}
```

- [ ] **Step 4: 跑绿**：同 Step 2 命令 → 全 PASS；再跑 `uv run pytest tests/unit/cost/ tests/unit/test_pricing_fail_loud.py -q` → 全 PASS（含既有 fail-loud 语义）
- [ ] **Step 5（仅当 Task 1 判定撞名）**: `tests/unit/test_pricing_fail_loud.py:21` `model="deepseek-v4-pro"` → `model="no-such-model-x"`（spec r2.2 夹具条款）；跑该文件绿
- [ ] **Step 6（仅当预注册=启用/删 override）**: `executor_config.toml` 删 `[overrides."shenbi-chapter-planning"]` 节两行，紧邻 session30 注释块后追加：

```toml
# spec #98 T0 预注册（2026-11-07）：实验口径=启用（容量满配=provider 默认）。
# 删 planning override 系档位定义整体单元变更（spec §1 ③）；T3 判定分叉附
# 回滚条款（PASS=生产迁移评估 / FAIL=回滚评估）。
# kill 臂（spec r2.3，若获用户裁跑）：flash 侧跑规划须临时恢复本 override
# （disabled 系 flash 成本调优）——setup 面 ledger 单列，臂毕即撤。
```

- [ ] **Step 7: Commit**: `git add src/shenbi/cost/pricing.py src/shenbi/cost/estimate.py tests/unit/cost/test_pricing.py tests/unit/cost/test_estimate.py [tests/unit/test_pricing_fail_loud.py] [executor_config.toml] && git commit -m "feat: spec98 T1 主备两档接线——PRICING+MODEL_CONTEXT_LIMITS（rates 源=T0 报告 <SHA>）"`
- [ ] **Step 8: audit-T2.md**（fresh-context 子 agent + 项目补充 rubric；sha_range=(Task1 commit, 本 commit)）

**复杂度: infra（跨 cost 模块+全局配置——协调者亲做）** ｜ **test_kind: tdd_red_green** ｜ 测试层级: T1 单元；fixture: 无（纯常量表，G0.9 不涉）

---

### Task 3: 收口登记

**Files:**
- Modify: `docs/superpowers/plans/INDEX.md`（本 plan ✅ ready→T0/T1 done 状态；顺带补登记 #97 plan 漂移行）
- Modify: `docs/superpowers/specs/INDEX.md`（#98 状态 → 执行中/T2 待令）

**Interfaces:**
- Consumes: Task 1/2 产物
- Produces: 索引登记态；T2/T3 待令声明（PR 描述+progress.md 最终状态块）

- [ ] **Step 1: 双 INDEX 更新**（四点）：① plans/INDEX 头部（最后更新日期+活跃 plan 数 1→3）与活跃列表补 #97+#98 两行——#97 系 2026-11-06 建档未登记的陈旧漂移（顺带清偿记 deviation），行内状态逐字镜像 specs/INDEX #97 现态防注册表分叉；② specs/INDEX #98「对应 plan」字段「待执行时建」→本 plan 路径+T0/T1 完成态；③ specs/INDEX #98 状态字段补「执行中（T0/T1 落地；T2 待实弹令）」；④ plans/ 根下另有 5 份已完结 spec 未归档 plan 文件（74-79 系）——仅记 deviation 不动（越权清理属 #97/工具链面）。
- [ ] **Step 2: Commit**: `git add docs/superpowers/plans/INDEX.md docs/superpowers/specs/INDEX.md && git commit -m "docs: spec98 plan 登记+T0/T1 完成态（T2 实弹窗待用户令）"`
- [ ] **Step 3: audit-T3.md**（fresh-context 子 agent）

**复杂度: leaf** ｜ **test_kind: N/A（登记）** ｜ 测试层级: N/A

---

## 验收覆盖表（spec §3 → task → 验证命令）

| spec 验收 | task | 验证 |
|---|---|---|
| 1. T0 探测报告（连通性+thinking 行为+预注册）落 docs/research/ | Task 1 | 报告文件在盘含 §锁定档位表/§预注册/§成本 三节；audit-T1.md |
| 2. T1 PR 合并（CI 全绿） | Task 2 + 阶段 7-10 | `just check` EXIT=0 + PR CI 全绿记录 |
| 3. T2 trace 对照表+判定书落 vol1-ledger（束7） | **本批外**（待用户实弹令） | spec r2.1-r2.4 预注册口径届时直接引用 |
| 4. 分叉落点登记（生产模型决策 or 新 spec 编号） | **本批外**（随 T3） | 同上 |

**G3.4 声明**: N/A——本批无生成产物评分场景。**F947 声明**: N/A——本批验收全部离线可执行（常量表断言+报告文件）；T0 探针系 spec 交付物本体非「验证性 dispatch」。

## Self-Review

- 覆盖：spec T0/T1 全落到 Task 1/2（含 r2.2 主备同批/夹具条款/r2.1 预注册准则三分支+病理区分度+stream 预算纪律）；T2/T3 边界显式声明 ✅
- 占位符：Task 2 Step 3 的 `<主档 input USD/M>` 等=Task 1 报告的运行期抄录位（T0 先行定值），非「TBD」式占位；两测试文件的同名常量系人工同步+**跨表 parity guard**（`set(PRICING)==set(MODEL_CONTEXT_LIMITS)`）兜底表间一致性 ✅
- 类型一致：PRICING/MODEL_CONTEXT_LIMITS 字典签名与现源一致；测试类名/常量名 Task 内自洽 ✅

## Plan 审查修订记录（阶段 5）

- 审查裁定 With fixes（3I+6M）→ 全修：I-1 Step 3 改 stream 首块信号+最坏情形预算+缺 key BLOCKED 出口；I-2 病理触发条件钉「pinned-at-cap」+4096 重探+不确定走默认启用；I-3 kill 臂配置继承（executor_config 注释+回滚条款）；M-1 (c) 单拒降级模式预注册；M-2 parity guard 替代表述；M-3 阈值 128_000；M-4 基线命令统一；M-5 去重复测试；M-6 Task 3 INDEX 机制四点补全。
