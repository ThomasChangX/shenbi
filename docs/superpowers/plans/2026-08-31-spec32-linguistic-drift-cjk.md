# Plan · Spec #32 linguistic-drift-cjk（簇 C6）

> **Spec**: `../specs/2026-08-16-audit-linguistic-drift-cjk-fix.md`（v3）
> **分支**: `fix/spec32-linguistic-drift-cjk` | **日期**: 2026-08-31
> **方法**: 每 task TDD（红→绿→重构），独立 commit

## Task 1 · 共享度量层（F601/F609/F652/F404）

1. **红**：`tests/unit/text/cjk/` 新增 `test_quote_pair_count.py`——含内容引语（“你好”/「带内容」/ASCII "x"）计数 > 0；空引号对仍计；跨形态快照断言（对 `tests/fixtures/snapshot-dir/chapter-*.md` 弯引号 fixture、`tests/fixtures/chapter-7-draft.md` ASCII fixture 各跑一次：引号计数 > 0、对白占比 ∈ 实测区间 ±5pp）。跑测试确认红。
2. **绿**：改 `src/shenbi/text/cjk.py` 引号度量——QUOTES token 改为配对 regex（开/闭字符集：`“”‘’`、`「」`、`『』`、ASCII toggle），计数 = 配对出现的引语数；导出 `count_quote_pairs(text)` 与 `dialogue_char_ratio(text)`（对白字符数含引号内内容）。
3. `compute_stats.py`：`compute_punctuation`（:264-266）改为**只替换计数来源**——import cjk 的计数值，保留 `{name:{count,per_1000}}` 输出契约（compute_stats.py:410 调用方与 test_compute_stats.py:129-137 不破）；桶语义差（cjk 感叹号含半角 `!`、引号桶由 per-char 变配对计数）纳入 G6.5 diff 披露。TTR 排除串（:204）补 CJK 弯引号（改为从 cjk.py 导入统一排除集）。
4. `gates/g6_checks.py`（:111-115）：dialogue_chars 改用 cjk 配对计数的**字符数**（非匹配次数）；对同一 fixture 集跑修复前后 action/dialogue/introspection 分类 diff（脚本一次性跑，结果记入本 plan 附注与 PR 描述）。
5. **property 重设计**：`tests/property/cjk/test_punct_properties.py:26-27` 整 token `text.count` 契约改为配对计数 property（计数值 ≤ 开引号字符出现数；无引号文本计数 0；空对仍计）。
6. 验收：AC1 相关测试绿；AC2 快照测试绿；AC6 部分。

## Task 2 · 触发边界（F646/F653 + F618 行为面）

1. **红**：`tests/unit/skill_utils/test_drift_detection.py` 新增：`_try_float("nan")/("inf")/-inf → None`；短句链判定——先切句再数句长：长句尾部 ≤15 字不触发、段中真实 3 连短句触发。
2. **绿**：`compute_drift.py:219-224` 加 `math.isfinite`；`linguistic_drift.py` `_short_chain_chars`（:107）重写为切句+长度判定（不用正则锚）。
3. 零基线：`linguistic_drift.py:227` 零基线分支改 `insufficient_baseline` 标记不触发 is_drift（首见不触发）；对应测试在 `drift_detection/test_linguistic_drift.py` 新增。
4. 验收：AC1 绿。

## Task 3 · 单源化（F644/F645/F647/F617 + 6.0 归属）

1. **红**：`drift_detection/test_linguistic_drift.py` 新增 AST 断言测试：模块内无 `Compare` 节点以字面量 Float/Int(100/50/30/6.0) 为比较子（walk `linguistic_drift` AST）。
2. **绿**：`linguistic_drift.py:247-251` 改 import `src/shenbi/config/thresholds.py`（注意仓内另有一 contracts/thresholds.py，勿改错），补 `system_term_density_escalate=100`（补 `system_term_density_escalate=100` 到 thresholds.py）；`:227` 6.0 裁决为命名语义常量 `_ZERO_BASELINE_RATIO_SENTINEL`（文档化：仅历史兼容路径，配合 T2 insufficient_baseline 后该分支收敛）。
3. genre-config `drift_detection` 键裁决（AC3 grep 命中可能及于 drift_detection 目录其他文件，白名单按文件逐条核对）：读方 `linguistic_drift.py:68-102`——裁决为**删读方、保留 bootstrap 词表 + thresholds 阈值**（无写方即无信息，补写方属功能新增非本簇）；成文于 spec 修订注记。
4. `compute_pattern.py:88` `compute_entropy` 改全标签求和（Counter 全量进求和，分母一致）。
5. 删除 legacy 死面：`linguistic_drift.py:307-390`（整段：`_load_baseline` + `check_linguistic_drift` 两函数全量） + 随删 `tests/pipeline/test_linguistic_drift.py`；核对覆盖率 ≥85。
6. 验收：AC3 grep（`git grep -nwE "100|50|30|6\.0" -- src/shenbi/skill_utils/drift_detection/`）白名单核对 + AST 测试绿。

## Task 4 · 管线接线（F304/F333）

1. **红**：`tests/unit/pipeline/test_chapter_loop_*` 新增并行波共振解析测试（构造 cs.resonance_score 缺失 + 分数低于 floor 两形态）；`test_revision_router.py:110` `test_none_resonance_passes` 改写——裁决 None 语义为 **fail-open 保留但披露**（返回 True + check_resonance 纯函数内 structlog 记 `resonance_unscored` 事件，签名不变；生产并行流升级后 None 应消失，保留 fail-open 是防御深度）；scr_extractor 行号/POV 测试：多行输入 line_range 与真实换行位置对应（非句子序号）、POV 无显式标记时返回 None/空而非伪造串。
2. **绿**：`chapter_loop.py` 并行流 consolidation 后解析共振分（对齐 serial :3034 逻辑）+ 更新 resonance_trend；`scr_extractor.py:170` line_num 按 prose 换行位置重建真实行号映射（迭代对象是 re.split 句子，仅每句 +1 仍是假行号）；`_extract_pov_shifts`（:273-286）删除高频串伪造，无显式 POV 标记时如实返回空。
3. 验收：AC4 两断言绿。

## Task 5 · 隔离与回归（F615/F649 + 端到端）

1. **红**：jieba 隔离测试——tokenize 后全局 `jieba.dt` 词典不被 add_word 污染（跨调用状态消失）；`records/drift.py` 两方向测试——短行（cell 少于 header）补齐空 cell；溢出 cell（多于 header）丢弃溢出部分并计 discarded_cells（现行为：缺键保留部分行/溢出静默丢弃，均无披露）。
2. **绿**：`cjk.py:100-103` 模块级 `jieba.Tokenizer()` 实例；`records/drift.py:51-57` 短行补空 cell、溢出计 discarded_cells。
3. 端到端：`tests/unit/skill_utils/test_drift_triggers_integration.py` 新增——构造已知漂移章节样本 → detect_drift 触发 + escalation 记录落盘断言。
4. 验收：AC5 绿；`just check` 全绿（AC6）。

## 显式不做（本 PR 外）

- 影子模式实跑校准与阻断启用（spec 风险节，属运行时操作）
- F644 的"补写方"路线（裁决删读方）
- escalation_bridge 删除面（C37 #51）
- 已修 6 finding 的复修
- compute_linguistic_metrics:144-146 对白密度字符计数单源化（非本簇 LIVE finding，显式不做，记 spec-deviations）

## 验收对账

| AC | 承接 task | 证据 |
|----|----------|------|
| 1 边界用例全绿 | T2/T3 | pytest 四文件 |
| 2 快照 + G6.5 diff | T1 | 快照测试 + PR 描述 diff |
| 3 grep 白名单 + AST | T3 | grep 输出 + AST 测试 |
| 4 并行共振/SCR | T4 | 两测试 |
| 5 端到端触发 | T5 | integration 测试 |
| 6 just check | 全 | CI |
