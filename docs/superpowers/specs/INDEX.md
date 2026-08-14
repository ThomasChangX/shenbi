# Spec 执行索引

> **最后更新**：2026-08-14
> **活跃 spec 数**：14 | **已归档**：99（见 `archive/`）

仅列待执行 spec；已完成/合并的 spec 已移至 `archive/`，不在此重复。
按推荐执行顺序排列；执行序列号见各 spec 文件名日期前缀。

---

## 执行队列

### #3 · 确定性技能替换审计：何时把 skill 从 LLM 提升到 Python

- **文件**：`2026-08-01-deterministic-skill-replacement-audit-design.md`
- **系列**：Token 效率全栈 audit（子 spec 2/3，隶属已归档总纲 [`archive/...`](archive/2026-08-01-pipeline-read-write-consistency-audit-design.md) §0 分工）
- **状态**：Design
- **优先级**：🟡 Medium（架构层优化，非阻塞；但单条候选 payoff 最高——消除 1 次不必要 dispatch = 省 100% 该调用 token）
- **方法**：`systematic-debugging` 四阶段
- **依赖**：已归档总纲 spec；`src/shenbi/skill_utils/`（9 个已存在的确定性助手）；`src/shenbi/pipeline/{context_assemble,truth_io,hook_planting,scr_extractor}.py`；归档 `2026-07-19-01`（覆盖 vs 追加 postmortem）
- **内容**：只审 **"这个 LLM 调用本身是否必要"**——能否用确定性 Python 替代（部分或全部）。核心洞察：确定性替换非假设——repo 已 9 次实现该模式（`skill_utils/` + `pipeline/` 助手），且 postmortem 证明确定性写路径是 CN3 覆盖 bug 根因修复。形式化**提升判据**（{纯文件操作 / 键值 upsert / 计数 / 固定模板填充 / 阈值比较}）+ 逐候选评估：snapshot-manage（100% 确定，立即可换）/ context-composing（pipeline 模式 85% 确定，helper 已存在）/ state-settling（写半路径已落地 truth_io.py，抽取留 LLM）/ memory-distill（结构字段聚合确定，800 字叙事留 LLM）。铁律：`requires_independent_agent` 的 skill（review/score）不换。
- **对应 plan**：❌ 未写

### #4 · 输出侧浪费审计：重试放大 / 审计交叉冗余 / revision 原始 glob

- **文件**：`2026-08-01-output-side-waste-audit-design.md`
- **系列**：Token 效率全栈 audit（子 spec 3/3，隶属已归档总纲 [`archive/...`](archive/2026-08-01-pipeline-read-write-consistency-audit-design.md) §0 分工）
- **状态**：Design
- **优先级**：🟠 High（输出 token 单价 2-3× 输入；总纲的盲点）
- **方法**：`systematic-debugging` 四阶段
- **依赖**：已归档总纲 spec（§3.1 TokenLedger dead-wire 是本 spec 重试计量的前置——**PR #39 已修**）；推理控制 spec（已归档，§J finish_reason=length 盲点驱动本 spec F8 重试放大——**PR #40 已修**）；`src/shenbi/pipeline/{error_handler,revision_router,parallel_dispatch,chapter_loop}.py`
- **内容**：只审**输出侧浪费**——LLM 产出 token 的浪费。补总纲盲点（总纲 §3 的 10 条 findings 全是输入侧）。4 条 findings：F8 重试放大（坏章最坏 ~6 章等价输出 + 3 审计波；`error_handler.py:36-37` MAX_DISPATCH_RETRIES=2/MAX_AUDIT_RETRIES=3）/ F9 审计交叉冗余（同一缺陷 5 份报告各描述，`parallel_dispatch.py:189-249` consolidate 只提 BLOCKING 行不去冗）/ F10 revision 读 raw glob 无去重（`revision_router.py:199`，~60-120KB/次）/ dead sidecar 产出 token。根因簇：无输出聚合层 / 无重试预算计量。P0：revision 前加审计聚合去重层；P1：重试预算计量 + TokenLedger 接线（**PR #39 已接 API 路径**）；P2：审计器缺陷共享去冗。
- **对应 plan**：❌ 未写

### #5 · 全项目深度审查 Prompt 设计（full-project-audit-prompt）

- **文件**：`2026-08-13-full-project-audit-prompt-design.md`
- **系列**：2026-08-13 全项目审查（总纲；只设计审查 prompt 文档本身，审查执行另起会话）
- **状态**：Design
- **优先级**：🟠 High（工程卫生总审查的执行载体；产出驱动后续所有修复 spec）
- **方法**：`brainstorming`（已完成）→ 直接编写 prompt 文档（superpowers skill 可选增强 / 无 SDD）
- **依赖**：`docs/superpowers/single-model-sdd-prompt.md`（仅风格先例：Iron Law / 反合理化）；repo spec/INDEX 约定；AGENTS.md
- **内容**：设计无时间盒、完备性门驱动（G1-G7）的全项目审查 prompt（交付物：`docs/superpowers/full-project-audit-prompt.md`，自包含基线 + superpowers skill 白名单可选增强（增强非替代）/ 无 SDD）：四层覆盖模型（D1 机械 100% / D2 模式 100% / D3 语义深读全文件 / D4 磁盘运行时产物与日志审计）+ 双台账（tracked 表 A + 磁盘产物表 B，无 sampled 兜底）+ 分区矩阵 Z1-Z11 + 跨模块审计线程 T1-T11（含 T10 历史修复回归核验、T11 运行时行为核验）+ per-file 报告/findings ledger schema + 每 finding 独立 spec 产出契约（1 总纲 + N 子 spec + M 级合并批量 spec）+ checkpoint/resume 协议。只审不修。诚实代价：串行 100+ 小时 / 并行墙钟 20-40 小时、10-20 会话。
- **对应 plan**：❌ 未写

---

v1 基线（Foundation / Contracts / Pipeline / Quality Gates / Context Handoff / CI / 07-19 一致性与韧性集群）已全部交付，对应 PR #1–#19 均已合并。PR #21/#22（Dependabot）+ PR #25（消除既有 warning）也已合并。

新增 spec 时在此登记（`### #NN · <title>` + 文件/系列/状态/优先级/依赖/内容/对应 plan 字段），完成后移动至 `archive/` 并从本页删除。

## 依赖关系图

```
─── v1 基线（已全部合并，PR #1–#19）───
P-1 卫生 (#3) ─┬─► P-1.E 地基补完 (#4)
               └─► Contract 单一信源 (#6/#8) ─► 一致性基础设施 (#17)
Documentation 重设计 (#10)
Novel Pipeline (#11/#13/#14) ─► 性能重设计 ─► Clean-Context Handoff (#16/#17)
Quality Gates (#7)     CI 优化 (#18)
P0 阻塞修复 (#19) ◄── 07-19 一致性与韧性集群（19 spec，全部落地）
```

> 完整合并历史见 `git log --oneline` 及各 PR。下方仅列分类导航。

## 快速参考

| 想做什么 | 先看哪个 |
|----------|----------|
| 了解 v1 整体架构 | ✅ 已合并 — `docs/architecture/overview.md` |
| 了解 Gate 体系（G0–G7） | ✅ 已合并 — `docs/framework/gates.md` |
| 查某 P-1.E 子项交付 | `archive/2026-06-15-p-1.e-foundation-completion/README.md` |
| 查 07-19 某 spec 实现细节 | `archive/2026-07-19-NN-*-design.md` |
| 查契约 / 契约一致性 | `archive/2026-07-08-contract-consistency-infrastructure-design.md`（PR #17） |
| 查 Pipeline 可靠性 / 崩溃恢复 | `archive/2026-07-19-17-pipeline-infrastructure-and-resilience-design.md` |
| 新增 spec 的写法 | 参照 `archive/` 内近期 spec 的 `> **Date/Series/Depends on/Status**` 块 |

## 归档说明

97 个已完成 spec 在 `archive/` 中，按日期排序（2026-06 ~ 08）。按系列：

- **P-1 基础卫生与地基**（`2026-06-14` ~ `2026-06-16`，含 `2026-06-15-p-1.e-foundation-completion/` 主 spec 簇）— pyproject/uv/ruff/mypy、structlog、ADR、src 布局、测试地基、CI 供应链、企业文件、文档配置；交付于 PR #3/#4
- **契约单一信源**（`2026-06-21`、`2026-06-29`、`2026-06-30`）— frontmatter 契约 + 生成物 + lint、契约执行与生产接线；交付于 PR #6/#8
- **质量门与评分**（`2026-06-22`、`2026-06-28`）— 正向质量门、分层记忆评分系统（Wave 1–4）；交付于 PR #7 及 Wave 提交
- **文档重设计**（`2026-07-01`）— 双语文档、69 技能目录；交付于 PR #10
- **Novel Pipeline**（`2026-07-01`、`2026-07-02`、`2026-07-06`）— 运行器、5 波实现、根因修复、Phase1 缺陷修复；交付于 PR #11/#13/#14
- **性能与上下文交接**（`2026-07-07` ×2）— 性能重设计、Clean-Context Handoff（decisions-sidecar + 字段级 reads）；交付于 PR #16/#17
- **一致性基础设施**（`2026-07-08`）— RoundPaths / match_field / DecisionsDoc / Producer Registry；交付于 PR #17
- **CI 优化**（`2026-07-09`）— 矩阵收缩、codegen 合并、nightly 仅 dispatch；交付于 PR #18
- **07-19 一致性与韧性集群**（`2026-07-19-01` ~ `-19`，19 个 spec）— truth-file 累积、输出校验、成本核算、配置治理、语义索引、上下文工程、并发安全、内容规划、存储优化、状态计数、生命周期、技能契约、内容质量门、结构完整性、基础设施韧性、架构优化、端到端验证；全部落地于 PR #19
- **08-01 ~ 08-02 巩固期**（`2026-08-01` ×2、`2026-08-02` ×3）— 既有 warning 清零（PR #25）、PR #23 调试 postmortem、cyclic-import 簇消除（PR #26）、PR #20 torch-bump 处置（待 #3 follow-up）；plus 单平台 codex 收敛（PR #23）
- **被取代的早期文档**（`2026-06-11` 测试门、`2026-06-13` 测试完整性、`2026-06-14` P-1 卫生 v1、`2026-06-29` pipeline-runner 设计笔记）— 主题被后续 spec 重做，或随 round-test 移除（PR #12）而吸收
- **遗留（superpowers 前）**（`2026-06-08` ×2）— shenbi 设计 v1、test-plan 设计

> 技术细节查各 archive spec 正文，不在此复述。

### #6 · 全项目审查执行：pipeline 永不完成（P0 簇）

- **文件**：`2026-08-14-pipeline-never-completes-design.md`
- **系列**：2026-08-14 全项目审查（总纲 #5 的执行产出，子 spec 1/10）
- **状态**：Design
- **优先级**：🟥 Critical（5 个独立根因使长篇小说 pipeline 永不进入 CLOSURE；生产 56 章实证）
- **方法**：`systematic-debugging` 四阶段
- **内容**：volume_map 中文格式 vs 英文解析器（F324）/ total_chapters 写点自锁（F353）/ closure 目录 G4（F371）/ N 占位 G4（F373）/ closure prompt-build（F379）+ 相关 F340/F341/F303/F304

### #7 · 全项目审查执行：数据丢失簇（P0）

- **文件**：`2026-08-14-data-loss-cluster-design.md`
- **状态**：Design | **优先级**：🟥 Critical
- **内容**：append_dedup no-op（F397，chapter_summaries 仅 2/56 章）/ atexit 清 staging（F364）/ materialize 覆盖（F640）/ 并行写竞态（F326）

### #8 · 全项目审查执行：门禁有效性（P1）

- **文件**：`2026-08-14-gate-effectiveness-design.md`
- **状态**：Design | **优先级**：🟠 High
- **内容**：G3.4 伪造 scorer（F408）/ 并行波无 G3（F345）/ 门序回归（F227）/ GR.2 masking（F401）/ P2.5 空串（F404）/ disabled 维度（F216）/ G7.1b（F432）/ G4 目录参（F163）/ F402/F158

### #9 · 全项目审查执行：契约单一信源（P1）

- **文件**：`2026-08-14-contract-single-source-design.md`
- **状态**：Design | **优先级**：🟠 High
- **内容**：deps.json 缺 5 skill（F0-02）/ 契约模型 dead-wire（F201）/ 字段过滤（F218）/ rubric 过滤 no-op（F115）

### #10 · 全项目审查执行：审计链失效（P1）

- **文件**：`2026-08-14-audit-chain-design.md`
- **状态**：Design | **优先级**：🟠 High
- **内容**：快照根错位（F513）/ N 占位不一致（F247）/ declared 无 chapter（F524）/ 路径绕过（F512）/ deleted 零拦截（F507）

### #11 · 全项目审查执行：drift 链失效（P1）

- **文件**：`2026-08-14-drift-chain-design.md`
- **状态**：Design | **优先级**：🟠 High
- **内容**：baseline 零调用（F602）/ off-by-one（F601）/ 门控（F612）/ 吞异常（F620）/ 判据 12 格式（F637）

### #12 · 全项目审查执行：成本计量（P0/P1）

- **文件**：`2026-08-14-cost-ledger-design.md`
- **状态**：Design | **优先级**：🟥 Critical（TokenLedger 少计，决策表 P0 例）
- **内容**：TokenLedger 接线不全（F302）/ 注入缓解 no-op（F300）

### #13 · 全项目审查执行：配置治理（P1/P2）

- **文件**：`2026-08-14-config-governance-design.md`
- **状态**：Design | **优先级**：🟠 High
- **内容**：4 个绕过向量（F611/F631/F643/F666）+ F606/F638/F635/F614

### #14 · 全项目审查执行：确定性助手统计（P2）

- **文件**：`2026-08-14-stats-determinism-design.md`
- **状态**：Design | **优先级**：🟡 Medium
- **内容**：标点双计/引号恒 0/熵分母/TTR/排比截断/双实现分叉等 21 子项

### #15 · 全项目审查执行：依赖供应链（P1）

- **文件**：`2026-08-14-deps-supply-chain-design.md`
- **状态**：Design | **优先级**：🟠 High
- **内容**：dev group 含 sentence-transformers 致降级路径测试 masking（D1-01）；Z11-01 decisions.json 无效产物

### #16 · 全项目审查执行：M 级批量（98 条）

- **文件**：`2026-08-14-minor-findings-batch-design.md`
- **状态**：Design | **优先级**：⚪ Low（批量）
- **内容**：全仓库 M 级文案/命名/格式/过期注释按区分节批量清理
