> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C6，21 条）| **代表 finding:** F602 | **严重度上限:** P1（F602/F601/F304）| **涉及文件面:** src/shenbi/skill_utils/drift_detection/、style_learning/compute_stats.py、text/cjk.py、pipeline/chapter_loop.py（resonance 死分支）、escalation/check.py、gates/g6_checks.py、scr_extractor.py

# 语言学漂移与风格分析链修复（audit-linguistic-drift-cjk）

## 背景

drift/style 分析链存在成体系的实现层缺陷，共同后果是**触发永不命中或恒误触发**——安全网整体形同虚设：

1. **触发条件数学性不可达**：F602（dialogue 崩塌触发 `5.0 > 5.0` 恒假，verified）、F618（零基线单次出现即触发——ratio 强制 6.0）、F650（空 system_terms → 空正则全位置匹配 → 恒 ESCALATE）。
2. **CJK 度量盲区**：F601（cjk.py:54 引号 token 只能匹配空引号对，真实引号恒计数 0，verified）、F625（对话 regex 只匹配 ASCII 直引号，CJK 弯引号恒 0）、F609（compute_punctuation 复刻 cjk.py 已修复的逐字计数 bug————/……双倍）、F652（TTR 排除串缺 CJK 弯引号）、F404（G6 对白指标数的是正则匹配次数不是字符数，低估 ~5x+）。
3. **基线/词表/阈值分裂**：F617（双基线体系三重不一致：路径/量纲/词表）、F644（genre-config drift_detection 键零写入方，SYSTEM_TERMS 恒走 bootstrap 词表）、F645（thresholds.py 单源被 linguistic_drift.py 硬编码绕过）、F647（PATTERNS 词表盲区致熵系统性低估）。
4. **解析与状态污染**：F615（tokenize 污染 jieba 全局词典——隐藏跨调用状态）、F646（_try_float 接受 nan/inf，单个 nan 单元杀死该维度全部触发）、F304（默认并行流中共振分永不解析——resonance floor 失效、resonance_trend 永不更新，verified）、F307（DriftEscalationError 被吞，当前触发面为零故 P2，F376 修复后回升 P1——与 C7 联动）、F333（scr_extractor 行号恒 1、POV 伪造）。
5. **截断伪影**：F651（排比检测 [:20] 截断——任意三个 >20 字连续句子恒判排比）。

## 修复目标

1. 所有触发条件可达且无误触发面（构造的边界用例逐条命中/不命中）。
2. CJK 度量（引号/对白/标点/TTR）与中文文本事实一致——text/cjk.py 作为度量单一信源，style_learning 复用而非复刻。
3. 基线/词表/阈值单源：thresholds.py + genre-config 驱动，双基线体系收敛。
4. 无隐藏全局状态（jieba 词典隔离）。

## 任务分解

- **T1 · 共享度量层（F601/F625/F609/F652/F404）**：text/cjk.py 修复引号 token 匹配后，作为 CJK 度量唯一实现；compute_stats/g6_checks/linguistic_drift 全部换用 import（删除各自复刻）。吸收 T14 候选 T1401（style-learning 统计半确定性化）作为接线载体。用真实章节文本（tests/fixtures 或 xinghuo-ranqiong）建立度量快照断言（引号计数 > 0、对白占比量级合理）。
- **T2 · 触发条件修复（F602/F618/F650/F651/F646）**：比较符边界（>→≥ 按语义裁决并文档化）；零基线策略（首见不触发、标记 insufficient_baseline）；空词表短路返回非触发；排比检测去 [:20] 截断；_try_float 拒绝非有限值（对齐 docstring）。
- **T3 · 单源化（F617/F644/F645/F647）**：基线体系二选一收敛（与 C7 的 establish_baseline 接线统一裁决）；词表/阈值从 thresholds.py + genre-config 读取，硬编码常量删除（死常量归 C37）。
- **T4 · 管线接线面（F304/F307/F333）**：默认并行流解析共振分并更新 resonance_trend（死分支删除或接线，与 C1 F372 解析修复联动）；DriftEscalationError 不再被 except Exception 降级（吞错面归 C13，此处修复其唯一 drift 触发点）；scr_extractor 行号真实化。
- **T5 · 隔离与回归（F615）**：jieba 初始化隔离（每进程独立词典或锁内 add_word）；新增 drift 链端到端回归：构造已知漂移样本 → 触发命中 + escalation 记录。

## 批量清理（纯 M 成员）

- F333（scr_extractor 行号）列 T4；F648（detect_rhetoric off-by-one）、F649（parse_markdown_table 短行部分比较）、F652（TTR 排除串）随 T1/T2 批量修复；F653（_short_chain_chars 无左锚）一行加锚。

## 验收标准

1. `uv run python -m pytest tests/unit/skill_utils/test_linguistic_drift.py`（新增边界用例：5.0 边界、零基线、空词表、排比截断、nan）全绿——每条对应簇内 finding 的可复现断言。
2. 对 xinghuo-ranqiong 真实章节跑度量快照：引号计数、对白占比非零且量级稳定（F601/F625/F404 复验）。
3. `git grep -n "6\.0\|5\.0 >" src/shenbi/skill_utils/drift_detection/` 无硬编码阈值残留（F618/F645 断言，常量移 thresholds.py）。
4. drift 链端到端回归：已知漂移样本触发 + escalation 记录落盘（F602/F307 断言）。
5. `just check` 全绿。

## 风险与回滚

- 风险：触发条件修复后 drift 链首次真实生效，可能在存量项目上产生此前从未出现的新 escalation——先以影子模式（记录不阻断）跑一轮真实章节数据校准阈值再启用阻断。基线收敛（T3）裁决可能废弃一套基线文件，需迁移脚本。
- 回滚：T1-T4 逐模块独立提交；影子模式开关可回退到"记录不触发"状态。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C6（21 条，代表 F602）：

F304 F307 F333 F404 F601 F602 F609 F615 F617 F618 F625 F644 F645 F646
F647 F648 F649 F650 F651 F652 F653
