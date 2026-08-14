# 全项目深度审查 Prompt 设计（full-project-audit-prompt）

> **Date:** 2026-08-13
> **Status:** Design（v1 已交付并执行一轮完毕；**v2 修订记录见 §0，v3 修订记录见 §0.1**）
> **Severity:** 🟠 High（工程卫生总审查的执行载体；其产出的每一条 finding 是后续所有修复 spec 的来源）
> **方法:** `brainstorming`（已完成）→ 本文档 → **直接编写 prompt 文档**（用户 2026-08-13 更正：superpowers skill 可作为**可选增强**用于提升审查/spec 质量；仍不走 writing-plans、不用 SDD 流程）
> **系列:** 2026-08-13 全项目审查（总纲；本 spec 只设计**审查 prompt 文档本身**，不包含审查执行）
> **依赖:** `single-model-sdd-prompt.md`（仅作 Iron Law / 反合理化表的**风格先例**）；superpowers skill 白名单（可选增强，见 prompt §1.5 映射）；repo spec 约定（specs/INDEX.md 登记、archive 流程）；AGENTS.md（三层测试、G0-G7、decisions-sidecar、字段级 reads、G0.9 fixture 真实性——prompt 的执行依据）
> **范围:** 交付物为 `docs/superpowers/full-project-audit-prompt.md`。审查执行、findings 修复、子 spec 产出**均不在本 spec 范围内**——它们是该 prompt 被执行后的产物。执行者：任意有文件读写 + 命令执行能力的会话；子 agent 派发为**可选**能力，无则串行。
> **核心洞察（决定本 spec 框架）:** 用户已明确**无时间盒**、"最深入最广"。无时间约束的审查必须由**完备性门驱动而非时钟驱动**——否则要么无限审、要么执行者自我妥协降级为抽样。全量深读 65K 行 Python + 74 skills + 200 docs + 独立复核的诚实代价是串行 100+ 小时 / 并行墙钟 20-40 小时、跨 10-20 个会话，因此**可恢复性是第一公民**，且执行者**不得自行宣布完成**（最终"够了"由人类拍板）。

---

## 0. v2 修订记录（2026-08-13，人类指示；交付物 `full-project-audit-prompt.md` 已同步升级为 v2）

v2 由一轮独立评审驱动（评审结论：wide ≈ 90/100、deep ≈ 88/100；v1 存在 1 个自身机制 bug、2 个结构性盲区、若干维度缺失）。逐条变更如下，prompt 中对应位置在括号内：

### A. 审计机制自身修复（v1 的洞，最优先）

| 编号 | v1 问题 | v2 修复 |
|---|---|---|
| A1 | **并行 agent 写同一报告文件会互相覆盖**：Z7/Z8 拆多 agent 并行，但 §5 模板要求"追加写入 `zone-reports/Z<N>.md`"——Write 是全量覆盖，并行写 = 互相抹除，且协调者会误判"假深读/报告缺失" | 写隔离（铁则 6 + §4 阶段 2 写协议）：每 agent 只写独立段文件 `Z<N>.<seg>.md`，协调者收齐后合并为 `Z<N>.md` 才进复核；并行上限 ≤6；模板同步改为段文件 |
| A2 | **G2/G4 收敛判据"0 新 C/I"依赖严重度判定，而严重度无决策表**：复核 agent 可把新发现压成 M 宣称收敛（可游戏化）；阶段 4 校准升级严重度不会触发重审 | ① 收敛判据收紧为 **0 新 finding（含 M）**（G2/G4/原则 5）；② 新增 **§8.1 严重度决策表**（P0/P1/P2/M 触发条件 + 5 条判定规则），子 agent 派发时完整内联；③ 铁则 5：复核无权单方降级初审严重度（异议交协调者裁决）；④ 阶段 4 校准**升级** → 该区/线程强制补复核 |
| A3 | **G6 meta-audit 的 ≥20% 抽样方法未指定**：执行者自选样本 = 挑容易的过 | 抽样种子阶段 0 预先登记（§2 + §7.1 progress.md schema）：固定随机种子 + 按区成层 + 高风险区（Z3/Z4/Z5/Z11）与低置信度文件必抽；假深读判定规则明确（3 条）+ 结果落 `meta-audit.md` |

### B. Wide 维度补充（v1 缺失）

| 编号 | v1 缺失 | v2 补充 |
|---|---|---|
| B1 | **安全维度整体缺席**（D1 禁用模式 grep 不是安全审计；11 条线程无一条安全） | 新线程 **T12 安全**（凭证泄露/命令注入/路径遍历/prompt injection 面/敏感数据落盘）+ D1⑧ 凭证扫描（git 全历史 + 工作树）+ 阶段 1 维度 8 + 通用 rubric 维度 9 安全初查 + findings 类别新增 `security` + 白名单新增 `superpowers:security-review` |
| B2 | **依赖与供应链**：仅"锁定卫生"一句话 | 新线程 **T13 依赖与供应链**（D1⑨ 漏洞清单核实/未使用依赖/重型依赖必要性/许可证/uv.lock 可复现/`.venv` 漂移/plugins 依赖面）+ D1⑨⑩⑫（uv audit、deptry/uv tree 初判、uv lock --check）+ findings 类别新增 `deps` + 阶段 1 维度 7 |
| B3 | **前序审计未播种**：08-01 确定性技能替换 audit-design（self 标注"单候选 payoff 最高"）在 T1-T11 完全缺席 | 新线程 **T14 确定性技能替换**（承接 Z8 候选初筛；用 `skill_utils/` 9 先例判据逐候选 payoff 数值化）+ Z8 增加候选初筛维度 |
| B4 | **被跳过测试无处置要求**（v1 执行 2814 passed + 214 skipped） | D1⑪ skip/xfail 清点（`pytest --collect-only`）+ Z7 逐条处置规则（keep/enable/stale/masking；masking=P1、stale=P2） |
| B5 | **覆盖率缺口无处置要求**（85.14% 的缺口只用于排序） | D1⑥ 输出每文件未覆盖行清单 + 通用 rubric 维度 8 逐行处置（dead-code / must-test / acceptable(理由)） |
| B6 | **git 考古缺席**（churn 只用于排序） | 新线程 **T15 git 历史考古**（revert 周期/未完成迁移/孤儿分支/churn 簇/大文件入库/历史凭证转 T12） |

### C. Deep 维度加强（v2 变更）

- **T11 扩展**：并发运行时压力（重复并发运行观察竞态）、运行时幂等核验（同一 phase 两次跑产物 diff）、同 seed 全 pipeline 重跑确定性（关键产物 hash）、flaky 抽检（核心子集重复 ≥3 次）、mutmut 扩至全部 gate checkers + scoring/contracts 确定性助手（量小模块全跑）；
- **T10 扩展**：补充 torch-bump 处置 follow-up 核验（INDEX 历史 #3）；
- **D2 修正自相矛盾**：原"100% 文件"却含"漂移抽查"——v2 明确穷举项（契约图闭包/import 环/死代码/重复块/SKILL.md 元数据）与抽样项（文档漂移，规则固定：每文档 ≥5 引用 + 高风险文档全查，清单阶段 0 登记）；
- **阶段 4 与 G6 职责区分**：原两处"≥20% 抽查 per-file 报告"完全重复——阶段 4 = findings **结论**核实（≥10%，抓结论与证据脱节）；G6 = per-file 报告**真实性** meta-audit（≥20%，抓假深读）；两套抽样独立、种子均预先登记。

### D. 其他

- **表 A 新增 `self-artifact` 处置**（仅限 `$AUDIT_DIR` 自身文件）：审计过程中持续变化，不参与 Z9 深读，由 G6 + 阶段 6 自检覆盖（每文件须有 meta-audit 记录链接）；
- 阶段 2 可选 scribe agent 机械录账（协调者上下文压力缓解，核实权不变）；
- 阶段 4 末可选人类中间简报（不替代 G7）；
- 阶段 1 审查维度 6 → 8（新增依赖与供应链顶层、安全顶层）；
- 反合理化表 +6 行（M 游戏化 / 并行写文件 / 校准升级 / skip 处置 / workflow 豁免 / 抽样挑选）；
- §9 恢复协议新增 prompt 升级处理（v1→v2：恢复时补跑 D1 ⑧-⑫ 再进阶段 2）；
- §11 成本更新（线程 15 条；D1 新增扫描分钟级）。

---

## 0.1 v3 修订记录（2026-08-15，人类指示；交付物 `full-project-audit-prompt.md` 已同步升级为 v3）

v3 是对 v2 的**实证修复版**：每条机制变更对应 2026-08-14 执行 run（`audit-runs/2026-08-14/`）暴露的一个具体缺陷，而非新一轮先验评审。逐条变更如下（prompt 中对应位置在括号内）：

### A. 审计机制自身修复（源自 run 复盘，最优先）

| 编号 | v2 实证缺陷（2026-08-14 run 证据） | v3 修复 |
|---|---|---|
| A1 | **G4"唯一终止条件 = 本轮 0 新 finding（含 M）"实际不可达**：Z2/Z3/Z4/Z6 四区结束轮仍有 1-4 条新 finding，全部按人类"无新 P0/P1"豁免放行——豁免无记录标准、无披露义务 | **G4 双轨收敛**：硬收敛（连续 2 轮 0 新含 M）自动通过；软收敛（连续 3 轮无新 P0/P1 且每轮新增 ≤3）须三件套——轮次计数证据 + 残余风险清单 + 阶段 4 简报/G7 人类追认；含未解 P0 的区禁用软收敛（§3 G4） |
| A2 | **"单调下降、不降反升必须查明"被反复违反且零次查明**：Z1 5→6、Z3 8→11、Z4 6→10、Z5 4→8、Z6 3→1→3，progress/final-report/meta-audit 中"单调"零次出现 | **波动条款**：承认波动是 fresh-context 重审的正常产出，义务从"查明"降为"当轮记一行波动分析"（发现角度/上轮漏因）；累计 2 次同盲区 → 强制新角度轮（§1 原则 5） |
| A3 | **完备性实际靠人类补洞**：收敛出 final-report 后，人工指示的 7 项后续扫描仍产出新 finding（F1322）与新确认——新攻击角度 > 重复重读，但 v2 无角度机制 | **§3.5 攻击角度库**：收录 7 项实证有效角度 + 4 个泛化模板；每轮复核强制声明 ≥1 个本轮新增角度，连续两轮不得复用；起步清单用尽后才允许模板派生（§3.5、§4 阶段 2） |
| A4 | **G5 等式"ledger 条目数 == 子 spec 文件数"设计错误**（M 批量/merged 语义下不成立：786 findings vs 23 specs），实际执行阶段 5 只覆盖 10/118 P1，靠人工续会话补齐 8 份 spec 才闭合 | **G5 重写为"产出与对账"**：(a) findings↔spec 语义覆盖 grep 命令（已在真实 786 条台账实测输出空）(b) INDEX↔磁盘↔总纲三方对账 + ID 唯一性命令 (c) spec 自审保留；铁则 6 禁手抄数字（§3 G5、§0 铁则 6） |
| A5 | **G6 有效深核率被隐性稀释**：登记 552 样本（达标 ≥20%），实际逐条深核 228 条（≈8.3%），稀释恰在 Z7（tests）与 Z11（运行时产物）两个最大区，final-report 未披露分母落差 | **G6 分层深核下限**：Z1-Z6/Z8-Z10 全样本、Z7 ≥35%、Z11 ≥25% 条目级 + 全量类别级计数复演；低于下限 = BLOCKING deviation；final-report 强制披露三重分母（逐条深核数/登记样本数/总文件数）（§3 G6、§4 阶段 6） |
| A6 | **final-report 手抄统计漂移**：报告写 781，台账实际 786；机械统计还暴露 6 条词表外严重度行 | **机械统计强制**：统计数字一律由内联 awk/grep 命令产生并粘贴输出；词表外严重度行 = 台账格式缺陷先修再报；ledger 严重度单元格限 P0/P1/P2/M 四字面量（§4 阶段 6、§7.2） |
| A7 | **测量装置被测量污染**：审计期间 coverage.xml 2 次被并行测试覆写（D1-02 族） | **原则 7 测量装置隔离**：COVERAGE_FILE 独占 + 除 T11 外禁止并发 pytest；D1⑥ 同步（§1 原则 7、§2 D1⑥） |
| A8 | **只读审计的根因不可实验验证但无分级**：根因聚类纯推理，下游 spec/SDD 无从区分可信度 | **根因证据等级标注**：每条根因标 `实验佐证`（附命令+输出）或 `推理假设`；SDD 阶段 1 驳斥门优先核验推理假设级；v2"可选简报"升级为触发式强制（findings ≥300 或任一软收敛区）（§4 阶段 4.3/.5、§8） |

### B. Wide 维度补充（v3 新增）

| 编号 | v2 缺失 | v3 补充 |
|---|---|---|
| B1 | **计算/内存/IO 性能整类缺席**（v2 仅 token 成本有 T4/T14；通用 rubric 9 维度无一涉及复杂度；T11 只跑既有 benchmark——无 benchmark 的性能退化无机制可发现） | 新线程 **T16 性能与资源效率**：热路径复杂度标注（每章循环体）/ cProfile 实测 / 内存生命周期 / IO 重复读写 / 启动 import 面 / **步骤复用与重复 dispatch 指纹去重（对 Z11 实际 dispatch 记录统计相同 skill+相同上下文指纹的重复派发与 memoization 命中率）**；每条性能 finding 必附增长曲线断言（§6 T16） |
| B2 | 通用 rubric 无性能维度 | **通用维度 10 复杂度与资源效率**（轻量必查，深查归 T16）；阶段 1 新增维度 9 性能顶层设计（§5、§4 阶段 1） |
| B3 | **运行时路径无离线验证手段且未被声明为缺口**（实况：`internal` 模式硬拒绝、`trace/replay.py` 为签名链校验——无可用的离线派发模式） | **T11 stub 实机 smoke**：grep 离线模式，有则 1-3 章迷你 pipeline 实跑全链；无则记 P2 可测性 finding + final-report 遗留风险声明（§6 T11；§8.1 P2 典型例子加"可测性缺陷"） |
| B4 | T10 回归核验源不含既往审计产物 | T10 核验源扩展：archive spec / INDEX / **既往 `audit-runs/*/final-report.md` 修复声明**（§6 T10） |

### C. 诚实边界与防偷懒

- **§0 任务节新增"诚实边界"声明**：本 prompt 保证过程完备（每文件处置、每声称可对账），不保证本体完备（每缺陷被发现）；G7 因此不可绕过（§0、§11）；
- 严重度表 P1 新增性能触发条件（热路径超线性致生产规模不可行）、P2 新增"增长曲线断言支撑的性能优化 / 可测性缺陷"（§8.1）；
- 反合理化表 +9 行（软收敛三件套 / 角度复用 / G6 稀释 / 手抄数字 / 波动不记 / 性能无 benchmark / 根因不分级 / stub 静默跳过 / 交互阻塞挂着等）（§10）；
- **§1.6 无人值守与非交互纪律（$UNATTENDED，人类指示补入）**：Variables 新增 `$UNATTENDED`；人类门降级语义表（阶段 4 简报→记录+默认"继续"不等待 / 软收敛追认→标待追认不阻塞 / BLOCKING deviation→子项挂起继续他项 / G7=终点停止而非卡住）；非交互纪律（timeout 包裹 + stdin 隔离 + **禁触等待人工 checkpoint decision 的真实 pipeline 入口**，交互阻塞 = P2 finding + 不可审计声明）；T11 / 阶段 4.5 / 变更注⑦ 同步（§1.6、§4 阶段 4、§6 T11）；
- §9 恢复协议新增 v3 补跑项（未收敛区改双轨判定 / 阶段 5 补 G5 对账 / 补 T16 / final-report 按机械统计重出）（§9）；
- progress.md schema 新增软收敛登记表与波动分析登记表（§7.1）。

---

## 1. 背景与目标

### 1.1 用户需求（已确认，逐字对齐）

1. **先创建 prompt 文档**（本 spec 的交付物），随后按该 prompt 独立执行审查。
2. 审查范围：**整个 shenbi 项目**——从整体（架构、契约、pipeline、gates、CI、文档体系）到细节（每文件逐项）。
3. 目标：找出**所有错误和优化点**（bug / 契约违反 / 不一致 / 浪费 / 架构债 / 测试失效 / 文档漂移……）。
4. 产出：**每个 finding 一个独立 spec**，遵循 repo spec 约定；**minor issue 可合并**为一个批量 spec（用户 2026-08-13 补充确认）。
5. **不限制审查时长**；要求最深入、最广的审查。
6. **只审不修**：执行者不修复任何问题，修复留给后续 spec→plan。
7. **skill 可选增强 / 无 SDD**：prompt 机制自包含为基线（无 skill 环境可执行）；superpowers skill 按白名单表可选使用以提升审查/spec 质量（用户 2026-08-13 更正）；不走 SDD 流程。

### 1.2 关键设计张力与裁决

| 张力 | 裁决 |
|---|---|
| "逐项检查" vs 65K 行代码 | 三层覆盖模型（§4）：机械层与模式层 100% 文件覆盖，语义深读层扩至**全部文件**（per-file 报告），台账消除 sampled 兜底 |
| 无时间盒 vs 无限审 | 完备性门 G1-G7（§5）是唯一终止条件；每轮必须增量收敛（新 C/I 数单调下降），最终人类裁决 |
| 深读真实性 vs 假深读 | per-file 报告必须列**声称检查的不变量清单** + 验证命令输出；独立复核 agent + meta-audit 抽查抓假 |
| 多天多会话 vs 上下文丢失 | checkpoint commit + tracked 审计状态目录 + resume 协议（§10） |
| 并行提速 vs 审查独立性 | 审查全程**只读**（只写各自报告文件），zone 子 agent 可并行派发；复核与初审分离、协调者逐条核实 |
| skill 可选 vs 机制完整性 | Iron Law / 反合理化 / 独立复核全部**内联自包含**（无 skill 环境可执行）；superpowers skill 按 prompt 内白名单表作可选增强——增强非替代，使用必粘贴输出，白名单外禁止 |

---

## 2. 交付物

`docs/superpowers/full-project-audit-prompt.md`——中文、**自包含基线**的自治执行 prompt：机制全部内联（无 skill 环境可执行）；superpowers skill 作为白名单**可选增强**（提升审查/spec 质量，增强非替代，用户 2026-08-13 更正）；不含 SDD 机制。只依赖执行会话的通用能力（文件读写、命令执行、可选的子 agent 派发）与 repo 的 AGENTS.md。与 `single-model-sdd-prompt.md` 同目录同风格（仅风格，非机制）。其结构 TOC 见 §11。

---

## 3. Prompt 的总体流程：漏斗 7 阶段（完备性门驱动，无时间盒）

```
阶段 0 清点与基线 ──► 阶段 1 整体层审查 ──► 阶段 2 全量分区深度审查（并行只读）
                                                    │
  阶段 6 覆盖证明 + meta-audit ◄── 阶段 5 spec 产出 ◄── 阶段 4 根因聚类 ──◄─ 阶段 3 跨模块线程（与 2 交错）
```

| 阶段 | 内容 | 退出条件（门） |
|---|---|---|
| 0 清点与基线 | 生成全文件清单台账；跑 D1 机械基线（`just check` 全套 + tools/ 全部 lint 脚本 + 74 个 SKILL.md frontmatter 解析 + G2/G4 校验 + coverage 报告），记录 **pre-existing 失败基线** | G1 台账建成 + D1 基线归档 |
| 1 整体层审查 | 架构一致性（AGENTS.md 声明 vs 实际）、契约单一信源体系、pipeline 状态机设计、G0-G7 体系、CI 设计、文档体系——找**系统性**错误 | 每项有结论（通过/问题→findings） |
| 2 分区深度审查 | Z1-Z11 十一区，每区一个 fresh-context 初审 agent **并行只读**深读，产出 per-file 报告 | 每区报告含**全文件** per-file 条目（G1） |
| 3 跨模块审计线程 | T1-T11 十一条横切线程，每条一个 fresh-context agent，读全部相关文件，产出线程报告 | 11 线程报告齐全 |
| 4 根因聚类 | 跨区去重（同根因→合并）、严重度校准 P0/P1/P2/M、根因簇图、抽查复核（fresh-context agent 抽查 20% 分区结论 vs 真实文件） | findings ledger 无重复根因 + 严重度已校准 |
| 5 spec 产出 | 总纲 catalog spec + 每 finding 独立子 spec + INDEX 登记 | G5：ledger 条目数 == spec 文件数 |
| 6 覆盖证明 + meta-audit | G1 台账零未处置文件；G2 复核收敛；meta-audit 审审计（抽查 per-file 报告 vs 真实文件）；总结报告 → **人类裁决** | G1-G6 全过 + 人类说"够了"（G7） |

阶段 2 与阶段 3 可交错（线程可随分区并行派发）；其余严格串行。

---

## 4. 覆盖模型：三层 D1/D2/D3 + 覆盖台账

| 层 | 内容 | 覆盖保证 |
|---|---|---|
| **D1 确定性机械层** | `just check` 全套（contract lints ×3 + ruff + format + mypy + basedpyright + sync-contracts 幂等 + pytest 双 pass）+ tools/ 其余脚本（`audit-skill-descriptions.py`、`check_fixture_mirror.py`、`lint_no_forbid_with_computed_field.py`、`lint_no_fs_mutation.py` 等 13 个）+ 全部 74 个 SKILL.md frontmatter 解析 + G2/G4 校验全部 fixtures/skills + 禁用模式 git grep（bare except / print() / pickle / TODO-FIXME-HACK）+ pytest `--cov` 缺口报告 | **100% 文件**，机器穷举；输出归档为 `d1-baseline.md`（含 pre-existing 失败，与审查新增发现分离） |
| **D2 结构化模式层** | 契约图闭包与 reads/writes 接线 vs deps.json、import 环、死代码、重复块、文档↔代码 file:line 漂移、SKILL.md 元数据一致性（name/description ≤500 字符规则/kind/reads） | **100% 文件**，grep/脚本模式可达 |
| **D3 语义深读层** | 每文件人工语义审查：逻辑正确性、设计质量、边界条件、错误处理、测试真实性。**不抽样**——全文件深读 | **100% 文件**（生成物目录除外，见 §4.1） |
| **D4 运行时产物与日志层** | 磁盘未跟踪执行产物的清点与审计：`novel-output/`、`truth/`、`.superpowers/`、`*.log`、`.hypothesis/examples/`（真实运行证据——novel-output 的 .gitignore 注释明示其为 auditable pipeline verification）；日志 grep 异常；sdd 历史已知问题转 pre-seeded findings | **100% 磁盘执行产物**（构建产物/工具缓存除外） |

**覆盖台账（G1 的载体，双表）**：

- **表 A · tracked**（`git ls-files`，当前 2736 文件）：每文件一条处置，唯一合法值 `deep-read`（链接 per-file 报告）。
- **表 B · 磁盘执行产物**（阶段 0 `find` + `git status --ignored` 清点）：`audited`（链接 D4 报告）\ `generated-excluded(理由)`（仅可再生成的构建产物 dist/site）\ `cache-ignored`（工具缓存，验证 .gitignore）。

不存在 `sampled`。两表零未处置是阶段 6 的硬门。

### 4.1 D3 排序（派发顺序优化，非覆盖裁剪）

虽然全文件深读，但**派发顺序**按风险加权：(a) postmortem 聚集区（pipeline / gates / contracts / cost——CN3 覆盖 bug、TokenLedger dead-wire、finish_reason 盲点均在此）(b) git churn (c) coverage 缺口 (d) 复杂度。高风险区先审，使早期发现尽早进入后续阶段；覆盖不受影响。

---

## 5. 完备性门 G1-G7（唯一终止条件，取代时间盒）

| 门 | 判据 |
|---|---|
| **G1 广度** | 台账表 A 每文件 = `deep-read`；表 B 每项 = `audited` / `generated-excluded(理由)` / `cache-ignored`；两表零未处置 |
| **G2 深度** | 每区初审通过**独立** fresh-context 复核 agent（与初审分离）：复核重读全文件，0 新 Critical/Important 才算过；11 条线程报告齐全 |
| **G3 验证** | D1 全工具真实运行、输出归档（pre-existing 失败单独列）；全部 CLI 入口冒烟（shenbi-validate G0/G2/G4、shenbi-score、shenbi-phase、shenbi-dispatch dry-run 若可行） |
| **G4 收敛** | 复核轮次不设上限、重审无条件；终止条件仅为本轮 0 新 C/I |
| **G5 产出** | findings ledger 条目数 == 子 spec 文件数（M 级批量 spec 例外见 §9）；每 spec 过自审 |
| **G6 Meta** | meta-audit：fresh-context agent 抽查 ≥20% 的 per-file 报告 vs 真实文件，抓假深读/橡皮图章/覆盖空洞 |
| **G7 人类裁决** | 执行者**禁止**自行宣布"审计完成"；阶段 6 产出总结报告（覆盖数字、findings 统计、遗留风险）后停，由人类拍板结束或追加审查 |

---

## 6. 分区矩阵 Z1-Z11（阶段 2 派发单元）

每区 = 一个 fresh-context 初审 agent + 独立复核 agent；并行只读，只写各自 `zone-reports/Z<N>.md`。

| 区 | 文件范围 | 重点 rubric 维度 |
|---|---|---|
| Z1 | `src/shenbi/` 顶层 19 文件（exceptions / logging / scoring / phase_runner / status / paths / recovery / safe_write / capability_fs / cli_utils / error_guidance / sync_contracts） | 异常层次完整性、T2/T3 状态机正确性、幂等写、structlog 无 print |
| Z2 | `src/shenbi/contracts/` + `src/shenbi/dispatcher/` | 契约单一信源、字段级 reads 过滤与 escape hatch、派发协议 |
| Z3 | `src/shenbi/pipeline/` | 状态机、并发、重试、truth 写路径、token 计量（历史 P0 聚集区） |
| Z4 | `src/shenbi/gates/`（含 g4 checkers） | 门幂等、decisions.json G4 schema、P2.5 rationale 规则 |
| Z5 | `src/shenbi/audit/` + `cost/` + `orchestration/` | TokenLedger 接线、审计波调度、成本计量 |
| Z6 | `records/` + `trace/` + `text/` + `config/` + `plugins/` + `skill_utils/` | 确定性助手正确性、序列化、配置治理 |
| Z7 | `tests/` 16 子目录（unit / gates / pipeline / integration / contracts / tiers / skill-behavior / skill-triggering / property / benchmark / pressure-tests / coverage / golden / baselines / fixtures / rounds） | 测试真实性（L4 无纯 mock）、fixture 真实性（G0.9）、覆盖缺口、测试自身 bug |
| Z8 | `skills/` 74 个 skill（SKILL.md 全文 + 附属文件） | 触发条件 description ≤500 字符、DOT 流程图与正文一致性、decisions 声明、reads 字段声明 vs truth 文件实况 |
| Z9 | `docs/` 200 md（framework / architecture / superpowers/specs+plans+archive / ADR）+ 根级 AGENTS.md / README / 其余根 md | 文档↔代码漂移（file:line 引用抽查）、INDEX 一致性、spec 间矛盾 |
| Z10 | `.github/workflows/` 8 个 + `pyproject.toml` + `justfile` + `uv.lock` + `tools/` 13 脚本 + `scripts/` + `plugins/master.json` + `benchmarks/` + `executor_config.toml` + `goal-prompt.md` + `command-to-give.md` + `run_pipeline.sh` + `mkdocs.yml` + `cliff.toml` | CI 与 just check 一致性、脚本正确性、配置漂移、meta-prompt 自身（含 single-model-sdd-prompt.md） |
| Z11 | **磁盘执行产物**（清单 = 台账表 B）：`novel-output/`（test-validation / validation-results / xinghuo-ranqiong 真实运行）、`truth/`、`.superpowers/sdd*`、`*.log`（先读 `src/shenbi/logging.py` 定位日志汇） | 产物与 pipeline 不变量一致性、decisions.json 真实数据 schema/P2.5、日志异常（ERROR/traceback/retry/429/finish_reason）、sdd 历史已知问题转 pre-seeded findings |

子 agent prompt 必须**内联完整 rubric**（fresh-context 子 agent 看不到本 prompt 文件，禁止只引用章节名——沿用 single-model-sdd-prompt.md 的注入规则）。

---

## 7. 跨模块审计线程 T1-T11（阶段 3，第一公民）

每条线程一个 fresh-context agent，读全部相关文件横切审查；与分区并行派发。

| 线程 | 内容 | 依据 |
|---|---|---|
| T1 | decisions-schema v1 全链合规：producer 写入 vs consumer 读取 vs G2（file_type=decisions）vs G4（schema + P2.5 rationale 规则） | AGENTS.md decisions-sidecar |
| T2 | 契约单一信源：SKILL.md frontmatter ↔ deps.json ↔ docs/framework ↔ skills/ 生成物；`shenbi-sync-contracts` 幂等 | AGENTS.md + PR #17 |
| T3 | 字段级 reads 过滤 + escape hatch：dispatcher 实现 vs 契约声明；缺字段回退全文件 + WARN 日志是否真实存在 | AGENTS.md 字段级 reads |
| T4 | TokenLedger 接线：计量代码存在但未接线（dead-wire 模式，PR #39 先例） | 历史 postmortem |
| T5 | 重试经济与错误处理：error_handler 重试参数、异常层次、bare except、finish_reason 处理 | PR #40 先例 |
| T6 | 并发与序列化安全：ProcessPool / threading / multiprocessing 的 pickle 边界、共享状态 | single-model-sdd-prompt 文件级检查表 |
| T7 | truth 文件写路径幂等：覆盖 vs 追加、upsert 键唯一性（CN3 先例） | 归档 postmortem |
| T8 | fixture 真实性：G0.9 禁止手写 mock；fixtures 必须为真实输出或上游生成副本 | AGENTS.md fixtures |
| T9 | 枚举/状态字符串单一信源：`contracts/enums.py` 唯一定义；lint_status_strings 覆盖范围是否有洞 | PR #19 集群 |
| T10 | 历史修复回归核验：archive spec / INDEX 全部"已修(PR #N)"声明逐一 grep 修复签名是否仍在当前代码（TokenLedger 接线、finish_reason 检测、truth_io upsert 调用方全覆盖）；消失 = 回归 | 归档 spec P0 声明 |
| T11 | 运行时行为核验：实际运行 pressure-tests / benchmark（对比 baselines）/ golden / 差分测试；3-4 关键模块跑 mutmut 突变测试；重放 .hypothesis/examples/ 失败样本 | pyproject `[tool.mutmut]`、tests 分层 |

---

## 8. 报告与台账 schema（写入 tracked 审计目录）

审计状态目录：`docs/superpowers/audit-runs/2026-08-13/`（tracked；每阶段 checkpoint commit）：

```
audit-runs/2026-08-13/
├── progress.md            # 阶段状态机 + 每会话 resume 点（权威恢复入口）
├── coverage-ledger.md     # G1 台账：全文件 → 处置 + 报告链接
├── findings-ledger.md     # 唯一权威 findings 表（见下）
├── d1-baseline.md         # D1 工具输出归档 + pre-existing 失败
├── zone-reports/Z1.md … Z10.md
├── thread-reports/T1.md … T9.md
└── final-report.md        # 阶段 6 总结（覆盖数字/findings 统计/遗留风险）
```

**per-file 报告条目**（zone/thread 报告的主体）：

```markdown
### <file path>
- 处置: deep-read | generated-excluded(理由)
- 审查者: <agent 标识>  | 复核: <复核 agent 标识 + 结论>
- 声称检查的不变量: [列表——写文件时应检查的具体不变量]
- findings: F<NNN> …
- 验证命令: [本文件相关的实际命令 + 输出摘要]
- 置信度: high | medium | low（low 必须说明原因）
```

**findings ledger 条目**（`findings-ledger.md` 每行一条，唯一权威）：

| 字段 | 说明 |
|---|---|
| ID | F<NNN> 递增 |
| 标题 | 一句话 |
| 类别 | `error`（bug/契约违反/不一致/测试失效）\| `optimization`（性能/token/架构/可维护） |
| 严重度 | P0（立即）/ P1（高）/ P2（中）/ M（文案类 minor） |
| 证据 | file:line ×N（每条必须真实验证过） |
| 根因 | 根因级描述（聚类去重键） |
| 验证 | 已运行命令 + 输出摘要 |
| 影响 | 质量/成本/维护影响 |
| 建议方向 | 修复方向一句话（完整方案留给 spec） |
| 状态 | `open` → `verified`（协调者核实）→ `merged-into-Fx`（去重合并）→ `specced`（spec 已产出） |
| 深度标注 | deep-read / tool-only（D1 发现） |

---

## 9. Spec 产出契约（阶段 5）

- **单位 = 根因**：同一根因的多处表现合并为 1 个 spec（findings 表内列全）；不同根因不同 spec。
- **严重度规则**：P0/P1/P2 每个根因一个独立子 spec；M 级（错别字/命名不一致等文案类）合入单一批量 spec `2026-08-13-minor-findings-batch-design.md`（按区分节）——避免数十个单行 spec 噪音。
- **文件**：`docs/superpowers/specs/2026-08-13-<slug>-design.md`，头部块 `Date/Status/Severity/方法/系列/依赖/范围/核心洞察`；每条 finding 含 症状/证据 file:line/根因/分类/影响/假设+验证命令/修复方向/数值化标准（沿用现有 audit spec 格式）。
- **总纲**：`2026-08-13-full-project-audit-design.md`（catalog：每 finding 一行 + 根因簇图 + 建议执行顺序 + 覆盖统计）。
- **INDEX**：登记 1 总纲 + N 子 spec；`#NN` 顺序号按现有队列续排。
- **只审不改**：全程唯一可写的是审计目录 + specs/ + INDEX.md；src/tests/skills/docs 正文零修改，修复一律留给后续 spec→plan。

---

## 10. 防偷懒机制与 Anti-Rationalization 表

1. **Iron Law（每条消息级）**：任何含"通过/完成/无问题"字样的消息，其验证命令必须在同一条消息内运行过并粘贴输出。
2. **审查独立性**：初审 / 复核 / 协调者核实三层分离；复核是**全量重读**，非 diff 抽查；"协调者核实过即免独立复核"= 禁止。
3. **rubric 内联**：子 agent prompt 复制完整 rubric，禁止只引用章节名。
4. **meta-audit**：G6 抽查 ≥20% per-file 报告 vs 真实文件。

| 模型可能说 | 回应 |
|---|---|
| "时间不够，这区抽样吧" | 禁止。无时间盒，抽样概念不存在（§4 台账无 sampled）。 |
| "工具绿了 = 没错误" | 禁止。D1 只是基线；语义错误跑不出来。 |
| "已经审过 3 轮了" | 唯一终止条件：本轮 0 新 C/I（G4），且每轮新 C/I 数必须单调下降并记录。 |
| "这文件一看就是样板，快速过" | 禁止。per-file 报告必须列声称检查的不变量，写不出来 = 没审。 |
| "子 agent 报告成功" | 协调者逐条打开真实文件核对 findings，不轻信。 |
| "生成物目录可以整目录跳过" | 必须逐个声明 `generated-excluded` + 再生成性验证 + 理由。 |
| "审查完成" | 禁止自宣完成。G1-G6 全过 + 人类裁决（G7）。 |
| "发现太多先记着后面写" | 发现即录入 findings ledger（当轮），禁止内存暂存。 |

---

## 11. 交付物 prompt 文档 TOC

`docs/superpowers/full-project-audit-prompt.md` 结构：

1. 标题 + Variables（日期、审计目录路径）
2. 核心原则（Iron Law / 只审不改 / 完备性门驱动 / 审查独立性 / 可恢复）+ skill 白名单（可选增强映射表）
3. 覆盖模型三层 + 台账规则（§4 内容）
4. 完备性门 G1-G7 表（§5 内容）
5. 阶段 0-6 流程（§3 内容；每阶段：输入、动作、退出条件；skill 增强点见白名单表）
6. 分区矩阵 Z1-Z10（§6 内容，含每区文件 glob + rubric 内联模板）
7. 跨模块线程 T1-T9（§7 内容）
8. schema 三件套（per-file 报告 / findings ledger / coverage 台账模板，§8 内容）
9. spec 产出契约（§9 内容）
10. checkpoint/恢复协议（checkpoint commit 时机、resume 第一步 = 读 progress.md、会话间状态交接）
11. Anti-Rationalization 表（§10 内容）
12. 成本预期与诚实声明（串行 100+ 小时 / 并行墙钟 20-40 小时、10-20 会话；禁止中途自我降级）

---

## 12. 本 spec 的验证标准

| 标准 | 判据 |
|---|---|
| 设计↔prompt 映射 | prompt 文件包含 §11 全部 12 节，且 G1-G7 / Z1-Z10 / T1-T9 / 三 schema / 反合理化表**逐项在 prompt 中可找到对应机制** |
| 无占位符 | prompt 中无 TBD/TODO/待定 |
| 自包含基线 | 新会话只读 prompt + AGENTS.md 即可**无 skill** 完整执行；skill 引用仅存在于白名单表（增强非替代）与否定声明中 |
| repo 惯例 | 遵循 spec 头部块、INDEX 登记、Conventional Commits |

---

## 13. 依赖关系图

```
single-model-sdd-prompt.md（仅风格先例：Iron Law / 反合理化）
        │
        ▼
本 spec（prompt 文档设计）──► 直接编写 full-project-audit-prompt.md（无 writing-plans）
        │
        ▼（prompt 被执行后，另起会话）
审计执行（阶段 0-6，完备性门驱动，产出 audit-runs/2026-08-13/）
        │
        ▼
1 总纲 catalog spec + N 子 spec（每 finding 一个）→ INDEX 登记 → 各自走 plan → 实施
```
