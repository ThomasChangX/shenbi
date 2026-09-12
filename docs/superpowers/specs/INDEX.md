# Spec 执行索引

> **最后更新**：2026-09-13（#62 Done PR #214——C24 文档语义矛盾闭合，45 findings 回写；F935 队列重排已随 #62 归档消解，现序 #40→#63→#64→#6→#65→#66）
> **活跃 spec 数**：6（#62 Done PR #214）

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列

### #40 · 2026-08-15 审计修复总纲（37 簇 master）

- **文件**：`2026-08-16-audit-remediation-master.md`
- **系列**：2026-08-15 全项目深度审计 · 阶段 5（总纲；supersede #17 的 catalog 角色）
- **状态**：Design（记账 pass Done PR #147；§6.4 矩阵同步 pass Done PR #172；C14/C16/C37 回标 pass 2026-09-08——C14 #52 PR #183、C16 #54 PR #174、C37 #51 PR #179；C15-C18/C37 回标 + C19 速览补录与 ledger 回写 13 行 + F750/F0-06 归宿 #66 pass 2026-09-11；索引长期保留） | **优先级**：🔴 P0（总纲）
- **内容**：phase4 37 簇修复优先级矩阵（P0×7 簇=191 条 / P1×26 簇=483 / P2×4 簇=100，纯 M 簇 0 个）、跨簇依赖链（C32→C33→成本类、C3+C34→C1 验收、C10→C28/C33、C19#26→C37 解冻、C16→C14→C15）、量级汇总（L×7/M×22/S-M×8，3 泳道 6-9 周墙钟）、与既有 23 活跃 spec 的 supersede/解散/保留关系表、回写协议（737 条 merged）

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

### #66 · 遗留微修批：F750 集成测试真实 fixture 化 + F0-06 python 版本三元统一

- **文件**：`2026-09-11-leftover-microfix-f750-f006.md`
- **系列**：2026-08-15 审计轮遗留收口（非 37 簇成员——F750 原簇 C16 边界争议条 deferred 出局、候选归宿 C15/C17 双亡；08-14 轮 F0-06 无簇承接；归宿由 spec #40 master 维护 pass 2026-09-11 裁决）
- **状态**：Design | **优先级**：🟡 P2（两 finding 均 P2 · 微修 S 量级）
- **方法**：机械替换 + 配置统一（两 finding 根因与修复路径均已定案，无需 systematic-debugging）
- **依赖**：F750 素材源在盘（novel-output/xinghuo-ranqiong/ 真实产物全套 + fixtures 既有 upstream-copy/synthetic-sample 面，映射表见 spec）；F0-06 无依赖
- **内容**：(1) F750：test_gate_cli.py `_make_worldbuilding_project`（:27-97）手工捏造换 fixture 拷贝（首选 novel-output upstream-copy 引入、载体双形态，映射表见 spec），仅保留目录组装逻辑；(2) F0-06：pyproject python 版本三元统一为 3.11（mypy :379 改值，其余两处已符）
- **对应 plan**：❌ 未写

---

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
