# Spec #89 · 门禁内部性修复（gates-internal-repair）：CheckContext 一次装载、四窄助手、shared.py 出鞘、调用缝说真话

**日期**：2026-11-01（r2 修订 2026-11-02：**删除对 #85 的伪依赖**——CHAPTER_NUM_RE 已存在；RoundPaths 落点修正 paths.py；text 合流目标核清）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #4/#17/#18 卡；协调者亲验：`g4_chapter_drafting` 主函数恰 772 行；`CHAPTER_NUM_RE` 在 gates/shared.py:182 **已存在**（gates/g4 与 g6 零使用）；`class RoundPaths` 在 **src/shenbi/paths.py:55**（非 gates/shared）；`_ending_archetype_of` 被 audit_context_cache.py:124 跨包 import（带 pyright 压制）；`check_chapter_title`/`check_hook_fulfillment` 被 chapter_loop.py:3503/3511 惰性 import

**触及的不变量维度**：无（门禁内部结构；判定语义不变——characterization 先行）

---

## 0. 根因

ADR 0008 strangler 分件完成但未剪枝：g4_chapter_drafting 单函数 772 行横跨 6 spec 的 ~20 项检查，逐检查重推导同一上下文（plan 同文件每章重读 5 次；章号内联正则 ×5-6）。`gates/shared.py` 923 行是单子算术楼：含写文件函数、import 时 FS 扫描、文本原语错置（skill_utils 因此倒依赖 gates）。33 checker 间 ~10-30% 脚手架拷贝。pipeline 直连门禁内部（`g4_cross_chapter` 根本不在 build_checkers 注册表——注册表对「哪些门存在」说谎）。

## 1. 任务分解（**抗过度工程裁决先行：不做 table-DSL**）

### T1 · CheckContext 一次装载（chapter_drafting）
循环顶构造 `CheckContext`（content / memo_text / chapter_no / project_root / props/counters/identity facts oracle），plan 读 1 次入 context；~20 检查从 context 取；主函数目标 <300 行，检查体拆为该文件已会写的具名函数（`_spec82_hook_rotation` 样板）。**characterization**：既有 10 个测试文件全绿不动。

### T2 · 章号单源采用（**无 #85 依赖**）
`CHAPTER_NUM_RE`（gates/shared.py:182）已存在，直接采用：g4 全域内联 `chapter-(\d+)`（chapter_drafting ×5-6、cross_chapter ×5、generic ×2、chapter_planning ×1+1、decisions_validator ×1）+ g6.py:87,421,431 → 换常量；chapter_planning 的 `-(\d+)-plan` 分歧形态（:763）统一。
**判据**：`grep -rn 'chapter-(\\(\\\\d+\\))\|chapter-(\\\\d+)' src/shenbi/gates/ | grep -v CHAPTER_NUM_RE` 零输出。

### T3 · 四窄助手（跨文件拷贝收敛，非框架）
- `chapter_no(path)`（封 T2 常量）；
- `load_facts_oracle(project_dir, dim)`（`load_facts + is not None and not is_empty` 三连 ×3 文件收敛——chapter_drafting:552-571/state_settling:787-795/chapter_planning:629-635/cross_chapter:888-920）；
- `degrade(check_id, reason)`（「degradation visible」WARN 惯用串 ×6 收敛）；
- `RoundPaths.require_roots()`（**落 src/shenbi/paths.py:55 的 RoundPaths**）——11 个 checker 的 7 行同体前导（含同串 ValueError）收进构造/类方法。

### T4 · shared.py 出鞘（不重排整体，只搬错置件）
- `write_gate_marker`/`marker_filename`（:701-726）迁 `gate_manifest.py`（record_gate_result 已在彼）；
- 文本原语迁 `shenbi/text/`：`segment_sentences`（shared:374）、`strip_narrative_body`（shared:337）——**目标已核**：`text/cjk.py` 已有 `find_quote_spans`/`count_quote_pairs`/`dialogue_char_ratio`，本批只搬这两个缺位者，**不新建包、不动既有 cjk 函数**（避免制造第二处重复）；解开 `skill_utils/style_learning/compute_stats.py:12-18` 的倒依赖；
- `ALL_SKILLS`/`T1_SCAFFOLD_SKILLS`（:759-776）import 时扫目录改惰性函数（消除 import 对 checkout 布局的耦合 + CLI spawn 提速）。

### T5 · 调用缝说真话
- 已亲验的 4 个被 pipeline import 的助手正名公共：`check_chapter_title`（chapter_loop:3503）、`check_hook_fulfillment`（:3511）、`entity_in_text`（:1476）、`_ending_archetype_of`→`ending_archetype_of`（audit_context_cache:124，摘 pyright 压制）；
- `g4_cross_chapter` **文档化为非注册表门**（docs/framework/gates.md 增行：pipeline 直调、需跨章上下文装配，注册表形态装不下）；
- `verdict_fence.match_verdict_scoped` 已被两个 review checker 内部 import（review_arc_payoff:16 / review_resonance:33）——**不动**（同包内部协作，非跨包私用）。

### T6 · G0.12 真实现（现为假检查——亲验 :708-723 仅计数后无条件 PASS）
调用 `build_checkers()` 对 ALL_SKILLS 解析，断言无 UNIMPLEMENTED（每轮一次）；无 checker 技能红。**备选**（若实测成本不可接受）：改诚实 SKIP（G3.1 模式：显式声明为何 SKIP）。

## 2. 验收

1. `g4_chapter_drafting` 主函数 <300 行；plan 每章恰读 1 次（测试断言 read 计数）；
2. 章号内联正则归零（T2 判据）；
3. RoundPaths 前导 ValueError 同串归一（11→1）；
4. `gates/shared.py` 无写函数、无 import 时 FS 扫描（import 副作用测试）；`text/` 仅新增两函数（diff 核对）；
5. skill_utils 对 `gates/shared` 文本原语 import 归零；
6. G0.12 对注入的无 checker 假技能红（红测）；
7. `just check` exit 0。

## 3. 顺序

T4 文本原语迁移与 #85 无符号冲突；T1 与 #87 T3 不同文件，t 先后皆可（建议先于 #87，减并行冲突面）。
