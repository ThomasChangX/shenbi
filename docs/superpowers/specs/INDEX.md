# Spec 执行索引

> **最后更新**：2026-08-15
> **活跃 spec 数**：24

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列

### #6 · 全项目审查执行：pipeline 永不完成（P0 簇）

- **文件**：`2026-08-14-pipeline-never-completes-design.md`
- **系列**：2026-08-14 全项目审查（总纲 #5 的执行产出，子 spec 1/10）
- **状态**：Design（Revised 2026-08-15 · SDD 阶段 3 设计审查 6 轮收敛 · 末轮 0C/0I：R1 卷级作用域+负面验收 / R2 total=100+在途 heal / R3 参数化目录校验+manifest 钉契约 / R4 per-step N 语义表+四消费者+[path-context] 跨路由通道 / R5 显式解析上下文 / R6 三消费方+全桥接段聚合 / F303 拆至 #26 / F340 重试计数重置+全类型表 / F341 全守卫体镜像 / F304 捕获定位 / F380 哨兵路径）
- **优先级**：🟥 Critical（5 个独立根因使长篇小说 pipeline 永不进入 CLOSURE；生产 100 章规划实证）
- **方法**：`systematic-debugging` 四阶段
- **内容**：volume_map 中文格式 vs 英文解析器（F324）/ total_chapters 写点自锁（F353）/ closure 目录 G4（F371）/ N 占位 G4（F373）/ closure prompt-build（F379）+ R6 节点桥接中文提取 + F340/F341/F304 + 从属 F313/F380/F3B5/F245。**F303 已拆至 #26**。修订要点：R1 卷级作用域+负面验收（边界集=={15,35,55,75,100}）、R2 total=100 修正（max(boundaries) 规划总章数，非已写 56）、R3 目录校验+契约对齐（gates/g4）、R4 per-step N 语义表（arc=chapter//12/stratum=//36/volume=卷索引）、R5 显式路径解析上下文

### #7 · 全项目审查执行：数据丢失簇（P0）

- **文件**：`2026-08-14-data-loss-cluster-design.md`
- **状态**：Design | **优先级**：🟥 Critical
- **内容**：append_dedup no-op（F397，chapter_summaries 仅 2/56 章）/ atexit 清 staging（F364）/ materialize 覆盖（F640）/ 并行写竞态（F326）

### #12 · 全项目审查执行：成本计量（P0/P1）

- **文件**：`2026-08-14-cost-ledger-design.md`
- **状态**：Design | **优先级**：🟥 Critical（TokenLedger 少计，决策表 P0 例）
- **内容**：TokenLedger 接线不全（F302）/ 注入缓解 no-op（F300）

### #17 · 全项目审查执行：总纲 catalog（#6-#16 父条目）

- **文件**：`2026-08-14-full-project-audit-design.md`
- **状态**：Design | **优先级**：🔴 P0（总纲）
- **内容**：2026-08-14 全项目深度审查执行总纲（F1105 补登）：四层覆盖（D1-D4）执行结果、分区矩阵 Z1-Z11 与线程 T1-T15 产出、去重后 10 根因簇图与执行顺序（1+2 → 3 → 5 → 4/6/7/8 → 9/10+M）、G1-G7 完备性门说明；子 spec #6-#16 的父条目（F0-04 家族登记补全）

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
- **内容**：设计无时间盒、完备性门驱动（G1-G7）的全项目审查 prompt（交付物：`docs/superpowers/full-project-audit-prompt.md`，自包含基线 + superpowers skill 白名单可选增强（增强非替代）/ 无 SDD）：四层覆盖模型（D1 机械 100% / D2 模式 100% / D3 语义深读全文件 / D4 磁盘运行时产物与日志审计）+ 双台账（tracked 表 A + 磁盘产物表 B，无 sampled 兜底）+ 分区矩阵 Z1-Z11 + 跨模块审计线程 T1-T16（T10 历史修复回归核验、T11 运行时行为核验 + stub smoke、T12 安全、T13 依赖供应链、T14 确定性替换、T15 git 考古、T16 性能与资源效率）+ per-file 报告/findings ledger schema + 每 finding 独立 spec 产出契约（1 总纲 + N 子 spec + M 级合并批量 spec）+ checkpoint/resume 协议。只审不修。诚实代价：串行 100+ 小时 / 并行墙钟 20-40 小时、10-20 会话。v2/v3 修订见 spec §0/§0.1（v3 为 2026-08-14 执行 run 的实证修复：G4 双轨收敛、§3.5 攻击角度库、G5 机械对账、G6 分层深核禁稀释、T16 性能线程、final-report 机械统计）。
- **对应 plan**：❌ 未写

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

### #13 · 全项目审查执行：配置治理（P1/P2）

- **文件**：`2026-08-14-config-governance-design.md`
- **状态**：Design | **优先级**：🟠 High
- **内容**：4 个绕过向量（F611/F631/F643/F666）+ F606/F638/F635/F614

### #15 · 全项目审查执行：依赖供应链（P1）

- **文件**：`2026-08-14-deps-supply-chain-design.md`
- **状态**：Design | **优先级**：🟠 High
- **内容**：dev group 含 sentence-transformers 致降级路径测试 masking（D1-01）；Z11-01 decisions.json 无效产物

### #18 · 全项目审查执行：Fixture 真实性与测试质量（补齐 A）

- **文件**：`2026-08-14-fixture-authenticity-design.md`
- **状态**：Design | **优先级**：🟠 P1（补齐）
- **内容**：fixtures 56% 手写/伪造（G0.9 声称不符）、scenario↔fixture 断链、伪造基准进门禁、测试质量洞（R1-R4 + P2×31 + M×15）

### #19 · 全项目审查执行：Decisions 链（补齐 B）

- **文件**：`2026-08-14-decisions-chain-design.md`
- **状态**：Design | **优先级**：🟠 P1（补齐）
- **内容**：decisions.json 全链（T1-01 G4.dec 恒 SKIP = Z11-01 根因、T1-02 producer 零编码、T1-03 写路径无校验、F1303-F1305）

### #20 · 全项目审查执行：产物契约 Z11（补齐 C）

- **文件**：`2026-08-14-z11-output-contracts-design.md`
- **状态**：Design | **优先级**：🟠 P1（补齐）
- **内容**：章节头/META 契约（F1301/F1302）、truth registry 三源合一（F1307/F1322）、状态/账本产物契约（F1309/F1310/F1313）

### #21 · 全项目审查执行：Truth 写路径（补齐 D）

- **文件**：`2026-08-14-truth-write-path-design.md`
- **状态**：Design | **优先级**：🟠 P1（补齐）
- **内容**：T7-01 双写者键漂移、T7-02 hooks 记录丢失、T7-03 staging 分叉、T7-06 state-settling 契约自相矛盾

### #22 · 全项目审查执行：安全与提示注入（补齐 E）

- **文件**：`2026-08-14-security-injection-design.md`
- **状态**：Design | **优先级**：🟠 P1（补齐）
- **内容**：T12-01 wrapper 属性注入、T12-02 持久化注入链 + codex 写面约束 + 命令注入/env/路径穿越 P2

### #23 · 全项目审查执行：Z8 契约漂移补完（补齐 F）

- **文件**：`2026-08-14-z8-contract-drift-design.md`
- **状态**：Design | **优先级**：🟠 P1（补齐）
- **内容**：DEPRECATED 接线拆除（F904/F950/F1004）、reads/writes 声明补全（F953/F1002/F1011 等）、双重调度（F905/F906/F907）、内部矛盾（F903）、drift-guidance（F1001）

### #24 · 全项目审查执行：工具与门禁链补完（补齐 G）

- **文件**：`2026-08-14-tooling-gate-chain-design.md`
- **状态**：Design | **优先级**：🟠 P1（补齐）
- **内容**：lint 接线/发明值盲区（T201/T302/T9-01/F1212/F1214）、CLI 契约（F140）、并行波/重试（F301/F354/T501/T502）、助手接线（T14-01/03/04）、字段过滤接线（T301）

### #3 · 确定性技能替换审计：何时把 skill 从 LLM 提升到 Python

- **文件**：`2026-08-01-deterministic-skill-replacement-audit-design.md`
- **系列**：Token 效率全栈 audit（子 spec 2/3，隶属已归档总纲 [`archive/...`](archive/2026-08-01-pipeline-read-write-consistency-audit-design.md) §0 分工）
- **状态**：Design
- **优先级**：🟡 Medium（架构层优化，非阻塞；但单条候选 payoff 最高——消除 1 次不必要 dispatch = 省 100% 该调用 token）
- **方法**：`systematic-debugging` 四阶段
- **依赖**：已归档总纲 spec；`src/shenbi/skill_utils/`（9 个已存在的确定性助手）；`src/shenbi/pipeline/{context_assemble,truth_io,hook_planting,scr_extractor}.py`；归档 `2026-07-19-01`（覆盖 vs 追加 postmortem）
- **内容**：只审 **"这个 LLM 调用本身是否必要"**——能否用确定性 Python 替代（部分或全部）。核心洞察：确定性替换非假设——repo 已 9 次实现该模式（`skill_utils/` + `pipeline/` 助手），且 postmortem 证明确定性写路径是 CN3 覆盖 bug 根因修复。形式化**提升判据**（{纯文件操作 / 键值 upsert / 计数 / 固定模板填充 / 阈值比较}）+ 逐候选评估：snapshot-manage（100% 确定，立即可换）/ context-composing（pipeline 模式 85% 确定，helper 已存在）/ state-settling（写半路径已落地 truth_io.py，抽取留 LLM）/ memory-distill（结构字段聚合确定，800 字叙事留 LLM）。铁律：`requires_independent_agent` 的 skill（review/score）不换。
- **对应 plan**：❌ 未写

### #14 · 全项目审查执行：确定性助手统计（P2）

- **文件**：`2026-08-14-stats-determinism-design.md`
- **状态**：Design | **优先级**：🟡 Medium
- **内容**：标点双计/引号恒 0/熵分母/TTR/排比截断/双实现分叉等 21 子项

### #16 · 全项目审查执行：M 级批量（98 条）

- **文件**：`2026-08-14-minor-findings-batch-design.md`
- **状态**：Design | **优先级**：⚪ Low（批量）
- **内容**：全仓库 M 级文案/命名/格式/过期注释按区分节批量清理

### #25 · 全项目审查执行：P2 批量（补齐 H）

- **文件**：`2026-08-14-p2-batch-design.md`
- **状态**：Design | **优先级**：🟡 P2（批量）
- **内容**：287 条 P2 按区批量处置，家族统一修复模式（F431 崩溃族/采样截断/契约漂移/死代码/路径参数/错误处理）

### #26 · 全项目审查执行：快照子系统接线（自 #6 拆分）

- **文件**：`2026-08-15-snapshot-subsystem-wiring-design.md`
- **系列**：2026-08-14 全项目审查（自 #6 拆分：设计审查裁决三路设计决策无法一行方向化）
- **状态**：Design
- **优先级**：🟠 P1
- **方法**：`systematic-debugging` 四阶段
- **依赖**：无（与 #6 的 closure step 10 契约对齐有衔接面，见各自内容字段）
- **内容**：快照子系统三机制并存零接线（F303）：chapter_loop 差分三件套死代码 / crash_recovery 平行实现 / cli rollback deferred；三路裁决（接线 / 收敛后接线 / 移除）+ 按路径定稿验收
- **对应 plan**：❌ 未写

---

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
