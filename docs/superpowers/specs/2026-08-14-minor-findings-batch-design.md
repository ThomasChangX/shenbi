> **Date:** 2026-08-14 | **Status:** Revised (2026-08-30 · SDD #16 价值门收窄：41 条无主残留执行；6 条已修核销 F166/F344/F509/F618/F0-04/F3B3；82 条移交活跃簇 spec——移交清单见 .superpowers/sdd-archive-stats-determinism 同批归档注记与执行 PR；F478→#27、F3A1→#27、F351→#47、F270→#46、F653→#32) | **Severity:** ⚪ M | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** 全仓库 | **核心洞察:** 98 条 M 级文案/命名/格式/过期注释批量清理（实际唯一 ID ~132，收窄后 41）

# M 级批量 spec（按区分节）

## Z1（src 顶层）
- F110 "1 source files changed" 语法、F111 forwarder 过期注释、F159 sync_contracts 缺 configure_logging、F160 emit_json BrokenPipe、F162 冗余 configure_logging、F165 T2-only 承诺、F166 skill 参数穿越、F157 交互 stdout 污染、F151 非数字键静默、F152 kill-switch 解析、F153 render_body_view 死参数、F136 CommandResult 死成员、F127 ScoringStatus 死成员、F138 死 log、F139 子模块清单 6/12、F155 NaN 双函数、F146/F147 损坏 JSON、F164 裸 GateStatus

## Z2（contracts/dispatcher）
- F226 prompt 可选 vs codex 必填、F263 frontmatter 锚定、F264 H2 折叠、F265 None 哨兵、F267 argv 截断、F268 逗号拼接、F270 ledger 写无防护、F271 围栏伪 section、F258 chapter 0、F261 decisions 死常量、F251/F252 评分产物

## Z3（pipeline）
- F318 文档漂移合集、F334 编号空洞、F343 escalation chapter 0、F344 write_safety 注释、F350 无条件备份、F351 response_format、F352 timeout 死参、F361 early_stop 死参数、F362 print()、F363 触发重发、F376/F377、F390 feedback 误报、F394 reset 注释、F395 timeout 谎称、F3AA ReadLock、F3AD 锁 mkdir、F3AE status 信封、F3B0 行号引用、F3B1 degraded 字面量、F3A6 wave 裸解析、F3A7 resume 快照丢弃、F3A2 plan 自指、F3A3 state 损坏、F3AA、F3AB re.match 标题、F3AD

## Z4（gates）
- F410 SHORT_MAP、F411 missing_dirs、F412/F413 行引用、F414 HARD_FAIL、F416 枚举缺 medium、F436 planted_chapters、F438 阈值漂移、F445 unimplemented、F456 字典序（升 P2 复核）、F459/F470 等家族 M 实例、F481/F482、F490 checks 槽、F492 G0.5b、F495 证据正则、F4A1/F4A2/F4A4

## Z5（audit/cost）
- F509 幻影条目、F510 return 2、F511 归档漂移、F516 glob 处置、F530 parse_resonance 0 分

## Z6（skill_utils 等）
- F618 RHETORICAL 死字典、F623 AI 标记字面量、F629 §5.3 校验器、F639 compute_drift CLI、F653 表终止、F657 卷级排除、F658 md 重复 id

## Z7-Z11（tests/skills/docs/CI/产物）
- ## Z1 整体层（补全逐条）
- **F0-04**、**F0-08**
- ## Z1（补全逐条）
- **F126**、**F130**、**F131**、**F132**、**F142**、**F143**、**F145**、**F154**
- ## Z2（补全逐条）
- **F256**、**F257**、**F259**
- ## Z3（补全逐条）
- **F367**、**F368**、**F369**、**F370**、**F398**
- ## Z4（补全逐条）
- **F455**、**F478**、**F479**、**F480**、**F486**
- ## Z9（补全逐条）
- **F1102**、**F1103**、**F1105**、**F1106**、**F1107**、**F1108**、**F1109**、**F1110**、**F1111**、**F1112**、**F1114**、**F1115**、**F1116**
- ## Z11（补全逐条）
- **F1318**、**F1320**
- ### 线程（补全逐条）
- **T6-05**
- ### 其他（补全逐条）
- **F3A1**、**F3A5**、**F3B2**、**F3B3**、**F3B4**

## 统一修复模式
- 文案/注释/命名：直接订正；死代码：删除或标注；格式：统一
- **验收**：grep 无残留目标模式；`just check` 全绿
