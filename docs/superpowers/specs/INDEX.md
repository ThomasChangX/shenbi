# Spec 执行索引

> **最后更新**：2026-11-14（**#88 完结归档**（PR #334——finding 契约统一：finding() 发射器+AST lint+四类拓扑改写[ss. 13 站点/纯中文 11 新 id/变量前缀 5 站点字节等价]+check_id 单源[数字安全]+精确 id 匹配[29→2 活键]+inventory 193 id 双向防漂+全 checker 参数化；REWRITE 一轮[PR #333]+七轮 spec 审查+五轮 plan 审查；T1-T8 全 audit+终审 Ready；有意修正三例全钉死）；前次 #88 r2.2→r2.8 修订链（**#87 完结归档**（PR #331——god 文件拆分：chapter_loop 4,820+dispatch_helper 4,663=9,483≤9,500；五体制出鞘+位置作用域四钩+ExtractSpec 注册表坍缩 11 臂[−252 行]+BuiltPrompt NamedTuple 63 位点零破坏+子串判定双路径根除+18 符号正名+tests 私有 import 基线 170 冻结；两轮驳斥+四轮 spec 审查+六轮 plan 审查；T0-T5 全 audit+终审 PASS；行为保持=T0 八路径 characterization 拆分时刻零改动）
> **活跃 spec 数**：8

本页**只追踪活跃（待执行）spec**，按推荐执行顺序排列：优先级 🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量，同级按编号升序。
已完成/合并/驳回的 spec 移至 `archive/`（按日期排序），**本页不追踪归档**——归档历史查 `archive/` 目录与 `git log`。

---

## 执行队列


### #89 · 门禁内部性修复（gates-internal-repair）

- **文件**：`2026-11-01-spec89-gates-internal-repair.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟠 P1
- **依赖**：无（r2 修正：CHAPTER_NUM_RE 已存在于 gates/shared.py:182，无需 #85 前置）
- **内容**：g4_chapter_drafting CheckContext 一次装载（772 行主函数 <300；plan 每章读 1 次非 5 次）+ 章号正则 **AST 判据**归零（实测 20 处内联，含 g6_checks）+ 四窄助手（chapter_no/load_facts_oracle（**6 处/3 文件，删 ss 伪条目**）/degrade/**RoundPaths.require_roots 落 paths.py:55**；**明确不做 table-DSL**）+ shared.py 出鞘（write_gate_marker 迁 gate_manifest、**segment_sentences 迁 text/（仅 1 符号；strip_narrative_body 的 frontmatter 面归 #85）**、import 时 FS 扫描惰性化）+ 4 门禁助手正名公共（**实为 1 个真改名** + `_declared_history`）+ g4_cross_chapter 非注册表门文档化 + G0.12 假检查真实现（**集合对账，不 import g4**）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（门禁内部结构，characterization 先行）

---

### #90 · 契约数据面单源（contract-data-single-source）

- **文件**：`2026-11-01-spec90-contract-data-single-source.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟡 P2
- **依赖**：无（spec #9 裁决约束已核——不新增契约模型消费）
- **内容**：**一个权威集合 + 三处派生（零构建基础设施）**：G4_CHECKER_KEYS 迁 **零依赖叶 g4/roster.py** 为单源 → G4_CHECKER_SKILLS 别名 / SHORT_MAP 机械派生 / build_checkers 断言对齐（加 checker 从 5-6 处编辑降到 2 处）+ lint 9 面收缩（AGENTS.md 计数面实测恒真——删或补真计数）+ lint_decisions_sources 弃 crude scan 走 load_contract + STEM_TO_SKILL 派生（N/N+1 归一，二义即 fail）+ decisions 枚举 value-set 对账（status-vocab 模板；**Per-Skill 表生成器 r2 裁剪**）+ writing-skills 机器契约节 + lint_contract_prose **allowlist 迁 tools/ 配置（r2.2：frontmatter 会进 system prompt，红线失真）**
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（契约/名册数据面）

---

### #91 · 状态与并发纪律（state-and-concurrency-discipline）

- **文件**：`2026-11-01-spec91-state-concurrency-discipline.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟠 P1
- **依赖**：与 #87 的 chapter_loop 调用点撞面时 #87 先行、本 spec 适配新结构
- **内容**：gate_passed 单源（5 定义 SKIP 语义分歧收敛，容忍度逐点显式 + characterization 钉死）+ 失败协议纯函数共享（**r2.2：复用既有 classify_dispatch_failure——r2 的 is_deterministic_failure(gate_result) 系凭空新造**；genesis 补传 failure_class）+ ledger_archive 锁窗口闭合（**确定性红测重设计：注入 _section_fields；红绿两测形态不同**）+ dispatch_helper outline 合并同修 + **retry 助手接线**（increment_retry/reset_retry 接线；**新增 increment_retry_budget——charge 是幂等 max 不能承接串行增量**）+ retry_feedback 10 处裸写回归封装（含 pop 与 triggers/cli 点）+ dispatch_with_retry 正名/run_post_draft_pair 改名（**semaphore 改可选+nullcontext**）/信号量戏法删除
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（运行时状态纪律；SKIP 语义 characterization 先行）

---

### #92 · 测试与门禁管线卫生（test-ci-hygiene）

- **文件**：`2026-11-01-spec92-test-ci-hygiene.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟠 P1
- **依赖**：无硬依赖（与 #90/#93/#95 共 justfile/lint_registry 文件面，顺序见「批次 A 共享文件面」表）
- **内容**：deps.json **_tool_hashes 整删**（G7 不使用、唯一消费者是 R3 自洽检查；连带 lock-tool-hashes.sh/R3/**5 处测试+2 处 G0.14 断言+3 份活文档**/DepsDoc 字段）+ DepsDoc 单装载函数 **6 个 src 读者+3 tools** 换装（phase_runner 同名 load_deps 改薄包装）+ REPO_ROOT 常量替 parents[N] 魔法（7 点）+ **test 与 test-all 合并**（`unit` 标记退役**三选一**——`--strict-markers` 下删定义=全仓 1,153 处标注收集 ERROR，已复现）+ --cov-fail-under 四拷收敛 pyproject + just lint/type/test-ci 子配方（lint 20+#95 新增 1）+ pre-push hook 构造性子集（补 hypothesis profile 对齐）+ 死目录/幻影 norecursedirs/contract 孪生/per-file-ignores 整并 + dispatch_payload 构造器首批 5 文件；**＋tests/pipeline pytest-randomly 顺序 flake**（束7 实测：随机序 6 失败/固定序双侧全绿——顺序敏感根因待查，2026-11-08 束7 发现）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（测试/CI 基建）

---

### #93 · 阈值权威化（threshold-authority）

- **文件**：`2026-11-01-spec93-threshold-authority.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟠 P1
- **依赖**：无
- **内容**：lint_threshold_reconciliation 改 import 执法器读常量（**r2 前置：先提取 CONSTELLATION_HARD_BAND 常量**；**r2.2：判定式改包含式**——原相交式仍放行带内漂移）+ 删 allowlist bounds 第三源 + **新增 `--strict` 并接线**（现不存在）+ **散文↔门裕度决策入 docs/framework/gates.md + g4 注释回指（不改 SKILL.md 散文——束4 验收后窗口 prompt 行为红线）** + pricing 模型契约 import 单源 + executor 派生集 mtime 失效 + **trend 列契约常量覆盖三消费者（writer/escalation_bridge/confidence_calibration；r2.2 更正：compute_drift 按表头名读、无 cells[6]）**
- **对应 plan**：待执行时建
- **触及的不变量维度**：情绪节奏（弱关联——pacing 域阈值声明单源化，不新增门检）

---

### #94 · 接口诚实批（interface-honesty）

- **文件**：`2026-11-01-spec94-interface-honesty.md` ｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟡 P2
- **依赖**：T4（trace 累积器）须 #87 后施工；**T6 须 #85 后**（split_frontmatter）；其余独立
- **内容**：modes 清障（codex_api 死桩/internal 戏服删除，**不建 DispatchRoute Protocol**；错误移 `dispatch()` else 非 detect_mode）+ dispatcher.md 真三路由重写 + cli.py 引擎出鞘 **orchestration/checkpoint_flow.py**（~950 行搬家——**含 cmd_review 决策体才达 <900**）+ scoring argparse 子命令化与归一化单源（**补 codex 调用方迁移/shim；差异 4 项**）+ **DispatchContext 收拢 + legacy 参数文档化（test_type/round_dir/skip_reads）**（原 #87 T6 并入）+ _DispatchOutcome 累积器（4 trace 块/账目双拷归一，characterization 四出口**归一化白名单**）+ 文档诚实小批（AGENTS phase_runner 行/ADR 0004/行号注释 **6 处（src）**/now_iso 双拷；**_record_gate_manifest 三拷只登记不盲合**）+ 杂项微接口（write mode Literal/asdict/角色名单解析器/closure context_kind）
- **对应 plan**：待执行时建
- **触及的不变量维度**：无（接口/文档诚实层）

---

### #96 · 反 AI 检测体系方法论对齐（anti-ai-tell-alignment）

- **文件**：`2026-11-04-spec96-anti-ai-tell-alignment.md` ｜ **系列**：文笔面强化批（humanizer 对标） ｜ **状态**：Active（**r2** 2026-11-04——吸收第二源 Humanizer-zh＋实弹过滤） ｜ **优先级**：🟡 P2
- **依赖**：**#95 T1（词表/枚举常量单源）落地后施工**（先动=双源复发；#85 已完结）；**批次 A 清偿后启动**（主战场 SKILL.md×3＋review_checklist.py 预计算，不抢 chapter_loop 最热文件）；验收搭卷二实弹后续章不开新探针
- **内容**：双源对标（blader/humanizer v3.1.0＋op7418/Humanizer-zh 中文改编版，调研全录 docs/research/2026-11-04-humanizer-skill-analysis.md 与 -zh-skill-analysis.md）——已覆盖 7 条不重做＋**五缺口**：G1 机制层解释缺失/G2 证据分级聚集规则缺失（口癖帽×voice 互斥即 over-enforcement 实案）/G3 结构 tell 缺口/G4 anti-detect 工艺薄弱（无例证+无人味保留清单+不读 #71 正向资产）/G5 事实守恒无显式复核＋**r2 实弹过滤（novel-xinghuo-vol1 42 章 15.8 万字测频，§0.4）**：zh F 组中文 tell 四剔除（层叠的/进行+动词/被字句/随着——零真阳性）两弱化（排比堆叠仅语义判定+真枚举/声口排比豁免；中段收束降弱 tell）一撤销（重复句首——62 处全为跟拍合法形态）；吸收三件套体例（改写前/改写后/保留）+六维改写安全核对（施事者/时间/条件/范围/否定/归因+确定性传递防认知态漂移）+样本防污染+结构保护比对；不跟随 zh 三宽松化（删分级/删机制模型/破折号条件化）＋四任务：T1 D3 机制段+强/弱 tell 分级（**机器面硬闸一律不动**）+ T2 结构 tell 两条进 D3（参考计数不设硬阈值）+ T3 anti-detect 工艺升级（10 手法三件套/人味保留/reads 接声口指纹+金句位/六维对照/整段重述第 10 手法）+ T4 技能测试+实弹回归（audits 误报不升、剔除面零误报、金句位零丢失）。**根本裁定**：humanizer「不以过检测器为目标」对 shenbi 不适用（平台 AIGC 检测=商业约束）——检测器导向硬闸全保留，两目标并存
- **对应 plan**：待执行时建（`../plans/2026-11-04-spec96-*.md`）
- **触及的不变量维度**：叙事纪律（POV/声口）（弱关联——T3 人味/声口保留面）；其余为审计/改写工艺层

---

### #97 · pre-commit hook rev 落地链（precommit-rev-landing）

- **文件**：`2026-11-06-spec97-precommit-rev-landing.md` ｜ **系列**：工具链卫生批（PR #288 后件） ｜ **状态**：Active（**执行完毕待归档**——T0-T3 落地 2026-11-06［PR #293］＋首跑验收三指标全过 2026-11-09［run 42549398259：success·零 bot PR·C13 守卫绿·分支零残留，§首跑验收结果］；站点数勘误 7 非 6［archive.py:195 保留 noqa］+uv.lock ruff/mypy 双对齐为 spec 未预判的第 5 组 bump） ｜ **优先级**：🟠 P1（死线已达成——周 bump 管线稳态）
- **依赖**：**T0 前置 = PR #288 合并**（守卫/两遍验证执法面）；与批次 A 无文件域冲突，**先于批次 A 执行**（小件+死线，不触最热文件）
- **内容**：四组 rev 落地（ruff 0.15.17→0.17.3/mypy 2.1.0→2.4.1/pre-commit-hooks 4.5.0→6.0.0/shellcheck→-1）＋C13 理由迁移（**RUF100×6 判死实锤**——`uvx ruff@0.17.3` 干跑确认；六站点 noqa 删指令留纯注释理由，pyproject 治理注释同步演进，`grep -rc "C13 allowlist" src/` ≥6 红测）＋**冻结单源**（#288 的 hook 级 ruff-format exclude 收敛为 pyproject `[tool.ruff]` 单源——干跑实锤直接 `ruff format` 面不认 hook 级；活面残留仅 2 md 顺手清零）＋新规 fallout（**PLR0917×29 ignore 挂账批次 A 后**不做签名重构；tests 非法 noqa 1 处修）＋首跑验收观察点。回测基线 7725f002（173 文件污染批，已删）。干跑证据：format 面 169（archive 166＋活 2＋audit 1）/lint 面 35 零 md
- **对应 plan**：已建 `../plans/2026-11-06-spec97-precommit-rev-landing.md`（T0-T3+首跑验收全落，含 §首跑验收结果）
- **触及的不变量维度**：无（工具链卫生）

---

## 批次 A 共享文件面与施工顺序（2026-11-02 r2.2 审计增补）

同一文件同一时间只允许一个 spec 施工；跨 spec 共享文件的建议顺序（与各 spec 依赖字段不冲突时以本表为准）：

| 共享文件 | 触及 spec | 建议顺序 |
|---|---|---|
| `gates/shared.py` | #88 finding/#89 出鞘/#90 别名 | **#89 → #88/#90** |
| `justfile` check 面 | #95 T1 lint/#93 --strict/#92 子配方 | **#95 → #93 → #92** |
| `tools/lint_registry_reconcile.py` | #90 T2/#92 T1 | **#90 → #92** |
| `phase_runner.py` | #92 T2 loader/#94 T5 now_iso | **#92 → #94** |
| `pipeline/chapter_loop.py`（最热） | #86 T3/#87 T3/#88 T3/#91 T4/#93 T5 | **#95 → #86 → #87 → #88/#91/#93/#94**（每 plan 首步 re-anchor；#95 的分窗/早检/修订先落） |
| `pipeline/cli.py` | #94 T2 | #94（cli→orchestration/checkpoint_flow.py） |

**总序**：#85 → #95（T1-T6 实现落地）→ 束4 验收 → #86 → #87 → 其余批次 A（#88/#89/#90/#91/#92/#93/#94 按上表与依赖插入）；#84 的 T0-14 已补落（PR #325，2026-11-10 归档）；#96（humanizer 对标批）批次 A 后启动——依赖 #95 T1 词表单源先行；**#97（工具链卫生小件）死线驱动插队先行——2026-11-09 修复版工作流首跑前清偿，T0 前置 #288 合并（已达成：首跑验收三指标全过，待归档）**；**#98 已完结（2026-11-08 归档）——束7 判定 PASS（强）：flash+thinking 启用规划 1 派收敛，卷二解堵；残余族（草写字数/settle matrix 增量）另议**。

## 登记与编号约定

- 新增 spec 时在此登记：`### #NN · <title>` + 文件/系列/状态/优先级/方法/依赖/内容/对应 plan 字段；编号 = 现有最大号 +1
- **行号锚纪律（r2.2 新增）**：spec 内行号为立项/修订时点快照（本批已按 2026-11-02 当前树全量对码，含 #275 后 +3 漂移）；**每一份 plan 首步必须按函数/符号 re-anchor**，不得直接沿用行号——#85/#95 落地后 chapter_loop/dispatch_helper 的绝对行号必然再漂。
- **「触及的不变量维度」必填节**（spec #80 T10）：每个活跃 spec 的登记块须含一行 `- **触及的不变量维度**：<清单 或 无>`——引用 `docs/framework/invariants.md` 普查表的维度名（如 `恒等 identity/持有与经手 props`）；不触及任何维度写 `无`。`lint_invariant_coverage` 校验活跃项该节存在性（P1 只校 P1 期相维度）
- spec 完成（Done）或驳回（Rejected）→ 移 `archive/` 并从本页删行；**编号是历史唯一标识，不重编号、不复用**（系列/依赖字段按编号交叉引用，重编号会断链）
- 本页不维护归档计数与归档分类汇总
