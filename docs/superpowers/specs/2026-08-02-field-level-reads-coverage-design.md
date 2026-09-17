# 字段级 reads 覆盖率：三大 truth 文件的精准切片

> **Date:** 2026-08-02
> **Status:** Design (Revised 2026-09-18 — SDD #65 价值门 REWRITE：Layer B dispatch 死线修复前置；消费面重推（context-composing 退出主链）；volume_map 提取器改选 `_shared` 族；铁律 1 落证改三方交集；度量全面离线化。修订证据见本 spec 各节 file:line)
> **Severity:** 🟡 Medium（P1 契约一致 + 效率混合；浪费量大但字段名匹配有准确性风险）
> **方法:** [`systematic-debugging`](archive/2026-07-19-06-llm-context-engineering-design.md) skill 四阶段（Root Cause → Pattern → Hypothesis → Implementation）
> **系列:** Token 效率全栈 audit（契约层补漏，承接已归档总纲 [`archive/2026-08-01-pipeline-read-write-consistency-audit-design.md`](archive/2026-08-01-pipeline-read-write-consistency-audit-design.md) §3.7 + §6.2 P1 第二项；PR #39 plan T8 延后项；spec #28 R2 显式接力——其归档文本 :48「token 面优化归 spec #65 的 extractor 方案」）
> **依赖:** 已归档总纲（§3.7 finding、§6.2 P1 分级）；`src/shenbi/contracts/fields.py` `filter_to_fields`（:113）；`src/shenbi/contracts/loader.py` `_validate` reads 归一化（:211-218）+ `read_fields` 旁路（:52/:205/:217）；`src/shenbi/pipeline/dispatch_helper.py` `_build_skill_prompt` read 循环（:601/:668-702）；`src/shenbi/pipeline/context_assemble.py` `_load_volume_context`（:207）+ `src/shenbi/pipeline/_shared.py` 提取器族；`skills/shenbi-{review-group-factual,chapter-planning}/SKILL.md`；git 历史真实产物（`git show d120a444^:novel-output/xinghuo-ranqiong/...`，生产树已按 spec #63 T1504 出库）
> **范围:** 本 spec 只审 **字段级 reads 过滤（Layer B）的覆盖率提升 + 其 dispatch 死线修复**——为 power_system.md / volume_map.md 在现行消费方的 reads 声明精确切片，使 dispatcher 只发相关 section 而非全文。**不审** P0 纯浪费（PR #39 已清）、不审 cache/示例外置（P2 spec #6 已 Done，其 cache 裁决不实施）、不审采样/模型/重试（#3）、不审输出侧（#5）、不审确定性替换（#4）、chapter-N.md 显式不管（§2.3）。
> **Purpose:** 把总纲 §3.7 从"发现+提议"推进到"可实施"。原 spec 假设 Layer B 机制已工作、只需声明 fields——价值门驳斥证明该假设不成立（§1.5 死线）：fields 声明在 dispatch 路径从未生效。本 spec 修订后 = 死线修复（机制）+ 消费面切片（调优）两层。

---

## 1. 背景：字段级过滤机制现状（2026-09-18 修订）

### 1.1 设计机制 vs 实际行为

**设计机制**（AGENTS.md 记载）：dispatcher 的 `_build_skill_prompt` read 循环对每个 read 条目，dict 形（`- file: ...\n  fields: [...]`）应调 `filter_to_fields(content, fields, path)`（`contracts/fields.py:113`）只提取匹配的 `## ` section；string 形全文发送。逃逸门：任何声明的 field 在文件中无匹配 → 返回全文 + structlog WARN（事件名 **`field_filter_missing_fields`**，`fields.py:79-84`；any-missing 语义，F218/spec #9 R3）。

### 1.5 发现（本次修订新增）：dispatch 路径字段过滤是先天死线

`load_contract` → `_validate`（`src/shenbi/contracts/loader.py:211-218`）把 dict-form reads **归一化为纯字符串列表**：`paths.append(path)`，fields 移入旁路 dict `read_fields[path]`。`_build_skill_prompt`（`dispatch_helper.py:643` load_contract → `:667` `contract.get("reads")`）取到的 reads **恒全为 string** → `:669` 的 `isinstance(read_path_entry, dict)` 分支永不触发 → fields 恒 `[]` → `:699` 的 `filter_to_fields` 调用**在全部 dispatch 路径不可达**。

- **行为复现证据**（2026-09-18，离线直调 `_build_skill_prompt('shenbi-chapter-planning', ...)`，零 LLM）：chapter-planning 声明了 `truth/chapter_summaries.md` fields `[已完成章节]`，未声明的 `## OTHER_STUFF` section 仍完整进入 user_prompt；structlog 零 `field_filter_*` 事件。
- **历史**：dict 分支 2026-07-20 引入（dd1fc629，PR #19），晚于 loader 归一化（2026-06-22）——**先天死线，非回归**。
- **波及面**：AGENTS.md「The dispatcher filters file content to only declared fields」声明失效；spec #28 归档文本 :14「T1/F224 管线过滤接线已正确处理且测试覆盖」声称不成立（`tests/unit/pipeline/test_field_filtering.py:1-7` 自明只直测纯函数、不测 dispatch 循环）。
- **fields 的唯一真实消费**：`read_fields` 旁路 → `_collect_declared_truth_fields`（`dispatch_helper.py:1685`，genesis 模板播种）——声明不是死的，但 dispatch 过滤这半边是死的。

**推论：本 spec §3 的任何 fields 声明，若不先修死线，都是运行时 no-op。死线修复是 §3/§4 的共同前置（§3.0）。**

### 1.2 覆盖率现状（2026-09-18 复测）

302 条 read 中 dict-form `fields:` 仅 36 条（11.9%），74 skill 中 60 个从不用字段过滤。三大文件在**现行消费方**中零 fields 声明：

| 文件 | 体积（git 历史实测） | 现行消费方（contract.reads） | 当前形态 |
|------|------|---------------|----------------|
| `world/power_system.md` | 28,808B | `review-group-factual`（string 全文；主链 step 9 唯一读者）。`review-world-rules` 已 RETIRED（SKILL.md:21-22 DEPRECATED 标记、src/shenbi 零 dispatch 引用、test_audit_layer.py:409 断言 not in active）不入消费面 | ❌ 零 fields |
| `outline/volume_map.md` | 26,334B | 10 skill 字面读者（chapter-planning/foreshadowing-plant/foreshadowing-lifecycle/pacing-design/plot-thread-weaver/review-arc-payoff/score-volume/sequel-writing/volume-outlining/book-spine-init），全部 string；另有 `world/*.md`/`outline/*.md` glob 读者（foundation-review/snapshot-manage/truth-sync）不在此表——glob 展开逐文件、本 spec 不动 | ❌ 零 |
| `chapters/chapter-N.md` | ~21.5KB/章 | 33 读者（31 string + 2 dict），几乎全为审计波 review 技能 + revision/后处理；**drafting 主链已迁移**（chapter-drafting 读 `context/chapter-N-context.md`，不读前章全文） | 本 spec 显式不管（§2.3） |

**消费面修订**（原 spec 以 2026-08-02 主链为准，已失效）：
- `context-composing` 已退出 power_system/volume_map 消费面——其 reads 重构为分层 truth 文件族（book_spine/book_strata/volume_summaries/arcs/arc-N，全 fields 化），且该 skill 已被确定性 curation 替代出主链（`chapter_loop.py:1550` "Replaces the shenbi-context-composing LLM call"；仅 user-routable，chapter_loop.py:133）。原 §3.1/§4.2 表格中 context-composing 行**全部作废**。
- `review-world-rules` **已 RETIRED**（SKILL.md:21-22 "Superseded by shenbi-review-group-factual (2026-07-19)"；src/shenbi 零 dispatch 引用；test_audit_layer.py:409 断言其 not in active）——原 §3.1 表格该行**作废**，不为其声明 fields（零 dispatch 路径 = 零生产收益，且违本 spec 自己的死线纪律）。
- 主链每章消费者：power_system → **review-group-factual**（CHAPTER_STEPS step 9，`chapter_loop.py:210-218`）；volume_map → **chapter-planning**（step 2）。

### 1.3 浪费量（修订口径）

每章主链浪费 ≈ power_system 全文 ×1（review-group-factual 审计，~28.8KB）+ volume_map 全文 ×1（chapter-planning，~26.3KB）+ 本章全文 × 审计技能数（chapter-N 面，非本 spec）。power_system + volume_map 两项合计 ~55KB/章可削减至 ~16-17.5KB（§3.1 4-field 实测 15,500B + §4 卷节点 500B-2KB；子集终值 plan 定稿后联动重算，§7 同）。genesis 阶段另有 5 个 skill 全文读 volume_map（string 读不经 extractor，§4.3）。原 spec「三大文件 ~86KB/章、累计 200-400KB/章」口径基于 drafting 全文读前章的旧主链，已失效。

---

## 2. 根因发现：字段名匹配的三类风险（证据更新）

### 2.1 风险 A：volume_map 的 section header 是动态的（存活）

git 历史真实文件（`git show d120a444^:novel-output/xinghuo-ranqiong/outline/volume_map.md`，26,334B）的 `## ` header 为卷标题（`## 第一卷：觉醒之火（第1-15章）`…`## 汇总`），每本书不同——不能用固定 field 名匹配。

**结论（修订）：** volume_map 不适合 `fields:` 过滤（原判断存活），接入点 = 通用 read 路径的**提取器**（§4）。且提取器**不复用**原 spec 点名的 `_extract_volume_chapter`（`pipeline/audit_context_cache.py:125`）——它是 C28 R2 drop 后的零消费者死输出（`ctx.volume_context` 零下游消费，:103-104 注释自证；仅 tests/unit/pipeline/test_c15_wave_and_context_branches.py:87-94 对死字段直测）。正确抽象已存在且活跃：`context_assemble.py:207` `_load_volume_context` + `_shared.py` 提取器族（运行时卷边界 `read_volume_boundaries`、`_resolve_volume_at_runtime`、章节点、跨卷桥），测试 5+2 个（test_context_assemble.py:289-316、test_cn_extract.py:61-105）。

### 2.2 风险 B：power_system 的 section header 稳定集 = 生产者模板 8 个（修订）

`power_system.md` 的权威生产者是 `shenbi-power-system`（genesis step 10），其 SKILL.md 输出模板（:120-185）硬编码固定 header：**总览 / 等级表 / 进阶规则 / 能力边界 / 代价机制 / 力量天花板 / 跨级战斗参考 / 力量体系设计汇总**（8 个）。git 历史真实文件（xinghuo-ranqiong，28,808B）9 个 header = 模板 8 个 + 「与世界观核心主题的关系」——后者**无生产者背书**（全仓唯一出现处是本 spec 自身原文，系运行时 LLM 自由发挥），不入安全集。合成 fixture `tests/fixtures/world-power-system-example.md` 的第 9 个 header 又是另一个（「章节里程碑映射」）。另一生产者 `shenbi-world-extraction`（反向提取 writes）模板 header 与 power-system **不同名**（等级表/进阶条件/能力边界/代价）——两生产者交集仅 等级表+能力边界。

**安全字段键集 = 生产者模板 8 个 ∩ 真实文件 ∩ 现行消费方需求。** fields 声明必须限制在模板 8 个内。

### 2.3 风险 C：chapter-N.md 无 section 可过滤（存活，叙事更新）

chapter-N.md 正文是连续 prose，无 `## ` section。其 drafting 主链浪费已被后续演化解决：chapter-drafting 读 `context/chapter-N-context.md`（context-composing→确定性 curation 的产物）而非前章全文。剩余读者（33 个：审计波 review 技能、revision、后处理）读的是**本章**内容——审计对象本身，不可切。**本 spec 不处理 chapter-N.md**（原裁决存活；原「归 P2 #6」的引用已过时——#6 已 Done，二者都不需要再处理此面）。

### 2.4 修正后的可实施范围（修订）

| 文件 | 可字段过滤？ | 本 spec 处置 |
|------|------------|-------------|
| `power_system.md` | ✅ 模板 8 header | **§3：修死线（§3.0）+ 现行消费方声明 fields** |
| `volume_map.md` | ❌ 动态卷标题 | **§4：`extractor:` 契约字段接 `_shared` 族提取器**；范围 = chapter-planning（主链）+ genesis 兜底 |
| `chapter-N.md` | ❌ 连续 prose | 不在本 spec 范围（剩余读者是审计对象） |

---

## 3. Finding：Layer B 死线修复 + power_system.md 字段级声明

### 3.0 前置：修 dispatch 死线（新增，机制层）

`_build_skill_prompt` read 循环从 `load_contract` 的归一化 string reads 取数，永远看不到 dict 形。修复方向（plan 阶段定稿）：read 循环按 `read_fields` 旁路查表——`fields = contract.get("read_fields", {}).get(read_path, [])`（旁路已存在且是 fields 的既有权威载体，`_collect_declared_truth_fields` 同源），dict 分支移除或改为断言。**查表键 = 占位符解析前的契约路径**（read 循环在 :680-684 会把 read_path 经 `resolve_or_skip_ctx`/glob 展开改写——查表必须在解析前，`read_fields` 的键是契约原始路径）。**禁止**反向改 loader 保留 dict（会破坏 sync_contracts/lint 等全部下游消费者对 string reads 的既有假设）。

**验收：** 行为级——直调 `_build_skill_prompt`（fixtures 输入，零 LLM）：声明 fields 的 read，未声明 section 不进 prompt；structlog 无 `field_filter_missing_fields`（fields 全匹配）或恰在该场景出现（负向用例）。回归——既有 4470 tests 全绿；`tests/unit/pipeline/test_field_filtering.py` 补 dispatch 循环级用例（现状 :8 自明不测）。

### 3.1 修复方案：现行消费方 fields 声明（重推）

按消费方 SKILL.md body 实际需要（body 是 fields 子集的依据——概念名 → 安全字段键集映射）：

| skill | body 依据 | 应声明 fields（模板 8 个内） | 量级（真实文件实测） |
|-------|----------|-------------|------|
| `review-group-factual`（主链 step 9，唯一活消费方） | body :133「战力体系=不可逾越的天花板」、:141「检查角色等级上限、能力使用代价、跨等级对决规则」 | `[力量天花板, 代价机制, 跨级战斗参考, 能力边界]` | 28,808B → 15,500B（54%，`filter_to_fields` 直测） |

（原表 context-composing 行作废——退出消费面；原 review-world-rules 行作废——RETIRED 零 dispatch（§1.2）；子集终值在 plan 阶段按 body 精读定稿，§7 目标随子集联动。）

### 3.2 验证（离线化修订）

- 字段名对照安全集（§2.2 模板 8 个）——plan 实施时 grep 生产者模板 + git 历史真实文件字节匹配确认（`filter_to_fields` 的 NFKC 归一化处理全角/空白差异，header 文本本身须对得上）。
- **lint 样本接线（防漂移）**：`scripts/lint_contract_fields.py` 的 `EXAMPLE_FIXTURES`（:53-86）现无 `world/power_system.md` 条目——不补则新声明零样本 vacuous skip、三方落证沦为一次性人工检查。实施时加 `"world/power_system.md": [FIXTURES_DIR / "world-power-system-example.md"]`（该 fixture 含模板 8 个 header 全集，生产者模板改名将直接 lint 红）。
- 逃逸门验证改离线：直调 `filter_to_fields`（或修死后直调 `_build_skill_prompt`）断言零 `field_filter_missing_fields` WARN——**事件名以 `fields.py:79-84` 实现为准**（原 spec 写的 `field_not_found` 不存在）。
- G4 对 review-group-factual 仍 PASS（G4 不校验 reads 面——驳斥 B7 核实；跑 G4 确认契约变更无副作用。注意 G4 PASS **不构成**内容充分性证据——它只证契约面无副作用）。

### 3.3 度量（离线化修订）

改前 vs 改后，直调 `_build_skill_prompt('shenbi-review-group-factual', fixtures 树, ...)` 量 `len(system_prompt + user_prompt)` 字节与 `estimate_prompt_tokens`（`src/shenbi/cost/estimate.py` 纯函数）——power_system 项预期 28,808B → 15,500B（4-field 子集实测；子集终值 plan 定稿后 §7 目标联动重算）。**不触发真实 dispatch**（核心原则 8；TokenLedger 真实行需 dispatch，禁用）。

---

## 4. Finding：volume_map.md 提取器接入通用 read 路径（选型修订）

### 4.1 现状（修订）

`_shared.py` 族提取器（`read_volume_boundaries`/`_resolve_volume_at_runtime`/章节点/跨卷桥）已由 `context_assemble._load_volume_context`（:207）用于 step 3 确定性 context 装配（route-c → `context/chapter-N-context.md` → drafting 消费）——**drafting 侧的卷需求已覆盖，不重复做**。但通用 read 路径（dispatcher `_build_skill_prompt`）无提取器：chapter-planning（主链 step 2）每章全文读 volume_map（~26.3KB）；genesis 阶段 5 个 skill（volume-outlining/pacing-design/plot-thread-weaver/foreshadowing-lifecycle/book-spine-init，chapter=None）全文读是既成事实语义（§4.3 兜底）。

### 4.2 修复方案（选型修订：提取器改 `_shared` 族）

在 `_build_skill_prompt` read 循环接入提取器，契约层新增 dict-form read 的 `extractor:` 字段（**选项 A 维持推荐**，`extractor:` 是 `fields:` 的动态版）：

```yaml
- file: outline/volume_map.md
  extractor: volume_chapter
```

dispatcher 按 extractor 名调提取函数（volume_chapter → `_shared` 族的按章卷上下文形态）。**提取实现统一到 `_shared` 族**（与 context_assemble 同源、已有测试），不复活 `_extract_volume_chapter`（审计侧死代码，见 §2.1）。组合函数的家（下沉 `_shared.py` 新函数 vs 从 dispatcher 调 `context_assemble` 的现成形态）由 plan 阶段定——倾向下沉 `_shared`（leaf 模块章程），避免 dispatcher 反向 import context_assemble。触面（驳斥 B7 核实清单）：`contracts/loader.py` `_normalize_read_item`（:72-87，今日静默丢弃未知键——须让 `extractor:` 进旁路，如 `read_extractors`，与 `read_fields` 同模式）+ `_validate`（:204-239）+ dispatch read 循环 + `scripts/lint_contract_fields.py`（:53-86——**可能零代码改动**：`_check_read_item` 对 falsy fields 已早退，extractor-only 条目自然通过；plan 验证而非预算改动）+ Contract TypedDict（:52）。**G4 不在触面**（gates/g4 零 reads 校验）；`sync_contracts`/`lint_contract_prose` 消费归一化 string 不受影响（前提：loader 保持归一化）。

**失败语义（新增，防新死线）**：`extractor:` 的逃逸门与 `fields:` 对齐——**提取失败（文件存在但解析不出卷边界/chapter 超界/提取结果为空）→ 全文兜底 + 命名 WARN**（如 `extractor_failed_fulltext`），禁止静默空串替换（`_load_volume_context` 在 context_assemble 家里返回 `""` 是良性的——那里有其他 route 补位；dispatcher read 槽位没有，静默空串 = 丢全部卷上下文的新死线）。**文件缺失是另一分支非本 spec 面**：字面 read 文件缺失今日即被 `_resolve_read_with_fallback`（:476-489）解析为空列表静默跳过槽位——保持既有行为，不并入提取失败。**`fields` 与 `extractor` 同条目互斥**（loader 对两者并存抛 `ContractError`——语义冲突，无合理并存）。**extractor 名 fail-loud**：closed registry（首个成员 `volume_chapter`），未知名在 `load_contract` 即抛 `ContractError`（对齐 `contract.kind` 校验形态 loader.py:194-202）——否则拼错名静默降级全文，永无信号。

### 4.3 范围与兜底（修订）

- 实施范围：**chapter-planning**（主链 step 2，每章一次 ~26.3KB → ~500B-2KB）。genesis 5 读者是 string 读、不经 extractor（无兜底问题，保持全文）。`chapter=None` 分支保护的是**无章号的手动/CLI dispatch**（如用户对 planning 无章号调用）——不提取，全文发送（`resolve_chapter_path` 对无占位符路径原样放行，genesis.py:276 chapter=None 是既成语义）。
- volume_map 其余 string 读者本 spec 不动（字面活读者 = 10 − chapter-planning − deprecated foreshadowing-plant = 8 个：foreshadowing-lifecycle/pacing-design/plot-thread-weaver/review-arc-payoff/score-volume/sequel-writing/volume-outlining/book-spine-init）——单 spec 原子性，扩面待 chapter-planning 效果验证后另行处置。

### 4.4 验证（离线化修订）

- 直调 `_build_skill_prompt('shenbi-chapter-planning', fixtures 树, chapter=N)`：volume_map 内容从 ~26.3KB 降至当前卷节点（~500B-2KB）。
- **双兜底分支都有用例**：chapter=None（genesis 形态）→ 全文；**chapter 有值但提取不出**（无卷边界/超界/文件坏）→ 全文 + `extractor_failed_fulltext` WARN（§4.2 失败语义）——两个降级路径都必须行为断言，禁止只测 happy path。
- `_shared` 族既有测试仍 PASS；新增 dispatch 循环级用例（提取生效 + 两兜底分支）。
- G4 对 chapter-planning PASS（契约面无副作用；**不构成**内容充分性证据，见 §3.2 注）。
- **充分性验证（plan 阶段定稿形态）**：fixtures 树上对比改前/改后 chapter-planning 的输入面差异（保留的卷上下文是否含 planning 决策所需要素）；**相邻章节点（N±1）取舍**是待决项——`_load_volume_context` 现返回当前章节点+卷 Objective+跨卷桥，无相邻章节点；planning 是否需要 N±1 做节奏连续性由 plan 阶段裁决（需要则提取形态加相邻节点，不需要则记录理由）。

---

## 5. 假设与验证（每条一行，修订）

| # | 假设 | 验证 |
|---|------|------|
| §3.0 | read_fields 旁路是 fields 权威载体，dispatch 查表修复可行 | 直调 `_build_skill_prompt` 行为断言（§3.0 验收）+ 全量回归绿 |
| §3 | 安全字段键集（模板 8 个）跨生产路径稳定 | 生产者模板（power-system SKILL.md:120-185）+ git 历史 xinghuo 真实文件 + fixture 三方对比（§2.2 已落证；lint 样本接线后 CI 持续执法） |
| §3 | 声明的 field subset 覆盖 skill 实际需要 | 离线断言零 `field_filter_missing_fields` WARN + body 精读复核（plan 阶段）；G4 仅证契约面无副作用 |
| §4 | `_shared` 族提取的卷节点足够 chapter-planning 决策 | fixtures 树改前/改后输入面对比 + N±1 取舍裁决（§4.4；G4 不构成充分性证据） |
| §4 | chapter 未知时全文兜底不破坏 genesis | genesis 形态直调断言（chapter=None → 全文） |
| §4 | 提取失败不静默丢上下文 | 双兜底分支行为断言（chapter 有值提取不出 → 全文 + WARN，§4.4） |

---

## 6. 修复方案分级（修订）

### 6.1 P1（本 spec 实施）

| finding | 修复 | 风险 | 验证 |
|---------|------|------|------|
| §3.0 dispatch 死线 | read 循环改查 `read_fields` 旁路 | 中（机制层，触全部 dict-form reads 的行为——从 no-op 变生效；36 条既有 dict 声明将首次真实过滤，须全量回归 + 零 WARN 核查（scope 见下）） | 行为断言 + 全量回归 + 零 WARN（scoped） |
| §3 power_system fields | review-group-factual 声明 fields（模板 8 个内） | 低（field 不匹配有 WARN 逃逸门 + 全文兜底） | 零 WARN + G4 PASS + 离线字节下降 |
| §4 volume_map extractor | `extractor:` 契约字段接 `_shared` 族（chapter-planning） | 中（契约 schema 扩展：loader 旁路 + 互斥/fail-loud 校验 + lint 识别；提取器复用已测实现） | 三分支断言（happy + 两兜底） + G4 PASS + 离线字节下降 |

**§3.0 零 WARN 断言语料 scope**：shenbi-native 谱系（genesis 模板按声明并集播种 header，`_collect_declared_truth_fields` → `_init_truth_templates`）+ `tests/fixtures/` 树。**已知 at-risk 集（plan 阶段必须枚举核对全部 36 条声明）**：`truth/current_state.md` 家族——chapter-planning 与 review-continuity 声明 `[系统演化阶段, 参数当前位置, 进行中的情节线]`，与 chapter-025 生产快照（`主角状态/当前世界局势/活跃线索`，零交集）不符、与 truth-current_state.md 仅 1/3 命中、与 xinghuo 样本 3/3 命中——历史 lineage 树上死线修复后会触发逃逸门（全文兜底是正确行为，不算缺陷，铁律 2 谱系 scope 同理）；其余 34 条声明经 lint any-match 复核全样本命中。**契约改动再生成面**：改 2 个 SKILL.md frontmatter 后跑 `just generate` 验证 deps.json/docs 生成物 diff 空（归一化 string 不变，预期零 diff；三源纪律 checklist 项）。

### 6.2 显式不做

- **chapter-N.md 字段过滤：** 连续 prose 无 section；剩余读者是审计对象本身（§2.3）。
- **volume_map 的 `fields:` 声明：** 动态卷标题，必须用提取器（§4）。
- **volume_map 其余 8 个 string 读者扩面：** 单 spec 原子性（§4.3）。
- **`_extract_volume_chapter` 复活：** 死代码弱实现，统一 `_shared` 族（§2.1）。
- **AGENTS.md Layer B 叙事修订：** 随 §3.0 实施同步（机制从「声称工作」变「真工作」，文档面在 plan 中列出）。

---

## 7. 验证标准（数值化，离线口径修订）

| 标准 | 当前 | 目标 | 度量方式 |
|------|------|------|---------|
| dispatch 循环字段过滤 | 死线（§1.5） | 行为生效 | `_build_skill_prompt` 直调断言（fixtures 树） |
| power_system.md 发送体积（review-group-factual） | ~28.8KB 全文 | 15.5KB（4-field 子集实测 54%；子集终值 plan 定稿后联动重算） | 直调字节 + estimate_prompt_tokens |
| volume_map.md 发送体积（chapter-planning） | ~26.3KB 全文 | ~500B-2KB（当前卷节点） | 直调字节 |
| `field_filter_missing_fields` WARN | 未测（死线下恒零事件——假绿） | 0（修复后真实过滤下仍零；**scope = shenbi-native 谱系 + fixtures 树**，历史 lineage 的 current_state 家族除外——§6.1 at-risk 集，全文兜底为正确行为） | 直调 + structlog 捕获断言 |
| `extractor_failed_fulltext` WARN | 机制不存在 | 仅在提取失败用例中出现（happy path 零；文件缺失走既有静默跳过分支，§4.2） | 双兜底分支行为断言（§4.4） |
| G4（review-group-factual / chapter-planning） | PASS | PASS（契约面无副作用；非充分性证据） | `just gate G4` |
| 全量回归 | 4470 passed 基线（执行时以当期 `just check` 重基线） | 全绿（死线修复后 36 条既有 dict 声明首次生效） | `just check` |

（原表「TokenLedger prompt_tokens 下降」改离线直调口径——真实 dispatch 违反核心原则 8；原「`>5KB reads` 字段级覆盖率 ≥30%」删除——生产树已出库、口径无定义语料不可算，且声明覆盖率在死线下是虚荣指标。）

---

## 8. 铁律（修订）

1. **字段名必须落证安全集。** fields 声明限制在生产者模板 8 个 header 内（power-system SKILL.md:120-185 硬编码）；落证 = 模板 ∩ git 历史真实文件（`git show d120a444^:novel-output/xinghuo-ranqiong/world/power_system.md`）∩ 消费方 body 需求三方对比。不可从 skill body 概念名直接当 header 键（body 是依据不是字节键；「与世界观核心主题的关系」类无背书 header 不入集）。
2. **逃逸门 WARN 即缺陷（事件名更正；谱系 scope）。** `filter_to_fields` field 不匹配返回全文 + `field_filter_missing_fields` WARN——实施后离线断言零该事件（scope = shenbi-native 谱系 + fixtures 树，§6.1）。**死线修复前「零 WARN」是假绿**（过滤不发生当然无事件）——§3.0 必须先行并单独验收。**谱系豁免**：genesis 模板按声明并集播种 header，shenbi-native 项目声明天然匹配；**导入路径（world-extraction）与历史 lineage（如 chapter-025 快照形态的 current_state）不在 fields 声明适用面**——其 miss → 逃逸门全文兜底是正确行为，不算缺陷。
3. **volume_map 不用 fields 用 extractor，提取器统一 `_shared` 族。** 动态 header 文件不可假装能字段过滤；提取实现与 context_assemble 同源（已测），不复活审计侧死代码。
4. **新机制必须有逃逸门 + fail-loud（防新死线）。** `extractor:` 失败 → 全文兜底 + 命名 WARN（禁静默空串）；未知名/与 fields 并存 → load 时 `ContractError`。本 spec 存在的意义是杀静默降级——新机制自身不得重蹈。

---

## 9. 依赖关系（修订）

```
PR #39（TokenLedger 前提）已合并 · spec #28（Layer B 声明/lint 修正）已合并 · C28（审计波读抑制）已合并 · P2 #6 已 Done（cache 裁决不实施）
        │
        ▼
本 spec:
  ├─ §3.0 dispatch 死线修复 ── 前置于一切 fields/extractor 生效
  ├─ §3 power_system fields ── 依赖: §3.0 + 安全字段键集（§2.2 三方落证）
  └─ §4 volume_map extractor ── 依赖: §3.0 + _shared 族提取器（已存在已测）+ loader 旁路扩展
        │
        ▼
  plan + 实施 + G4 验证 ──► 归档本 spec
```

与已归档 #6 的边界（终局确认）：#6 管 cache（裁决不实施）/示例外置（已实施）；本 spec 管 fields/extractor 切片 + 死线修复。#6 归档裁决「#65 正交——Layer B 省 prompt 发送字节」在死线修复前不成立（Layer B 从未省过 dispatch 字节），修复后成立。

本 spec 是 **design，不实施**。实施前需另写 plan 并批准。
