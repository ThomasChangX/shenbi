> **Date:** 2026-08-16 | **修订:** 2026-08-31（SDD #32 驳斥复核后收窄，v2） | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C6，21 条）| **代表 finding:** F602 | **严重度上限:** P1（F304/F404/F333）| **涉及文件面:** src/shenbi/text/cjk.py、skill_utils/drift_detection/、style_learning/compute_stats.py、pipeline/chapter_loop.py（resonance 死分支）、pipeline/scr_extractor.py、gates/g6_checks.py、records/drift.py、skill_utils/chapter_pattern/compute_pattern.py

# 语言学漂移与风格分析链修复（audit-linguistic-drift-cjk）

## 修订注记（2026-08-31，fresh-context 驳斥复核 agent_ebc1aabc）

- **已 FIXED 剔除**（main c8ec47d8 实读）：F602（linguistic_drift.py:26,240 比较已 `>=`）、F650（:128-132 空词表短路）、F625（compute_stats 对话 regex 已被 F668 方向引号机制取代）、F651/F648（compute_stats.py:293-298 排比窗口已完整）、F307（chapter_loop.py:556-560 DriftEscalationError 先 re-raise）。
- **F618 并入 T2 阈值裁决**（后果仅 WARN 级，不再单列）；**F617 收窄为删除 legacy 双基线死面**（`_load_baseline/check_linguistic_drift` 仅测试调用，非三重对齐）。
- 保留 15 条 LIVE（含 F615/F646 两处已自认限制），剔除 6 条已修。

## 背景

drift/style 分析链存在成体系的实现层缺陷，共同后果是**触发永不命中、恒误触发或度量与中文文本事实不符**——安全网整体形同虚设。2026-08-31 复核确认以下活面：

1. **CJK 度量盲区**：F601（cjk.py:54 引号 token 为两字符字面量，只能匹配空引号对，真实引语恒计数 0）、F609（compute_stats.py:264-266 compute_punctuation 复刻 cjk.py 已修复的逐字计数 bug——"——"/"……"双倍）、F652（compute_stats.py:204 TTR 排除串缺 CJK 弯引号 “”‘’）、F404（g6_checks.py:111-115 对白指标数的是 regex 匹配次数而非字符数，且 regex 仍只认 ASCII 直引号）。
2. **触发与解析缺陷**：F618（linguistic_drift.py:227 零基线 ratio 强制 6.0，单次出现即 WARN 触发）、F646（compute_drift.py:219-224 _try_float 接受 nan/inf，违背自述 docstring）、F653（linguistic_drift.py:107 _short_chain_chars 无左锚，长句尾部可被回溯误判短句链）、F651 已修剔除。
3. **基线/词表/阈值分裂**：F617（linguistic_drift.py:309-327 legacy `_load_baseline/check_linguistic_drift` 死面指向 context/ 旧基线，生产走 style/ 新基线，双轨发散）、F644（genre-config drift_detection 键零写入方，SYSTEM_TERMS 恒走 bootstrap 词表）、F645（thresholds.py:39-40 单源被 linguistic_drift.py:247-250 内联硬编码绕过，ESCALATE=100 只存在于硬编码侧）、F647（compute_pattern.py:88 compute_entropy 只遍历词表内模式，out-of-vocab 计入分母不进求和，熵系统性低估）。
4. **管线接线面**：F304（chapter_loop.py:3034,3050 共振分解析+trend 写入仅在 serial 路径；并行波 :2645 直接 `_route_revision_after_resonance`，revision_router.py:115-117 `check_resonance(None)` 恒 True——resonance floor 在默认并行流失效）、F333（scr_extractor.py:170,273-286 line_num 恒 1、POV 用段落高频 2-3 字 CJK 串伪造，污染下游 LLM 上下文）。
5. **解析与状态污染**：F615（cjk.py:100-103 jieba.add_word 污染全局词典，docstring 自认）、F649（records/drift.py:51-57 parse_markdown_table 短行超出 header 部分静默丢弃仍以部分字段参与比较）。

## 修复目标

1. 所有触发条件可达且无误触发面（构造的边界用例逐条命中/不命中）。
2. CJK 度量（引号/对白/标点/TTR）与中文文本事实一致——text/cjk.py 作为度量单一信源，style_learning/g6_checks 复用而非复刻。
3. 阈值/词表单源：thresholds.py 驱动，硬编码常量删除；legacy 双基线死面删除。
4. 无隐藏全局状态（jieba 词典隔离）；共振分在并行流真实解析。

## 任务分解

- **T1 · 共享度量层（F601/F609/F652/F404）**：text/cjk.py 修复引号 token 匹配（配对计数含内容引语与 CJK 弯引号）后作为 CJK 度量唯一实现；compute_stats 的 punctuation/TTR 排除串、g6_checks 的对白指标全部换用 import（删除各自复刻）。用真实章节文本建立度量快照断言（fixture 选点：`tests/fixtures/snapshot-dir/chapter-*.md` 为含 CJK 弯引号 “” 的真实快照、`tests/fixtures/chapter-*-draft.md` 为含 ASCII 直引号对白的真实草稿——两类引号形态各有覆盖；novel-output 不入测试，仅影子模式校准用）。**配套测试面**：`tests/property/cjk/test_punct_properties.py:26-27` 的 `text.count(token)` 整 token 计数契约随修复重设计（配对计数后改为新 property：计数值 ≤ 引号字符出现数/2、对称性等）；G6.5 存量影响披露——对同一 fixture 集跑修复前后 action/dialogue/introspection 分类 diff，披露 dialogue_pct 上移幅度（g6_checks.py:118-127 阈值 30/35 的语义漂移窗口）。
- **T2 · 触发边界修复（F618/F646/F653）**：_try_float 拒绝非有限值（math.isfinite，对齐 docstring）；_short_chain_chars 修复方案定为**先切句再数句长**（不锁死正则左锚——锚定会漏段中真实短句链，按 M6 裁决）。零基线策略（首见不触发、标记 insufficient_baseline）在 linguistic_drift.py 实现断言，其 6.0 magic 的归属与阈值语义文档化**统一归 T3**（M7，本任务不重复认领）。
- **T3 · 单源化（F644/F645/F647/F617/F618 阈值）**：词表/阈值从 thresholds.py 读取，linguistic_drift.py 内联 100/50/30 删除（含 :227 零基线 6.0 magic——裁决为语义常量并文档化或入 thresholds，单一归属本任务）；genre-config drift_detection 键裁决（补写方或删读方，二选一成文）；compute_entropy 熵求和覆盖全标签（out-of-vocab 不再只占分母）；删除 legacy `_load_baseline/check_linguistic_drift` 死面及 context/ 基线路径，**随删测试文件 `tests/pipeline/test_linguistic_drift.py`**（整文件以 check_linguistic_drift 为被测对象），覆盖率波动在本 PR 内核对 ≥85 门。
- **T4 · 管线接线面（F304/F333）**：并行流 consolidation 后解析共振分并更新 resonance_trend（对齐 serial 路径 :3034 行为）；`check_resonance(None)` 的 None 语义重定义（现被 `tests/unit/pipeline/test_revision_router.py:110` 锁定为通过——改为"None 视为未评分、走显式未评分分支（fail-open 记录披露）或拒绝并记录"，二选一裁决成文，契约测试同步改写）；scr_extractor line_num 真实跟踪行号、POV 提取改为显式标记或如实标注置信缺失（删除伪造）。
- **T5 · 隔离与回归（F615/F649）**：jieba 初始化隔离（模块级 `jieba.Tokenizer()` 实例，禁全局 add_word）；parse_markdown_table 短行策略定稿（丢弃整行并计数披露，或补齐空 cell——按下游 `_values_equal` 语义裁决）；新增 drift 链端到端回归：构造已知漂移样本 → 触发命中 + escalation 记录。

## 批量清理（纯 M 成员）

F649 列 T5；F653 一行加锚（列 T2）。已修项 F648/F651/F625/F602/F650/F307 移出本 spec（复核证据存档于本修订注记）。

## 验收标准

1. `uv run python -m pytest tests/unit/skill_utils/drift_detection/test_linguistic_drift.py tests/unit/skill_utils/test_drift_detection.py tests/unit/skill_utils/test_drift_triggers_integration.py tests/unit/pipeline/test_triggers.py`（新增边界用例：零基线首见不触发、nan/inf 拒绝、短句链先切句判定、熵全标签——按现有测试文件就近落位）全绿——每条对应簇内 LIVE finding 的可复现断言。
2. 对上述真实章节 fixture 跑度量快照：引号计数 > 0（弯引号与 ASCII 形态各自 > 0）；对白占比落在固定区间断言（以修复前后实测值定区间并写入测试，容差 ±5pp）且 G6.5 分类 diff 披露于 PR 描述（F601/F404 复验）。
3. `git grep -nwE "100|50|30|6\.0" -- src/shenbi/skill_utils/drift_detection/`（Apple Git POSIX ERE 无 `\b`，用 -w 词边界；`6\.0` 的 `.` 转义）命中处仅为 thresholds import、语义常量定义（带命名与注释）或 docstring 示例（白名单逐条列于 PR）；**主断言为 AST 级检查（或等价测试）**：linguistic_drift 模块无对字面量阈值的比较表达式（F618/F645 断言，杜绝 grep 漏报）。
4. 并行流回归：构造共振分低于 floor 的并行波 round → 走 revision 路由（F304 断言）；SCR 提取 line_range 随行号递增且非恒 [1,2]（F333 断言）。
5. drift 链端到端回归：已知漂移样本触发 + escalation 记录落盘。
6. `just check` 全绿。

## 风险与回滚

- 风险：触发条件修复后 drift 链首次真实生效，可能在存量项目上产生此前从未出现的新 escalation——先以影子模式（记录不阻断）跑一轮真实章节数据校准阈值再启用阻断。并行流共振解析（T4）改变 revision 路由行为，需构造双结局（floor 上下）回归。
- 回滚：T1-T5 逐模块独立提交；影子模式开关可回退到"记录不触发"状态。

## 簇成员清单（与 phase4-clustering.md §2 机械对照，v2 复核后）

C6（21 条；15 条 LIVE 入任务，6 条已修剔除）：

LIVE：F304 F333 F404 F601 F609 F615 F617(收窄为死面删除) F618 F644 F645 F646 F647 F649 F652 F653（F625 以 F668 修复形态剔除）
FIXED 剔除：F602 F307 F648 F650 F651
