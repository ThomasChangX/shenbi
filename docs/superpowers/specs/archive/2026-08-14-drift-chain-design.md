> **Date:** 2026-08-14 | **Status:** Done (PR #70 · 2026-08-24 · R2/R4 面供 #32 核销) | 原 Design (Revised 2026-08-24) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** skill_utils/drift_detection/ + pipeline/chapter_loop.py + pipeline/hook_planting.py + records/ | **核心洞察:** 语言漂移 3 层干预全链失效（未接线 + 门控 + 吞异常），且真实格式与检测假设分叉

# Drift 检测干预链失效

> **与 #32（C6 drift/CJK 度量）分工边界（2026-08-24 定稿）**：本 spec 拥有 **R1 接线、R3 门控、R5 记录格式链**；#32 拥有 **度量数学与阈值语义**（其 T2 对话塌陷边界 = 本 spec R2；其 T4 异常面 = 本 spec R4）。执行冲突处置：**本 spec 先行实施 R2/R4 的最小形态（见各条修复定稿）并落地测试，#32 执行时核销其 T2/T4 中已被覆盖的面，只做度量单源/影子模式/CJK 面**。跨轮 F 编号碰撞（#32 的 F602=本文 F601，#32 的 F601=cjk 引号）归 #49（C35）ID 命名空间隔离管辖，不在本 spec 重编号。注：#32 T4 现文仍自claim 修同一吞错面（其文另引 C13 为吞错面归属）——本 spec R4 落地后，#32 下次修订须在其 T4 加核销注记（边界是单向声明的，待 #32 侧回写闭合）。
>
> **基线 canonical 声明（R1/R5 与 #32 T3、#46(C7) 的对齐点）**：`style/linguistic_baseline.json`（per-mille schema，`establish_baseline` 唯一写方）为 chapter_loop 漂移检测的 canonical 基线；`linguistic_drift.py` 内 `_load_baseline` 写的第二条 `context/linguistic_baseline.json`（`dialogue_ratio` 非 per-mille schema）属 #32 F617 双基线收敛面，本 spec 不动它，仅在接线时不新增对它的依赖。

## R1 · establish_baseline 零调用（F602, P1；从属 F389）
- 证据：baseline.py:24 唯一写 `style/linguistic_baseline.json` 的函数全仓零调用；chapter_loop.py:2046-2050 每章走 no_linguistic_baseline 分支；plan 07-19-07 Task 5a 明确要求接线
- 修复：chapter 3 后在 pipeline 内部步骤接线 `establish_baseline`（纯确定性 Python，无 LLM dispatch——成本维度合规）；基线路径=canonical `style/linguistic_baseline.json`
- **验收：第 4 章起 baseline 文件存在**——测试锚点：`tests/unit/pipeline/` 用真实章节 fixture（`tests/fixtures/` 真实 skill 输出，G0.9）驱动 chapter 推进至 ch4，断言文件生成

## R2 · 对话塌陷 off-by-one（F601, P1）
- 证据：linguistic_drift.py:215 `max(...,5.0)` vs :218 `> 5.0` → 对话塌陷 is_drift 恒 False
- 修复：消除双字面量耦合——提取共享阈值常量（模块级 `_DEVIATION_DRIFT_THRESHOLD = 5.0`），触发条件改 `>=`（或显式 `triggered` 布尔）；禁止 `5.01` 魔数补丁。**边界语义（> vs ≥）与 #32 T2 的阈值裁决对齐：本 spec 只修可达性（塌陷能触发），阈值重标定归 #32**
- **验收：dialogue ratio<0.2 → is_drift=True**——测试锚点：`tests/unit/skill_utils/drift_detection/test_linguistic_drift.py` 新增纯 dialogue-collapse 用例（当前测试只覆盖 system-term-density）

## R3 · severity 阶梯被 is_drift 门控（F612, P1）
- 证据：chapter_loop.py:2056 `if result.is_drift:` 包裹全部干预；baseline 污染时 severity=ESCALATE 但 is_drift=False → 安全网静默放行
- 修复：按 `severity != NONE` 驱动干预。**安全前提（须以测试固化）**：`detect_drift` 保证 `is_drift=True ⇒ severity ≥ WARN`（linguistic_drift.py:221-229 分支结构），故不存在 NONE+is_drift 组合，改门控不放大 NONE 面。附带：`DriftResult.message`（linguistic_drift.py:231-238）在 severity=ESCALATE + is_drift=False 时仍报 "No linguistic drift detected"，改为按 severity 生成消息（否则暂停审查者看到自相矛盾信息）
- **验收：stm 110‰ 触发 ESCALATE**——测试锚点：`tests/unit/pipeline/test_drift_intervention.py` 补 stm=110、is_drift=False 组合用例断言 raise
- 顺序依赖：R1 之后（否则 baseline 缺失在 chapter_loop.py:2050 提前返回，验收不可观测）

## R4 · 调用点吞 DriftEscalationError（F620, P1）
- 证据：chapter_loop.py:2066 raise；唯一调用点 :2853-2861 裸 `except Exception` 吞 raise（注释自称 non-blocking 与函数内 raise 矛盾）
- 修复：**定稿为按异常类型处理，禁止删 raise**（删 raise = 永久拆除 ESCALATE 暂停安全网，与 R3 语义矛盾）：`except DriftEscalationError: raise`（传播到 checkpoint 暂停逻辑），其余异常保持 non-blocking log.warning
- **验收：ESCALATE 到达暂停逻辑**——测试锚点：`tests/unit/pipeline/` 断言 DriftEscalationError 从 step 执行路径向外传播（不被降级为 warning）；同时断言普通异常仍不阻塞
- 顺序依赖：R3 之后（raise 路径先可达）

## R5 · 判据 12 真实格式分叉（F637, P1）
- 证据：真实 pending_hooks.md 无 `## hooks` YAML 块与 `## 活跃伏笔` 表 → 检测恒空转；测试 fixture 格式与真实分叉。**根因补全（阶段 3 审查）**：`_append_to_pending_hooks`（hook_planting.py:204-269）只读 frontmatter 且整文件重写为 frontmatter-only，静默摧毁既有 body 块/表——破坏性重写才是格式分叉的机制
- 修复：**定稿 Branch A（恢复权威格式）+ 双源写**：canonical 格式 = frontmatter `hooks` 列表**保留** + `## hooks` body 块 + `## 活跃伏笔` 表三部分并存——frontmatter 保留的原因：`pipeline/context_curation.py:361`（`_read_pending_hooks`，静默空回退喂每章上下文）、`pipeline/review_checklist.py:319`、`chapter_loop.py:1288`（`_count_triggered_hooks`）三个 frontmatter 读取方，丢 frontmatter 会让它们静默失去全部 hook（空回退掩盖失败、无门禁拦截）；body 段与 `records/parser.py:18-49`、`records/drift.py:23`、`audit/write_audit.py` 三个 body 消费方对齐。`_append_to_pending_hooks` 改为保留既有全部段落的合并写（禁止 frontmatter-only 整写摧毁 body）；**迁移为并集合并**（源 = frontmatter `hooks` ∪ body 源；body 源按存量形态分派——有 `## hooks` YAML 块用 `parse_records`，无块的 body-only 生产态（`truth_index.py:171-175` 记载：自由文本正文里的 `P0-N`/`H\d+`/`M\d+` hook ID）用 truth_index 的 Source-2 ID 扫描兜底，两者皆适用 `records/drift.py` 的 `parse_markdown_table` 读既有表——只用 `parse_records` 会对 body-only 文件得空集、静默清空记录，正是要防的失败态；`parse_records` 是迁移后稳态的 body 源）；同 hook_id 冲突时 **field-level 合并、body 值优先**（body YAML 记录字段少于 frontmatter 富载荷——state/last_reinforced/max_distance 等，record-level 整替会静默丢 frontmatter-only 字段）→ 合成三段双源 canonical 写回（**记录归一化**：并集内**每条**记录按 drift 表 8 列集（`_MD_HEADER_TO_KEY`：id/type/dimension/subtlety/escalation_curve/plant_chapter/operation/state）补齐缺失列——ID-only 记录 `state: "PENDING"`、其余缺列 `""`；部分填充记录的缺列同样补 `""`（`_values_equal(None,"")` 为 False，列缺省 None 会自造假 drift）——且 `## 活跃伏笔` 表直接由同一记录集生成，YAML 块与表同源故 `detect_cross_section_drift` 恒空；`_append_to_pending_hooks` 的去重读同样走并集源，不只读 frontmatter）；序列化确定性（sorted-key YAML dump 对齐 `serialize_records`、表列序固定、数值格式统一、**记录列表序 = 首次出现序（frontmatter 先、body 后）**）保证迁移幂等；注：`_count_triggered_hooks` 文本扫描回退在双源文件 frontmatter 损坏路径可能双计（仅影响告警计数启发式，记录不改）；`truth_index.py:167-182` 的双源读取天然兼容。Branch B（改 parser）否决——会搁浅 records/drift.py 与 write_audit.py 且破坏 `is_idempotent` 往返契约
- **验收：真实格式文件检出 drift**——测试锚点：用 `tests/fixtures/` 真实 pending_hooks 产物驱动 parser+drift 检测非空；writer 往返（append 后再 parse）幂等用例 + append 后 `detect_cross_section_drift(...) == []`（writer 不得自造 hooks 块↔活跃伏笔表失配——正是该检测在审计期执法的不变量）
- 顺序依赖：独立，但排最后（改动面最大）

## 执行顺序（阶段 3 定稿）

R1 → R2 → R3 → R4 → R5（R3/R4 验收依赖 R1/R2 先落地；每条独立 conventional commit：`fix: R<N> …`）
