> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1（F901 执行协议断链）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C23）| **代表 finding:** T1001 | **簇规模:** 46 条 | **严重度上限:** P1
> **范围:** AGENTS.md、command-to-give.md、overview.md、gates/dispatcher docstring、活跃+归档 spec、plans/INDEX、README、doc-links CI | **证据等级:** 实验佐证（grep/ls 机械对账实跑，T10 线程 + Z9-a + Z6 + Z7-d）
> **与既有 spec 关系:** phase4 §7 建议 C23/C24 合并为"文档对账工具+CI"批量处理——本 spec 与 C24（语义矛盾）为**同工具两用**：本 spec 管机械面（计数/断链/行号），C24 管语义面（矛盾版本）；CI 承载面依赖 C17 T2 的 doc-links 落地
> **phase4 §7 排序:** 文档卫生 102 条合并批处理的机械半

# C23 · 文档机械漂移批量修复与 doc-links 防线（docs-mechanical-drift）

## 背景（根因 + 证据）

**根因**：文档声称的计数（69/59/15）、文件引用、行号锚点随代码演进**单向过期**——修复动作存在但修复效果衰减（T1001：D1 行号订正在归档 spec 中第三次漂移，PR #42 +61 行后较上轮恶化 +22→+43 行），因为 internal-links 检查 371 项测试零执行环境（nightly 禁用 + 本地 skip，F001/F732 → C17）。

证据分组（46 条）：
- **断链（文件已删/已移）**：F901（P1，执行协议引用已删除的 dispatch 脚本）+ F461/F1034（command-to-give.md:48 引用已删除的 tests/dispatch-subagent.sh，双重发现）、F952（:24 工具名 validate-gate.py 全仓不存在）、F951（:1 引用已归档 plan 路径）、F236（registry.py docstring 指向已删除的 src/shenbi/contract.py）、F461、F917（AGENTS.md 结构树含已删除的 tests/rounds）、F879→C24（using-shenbi 引用已移至 archive 的 spec 路径——归 C24）、F638（recall.py docstring 引用不存在的 RAG benchmarks/index/）、F714（test_logging.py docstring 引用不存在的 tests/logging.py）、F968（32 个归档 plan 的 spec 批量路径漂移——全部可按 basename 在 specs/archive 找到，0 真死链）
- **计数漂移**：F904/F007/F1023/F1033（技能总数 69/67/59 四文档 vs 磁盘 74，多区立案合并）、F906（"59 个 skill"推进条件过期）、F907（"15 种 kind" 实际 16）、F423（gates.md 称 8 个 gate，cli 实际 11）、F440（G0.12 注释称 20 skills，注册表 31）、F967（plans/INDEX 归档计数 66/63 vs 磁盘 68）、F974（68 份归档 plan 63 份复选框未回填）、F1037（覆盖率阈值文档 78/85 vs 配置 80/89——与 F707/C24 交界，机械面归此）、F769（doc_links 参数化计数单调增长，"371 项"自设计上过期）
- **行号/引用漂移**：T1001（代表，第三次漂移）、F331（活跃 spec file:line 漂移 >5 行）、F425（g3_independence docstring 行号过期）、F426（chapter_revision docstring 引用 :87 实际 :147）、F460（错误消息引用 SKILL.md:125 实际 140）（邻接：F934 活跃 spec 证据系统性漂移归 C24 处理）
- **docstring/注释过期**：D103（chapter_loop.py:20 TODO 措辞）、F117（__init__ 称 forwarder until PR-19/20）、F127（子模块清单仅列 6 项实际 26）、F334（timeout "base=300s" vs 900）、F335（_AUDIT_MIN_BYTES=200 vs ">500"）、F428（G2.10 注释仅 chapter 实则全类型 + 与 G7.5 重复）、F429（G6.12 SKIP 备注 round INCOMPLETE）、F126（scoring CLI usage 三重漂移）、F612（docstring CLI 用法不存在）
- **占位/杂项**：F804/F854（.gitkeep 在已有内容目录中冗余）、F953（command-to-give.md 空节）、F955（spec 预写目录漂移）、F970（coverage-ledger 锚点指向不存在报告）、F971（覆盖率数值与 coverage.xml 不一致）、T1003（台账文本 12 vs 13 patch 笔误）

## 目标

1. 机械面 46 条一次清零：断链修复、计数对齐或去数字化、行号锚点更新
2. **结构性止血**：计数类声称去数字化（指向单源或"见 X"），行号引用改为符号/锚点引用，使漂移面从设计上缩小
3. doc-links 内链检查进 per-PR CI（依赖 C17 T2 承载），断链不再复发

## 任务分解

### T1 · 断链清零（P1 先行）
1. F901/F461/F1034/F952/F951：command-to-give.md 五处引用重写（已删脚本 → 现行 shenbi-dispatch 入口；validate-gate.py → shenbi-validate；归档路径 → 现行路径或删行）
2. F236/F638/F714/F917：四处 docstring/结构树过期引用更新
3. F968：归档 plan 的 32 个 spec 路径批量改 basename 可解析形式（或加 `archive/` 前缀重写，一次性 codemod）

### T2 · 计数治理（去数字化优先于追数字）
4. 技能计数四文档（F904/F906/F007/F1023/F1033）：AGENTS.md/overview 等**删除硬编码数字**，改"以 `ls skills/` 与 deps.json 对账为准"（C22 R1 lint 会拦不一致；若保留数字则必须由 lint 校验——二选一，推荐去数字）
5. gates 计数（F423）、kind 计数（F907）、G0.12/注册表计数（F440）、归档计数（F967）、复选框回填（F974）、覆盖率阈值自述（F1037→对齐 pyproject 实值）、F971/F970 数值锚点重算或删除
6. F769：doc_links 自身文档去掉"371 项"类快照计数，改动态描述

### T3 · 行号锚点降险
7. T1001/F331/F425/F426/F460：spec 与 docstring 中的 `file.py:NNN` 引用尽量改为 `file.py::<symbol>`（函数/常量名）形式；无法符号化的加"行号为 2026-08-16 快照"标注；归档 spec 只在 doc-links 可达性上修，不逐行追号（追不动是 T1001 的教训）
8. D103/F117/F127/F334/F335/F428/F429/F126/F612：docstring 过期注释逐条更新（多数为删一行或改一个数）

### T4 · 防线接线（与 C17 T2 合流）
9. internal-links 检查进 per-PR CI 后，本簇 T1/T2 修复以该检查绿灯为机械验收
10. 新增一条最小"文档计数哨兵"（可选）：对保留数字的声称（若 T2 选择保留路线）做 CI 校验——默认走 C22 R1，不建第六张表

### 批量清理（M 级成员，20 条）
D103、F117、F127、F236、F334、F335、F423、F425、F426、F428、F429、F440、F460、F461、F714、F804、F854、F953、F955、T1003 —— 均为单行/单词级修订，随 T1/T3 批量 PR 顺带清（上表已并入各任务项，此处列 ID 备查对账）。

## 验收标准（真实数据可复验）

1. internal-links 检查（C17 T2 落地后）对全仓 docs+README+command-to-give 跑批 0 断链；修复前基线计数留档对照
2. `grep -rn "dispatch-subagent\|validate-gate" docs/ command-to-give.md` 0 命中；`git grep -n "69 total\|67 functional" AGENTS.md docs/` 0 命中（去数字化路线）或与 C22 R1 输出一致（保留路线）
3. 抽查 10 处行号锚点（T1001/F331/F425/F426/F460 各 2）：引用目标符号可 `grep -n <symbol>` 命中且唯一
4. `just check` 全绿；归档 plan 32 条路径用 basename 解析脚本验证 0 失败（F968 红转绿记录）

## 风险与回滚

- **风险**：去数字化改变入口文档风格（AGENTS.md 是 agent 入口）——保留语义描述、只删精确计数，PR 里前后对照
- **风险**：归档 spec/plan 大面积文本改动污染 git blame——归档区用单批 codemod commit（消息注明机械替换），可整体 revert
- **风险**：行号改符号引用在重构时同样会断（符号改名）——doc-links + CI 符号存在性检查兜底（T4）
- **回滚**：全部为文档/docstring 改动，零生产代码；分 T1/T2/T3 三批 PR 各自可回滚

## 簇成员清单（46 条，自查用）

D103, F006-F007, F117, F126-F127, F236, F331, F334-F335, F423, F425-F426, F428-F429, F440, F460-F461, F612, F638, F714, F769, F804, F854, F901, F904, F906-F907, F909-F910, F917, F951-F953, F955, F967-F968, F970-F971, F974, F1023, F1033-F1034, F1037, T1001, T1003（代表 T1001）
