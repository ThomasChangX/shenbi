# Spec #116 · 门禁判别力（gate-discriminative-power）：真语料回放仪表、恒真检查登记、表面门标定

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit · B 异模型元审）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟠 P1
**补充证据（2026-11-15 Goodhart 执行）**：`reports/2026-11-15-goodhart-escape-execution.md` + `reports/2026-11-15-goodhart-r2-single-chapter.md`——r1 六臂 98 派发：5/6 臂先死于 bundle/word_band/scene_domain，8 个已产出章 G4.cd **0 通过**；A/B 两臂均出现 POST 自检字数虚报（A2 3300→1869；B1 4 章全部虚报；B2 3232→2242）。r2 单章重跑 18/18 章成稿：A 1/9、B 2/9 通过（Fisher p=1.0），`voice_density` 仍主导失败（A 8/9、B 7/9）；B 的边际改善被 `prop_handoff` 3 次/`word_count` 1 次抵消。写手侧证据补充本件判别力结论：真拦住博弈的是 B 类结构门（bundle/字数/场景域）+ `voice_density` 词表阈值，A 类散文门仍恒真；`voice_density` 在 r2 两臂 15/18 章失败，是本件 T3 标定提案的最高优先项。
**动机证据**：本批真 G4 回放（`g4_chapter_drafting`，`novel-xinghuo-vol1/chapters/chapter-1..50.md`，`project_dir=novel-xinghuo-vol1`；脚本附录 A）——**10 项检查 50/50 PASS 且零 WARN/FAIL**：`G4.cd.chapter_end_hook` / `G4.cd.protagonist_presence` / `G4.cd.scene_concreteness` / `G4.cd.scene_count` / `G4.cd.surge` / `G4.fatigue` / `G4.meta` / `G4.transition` / `G4.word_count` / `G4.pre_check`；另 `G4.post_check` 48/48、`G4.cd.scene_hook_match` 37/37、`G4.cd.golden_slot` 47 PASS+3 WARN 亦零 FAIL；真开火的只有**对账类**：`G4.cd.voice_density` 14 次 must_fix、`G4.cd.prop_handoff` 11 次、`cd.balance_value_drift` 7 次（另有 counter/post_quote/post_wordcount WARN 行）。触发归因：hook 门 50/50 过，其中 **15/50（30%）只靠单字张力词**（窗内无？、无账目行、无多字标记），窗口单字命中 `还`=38 章、`账`=38 章——与主角声口「账房腔：用记账动词描述一切」（`novel-xinghuo-vol1/characters/protagonist.md` voice_profile）**同词表**；`G4.cd.protagonist_presence` 用 `sum(text.count(name) for name in protagonist_names)`（`src/shenbi/gates/g4/chapter_drafting.py:475`）+ `_load_protagonist_names` 追加 `他`（`:514`），实弹名字表=`['那罕','那罕','他']`（frontmatter 正则与 YAML 双取致重复——`:493`/`:507` 双 append），50 章总数中位 **93**、最小 64，阈值 3，**仅 `他` 一项在 50/50 章 ≥3**；`G4.transition` 在 narrative 上 `count_transition_words`（`src/shenbi/gates/shared.py:919-934`），实弹中位 **0**，阈值 `max(5, wc//1000)`=5，50/50 过（未减化合物「必然/果然/偶然…」全语料总命中仅 3——**化合物假说在本语料不成立**，记负结果）；`G4.cd.simile_band` 28/50（56%）落在 [2,4] 带外但只 WARN（`chapter_drafting.py:1289-1313`（阶段 2 刷新：#93 T6 插入 `_fatigue_word_list` 漂移 +24 行），count_similes 吃 `ctx.content` 原文含 PRE/POST）；`ending_archetype_of` 47/50 返回 None（`:519-536`）——结尾多样性哨兵几乎无数据；触发清单显示**真开火的绝大多数是对账类**（`voice_density`/`prop_handoff`/`balance`/`counter`/`quote_verbatim`/`wordcount` 精度），散文形态门零点火（唯一例外 `G4.post_check` 2 次）——判别力集中在 B 类对账面，A 类散文门在唯一语料上是常数；红测存在（`tests/unit/gates/g4/test_chapter_drafting.py`）证明门**能**失败，但本项目无「生产语料 firing-rate 基线」，无法区分「floor 从未需要」与「floor 已坏」；#108 的变异器目录尚未实现（`src/shenbi/pipeline/canary/mutators.py` 不存在，P2 Design），其期望面已列 `cd.chapter_end_hook`——本件 T4 复用其变异器做确定性门召回，不另造；名册单源 `src/shenbi/gates/shared.py:782`（`G4_CHECKER_KEYS` 30）与 `:823`（`GENERIC_ONLY_ROSTER` 44）。

**触及的不变量维度**：无（门禁判别力是测量/标定面；不改任何载体/声明/门检 id；T3 提案经用户裁定后才动 check 语义）

---

## 0. 根因

**门禁以「形态可过」为设计目标，缺少「判别力」验收面。** 阈值与词表按单本项目逐次实弹调参，且调参方向被「不过就放宽」主导（`G4.transition` 从 1/3000 放宽到 1/1000 的历史注记、hook 窗口从 5 开到 8 的 escalation 链）；没有任何机制记录「这个门在真语料上的点火率/触发归因/期望带」，也没有「恒真 = 可疑」的登记义务。于是 A 类散文门（hook/protagonist/transition/scene_concreteness/surge/fatigue/meta/word_count）在唯一语料上成为恒真函数，质量判别全部外包给 C 类 LLM 判官（其信度见 #110，其证据可验证性见 #117）。**红测证明「能失败」≠ 生产证明「会失败」**——本件补的是后者。

**用户裁定（2026-11-15）**：本件只建仪表与提案，**不改任何门行为**——T3 的每项标定提案交用户逐项裁定；不考虑在飞项目（vol1 只回放报告，不重跑不改产物）；零付费派发（确定性回放零成本）。

**备选案已评估并否决**：「直接删恒真门」——它们可能是从未需要的 safety floor，删除丢失兜底；须先分类（floor-untested / decorative / discriminating / retired）再裁；「并入 #108 canary」——#108 测 LLM 审计召回（需付费派发），确定性门回放零成本且对象不同（门 vs 判官），合并稀释两者判据；「并入 #93 threshold-authority」——#93 做阈值单源/allowlist/strict，不做判别力测量，两者无重叠。

## 1. 任务分解

### T1 · `just gate-power <dir>` 离线判别力回放
- 对指定项目章集回放全部确定性 G4（及可离线复用的 G2/G6 散文检查），输出 per-check：PASS/WARN/FAIL/SKIP 计数、firing rate、**触发归因**（命中的 arm/词；单字 vs 多字 vs 代词 vs 对账；是否化合物）；
- 历史章回放对**当前 truth** 会伪 FAIL（balance/counter/prop handoff 依赖现值）——必须分口径：`--state-free-only`（不读 truth oracle，只测散文门）与 `--full`（标注「truth 漂移伪 FAIL」）；
- 纯确定性、零 LLM、零写盘（报告落 `reports/`）。

**判据**：对本项目 50 章回放，输出与附录 A 表一致（10 项 50/50、voice_density 14、prop_handoff 11、simile 28 WARN、ending None 47）；`--state-free-only` 下 FAIL 计数=附录 A 的散文门口径；报告可重放（同输入同输出）。

### T2 · 恒真检查登记（vacuity registry）
- `docs/framework/gate-power-baseline.md`：每 hard gate 一行——期望点火带 / 分类（`floor-untested` | `decorative` | `discriminating` | `retired`）/ 最近回放数 / 触发归因；
- `just check` 哨兵：某 check 在 ≥50 章回放中 0 点火且未分类 → WARN（不 FAIL、不阻断既有流）；分类为 `floor-untested` 的必须附「负例证明」链接（T4）；
- 与 `docs/framework/invariants.md` 门检列做 check-id 对账（复用 #89/#90 单源机制，不新造名册）。

**判据**：baseline 文档存在且覆盖全部 hard gate；哨兵红测（新增未分类 0 点火 check → WARN；分类后消失）；`just check` 全绿。

### T3 · 标定提案（只提案，不改行为）
逐项含「现状/提案/红测/回滚」四栏，交用户裁定：
- **hook**：要求多字/结构臂，或强制张力词表与本项目母题词表（账/欠/还/藏）不相交——现词表与主角账房腔同表；
- **protagonist**：去重复名 append（`:493`/`:507`）、名字单独下限或 POV 声明，阈值按真语料分布重标定（现中位 93 vs 阈值 3）；
- **transition**：retire 或重标定（现中位 0 vs 阈值 5）；化合物扩展与否按负结果（全语料 3 次）判定；
- **scene_concreteness / surge / fatigue / meta**：逐项分类 + 真语料负例；
- **simile**：56% WARN 的劝谏面——路由或降为报告行（alarm fatigue 风险）；
- **ending archetype**：扩分类器或退役 `ending_diversity` 哨兵（47/50 None = 盲哨兵）。

**判据**：提案文档六项齐全；每项有现状数字（本件动机证据）与回滚条件；无代码行为改动（`git diff` 仅 docs/tools/tests）。

### T4 · 真语料负例（证明门在真实散文上能失败）
- 对保留的 hard gate，用真实章做**确定性变异**（删除/替换属性）构造负例，证明门能失败；变异器优先复用 #108 `pipeline/canary/mutators.py`（`cd.chapter_end_hook` 已在期望面），#108 未落地时用最小本地变异器；
- fixture 存 `tests/fixtures/`（G0.9：真实产物 + 确定性变异，非手工 mock；变异副本只进测试目录，不得写项目）。

**判据**：每个保留 hard gate 至少 1 条「真实章变异→FAIL」红测；变异前后文件 mtime 不变（项目只读）；G0.9 provenance 头合规。

## 2. 验收
1. T1-T4 判据全绿；
2. `just gate-power` 对 vol1 50 章回放可复现；报告含 state-free 与 full 两口径；
3. 恒真登记覆盖全部 hard gate，未分类 0 点火 check 触发 WARN；
4. 标定提案六项 + 回滚条件交用户裁定（本件不执行）；
5. 变异负例红测：hook/protagonist/transition 至少三项在真实章上可被门捕获（或证明不可捕获 → 进 `decorative` 分类）。

## 3. 风险
- 回放历史章对当前 truth 伪 FAIL（状态漂移）→ 双口径 + 报告标注，禁止用 full 口径做判别力结论；
- **共享文件面**：`src/shenbi/gates/g4/chapter_drafting.py` 与 `shared.py` 为 #116 独占用（无在飞 spec 冲突；#88/#89 已完结）；`justfile 配方面` 与 #92/#95/#116/#117 共享——顺序 **#92 → #93 → #116 → #117**（#92 在飞，先落子配方拆分）；`tests/fixtures/` 与 #108 变异器同面——**#108 落地后 T4 换装**（此前用本地最小变异器）；
- 判别力 ≠ 正确性：0 点火可能是 floor 有效（从未需要），也可能是门坏——分类标签必须人工裁定，不得由仪表自动断言；
- 单书语料（B5 边界）：baseline 只对 vol1 成立；跨书回放作为 T1 的 `--dir` 泛化验收，不在本件裁阈值。

## 附录 A · 50 章回放表（2026-11-15，state-free 检查）
| check | PASS | WARN | FAIL | 归因/备注 |
|---|---:|---:|---:|---|
| G4.cd.chapter_end_hook | 50 | 0 | 0 | 15/50 仅单字张力词；`还`=38 章、`账`=38 章 |
| G4.cd.protagonist_presence | 50 | 0 | 0 | 名表中位 93 vs 阈值 3；`他` 单独 50/50 ≥3；名字表重复 |
| G4.cd.scene_concreteness | 50 | 0 | 0 | 视觉动词窗恒真 |
| G4.cd.scene_count | 50 | 0 | 0 | — |
| G4.cd.surge | 50 | 0 | 0 | 长句配额恒真 |
| G4.fatigue | 50 | 0 | 0 | — |
| G4.meta | 50 | 0 | 0 | — |
| G4.transition | 50 | 0 | 0 | 中位 0 vs 阈值 5；化合物总命中 3 |
| G4.word_count | 50 | 0 | 0 | — |
| G4.pre_check | 50 | 0 | 0 | — |
| G4.post_check | 48 | 0 | 0 | 2 章无 POST |
| G4.cd.scene_hook_match | 37 | 0 | 0 | 13 章无场景钩声明 |
| G4.cd.golden_slot | 47 | 3 | 0 | — |
| G4.cd.simile_band | 22 | 28 | 0 | 56% 带外，仅 WARN |
| G4.cd.voice_density | 36 | 0 | 14 | must_fix（真开火） |
| G4.cd.prop_handoff | — | — | 11 | must_fix（真开火） |
| cd.balance_value_drift | 0 | 12 | 7 | must_fix/WARN（部分 truth 漂移） |
| ending_archetype_of | — | — | — | 47/50 None（哨兵盲） |

**命令**：`uv run python /tmp/shenbi_b_audit/run_g4_census.py`（脚本全文见会话记录；只读 `g4_chapter_drafting` 对绝对路径逐章调用，`project_dir=novel-xinghuo-vol1`）。
