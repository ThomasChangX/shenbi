# Spec 执行索引

> **最后更新**：2026-11-02（架构深审批次 A **r2 对抗复审完成**：#85-#94 十件全部按「最优性/非过度施工」重审重写——8 处设计修正，见各 spec 头 r2 注记；spec #84 设计审查七轮收敛至 r10）
> **活跃 spec 数**：12

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列

### #84 · 卷一清偿与卷二开卷（vol1-repair-vol2-launch）

- **文件**：`2026-10-30-spec84-vol1-repair-vol2-launch.md` ｜ **系列**：卷一复盘→卷二防复发 ｜ **状态**：Active（**执行中**——2026-11-02：Task 0-9+11 完成[注入器适配/驱动 prompt/T0 修复轮 13 项/ch37 重规划/G3.4 r4=88.10·P1=0·P2=7]，Task 10 束1-3 完成[ch37-42 在盘，裁决 #02-#09 见 vol1-ledger「卷二开卷运行」节]，**冻结于 ch43-0**——束4 待 #95 坡道修复后重跑[兼 #95 验收场]） ｜ **优先级**：🟠 P1
- **依赖**：#82 T3 + #83 T3（大纲面回填/回灌先行，T1 开卷协议前）；**T0 验收与 #83 T7 解耦**（判据 5 挂账口径，转绿归卷二侧）；T0 执行前提=用户确认启动修复轮。推荐顺序：大纲面→框架面最小核（#82 T0/T1/T2＋#83 T1/T5）→**章头注入器适配（r4/r5 框架面任务，T0-4 前置）**→T0 修复轮→其余框架面→开卷协议
- **内容**：章头注入器适配（chapter_header_style 参数化，z11 F1301 缺省不变）＋卷一内容修复 13 项工作单（P1×4＋盲审新连续性×4＋誓言拍去稀释＋卷二钩实体化＋罚单钟处置＋体例清扫/档案卡拆出另立项登记＋G3.4 无主 P2 外科小批 r5；ch28 修后 cd.counter 取证）＋卷二开卷协议（ch37 三件套/断供钩清偿排期含笔迹链挂起（挂起带清偿锚）/金手指首片/shadow 门转正检查点（两束协议））
- **对应 plan**：已建已执行 `plans/2026-11-01-spec84-vol1-repair-vol2-launch.md`（12 task；执行台账 `.superpowers/sdd/progress.md`＋`novel-xinghuo-vol1/vol1-ledger.md`）
- **触及的不变量维度**：持有与经手 props、枚举计数 counters、承诺与债务（钩）、情绪节奏、叙事纪律（POV/声口）

---

### #85 · 真相文件格式单源（truth-format-single-source）

- **文件**：`2026-11-01-spec85-truth-format-single-source.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟥 P0
- **依赖**：无（本批次首件）。与 #84 无文件冲突面（本批全为框架侧）；**执行时序由用户裁**——建议 #84 卷二开卷冻结窗后
- **内容**：叶模块 truth_format.py（hook-id/thread-id/表格行/分隔行/frontmatter/节边界六族解析单源，gates↔pipeline 双向 import 下的唯一无环落点）+ 5 处误解析红测修复（M1/M2 truth_index MH/CP 改键、M3 truth_readers CP→P、**M4 truth_io cell 正则漏 P 族**（r2 修正：缺口在 :414 非 heading）、M5 lint_truth_pool 旧线程集）+ 8 处 g4 严格 MH\d+ 收敛 + volume_map 收敛落 **_shared**（r2 亲验依赖方向 volume_budget→_shared）+ fixtures 误报清单过审
- **对应 plan**：待执行时建（`plans/2026-11-01-spec85-*.md`）
- **触及的不变量维度**：承诺与债务（钩）（hook-id 检测语法决定对账/归档/检索三面可见集）

---

### #86 · 死面清扫批（dead-surface-purge）

- **文件**：`2026-11-01-spec86-dead-surface-purge.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
- **依赖**：**#87 的前置**（拆分前减重）；全部条目 grep 亲验零引用
- **内容**：scr_extractor 缩编（16 字段 15 死 → 单函数 ~20 行，含两调用点与测试改写）/ review_checklist 死半边+__all__ 私有名 / chapter_loop 死分支 ×4 / **trace materialize+replay 删除**（r2 改判：零消费者+与 compaction 重复的两套签名校验；替代条款=若事件溯源为既定方向则保留原状另立项）/ capability_fs 迁 tests 支撑 / executor_config 6 DEPRECATED 死块 + registry 死 kind "short"。src 净减 ≥650 行
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（纯删除零引用面）

---

### #87 · god 文件拆分与正名（god-file-decomposition）

- **文件**：`2026-11-01-spec87-god-file-decomposition.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟥 P0
- **依赖**：#86 先行；建议 #84 卷二开卷冻结窗后执行（两热文件全量改动面）
- **内容**：BuiltPrompt dataclass 替 5 元组 + extractor 注册表（九臂 elif 坍缩，18 WARN→1）+ _run_chapter_step_impl 五体制拆分（917 行函数出鞘，技能后钩收一个显式具名函数——**不做全局注册表**）+ 子串判定消灭（ChapterStep 属性）+ ~12-15 事实公共符号正名 + tests 私有 import **增量** lint。（DispatchContext 原 T6 **移出至 #94 T4**——拆分中不同时改签名面）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（行为保持重构，characterization 先行）

---

### #88 · 门禁 finding 格式契约（gate-finding-contract）

- **文件**：`2026-11-01-spec88-gate-finding-contract.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
- **依赖**：无硬依赖（与 #87 不同文件域；#87 落地后 chapter_loop 侧改动面更小）
- **内容**：`G4.` 前缀补齐（r2 亲验：4 类发射点缺前缀致 shadow.check_id 恒 None——spec #83 T9 未修完整面）+ finding() 发射器 + 全 checker 输出契约 lint + _extract_check_id 归一 shadow.check_id + **G4_CHECK_MAP 28 键瘦身至 5 个非 HARD 覆盖键**（r2：23 个 HARD 键与未匹配默认 HARD 等价，全冗余）+ 分类改点边界精确 id 匹配（消灭 prose 子串误判）+ id 清单与行为不回归双断言 + G2.6/G4.cd 字数双 finding 互引去重
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（门禁元层，不改判定语义）

---

### #89 · 门禁内部性修复（gates-internal-repair）

- **文件**：`2026-11-01-spec89-gates-internal-repair.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
- **依赖**：无（r2 修正：CHAPTER_NUM_RE 已存在于 gates/shared.py:182，无需 #85 前置）
- **内容**：g4_chapter_drafting CheckContext 一次装载（772 行主函数 <300；plan 每章读 1 次非 5 次）+ 章号正则 17 处内联改用既有常量 + 四窄助手（chapter_no/load_facts_oracle/degrade/**RoundPaths.require_roots 落 paths.py:55**；**明确不做 table-DSL**）+ shared.py 出鞘（write_gate_marker 迁 gate_manifest、segment_sentences/strip_narrative_body 迁 text/ 解 skill_utils 倒依赖、import 时 FS 扫描惰性化）+ 4 门禁助手正名公共 + g4_cross_chapter 非注册表门文档化 + G0.12 假检查真实现
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（门禁内部结构，characterization 先行）

---

### #90 · 契约数据面单源（contract-data-single-source）

- **文件**：`2026-11-01-spec90-contract-data-single-source.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（**r2 重写**——原 codegen 方案经复审否决） ｜ **优先级**：🟡 P2
- **依赖**：无（spec #9 裁决约束已核——不新增契约模型消费）
- **内容**：**一个权威集合 + 三处派生（零构建基础设施）**：G4_CHECKER_KEYS 为单源 → G4_CHECKER_SKILLS 别名 / SHORT_MAP 机械派生（亲验 30 条 100% 为 shenbi- 前缀剥离）/ build_checkers 断言对齐（加 checker 从 5-6 处编辑降到 2 处）+ lint 恒真面收缩（散文面保留）+ lint_decisions_sources 弃 crude scan 走 load_contract + STEM_TO_SKILL 派生 + decisions 枚举 value-set 对账（status-vocab 模板；**Per-Skill 表生成器 r2 裁剪**）+ writing-skills 机器契约节 + lint_contract_prose 掩码收窄
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（契约/名册数据面）

---

### #91 · 状态与并发纪律（state-and-concurrency-discipline）

- **文件**：`2026-11-01-spec91-state-concurrency-discipline.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
- **依赖**：与 #87 的 chapter_loop 调用点撞面时 #87 先行、本 spec 适配新结构
- **内容**：gate_passed 单源（5 定义 SKIP 语义分歧收敛，容忍度逐点显式 + characterization 钉死）+ 失败协议纯函数共享（**genesis 侧保守化：差异表等价才换装，行为变更挂用户裁定**；不建 Router 类）+ ledger_archive 锁窗口闭合（**确定性交错红测**：barrier 注入非 sleep）+ dispatch_helper outline 合并同修 + **retry 助手接线**（r2 改判：increment_retry/reset_retry 有锁有测试零生产调用方——接线上串行裸写，非删除）+ retry_feedback 10 处裸写回归封装 + dispatch_with_retry 正名/run_post_draft_pair 改名/信号量戏法删除
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（运行时状态纪律；SKIP 语义 characterization 先行）

---

### #92 · 测试与门禁管线卫生（test-ci-hygiene）

- **文件**：`2026-11-01-spec92-test-ci-hygiene.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
- **依赖**：无
- **内容**：deps.json **_tool_hashes 整删**（r2 改判：G7 不使用、唯一消费者是 R3 自洽检查——零信息量的编辑税；连带 lock-tool-hashes.sh/R3/3 处测试/DepsDoc 字段）+ DepsDoc 单装载函数七读者换装 + REPO_ROOT 常量替 parents[N] 魔法 + **test 与 test-all 合并**（unit 标记退役）+ --cov-fail-under 四拷收敛 pyproject + just lint/type/test-ci 子配方 + pre-push hook 构造性子集（补 hypothesis profile 对齐）+ 死目录/幻影 norecursedirs/contract 孪生/per-file-ignores 整并 + dispatch_payload 构造器首批 5 文件
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（测试/CI 基建）

---

### #93 · 阈值权威化（threshold-authority）

- **文件**：`2026-11-01-spec93-threshold-authority.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
- **依赖**：无
- **内容**：lint_threshold_reconciliation 改 import 执法器读常量（**r2 前置：先提取 CONSTELLATION_HARD_BAND 常量——现为 validator 内联字面量**）+ 删 allowlist bounds 第三源 + --strict 翻转 + **散文↔门裕度决策入 docs/framework/gates.md + g4 注释回指（r2：不改 SKILL.md 散文——卷二开卷前 prompt 行为红线）** + pricing 模型契约 import 单源 + executor 派生集 mtime 失效 + trend 列契约常量与往返测试
- **对应 plan**：待执行时建
- **触及的不变量维度**：情绪节奏（弱关联——pacing 域阈值声明单源化，不新增门检）

---

### #94 · 接口诚实批（interface-honesty）

- **文件**：`2026-11-01-spec94-interface-honesty.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟡 P2
- **依赖**：T4（trace 累积器）须 #87 后施工；其余任务独立
- **内容**：modes 清障（codex_api 死桩/internal 戏服删除，**不建 DispatchRoute Protocol**）+ dispatcher.md 真三路由重写 + cli.py 引擎出鞘 pipeline/orchestrator.py（~700 行搬家）+ scoring argparse 子命令化与归一化单源 + **DispatchContext 收拢 + 删 test_type/round_dir 零传参**（原 #87 T6 并入）+ _DispatchOutcome 累积器（4 trace 块/账目双拷归一，characterization 四出口）+ 文档诚实小批（AGENTS phase_runner 行/ADR 0004/行号注释≥12 处/now_iso 双拷；**_record_gate_manifest 三拷只登记不盲合**）+ 杂项微接口（write mode Literal/asdict/角色名单解析器/closure context_kind）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（接口/文档诚实层）

---

### #95 · 模型契约对齐与上下文预算（model-contract-alignment）

- **文件**：`2026-11-02-spec95-model-contract-alignment.md` ｜ **系列**：卷二实弹复盘批 ｜ **状态**：Active（r1） ｜ **优先级**：🔴 P1
- **依赖**：T3 复用 #81 归档窗口；T4 衔接 #88 finding 契约；其余独立
- **内容**：束1-3 九次人工接骨的根因矩阵（R1-R8，blob 级证据：**教错的**——SKILL 枚举斜杠形/defer 锚零进 prompt/热协议只在监控侧；**看不全的**——settle prompt 68→96k 无界增长+pending_hooks 被 32k 截断后盲写最新钩行；**没锚住的**——drafting 无范例章+JSON 信封长文压缩；**被放大的**——「你丢了行」反馈驱动整档重发越试越糟）＋六任务：T1 gate 词表⇄prompt 契约同步器（lint 进 just check）+ T2 卷期热协议参数下沉 + T3 settle 读面分窗（≤60k 断言+截断告知保底）+ T4 失败反馈改操作路径（verbatim 行清单+修复正例）+ T5 范例章注入+字数落盘早检 + T6 修订场景级 diff 化+束 follower 章 memo 检查点。验收=束4 重跑 ≤1 次接骨（对照束1-3 的 3-5 次/束）
- **对应 plan**：待执行时建（束4 重跑=验收场，亦即 #84 Task 10 解冻条件）
- **触及的不变量维度**：无（prompt/预算/反馈层——不动门禁判据与 truth 结构）

---

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- **「触及的不变量维度」必填节**（spec #80 T10）：每个活跃 spec 的登记块须含一行 `- **触及的不变量维度**：<清单 或 无>`——引用 `docs/framework/invariants.md` 普查表的维度名（如 `恒等 identity/持有与经手 props`）；不触及任何维度写 `无`。`lint_invariant_coverage` 校验活跃项该节存在性（P1 只校 P1 期相维度）
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
