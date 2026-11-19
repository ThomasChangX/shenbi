# G4 门判别力基线（恒真登记）· spec #116

> 登记分母 = `src/shenbi/gates/g4/chapter_drafting.py` 单文件 AST 单源（check 行
> dict id ∪ mf 首常量 id，经别名表回射 canonical）∪ 扫描不可见的显式补充面。
> **check-id 对账由 `tools/lint_gate_power_baseline.py` 执行**（进 `just lint`）：
> 行缺/多、分类值域外、非 discriminating 缺证据、registry↔AST 漂移均红；本表
> 与 `docs/framework/invariants.md` 分工——彼表管不变量维度覆盖，本表管判别力。

## 口径定义（附录 A 列锚，r2/M3）

- **state-free**：不读 truth oracle 可机检（读 memo/plans 声明属此列）；
- **truth 依赖**：回放历史章对当前 truth 有伪 FAIL 面（对账类：handoff/
  balance/counter 族；hook_type_rotation 读 plans 历史亦入此列）。

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

baseline 回填日 **2026-11-19** ＋ 30 天（一个完整裁定周期，spec r2/I5「分类
义务清偿后」以日历日近似）→ **2026-12-19**。该日后仍 `unclassified` 且最近
回放数为「0 点火」的行由 lint 升格为红（此前仅 stderr WARN）。若回填实跑日
晚于 2026-11-19，锚随「实跑日＋30 天」修正常量（`tools/lint_gate_power_baseline.py`
`ESCALATION_DATE`）并在 task report 记录。

## 登记表（31 行；分类全 `unclassified` 骨架，回放数 Task 5 回填）

| check | 口径 | 期望点火带 | 分类 | 证据 | 最近回放数 | 归因 |
|---|---|---|---|---|---|---|
| `G4.pre_check` | state-free | — | unclassified | — | — | — |
| `G4.post_check` | state-free | — | unclassified | — | — | — |
| `G4.transition` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_transition_flooded_real_chapter_fails_transition_gate` | — | — |
| `G4.fatigue` | state-free | — | unclassified | — | — | — |
| `G4.meta` | state-free | — | unclassified | — | — | — |
| `G4.word_count` | state-free | — | unclassified | — | — | — |
| `G4.cd.scene_count` | state-free | — | unclassified | — | — | — |
| `G4.cd.scene_concreteness` | state-free | — | unclassified | — | — | — |
| `G4.cd.scene_hook_match` | state-free | — | unclassified | — | — | — |
| `G4.cd.chapter_end_hook` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_hook_killed_real_chapter_fails_hook_gate` | — | — |
| `G4.cd.protagonist_presence` | state-free | — | unclassified | `tests/unit/gates/g4/test_gate_power_negatives.py::test_protagonist_vanished_real_chapter_fails_presence_gate` | — | — |
| `G4.cd.surge` | state-free | — | unclassified | — | — | — |
| `G4.cd.simile_band` | state-free | — | unclassified | — | — | — |
| `G4.cd.voice_density` | state-free | — | unclassified | — | — | — |
| `G4.cd.golden_slot` | state-free | — | unclassified | — | — | — |
| `G4.cd.content_uniqueness` | state-free | — | unclassified | — | — | — |
| `G4.cd.quote_verbatim` | state-free | — | unclassified | — | — | — |
| `G4.cd.payoff_density` | state-free | — | unclassified | — | — | — |
| `G4.cd.quote_type` | state-free | — | unclassified | — | — | — |
| `G4.cd.micro_hook_run` | state-free | — | unclassified | — | — | — |
| `cd.post_quote_verbatim` | state-free | — | unclassified | — | — | — |
| `cd.post_transition_cross` | state-free | — | unclassified | — | — | — |
| `cd.post_wordcount_precision` | state-free | — | unclassified | — | — | — |
| `G4.cd.ending_diversity` | state-free | — | unclassified | — | — | — |
| `cd.prop_handoff` | truth 依赖 | — | unclassified | — | — | — |
| `cd.balance_value_drift` | truth 依赖 | — | unclassified | — | — | — |
| `cd.counter` | truth 依赖 | — | unclassified | — | — | — |
| `cd.counter.plan_conflict` | truth 依赖 | — | unclassified | — | — | — |
| `cd.counter.base_mismatch` | truth 依赖 | — | unclassified | — | — | — |
| `cd.counter.prose_mismatch` | truth 依赖 | — | unclassified | — | — | — |
| `G4.cd.hook_type_rotation` | truth 依赖 | — | unclassified | — | — | — |

脚注：

- 附录外行 `G4.cd.quote_type`/`G4.cd.micro_hook_run` 为扫描侧真实 in-scope 检查
  （NB4）：micro_hook_run 需 memo_v3 前置物，回放面记 SKIP；quote_type 为引号型
  检查行，回放面 0 观测。
- `cd.balance_value_drift.bundle` 不占行：唯一发射点在 settle 面
  （`src/shenbi/gates/g4/state_settling.py:305` 束级升格），非本章门回放分母；
  其 mf 串回射父行 `cd.balance_value_drift`（Task 4 裁定，详见 task report）。
- hook/protagonist/transition 三行证据列已填 spec #116 T4 红测（真实章变异→门
  FAIL），供裁定参考；其余行证据列 `—`（unclassified 允许），Task 5 回放数据
  落表后进入人工裁定。
