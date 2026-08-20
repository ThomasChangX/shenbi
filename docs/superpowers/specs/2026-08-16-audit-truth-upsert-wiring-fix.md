> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C3，21 条）| **代表 finding:** F360 | **严重度上限:** P0（F360/F868/F1101）| **涉及文件面:** src/shenbi/pipeline/truth_io.py（upsert 原语）、dispatch_helper 写路径、chapter_loop/staging 提交路由、skill_utils/（hook_planting、compute_drift）、约 20 个 append_dedup 技能 SKILL.md

# truth 追加写路径接线（audit-truth-upsert-wiring）

## 背景

候选元根因 B："有键的没接线、接线的没键"。`truth_io.py` 的 append_dedup/upsert 写原语（upsert_markdown_row/upsert_yaml/_upsert_by_key）已实现但生产零接线（T705：3 个 upsert 原语 0 调用），实际派发仍是整文件覆写或让看不到现状的 LLM 盲重建——累积类 truth 数据（章摘要、趋势、钩子、卷摘要）每章丢失/坍缩。三个 P0 均有生产实证：F360（append_dedup 契约更新模式全链路零实现）、F868（volume-consolidation 盲覆写 volume_summaries，reads 不含该文件，旧卷摘要丢失）、F1101（5 章正文被修订技能摘要覆写丢失，不可恢复）。F1104（chapter_summaries 仅 2/56 章）与 F1105（resonance_trend 1 行/audit_drift 1 章）为趋势类同族；F1175 快照实证 state-settling 曾生成 8 truth 文件含 Ch5 摘要但未落盘。

同时原语自身有数据丢失级缺陷（thread-reports/T7.md 写原语矩阵）：T701（dict upsert 整文件结构坍缩——frontmatter/H2/表格/散文全灭，/tmp 实测）、T702（表行键=首格首 token `\S+`，含空格/CJK 键整族互删："第 1 章"行被 upsert 全删，truth_io.py:209/219 协调者核验）、T703（静默丢弃无键新记录）、T706（YAML 解析失败→[] 回退→整文件坍缩重写）、T704/T711（compute_drift 裸 append 非幂等/绕过 safe_write）、T707（restore 链零调用，与 C19 快照簇衔接）。

声明面错配：F828（18 个 updates 目标不在所属技能 reads，API 路由盲覆写；state-settling 6 truth 文件与 arc-payoff 双文件为数据丢失级）、F814（faction-builder 写废弃文件且写未声明、append 语义 vs create_or_overwrite 错配）、F840（review-arc-payoff `key: chapter` 用于卷键文件）、F869（state-settling frontmatter(append_dedup) 与正文(replace) 写模式互相矛盾）、T304（模板自愈环被 replace 写方首写即毁）。

## 修复目标

1. 生产派发路径的 append_dedup 声明 100% 路由到确定性 upsert 原语（LLM 产出补丁，程序合入），累积类 truth 不再整文件重建。
2. upsert 原语自身达到幂等且不丢数据（T7 矩阵全部缺陷修复）。
3. 声明面闭合：updates 目标 ⊆ reads 声明；frontmatter 与正文写模式一致（与 C20 联动）。
4. 防复发：append 路由集成护栏（参照 T409 模式——dead-wire 已两次复发，根因是无护栏）。

## 任务分解

- **T1 · 原语修复先行（T701/T702/T703/T706）**：表行键提取改为显式 key_field 且对含空格/CJK 键按整格取值（T713：key_field 对 str 表行无效需一并修复）；dict upsert 拒绝结构坍缩（保留 frontmatter/H2/body，仅更新目标节）；YAML 解析失败 fail-loud 不回退 []；无键新记录与既有无键记录同策略。验收锚点用 T7 实测用例（"第 1 章/第 2 章"行不互删）。
- **T2 · 派发路由接线（F360/F828/T1402 方向）**：dispatch_helper 写路径按 frontmatter `write_semantics: append_dedup` 路由 truth_io upsert——技能输出"增量行/记录"，程序按键合入。吸收 T14 候选 T1402（state-settling 写半确定性化）作为第一个接线技能，随后扩至 18 个 updates 目标全量。禁止"传给 LLM 全文重写"形态。
- **T3 · 数据丢失级特修（F868/F1101/F1104/F1105）**：volume-consolidation/state-settling/摘要与趋势类技能全部走 T2 路由；修订技能对正文文件一律禁写（只产 diff/摘要到侧车）。
  - **T3 显式输入（2026-08-17 T5 审查发现，F2/F3 级）**：T2 路由已全局生效（声明即路由），但 18 个声明目标中仅键控表行写者（state-settling 全部 6 目标）真正按键合入；其余 8 个写者的**设计格式即无键**，走"无损追加"回退（较 BASE 整替坍缩严格变好但无去重）：plant/resolve/track/lifecycle 输出 YAML 记录块（追加在 frontmatter 外，YAML 记录消费者不可见）；review-resonance/arc-payoff/score-arc 对 audit_drift 输出 bullet。T3 需统一 audit_drift 写者格式为键控表行（或明确分层：键控行技能走 upsert，无键记录技能改走记录级 upsert_yaml——须先补其丢 body 的 T4 遗留）。另：review-resonance 的 resonance_trend 正文示例首格为数字 N，与 chapter_loop 程序写者的 `Ch{N}` 键格式漂移——同章会双行而非幂等，T3 收口键格式；score-volume 的 append_dedup 声明在 `writes:` 段落错位（F814 残留）需挪 `updates:`。drift-guidance 的合并器语义冲突已随 T5 fix 循环改 create_or_overwrite 处理，不在 T3。
  - **T3 显式输入（2026-08-17 final review N1，Important）**：staging 双写者 lost-update——step7(lifecycle)/step8(settling) 并行对（chapter_loop.py run_parallel_post_draft_steps）都以 uses_staging=True 声明 append_dedup 写 truth/pending_hooks.md，而 staging 合并基恒为 live（_route_append_dedup_write staging 分支）→ 后写者胜，先写者增量从 staging 丢失（final review /tmp PoC 实证：lifecycle 的 TRIGGERED 状态丢失）。相对 BASE（裸增量整替，历史全灭）严格改善；T3 根治方向：按文件串行或 staging 链式合并。
  - **T3 显式输入（2026-08-17 PR #43 Copilot 复核，= SDD T2 审查 M1/M5）**：staging 派发的写审计盲区——`_with_write_audit` 的 watch 面为无前缀契约路径，而 uses_staging=True 的派发写 `staging/<contract-path>` → pre==post==unchanged → Tier B 审计与账本对 staged 写（含越权）整体不可见，且会发出 blocked:false 的"空过"记录（audit theater）。T3 方向（Copilot 建议与 SDD 分诊一致）：uses_staging 时快照 staging/<declared> 路径并在调 audit_writes 前把快照键归一化回声明 relpath（去 staging/ 前缀），使 ownership+声明面匹配仍生效。
- **T4 · 声明与模式对账（F814/F840/F869/F824 关联）**：updates 目标补进 reads；`key:` 与文件实际键轴一致（卷键文件用 volume）；frontmatter/正文写模式矛盾以 frontmatter 为准修订正文（G4/lint 拦截面与 C20 联动）。
- **T5 · 幂等与 durability（T704/T711）**：compute_drift 追加改幂等（键去重）且经 safe_write；hook_planting 读-改-写加锁（与 C11 T709 联动）。
- **T6 · 集成护栏**：集成测试跑两章循环，断言 chapter_summaries 行数 == 已完成章数、resonance_trend/audit_drift 行数单调递增（防 F1104/F1105 复发）；`git grep append_dedup` 声明技能全集 × 路由断言。

## 批量清理（纯 M 成员）

- T713（key_field/key_name 对 str 表行无效）并入 T1 修复；T712（replace 模式 dict 输入渲染 Python repr 不可回读）随 T1 的渲染层一并处理。

## 验收标准

1. `uv run python -m pytest tests/unit/test_truth_io.py -k "cjk_key or structure_preserve"`（T1 新增用例，用 T7 实测数据）全绿。
2. `git grep -l "append_dedup" skills/*/SKILL.md | wc -l` 与 truth_io 路由断言覆盖数一致（T2 完成后 ≥ 18 个 updates 目标全路由）。
3. 集成护栏（T6）在 CI 绿：两章 dry-run 后 chapter_summaries.md 行数=2、趋势文件每文件 2 行。
4. `just check` 全绿。

## 风险与回滚

- 风险：T2 改变技能输出契约（增量行而非全文），需要同步修订技能 SKILL.md 指令与 G2/G4 校验口径，改动面大——按技能灰度（state-settling 先行）。upsert 原语修复若引入新回归，幂等护栏（T6）先行兜底。已丢失数据（F1101 5 章）不可由本 spec 恢复，恢复面归 C19 快照簇。
- 回滚：T2 路由按 frontmatter 声明开关（append_dedup 声明存在才走新路径），单技能可回退整文件覆写旧路径；T1 原语修复独立 PR。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C3（21 条，代表 F360）：

F360 F814 F828 F840 F868 F869 F1101 F1104 F1105 F1175 T304 T701 T702 T703
T704 T705 T706 T707 T711 T712 T713
