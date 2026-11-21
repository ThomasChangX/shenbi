# spec #116 gate-power replay report

- 项目: novel-xinghuo-vol1
- 章数（分母，纯章形 chapter-NN.md）: 50
- 口径过滤: 全量（双口径列）

## Per-check 判别力

| canonical id | 口径 | PASS | WARN | FAIL | SKIP | firing |
|---|---|---|---|---|---|---|
| cd.counter | truth | 0 | 33 | 0 | 0 | 0.66 |
| cd.balance_value_drift | truth | 0 | 12 | 7 | 0 | 0.20 |
| G4.pre_check | state-free | 50 | 0 | 0 | 0 | 0.00 |
| G4.post_check | state-free | 48 | 0 | 2 | 0 | 0.04 |
| cd.post_wordcount_precision | state-free | 0 | 16 | 0 | 0 | 0.32 |
| G4.transition | state-free | 50 | 0 | 0 | 0 | 0.00 |
| G4.fatigue | state-free | 50 | 0 | 0 | 0 | 0.00 |
| G4.meta | state-free | 50 | 0 | 0 | 0 | 0.00 |
| G4.word_count | state-free | 50 | 0 | 0 | 0 | 0.00 |
| G4.cd.scene_count | state-free | 50 | 0 | 0 | 0 | 0.00 |
| G4.cd.scene_hook_match | state-free | 37 | 0 | 0 | 0 | 0.00 |
| G4.cd.content_uniqueness | state-free | 50 | 0 | 0 | 0 | 0.00 |
| G4.cd.scene_concreteness | state-free | 50 | 0 | 0 | 0 | 0.00 |
| G4.cd.chapter_end_hook | state-free | 35 | 15 | 0 | 0 | 0.30 |
| G4.cd.protagonist_presence | state-free | 46 | 0 | 4 | 0 | 0.08 |
| G4.cd.surge | state-free | 50 | 0 | 0 | 0 | 0.00 |
| G4.cd.simile_band | state-free | 50 | 0 | 0 | 0 | 0.00 |
| G4.cd.voice_density | state-free | 36 | 13 | 1 | 0 | 0.28 |
| G4.cd.golden_slot | state-free | 47 | 3 | 0 | 0 | 0.06 |
| cd.post_quote_verbatim | state-free | 0 | 12 | 0 | 0 | 0.20 |
| G4.cd.micro_hook_run | state-free | 0 | 0 | 1 | 0 | 0.02 |
| cd.prop_handoff | truth | 0 | 0 | 9 | 0 | 0.18 |
| G4.cd.hook_type_rotation | truth | 0 | 0 | 1 | 0 | 0.02 |
| G4.cd.ending_diversity | state-free | 0 | 1 | 0 | 0 | 0.02 |
| cd.counter.base_mismatch | truth | 0 | 0 | 1 | 0 | 0.02 |

## 触发归因（诊断再推导，不改门判定）

### hook（narrative_window 尾 8 段三臂）

- single_char_only 章数: 15（仅单字张力词命中——最弱臂）
- 「还」命中章数: 38
- 「账」命中章数: 38
- gate_class 三向: {'hard': 35, 'single_only': 15, 'none': 0}（spec #118 T2）

### protagonist（name frontmatter＋他 再推导）

- 名单: 那罕、他
- 出现总数中位: 76.0 / 最小: 49

### transition（narrative 口径）

- 每章计数中位: 0.0

### ending（ending_archetype_of）

- None（未归类收束）章数: 19

### simile 双口径（r2/M7 对照列）

- raw 口径 per_1000 均值: 2.02
- narrative-only 口径 per_1000 均值: 2.02
