# 全项目深度审查执行 Prompt（full-project-audit）

> **自包含基线 + 可选 skill 增强**：所有审查机制、防偷懒规则、产出契约都在本文件内，**无 skill 环境完整可执行**；若环境具备 superpowers skill，可按 §1.5 白名单作**可选增强**（增强非替代，映射表外的 skill 禁止使用）。SDD 流程不使用。执行者所需通用能力：**文件读写、命令执行、（可选的）子 agent 派发**。

---

## Variables

| 变量 | 值 |
|------|----|
| `$AUDIT_DATE` | `2026-08-13`（若实际开始执行日不同，用执行开始日替换，并同步修改下文所有引用） |
| `$AUDIT_DIR` | `docs/superpowers/audit-runs/$AUDIT_DATE/` |
| `$SPECS_DIR` | `docs/superpowers/specs/` |
| `$INDEX` | `docs/superpowers/specs/INDEX.md` |

---

## 0. 任务与铁则

**任务**：对 shenbi 项目做**最广、最深**的独立审核——从整体（架构、契约、pipeline、gates、CI、文档体系）到细节（每个文件逐项），找出**所有错误与优化点**（bug / 契约违反 / 不一致 / 浪费 / 架构债 / 测试失效 / 文档漂移……），并为**每个 finding 产出独立 spec**（minor 可合并，见 §8）。

**铁则（最高优先级，违反任何一条 = 执行失败）**：

1. **只审不改**：除 `$AUDIT_DIR`、`$SPECS_DIR` 新增 spec、`$INDEX` 登记行外，**禁止修改仓库任何文件**（含 src/tests/skills/docs/配置）。修复一律留给后续 spec→plan。
2. **机制自包含为基线，skill 可选增强**：本文件是全部机制的来源；无 skill 环境必须完整执行，**禁止自造"等价流程"替代本文件规定的步骤**。SDD 流程不使用。若环境具备 superpowers skill，仅可按 §1.5 白名单在指定环节使用——**skill 增强而非替代**：使用 skill 不豁免本文件任何步骤，且调用 skill 后必须粘贴其实际输出（Iron Law 同样适用于 skill 调用）。
3. **完备性门驱动，非时间驱动**：无时间盒。唯一终止条件 = 完备性门 G1-G6 全过（§3）**且**人类裁决（G7）。**禁止自宣"审计完成"。**
4. **证据先于断言（Iron Law）**：任何含"通过 / 完成 / 无问题 / 已审 / 正确"字样的消息，该断言的具体验证命令**必须在同一条消息内运行过并粘贴输出**。上一轮跑过 ≠ 本轮成立。

---

## 1. 核心原则

1. **Iron Law**（铁则 4）。
2. **审查独立性**：初审 → 协调者核实 → 独立复核，三层分离。复核是 fresh-context **全量重读**，不是 diff 抽查；协调者核实是**打开真实文件逐条核对**，不轻信初审报告。
3. **rubric 内联**：派发子 agent 时，必须把对应 rubric **完整复制**进子 agent prompt。子 agent 看不到本文件，禁止只引用章节名/表名。
4. **可恢复**：每完成一个 zone / 线程 / 阶段即 checkpoint commit；`progress.md` 是权威状态（§9）。
5. **增量收敛**：复核轮次不设上限、重审无条件；唯一终止条件为本轮 **0 新 Critical/Important**。每轮新 C/I 数必须记录，出现不降反升说明审查流程本身有缺陷，必须查明。

### 1.5 superpowers skill 白名单（可选增强，非替代）

本 prompt 在无 skill 环境完整可执行。若执行环境具备以下 superpowers skill，可在对应环节**选择性使用**以提升审查/spec 质量；映射固定，禁止越界使用；使用后必须粘贴 skill 实际输出（Iron Law）。不使用 skill 完全合规——skill 是增强，不是步骤。

| skill | 强化环节 | 用法 | 不替代什么 |
|---|---|---|---|
| `superpowers:systematic-debugging` | 阶段 4 根因分析、阶段 5 spec 编写 | 其四阶段框架组织每个 finding 的根因分析与假设验证；spec 的"方法"字段本应引用它 | 不替代 file:line 证据核实；不替代独立复核 |
| `superpowers:verification-before-completion` | 每阶段退出、G3/G6 核验 | 声称门通过前用它做证据清单核对 | 不替代实际运行命令并粘贴输出 |
| `superpowers:requesting-code-review` | 阶段 2/3 独立复核层 | 其 rubric 结构（Critical/Important/Minor + plan/code/test 维度）作为复核 agent 的**补充** rubric 来源 | 不替代 fresh-context 全量重读；不替代协调者逐条核实 |
| `superpowers:dispatching-parallel-agents` | 阶段 2/3 并行派发 | 其并行分派实践指导 zone/线程 agent 组织（只读任务互不冲突） | 不替代 rubric 内联与编号段分配 |

**禁止**：`superpowers:writing-plans`（本任务产出 spec 不产出 plan）、`superpowers:brainstorming`（需求已定）、SDD 系流程（`subagent-driven-development` / `executing-plans`）。任何 skill 与本文件冲突时，**以本文件为准**。

---

## 2. 覆盖模型：三层 D1/D2/D3 + 覆盖台账

| 层 | 内容 | 覆盖保证 |
|---|---|---|
| **D1 确定性机械层** | ① `just check` 全套；② `tools/` 全部检查类脚本逐个运行（`lint_status_strings.py` / `lint_repo_consistency.py` / `lint_contract_graph.py` / `scripts/lint_contract_fields.py` / `tools/lint_contracts.py` / `audit-skill-descriptions.py` / `check_fixture_mirror.py` / `lint_no_forbid_with_computed_field.py` / `lint_no_fs_mutation.py`，迁移类工具除外）；③ 全部 `skills/*/SKILL.md` frontmatter 用 Python（yaml 解析）逐文件解析校验；④ 对全部 fixtures/skills 跑 `shenbi-validate G2` / `G4`；⑤ 禁用模式 git grep（bare except / `print(` / pickle / TODO-FIXME-HACK / hardcoded 路径）；⑥ `pytest --cov` 生成覆盖率缺口报告；⑦ 全部 CLI 入口冒烟（`shenbi-validate G0 <seed>` / `shenbi-score` / `shenbi-phase` / `shenbi-dispatch --help`）。 | **100% 文件**，机器穷举。输出归档 `$AUDIT_DIR/d1/d1-baseline.md`；pre-existing 失败**单独一节**列出（与本次审查新增发现分离，但失败本身也是 finding）。 |
| **D2 结构化模式层** | 契约图闭包与 reads/writes 接线 vs `tests/tiers/deps.json`、import 环、死代码、重复块、文档↔代码 file:line 漂移抽查、SKILL.md 元数据一致性（name 小写 kebab / description ≤500 字符且只写触发条件 / kind / reads 字段存在性）。 | **100% 文件**，grep/脚本模式可达。 |
| **D3 语义深读层** | 每文件人工语义审查：逻辑正确性、设计质量、边界条件、错误处理、测试真实性。**不抽样——全文件深读。** | **100% 文件**（生成物目录除外，见下）。 |

**覆盖台账（G1 载体）**：`git ls-files` 全清单，每文件恰好一条处置记录，唯一合法值：

- `deep-read` → 必须链接 per-file 报告条目；
- `generated-excluded` → 仅限生成物目录（`dist/`、`site/`、`novel-output/`、`truth/`、`__pycache__/` 等），**必须逐个记录排除理由 + 已验证可再生成 / .gitignore 正确**。

**不存在 `sampled` 处置值。** 台账零未处置文件是阶段 6 的硬门。

**D3 派发顺序（仅优化调度，不裁剪覆盖）**：按风险加权先审——(a) postmortem 聚集区（pipeline / gates / contracts / cost——历史 P0：CN3 覆盖 bug、TokenLedger dead-wire、finish_reason 盲点）(b) git churn 高 (c) coverage 缺口大 (d) 复杂。先审高风险区，覆盖不受影响。

---

## 3. 完备性门 G1-G7（唯一终止条件）

| 门 | 判据 |
|---|---|
| **G1 广度** | 覆盖台账每文件 = `deep-read`（有 per-file 报告）或 `generated-excluded`（有理由）；零未处置 |
| **G2 深度** | 每区初审通过**独立** fresh-context 复核（初审者≠复核者）：复核重读全文件，本轮 0 新 Critical/Important 才算过；T1-T9 线程报告齐全 |
| **G3 验证** | D1 全部工具真实运行、输出归档；pre-existing 失败单列；CLI 冒烟全部执行过 |
| **G4 收敛** | 复核轮不设上限、重审无条件；终止仅为本轮 0 新 C/I，且轮次历史记录在案 |
| **G5 产出** | findings ledger 条目数 == 子 spec 文件数（M 批量例外见 §8）；每 spec 过 §8 自审 |
| **G6 Meta** | meta-audit：抽查 ≥20% 的 per-file 报告条目 vs 真实文件，抓假深读 / 橡皮图章 / 覆盖空洞 |
| **G7 人类裁决** | 阶段 6 产出 `final-report.md`（覆盖统计 / findings 统计 / 遗留风险）后**停止**，由人类拍板结束或追加审查。执行者禁止自行宣布完成 |

---

## 4. 阶段流程（0-6）

**全局规则**：每阶段结束时更新 `progress.md`（§9 格式）；阶段间严格串行（阶段 2 与阶段 3 可交错并行）。

### 阶段 0 · 清点与基线

- **动作**：
  1. 建目录：`$AUDIT_DIR/{progress.md, coverage-ledger.md, findings-ledger.md, zone-reports/, thread-reports/, d1/, zones/}`（progress/ledger 用 §7 schema 初始化）。
  2. 运行 `git ls-files` 生成覆盖台账，全部文件初始处置 `unreviewed`。
  3. 按 §5 分区矩阵的 glob 生成 `zones/Z<N>.files` 权威文件清单（供子 agent 读取，避免各自 glob 漂移）。
  4. 运行 D1 全套（§2），输出归档 `d1/d1-baseline.md`；D1 发现的独立问题记入 findings ledger（编号段 `D1xx`）。
  5. 提交 checkpoint：`docs(audit): phase-0 inventory + D1 baseline`。
- **退出**：台账 + 文件清单生成完、D1 归档、progress.md 更新为"阶段 1 进行中"。

### 阶段 1 · 整体层审查（协调者亲自，不派发）

- **读**：`AGENTS.md`、`docs/architecture/overview.md`、`docs/framework/gates.md`、契约相关文档、`justfile`、`pyproject.toml`、`docs/superpowers/specs/INDEX.md` 及活跃 spec、`.github/workflows/` 全部。
- **审查维度**（每维度必须给出结论：通过 / findings 编号）：
  1. 架构一致性——AGENTS.md 声明的目录结构、命令、分层 vs 实际；
  2. 契约单一信源体系——frontmatter → 生成物 → 执行 的链路设计是否有洞；
  3. pipeline 状态机设计——T2/T3 阶段模型、并行调度、崩溃恢复设计；
  4. G0-G7 门体系——门间依赖、不可跳过性、幂等性设计；
  5. CI 设计——8 个 workflow 与 `just check` 的一致性、覆盖缺口；
  6. 文档体系——specs/INDEX/archive 流程、文档间矛盾。
- findings 编号段：`F0xx`。
- **退出**：6 维度全部有结论并录入 ledger；progress.md 更新。

### 阶段 2 · 分区深度审查（Z1-Z10）

- **派发协议**：
  1. 若执行环境支持子 agent 派发：每区一个 **fresh-context 只读** 初审 agent（并行）。**大区可拆**：Z7 按 tests/ 子目录拆 2-4 个 agent、Z8 按 skill 名首字母拆 2-3 个——拆多 agent 时报告文件仍唯一（各 agent 追加自己的编号段到同一 `zone-reports/Z<N>.md`），编号段先分配防冲突。
  2. 无子 agent 能力：协调者逐区串行亲审，流程不变。
  3. 子 agent prompt = §5 模板 + 该区 rubric **完整复制** + 该区文件清单路径 + 报告输出路径 + 只读禁令。
- **协调者收报告后**（每区）：
  1. 更新 coverage-ledger：该区文件全部 `deep-read` + 链接报告条目；
  2. **逐条核实** findings：打开真实文件核对 file:line 证据与结论，不实 finding 在 ledger 标 `false-positive`（附理由），核实通过的标 `verified`；
  3. 派发**独立复核 agent**（fresh-context，≠ 初审者）：重读该区全文件 + 初审报告，任务 = 找漏报（初审没发现的 C/I）+ 误报（初审发现但站不住的）+ 覆盖空洞；复核 findings 编号段 = 该区段内剩余号；
  4. 复核有 0 新 C/I → 该区 G2 通过，checkpoint commit；有 → 更新报告，**再派新一轮复核**（G4），直到 0 新 C/I。
- **退出**：Z1-Z10 全部 G2 通过；progress.md 记录每区轮次历史。

### 阶段 3 · 跨模块审计线程（T1-T9，与阶段 2 可交错）

- 每条线程一个 fresh-context 只读 agent（无子 agent 能力则协调者亲自逐条），prompt = §6 模板 + 线程 rubric 完整复制。
- 线程 findings 编号段 `T{n}xx`（T1→T1xx … T9→T9xx）。
- 协调者对线程报告同样逐条核实 + 独立复核。
- **退出**：9 条线程报告齐全且全过复核。

### 阶段 4 · 根因聚类与校准（协调者亲自）

1. **去重**：findings ledger 按「根因」聚类——同一根因的多处表现**合并**（主条目保留，其余标 `merged-into-Fx`）。去重键 = 根因描述，非症状描述。
2. **严重度校准**：每条按 §8 规则定 P0/P1/P2/M；同根因取最高。
3. **根因簇图**：跨 finding 的根因聚类（如"dead-wire 簇"），写入总纲 spec 草稿。
4. **抽查复核**：fresh-context agent（或协调者亲自）抽查 ≥20% 的 per-file 报告条目 vs 真实文件，抓假深读；抽查结果记录在案。
- **退出**：ledger 无未合并的重复根因；严重度定稿。

### 阶段 5 · spec 产出（协调者亲自）

- 按 §8 契约产出：1 总纲 catalog spec + 每 finding 独立子 spec + M 批量 spec + `$INDEX` 登记。
- **退出**：G5 核对（ledger `specced` 数 == spec 文件数；每 spec 过自审）。

### 阶段 6 · 覆盖证明 + meta-audit + 人类裁决

1. G1 终检：台账零 `unreviewed`、零空链接；
2. G6 meta-audit：执行并记录结果；
3. 写 `final-report.md`：覆盖数字（deep-read 文件数 / 总文件数 / excluded 清单）、findings 统计（按严重度）、轮次历史、遗留风险（低置信度文件列表）；
4. checkpoint commit；
5. **停止，向人类汇报 final-report 摘要，等待裁决**（G7）。收到"继续"则从指示处续审；收到"结束"才可收尾（不改代码，只留 spec）。

---

## 5. 分区矩阵 Z1-Z10

每区列出：文件范围（glob）、重点 rubric 维度。派发时按下方模板组装子 agent prompt。

| 区 | 文件范围（glob，以 `git ls-files <glob>` 实际结果为准） | 重点 rubric 维度 |
|---|---|---|
| Z1 | `src/shenbi/*.py`（顶层 19 文件，不含子目录） | 异常层次完整性（typed exceptions 全链使用）、phase_runner 状态机正确性、safe_write/幂等写、structlog 无 print、recovery 语义 |
| Z2 | `src/shenbi/contracts/`、`src/shenbi/dispatcher/` | 契约单一信源、字段级 reads 过滤实现与 escape hatch（缺字段→全文件+WARN）、派发协议与重试参数 |
| Z3 | `src/shenbi/pipeline/` | 状态机、并发调度、重试经济、truth 写路径幂等、token 计量（历史 P0 聚集区） |
| Z4 | `src/shenbi/gates/`（含 g4 checkers） | 门函数幂等（纯验证无副作用）、decisions.json G4 schema、P2.5 rationale 规则（routine+low 禁 rationale / manual_override+high 必 rationale） |
| Z5 | `src/shenbi/audit/`、`src/shenbi/cost/`、`src/shenbi/orchestration/` | TokenLedger 接线（计量代码未接线 = dead-wire 模式）、审计波调度、成本分摊正确性 |
| Z6 | `src/shenbi/records/`、`src/shenbi/trace/`、`src/shenbi/text/`、`src/shenbi/config/`、`src/shenbi/plugins/`、`src/shenbi/skill_utils/` | 确定性助手正确性（纯函数、边界）、序列化、配置治理、text 处理边界 |
| Z7 | `tests/`（16 子目录，可拆 2-4 agent） | 测试真实性（走真实代码路径，非纯 mock）、fixture 真实性（G0.9：真实输出或上游生成副本，禁手写 mock）、覆盖缺口、测试自身 bug、golden/baseline 漂移 |
| Z8 | `skills/`（74 skill，可拆 2-3 agent） | description ≤500 字符且只写触发条件（不写做什么）、DOT 流程图与正文一致、decisions.json 声明 vs 实际产出、reads 字段 vs truth 文件实况、anti-rationalization 表完整性 |
| Z9 | `docs/` + 根级 `*.md`（AGENTS/README/CHANGELOG/CODE_OF_CONDUCT/CONTRIBUTING/SECURITY/goal-prompt/command-to-give/outline-example） | 文档↔代码漂移（file:line 引用抽查）、INDEX 与 archive 一致性、活跃 spec 间矛盾、meta 文档自身（含本 prompt 的设计 spec） |
| Z10 | `.github/`、`pyproject.toml`、`justfile`、`uv.lock`、`tools/`、`scripts/`、`plugins/`、`benchmarks/`、`executor_config.toml`、`run_pipeline.sh`、`mkdocs.yml`、`cliff.toml` | CI 与 `just check` 一致性（justfile 是权威，workflow 不得漂移）、脚本正确性、配置漂移、依赖锁定卫生 |

**通用 rubric 维度（每区每个文件必查，与重点维度叠加）**：
1. 正确性：逻辑错误、边界条件、off-by-one、None/空输入；
2. 错误处理：无 bare except 吞错、异常不丢失上下文；
3. 签名一致性：函数签名 vs 调用方（grep 调用方验证）、plan/spec 中声明的签名 vs 实际；
4. 序列化安全：涉及 ProcessPool / threading / multiprocessing 的 pickle 边界；
5. 枚举/状态字符串：唯一定义在 `src/shenbi/contracts/enums.py`（相关文件时）；
6. 测试对应：相关测试存在且真实（读 tests/ 对应文件）；
7. 文档引用：相关 docs 的 file:line 引用未漂移（超出 ±5 行即记 finding）。

**子 agent prompt 模板（分区版，派发时按模板 + rubric 复制组装）**：

```
你是全项目深度审查的分区初审 agent，负责 Z<N>（只读）。
# 任务
对文件清单 `$AUDIT_DIR/zones/Z<N>.files` 中的【每一个】文件做语义深读审查，
产出 per-file 报告，追加写入 `$AUDIT_DIR/zone-reports/Z<N>.md`（用 Write/Edit 工具）。
# 只读禁令（违反 = 任务失败）
除上述报告文件外，禁止创建/修改/删除任何仓库文件；禁止 git add/commit；禁止运行
会写入仓库的命令（pytest 只允许 --collect-only 与单个纯读测试文件）。
# 审查 rubric（每个文件必查）
<此处完整复制：通用维度 + Z<N> 重点维度，逐条列出，禁止只引用表名>
# 报告 schema（每个文件一条，必须覆盖全部清单文件，缺一条 = 未完成）
### <file path>
- 处置: deep-read
- 声称检查的不变量: [列表——本文件应维护的具体不变量，写不出来 = 没审]
- findings: [F<编号> 或 无]
- 验证命令: [实际运行过的命令 + 输出摘要；没运行的写"未运行"]
- 置信度: high|medium|low（low 必须说明原因）
# findings 格式（每条）
F<编号> | 标题 | 类别(error|optimization) | 严重度(P0|P1|P2|M) | 证据 file:line | 根因 | 验证命令+输出 | 建议方向
# 证据铁律（Iron Law）
每条 finding 的证据必须是真实读到的 file:line；验证命令必须实际运行并粘贴输出；
未实际运行的一律写"未验证"，禁止暗示验证过。
# 编号段
本 agent 使用 F<N>00-F<N>99（按分配）。
# 返回
最终消息返回：findings 清单摘要（编号/标题/严重度/证据行）+ 覆盖统计
（deep-read 文件数/清单总数）+ 低置信度文件列表 + 未覆盖文件列表（必须为空）。
```

---

## 6. 跨模块审计线程 T1-T9

每条线程横切多区；agent 读线程涉及的全部文件（自行用 glob + grep 定位，禁止只读清单文件）。

| 线程 | 审查内容 | 依据 |
|---|---|---|
| T1 | decisions-schema v1 全链合规：producer 写入 vs consumer 读取 vs G2（file_type=decisions）vs G4（schema + P2.5 rationale 规则） | AGENTS.md decisions-sidecar |
| T2 | 契约单一信源：SKILL.md frontmatter ↔ deps.json ↔ docs/framework ↔ skills/ 生成物；`shenbi-sync-contracts` 幂等（跑 `git diff --exit-code`） | AGENTS.md + 契约基础设施 |
| T3 | 字段级 reads 过滤 + escape hatch：dispatcher 实现 vs 契约声明；缺字段回退全文件 + WARN 日志是否真实存在 | AGENTS.md 字段级 reads |
| T4 | TokenLedger 接线：计量代码存在但未接线的 dead-wire 模式；成本归集路径完整性 | 历史 postmortem（dead-wire 先例） |
| T5 | 重试经济与错误处理：重试参数、异常层次使用、finish_reason=length 处理、429 行为 | 历史 postmortem |
| T6 | 并发与序列化安全：ProcessPool / threading / multiprocessing 的 pickle 边界、共享状态竞态 | §5 通用维度 4 |
| T7 | truth 文件写路径幂等：覆盖 vs 追加、upsert 键唯一性（CN3 覆盖 bug 先例） | 历史 postmortem |
| T8 | fixture 真实性：G0.9 禁止手写 mock；fixtures 为真实输出或上游生成副本 | AGENTS.md fixtures |
| T9 | 枚举/状态字符串单一信源：`contracts/enums.py` 唯一定义；lint_status_strings 覆盖是否有洞 | §5 通用维度 5 |

**线程 agent prompt 模板**：同 §5 模板，改动三处——任务改为"跨模块线程 T<N>，横切审查下列主题"；报告写入 `thread-reports/T<N>.md`；rubric 段复制该线程的审查内容 + 涉及文件定位方法；编号段 `T<N>00-T<N>99`。

---

## 7. schema 三件套（状态文件格式）

### 7.1 progress.md（权威恢复入口）

```markdown
# 审计进度 — $AUDIT_DATE
## 阶段状态机
| 阶段 | 状态 | 轮次历史 |
|---|---|---|
| 0 清点与基线 | done | — |
| 1 整体层审查 | done | — |
| 2 分区深度审查 | in_progress | Z1:初审✓复核1/1✓ … |
| 3 线程 | pending | — |
| 4 聚类校准 | pending | — |
| 5 spec 产出 | pending | — |
| 6 覆盖证明+裁决 | pending | — |
## 会话日志（追加式）
### <日期> 会话 N
- 完成: …
- 下一步: …
- 待核实 findings: …
```

### 7.2 findings-ledger.md（唯一权威 findings 表）

```markdown
# Findings Ledger
| ID | 标题 | 类别 | 严重度 | 证据 | 根因 | 验证 | 影响 | 建议方向 | 深度 | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|
| F301 | … | error | P1 | file:line… | … | 命令+输出摘要 | … | … | deep-read | open→verified→specced |
```
状态机：`open`（已记录）→ `verified`（协调者核实）→ `merged-into-Fx`（去重合并）→ `specced`（spec 已产出）；`false-positive`（核实不成立，保留记录+理由）。

### 7.3 coverage-ledger.md（G1 台账）

```markdown
# 覆盖台账
| path | 处置 | 报告链接 | 理由 |
|---|---|---|---|
| src/shenbi/scoring.py | deep-read | zone-reports/Z1.md#scoring | — |
| dist/… | generated-excluded | — | 生成物，uv build 可再生 |
```
初始生成全部 `unreviewed`；每区完成后由协调者批量更新。

---

## 8. spec 产出契约（阶段 5）

- **单位 = 根因**：同一根因的多处表现合并为 1 个 spec（findings 表内列全）；不同根因不同 spec。
- **严重度**：P0（立即修，阻塞级）/ P1（高）/ P2（中）/ M（文案类 minor：错别字、命名不一致、格式）。**M 级全部合并**进一个批量 spec `$AUDIT_DATE-minor-findings-batch-design.md`（按区分节）；P0/P1/P2 每个根因一个独立 spec。
- **文件**：`$SPECS_DIR/$AUDIT_DATE-<slug>-design.md`，头部块：
  ```
  > **Date:** … | **Status:** Design | **Severity:** 🟥/🟠/🟡 … | **方法:** systematic-debugging 四阶段
  > **系列:** $AUDIT_DATE 全项目审查 | **依赖:** … | **范围:** … | **核心洞察:** …
  ```
  每条 finding 正文含：症状 / 证据 file:line / 根因 / 分类 / 影响 / 假设+验证命令 / 修复方向 / 数值化标准。
- **总纲**：`$AUDIT_DATE-full-project-audit-design.md`（catalog：每 finding 一行 + 根因簇图 + 建议执行顺序 + 覆盖统计）。
- **INDEX 登记**：1 总纲 + N 子 spec + 1 M 批量，顺序号续排；更新活跃 spec 数。
- **spec 自审**（每份）：① 无 TBD/TODO/占位符；② 内部无矛盾；③ 范围单聚焦（一个根因）；④ 证据无歧义（file:line 唯一）。
- 提交：`docs(audit): findings specs — <总纲+子spec列表>`。

---

## 9. checkpoint / 恢复协议

- **checkpoint commit 时机**：阶段 0/1/4/5/6 完成后各一次；阶段 2/3 每区（每线程）复核通过后一次。提交消息 `docs(audit): <阶段/zone> checkpoint`。
- **会话结束前**（每轮）：更新 progress.md 会话日志（下一步动作写具体、待核实 findings 列 ID）→ commit → 结束。
- **新会话恢复第一步**：读 `$AUDIT_DIR/progress.md` → 按阶段状态机继续；先 `git status` 确认工作树干净（除未提交的审计文件）。
- **恢复后的 Iron Law**：恢复点之前的结论只可作索引，**声称通过必须本轮重跑验证**。

---

## 10. Anti-Rationalization 守则

| 执行者可能说 | 回应 |
|---|---|
| "时间不够，这区抽样吧" | 禁止。无时间盒；台账不存在 sampled 处置（§2）。 |
| "工具绿了 = 没错误" | 禁止。D1 只是基线；语义错误跑不出来。 |
| "已经复核 3 轮了" | 唯一终止条件：本轮 0 新 C/I（G4），轮次历史必须记录且新 C/I 单调下降。 |
| "这文件一看就是样板，快速过" | 禁止。per-file 报告必须列出声称检查的不变量，写不出来 = 没审。 |
| "子 agent 报告成功" | 协调者逐条打开真实文件核对，不轻信。 |
| "生成物目录可以整目录跳过" | 必须逐个声明 `generated-excluded` + 再生成性验证 + 理由。 |
| "审计完成" | 禁止自宣。G1-G6 全过 + 人类裁决（G7）。 |
| "发现太多先记着后面写" | 发现即录入 findings ledger（当轮），禁止内存暂存。 |
| "用了 skill 就能跳过 prompt 的步骤" | 禁止。skill 是增强非替代（§1.5）；白名单之外禁止；使用必粘贴输出。 |
| "环境没有 skill 所以完不成" | 禁止。本 prompt 无 skill 环境完整可执行（自包含基线）。 |
| "没有子 agent 能力，所以抽样" | 禁止。降级为协调者串行全量，绝不抽样。 |
| "这 finding 和另一个类似，我口头合并了" | 禁止。合并必须走 ledger `merged-into-Fx` 标记，理由写入。 |
| "文档没改动就不用复核" | 禁止。重审无条件，doc-only / 配置文件无例外。 |

---

## 11. 成本预期与诚实声明

- **规模**：src 199 文件/29K 行 + tests 284 文件/36K 行 + skills 74 + docs 200 + CI/工具链，`git ls-files` ≈ 2700 文件。
- **诚实代价**：全量深读 + 独立复核的串行等价工作量 **100+ 小时**；有子 agent 并行派发时墙钟约 **20-40 小时、跨 10-20 个会话**。这不是慢，这是"最深入最广"的真实价格。
- **禁止自我降级**：发现远超预期时不许把 D3 降级为抽样、不许减复核轮次——只能按 §9 的恢复协议如实记录进度、续跑。
- **边界诚实**：`final-report.md` 必须如实标注低置信度文件与任何被 `generated-excluded` 的目录；"已审计"的范围定义 = 台账状态，不夸大。

---

*本 prompt 与设计 spec `docs/superpowers/specs/2026-08-13-full-project-audit-prompt-design.md` 一一对应；执行时如发现本 prompt 内部矛盾或缺失机制，停止并报人类裁决，禁止自行改写规则。*
