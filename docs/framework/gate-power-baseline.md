# G4 门判别力基线（恒真登记）· spec #116

> 登记分母 = `src/shenbi/gates/g4/chapter_drafting.py` 单文件 AST 单源（check 行
> dict id ∪ mf 首常量 id，经别名表回射 canonical）∪ 扫描不可见的显式补充面。
> **check-id 对账由 `tools/lint_gate_power_baseline.py` 执行**（进 `just lint`）：
> 行缺/多、分类值域外、非 discriminating 缺证据、registry↔AST 漂移均红；本表
> 与 `docs/framework/invariants.md` 分工——彼表管不变量维度覆盖，本表管判别力。

## 口径定义（附录 A 列锚，r2/M3；M3 用词统一——列值与 registry `_caliber()` 输出一致）

- **state-free**：不读 truth oracle 可机检（读 memo/plans 声明属此列）；
- **truth**（附录 A 原文作「truth 依赖」，列值统一取 registry `_caliber()` 形）：
  回放历史章对当前 truth 有伪 FAIL 面的对账类（handoff/balance/counter 族；
  hook_type_rotation 读 plans 历史亦入此列）。WARN-only 行（provenance_anchor）
  无伪 FAIL 面、伪 WARN 面如实——口径按「是否读 truth oracle」判，不按
  FAIL/WARN 判，仍入此列。

## 分类语义（值域五值，闭合）

| 值 | 语义 |
|---|---|
| `unclassified` | 尚未裁定（初始态；证据列允许填红测链接供裁定参考） |
| `floor-untested` | 裁定为「floor 有效但本语料从未触发下界」——0 点火可接受 |
| `decorative` | 裁定为装饰性/恒真——判别力缺失，须给整改或保留依据 |
| `discriminating` | 裁定为有判别力——真语料开火或红测可捕获 |
| `retired` | 已退役（连同年发射面移除的检查） |

**分类必须人工裁定**：判别力 ≠ 正确性——0 点火可能是 floor 有效（从未需要），
也可能是门已坏；仪表与 lint 均不得自动断言分类，lint 只强制登记在册与义务
可见（非 discriminating 行证据列非空）。

## 升格锚（M1）

baseline 回填日 = Task 5 实跑日 **2026-11-20**（原计划 2026-11-19，实跑晚一天，
按「实跑日＋30 天」校正锚）＋ 30 天（一个完整裁定周期，spec r2/I5「分类义务
清偿后」以日历日近似）→ **2026-12-20**。该日后仍 `unclassified` 且最近回放数为
「0 点火」的行由 lint 升格为红（此前仅 stderr WARN）。校正记录见 task-5-report
（`tools/lint_gate_power_baseline.py` `ESCALATION_DATE` 同步）。

## 登记表（32 行；**分类裁定记录 2026-11-20**：用户对 spec #116 七项提案＋对账类逐项裁定「全部同意」——29 行已分类（12 discriminating＋17 floor-untested），3 残行已分类（spec #118 T8：payoff_density 变异红测＋quote_type/provenance_anchor 既有测试证据链，r2/I-7 收窄）。**2026-11-20 spec #118 落地后权威回放=reports/2026-11-22-gate-power-vol1-post119.md**（七门裁定执行＋content_uniqueness 死门修复；两 FINDING 已回裁 2026-11-21：protagonist 零动作＝臂即修复／uniqueness 纯形池过滤→spec #119）。**2026-11-22 spec #119 落地后权威回放=reports/2026-11-22-gate-power-vol1-post119.md（uniqueness 纯形白名单池 is_pure_chapter 单源——重放 FAIL 32→0＝聋门修复，audit-T8 预证兑现）**裁定动作（阈值/词表/结构改动）由落地批 spec #118 执行，本表只记分类与依据）

| check | 口径 | 期望点火带 | 分类 | 证据 | 最近回放数 | 归因 |
|---|---|---|---|---|---|---|
| `G4.pre_check` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_pre_removed_fails_pre_check_gate` | 50 章 @ 2026-11-22（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 50 PASS（附录 A 同；裁定 2026-11-20） |
| `G4.post_check` | state-free | — | discriminating | — | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 48 PASS＋2 FAIL（2 章无 POST 块真开火；附录 A 同） |
| `G4.transition` | state-free | FAIL=密度>1.0/千字（重放实测 0） | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_transition_flooded_real_chapter_fails_transition_gate`＋`test_transition_cap_single_source.py`（常量钉＋口径区分红测） | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 原 50 PASS（中位 0 vs 绝对阈 5）；**裁定 B 已执行（spec #118 T4）**：per-1000 封顶 1.0（vol1 定标注释在常量处：median 0/P95≈0.36/max 0.809→1.0=max·1.24）——重放 50 PASS 零新 FAIL（带内）；flooded 负例 ≫1 仍 FAIL；化合物负结果不扩 |
| `G4.fatigue` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_fatigue_flooded_fails_fatigue_gate` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 50 PASS（附录 A 同；裁定 2026-11-20 floor-untested） |
| `G4.meta` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_meta_injected_fails_meta_gate` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 50 PASS（附录 A 同；裁定 2026-11-20 floor-untested——闭集词零命中＝floor 有效） |
| `G4.word_count` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_word_count_truncated_fails_word_count_gate` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 50 PASS（附录 A 同；Goodhart r1 虚报被 word_band 重算拦截的对照面在他路径；裁定 2026-11-20） |
| `G4.cd.scene_count` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_scene_markers_removed_fails_scene_count_gate` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 50 PASS（附录 A 同；裁定 2026-11-20） |
| `G4.cd.scene_concreteness` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_scene_visuals_stripped_fails_concreteness_gate` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 50 PASS（视觉动词窗恒真，附录 A 同；裁定 2026-11-20 floor-untested） |
| `G4.cd.scene_hook_match` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_hookdecl_mismatched_fails_scene_hook_match_gate` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 37 PASS＋13 章无场景钩声明（无行发射；裁定 2026-11-20） |
| `G4.cd.chapter_end_hook` | state-free | WARN=单字-only 章数（重放实测 15）；FAIL=全灭（红测面） | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_hook_killed_real_chapter_fails_hook_gate`＋`test_hook_single_char_only_warns_not_fails`（三态）＋`TestHookMirrorGateEquivalence`×2（镜像等价钉） | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 原 50 PASS（15 单字-only）；**裁定 A 已执行（spec #118 T2）**：三态化后 35 PASS＋15 WARN＋0 FAIL（15 单字章转 WARN 与镜像归因数一致）；镜像 gate_class 同名映射＋等价钉执法 |
| `G4.cd.protagonist_presence` | state-free | FAIL=名字缺席章数（重放实测 4） | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_protagonist_vanished_real_chapter_fails_presence_gate`＋`test_protagonist_roster_no_duplicate_append`＋`test_protagonist_name_absent_fails_presence_gate` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 原 50 PASS；**裁定 A+B 已执行（spec #118 T3）**：roster 去重（YAML 单源优先＋regex 回退）＋名字下限臂 → 46 PASS＋4 FAIL；**FINDING 回裁已落（2026-11-21 用户裁定：专家团四席推荐·零动作＝臂即修复）**：ch17/18/35/44 四章 raw 主角名 0 次＋代词 71-91 次＝生成器行为 finding 真阳性——臂原样保留即生产纠正机制（后续生成遇缺席 FAIL→重派反馈自纠），四章留红 firing 0.08＝诚实新常态；不修文不放宽；C 重标定推迟跨书（B5）；镜像中位/最小不变 |
| `G4.cd.surge` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_surge_killed_warns_surge_quota_gap` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 50 PASS（长句配额恒真，附录 A 同；裁定 2026-11-20 floor-untested） |
| `G4.cd.simile_band` | state-free | WARN 通道 0 行（重放实测 0） | discriminating | `tests/unit/gates/g4/test_gate_power_negatives.py::test_simile_flooded_warns_pileup_side`（改钉：报告行 s=PASS＋载荷）＋`test_chapter_drafting.py::test_cd_simile_band_three_states_and_edges`（改钉：带外=报告行） | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 原 22 PASS＋28 WARN；**裁定 C+A 已执行（spec #118 T5）**：带外路由报告行 → 50 PASS/0 WARN（28 归零转报告行）——**audit-T6/I-1 实证：归零 100% 来自路由 A，C 为计量空转**（count_similes 内部已剥，M7 2.02=2.02；call-site 钉口径为防御性）；discriminating 依据自「WARN 开火」迁移为「红测可捕获（改钉后）」（r2/M-3）；B 带重设可径用现有重放数据评估（换装前后数字相同） |
| `G4.cd.voice_density` | state-free | FAIL=absent 章数（重放实测 1）；WARN=密度带外章数（实测 13） | discriminating | `tests/unit/gates/g4/test_gate_power_negatives.py::test_voice_stripped_fails_voice_density_gate`（0<1 FAIL 面）＋`test_voice_density_two_level_three_states`（三态）＋`test_voice_old_key_maps_to_density_arm`（旧键→密度臂映射钉） | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 原 36 PASS＋14 FAIL（**下行引用报告=拆分前快照**）；**裁定 B 已执行（spec #118 T1）**：两级拆分后 36 PASS＋13 WARN＋1 FAIL（hard 臂=在场 ≥1——absent=1 章与实现首日离线重算逐位吻合，task-2 重放数字在 workspace replay-T2.md；权威终版重跑报告落 Task 8 post118）；密度臂 13 WARN 劝谏面；genre-config 旧键映射密度臂（vol1 活覆盖兼容）＋presence_min∈[1,5] |
| `G4.cd.golden_slot` | state-free | — | discriminating | — | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 47 PASS＋3 WARN（附录 A 同；WARN 开火故 discriminating，裁定 2026-11-20） |
| `G4.cd.content_uniqueness` | state-free | FAIL=真实跨章重复（#119 过滤落地后现语料预期 0） | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_content_duplicated_fails_content_overlap_gate`＋`test_content_uniqueness_skip_rows_explicit`（SKIP 双分支） | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | **裁定二 P1 修已执行（spec #118 T7）**：目录对齐 rd/chapters＋显式 SKIP＋git 考古定案「从未活过」（P-1.E PR-19 出生即死路径）；**史上首份真实点火：18 PASS/32 FAIL（firing 0.64）——FINDING 回裁已落（2026-11-21 用户裁定：批准纯章形池过滤→spec #119 T1）**：audit-T8 独立重算 32/32 FAIL 均对自身 pre-rev、纯池重跑 0/50（自稿污染 100%、vol1 零真实跨章重复）；修法=纯形白名单池（测量面=执法面同谓词单源，40% 阈不动——测量效度修复非放宽）；**spec #119 T1 已执行**：is_pure_chapter 单源落地（gates/shared）——重放 50 PASS/0 FAIL（firing 0.00＝纯池零跨章重复） |
| `G4.cd.quote_verbatim` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_quote_verbatim_full_pipeline_fails_on_nonverbatim_anchor` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 回放 0 行发射（『』锚定引句对章尾实拍比对面未触发；裁定 2026-11-20） |
| `G4.cd.payoff_density` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_payoff_stripped_warns_payoff_density` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 回放 0 行发射（v3 近窗无轴登记章为 0——WARN-only 臂；**spec #118 T8 变异红测已建**）；裁定 2026-11-20 floor-untested |
| `G4.cd.quote_type` | state-free | — | floor-untested | `tests/unit/gates/g4/test_spec76_voice_quote.py::test_g4cd_quote_type_three_point_sync` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 回放 0 行发射（引号型检查行，0 观测）；既有行为红测（真实 g4 管线三场景 must_fix 点火）为分类证据——spec #118 T8 r2/I-7 裁定依据：不为 M-1 形态同源重复建测；裁定 2026-11-20 floor-untested |
| `G4.cd.micro_hook_run` | state-free | — | discriminating | — | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 1 FAIL（mf 臂；v3+ plans 前置物章开火——真开火，裁定 2026-11-20） |
| `cd.post_quote_verbatim` | state-free | — | discriminating | `tests/unit/gates/g4/test_gate_power_negatives.py::test_post_quote_broken_fails_post_quote_verbatim_gate` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 12 WARN（附录 A「post_quote WARN 行」同源；WARN 开火故 discriminating，裁定 2026-11-20） |
| `cd.post_transition_cross` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_post_transition_lied_fails_post_transition_cross_gate` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 回放 0 行发射（POST 转折交叉面未触发；裁定 2026-11-20） |
| `cd.post_wordcount_precision` | state-free | — | discriminating | `tests/unit/gates/g4/test_gate_power_negatives.py::test_post_wordcount_lied_warns_precision` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 16 WARN（附录 A「post_wordcount WARN 行」同源；Goodhart r1 POST 虚报 6 章次同类病灶；WARN 开火故 discriminating，裁定 2026-11-20） |
| `G4.cd.ending_diversity` | state-free | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_ending_repeated_helper_three_ledger_closers`＋`test_ending_four_new_forms_classified`（四形态各 ≥1 真章 fixture） | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 原回放 0 行发射；**裁定 A 已执行（spec #118 T6）**——扩表后哨兵**首开火 1 WARN**（ch45/46/47 三连「落笔收束」=真阳性，audit-T7 核）：+4 archetype（未答问句 4/未答回避 10/落笔收束 10/景物余韵 7——vol1 47 None 采样归纳，来源章号在分类器注释）→ None 率 47/50→**19/50=38%**＜50% 停手线（重放实测权威数——离线预估 16 为筛选近似；无 retire 提案）；哨兵判别力已活化（Task 8 终版复核分类——表约「WARN 开火→discriminating」候选） |
| `cd.prop_handoff` | truth | — | discriminating | — | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 9 章 FAIL（mf 11 次，2 章×2 次——附录 A 记 11 次同源；含 truth 漂移成分；真开火，裁定 2026-11-20） |
| `cd.balance_value_drift` | truth | — | discriminating | — | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 12 WARN＋7 FAIL（附录 A 同数；部分 truth 漂移；真开火，裁定 2026-11-20） |
| `cd.counter` | truth | — | discriminating | — | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 33 WARN（附录 A「counter WARN 行」同源；WARN 开火，裁定 2026-11-20） |
| `cd.counter.plan_conflict` | truth | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_counter_reconciliation_helper_flags_plan_prose_conflict` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 回放 0 行发射（family helper 红测为据；裁定 2026-11-20） |
| `cd.counter.base_mismatch` | truth | — | discriminating | — | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 1 FAIL（真开火，裁定 2026-11-20） |
| `cd.counter.prose_mismatch` | truth | — | floor-untested | `tests/unit/gates/g4/test_gate_power_negatives.py::test_counter_reconciliation_helper_flags_plan_prose_conflict` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 回放 0 行发射（family helper 红测为据；裁定 2026-11-20） |
| `G4.cd.hook_type_rotation` | truth | — | discriminating | `tests/unit/gates/g4/test_gate_power_negatives.py::test_hook_type_rotation_full_pipeline_fails_on_same_type` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态） | 1 FAIL（读 pipeline-state 声明历史；真开火，裁定 2026-11-20） |
| `cd.provenance_anchor` | truth | — | floor-untested | `tests/unit/gates/g4/test_spec83_provenance_anchor.py::test_provenance_mismatch_warns_and_match_green` | 50 章 @ 2026-11-20（reports/2026-11-22-gate-power-vol1-post119.md＝#119 后权威态）0 点火 | 回放 0 行发射（WARN-only 来历锚：50 章无违例；I-1 归位行，见脚注）；既有 helper 级红测（直调真实 helper WARN 点火）为分类证据——spec #118 T8 r2/I-7 同；裁定 2026-11-20 floor-untested |

脚注：

- 附录外行 `G4.cd.quote_type`/`G4.cd.micro_hook_run` 为扫描侧真实 in-scope 检查
  （NB4）：micro_hook_run 需 memo_v3 前置物（v3 前置物缺席章记 SKIP 面，本语料
  1 章开火）；quote_type 为引号型检查行，回放面 0 观测。
- `cd.balance_value_drift.bundle` 不占行：唯一发射点在 settle 面
  （`src/shenbi/gates/g4/state_settling.py:305` 束级升格），非本章门回放分母；
  其 mf 串回射父行 `cd.balance_value_drift`（Task 4 裁定，详见 task report）。
- **I-1 归位脚注（Task 5 承批）**：`cd.provenance_anchor`（spec #83 T6 来历锚，
  WARN-only 人工裁决面）为 `chapter_drafting.py:895` 裸形 check 行——dict id 无
  `G4.` 前缀且非 f-string，双扫描正则均不可见（Task 4 known limitation），经
  `EXPLICIT_SUPPLEMENT` 扩一项归位；口径裁定=读 `truth/prop_registry.md`
  （truth oracle）→ `TRUTH_DEPENDENT_IDS`＋本表行（WARN-only 无伪 FAIL 面、
  伪 WARN 面如实——口径按「是否读 truth oracle」判）。扩后 registry 32 行配平
  （`tests/unit/tools/test_lint_gate_power_baseline.py::
  test_provenance_anchor_registered_truth_dependent_32_rows` 钉住）。
- hook/protagonist/transition 三行证据列已填 spec #116 T4 红测（真实章变异→门
  FAIL）；批C/D/E/F 红测覆盖行除批E helper 级 truth 族三行（prop_handoff/counter/
  balance_value_drift——构造性输入红测，行证据仍 `—` 待人工裁定）外证据列已
  **全部实填**（终审 fix 补 voice_density；fix r1 M-2 补齐 scene_hook/golden/
  surge/simile/content_overlap 五行；另有 quote_verbatim/post 族三行/ending/
  hook_type_rotation）——统一 `tests/unit/gates/g4/test_gate_power_negatives.py::
  <测试名>` 形态引用（M-1 裁定：不另造 t4_evidence 列）；其余行证据列 `—`
  （unclassified 允许），回放数据已落表，进入人工裁定。
- 回放计数口径：报告行 FAIL/WARN 为**章数**（同章同 id 去重）；附录 A 的
  「11 次」为 mf 原始次数——`cd.prop_handoff` 11 次 mf 分布于 9 章，两口径
  同源不同粒度（task-5-report 对账）。
