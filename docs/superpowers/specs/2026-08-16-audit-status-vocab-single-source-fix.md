> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟡 P2（面广量大）| **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C8，24 条）| **代表 finding:** F210 | **严重度上限:** P2（全簇无 P0/P1，但为候选元根因 D 的核心分簇）| **涉及文件面:** src/shenbi/contracts/enums.py、contracts/schemas/decisions.py、gates/（g4/chapter_revision、g5、g6）、records/、trace/、tools/lint_status_strings.py、各 checker 硬编码词表点

# 状态/词表/枚举单源收编（audit-status-vocab-single-source）

## 背景

候选元根因 D 分簇一：severity/verdict/status 等词表在 enums.py、checker 硬编码、schema 文档、state JSON 之间多源并立，生产值越表无人拦截。T9 线程全量对账（thread-reports/T9.md 对账矩阵）给出量化：

- **双"唯一信源"并立**：T901——36 个声明域中仅 9 域在两个自称单源的文件内，27 域散落 12 文件；F210——pydantic 契约层 4 个 schema + 7 个 skill 模型未接线，门内并行规则重复。
- **同概念多词表**：T902（enums.Verdict 零 src 消费者，真实第二词表硬编码于 checker）；T903（severity 概念六词表并立，revision-decisions 生产 21.1% severity 值越一切词表——F211 的量化扩展）；T904（GateOutcome.status 重复定义 GateStatus 且缺 UNIMPLEMENTED）；T909（审批决定 approve/modify/reject vs approved/rejected 双词表）；F211（"所有 Literal 必须从此 import"被多处违反，decisions.Severity 与 enums.Severity 同名不同域）。
- **无主域**：T906（progress.json skill status 域无枚举定义）、T907（ChapterState.status 自由串 + complete/completed 同族异形）、T908（"未实现"三形态 + CommandStatus 域外值 degraded）、T910（修订 mode 生产越表：reconstruction/no_op 不在任一词表且 G4 不校验）、T911（novel.json status 无主域无读写方）。
- **生产越表实例**：F402/F711（g4/chapter_revision 返回未声明 "HARD_FAIL"，测试 pin）；F447（状态词表 lint 只拦"词表内"字面量，越表反逃逸——单源门禁盲区）。
- **lint 失效**：T905（lint_status_strings 三重覆盖洞：面内拦截目标空集 + 越表逃逸率 100% + s 键/面外/CWD 三盲区，实跑 0 违规 exit=0）；F1016（lint_status_strings 自身缺陷）。

## 修复目标

1. 每个状态概念（status/verdict/severity/mode/approval）恰一个主词表，位于 enums.py（或专属 schema），checker/文档/state JSON 全部换源。
2. 生产值越表被机械拦截：lint 修复后实跑违规检出（当前 0 检出 vs 生产 21.1% 越表）。
3. 同族异形值（complete/completed、UNIMPLEMENTED 三形态）统一，迁移不留双形。

## 任务分解

修复形状吸收 **F771 族的词表对齐方向**：同族问题一次统一裁决、全体成员同批收编（F771 对严重度"同类不同级统一升 P1"的方法论用于词表——不做逐文件补丁，避免修一半留一半的新漂移）。

- **T1 · 词表主域登记表**：以 T9 对账矩阵（36 声明域 + 5 无主生产域）为基线，产出 `docs/framework/status-vocab.md` 概念→主词表→合法值→生产读写方清单，作为唯一裁决依据。
- **T2 · enums.py 收编（F210/F211/F514/T902/T904）**：Verdict/GateStatus/GateOutcome.status/severity 等收编至 enums.py，删除 checker 内硬编码第二词表与 decisions.Severity 同名冲突（改名 decisions.SeverityLevel 或合并——按 T1 裁决）；GateOutcome 补 UNIMPLEMENTED。
- **T3 · lint_status_strings 补洞（T905/F1016/F447）**：拦截目标改为 T1 登记表全集（面内目标空集修复）；检测面扩到生产值域（越表逃逸率 100%→0）；补 s 键/面外/CWD 三盲区——lint 必须对 repo 内全部相关文件按绝对路径执行。
- **T4 · 无主域建域（T906/T907/T908/T910/T911）**：progress skill status、ChapterState.status、"未实现"形态、修订 mode（reconstruction/no_op 收编 + G4 校验）、novel.json status 逐个立域；complete/completed 同族统一（读方兼容迁移期后删旧形）。
- **T5 · 生产越表实例修复（F402/F711）**：HARD_FAIL 改用词表内值（如 FAIL+severity 标注）或正式入表（按 T1 裁决），同步解 pin 该值的测试。
- **T6 · 文档词表对齐（F212 关联面归 C4）**：schema 文档/AGENTS.md 中词表引用全部指向 T1 登记表，不再内嵌复制值。

## 批量清理（纯 M 成员）

- F220（VALID_BASIS/VALID_SEVERITY 死常量删除，随 T2）、F221（ScoreReport 双定义合一）、F336/F352（chapter=0 vs None 语义分裂——统一 None 并在词表登记"genesis 语义"）、F441（score checker check id 补技能前缀，归入 id 命名词表）、T302（extract_h2_sections 与 lint 匹配语义统一——由 C2 T4 承接，此处登记）、T911（novel.json status 若确认无读写方则删字段，归 C37 联动）。

## 验收标准

1. `uv run python tools/lint_status_strings.py` 对生产树（novel-output/xinghuo-ranqiong）与 repo 全量执行：exit 非 0 且报告越表值清单（T905 断言——当前实跑 0 违规是假阴性）；修复后 exit 0。
2. `python3 -c "..."` 复算 revision-decisions severity 越表率（T903 口径）：21.1% → 0%。
3. `git grep -rn "HARD_FAIL" src/` 零残留或仅 enums.py/登记表出现（F402/F711 断言）。
4. T1 登记表 36+5 域每域有主词表与读写方（机械对照 T9 矩阵）。
5. `just check` 全绿。

## 风险与回滚

- 风险：收编改变序列化值会破坏存量 state JSON/trace 兼容（complete→completed 类）——读方保留双形兼容层一个版本周期；HARD_FAIL 改值影响下游消费方（若有），先 grep 消费面。
- 回滚：T2 每概念独立提交；lint（T3）先 WARN 周期再 FAIL，可独立 revert。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C8（24 条，代表 F210）：

F210 F211 F220 F221 F336 F352 F402 F441 F447 F514 F711 F1016 T302 T901
T902 T903 T904 T905 T906 T907 T908 T909 T910 T911
