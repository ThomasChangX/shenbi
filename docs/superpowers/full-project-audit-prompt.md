# 全项目深度审查执行 Prompt（full-project-audit）· v3

> **自包含基线 + 可选 skill 增强**：所有审查机制、防偷懒规则、产出契约都在本文件内，**无 skill 环境完整可执行**；若环境具备 superpowers skill，可按 §1.5 白名单作**可选增强**（增强非替代，映射表外的 skill 禁止使用）。SDD 流程不使用。执行者所需通用能力：**文件读写、命令执行、（可选的）子 agent 派发**。
>
> **版本**：v3（2026-08-15 修订，人类指示）。v3 是对 v2 的**实证修复版**：每条机制变更对应 2026-08-14 执行 run（`docs/superpowers/audit-runs/2026-08-14/`）暴露的一个具体缺陷，逐条对照表见设计 spec `docs/superpowers/specs/2026-08-13-full-project-audit-prompt-design.md` §0.1。核心变更：① G4 收敛双轨化（硬收敛自动 / 软收敛须披露+人类追认——v2 的"唯一终止条件"实际不可达，4/6 src 区靠无标准豁免放行）；② 每轮复核强制新增攻击角度（§3.5 角度库——后续人工扫描实证"新角度 > 重复重读"，F1322 即新角度产物）；③ G5 由错误的条目数等式改为机械对账命令（v2 下实际 spec 覆盖仅 10/118 P1）；④ G6 分层深核下限、禁隐性稀释（v2 下有效深核率 ≈8.3% 未披露）；⑤ 新增 T16 性能线程（计算/内存/IO 性能在 v2 整类缺席）；⑥ final-report 数字机械生成（v2 下与台账漂移 781↔786）；⑦ 无人值守协议（§1.6：`$UNATTENDED` 人类门降级语义 + 非交互纪律——覆盖 shenbi pipeline checkpoint review 的人工确认面，长跑不卡）。已按 v2 完成的审计结论继续有效；新审计/续审以 v3 为准（升级处理见 §9）。

---

## Variables

| 变量 | 值 |
|------|----|
| `$AUDIT_DATE` | `<执行开始日，如 2026-08-14>`（若与既往审计同日重跑，加后缀 `-r2` 区分目录） |
| `$AUDIT_DIR` | `docs/superpowers/audit-runs/$AUDIT_DATE/` |
| `$SPECS_DIR` | `docs/superpowers/specs/` |
| `$INDEX` | `docs/superpowers/specs/INDEX.md` |
| `$UNATTENDED` | `false`（默认）\| `true`——无人值守模式：人类不在场的长跑（如过夜），人类门降级为"记录 + 默认方向"，非交互纪律强制（§1.6） |

---

## 0. 任务与铁则

**任务**：对 shenbi 项目做**最广、最深**的独立审核——从整体（架构、契约、pipeline、gates、CI、文档体系、依赖与供应链、安全、**性能与资源效率**）到细节（每个文件逐项），找出**所有可达的错误与优化点**（bug / 契约违反 / 不一致 / 浪费 / 架构债 / 测试失效 / 文档漂移 / 安全风险 / 依赖问题 / 性能与资源浪费……），并为**每个 finding 产出独立 spec**（minor 可合并，见 §8）。

**诚实边界（先于一切机制声明）**：本 prompt 保证的是**过程完备**（每个文件被处置、每个声称可对账），不是**本体完备**（存在的每个缺陷都被发现）。收敛是停止规则，不是完备性证明；同模型复核存在相关性盲区。因此：G7 人类裁决不可绕过，遗留风险必须如实声明。

**铁则（最高优先级，违反任何一条 = 执行失败）**：

1. **只审不改**：除 `$AUDIT_DIR`、`$SPECS_DIR` 新增 spec、`$INDEX` 登记行外，**禁止修改仓库任何文件**（含 src/tests/skills/docs/配置）。修复一律留给后续 spec→plan。
2. **机制自包含为基线，skill 可选增强**：本文件是全部机制的来源；无 skill 环境必须完整执行，**禁止自造"等价流程"替代本文件规定的步骤**。SDD 流程不使用。若环境具备 superpowers skill，仅可按 §1.5 白名单在指定环节使用——**skill 增强而非替代**：使用 skill 不豁免本文件任何步骤，且调用 skill 后必须粘贴其实际输出（Iron Law 同样适用于 skill 调用）。
3. **完备性门驱动，非时间驱动**：无时间盒。唯一终止条件 = 完备性门 G1-G6 全过（§3）**且**人类裁决（G7）。**禁止自宣"审计完成"。**
4. **证据先于断言（Iron Law）**：任何含"通过 / 完成 / 无问题 / 已审 / 正确"字样的消息，该断言的具体验证命令**必须在同一条消息内运行过并粘贴输出**。上一轮跑过 ≠ 本轮成立。
5. **严重度只按 §8.1 决策表判定**：禁止主观升降级。复核 agent **无权单方降级**初审 findings 的严重度（有异议 → 作为"严重度异议"附理由提出，协调者裁决并记录）；阶段 4 校准**升级**严重度必须触发该 finding 所属区/线程的强制补复核（§4 阶段 4）。
6. **对账机械化**：一切计数/覆盖/登记声称（G5 对账、final-report 统计、meta-audit 分母）必须由 §3/§4 内联的机械命令产生并粘贴输出，**禁止手抄数字**（2026-08-14 run 的 final-report 与台账曾漂移 781↔786）。

---

## 1. 核心原则

1. **Iron Law**（铁则 4）。
2. **审查独立性**：初审 → 协调者核实 → 独立复核，三层分离。复核是 fresh-context **全量重读**，不是 diff 抽查；协调者核实是**打开真实文件逐条核对**，不轻信初审报告。同模型复核有相关性盲区——用 §3.5 角度库的**角度多样性**对冲，而非单纯加轮次。
3. **rubric 内联**：派发子 agent 时，必须把对应 rubric **和 §8.1 严重度决策表**完整复制进子 agent prompt。子 agent 看不到本文件，禁止只引用章节名/表名。
4. **可恢复**：每完成一个 zone / 线程 / 阶段即 checkpoint commit；`progress.md` 是权威状态（§9）。
5. **增量收敛（波动是正常产出，不记录才是违规）**：复核轮次不设上限、重审无条件；收敛判定见 §3 G4 双轨（硬收敛自动通过；软收敛须披露 + 人类追认）。每轮新 finding 数记录在案；**任一轮高于上轮 → 当轮记一行波动分析**（发现角度 / 上轮为何漏）；累计 2 次波动分析指向同一盲区 → 该区强制新角度轮（§3.5）。（v2 的"单调下降、不降反升必须查明"实际被反复违反且零次查明——v3 承认波动是 fresh-context 重审的正常价值，把义务从"查明"降为"记录"，把升级条件定量化。）
6. **写隔离**：并行 agent 各写自己的**独立段文件**，禁止并行写共享文件（写协议见 §4 阶段 2）；违规 = 数据污染，该轮成果作废重写。
7. **测量装置隔离**：审计期间一切产生覆盖率/统计产物的运行**独占其产物路径**（`COVERAGE_FILE` 等环境变量隔离），且除 T11 指定运行外禁止并发 pytest（2026-08-14 审计期间 coverage.xml 曾 2 次被并行测试覆写污染）。

### 1.5 superpowers skill 白名单（可选增强，非替代）

本 prompt 在无 skill 环境完整可执行。若执行环境具备以下 superpowers skill，可在对应环节**选择性使用**以提升审查/spec 质量；映射固定，禁止越界使用；使用后必须粘贴 skill 实际输出（Iron Law）。不使用 skill 完全合规——skill 是增强，不是步骤。

| skill | 强化环节 | 用法 | 不替代什么 |
|---|---|---|---|
| `superpowers:systematic-debugging` | 阶段 4 根因分析、阶段 5 spec 编写 | 其四阶段框架组织每个 finding 的根因分析与假设验证；spec 的"方法"字段本应引用它 | 不替代 file:line 证据核实；不替代独立复核 |
| `superpowers:verification-before-completion` | 每阶段退出、G3/G6 核验 | 声称门通过前用它做证据清单核对 | 不替代实际运行命令并粘贴输出 |
| `superpowers:requesting-code-review` | 阶段 2/3 独立复核层 | 其 rubric 结构（Critical/Important/Minor + plan/code/test 维度）作为复核 agent 的**补充** rubric 来源 | 不替代 fresh-context 全量重读；不替代协调者逐条核实 |
| `superpowers:dispatching-parallel-agents` | 阶段 2/3 并行派发 | 其并行分派实践指导 zone/线程 agent 组织（只读任务互不冲突） | 不替代 rubric 内联与编号段分配；不替代写隔离协议 |
| `superpowers:security-review` | T12 安全线程 | 其安全审查清单（注入/路径/凭证/敏感数据）作为 T12 的**补充**检查维度 | 不替代 T12 的仓库特定清单（git 历史凭证扫描、prompt injection 面）；不替代证据铁律 |

**禁止**：`superpowers:writing-plans`（本任务产出 spec 不产出 plan）、`superpowers:brainstorming`（需求已定）、SDD 系流程（`subagent-driven-development` / `executing-plans`）。任何 skill 与本文件冲突时，**以本文件为准**。

### 1.6 无人值守与非交互纪律（$UNATTENDED）

**非交互纪律（任何模式都适用，$UNATTENDED=true 只是强化执行）**：

- 审计执行的一切命令必须**非交互**：长命令 `timeout` 包裹（上限按命令类型预设，如单测类 3600s）；stdin 重定向 `</dev/null` 或预设默认答案（CI 类环境变量 / `--no-input` 类 flag）。
- 命令等待输入 = 缺陷，不是等待理由：kill 该命令 → 记 finding（P2 可测性：交互式阻塞无人值守审计）→ 继续后续工作。
- **被审对象的人工确认面**：shenbi novel pipeline 的 checkpoint review 按设计等待人工 decision——审计**禁止触发任何会停在人工确认上的真实 pipeline 入口**（`just pipeline-init` / `just pipeline-review` / `shenbi-phase` 的交互形态）；T11 运行时核验只走非交互测试入口（pytest 包装 / 临时目录）；某核验只能经交互入口完成 → 记"**不可审计（交互阻塞）**"进 final-report 遗留风险，**不挂起**。

**$UNATTENDED = true 时的人类门降级语义**：

| 人类门 | 有人模式 | 无人值守模式 |
|---|---|---|
| 阶段 4 触发式强制简报 | 简报并等待方向指示 | 简报全文写入 progress.md 后按**"继续"默认方向**执行，不等待回复；用户醒来可追认/改向——审计只读 + checkpoint commit，改向成本低（重跑聚焦角度即可） |
| G4 软收敛三件套之"人类追认" | 简报/G7 当场追认 | 标 `待追认`，**不阻塞**后续区/线程/阶段；G7 终点统一追认 |
| BLOCKING deviation（G6 低于下限等） | 停下报人类 | 记录 deviation + 该子项**挂起为未闭合**（禁止伪造闭合）+ 继续其他独立工作；G7 汇总 |
| G7 人类裁决 | 汇报后等待裁决 | 正常执行到阶段 6 完结后停在 G7——**这是"做完了停"，不是"卡住"**；醒后裁决即可 |

**无人值守不放松的硬线**：含未解 P0 的区禁用软收敛（不因人类不在场放松）；G5 语义覆盖缺口 = 补工作（写 spec 是工作不是等批准）；只审不改（铁则 1）；**页脚条款（发现本 prompt 内部矛盾/缺失机制）在无人值守下取更严格解释继续 + 记录 deviation，G7 报备——禁止以歧义为由停摆**。

---

## 2. 覆盖模型：四层 D1-D4 + 覆盖台账

| 层 | 内容 | 覆盖保证 |
|---|---|---|
| **D1 确定性机械层** | ① `just check` 全套；② `tools/` 全部检查类脚本逐个运行（`lint_status_strings.py` / `lint_repo_consistency.py` / `lint_contract_graph.py` / `scripts/lint_contract_fields.py` / `tools/lint_contracts.py` / `audit-skill-descriptions.py` / `check_fixture_mirror.py` / `lint_no_forbid_with_computed_field.py` / `lint_no_fs_mutation.py`，迁移类工具除外）；③ 全部 `skills/*/SKILL.md` frontmatter 用 Python（yaml 解析）逐文件解析校验；④ 对全部 fixtures/skills 跑 `shenbi-validate G2` / `G4`；⑤ 禁用模式 git grep（bare except / `print(` / pickle / TODO-FIXME-HACK / hardcoded 路径）；⑥ `pytest --cov` 生成覆盖率缺口报告（**每文件未覆盖行清单**，逐行处置在 per-file 报告，见 §5 通用维度 8）——运行时**独占 `COVERAGE_FILE` 环境变量**且与 T11 以外的 pytest 运行互斥（防并行覆写污染，见原则 7）；⑦ 全部 CLI 入口冒烟（`shenbi-validate G0 <seed>` / `shenbi-score` / `shenbi-phase` / `shenbi-dispatch --help`）；⑧ **凭证扫描**：`git log -p --all` 全历史 + 工作树 grep 高熵/凭证模式（`sk-` 长串、`ghp_`、`AKIA`、`BEGIN (RSA|OPENSSH|EC) PRIVATE KEY`、`password\s*=` 等），命中即 finding（语义确认归 T12）；⑨ **依赖漏洞审计**：`uv audit`（版本不支持则 pip-audit / osv-scanner 等价）全量漏洞清单；⑩ **依赖健康初判**：未使用依赖检测（deptry，若可用）或 `uv tree` 与 pyproject 声明对照 + 重型依赖必要性初判（如 torch/transformers 级依赖是否真的被引用）；⑪ **skip/xfail 清点**：`pytest --collect-only -q` 统计并输出全部 skip/xfail 测试清单（文件:行，处置归 Z7）；⑫ **锁定与环境一致性**：`uv lock --check`（只读）+ `.venv` 与 lock 漂移对照（`uv pip list` vs pyproject 声明）。 | **100% 文件**，机器穷举。输出归档 `$AUDIT_DIR/d1/d1-baseline.md`；pre-existing 失败**单独一节**列出（与本次审查新增发现分离，但失败本身也是 finding）。 |
| **D2 结构化模式层** | 契约图闭包与 reads/writes 接线 vs `tests/tiers/deps.json`、import 环、死代码、重复块、SKILL.md 元数据一致性（name 小写 kebab / description ≤500 字符且只写触发条件 / kind / reads 字段存在性）。**穷举项**（脚本/grep 可达，必须全量）：契约图闭包、import 环、死代码、重复块、SKILL.md 元数据一致性。**抽样项**（规则固定，禁止随意挑样本）：文档↔代码 file:line 漂移——每文档抽验 ≥5 个引用，高风险文档（架构/契约/gates/AGENTS 相关）全查；抽样清单在阶段 0 预先登记进 progress.md。 | **100% 文件**（穷举项全量；抽样项按预先登记的固定规则），grep/脚本模式可达。 |
| **D3 语义深读层** | 每文件人工语义审查：逻辑正确性、设计质量、边界条件、错误处理、测试真实性、**复杂度与资源效率（通用维度 10）**。**不抽样——全文件深读。** | **100% 文件**（生成物目录除外，见下；`$AUDIT_DIR` 自身文件除外，见台账 `self-artifact`）。 |
| **D4 运行时产物与日志审计层** | ① 阶段 0 用 `find` + `git status --ignored` 清点磁盘上**未跟踪的执行产物**（`novel-output/`、`truth/`、`.superpowers/`、`*.log`、`.hypothesis/examples/`）；② 执行产物语义审计：章节/truth/decisions.json 与 pipeline 不变量的一致性、报告与审计波冗余、round 状态标记、token ledger 实际数据；③ 日志审计：先读 `src/shenbi/logging.py` 定位日志汇，再 grep ERROR/WARN/traceback/429/finish_reason/retry 异常并与 findings 关联；④ `.superpowers/sdd*` 历史状态中的已知问题/spec-deviations 转 pre-seeded findings | **100% 磁盘执行产物**（构建产物与工具缓存除外，见台账） |

**覆盖台账（G1 载体，双表）**：

- **表 A · tracked 文件**（`git ls-files` 全清单）：每文件恰好一条处置，合法值：
  - `deep-read`（链接 per-file 报告条目）；
  - `self-artifact`（**仅限** `$AUDIT_DIR` 自身文件——审计执行过程中持续变化，不参与 Z9 深读；由阶段 6 G6 meta-audit 与自检覆盖，每文件须有 meta-audit 记录链接）。
- **表 B · 磁盘执行产物**（阶段 0 清点）：每项恰好一条处置，合法值：
  - `audited` → 链接 D4 报告条目（`novel-output/`、`truth/`、`.superpowers/`、`*.log`、`.hypothesis/examples/` 等真实运行证据，**禁止跳过**）；
  - `generated-excluded(理由)` → 仅限**可再生成**的构建产物（`dist/`、`site/`），必须已验证再生成路径；
  - `cache-ignored` → 仅限工具缓存（`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`、`.cache/` 等），必须已验证 .gitignore 覆盖。

**不存在 `sampled` 处置值。** 两表零未处置是阶段 6 的硬门。novel-output 的 .gitignore 注释明确其为 "auditable pipeline verification"——正是本审计的必审对象。

**抽样种子登记**：所有抽样（D2 漂移、阶段 4 抽查、G6 meta-audit）的样本清单必须**预先**生成并登记进 progress.md（固定随机种子 + 规则），禁止事后挑选样本。

**D3 派发顺序（仅优化调度，不裁剪覆盖）**：按风险加权先审——(a) postmortem 聚集区（pipeline / gates / contracts / cost——历史 P0：CN3 覆盖 bug、TokenLedger dead-wire、finish_reason 盲点）(b) git churn 高 (c) coverage 缺口大 (d) 复杂。先审高风险区，覆盖不受影响。

---

## 3. 完备性门 G1-G7（唯一终止条件）

| 门 | 判据 |
|---|---|
| **G1 广度** | 台账表 A 每文件 = `deep-read` / `self-artifact`（仅限 `$AUDIT_DIR` 自身）；表 B 每项 = `audited` / `generated-excluded(理由)` / `cache-ignored`；两表零未处置、零空链接 |
| **G2 深度** | 每区初审通过**独立** fresh-context 复核（初审者≠复核者）：复核重读全文件，产出漏报/误报/覆盖空洞/严重度异议四类结论；T1-T16 线程报告齐全。**G2 只验证"复核结构发生过"；何时算收敛由 G4 判定** |
| **G3 验证** | D1 ①-⑫ 全部工具真实运行、输出归档；pre-existing 失败单列；CLI 冒烟全部执行过 |
| **G4 收敛（双轨）** | **硬收敛**：连续 2 轮 0 新 finding（含 M）→ 自动通过。**软收敛**：连续 3 轮无新 P0/P1 且每轮新增 ≤3 → 可申报，三件套缺一即 BLOCKED：① progress.md 记录触发条件满足的轮次计数证据；② 残余风险清单（末 3 轮全部新 finding 逐条列出）；③ 阶段 4 简报或 G7 人类追认。**含未解 P0 的区/线程禁用软收敛。** 角度条款与波动条款见 §1 原则 5 与 §3.5；轮次历史全部记录在案 |
| **G5 产出与对账（机械）** | 三项全过：(a) **语义覆盖**——下方命令输出为空（每条非 false-positive / 非 merged 的 finding ID 被 ≥1 份 spec 文本引用）；(b) **三方对账**——`grep -c '^### #' $INDEX` == `ls $SPECS_DIR/*.md \| grep -v INDEX \| wc -l` == 总纲 catalog 行数，且 ledger ID 无重复；(c) **spec 自审**——每份过 §8 自审四条 |
| **G6 Meta（分层深核，禁隐性稀释）** | 全样本 100% 机械核对（样本在磁盘 + 报告有条目）；**条目级深核下限**：Z1-Z6/Z8-Z10 = 全部样本、Z7 ≥35%、Z11 ≥25% 条目级 + **全量**类别级计数复演（独立重算关键计数 vs 报告声称）。低于下限 = **BLOCKING deviation**（人类追认）；final-report 必须披露**三重分母**：逐条深核数 / 登记样本数 / 总文件数（2026-08-14 run 实际逐条深核 228 条 vs 登记 552 条 vs 总 2738 文件，v2 下未披露）。假深读判定规则：报告声称检查的不变量与文件实际内容不符 / 声称运行过的验证命令无对应输出 / 报告内容与文件无实质关联 → 标 `fake-deep-read`：该文件重审 + 该 agent 全部条目进复查清单。结果记录 `meta-audit.md`（样本清单 + 逐条判定 + 复查清单 + **实际深核比例声明**） |
| **G7 人类裁决** | 阶段 6 产出 `final-report.md`（覆盖统计 / findings 统计 / 遗留风险）后**停止**，由人类拍板结束或追加审查。执行者禁止自行宣布完成 |

**G5(a) 语义覆盖命令**（在 `$AUDIT_DIR` 运行，期望输出为空；非空行即覆盖缺口，禁止进入阶段 6）：

```bash
awk -F'|' 'NR>2{gsub(/[ \t]/,"",$2); if($2 ~ /^(F|T|D)[0-9]/ && $11 !~ /false-positive|merged/) print $2}' \
  findings-ledger.md | sort -u | while read id; do
    grep -ql "$id" ../../specs/*.md 2>/dev/null || echo "UNCOVERED: $id"; done
```

**G5(b) ID 唯一性命令**（期望输出为空）：

```bash
awk -F'|' 'NR>2{gsub(/[ \t]/,"",$2); if($2 ~ /^(F|T|D)[0-9]/) print $2}' findings-ledger.md | sort | uniq -d
```

（两命令已在 2026-08-14 真实台账（786 条）上实测：前者输出空 = 786/786 全覆盖，后者输出空 = 零重复。）

### 3.5 攻击角度库（G4 每轮新增角度的强制来源）

同模型重复重读的边际产出递减——2026-08-14 run 的实证：收敛并出 final-report 之后，**新扫描角度**（而非更多重读）仍产出新 finding（F1322）。因此每轮复核必须引入此前未用的攻击角度。

**起步清单**（全部经 2026-08-14 后续扫描实证有效）：

1. **调用形状全仓核对**：对每个关键函数/门入口，grep 全部调用点逐一核对实参形状 vs 签名（含第 N 位置参数语义）。
2. **声明面↔磁盘面对账**：registry/manifest/INDEX 声明的条目 vs 实际文件清单双向 diff（声明有磁盘无 / 磁盘有声明无，两个方向都查）。
3. **词表/字面量全仓扫描**：status/state/classification 等受限词表的全部字面量 vs 唯一定义源（如 `contracts/enums.py`），含跨行三元表达式等易漏形态。
4. **引用断链重扫**：scenario/fixture/文档/配置中全部路径引用 vs 磁盘存在性（区分：路径前缀面 vs 完整路径面）。
5. **形状家族枚举**：同一数据结构的全部变体形状（如内层 dict 键族）逐一列举 vs 解析器分支覆盖。
6. **采样截断检查**：任何 top-N / head / limit 的输出验证未被截断（`| head` 之后的结论必须复核全量）。
7. **计数三方对账**：ledger 行数 vs 台账处置数 vs 报告声称数（本条为常设义务，见 G5/铁则 6）。

**泛化模板**（派生新角度用）：

- "所有 X 的调用点" —— 对任意核心符号 X；
- "声明 X 的每一处 vs 磁盘真实" —— 对任意 registry/清单/字段；
- "词表 X 的每个字面量 vs 唯一信源" —— 对任意受限枚举；
- "计数 A vs B vs C" —— 对任意双源以上的数字。

**使用规则**：每轮复核派发时由协调者指定本轮角度（从上述清单/模板派生），登记进该轮报告头部（`本轮新增角度: <名称>`）；连续两轮不得复用同一角度声明；协调者可扩充角度库，新角度入库须附产出证据（发现了什么 / 闭合了什么）。**全部起步清单用尽后**，才允许以泛化模板自由派生。

---

## 4. 阶段流程（0-6）

**全局规则**：每阶段结束时更新 `progress.md`（§9 格式）；阶段间严格串行（阶段 2 与阶段 3 可交错并行）。

### 阶段 0 · 清点与基线

- **动作**：
  1. 建目录：`$AUDIT_DIR/{progress.md, coverage-ledger.md, findings-ledger.md, zone-reports/, thread-reports/, d1/, zones/}`（progress/ledger 用 §7 schema 初始化）。
  2. 运行 `git ls-files` 生成台账表 A（全部 `unreviewed`；`$AUDIT_DIR` 自身文件标 `self-artifact`）；运行 `find . -not -path './.git/*' -not -path './.venv/*'` + `git status --ignored` 清点磁盘执行产物与缓存目录，生成台账表 B（执行产物 → 待审；构建产物 → 验证再生成；工具缓存 → 验证 .gitignore）。
  3. 按 §5 分区矩阵的 glob 生成 `zones/Z<N>.files` 权威文件清单（Z11 用台账表 B 的执行产物清单），供子 agent 读取，避免各自 glob 漂移。
  4. **登记抽样种子**：D2 漂移抽样清单、阶段 4 抽查种子、G6 meta-audit 种子（≥20% 样本清单，按 §3 G6 分层要求生成）预先生成并写入 progress.md。
  5. 运行 D1 全套（①-⑫，§2），输出归档 `d1/d1-baseline.md`；D1 发现的独立问题记入 findings ledger（编号段 `D1xx`）。
  6. 提交 checkpoint：`docs(audit): phase-0 inventory + D1 baseline`。
- **退出**：台账 + 文件清单 + 抽样种子生成完、D1 归档、progress.md 更新为"阶段 1 进行中"。

### 阶段 1 · 整体层审查（协调者亲自，不派发）

- **读**：`AGENTS.md`、`docs/architecture/overview.md`、`docs/framework/gates.md`、契约相关文档、`justfile`、`pyproject.toml`、`docs/superpowers/specs/INDEX.md` 及活跃 spec、`.github/workflows/` 全部。
- **审查维度**（每维度必须给出结论：通过 / findings 编号）：
  1. 架构一致性——AGENTS.md 声明的目录结构、命令、分层 vs 实际；
  2. 契约单一信源体系——frontmatter → 生成物 → 执行 的链路设计是否有洞；
  3. pipeline 状态机设计——T2/T3 阶段模型、并行调度、崩溃恢复设计；
  4. G0-G7 门体系——门间依赖、不可跳过性、幂等性设计；
  5. CI 设计——8 个 workflow 与 `just check` 的一致性、覆盖缺口；
  6. 文档体系——specs/INDEX/archive 流程、文档间矛盾；
  7. 依赖与供应链顶层设计——pyproject/uv.lock 声明面、重型依赖必要性、锁定策略；
  8. 安全顶层设计——凭证/密钥的存放与使用面、子进程调用面、executor_config/run_pipeline.sh 的 shell 语义；
  9. **性能与资源效率顶层设计**——pipeline 每章循环的成本模型（随章数/卷数/truth 体积的增长曲线）、全量重读 vs 增量读的架构选择、缓存层有无（深查归 T16）。
- findings 编号段：`F0xx`。
- **退出**：9 维度全部有结论并录入 ledger；progress.md 更新。

### 阶段 2 · 分区深度审查（Z1-Z11）

- **派发协议**：
  1. 若执行环境支持子 agent 派发：每区一个 **fresh-context 只读** 初审 agent（并行）。**大区可拆**：Z7 按 tests/ 子目录拆 2-4 个 agent、Z8 按 skill 名首字母拆 2-3 个——拆多 agent 时**每 agent 一个独立段文件**（见写协议），编号段先分配防冲突。**并行上限**：同时并行 agent ≤6（协调者调度，避免资源争抢）。
  2. 无子 agent 能力：协调者逐区串行亲审，流程不变。
  3. 子 agent prompt = §5 模板 + 该区 rubric **完整复制** + **§8.1 严重度决策表完整复制** + 该区文件清单路径 + 报告输出路径（段文件）+ 只读禁令。
  4. **写协议（铁则 6）**：每 agent 只写自己的段文件 `zone-reports/Z<N>.<seg>.md`（如 `Z7-a.md` / `Z7-b.md`），**禁止任何 agent 直接写共享的 `zone-reports/Z<N>.md`**（Write 是全量覆盖，并行写 = 互相抹除）；协调者收齐全部段文件后合并为 `Z<N>.md`（每段标注来源 agent），合并完成后该区才进入复核。
- **协调者收报告后**（每区）：
  1. 更新 coverage-ledger：该区文件全部 `deep-read` + 链接报告条目；
  2. **逐条核实** findings：打开真实文件核对 file:line 证据与结论，**并按 §8.1 决策表复验严重度**（复核 agent 提出的"严重度异议"在此裁决并记录）；不实 finding 在 ledger 标 `false-positive`（附理由），核实通过的标 `verified`；
  3. 派发**独立复核 agent**（fresh-context，≠ 初审者）：重读该区全文件 + 初审报告，任务 = 找漏报（初审没发现的 finding）+ 误报（初审发现但站不住的）+ 覆盖空洞 + **严重度异议**（初审定级不符 §8.1 决策表的条目）；复核 findings 编号段 = 该区段内剩余号；**复核 agent 无权修改初审 findings 的严重度，只能提出异议**；**每轮复核派发时指定本轮攻击角度**（§3.5 派生，写入该轮报告头部 `本轮新增角度:`）；
  4. 复核有 0 新 finding → 该区硬收敛计数 +1（连续 2 轮即 G4 硬收敛通过）；有 → 更新报告，**再派新一轮复核**（新角度），直到 G4 硬收敛、或满足 G4 软收敛条件并完成三件套。**每轮计数高于上轮 → 当轮波动分析一行**（原则 5）。checkpoint commit。
  5. 可选（上下文压力大时）：派 scribe agent 做**机械录账**（从段文件转抄 findings 行进 ledger），核实与裁决仍由协调者亲自。
- **退出**：Z1-Z11 全部按 G4 双轨收敛（软收敛区已在 progress.md 登记）；progress.md 记录每区轮次历史（含每轮角度声明）。

### 阶段 3 · 跨模块审计线程（T1-T16，与阶段 2 可交错）

- 每条线程一个 fresh-context 只读 agent（无子 agent 能力则协调者亲自逐条），prompt = §6 模板 + 线程 rubric 完整复制 + §8.1 严重度决策表完整复制。
- 线程 findings 编号段 `T{n}xx`（T1→T1xx … T16→T16xx）。
- 协调者对线程报告同样逐条核实 + 独立复核（写隔离：线程报告由单 agent 写，无并行冲突）；线程收敛同样按 G4 双轨判定。
- **退出**：16 条线程报告齐全且全过复核。

### 阶段 4 · 根因聚类与校准（协调者亲自）

1. **去重**：findings ledger 按「根因」聚类——同一根因的多处表现**合并**（主条目保留，其余标 `merged-into-Fx`）。去重键 = 根因描述，非症状描述。
2. **严重度校准**：每条按 §8.1 决策表定 P0/P1/P2/M；同根因取最高。**校准升级（M/P2 → P1/P0）= 该 finding 所属区/线程强制追加一轮 fresh-context 复核**，确认无同类漏网后该区才算重新收敛；降级必须记录理由。
3. **根因簇图**：跨 finding 的根因聚类（如"dead-wire 簇"），写入总纲 spec 草稿。**每条根因标注证据等级**：`实验佐证`（附已运行命令+输出）或 `推理假设`（纯阅读推断——只读审计无法实验验证根因，此标注让下游知情：spec 与 SDD 阶段 1 驳斥门**优先核验"推理假设"级根因**）。
4. **抽查复核（findings 结论核实，与 G6 区分）**：fresh-context agent（或协调者亲自）按阶段 0 登记的种子抽查 **≥10% 已 verified findings**，核对"结论 ↔ 证据"一致性（抓过度推断/证据不足/结论与证据脱节）；结果记录。**G6（阶段 6）是另一件事**：per-file 报告**真实性**抽查（抓假深读），两套抽样独立、样本清单均预先登记。
5. **触发式强制简报**（v2"可选简报"升级为条件强制）：findings 总数 ≥300，或**任一区/线程以软收敛关闭** → 必须向人类简报一次（findings 统计 + 根因簇图 + 软收敛区残余风险清单），人类可指示方向（继续 / 聚焦某簇 / 追加角度 / 提前终止）；简报**不替代** G7。未触发条件时简报仍可选。**$UNATTENDED=true 时：简报全文写入 progress.md 后按"继续"默认方向执行，不等待回复（§1.6）**。
- **退出**：ledger 无未合并的重复根因；严重度定稿且升级触发的补复核已收敛；根因证据等级标注完成；简报义务（若触发）已履行。

### 阶段 5 · spec 产出（协调者亲自）

- 按 §8 契约产出：1 总纲 catalog spec + 每 finding 独立子 spec + M 批量 spec + `$INDEX` 登记。
- **退出**：G5 三项全过——(a) 语义覆盖命令输出为空（**禁止像 2026-08-14 run 那样在阶段 5 只覆盖 10/118 P1 的情况下放行**）；(b) 三方对账通过；(c) 每 spec 过自审。命令与输出粘贴进 progress.md。

### 阶段 6 · 覆盖证明 + meta-audit + 人类裁决

1. G1 终检：台账零 `unreviewed`、零空链接（`self-artifact` 条目必须各有 meta-audit 记录链接）；
2. **G6 meta-audit**（按阶段 0 登记的种子执行，分层下限见 §3 G6）：抽样 ≥20% per-file 报告条目 vs 真实文件，**按区成层**（每区至少抽 1 条；高风险区 Z3/Z4/Z5/Z11 与低置信度文件必抽，随机补足至比例）。结果写入 `meta-audit.md`（样本清单 + 逐条判定 + 复查清单 + **实际深核比例声明**——逐条深核数 / 登记样本数 / 总文件数三重分母）；
3. 写 `final-report.md`：覆盖数字（deep-read 文件数 / 总文件数 / excluded 清单 / **G6 三重分母**）、findings 统计（按严重度）、轮次历史（含软收敛区及其追认状态）、遗留风险（低置信度文件列表、未实机验证面）。**全部统计数字必须由机械命令产生**（铁则 6），命令与输出粘贴进报告附录：

   ```bash
   # findings 按严重度机械统计（在 $AUDIT_DIR 运行；输出外任何口径的数字不得出现在报告正文）
   awk -F'|' 'NR>2{gsub(/[ \t]/,"",$5); if($5 ~ /^P[012]$|^M$/) c[$5]++} END{for(k in c) print k, c[k]}' findings-ledger.md
   # 词表外/异常严重度行清点（应输出 0；非 0 = ledger 本身有格式缺陷，先修台账再出报告）
   awk -F'|' 'NR>2{gsub(/[ \t]/,"",$2); gsub(/[ \t]/,"",$5); if($2 ~ /^(F|T|D)[0-9]/ && $5 !~ /^P[012]$|^M$/) print $2, "->", $5}' findings-ledger.md
   # 台账处置机械统计
   grep -c '| deep-read |' coverage-ledger.md; grep -c '| self-artifact |' coverage-ledger.md
   ```

   （第一个命令在 2026-08-14 真实台账上实测输出 P0 5 / P1 118 / P2 492 / M 165——与手抄报告的 496/166 差异正是手抄漂移的实证。）
4. checkpoint commit；
5. **停止，向人类汇报 final-report 摘要，等待裁决**（G7）。收到"继续"则从指示处续审；收到"结束"才可收尾（不改代码，只留 spec）。

---

## 5. 分区矩阵 Z1-Z11

每区列出：文件范围（glob）、重点 rubric 维度。派发时按下方模板组装子 agent prompt。

| 区 | 文件范围（glob，以 `git ls-files <glob>` 实际结果为准） | 重点 rubric 维度 |
|---|---|---|
| Z1 | `src/shenbi/*.py`（顶层 19 文件，不含子目录） | 异常层次完整性（typed exceptions 全链使用）、phase_runner 状态机正确性、safe_write/幂等写、structlog 无 print、recovery 语义 |
| Z2 | `src/shenbi/contracts/`、`src/shenbi/dispatcher/` | 契约单一信源、字段级 reads 过滤实现与 escape hatch（缺字段→全文件+WARN）、派发协议与重试参数 |
| Z3 | `src/shenbi/pipeline/` | 状态机、并发调度、重试经济、truth 写路径幂等、token 计量（历史 P0 聚集区） |
| Z4 | `src/shenbi/gates/`（含 g4 checkers） | 门函数幂等（纯验证无副作用）、decisions.json G4 schema、P2.5 rationale 规则（routine+low 禁 rationale / manual_override+high 必 rationale） |
| Z5 | `src/shenbi/audit/`、`src/shenbi/cost/`、`src/shenbi/orchestration/` | TokenLedger 接线（计量代码未接线 = dead-wire 模式）、审计波调度、成本分摊正确性 |
| Z6 | `src/shenbi/records/`、`src/shenbi/trace/`、`src/shenbi/text/`、`src/shenbi/config/`、`src/shenbi/plugins/`、`src/shenbi/skill_utils/` | 确定性助手正确性（纯函数、边界）、序列化、配置治理、text 处理边界 |
| Z7 | `tests/`（16 子目录，可拆 2-4 agent） | 测试真实性（走真实代码路径，非纯 mock）、fixture 真实性（G0.9：真实输出或上游生成副本，禁手写 mock）、覆盖缺口、测试自身 bug、golden/baseline 漂移、**skip/xfail 逐条处置**（D1⑪ 清单：`keep(理由)` / `enable(应启用)` / `stale(应删除)` / `masking(掩盖真实失败)`） |
| Z8 | `skills/`（74 skill，可拆 2-3 agent） | description ≤500 字符且只写触发条件（不写做什么）、DOT 流程图与正文一致、decisions.json 声明 vs 实际产出、reads 字段 vs truth 文件实况、anti-rationalization 表完整性、**确定性替换候选初筛**（每 skill 判定"是否存在可被 Python 确定性替代的环节"→ 候选清单交 T14 评估，判据见 §6 T14） |
| Z9 | `docs/` + 根级 `*.md`（AGENTS/README/CHANGELOG/CODE_OF_CONDUCT/CONTRIBUTING/SECURITY/goal-prompt/command-to-give/outline-example） | 文档↔代码漂移（file:line 引用抽查，按阶段 0 登记的抽样清单）、INDEX 与 archive 一致性、活跃 spec 间矛盾、meta 文档自身（含本 prompt 的设计 spec）。**`$AUDIT_DIR` 自身文件不深读**（台账 `self-artifact`，G6 覆盖） |
| Z10 | `.github/`、`pyproject.toml`、`justfile`、`uv.lock`、`tools/`、`scripts/`、`plugins/`、`benchmarks/`、`executor_config.toml`、`run_pipeline.sh`、`mkdocs.yml`、`cliff.toml` | CI 与 `just check` 一致性（justfile 是权威，workflow 不得漂移）、脚本正确性（含 subprocess/shell 调用面）、配置漂移、依赖锁定卫生（配合 T13）、shell 语义与命令注入面（配合 T12） |
| Z11 | **磁盘执行产物**（清单 = 台账表 B，阶段 0 生成）：`novel-output/`（含 `test-validation/`、`validation-results/`、`xinghuo-ranqiong/` 等真实运行）、`truth/`、`.superpowers/sdd*`、`*.log`（先读 `src/shenbi/logging.py` 定位日志汇） | 产物与 pipeline 不变量一致性（章节格式 / truth 结构 / decisions schema + P2.5 真实数据 / round 状态标记 / token ledger 实际值）、报告与审计波冗余、日志异常（ERROR/traceback/retry/429/finish_reason）、sdd 历史已知问题与 spec-deviations 转 pre-seeded findings |

**通用 rubric 维度（每区每个文件必查，与重点维度叠加）**：
1. 正确性：逻辑错误、边界条件、off-by-one、None/空输入；
2. 错误处理：无 bare except 吞错、异常不丢失上下文；
3. 签名一致性：函数签名 vs 调用方（grep 调用方验证）、plan/spec 中声明的签名 vs 实际；
4. 序列化安全：涉及 ProcessPool / threading / multiprocessing 的 pickle 边界；
5. 枚举/状态字符串：唯一定义在 `src/shenbi/contracts/enums.py`（相关文件时）；
6. 测试对应：相关测试存在且真实（读 tests/ 对应文件）；
7. 文档引用：相关 docs 的 file:line 引用未漂移（超出 ±5 行即记 finding）；
8. **覆盖缺口处置**：D1⑥ 报告中该文件的未覆盖行逐条给处置——`dead-code`（死代码→finding）/ `must-test`（需补测→finding）/ `acceptable(理由)`（可接受）;
9. **安全初查**：文件打开路径（相对/绝对、`../` 穿越）、子进程/shell 调用参数注入面、凭证与敏感数据引用；完整安全审查归 T12。
10. **复杂度与资源效率（轻量必查，深查归 T16）**：函数/循环的数据规模假设是否显式（章数/卷数/truth 体积）；是否存在每次调用全量重算/全量重读（可增量/可缓存点）；热路径超线性增长点标记。

**子 agent prompt 模板（分区版，派发时按模板 + rubric 复制组装）**：

```
你是全项目深度审查的分区初审 agent，负责 Z<N>（只读）。
# 任务
对文件清单 `$AUDIT_DIR/zones/Z<N>.files` 中的【每一个】文件做语义深读审查，
产出 per-file 报告，写入你的**独立段文件** `$AUDIT_DIR/zone-reports/Z<N>.<seg>.md`
（用 Write 工具创建/更新你自己的段文件；禁止写共享的 `zone-reports/Z<N>.md`）。
# 只读禁令（违反 = 任务失败）
除你的段文件外，禁止创建/修改/删除任何仓库文件；禁止 git add/commit；禁止运行
会写入仓库的命令（pytest 只允许 --collect-only 与单个纯读测试文件）。
# 审查 rubric（每个文件必查）
<此处完整复制：通用维度（1-10）+ Z<N> 重点维度，逐条列出，禁止只引用表名>
# 严重度决策表（判定 findings 严重度时逐条对照）
<此处完整复制：§8.1 严重度决策表全文，禁止只引用表名>
# 报告 schema（每个文件一条，必须覆盖全部清单文件，缺一条 = 未完成）
### <file path>
- 处置: deep-read
- 声称检查的不变量: [列表——本文件应维护的具体不变量，写不出来 = 没审]
- findings: [F<编号> 或 无]
- 验证命令: [实际运行过的命令 + 输出摘要；没运行的写"未运行"]
- 置信度: high|medium|low（low 必须说明原因）
# findings 格式（每条）
F<编号> | 标题 | 类别(error|optimization|security|deps) | 严重度(P0|P1|P2|M，按决策表) | 证据 file:line | 根因 | 验证命令+输出 | 建议方向
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

## 6. 跨模块审计线程 T1-T16

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
| T10 | 历史修复回归核验：从 archive spec / INDEX / **既往 `audit-runs/*/final-report.md` 的修复声明**提取全部"已修/已合并(PR #N)"声称，逐一 grep 修复签名在当前代码中是否仍存在（例：TokenLedger 接线、finish_reason 检测、truth_io upsert 调用方全覆盖、torch-bump 处置 follow-up）；消失 = 回归 finding | 归档 spec 的 P0 声明 + 既往审计产物 |
| T11 | 运行时行为核验：实际运行 `tests/pressure-tests/`、`tests/benchmark/`（对比 `tests/baselines/`）、`tests/golden/`、差分测试；对全部 gate checkers + scoring/contracts 确定性助手跑 mutmut 突变测试（量小模块全跑）；重放 `.hypothesis/examples/` 失败样本；**并发运行时压力**（对 1-2 个并行调度模块做重复并发运行，观察竞态/共享状态）；**运行时幂等核验**（同一 phase 连续跑两次，关键产物 diff 一致）；**同 seed 全 pipeline 重跑确定性**（关键产物 hash 对比，若 T3 层支持）；**flaky 抽检**（核心测试子集重复运行 ≥3 次，不稳定 = flaky finding）；**stub 实机 smoke**：grep 仓库是否存在离线/stub 派发模式（`stub\|dry_run\|offline\|replay`）——存在则以 1-3 章迷你 pipeline 实跑全链（G0-G7 markers、truth 写路径、token ledger、审计波），产物入 Z11 证据；**不存在则记 finding（P2 可测性缺陷：pipeline 无离线可执行模式，运行时路径无法在不触发真实计费的前提下被审计验证）并在 final-report 遗留风险声明**（2026-08-15 实况：`internal` 模式硬拒绝无 LLM 后端、`trace/replay.py` 是签名链校验非派发 stub——即当前无可用的离线模式）；一切覆盖率相关运行独占 `COVERAGE_FILE` 且与本线程以外的 pytest 互斥（原则 7）；**一切运行入口必须非交互**（§1.6）：timeout 包裹 + stdin 隔离，禁止触发等待人工 checkpoint 决策的真实 pipeline 入口（`just pipeline-init` / `just pipeline-review` 等交互形态），交互阻塞 = 记 finding + kill + 继续；结果全部作为 findings 证据 | pyproject `[tool.mutmut]`、tests 分层 |
| T12 | **安全**：凭证泄露（D1⑧ 命中逐条语义确认 + 配置文件/文档中的密钥引用 + `git log` 历史残留）、命令注入（subprocess/shell 调用点、`run_pipeline.sh`、executor_config 的 shell 语义）、路径遍历与任意文件读写面（capability_fs、dispatcher 文件参数、truth 写路径）、prompt injection 面（skill/truth/novel 内容进入 LLM 决策链的注入面评估）、敏感数据落盘（日志/产物中的 key/token） | D1⑧ 结果 + `.github/workflows/` security workflow + AGENTS.md |
| T13 | **依赖与供应链**：D1⑨ 漏洞清单逐条核实（是否真实可达、修复版本）、未使用依赖（D1⑩ 清单逐条确认）、重型依赖必要性（torch 等是否真被引用、能否移除/降级）、许可证兼容性、uv.lock 可复现性（`uv lock --check` + `uv sync --frozen` 试装结果）、`.venv` 陈旧依赖对照、plugins 依赖面 | D1⑨⑩⑫ 结果 + INDEX 历史（如 torch-bump 处置待 follow-up） |
| T14 | **确定性技能替换**：承接 Z8 候选清单，用 repo 既有先例（`skill_utils/` 9 个确定性助手 + pipeline 助手）的判据逐候选评估——"该 LLM 调用是否可被确定性 Python 替代（部分或全部）"；每候选产出 payoff 数值化（消除的调用次数 / 省 token / 引入风险 / 实现成本）+ 优先级；**消除 1 次不必要 dispatch = 省 100% 该调用 token，单候选 payoff 最高** | archive `2026-08-01-deterministic-skill-replacement-audit-design.md` + `src/shenbi/skill_utils/` |
| T15 | **git 历史考古**：`git log` 分析——revert-revert 周期（`--grep=revert`）、未完成迁移（半迁移标记文件/代码）、孤儿分支（`git branch -a` vs 已归档）、churn 簇（`git log --name-only --pretty=format: | sort | uniq -c | sort -rn` 高频文件 vs findings 关联）、大文件/二进制入库（`git rev-list --objects --all` 体积）、历史凭证残留（转 T12） | git 历史本身 |
| T16 | **性能与资源效率**（v3 新增——v2 中计算性能整类缺席，仅 token 成本有 T4/T14）：① **热路径复杂度标注**——pipeline 每章循环体逐步标注计算/IO 复杂度（输入规模 = 章数 / 卷数 / truth 体积），标记全部超线性增长点（重点：truth 全量重读 vs 增量读、上下文组装拼接策略、审计波每波扫描集、契约幂等重算）；② **profiling 实测**——cProfile 跑全部确定性助手（skill_utils/contracts/gates/scoring），若 T11 stub smoke 可跑则附 3 章迷你 pipeline 的 profile，热点前 20 函数逐一判定 `必要 / 可缓存 / 可增量 / 可移除`；③ **内存**——无上界缓存 / 全量加载点（novel-output、fixtures、truth 加载策略）逐个标注数据生命周期；④ **I/O**——同文件重复读写、每 dispatch 重解析全量 truth 的模式；⑤ **启动**——CLI 入口 import 面（lazy import 机会）；⑥ **步骤复用与重复 dispatch**——pipeline 步骤间的中间产物是否被下游复用（还是各自从头重算）；对 Z11 的 dispatch 记录 / trace / token ledger 做**prompt 指纹去重统计**（相同 skill + 相同上下文指纹的重复派发 = 直接 token 浪费 finding）；dispatch 结果有无 memoization / 缓存层及其实际命中率（数据不可得时记"不可审计"而非跳过）。**每条性能 finding 必须附增长曲线断言**：输入规模 ×2 → 成本如何变化；静态推导或 profile 实测二选一并注明是哪种 | §5 通用维度 10、阶段 1 维度 9、D1⑥ 覆盖缺口交叉 |

**线程 agent prompt 模板**：同 §5 模板，改动三处——任务改为"跨模块线程 T<N>，横切审查下列主题"；报告写入 `thread-reports/T<N>.md`（单 agent 写，无并行冲突）；rubric 段复制该线程的审查内容 + 涉及文件定位方法；编号段 `T<N>00-T<N>99`（T16 用 `T16xx`）。

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
| 2 分区深度审查 | in_progress | Z1:初审✓复核(角度:调用形状)1/1✓ … |
| 3 线程 | pending | — |
| 4 聚类校准 | pending | — |
| 5 spec 产出 | pending | — |
| 6 覆盖证明+裁决 | pending | — |
## 抽样种子登记（阶段 0 生成，禁止事后修改）
- D2 漂移抽样清单: [文件:引用 列表]
- 阶段 4 抽查: seed=<固定值>，≥10% 已 verified findings
- G6 meta-audit: seed=<固定值>，≥20% per-file 报告，按区成层
## 软收敛登记（仅 G4 软收敛的区/线程；硬收敛区不填）
| 区/线程 | 触发证据（末3轮计数） | 残余风险条目（finding ID） | 追认状态（简报/G7 + 日期） |
|---|---|---|---|
## 波动分析登记（每条一行）
| 区/线程 | 轮次 | 本轮 vs 上轮 | 发现角度 | 上轮为何漏 |
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

- 类别：`error`（bug/契约违反/不一致/测试失效）| `optimization`（**性能/资源**/token/架构/可维护）| `security`（凭证/注入/路径/敏感数据）| `deps`（依赖/供应链）。
- 严重度：P0/P1/P2/M，**一律按 §8.1 决策表判定**（协调者核实时复验，复核异议在此裁决）。**严重度单元格只允许 `P0`/`P1`/`P2`/`M` 四个字面量**（G5/阶段 6 机械统计按此词表解析，词表外值会被机械统计暴露）。
- 状态机：`open`（已记录）→ `verified`（协调者核实）→ `merged-into-Fx`（去重合并）→ `specced`（spec 已产出）；`false-positive`（核实不成立，保留记录+理由）。

### 7.3 coverage-ledger.md（G1 台账）

```markdown
# 覆盖台账
| path | 处置 | 报告链接 | 理由 |
|---|---|---|---|
| src/shenbi/scoring.py | deep-read | zone-reports/Z1.md#scoring | — |
| docs/superpowers/audit-runs/$AUDIT_DATE/progress.md | self-artifact | meta-audit.md#progress | 审计自身文件 |
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
  每条 finding 正文含：症状 / 证据 file:line / 根因（**标注证据等级：实验佐证 | 推理假设**）/ 分类 / 影响 / 假设+验证命令 / 修复方向 / 数值化标准。
- **总纲**：`$AUDIT_DATE-full-project-audit-design.md`（catalog：每 finding 一行 + 根因簇图 + 建议执行顺序 + 覆盖统计；行数计入 G5(b) 三方对账）。
- **INDEX 登记**：1 总纲 + N 子 spec + 1 M 批量，顺序号续排；更新活跃 spec 数（登记数进 G5(b) 对账）。
- **spec 自审**（每份）：① 无 TBD/TODO/占位符；② 内部无矛盾；③ 范围单聚焦（一个根因）；④ 证据无歧义（file:line 唯一）。
- 提交：`docs(audit): findings specs — <总纲+子spec列表>`。

### 8.1 严重度决策表（唯一判定依据，铁则 5）

| 严重度 | 触发条件（满足任一即该级；多条件取最高） | 典型例子 |
|---|---|---|
| **P0** 阻塞级 | 数据损坏/丢失或 pipeline **静默产出错误结果**；安全漏洞（凭证泄露、任意命令/文件执行）；契约被静默违反导致错误执行 | truth 覆盖 bug 复发、TokenLedger 少计、subprocess 注入、路径穿越写任意文件 |
| **P1** 高 | 违反 AGENTS.md **显式契约**；正常路径可复现功能错误；显著 token 浪费（单调用 >10%）；**热路径性能缺陷致生产规模不可行（每章循环内超线性增长，输入规模翻倍成本 >2× 且随章数累积）**；测试失效**掩盖**真实缺陷；并发竞态；skip/xfail 判定为 `masking` | decisions schema 违反、G2 校验洞、重试放大、flaky 测试掩盖 bug、truth 每章全量重读 |
| **P2** 中 | 边界/错误处理缺陷（吞异常、None/空路径）；文档↔代码漂移（file:line 超出 ±5）；死代码/未接线；优化机会（含确定性替换 payoff 中等者、**增长曲线断言支撑的性能优化**、可测性缺陷如无离线执行模式）；skip/xfail 判定为 `stale` | bare 防御缺失、INDEX 漂移、dead-wire 代码、同文件重复读写 |
| **M** 文案 | 错别字、命名不一致、格式、过期注释 | — |

**判定规则**：
1. 证据驱动——按证据事实定级，禁止按"影响心情/工作量"定级；
2. 不确定时**取更高严重度**（reviewer 可提"严重度异议"，协调者裁决）；
3. 复核 agent **无权单方降级**初审严重度（铁则 5）；
4. 阶段 4 校准**升级** → 该 finding 所属区/线程强制补一轮复核（§4 阶段 4）；
5. M 级不设独立 spec，全部合入批量 spec（§8）。

---

## 9. checkpoint / 恢复协议

- **checkpoint commit 时机**：阶段 0/1/4/5/6 完成后各一次；阶段 2/3 每区（每线程）G4 收敛（硬收敛，或软收敛三件套齐）后一次。提交消息 `docs(audit): <阶段/zone> checkpoint`。
- **会话结束前**（每轮）：更新 progress.md 会话日志（下一步动作写具体、待核实 findings 列 ID）→ commit → 结束。
- **新会话恢复第一步**：读 `$AUDIT_DIR/progress.md` → 按阶段状态机继续；先 `git status` 确认工作树干净（除未提交的审计文件）。
- **恢复后的 Iron Law**：恢复点之前的结论只可作索引，**声称通过必须本轮重跑验证**。
- **prompt 升级处理**（本审计已发生 v1→v2→v3）：恢复时对比 prompt 版本与执行版本；已按旧版本完成阶段的结论有效，但**未完成阶段必须按新版本规则执行**。v3 相对 v2 的恢复补跑项：① 未收敛区改按 G4 双轨判定（含角度条款）；② 阶段 5 出口补跑 G5(a)(b) 机械对账命令并粘贴输出；③ 阶段 3 补跑 T16（若未跑）；④ 阶段 6 的 final-report 统计与 G6 披露按 v3 机械命令/三重分母重出。

---

## 10. Anti-Rationalization 守则

| 执行者可能说 | 回应 |
|---|---|
| "时间不够，这区抽样吧" | 禁止。无时间盒；台账不存在 sampled 处置（§2）。 |
| "工具绿了 = 没错误" | 禁止。D1 只是基线；语义错误跑不出来。 |
| "已经复核 3 轮了" | 收敛按 G4 双轨判定：硬收敛自动；软收敛三件套（证据/清单/追认）缺一即 BLOCKED。轮次历史必须记录。 |
| "这文件一看就是样板，快速过" | 禁止。per-file 报告必须列出声称检查的不变量，写不出来 = 没审。 |
| "子 agent 报告成功" | 协调者逐条打开真实文件核对，不轻信。 |
| "生成物目录可以整目录跳过" | 表 A 必须逐个声明 `generated-excluded` + 再生成性验证 + 理由；表 B 执行产物（novel-output/truth/日志）是真实运行证据，禁止归为"生成物"。 |
| "运行产物是 untracked，不用审" | 禁止。D4 层 + 表 B 必审；novel-output 的 .gitignore 注释明确其为 auditable pipeline verification。 |
| "历史 spec 说已修，直接信" | 禁止。T10 逐条 grep 核验修复签名仍在当前代码中。 |
| "pressure/benchmark/mutation 太慢，跳过" | 禁止。T11 必须实际运行；慢不是理由（无时间盒）。 |
| "审计完成" | 禁止自宣。G1-G6 全过 + 人类裁决（G7）。 |
| "发现太多先记着后面写" | 发现即录入 findings ledger（当轮），禁止内存暂存。 |
| "用了 skill 就能跳过 prompt 的步骤" | 禁止。skill 是增强非替代（§1.5）；白名单之外禁止；使用必粘贴输出。 |
| "环境没有 skill 所以完不成" | 禁止。本 prompt 无 skill 环境完整可执行（自包含基线）。 |
| "没有子 agent 能力，所以抽样" | 禁止。降级为协调者串行全量，绝不抽样。 |
| "这 finding 和另一个类似，我口头合并了" | 禁止。合并必须走 ledger `merged-into-Fx` 标记，理由写入。 |
| "文档没改动就不用复核" | 禁止。重审无条件，doc-only / 配置文件无例外。 |
| "这 finding 标 M 就不用再复核了" | 禁止。收敛判定含 M（G4 硬收敛 = 0 新 finding 含 M）；严重度只按 §8.1 决策表，复核无权降级。 |
| "并行 agent 都写同一个报告文件，没事" | 禁止。写隔离（铁则 6）：每 agent 独立段文件，协调者合并；并行写共享文件 = 数据污染，成果作废。 |
| "校准把它升到 P1 了，但区已经过 G2" | 禁止。严重度升级 → 该区/线程强制补一轮复核（§4 阶段 4）。 |
| "skip 的测试是别人故意关的，不用管" | 禁止。Z7 必须逐条处置 D1⑪ 清单（keep/enable/stale/masking）。 |
| "安全/依赖有 CI workflow 了，不用审" | 禁止。workflow 只覆盖 CI 触发路径；T12/T13 是全量语义审查（含 git 历史、供应链）。 |
| "meta-audit 抽 20%，我挑好过的抽" | 禁止。抽样种子阶段 0 预先登记（§2），高风险区必抽，禁止事后挑选。 |
| "软收敛差不多得了，不用记不用追认" | 禁止。软收敛三件套：轮次计数证据 + 残余风险清单 + 人类追认（简报/G7），缺一即 BLOCKED；含未解 P0 的区禁用软收敛（G4）。 |
| "这个角度上轮已经查过了" | 每轮复核必须声明 ≥1 个本轮新增攻击角度（§3.5），连续两轮不得复用同一角度声明；全部起步清单用尽后才允许模板自由派生。 |
| "Z7/Z11 样本太大，深核比例降一点没事" | 禁止。G6 分层下限（Z7 ≥35%、Z11 ≥25% + 全量类别级复演）是硬线；低于下限 = BLOCKING deviation + final-report 三重分母披露。 |
| "统计数字我记得，直接写进 final-report" | 禁止。铁则 6：数字由机械命令产生并粘贴输出（§4 阶段 6）；词表外严重度行 = 台账格式缺陷，先修再报。 |
| "这轮比上轮发现还多，正常波动不用记" | 禁止。波动条款（原则 5）：当轮记一行波动分析；累计 2 次同盲区 → 强制新角度轮。 |
| "性能问题没有 benchmark 就没法审" | 禁止。T16 静态复杂度标注 + 增长曲线断言即证据；可实测的附 profile 输出。 |
| "根因我心里有数，不用标证据等级" | 禁止。阶段 4 每条根因标 `实验佐证 / 推理假设`（§4 阶段 4.3）；spec 正文同步标注（§8）。 |
| "仓库没有 stub 模式，实机验证就算了" | 禁止静默跳过。T11：无离线模式 → 记 P2 可测性 finding + final-report 遗留风险声明。 |
| "命令停在等 stdin / pipeline 卡在 checkpoint 等人工确认，先挂着" | 禁止。非交互纪律（§1.6）：timeout 包裹 + kill + 记 finding + 继续；$UNATTENDED 下人类门一律"记录 + 默认方向（继续）"，G7 终点停止是唯一合法等待点。 |

---

## 11. 成本预期与诚实声明

- **规模**：src 199 文件/29K 行 + tests 284 文件/36K 行 + skills 74 + docs 200 + CI/工具链（`git ls-files` ≈ 2700 文件）+ 磁盘执行产物（novel-output/truth/.superpowers/日志等，台账表 B）。线程 T1-T16 共 16 条（T12 安全 / T13 依赖 / T14 确定性替换 / T15 git 考古为 v2 新增；**T16 性能为 v3 新增**——复杂度标注为文档型审查 + profiling 为机械运行，成本中等）；D1 新增 ⑧-⑫ 为机械扫描（分钟级）。
- **诚实代价**：全量深读 + 独立复核的串行等价工作量 **100+ 小时**；有子 agent 并行派发时墙钟约 **20-40 小时、跨 10-20 个会话**。这不是慢，这是"最深入最广"的真实价格。
- **禁止自我降级**：发现远超预期时不许把 D3 降级为抽样、不许减复核轮次——只能按 §9 的恢复协议如实记录进度、续跑。
- **边界诚实**：`final-report.md` 必须如实标注低置信度文件、任何被 `generated-excluded` 的目录、G6 三重分母、软收敛区及其追认状态、未实机验证面（如无 stub 模式时的运行时路径）；"已审计"的范围定义 = 台账状态，不夸大。**本审计保证过程完备（每个文件被处置、每个声称可对账），不保证本体完备（存在的每个缺陷都被发现）**——这是同模型静态审计的原理边界，G7 人类裁决因此不可绕过。

---

*本 prompt（v3）与设计 spec `docs/superpowers/specs/2026-08-13-full-project-audit-prompt-design.md` 及其 §0（v2 修订）/§0.1（v3 修订）一一对应；执行时如发现本 prompt 内部矛盾或缺失机制，停止并报人类裁决，禁止自行改写规则。*
