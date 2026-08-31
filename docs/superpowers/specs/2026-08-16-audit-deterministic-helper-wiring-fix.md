> **Date:** 2026-08-16 | **Revised:** 2026-08-31（v2：价值门删 F376/F604；v3：阶段 3 设计审查 1C/3I/5M 修订；v4：route_block 权威冲突裁决等二轮修订；v5：anti-ai 活面重定向等三轮修订；v6：四轮审查 1C/1I/3M 修订——校准覆盖落点改为置信度单元格 patch（trend 行 insert-only 语义下技能富行 wins 的正常路径也可覆盖）、route_block SKILL.md 删除面扩全、缓存 version 字段为新建非 +1）| **Status:** Design (Revised 2026-08-31) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C7，原 5 条，修订后 3 条）| **代表 finding:** T1442 | **严重度上限:** P1 | **涉及文件面:** src/shenbi/skill_utils/（compute_stats、compute_pattern、recall、calibration、review_resonance.routing、review_checklist）、pipeline/（chapter_loop、dispatch_helper、hook_planting、genesis、triggers）、skills/（shenbi-review-anti-ai、shenbi-chapter-drafting、shenbi-review-resonance、shenbi-foreshadowing-plant 等正文改引 helper 输出）、tools/lint_helper_usage.py（新增）

# 确定性 helper 派发接线（audit-deterministic-helper-wiring）· v2

## 背景

候选元根因 C（边界收窄版）：确定性统计/检查 helper 已实现但派发仍纯 prompt——LLM 每章手算机器已能算的量，并**复刻其 bug**。

**v2 修订记录（2026-08-31 价值门驳斥复核，agent 全量 + 协调者 file:line VERIFY）**：

- ~~F376/F604（baseline 生产者零调用死线）~~：**已修**——`establish_baseline` 生产调用已存在（chapter_loop.py:1964-1966，PR #70 spec #11 R1 引入，PR #124 spec #32 加固）；原验收条件 1/2 已在 main 满足。本 spec 删除该任务（原 T1）。
- T1440/T1441/T1442 复核存活（证据见各任务节）。

修订后核心 3 条：

- **T1440**：hook_planting 确定性替换是**不可达死代码**——`plant_hooks_from_plan` 唯一调用点 chapter_loop.py:2819 的分支条件 `step.skill == "shenbi-foreshadowing-plant"`，但该技能已弃用不在 CHAPTER_STEPS（:129 注释、:192 仅存合并体 shenbi-foreshadowing-lifecycle）；plant 三个活跃面（genesis.py GenesisStep(9)、triggers.py:297 卷边界 TriggerStep、skills/shenbi-foreshadowing-plant/SKILL.md 手动路由）仍全走 LLM dispatch。
- **T1441**：anti-ai 检查与 G4 确定性检查构成双重体系（**v5 活面修正**：`shenbi-review-anti-ai` 已标 DEPRECATED 2026-07-19、无生产派发点；**活面是 `shenbi-review-group-craft`**——chapter_loop.py:224 CHAPTER_STEP，其 SKILL.md:207-226「检查执行」含同样 10 项确定性检查且要求 LLM 逐一执行，其中第 4 项转折词密度未标阈值）——10 项检查由 LLM 每章重算（`review_checklist.inject_checklist_into_prompt` 注入所有 `*review*` 技能但只给词表/预算，不给预计算计数）；同名检查阈值三面分裂：转折词密度 G4 `max(5, wc//1000)`（gates/g4/chapter_drafting.py:200）vs checklist.md:25 `max(1, floor(字数/3000))` vs `skills/shenbi-chapter-drafting/anti-ai-reference.md:20-22` `每3000字≤1`（注意路径：在 chapter-drafting 技能目录，非 review-anti-ai）。
- **T1442**：确定性统计 helper 五件套仍纯 prompt 级接线——src 生产代码零调用（仅 `__main__` CLI），dispatch_helper 无预计算注入钩子，SKILL.md 正文要求 LLM 自行执行 `python -m shenbi.skill_utils...`（如 shenbi-review-resonance/SKILL.md:65-66）。**按输入来源拆两半（v4 精化）**：派发前可预计算注入的是 compute_stats（输入章文件）与 compute_pattern 的**历史窗口半**（输入持久化的 `outline/chapter_patterns.md`；其"当章分类"半依赖 LLM 输出，不可预计算）；calibration（`calibrate_confidence(reported, hr)`——reported 是 LLM 自报置信度）只能派发后强制。**routing 权威裁决（v4）**：生产路由已由 `pipeline/revision_router.route_chapter_revision`（复用 `skill_utils/revision_routing`，chapter_loop.py:1823 消费）确定性地框架侧决策——`review_resonance/routing.py:route_block` 是**竞争性重复三路模型**（不同阈值/置信门/上限），接线它会在框架层再造一个双重体系（正是本 spec 要消除的对象）→ 裁决：route_block **作为重复死模型删除**（与 T2 死面清理同性质），revision_router 是唯一路由权威；不接线。另注：主生产路由（API 派发）下 LLM 根本无法执行 `python -m`，这些 SKILL.md 指令在主路由上是死指令而非"LLM 重算"。

先例佐证：仓库已 16 次实现该模式但仅 ~5 个代码层接线（T14-07 母模式）；归档 spec #3（确定性技能替换审计）已给出提升判据（纯文件操作/键值 upsert/计数/固定模板填充/阈值比较），#14 已覆盖统计**正确性**、#11/#32 已覆盖 baseline 接线——本 spec v2 只管五件套/anti-ai/plant 的**接线与死面**。

## 修复目标

1. T14 候选表按优先级接线：T1403 anti-ai dim3 前置 + T1442 接线（前三件派发前注入、后两件派发后强制）。
2. 消除双重体系：anti-ai 同名检查 LLM 版删除或降级为"引用 helper 输出"，阈值口径对齐 G4 单值。
3. 清除 T1440 不可达死分支，plant 活跃面二选一裁决（确定性路由或删死码保留 LLM 面）。
4. 防复发：派发前钩子 lint——凡 helper 已覆盖的统计类输出，SKILL.md 正文必须引用 helper 结果而非要求 LLM 重算。

## 任务分解

- **T1a · 派发前注入（compute_stats 全量 + compute_pattern 历史窗口半）**：dispatch_helper 派发前钩子（与既有 plan_skeleton/review_checklist 注入同层）——对声明了对应 helper 的技能，把预计算结果作为 prompt 注入块。**compute_pattern 输入路径（v5）**：当章分类由 LLM 产生、历史累积需结构化数据——不解析 LLM 变格式的 markdown 报告表，改为派发后把每章分类追加到结构化累积（keyed truth 行或 decisions sidecar，走契约声明与三源同步），下次派发前从该结构化累积预计算注入；首跑/缺文件 fallback 为空历史（显式披露）；fixture 需真实上游产物（若无现成 `outline/chapter_patterns.md` fixture，用既有章节 fixtures 驱动上游生成路径产出，G0.9 禁手写）；"删除请计算指令"通过**静态修订 SKILL.md 正文**实现（正文改引 helper 注入块，改后走 `just lint-contracts` + `just generate` 三源同步；不做运行时正则改写系统 prompt）。per-skill 开关机制沿用 executor_config.toml 既有模式，配一条回退路径测试（开关关→无注入块）。**foreshadowing-recall 面（v4）**：grep 显示 shenbi-foreshadowing-recall 无生产派发点（仅 chapter_loop.py:3109 manifest 更新钩子，技能已列弃用注释）→ 不做注入接线（防 dead-wire），其 recall helper 的处置并入 T2 死面裁决一并核查。
- **T1b · 派发后强制（仅 calibration）+ route_block 死模型删除**：前置——review-resonance 产品契约新增机器可解析的 confidence 与锚点判定字段（写入其 decisions sidecar / 报告结构，走契约三源同步）；框架在解析→落盘路径上从累计的 resonance 历史计算 HitRate，调用 `calibrate_confidence` 复算并**覆盖**落盘的 confidence 值（v6 落点重设计：trend 行经 `write_truth_file(mode="insert_markdown_row")` 是 insert-only——技能自写富行存在时框架占位行被跳过，这是**正常生产路径**，只 patch 框架占位行会漏掉主路径）——落点为：解析后对 truth 中该章 trend 行（无论技能富行还是框架占位行 wins）做**置信度单元格级 patch**（沿既有 keyed upsert 设施，只改 confidence 单元格，不动其余列；行缺失时写框架占位行再 patch），并在 decisions sidecar 记录校准前后值；不改写 LLM 已过 G2/G4 校验的报告 markdown，顺序在解析后、下一章派发前（LLM 自报值降级为参考、降级事件 structlog 披露）。技能契约同步修订：review-resonance SKILL.md 的 trend 行写入声明注明 confidence 单元格由框架校准后 patch，技能写自报原值即可。routing 半按背景节裁决：**删除 route_block 重复模型**——删除面（v5 补全）：`review_resonance/routing.py`、`review_resonance/__init__.py` 的 re-export（route_block/Routing/RevisionLoop/BORDERLINE_BAND/MAX_AUTO_REVISIONS）、`review_resonance/__main__.py` 的 routing 子命令、`skills/shenbi-review-resonance/SKILL.md` 中 routing 全部绑定面（v6 扩全）：铁律3 `python -m` 指令、铁律5「降级后的置信度才用于 §5.4 分流」（:68）、DOT 流程图「§5.4 分流 (确定性 routing)」节点（:81-82）、阻断规则「按 §5.4 三路径分流」（:114）、「置信度守护与分流（§5.4）」整节（:116 起）——routing 指令随死模型删除，confidence 校准叙述改为「框架自动执行」并注明 trend 行 confidence 单元格由框架 patch、`tests/unit/skill_utils/test_routing.py` 与 `test_confidence_routing_integration.py` 同步处置。revision_router 保持唯一权威。
- **T2 · hook_planting 死分支裁决（T1440）**：二选一——(a) 三个 plant 活跃面（genesis step 9 / triggers 卷边界）路由到 `plant_hooks_from_plan` 确定性实现；(b) 删除死面、保留 LLM 面。倾向 (b)：plant 输出依赖 plan 语义扩展（expand 模式），确定性实现仅覆盖固定场景。**清理面清单（v4 纠偏）**：chapter_loop.py:2819-2826 死分支、pipeline/hook_planting.py 死实现、dispatch_helper.py:385 OPTIONAL_READS 条目、tests/unit/pipeline/test_hook_planting.py 及其他引用死实现的测试同步处置（验收 grep 范围含 tests/）。**保留**：genesis.py:97 `_INDEX_UPDATE_SKILLS` 条目——选 (b) 时 LLM plant 面仍写 `truth/pending_hooks.md`，该条目驱动其后的实体索引更新，是活代码非残留。另核 `skills/shenbi-foreshadowing-plant/SKILL.md` 手动路由面与 using-shenbi.md:73 路由表是否随之更新。**recall 死分支（v5）**：chapter_loop.py:3109-3110 `shenbi-foreshadowing-recall` 分支同属不可达（技能不在 CHAPTER/CONDITIONAL_STEPS），一并核查处置。
- **T3 · anti-ai 双重体系收敛（T1441/T1403）**：**编辑面 = `skills/shenbi-review-group-craft/SKILL.md:198-226`（活派发面）**，弃用的 `shenbi-review-anti-ai/checklist.md` 作为死资产随 T2 死面一并处置（删或归档注记）。dim3 的 10 项确定性检查中可程序化项（转折词计数、AI 标记词计数、CV 等）派发前算好**并入既有 `review_checklist` 审查参考数据注入块**（不新增第二个注入块），group-craft「检查执行」清单只保留非确定性项并改引注入块；转折词阈值三面收敛到运行时实际注入的 G4 口径 `max(5, wc//1000)`（anti-ai-reference.md 与 group-craft 改引该口径；**分母统一**：`review_checklist.py` 的预算计算改调 `gates/shared.py word_count_md`（弃用 `_estimate_chapter_char_count` 的全字符口径），保证与 G4 同值；预计算统一使用 `gates/shared.py:429 count_transition_words` 单实现；ReviewChecklist 注入块扩展新计数/CV 字段时**新建缓存 `version` 字段**（现缓存 JSON 无版本字段；version=1 起步，不匹配即重生成）强制失效既有 `context/review-checklist-{ch}.json` mtime 缓存，避免旧缓存静默缺新字段）。**后果显式化**：6000 字场景下审查层允许转折词从 2 放宽到 6（3×），anti-ai LLM 层该项不再比 G4 灵敏——这是"消除双重体系"的接受代价，且 checklist.md 当前值本就与运行时注入（review_checklist.py transition_budget=max(5, wc//1000)）矛盾。thresholds.py 全局单源归 spec #35/C9，本处不越界（#35 若后续迁移字面量属预期二次触碰）。
- **T4 · lint 防复发**：`tools/lint_helper_usage.py`——SKILL.md 中「计算/统计/计数」类指令若命中 helper 能力清单则 WARN，要求改引 helper 输出；接入 just check。**顺序约束（v5）**：T4 在 T1a/T1b/T3 的 SKILL.md 修订之后落，否则 lint 会对本 spec 要删的指令报红。
- **T5 · 后续候选（T1404-T1419）**：P2 候选（T1404-T1409）按 T14 评估表在上述完成后排期，本 spec 不展开；P3 候选归批量清理储备。

## 批量清理（纯 M 成员）

本簇无 M 级成员（T1440-T1442 为 P2，T1403 为 P1 联动）。

## 验收标准

1a. 派发 prompt 断言（fixtures 驱动单元测试，直接构造派发 prompt，禁现场 dispatch）：style-learning / chapter-pattern 类派发 prompt 含对应 helper 预计算结果块（pattern 为历史窗口半）；SKILL.md 正文不再含 `python -m shenbi.skill_utils...` 自执行指令（改为引用注入块）；per-skill 开关关闭时无注入块。
2. T1440 裁决落地：选 (a) 则 genesis/triggers plant 面走 `plant_hooks_from_plan`（grep 生产调用点）；选 (b) 则死分支/死实现/OPTIONAL_READS 条目/genesis 技能集残留全清（`git grep plant_hooks_from_plan src/ tests/` 零残留）。
1b. 派发后强制断言：review-resonance 输出经 `calibrate_confidence` 复算覆盖（fixtures 驱动：构造高报置信度+低锚命中率的累计历史，断言落盘值为降级后的 mid，且降级有 structlog 事件）；`git grep route_block src/ tests/ -- ':!tests/coverage'` 零残留（死模型已删；tests/coverage 为生成物，重跑覆盖率后消散）。
3. group-craft 派发 prompt 含确定性检查预计算块（计数/CV，并入审查参考数据块），group-craft/anti-ai-reference.md 转折词阈值与 G4 一致（同分母 `word_count_md` 下同值断言测试）。
4. `uv run python tools/lint_helper_usage.py` exit 0（或输出仅剩已裁决豁免项），且该工具已加入 justfile `check` recipe（`just check` 实际执行到它）。
5. `just check` 全绿。

## 风险与回滚

- 风险：派发前钩子增加每派发延迟；预计算注入扩大 prompt 体积——与 C28（冗余注入）联动监控 token 面。helper 结果注入后 LLM 可能"照抄"错误值——统计正确性由 #14 的度量修复保障，本 spec 只保证接线。
- 回滚：钩子层带 per-skill 开关，可单技能回退纯 prompt 路径；T2 选 (b) 时删除为纯减法。

## 簇成员清单（与 phase4-clustering.md §2 机械对照，v2 修订）

C7（原 5 条，v2 存活 3 条）：

- FIXED：F376 F604（PR #70 4263df55 + PR #14/#124 承接）
- LIVE：T1440 T1441 T1442
