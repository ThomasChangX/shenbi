# 推理控制层审计：采样参数 / 模型路由 / 重试经济

> **Date:** 2026-08-01
> **Status:** Design
> **Severity:** 🟠 High（调用方式层的系统性浪费与盲点）
> **方法:** [`systematic-debugging`](archive/2026-07-19-06-llm-context-engineering-design.md) skill 四阶段（Root Cause → Pattern → Hypothesis → Implementation）
> **系列:** Token 效率全栈 audit（子 spec 1/3，隶属总纲 [`...read-write-consistency-audit-design.md`](2026-08-01-pipeline-read-write-consistency-audit-design.md) §0 分工）
> **依赖:** 总纲 spec（决策原则、跨 spec 根因簇图）；`executor_config.toml`；`src/shenbi/pipeline/dispatch_helper.py`；`src/shenbi/cost/pricing.py`
> **范围:** 本 spec 只审 **how the model is CALLED**（采样参数、模型选择、重试/截断处理），**不审** prompt 内容（见总纲）、不审输出侧浪费（见子 spec 3）、不审确定性替换（见子 spec 2）。
> **Purpose:** 把"模型怎么被调用"这一层的 10 类隐性浪费与盲点定位到根因——采样参数与任务类型错配、模型单点硬编码无路由、G4 重试全量重发、`finish_reason=length` 完全未检测致重试预算空烧——使调用层从"全 skill 同参数同模型"演进到"按任务类型分层调用"。

---

## 1. 背景

总纲 spec 审的是 prompt **内容层**（读/写/system prompt 重复）。但 LLM 调用成本 = 调用方式 × prompt 内容，调用方式层有独立的浪费面：

- 同一模型服务 73 个 task type 各异的 skill（长文生成 vs 判别打分 vs 聚合）
- 同一采样参数（temperature=0.7 / max_tokens=16384）服务差异 10× 的输出分布
- 重试时全量重发 prompt，无压缩、无预算计量
- 输出截断（`finish_reason=length`）完全未检测，截断输出被当成功写盘 → G4 必 FAIL → 全量重试 → 再截断 → 重试预算空烧

本 spec 用 systematic-debugging 四阶段逐一落证。

### 1.1 决策原则（继承总纲 §0）

质量 > token > 速度，但不应有浪费。**G4/gate 是唯一质量裁判**：任何调用层改动以 gate 仍 PASS 为前提；温度/模型/重试的调整若使 gate FAIL 即回滚。

---

## 2. 根因发现（Phase 1）—— 10 条，三子域

### 2.A 采样参数（sampling）

#### 2.1 21/24 review + 3/3 score skill 温度错配（用创意温度跑判别任务）

- **症状**：判别/打分类 skill 本该用低温（确定性），却跑了默认 0.7（创意温度）。
- **证据**：`executor_config.toml` 仅 6 个 skill 覆盖温度（drafting 0.85 / revision 0.6 / review-continuity 0.2 / review-anti-ai 0.15 / review-resonance 0.1 / foreshadowing-lifecycle 0.5）。skills/ 下有 **24 个 `shenbi-review-*`**，仅 3 个覆盖 → **21 个 review 落回默认 0.7**（`dispatch_helper.py:174-184` `_get_skill_temperature`）。**3 个 `shenbi-score-*`（最该确定的任务）零覆盖，全跑 0.7**。
- **根因**：温度覆盖是手动逐 skill 加的，无"按 task type 推断默认温度"的机制；score 类被遗漏。
- **分类**：纯浪费（判别任务高温既烧 token 又降一致性 → G4 重试概率升）。
- **浪费量**：间接——高温致输出方差大 → G4 FAIL 率升 → 重试（见 2.7）。score 类温度从 0.7→0.1 可降重试率。
- **质量影响**：高温判别 = 评分不稳；但 gate 仍可能 PASS（结构对、分数飘）。
- **假设**：score/review 类温度降至 0.1-0.2 后，同章 G4 一次通过率上升。
- **验证**：`pytest` 跑 score-volume 的 round，对比温度 0.7 vs 0.1 的 G4 首次通过率。

#### 2.2 `max_tokens` 双向错：review 头部空 62-75%，drafting 撑满并截断

- **症状**：全局 `max_tokens=16384`（`executor_config.toml:3`），对小输出 skill 是巨额头部空置，对 drafting 是撑满截断。
- **证据**：`_get_skill_max_tokens`（`dispatch_helper.py:187-197`）仅 drafting 覆盖（且值同默认=空操作）。实测输出分布（`novel-output/xinghuo-ranqiong/`，CJK ~1.5 字/token）：drafting AVG **15,787 tokens（96% 上限）**、review AVG **6,136（38%）**、state-settling AVG **4,109（25%）**。
- **根因**：max_tokens 无 per-skill 右对齐机制；drafting 撑满 = 输出本就 >16K 被截断；review/state-settling 空头部 = 无害但掩盖真实成本模型。
- **分类**：drafting 侧 = 质量风险（截断）；review 侧 = 计量盲点（非直接 token 浪费）。
- **浪费量**：drafting 截断的直接浪费见 2.7（重试空烧）。
- **质量影响**：drafting 撑满 → 截断 → G4 FAIL（见 2.7）。
- **假设**：drafting 的 max_tokens 提到 ≥实际输出 P99，截断消失，G4 首过率升。
- **验证**：统计 drafting 输出 token 分布 P95/P99，设为新上限；跑 round 对比截断率。

#### 2.3 `top_p` / `frequency_penalty` / `presence_penalty` 从未使用

- **症状**：三个标准采样杠杆全程默认，未针对重复倾向 skill 调。
- **证据**：grep `src/` + `executor_config.toml` + `skills/` 对三参数**零命中**；OpenAI 调用（`dispatch_helper.py:1323-1329`）只设 temperature/max_tokens/stream。
- **根因**：参数面未开放到 executor_config；重复倾向 skill（revision 重写、state-settling 重发累积）本可用 `frequency_penalty` 抑制。
- **分类**：潜在优化（非既存浪费）。
- **浪费量**：间接——重复输出可能触发 G4 文体检查 FAIL → 重试。
- **质量影响**：低。
- **假设**：revision 加 `frequency_penalty=0.3` 后，G4 "重复句式"类 FAIL 下降。
- **验证**：A/B 跑 revision round 对比。

### 2.B 模型路由（model routing）

#### 2.4 单点模型硬编码，无 per-skill 覆盖机制

- **症状**：73 个 task type 各异的 skill 全用同一模型。
- **证据**：`_DEFAULT_MODEL = "deepseek-v4-flash"`（`dispatch_helper.py:72`）；运行时 `os.environ.get(_ENV_LLM_MODEL, _DEFAULT_MODEL)`（`:1436`）一次性解析，**所有 dispatch 共用**。无类似 `_get_skill_temperature` 的 model 覆盖；`executor_config.toml` 无 `model` 键；`pricing.py:22` PRICING 仅一条。
- **根因**：从未设计分层路由；判别类（review/score，~30 skill）与聚合类（context-composing/state-settling，~8 skill）本可用更便宜/快模型，长文 drafting 才需大模型。
- **分类**：成本/延迟浪费（非 token 浪费，但属"调用方式"效率）。
- **浪费量**：review 类 667 dispatch × 6,136 output tokens 全用同一模型——若判别任务路由到便宜 reasoning 模型，单价可降。
- **质量影响**：取决于替代模型能力（需 G4 验证）。
- **假设**：判别类 skill 换更便宜模型后 G4 仍 PASS。
- **验证**：选 1 个 review skill，换模型跑 round，G4 对比。

#### 2.5 pro↔flash doc drift（计划文档与实现不一致）

- **症状**：归档 plan 写默认 `deepseek-v4-pro`，实代码是 `deepseek-v4-flash`，单价差 8-15×。
- **证据**：`docs/superpowers/plans/archive/2026-07-19-03-pipeline-cost-and-token-accounting-plan.md:13,30,55,134` 反复写 pro，甚至 pin 测试 `test_default_model_is_deepseek_v4_pro`（L52）；实代码 `dispatch_helper.py:72` flash；`pricing.py` 用 flash 单价（$0.14/$0.28 vs plan 的 $1.10/$4.40）。
- **根因**：代码降级到 flash（更便宜）后未回写 plan，文档漂移。
- **分类**：文档缺陷（非直接浪费，但使成本估算失真）。
- **验证**：grep 确认 plan vs code 不一致；应以代码为准订正 plan。

### 2.C 重试与截断经济（retry & truncation economics）

#### 2.6 G4-FAIL 重试全量重发 prompt，无压缩

- **症状**：G4 FAIL 后重试把完整 system+user prompt 重发。
- **证据**：`chapter_loop.py:2770-2800` 重试时 prompt 从零重建（`prompt = f"Execute {skill}..."`），`_build_skill_prompt` 重组全量 system+user；**无"只发失败检查项 + 相关摘录"路径**。
- **根因**：重试视为独立 dispatch，无增量上下文模式。
- **分类**：重复传输（属总纲 Cluster C）。
- **浪费量**：每次重试 = 一次全量 dispatch token；N 次重试 × 全量 prompt。
- **质量影响**：无（重发不降质量，但若根因是 prompt 本身问题，重发无效）。
- **假设**：重试若只发失败检查项 + 相关段落摘录，token 降至 ~20-30% 全量。
- **验证**：mock 一个 G4 FAIL，测"全量 vs 增量"prompt 字符数比。

#### 2.7 enriched retry feedback 只增不减

- **症状**：重试反馈是**追加**到全量 prompt，而非替换。
- **证据**：`_enrich_g4_feedback`（`chapter_loop.py:496-521`）构建反馈块，`chapter_loop.py:2782-2791` `prompt += "...CORRECTIVE FEEDBACK..."` 追加；方向永远是"加上下文"，无"裁剪"。
- **根因**：架构方向锁定为"重试加指导"，未考虑"重试精简输入"。
- **分类**：重复传输（与 2.6 同簇）。
- **浪费量**：每次重试比首次多 ~70 token/失败检查项。

#### 2.8 429 重试 thundering herd（结构风险）

- **症状**：并行审计波遇 429 时，N 个 worker 近同步退避再发，可能加剧限流。
- **证据**：`parallel_dispatch.py:25` `MAX_CONCURRENT_REVIEWS=4`；`:28` `MAX_RETRIES=2`；退避 `2.0**attempt + uniform(0,1.0)`（`:116`）——抖动仅 0-1s 叠在 2^attempt 上，worker 近锁步；无共享限流协调器、无 token bucket。两层重试叠加：streaming 层（`dispatch_helper.py:1354` 3 次）+ parallel 层（2 次）。
- **根因**：退避抖动幅度相对基数太小，不 decorrelate worker。
- **分类**：延迟/稳定性风险（非直接 token 浪费，但失败重发烧 token）。
- **验证**：模拟 429 注入，观察 worker 退避时序。

#### 2.9 `finish_reason=length` 完全未检测 —— 最关键盲点

- **症状**：输出因 max_tokens 截断时，系统**检测不到**，截断输出被当成功写盘 → G4 必 FAIL（结构不完整）→ 触发全量重试 → 再截断 → 重试预算空烧。
- **证据**：
  - `_call_llm_streaming`（`dispatch_helper.py:1307-1351`）返回的 `stop_reason` **只来自 `early_stop_patterns` 子串匹配**（`:1337-1344`），**从不查 API 的 `finish_reason`**（OpenAI chunk 的 `choices[0].finish_reason`，截断时为 `"length"`）。
  - `stop_reason` 在 `:1468-1469` 仅 `log.info` 后丢弃，无分支处理 length。
  - 截断的 `output_text` 直接流入 `_write_parsed_outputs`（`:1481-1488`）写盘。
  - G4 在截断内容上跑（`chapter_loop.py:2836-2838`）→ 结构缺陷 FAIL → 重试（2.6）→ 同 cap 再截断。
- **根因**：`stop_reason` 命名误导（实为 early_stop，非 finish_reason）；从未接 finish_reason 检测分支。
- **分类**：纯浪费 + 质量风险（最严重——重试预算被不可解决的问题空烧）。
- **浪费量**：drafting AVG 96% 上限（2.2），截断高频；每次截断 → G4 FAIL → 全量重试（2.6）→ 再截断。`max_revision_retries=3`（`state.py:64`）全空烧。
- **质量影响**：高（截断章节是残缺的）。
- **假设**：检测到 `finish_reason=length` 时直接提 max_tokens 重发（而非全量同参重试），可消除空烧。
- **验证**：mock 一个 length 截断，对比"当前行为（重试同参）vs 提 cap 重发"的最终成功率。

#### 2.10 并行 SharedAuditContext 省 disk-IO 不省 token（折叠自原待审维度 G）

- **症状**：普遍误解 SharedAuditContext 省 token，实只省 disk read。
- **证据**：`audit_context_cache.py:45-81` 一次性预算共享字段；`dispatch_helper.py:554-566` 注入 `raw_inputs[fname]` 覆盖，跳过 read_text。但**每个审计器仍把共享上下文全文塞进自己的 user prompt**（`:674-680` 逐 dispatch 拼输入）→ token 仍每器全发。仅 provider 端 prompt cache（总纲 §3.9）能省 token，且仅 API 路径。
- **根因**：cache 设计目标是 disk-IO + prompt 组装，非 token 传输。
- **分类**：认知澄清（非既存浪费，但避免后续优化误判）。

---

## 3. 模式分析（Phase 2）—— 3 个根因簇

| 簇 | 成员 | 共同根因 |
|---|---|---|
| **采样错配** | 2.1 / 2.2 / 2.3 | 采样参数面按"逐 skill 手动覆盖"维护，无"按 task type 推断默认"机制 → 判别类漏覆盖跑创意参数 |
| **模型单点** | 2.4 / 2.5 | 从未设计分层路由；文档与代码漂移 |
| **重试经济** | 2.6 / 2.7 / 2.8 / 2.9 | 重试视为无状态全量重发；不检测截断；退避不 decorrelate |

跨 spec 簇（归总纲 §1b）：2.6/2.7 属 Cluster C（重复传输）；2.9 属 Cluster A（dead-wiring——finish_reason 检测缺失是接线盲点）。

---

## 4. 假设与验证（Phase 3）

每条 finding 的假设+验证见 §2 各条"假设/验证"字段。关键三条：

- 2.1：score 温度 0.7→0.1 后 G4 首过率升
- 2.2/2.9：drafting max_tokens 提至 P99 + 检测 length 截断，空烧消除
- 2.4：review 类换便宜模型 G4 仍 PASS

---

## 5. 修复方案（Phase 4）

### 5.1 P0（纯浪费/盲点，修后 gate 必 PASS 或质量升）

| finding | 修复 | 落地点 | 验证 |
|---|---|---|---|
| 2.9 | `_call_llm_streaming` 读 chunk 的 `finish_reason`；`=="length"` 时提 max_tokens 重发（非全量同参重试），并 log `length_truncation` | `dispatch_helper.py:1307-1351, 1468-1469` | mock length 截断，确认重发提 cap 而非同参 |
| 2.1 | score-* 三 skill 加 `temperature=0.1` 覆盖；未覆盖的 21 review 按任务类型批量设（判别类 0.1-0.2） | `executor_config.toml` | 跑 score round 对比 G4 首过率 |
| 2.2 | drafting `max_tokens` 提至输出 P99（实测后定，预估 ≥32768） | `executor_config.toml:5-7` | 截断率降至 0 |

### 5.2 P1（契约/机制，需小范围 gate 验证）

| finding | 修复 | 风险 |
|---|---|---|
| 2.4 | `executor_config.toml` 加 per-skill `model` 键 + `_get_skill_model`（类比温度）；判别类先试点 1 个 review skill 路由便宜模型 | 中（替代模型能力需 G4 验证） |
| 2.5 | 订正 plan 文档 pro→flash（以代码为准） | 无 |
| 2.6/2.7 | 重试增量模式：G4 FAIL 时只发失败检查项 + 相关段落摘录（非全量重发） | 中（需保证摘录覆盖根因） |

### 5.3 P2（效率，需全量 G4 验证）

| finding | 修复 | 风险 |
|---|---|---|
| 2.3 | 开放 `top_p`/`frequency_penalty`/`presence_penalty` 到 config；revision/state-settling 试点 frequency_penalty 抑重复 | 低 |
| 2.8 | parallel 退避抖动幅度加大（decorrelate worker）；或引入共享 token bucket | 中 |

### 5.4 显式不动（证据不足）

- 2.10 是认知澄清，非缺陷——SharedAuditContext 省 disk-IO 是其设计目标，不该期待它省 token。

---

## 6. 验证标准（数值化）

| 标准 | 当前 | 目标 |
|---|---|---|
| `finish_reason=length` 检测 | 不检测 | 检测 + 提 cap 重发 |
| score-* 温度覆盖 | 0/3 | 3/3（0.1） |
| drafting 截断率（输出 token / max_tokens >100%） | AVG 96% | <P99 |
| 判别类模型路由 | 0 skill 分层 | ≥1 试点 PASS |
| `just check` | PASS | PASS |

---

## 7. 铁律（4 条）

1. **判别任务不用创意温度。** score/review 类默认温度必须 ≤0.2；只有长文生成可用 ≥0.7。温度覆盖按 task type 推断，不靠手动逐 skill 记。
2. **截断必须检测。** 任何 `finish_reason=length` 必须触发"提 cap 重发"而非"同参全量重试"；未检测截断 = 重试预算的定时空烧。
3. **重试不是无状态全量重发。** G4 FAIL 重试应发增量（失败项 + 摘录），非全量 prompt；重试预算是被计量资源。
4. **模型按 task type 分层。** 判别/聚合/长文生成三类用不同模型层；单点模型服务全部 task type 是成本/质量双失配。

---

## 8. 依赖关系图

```
总纲 spec（决策原则、Cluster A/C 归口）
    │
    ├─ 2.1/2.2 采样 ──► executor_config.toml
    ├─ 2.4/2.5 模型 ──► pricing.py + dispatch_helper.py
    ├─ 2.6/2.7 重试 ──► 属总纲 Cluster C（重复传输）
    ├─ 2.9 截断盲点 ──► 属总纲 Cluster A（dead-wiring）+ 关联输出侧 spec F8（重试放大）
    └─ 2.10 澄清 ──► 归总纲（折叠）

P0 实施前需另写 plan 并批准（本 spec 是 design）
```
