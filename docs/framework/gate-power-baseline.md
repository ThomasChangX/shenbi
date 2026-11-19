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

## 登记表（32 行；分类全 `unclassified`——回放数 2026-11-20 回填，分类待人工裁定）

| check | 口径 | 期望点火带 | 分类 | 证据 | 最近回放数 | 归因 |
|---|---|---|---|---|---|---|
| `G4.pre_check` | state-free | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 50 PASS（附录 A 同） |
| `G4.post_check` | state-free | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 48 PASS＋2 FAIL（2 章无 POST 块，附录 A 同） |
| `G4.transition` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_transition_flooded_real_chapter_fails_transition_gate` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 50 PASS；narrative 计数中位 0 vs 阈值 max(5, wc//1000)=5；化合物全语料 3 次（负结果） |
| `G4.fatigue` | state-free | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 50 PASS（附录 A 同） |
| `G4.meta` | state-free | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 50 PASS（附录 A 同） |
| `G4.word_count` | state-free | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 50 PASS（附录 A 同；Goodhart r1 虚报被 word_band 重算拦截的对照面在他路径） |
| `G4.cd.scene_count` | state-free | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 50 PASS（附录 A 同） |
| `G4.cd.scene_concreteness` | state-free | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 50 PASS（视觉动词窗恒真，附录 A 同） |
| `G4.cd.scene_hook_match` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_hookdecl_mismatched_fails_scene_hook_match_gate` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 37 PASS＋13 章无场景钩声明（无行发射） |
| `G4.cd.chapter_end_hook` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_hook_killed_real_chapter_fails_hook_gate` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 50 PASS；15/50 仅单字张力词命中，`还`=38 章、`账`=38 章（与账房腔同词表） |
| `G4.cd.protagonist_presence` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_protagonist_vanished_real_chapter_fails_presence_gate` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 50 PASS；出现总数中位 76（再推导名单 那罕＋他）vs 阈值 3 |
| `G4.cd.surge` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_surge_killed_warns_surge_quota_gap` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 50 PASS（长句配额恒真，附录 A 同） |
| `G4.cd.simile_band` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_simile_flooded_warns_pileup_side` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 22 PASS＋28 WARN（56% 带外仅 WARN；raw/narrative per_1000 均 2.02） |
| `G4.cd.voice_density` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_voice_stripped_fails_voice_density_gate` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 36 PASS＋14 FAIL（must_fix；附录 A 同数，Goodhart r2 15/18 同门主导失败） |
| `G4.cd.golden_slot` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_golden_emptied_warns_golden_slot` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 47 PASS＋3 WARN（附录 A 同） |
| `G4.cd.content_uniqueness` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_content_duplicated_fails_content_overlap_gate` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 回放 0 行发射：比对目录 `rd/project-output/chapters` 在真实项目布局缺席→检查静默不跑（发射面条件化，判别力盲区供裁定） |
| `G4.cd.quote_verbatim` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_quote_verbatim_full_pipeline_fails_on_nonverbatim_anchor` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 回放 0 行发射（『』锚定引句对章尾实拍比对面未触发） |
| `G4.cd.payoff_density` | state-free | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 回放 0 行发射（memo_v3 门内激活臂，本语料 0 观测） |
| `G4.cd.quote_type` | state-free | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 回放 0 行发射（引号型检查行，0 观测） |
| `G4.cd.micro_hook_run` | state-free | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 1 FAIL（mf 臂；v3+ plans 前置物章开火） |
| `cd.post_quote_verbatim` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_post_quote_broken_fails_post_quote_verbatim_gate` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 12 WARN（附录 A「post_quote WARN 行」同源） |
| `cd.post_transition_cross` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_post_transition_lied_fails_post_transition_cross_gate` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 回放 0 行发射（POST 转折交叉面未触发） |
| `cd.post_wordcount_precision` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_post_wordcount_lied_warns_precision` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 16 WARN（附录 A「post_wordcount WARN 行」同源；Goodhart r1 POST 虚报 6 章次同类病灶） |
| `G4.cd.ending_diversity` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_ending_repeated_helper_three_ledger_closers` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 回放 0 行发射；ending_archetype_of 47/50 None（哨兵盲） |
| `cd.prop_handoff` | truth | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 9 章 FAIL（mf 11 次，2 章×2 次——附录 A 记 11 次同源；含 truth 漂移成分） |
| `cd.balance_value_drift` | truth | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 12 WARN＋7 FAIL（附录 A 同数；部分 truth 漂移） |
| `cd.counter` | truth | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 33 WARN（附录 A「counter WARN 行」同源） |
| `cd.counter.plan_conflict` | truth | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 回放 0 行发射 |
| `cd.counter.base_mismatch` | truth | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 1 FAIL |
| `cd.counter.prose_mismatch` | truth | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 回放 0 行发射 |
| `G4.cd.hook_type_rotation` | truth | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_hook_type_rotation_full_pipeline_fails_on_same_type` | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md） | 1 FAIL（读 pipeline-state 声明历史） |
| `cd.provenance_anchor` | truth | — | unclassified | — | 50 章 @ 2026-11-20（reports/2026-11-20-gate-power-vol1.md）0 点火 | 回放 0 行发射（WARN-only 来历锚：50 章无违例；I-1 归位行，见脚注） |

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
