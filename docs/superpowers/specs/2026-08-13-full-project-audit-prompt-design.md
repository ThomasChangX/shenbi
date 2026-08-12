# 全项目深度审查 Prompt 设计（full-project-audit-prompt）

> **Date:** 2026-08-13
> **Status:** Design
> **Severity:** 🟠 High（工程卫生总审查的执行载体；其产出的每一条 finding 是后续所有修复 spec 的来源）
> **方法:** `brainstorming`（已完成）→ 本文档 → **直接编写 prompt 文档**（用户明确：不走 writing-plans；执行时不依赖任何 superpowers skill、不走 SDD）
> **系列:** 2026-08-13 全项目审查（总纲；本 spec 只设计**审查 prompt 文档本身**，不包含审查执行）
> **依赖:** `single-model-sdd-prompt.md`（仅作 Iron Law / 反合理化表的**风格先例**，本 prompt 不引用任何 skill）；repo spec 约定（specs/INDEX.md 登记、archive 流程）；AGENTS.md（三层测试、G0-G7、decisions-sidecar、字段级 reads、G0.9 fixture 真实性——prompt 的执行依据，非 skill）
> **范围:** 交付物为 `docs/superpowers/full-project-audit-prompt.md`。审查执行、findings 修复、子 spec 产出**均不在本 spec 范围内**——它们是该 prompt 被执行后的产物。执行者：任意有文件读写 + 命令执行能力的会话；子 agent 派发为**可选**能力，无则串行。
> **核心洞察（决定本 spec 框架）:** 用户已明确**无时间盒**、"最深入最广"。无时间约束的审查必须由**完备性门驱动而非时钟驱动**——否则要么无限审、要么执行者自我妥协降级为抽样。全量深读 65K 行 Python + 74 skills + 200 docs + 独立复核的诚实代价是串行 100+ 小时 / 并行墙钟 20-40 小时、跨 10-20 个会话，因此**可恢复性是第一公民**，且执行者**不得自行宣布完成**（最终"够了"由人类拍板）。

---

## 1. 背景与目标

### 1.1 用户需求（已确认，逐字对齐）

1. **先创建 prompt 文档**（本 spec 的交付物），随后按该 prompt 独立执行审查。
2. 审查范围：**整个 shenbi 项目**——从整体（架构、契约、pipeline、gates、CI、文档体系）到细节（每文件逐项）。
3. 目标：找出**所有错误和优化点**（bug / 契约违反 / 不一致 / 浪费 / 架构债 / 测试失效 / 文档漂移……）。
4. 产出：**每个 finding 一个独立 spec**，遵循 repo spec 约定；**minor issue 可合并**为一个批量 spec（用户 2026-08-13 补充确认）。
5. **不限制审查时长**；要求最深入、最广的审查。
6. **只审不修**：执行者不修复任何问题，修复留给后续 spec→plan。
7. **无 skill / 无 SDD**：prompt 不引用 superpowers skill，不采用 SDD 流程；所有防偷懒机制在 prompt 内自包含（用户 2026-08-13 明确）。

### 1.2 关键设计张力与裁决

| 张力 | 裁决 |
|---|---|
| "逐项检查" vs 65K 行代码 | 三层覆盖模型（§4）：机械层与模式层 100% 文件覆盖，语义深读层扩至**全部文件**（per-file 报告），台账消除 sampled 兜底 |
| 无时间盒 vs 无限审 | 完备性门 G1-G7（§5）是唯一终止条件；每轮必须增量收敛（新 C/I 数单调下降），最终人类裁决 |
| 深读真实性 vs 假深读 | per-file 报告必须列**声称检查的不变量清单** + 验证命令输出；独立复核 agent + meta-audit 抽查抓假 |
| 多天多会话 vs 上下文丢失 | checkpoint commit + tracked 审计状态目录 + resume 协议（§10） |
| 并行提速 vs 审查独立性 | 审查全程**只读**（只写各自报告文件），zone 子 agent 可并行派发；复核与初审分离、协调者逐条核实 |
| 无 skill / 无 SDD vs 防偷懒 | Iron Law / 反合理化 / 独立复核全部以**纯文本**内联进 prompt；执行者只用会话通用能力（文件 / 命令 / 可选子 agent 派发，无则串行） |

---

## 2. 交付物

`docs/superpowers/full-project-audit-prompt.md`——中文、**完全自包含**的自治执行 prompt：不引用任何 superpowers skill、不含 SDD 机制；只依赖执行会话的通用能力（文件读写、命令执行、可选的子 agent 派发）与 repo 的 AGENTS.md。与 `single-model-sdd-prompt.md` 同目录同风格（仅风格，非机制）。其结构 TOC 见 §11。

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
| 2 分区深度审查 | Z1-Z10 十区，每区一个 fresh-context 初审 agent **并行只读**深读，产出 per-file 报告 | 每区报告含**全文件** per-file 条目（G1） |
| 3 跨模块审计线程 | T1-T9 九条横切线程，每条一个 fresh-context agent，读全部相关文件，产出线程报告 | 9 线程报告齐全 |
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

**覆盖台账（G1 的载体）**：`git ls-files` 全清单（当前 2736 文件），每文件恰好一条处置记录，唯一合法值：

- `deep-read` → 必须链接 per-file 报告条目
- `generated-excluded` → 仅限生成物目录（`dist/`、`site/`、`novel-output/`、`truth/`、`__pycache__/`），且**必须记录排除理由 + 已验证可再生成/gitignore 正确**

不存在 `sampled`。台账零未处置文件是阶段 6 的硬门。

### 4.1 D3 排序（派发顺序优化，非覆盖裁剪）

虽然全文件深读，但**派发顺序**按风险加权：(a) postmortem 聚集区（pipeline / gates / contracts / cost——CN3 覆盖 bug、TokenLedger dead-wire、finish_reason 盲点均在此）(b) git churn (c) coverage 缺口 (d) 复杂度。高风险区先审，使早期发现尽早进入后续阶段；覆盖不受影响。

---

## 5. 完备性门 G1-G7（唯一终止条件，取代时间盒）

| 门 | 判据 |
|---|---|
| **G1 广度** | 覆盖台账每文件 = `deep-read`（有 per-file 报告）或 `generated-excluded`（有理由）；零未处置 |
| **G2 深度** | 每区初审通过**独立** fresh-context 复核 agent（与初审分离）：复核重读全文件，0 新 Critical/Important 才算过；9 条线程报告齐全 |
| **G3 验证** | D1 全工具真实运行、输出归档（pre-existing 失败单独列）；全部 CLI 入口冒烟（shenbi-validate G0/G2/G4、shenbi-score、shenbi-phase、shenbi-dispatch dry-run 若可行） |
| **G4 收敛** | 复核轮次不设上限、重审无条件；终止条件仅为本轮 0 新 C/I |
| **G5 产出** | findings ledger 条目数 == 子 spec 文件数（M 级批量 spec 例外见 §9）；每 spec 过自审 |
| **G6 Meta** | meta-audit：fresh-context agent 抽查 ≥20% 的 per-file 报告 vs 真实文件，抓假深读/橡皮图章/覆盖空洞 |
| **G7 人类裁决** | 执行者**禁止**自行宣布"审计完成"；阶段 6 产出总结报告（覆盖数字、findings 统计、遗留风险）后停，由人类拍板结束或追加审查 |

---

## 6. 分区矩阵 Z1-Z10（阶段 2 派发单元）

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

子 agent prompt 必须**内联完整 rubric**（fresh-context 子 agent 看不到本 prompt 文件，禁止只引用章节名——沿用 single-model-sdd-prompt.md 的注入规则）。

---

## 7. 跨模块审计线程 T1-T9（阶段 3，第一公民）

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
2. 核心原则（Iron Law / 只审不改 / 完备性门驱动 / 审查独立性 / 可恢复）
3. 覆盖模型三层 + 台账规则（§4 内容）
4. 完备性门 G1-G7 表（§5 内容）
5. 阶段 0-6 流程（§3 内容；每阶段：输入、动作、退出条件——**无 skill 引擎字段**）
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
| 自包含 | 新会话只读 prompt + AGENTS.md 即可开始执行；全文 grep 无 skill 引用（"skill" 一词只出现在否定声明中） |
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
