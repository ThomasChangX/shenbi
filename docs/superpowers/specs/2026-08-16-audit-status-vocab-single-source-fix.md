> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-08-31 · 审查收敛：T903/T909 归位 T5/T4、登记表机器对账、lint 双面+FAIL 直连、ChapterState 兼容层落地、T901 注册门归 T1/T3) | **Severity:** 🟡 P2（面广量大）| **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C8，24 条）| **代表 finding:** F210 | **严重度上限:** P2（全簇无 P0/P1，但为候选元根因 D 的核心分簇）| **涉及文件面:** src/shenbi/contracts/enums.py、contracts/schemas/decisions.py、gates/（g4/chapter_revision、g5、g6）、records/、trace/、tools/lint_status_strings.py、各 checker 硬编码词表点

# 状态/词表/枚举单源收编（audit-status-vocab-single-source）

## 背景

候选元根因 D 分簇一：severity/verdict/status 等词表在 enums.py、checker 硬编码、schema 文档、state JSON 之间多源并立，生产值越表无人拦截。T9 线程全量对账（thread-reports/T9.md 对账矩阵）给出量化：

- **双"唯一信源"并立**：T901——36 个声明域中仅 9 域在两个自称单源的文件内，27 域散落 12 文件；F210——pydantic 契约层 4 个 schema + 7 个 skill 模型未接线，门内并行规则重复。
- **同概念多词表**：T902（enums.Verdict 零 src 消费者，真实第二词表硬编码于 checker）；T903（severity 概念六词表并立，revision-decisions 生产 21.1% severity 值越一切词表——F211 的量化扩展）；T904（GateOutcome.status 重复定义 GateStatus 且缺 UNIMPLEMENTED）；T909（审批决定 approve/modify/reject vs approved/rejected 双词表）；F211（"所有 Literal 必须从此 import"被多处违反，decisions.Severity 与 enums.Severity 同名不同域）。
- **无主域**：T906（progress.json skill status 域无枚举定义）、T907（ChapterState.status 自由串 + complete/completed 同族异形）、T908（"未实现"三形态 + CommandStatus 域外值 degraded）、T910（修订 mode 生产越表：reconstruction/no_op 不在任一词表且 G4 不校验）、T911（novel.json status 无主域无读写方）。
- **生产越表实例**：F402/F711（g4/chapter_revision 返回未声明 "HARD_FAIL"，测试 pin）；F447（状态词表 lint 只拦"词表内"字面量，越表反逃逸——单源门禁盲区）。
- **lint 失效**：T905（lint_status_strings 三重覆盖洞：面内拦截目标空集 + 越表逃逸率 100% + s 键/面外/CWD 三盲区，实跑 0 违规 exit=0）；F1016（lint_status_strings 自身缺陷）、T204（自 #24 补登：G0.16 write_mode 只校验存在性不校验值合法性，拼写错误 mode 过门禁被当默认处理）。

## 修复目标

1. 每个状态概念（status/verdict/severity/mode/approval）恰一个主词表，位于 enums.py（或专属 schema），checker/文档/state JSON 全部换源。
2. 生产值越表被机械拦截：lint 修复后实跑违规检出（当前 0 检出 vs 生产 21.1% 越表）。
3. 同族异形值（complete/completed、UNIMPLEMENTED 三形态）统一，迁移不留双形。

## 任务分解

修复形状吸收 **F771 族的词表对齐方向**：同族问题一次统一裁决、全体成员同批收编（F771 对严重度"同类不同级统一升 P1"的方法论用于词表——不做逐文件补丁，避免修一半留一半的新漂移）。

- **T1 · 词表主域登记表（T901 架构面）**：以 T9 对账矩阵（36 声明域 + 5 无主生产域）为基线，产出 `docs/framework/status-vocab.md`：**机器可解析的固定格式 markdown 表**（每域一节，表头固定 `| 概念 | 主词表（模块.符号） | 合法值（竖线分隔） | 生产写方 | 生产读方 |`），作为唯一裁决依据。T901 的"双唯一信源"文案修正（enums.py:1 与 status.py:3 docstring 改为指向本登记表）归本 task。
- **T2 · enums.py 收编（F210/F211/F514/T902/T904）**：Verdict/GateStatus/GateOutcome.status/severity 等收编至 enums.py，删除 checker 内硬编码第二词表（含 review_resonance.py `_VERDICTS` 改 import enums.ResonanceVerdict）与 decisions.Severity 同名冲突（改名 decisions.SeverityLevel 或合并——按 T1 裁决）；GateOutcome 补 UNIMPLEMENTED（base.py:29 改用 status.py GateStatus，T904 最小改动面）。
- **T3 · lint_status_strings 补洞（T905/F1016/F447/T901 注册门）**：白名单反转为"仅枚举成员表达式合法"——拦截目标改为**逐文件锚定 `__file__` 的绝对路径全仓扫描**（修 CWD 盲区）+ 纳入 `s` 键 + tests/ 面 + 面外（.json/.yaml）扫生产值；新增**登记表对账子检查**（仿 `lint_decisions_sources.py` 模式）：解析 status-vocab.md 固定格式表 ↔ 枚举符号实际定义逐域比对，任何一域双源/漂移/代码中存在登记表外的状态类 Literal → 违规（即 T901 的"新域必须注册"门禁）。lint 保持 FAIL 直连 `just check`（本仓个人仓库无版本周期，不设 WARN 期——修复终点即 exit 0）。
- **T4 · 无主域建域（T906/T907/T908/T909/T910/T911）**：progress skill status（status.py 增 SkillProgressStatus）、ChapterState.status 收型（state.py:98 立域，**canonical 词表以 T1 登记表为唯一穷举**，须涵盖现存全部写方值：`pending/in-progress/complete/settling_failed`，complete 为 canonical（T9 矩阵多数派），归一兼容层落点为 `PipelineState.from_dict` 的 status 解析位点（state.py:~311，ChapterState 是 dataclass 非 pydantic），`completed→complete` 归一 + structlog WARN 一档，写方只写 canonical）、"未实现"三形态统一（CommandStatus 增 DEGRADED/NOT_IMPLEMENTED 或 cli 改用 ERROR，按 T1 裁决）、修订 mode（reconstruction/no_op 收编 + G4 值域校验）、genre-config approval 双词表统一（T909 裁决：**两个独立登记域**——genre-config approval.decision 值域 `{approved, rejected}` 与 pipeline review 命令域 `ReviewDecision {approve, modify, reject}`（state.py:51）语义不同（命令含 modify、值域是终态），不做值迁移，各自在登记表立域消除"同概念"误判）+ content_preservation/verdict.status 立域、novel.json status 按 T1 裁决立域或删字段。
- **T5 · 生产越表实例修复（F402/F711/T903）**：HARD_FAIL 改用词表内值（如 FAIL+severity 标注）或正式入表（按 T1 裁决），同步解 pin 该值的测试；**T903 生产侧收敛**：chapter-revision SKILL.md severity 枚举化（low/medium/high 词表）+ G4 对 severity/mode 做值域检查，使 revision-decisions severity 越表率 21.1%→0%（schema 全面验证失败面归 F237，本 task 只做词表层）。
- **T6 · 文档词表对齐（F212 关联面归 C4）**：schema 文档/AGENTS.md 中词表引用全部指向 T1 登记表，不再内嵌复制值。

## 批量清理（纯 M 成员）

- F220（VALID_BASIS/VALID_SEVERITY 死常量删除，随 T2）、F221（ScoreReport 双定义合一）、F336/F352（chapter=0 vs None 语义分裂——统一 None 并在词表登记"genesis 语义"）、F441（score checker check id 补技能前缀，归入 id 命名词表）、T302（extract_h2_sections 与 lint 匹配语义统一——由 C2 T4 承接，此处登记；若 C2 长期不落地由 T3 登记表挂 Dangling 标记）、T911（novel.json status 归 T1 裁决：有读写方→T4 立域；无读写方→删字段，分支条件唯一属 T1）。

## 验收标准

1. `uv run python tools/lint_status_strings.py --scan-tree novel-output`（repo 全量 + novel-output/ 全部生产树（含 xinghuo-ranqiong 与 test-validation）的 JSON 值面）：修复前 exit 非 0 且报告越表值清单（T905 断言——当前实跑 0 违规是假阴性）；修复后 exit 0。
2. `uv run python tools/check_severity_vocab.py`（本 spec 新增、入库 tools/ 并**接入 just check** 的 T903 口径复算脚本，替代 T9 的 /tmp 临时脚本）：revision-decisions severity 越表率 21.1% → 0%。
3. `git grep -rn "HARD_FAIL" src/` 零残留或仅 enums.py/登记表出现（F402/F711 断言）。
4. T3 登记表对账子检查 exit 0（= 36+5 域每域主词表与读写方机械成立，替代人工对照 T9 矩阵）。
5. `just check` 全绿。

## 风险与回滚

- 风险：收编改变序列化值会破坏存量 state JSON/trace 兼容（completed→complete 类）——ChapterState 经 `PipelineState.from_dict` 解析位点归一旧形（completed→complete）+ structlog WARN 一档，写方只写 canonical；HARD_FAIL 改值影响下游消费方（若有），先 grep 消费面（已核：仅 chapter_revision.py:97 + 4 处测试 pin）。
- 回滚：T2 每概念独立提交；lint（T3）独立可 revert。T3 的白名单反转与 T4/T5 的越表值修复必须**同批落地**（lint 已接 just check，中间红窗口不可停留在共享分支上）。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C8（24 条，代表 F210）：

F210 F211 F220 F221 F336 F352 F402 F441 F447 F514 F711 F1016 T302 T901
T902 T903 T904 T905 T906 T907 T908 T909 T910 T911
