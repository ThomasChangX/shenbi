# Spec #122 · 修订回路闭合批（revision-loop-closure）：聚合审计把证据带到修订者＋修订者读面补齐＋修订 SKILL↔框架对账＋decisions 顶层键收编

**日期**：2026-11-24｜ **系列**：实现审计清偿批（expert-panel-implementation-audit · 2026-11-24 八席审计，协调者逐条亲验）｜ **状态**：Design（r1，2026-11-24）｜ **优先级**：🟠 P1
**动机证据**（HEAD `3311a0af`）：
- **证据断流**：`src/shenbi/pipeline/audit_aggregate.py:11-14`（模块自述「lossless: every ANCHORED severity-bearing finding unit」——只保「带锚定严重度标记的发现单元」）与 `:114`（`extract_finding_units`）。审稿契约要求的四要素证据（位置／原文引述／违反规则／严重度，`skills/shenbi-review-group-craft/SKILL.md:274` 一带）不在同一锚定行上就不进聚合：vol1 真实审计的四要素证据行 339 条 → 聚合文件保留 3 条（2026-11-24 脚本口径：原始 audits 与 aggregate 中「位置／原文引述／违反规则」行计数）。而修订者契约 reads 只有四项——`chapters/chapter-N.md`、`chapters/chapter-N-decisions.json`、`audits/chapter-N.aggregate.md`、`plans/chapter-N-plan.md`（字段 1／6／8）：没有 `genre-config.json`（AI 词表）、`style/style_profile.md`（文风目标）、`characters/*`（声口档案），也没有备忘 §3／§7；
- **振荡实录**（`pipeline-state.json` checkpoint_history 的升级裁决反馈）：ch43「约束丢持振荡：每轮只修上轮反馈项，已修项回退」；ch45「四派振荡归因=约束丢持：字数修好丢声口、修声口又塌字数」；
- **承诺只在文字里**：`skills/shenbi-chapter-revision/SKILL.md:71`（「最多重试 3 次 — 3次修订后仍未通过，回退到最佳版本」）、`:107-112`（回退流程）、`:163`（「verify_preservation 必须通过」）、`:165`（「超限触发 `run_escalation_check`」）vs `src/shenbi/pipeline/revision_router.py:69`（`MAX_AUTO_REVISIONS = 2`，超限走 `dispatch_escalation`——无回退、无择优）；`src/shenbi/skill_utils/revision_routing/preserve_check.py:24`（`verify_preservation`）与 `src/shenbi/orchestration/escalation_bridge.py:29`（`run_escalation_check`）全仓只有定义行、零调用方；`REVISION_FAILED`／`best_version`／`acceptance_criteria` 在 `src/` 零命中。死代码闸 `tools/lint_dead_code_allowlist.py` 基于 basedpyright 的未使用检查，不报公有名——于是「安全检查不执行、单测照样绿、覆盖率照样算」；
- **schema 判定相反**：修订 decisions 顶层 `mode`／`status`（`SKILL.md:186` 要求）→ `DecisionsDoc` 报 `extra_forbidden`（G2 判 FAIL），而 G4(chapter-revision) 判 PASS（2026-11-24 复跑两门同文件对照）；vol1 真实修订 sidecar 26 份中 14 份带顶层 `mode`／`status`；
- **分工**：#117 管「证据是否成立」（校验器）；本件管「证据是否到达修订者」（管道）与「修订技能的承诺是否有代码兑现」。

**触及的不变量维度**：叙事纪律（POV/声口）（弱关联——T2 让修订者读到声口档案与文风目标，防修订磨平声口，不改门检判据）；字量结构（弱关联——T3 守住修订不恶化，不改带值）

---

## 0. 根因

修订回路里三件防「修 A 坏 B」的东西都只写在技能文字里，没有一件落到框架：**证据到不了修订者**（聚合只保带锚定严重度的单元）、**参照数据到不了修订者**（契约 reads 缺声口／文风／词表）、**回退与保留校验没有代码**。升级裁决记录里的振荡是这三件缺失的合成结果：审稿产出四要素证据 → 聚合丢掉证据行 → 修订者只见「哪条规则违例」不见「原文是哪句、在哪」→ 凭计划与记忆改 → 改坏已过门的项 → 再审再修。

**用户裁定（待裁两项）**：
- (a) **修订上限口径**：SKILL「3 次后回退最佳版本」vs 框架「2 次后升级」。二选一——落代码实现回退（上限 3＋择优），或改 SKILL 文字为「2 次后升级」。本件缺省取后者（行为零变化），前者登记为备选；
- (b) **零引用检查的处置**：`verify_preservation`／`run_escalation_check` 接线或删除。本件缺省取「接线 `verify_preservation`（纯函数，已有单测）；删除 `run_escalation_check` 并把 SKILL 文字指向既有的 `dispatch_escalation`」，plan 期按接线成本复核。

**备选案已评估并否决**：
- 「修订者直接读全部原始审计」——原始审计体量大且互相矛盾，聚合层的存在理由就是去重与定序；正确修法是让聚合带证据；
- 「让 12 个审稿技能把证据写进锚定行」——改输出格式的代价与形态漂移风险见 #117 的评估；
- 「提高修订上限硬扛」——掩盖证据断流的根因。

## 1. 任务分解

### T1 · 聚合审计带证据
- `extract_finding_units` 的发现单元携带其所属证据块（同一 finding 的四要素行／表格行：位置、原文引述、违反规则），`render_aggregate` 原样输出；去重键仍按发现单元（证据块随单元去重）；
- 判据：红测——原始审计含「发现行＋其下四要素块」→ 聚合含四行；vol1 真实审计 fixture 回放：聚合中四要素证据行数 ≥ 原始的 90%（基线 3／339）；每发现的证据块设行数上限，超限截断并带披露行（防聚合膨胀）。

### T2 · 修订者读面补齐
- `shenbi-chapter-revision` 契约 reads 增：`genre-config.json`（字段级：疲劳词／禁用词）、出场角色声口档案（`characters/*` 的 voice_profile 行，确定性名匹配）、`style/style_profile.md`（与 drafting 相同的字段子集）、`plans/chapter-N-plan.md` 字段补 §3／§7；全部走字段级或窗口读，不整读；
- 判据：dry-run manifest 含新增读面且 mode=fields／extractor 命中；prompt 体量增量 ≤ +15%（dry-run 对比）；契约 lint 全过。

### T3 · 修订 SKILL↔框架对账
- 上限口径统一（按裁定 a）；`verify_preservation`／`run_escalation_check` 按裁定 b 接线或删除并改文；`src/shenbi/pipeline/transitions.py:76`（`transition_to_failed`——FAILED 相位的唯一写者、零调用）移交 #112 的不变量清单登记；
- 新增单源断言测试：SKILL 文字里的修订上限数字 == `MAX_AUTO_REVISIONS`；
- 死代码闸加「公有名零引用」面（`tools/lint_dead_code_allowlist.py`；与 #94 T1 同文件，顺序见风险）；
- 判据：`git grep` 证明被保留的「强制步骤」都有调用方；单源断言测试绿；lint 对三个零引用函数报红（接线／删除后转绿）。

### T4 · decisions 顶层 mode／status 收编
- `mode`／`status` 进 `shenbi-decisions-v1` schema（optional；`docs/framework/decisions-schema.md` ＋ `DecisionsDoc`），G2 与 G4 判定一致；
- 判据：两门对同一修订 sidecar 同判；存量 14 份 sidecar 无需迁移（optional 键）；`lint_decisions_sources` 三源一致。

## 2. 验收
1. T1–T4 判据全绿；
2. 实弹（随用户令，≥3 章含修订）：修订派发的 prompt 含证据块与声口／文风读面；「修 A 坏 B」型重派（修订后原先 PASS 的 check id 转 FAIL）计数落报告，与基线对照。

## 3. 风险
- **聚合膨胀** → 证据块行数上限＋披露行；
- **读面补齐改变修订派发行为** → dry-run 差分＋首个适用窗观察；
- **共享文件面**：`audit_aggregate.py` 与 #117 T3（消费三态）同文件——**本件先行**，#117 T1（发现级 parser）落地时吸收 T1 的块级保留并为单源（两份 spec 互登记）；`revision_router.py` 与 #115 T1（floor 语义拆分）同文件——re-anchor；revision SKILL 与 #96／#102（drafting／review-group-plan SKILL）不同文件，无冲突；`tools/lint_dead_code_allowlist.py` 与 #94 T1 同文件——先施工者加面，后者 re-anchor。
- **contract-upgrade 纪律**：T4 为 optional 键、T2 只改 reads——显式声明「无既有工件受影响」，不触发迁移义务。

## 4. 立项预答（价值门 ④⑤ 前置）

**④ 博弈路径清单**：
- 聚合带了证据但修订者 reads 没跟进 → T2 manifest 断言；
- 证据块超限被截，又回到断流 → 上限＋披露行，回放判据（≥90%）守门；
- SKILL 文字改了、框架常量又漂 → 单源断言测试；
- `mode`／`status` 收编后别的技能 sidecar 带同名键被放行 → 键语义按技能限定（plan 期定：非修订技能是否仍判 `extra_forbidden`）。

**⑤ 候选机制清单**（buy-before-build）：`extract_finding_units`（升格既有，覆盖证据携带）；drafting 已有的声口／`style_profile` 字段读（复用同一子集，覆盖 T2 读面的大半）；`verify_preservation`（既有纯函数，接线即用）；`DecisionsDoc`／schema 文档（升格）；#117 T1 的发现级 parser（尚未建——本件 T1 先做块级保留，#117 落地时收敛，不重复建设）。无新建机制。
