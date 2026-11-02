# Spec #89 · 门禁内部性修复（gates-internal-repair）：CheckContext 一次装载、四窄助手、shared.py 出鞘、调用缝说真话

**日期**：2026-11-01（r2 修订 2026-11-02：**删除对 #85 的伪依赖**——CHAPTER_NUM_RE 已存在；RoundPaths 落点修正 paths.py；text 合流目标核清；**r2.2 2026-11-02 全量对抗式审计修订**——T2 grep 空判据改 AST、T3 删 ss 伪条目、T4 strip_narrative_body 归 #85、T5 正名事实更正、T6 恒真断言改集合对账）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #4/#17/#18 卡；协调者亲验：`g4_chapter_drafting` 主函数恰 772 行；`CHAPTER_NUM_RE` 在 gates/shared.py:182 **已存在**（gates/g4 与 g6 零使用）；`class RoundPaths` 在 **src/shenbi/paths.py:55**（非 gates/shared）；`_ending_archetype_of` 被 audit_context_cache.py:124 跨包 import（带 pyright 压制）；`check_chapter_title`/`check_hook_fulfillment` 被 chapter_loop.py:3503/3511 惰性 import

**触及的不变量维度**：无（门禁内部结构；判定语义不变——characterization 先行）

---

## 0. 根因

ADR 0008 strangler 分件完成但未剪枝：g4_chapter_drafting 单函数 772 行横跨 6 spec 的 ~20 项检查，逐检查重推导同一上下文（plan 同文件每章重读 5 次；章号内联正则 ×5-6）。`gates/shared.py` 923 行是单子算术楼：含写文件函数、import 时 FS 扫描、文本原语错置（skill_utils 因此倒依赖 gates）。33 checker 间 ~10-30% 脚手架拷贝。pipeline 直连门禁内部（`g4_cross_chapter` 根本不在 build_checkers 注册表——注册表对「哪些门存在」说谎）。

## 1. 任务分解（**抗过度工程裁决先行：不做 table-DSL**）

### T1 · CheckContext 一次装载（chapter_drafting）
循环顶构造 `CheckContext`（content / memo_text / chapter_no / project_root / props/counters/identity facts oracle），plan 读 1 次入 context；~20 检查从 context 取；主函数目标 <300 行，检查体拆为该文件已会写的具名函数（`_spec82_hook_rotation` 样板）。**characterization**：既有 10 个测试文件全绿不动。

### T2 · 章号单源采用（**无 #85 依赖**）
`CHAPTER_NUM_RE`（gates/shared.py:182）已存在，直接采用：g4 全域内联 `chapter-(\d+)` 实测 **20 处**（chapter_drafting ×6 :490/:598/:851/:986/:1123/:1140、cross_chapter ×5 :118/:698/:721/:822/:939、generic ×2 :250/:314、chapter_planning :561、decisions_validator :65、g6 :87/:421/:431、**g6_checks :42/:127（r2.2 补——r2 清单漏）**）→ 换常量；chapter_planning 的 `-(\d+)-plan` 分歧形态（:763）统一。
**判据（r2.2 替换——原 grep 写法在 shell 里恒 0 输出、即便零工作量也绿）**：落 `tests/unit/gates/test_chapter_num_single_source.py`，AST 遍历 `re.compile/search/match` 字符串常量，断言 `gates/` 下除 `shared.py:182` 无 `chapter-(\d+)` 字面量；`chapter_no()` 内部用 `CHAPTER_NUM_RE.search`，但 decisions_validator 的 `-decisions.json` 与 chapter_planning 的 `-plan` 保留**后缀断言**（裸 `chapter-(\d+)` 会把任意 `chapter-N-*.ext` 都匹配）。

### T3 · 四窄助手（跨文件拷贝收敛，非框架）
- `chapter_no(path)`（封 T2 常量）；
- `load_facts_oracle(project_dir, dim)`（`load_facts + is not None and not is_empty` 三连收敛——**r2.2 更正：state_settling.py 全文无 `load_facts`**，真实面是 chapter_drafting:552-571（3 次 :555/:558/:562）/ chapter_planning:631-634 / cross_chapter:888-920（2 次 :890/:916）＝ **6 处/3 文件**）；
- `degrade(check_id, reason)`（「degradation visible」WARN 惯用串 ×6 收敛）；
- `RoundPaths.require_roots()`（**落 src/shenbi/paths.py:55 的 RoundPaths**）——11 个 checker 的 7 行同体前导（含同串 ValueError）收进构造/类方法。

### T4 · shared.py 出鞘（不重排整体，只搬错置件）
- `write_gate_marker`/`marker_filename`（**r2.2：marker_filename 在 :692-699、write_gate_marker :701-726**）迁 `gate_manifest.py`（record_gate_result 已在彼）；消费者 `scoring.py:16,281,299,307`、`gates/cli.py:116,194,202,206` 同步换源；
- 文本原语迁 `shenbi/text/`：**只搬 `segment_sentences`（shared:374）**——**r2.2 改判**：`strip_narrative_body`（shared:337）尾部依赖 `META_BLOCK_RE`（shared:36）与 `strip_scene_markers`（shared:50），只搬它会反向 import gates.shared（正是本 spec 要解的倒依赖），三个一起搬则「仅新增两函数」不成立；且其首段 frontmatter 剥离与 #85 `split_frontmatter` 是第二份。`strip_narrative_body` 的 frontmatter 部分**归 #85**（先 #85 后本项），其余留原处待后续；**目标已核**：`text/cjk.py` 已有 `find_quote_spans`/`count_quote_pairs`/`dialogue_char_ratio`，本批不新建包、不动既有 cjk 函数；解开 `skill_utils/style_learning/compute_stats.py:13-19` 的倒依赖；
- `ALL_SKILLS`/`T1_SCAFFOLD_SKILLS`（:759-776）import 时扫目录改惰性函数（消除 import 对 checkout 布局的耦合 + CLI spawn 提速）；**r2.2 补消费者清单**：**10 处/7 文件**（`g0.py:413,606,715,720-721`、`g7.py:45` **与 :65**、`g_reconcile.py:76`、`sync_contracts.py:38`、`dispatch_helper.py:3026-3029`、**`g_dispatch.py:48`**），逐点换源；函数加 `functools.lru_cache`（G0/G7 会重复扫盘）。

### T5 · 调用缝说真话
- **r2.2 事实更正**：`check_chapter_title`（g4:322）、`check_hook_fulfillment`（g4:286）、`entity_in_text`（g4:66）**本来就是公共名**（无改名、无压制可摘）；真正要正名的只有 `_ending_archetype_of`→`ending_archetype_of`（audit_context_cache:124，摘 pyright 压制）；同主题另补 **gates→gates 的 `_declared_history`**（chapter_drafting:488/:1142 两处 `reportPrivateUsage`）——本批或明示不在范围；
- `g4_cross_chapter` **文档化为非注册表门**（docs/framework/gates.md 增行：pipeline 直调、需跨章上下文装配，注册表形态装不下）；
- `verdict_fence.match_verdict_scoped` 已被两个 review checker 内部 import（review_arc_payoff:16 / review_resonance:33）——**不动**（同包内部协作，非跨包私用）。

### T6 · G0.12 真实现（现为假检查——亲验 :708-723 仅计数后无条件 PASS）
**r2.2 更正**：`build_checkers()` 在 `g4/generic.py:404`，**调用它必须 import g4**——与「G0 不 import g4」互斥；可证伪的声明面判据是 **`set(G4_CHECKER_SKILLS) == set(G4_CHECKER_KEYS)`**（两者都是 roster 声明，当前恰 30=30）且 `ALL_SKILLS` 每项解析到专用或 generic fallback（当前 74 技能）；G0 **不 import g4 模块**（避免冷启动 + 把「环境检查」变成「门实现检查」），只做集合对账；`build_checkers()` 的导入完整性交给 `tests/unit/gates/g4/test_build_checkers.py`。仍保留「注入无 checker 假技能→红」的红测。

## 2. 验收

1. `g4_chapter_drafting` 主函数 <300 行；plan 每章恰读 1 次（测试断言 read 计数）；
2. 章号内联正则归零（T2 判据）；
3. RoundPaths 前导 ValueError 同串归一（11→1；**r2.2**：`pacing_design.py:33` 的 `if not project_dir` 启发式须保留/参数化；`tests/unit/gates/test_g4_signatures.py:42` 以 `match="round_dir or project_dir required"` 钉串，收敛不得改串）；
4. `gates/shared.py` 无写函数、无 import 时 FS 扫描（import 副作用测试）；**`text/` 仅新增 1 个符号**（segment_sentences；strip_narrative_body 的 frontmatter 面归 #85）；
5. **skill_utils 对 `segment_sentences` 的 import 归零**（r2.2 收窄：`compute_stats.py:14-20` 还 import META_BLOCK_RE/QUOTE_PAIR/count_similes/strip_narrative_body，本 spec 只搬 segment_sentences，其余符号留待 #85/后续——原「文本原语 import 归零」不可达）；
6. G0.12 对注入的无 checker 假技能红（红测）；
7. `just check` exit 0。

## 3. 顺序

**顺序（r2.2）**：T4 与 #85 有真实边界重叠（`strip_narrative_body` 的 frontmatter 剥离）——**#85 先落**，本 spec 的 T4 只做 `segment_sentences`；T1 与 #87 T3 不同文件，**T1/T3 先后皆可**（r2.2 修正 typo「t」；建议先于 #87，减并行冲突面）。
