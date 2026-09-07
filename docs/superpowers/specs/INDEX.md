# Spec 执行索引

> **最后更新**：2026-09-08（#40 总纲维护 pass：C14/C16/C37 回标 + ledger 回写 55 closed/2 注记；此前 #52 C14 Done PR #183）
> **活跃 spec 数**：14（#52 C14 Done PR #183——25 条弱断言改写、红灯验证 17 处、tests-only；#46 C32 Rejected：11 条成员已由 PR #43 修复；F513 残留待新归属）

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列

### #40 · 2026-08-15 审计修复总纲（37 簇 master）

- **文件**：`2026-08-16-audit-remediation-master.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（总纲；supersede #17 的 catalog 角色）
- **状态**：Design（记账 pass Done PR #147；§6.4 矩阵同步 pass Done PR #172；C14/C16/C37 回标 pass 2026-09-08——C14 #52 PR #183、C16 #54 PR #174、C37 #51 PR #179；索引长期保留） | **优先级**：🔴 P0（总纲）
- **内容**：phase4 37 簇修复优先级矩阵（P0×7 簇=191 条 / P1×26 簇=483 / P2×4 簇=100，纯 M 簇 0 个）、跨簇依赖链（C32→C33→成本类、C3+C34→C1 验收、C10→C28/C33、C19#26→C37 解冻、C16→C14→C15）、量级汇总（L×7/M×22/S-M×8，3 泳道 6-9 周墙钟）、与既有 23 活跃 spec 的 supersede/解散/保留关系表、回写协议（737 条 merged）

### #53 · 审计修复 C15：关键模块/分支零覆盖（P2）

- **文件**：`2026-08-16-audit-zero-coverage-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C15，12 条）
- **状态**：Design | **优先级**：🟡 P2
- **内容**：仓内变更器 sync_contracts 56%（F112）+ dispatcher/cli 0%（F216）+ G2.dec 恢复路径（F418）+ g4 检查器 12%/零引用（F417/F765）+ parallel_dispatch 重试退避（F738）+ audit_context_cache（F737）等 12 面补行为级测试 + per-module 覆盖率底线表（跌破即 CI FAIL，留 5-10pp 余量防 flaky）

### #55 · 审计修复 C17：测试基础设施配置失效（P1）

- **文件**：`2026-08-16-audit-test-infra-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C17，18 条）
- **状态**：Design | **优先级**：🟠 P1（F1159 回归重放双重死亡）
- **内容**：hypothesis 样本入库 + CI replay（F1159/T1107/T1108 族）+ doc-links 拆 per-PR CI（F001/F732，承载 C23）+ mutmut 空转修复或诚实下线（T1104 实测 editable .pth 根因）+ golden/benchmark 建集或删承诺（F741/F742）+ G0.5 假 PASS 清理（T1109）——每条防线"激活或下线"二选一，消灭配置存在但永不运行态

### #56 · 审计修复 C18：生产产物污染清洗（P1）

- **文件**：`2026-08-16-audit-artifact-contamination-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C18，17 条；候选元根因 G）
- **状态**：Design | **优先级**：🟠 P1 | **依赖**：与 C11 写安全协同；R5 覆写面在 #7 不重复
- **内容**：F1171 权威复扫 109 文件元叙述污染（audits 55+snapshots 37+staging 9+decisions 7+正文 1，verified）+ 2 章手算 resonance（F1162/F1172 铁律 3 实证）——派发层沙箱写权根治（临时区+原子搬入）+ 产物 lint（元叙述/手算自证/时间戳倒挂）+ 分层清洗与机器重算；清洗前后 lint 计数对照可复验

### #57 · 审计修复 C19：快照子系统半迁移收口（P1）

- **文件**：`2026-08-16-audit-snapshot-unify-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C19，12 条）
- **状态**：Design（大部分失效待复核）| **优先级**：🟠 P1 | **依赖**：#26 三路裁决先决 · **2026-08-30 注记**：#26 已裁决路径 3（移除差分子系统）——本 spec 按其 T0 大部分自动失效，存活面仅 T4 truth-files.yaml/词面协调，待其自身价值门复核
- **内容**：F351 step-15 空操作 + F1109 生产实证失能（拼接审计非正文、漏 ch1-4/ch56）——布局/命名单源化（F792/F350/F306 三套并存）、TRUTH_FILES 从 truth-files.yaml 派生（F348 缺 book_strata/arcs）、state_heal 识别定稿布局（F317）、词表 D20 协调（F1155）+ 恢复演练与 F1109 复验脚本

### #58 · 审计修复 C20：技能契约声明面断裂（P1）

- **文件**：`2026-08-16-audit-skill-contract-declaration-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C20，21 条）
- **状态**：Design | **优先级**：🟠 P1
- **内容**：契约闭合 lint（R1 正文引用⊆声明 / R2 声明 writes⇒正文有步骤）+ P1 十技能修复（F836 memory-distill L5 盲写风险 / F811 context-composing 写未声明+时序错位 / F838 market-radar 必然 JSON 校验失败 / F870 越权写 / F871 dedup key 错配 等）+ D104 meta skill 契约二义性裁决——#23 声明面并入（待归档）；token 预算与 C2 Layer B/C29 截断协同

### #59 · 审计修复 C21：技能注册/触发路由漂移（P1）

- **文件**：`2026-08-16-audit-skill-routing-deprecated-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C21，12 条）
- **状态**：Design | **优先级**：🟠 P1 | **依赖**：GENESIS_STEPS 换 lifecycle 排在 C3/C20 契约定稿后
- **内容**：F873（verified）触发表路由 14 个 DEPRECATED 且后继零触发行 + F887 GENESIS_STEPS 仍派发 plant + F816/F817/F819 deps.json 仍注册——三路由面拆除 + 后继触发行补齐 + description 契约整改（F835/F842/F877 when-to-use）+ 防回潮 lint（DEPRECATED⇒零路由）+ F905 双重调度语义面（自 #23 补登）；#23 拆除面并入（已归档 Rejected）

### #60 · 审计修复 C22：平行登记表对账门禁（P1）

- **文件**：`2026-08-16-audit-registry-reconcile-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C22，29 条）
- **状态**：Design | **优先级**：🟠 P1 | **依赖**：T209 canonicalizer 裁决先于 R2 词表闭包
- **内容**：单一对账 lint 五规则（R1 技能闭包八面 / R2 词表闭包 / R3 哈希新鲜度 / R4 迁移表 / R5 glob 有效性）+ 存量修正（#9 R1 已实现 skill↔deps.json 闭包 lint，R1 并入时以 #9 实现为基线扩展；F432 G5_CHECKER_GLOBS 假 FAIL 生产面 / F1004 master.json 缺 15 技能 / F414 SHORT_MAP 缺 11 / F756 66 过期哈希 / F231 三方 74-69-69）——phase4 §7 第 9 位（改动小拦截面大）；#9/#23 登记面并入（待归档）；T203 dependency-dag.json 生成零消费（自 #24 补登）

### #61 · 审计修复 C23：文档机械漂移（P1）

- **文件**：`2026-08-16-audit-docs-mechanical-drift-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C23，46 条）
- **状态**：Design | **优先级**：🟠 P1 | **依赖**：C17 T2 doc-links CI 承载
- **内容**：断链清零（F901 执行协议引用已删脚本 / F461/F1034 / F952 / F968 归档 32 路径）+ 计数去数字化（69/59/15 族四文档 vs 磁盘 74，F904/F1033 合并域；#9 R5 已做 69→74 同步，去数字化时直接替换）+ 行号锚点改符号引用（T1001 第三次漂移教训）+ docstring 过期批量清——与 C24 共用"文档对账工具+CI"（phase4 §7 合并建议的机械半）

### #62 · 审计修复 C24：文档语义矛盾（P2）

- **文件**：`2026-08-16-audit-docs-semantic-conflicts-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C24，56 条最大文档簇）
- **状态**：Design | **优先级**：🟡 P2 | **依赖**：阈值/词表类等 C9/C22/C16 定源后改引用
- **内容**：裁决次序表（代码实值 > 最新设计 > 多数版本）+ DOT↔正文矛盾修复（F837/F852/F855，DOT 为权威）+ 缺失件补齐（F893 五技能缺 DOT 含 group-* 主力 / F801/F813 anti-rationalization 表）+ INDEX/spec 体系自洽（F935 排序 / F936 编号 / F938 重复 / F946-F950 勘误注）+ 术语/刻度统一（F885 X/10 vs /100）+ F903 skill 内部矛盾族（自 #23 补登）

### #63 · 审计修复 C25：CI/just 双向同步漂移（P1）

- **文件**：`2026-08-16-audit-ci-just-sync-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C25，24 条）
- **状态**：Design | **优先级**：🟠 P1 | **依赖**：是 C17/C20/C21/C22 新 lint 的承载前提（先于此执行）
- **内容**：清单一源化（CI 调 just check，F004/F005/F1001/F1002 双向洞 + AGENTS.md 等价命令失真）+ coverage 工件隔离（D101 collect-only 污染 16.08% / F1040 just test 假失败，AGENTS.md PR 协议 4 制度化）+ hook/工具激活面（F1038/F1011/F1012/F1015/F1036）+ workflow 修复（F1006/F1007/F1021）+ F1207 codeql.yml 无 pull_request vs SECURITY.md "every PR" 声明漂移（自 #24 补登）+ T1504 novel-output 22.7MB 反忽略出库（与 C18 协同）

### #64 · 审计修复 C26：shell/just 包装层注入（P1）

- **文件**：`2026-08-16-audit-shell-injection-fix.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（簇 C26，11 条）
- **状态**：Design | **优先级**：🟠 P1
- **内容**：F1031（verified）just 全 recipe 参数无引用插值——自然语言 prompt 含 ;/$() 即任意命令（AGENTS.md 标准入口即攻击面）→ argv/env 安全传递模式 + 六类注入样本矩阵回归；F002 run_pipeline.sh 自动 approve ESCALATION + 直改 step_index → 白名单 opt-in 或降级 smoke 工具；F1013/T1205 python3 -c 拼接实证可执行任意 Python → argv 传参 + JSON 工具解析；README 示例实测（F902/F1030）
### #6 · Token 效率 P2 效率优化：跨 dispatch 缓存 / IDE-CLI system-user 分离 / 重示例 SKILL.md 外置

- **文件**：`2026-08-02-token-efficiency-p2-cache-ide-split-example-externalization-design.md`
- **系列**：Token 效率全栈 audit（P2 效率优化轮，承接已归档总纲 §6.3 P2 五项中的 3.3/3.9/3.10；3.2 归 #4（输出侧浪费），2.3 #8/#9 视 §3 而定）
- **状态**：Design
- **优先级**：🟡 Medium（效率优化，非阻塞；度量前提 TokenLedger 已由 PR #39 落地；每项需 G4 全量验证 + 准备回滚）
- **方法**：`systematic-debugging` 四阶段
- **依赖**：已归档总纲（Cluster C 重复传输根因簇、§3.3/§3.9/§3.10 findings）；**PR #39**（TokenLedger API 路径接线 = 全部收益的度量前提；`_input_key` = 缓存 key 基础；`_strip_autogen_blocks` = system 字节稳定前置）；`src/shenbi/pipeline/{dispatch_helper,audit_context_cache,chapter_loop}.py`；`skills/shenbi-{chapter-pattern,review-resonance,review-arc-payoff,state-settling}/SKILL.md`
- **内容**：把总纲 P2 三项从提议推进到可实施——(1) §1 跨 dispatch 文件缓存层（保守首版：read-only truth 文件 only，规避 content-hash 失效语义；`pending_hooks`/`current_state` 等高 churn 文件不入缓存）；(2) §2 IDE-CLI system/user 分离（默认形态=system 字节稳定回归测试；强形态=CLI 支持 `--system` flag 才做，否则 stretch 放弃）；(3) §3 重 SKILL.md 示例外置到 `skills/_shared/`（同时解决 2.3 #9），首次 dispatch 带、后续引用，逐 skill 可回滚。实施顺序 T_A→T_B→T_C→T_D（风险升序）。与审计 #42（C28 性能）分工：彼覆盖审计波共享注入/registry/SentenceTransformer 缓存化，本 spec 为跨 dispatch 只读 truth 文件缓存。
- **对应 plan**：❌ 未写

### #65 · 字段级 reads 覆盖率：三大 truth 文件的精准切片

- **文件**：`2026-08-02-field-level-reads-coverage-design.md`
- **系列**：Token 效率全栈 audit（契约层补漏，承接已归档总纲 §3.7 + §6.2 P1 第二项；PR #39 plan T8 延后项——原延后理由"字段名需真实 round 输出验证"已由 `novel-output/` 真实 round header 解决）
- **状态**：Design
- **优先级**：🟡 Medium（P1 契约一致 + 效率；浪费量大但字段名匹配有准确性风险）
- **方法**：`systematic-debugging` 四阶段
- **依赖**：已归档总纲 §3.7/§6.2；`contracts/fields.py` `filter_to_fields`；`audit_context_cache.py` `_extract_volume_chapter`；`skills/shenbi-{chapter-planning,context-composing,review-world-rules}/SKILL.md`；真实 round header（`novel-output/*/world/power_system.md` + `outline/volume_map.md`）
- **内容**：解决 PR #39 T8 延后项。三大文件分类处置——(1) `power_system.md`（固定 header）：review-world-rules + context-composing 声明 fields（能力边界/代价机制/力量天花板 等），~28.8KB→~8-12KB；(2) `volume_map.md`（动态卷标题，不可 fields）：把已有 `_extract_volume_chapter` 提取器接入通用 read 路径（选项 A：新 `extractor:` 契约字段），~26.3KB→~500B-2KB；(3) `chapter-N.md`（连续 prose 无 section）：**显式不本 spec 管**，归 P2 spec #6 cache + 确定性替换 #4 snapshot。逃逸门 WARN 即缺陷（field 声明必须字节匹配真实 header）。审计修复 #28（字段过滤死线/escape-hatch 修复）为接线前置。
- **对应 plan**：❌ 未写

---

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
