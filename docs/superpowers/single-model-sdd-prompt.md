# Single-Model SDD Workflow Prompt v6（自治版 · 价值门 + 回归 skill 机制）

> **v6 变更**（2026-08-15）：新增阶段 1 价值门（freshness / 注册表 / 驳斥三查 + GO·REJECT·DEFER·REWRITE 四裁决）；阶段重编号 0-12（无外部文档引用旧编号，无需同步）；新增队列模式、compaction 恢复协议、main 漂移 rebase 协议、验收可执行化（本项目无前端，以可执行验收替代截图类证据）、PR 线程 reply+resolve 协议（接入 AGENTS.md §PR Review Protocol）。**修正 v5 三处缺陷**：① 归档路径 `docs/superpowers/archive/` 不存在 → 实际为 `specs/archive/` + `plans/archive/` 双库；② rubric 引用的 I1/L1-L4/C-3 教训编号在本仓库无定义（fresh-context 子 agent 不可见）→ 全部改写为自包含检查描述；③ 补入本仓高频失败模式（dead-wire、契约三源同步、状态字面量单一信源、成本与状态纪律、环境同构）；④ INDEX 改为**仅追踪活跃 spec**（不维护归档计数），编号 append-only 不重编号（对齐 INDEX 登记与编号约定）。

---

## Variables

| 变量 | 值 |
|------|----|
| `$SPEC_PATH` | `<填入 spec 绝对路径>`（单 spec 模式必填） |
| `$QUEUE` | `<可选：P0 \| P1 \| P2 \| ALL>`——批处理模式。填了则忽略 `$SPEC_PATH`，按 `docs/superpowers/specs/INDEX.md` 优先级逐份执行（见「批处理模式」节） |

## 使用方式与交付物

- **单 spec 模式**：填 `$SPEC_PATH`，从阶段 0 执行到终止条件（GO 路线跑到阶段 12；REJECT/DEFER 在阶段 1 终止）。
- **队列模式**：填 `$QUEUE`，按 `specs/INDEX.md` 的推荐执行顺序逐份跑完整流程，每份独立分支/PR/合并。
- **交付物**：GO → 合并的 PR + 归档记录；REJECT → 驳斥证据 + 注册表更新；DEFER → 裁决报告。**一份失效 spec 被裁决 REJECT，与一份 spec 被修复合并，是同等合格的交付。**

---

## 核心原则（v6 强化）

1. **证据先于断言（Iron Law · 每条消息级，非阶段级）**：**任何**含「通过/完成/就绪/绿/done/已修」字样的消息，该断言的具体验证命令**必须在同一条消息内运行过并粘贴输出**。上一轮跑过 ≠ 本轮成立。
2. **审查不可绕过（机制化）**：所有审查（阶段 3/5/6/8）走 `superpowers:requesting-code-review` skill 调度 + 下方「项目补充 rubric」注入子 agent prompt。每个 task commit 后**必须**产出 `.superpowers/sdd/audit-T<N>.md`（fresh-context 子 agent 全量重审 findings 表）。阶段 7 核验 `audit-T*.md` 数量 == task 数，缺失即 BLOCKED。**audit-T<N>.md 与 skill ledger 分工**：ledger 是权威进度追踪（skill 原生，compaction 恢复用，答"task 完成了吗"）；audit-T<N>.md 是审查产物（本项目特有，阶段 7 计数核验用，答"task 审过了吗"）。两者并存不冲突。
3. **基础设施代码由协调者亲自实现**：子 agent 只做叶子任务。
4. **偏差实时记录**：每个 task commit 当轮即更新 `spec-deviations.md` 的 `### T<N>` 段。
5. **重审无条件**：审查发现任一新 C/I → 修复后必须重新 fresh-context 全量审查（例外清单见 Anti-Rationalization 表，目前为空）。
6. **价值先于投入**：阶段 1 裁决 GO 之前零实施动作（不建代码分支、不写测试、不改 spec 以外的文件）。REJECT/DEFER 是合法且期望的产出——硬修一份已失效 spec = 浪费整轮 SDD。本仓 spec 多为 findings 驱动（786 条 audit findings 的 spec 化），main 持续合并修复 → 失效风险常态存在。
7. **单 spec 原子性**：一次只执行一份 spec（其 `系列` 字段声明的簇分工联动项除外，以 spec 文本声明为准）。执行中发现应合并/应拆分/前提失效 → 停下回阶段 1 重裁，不就地膨胀 scope。
8. **成本与状态纪律**：真实 LLM dispatch（`shenbi-dispatch` / `pipeline init|resume|review`）是付费**且写状态**的操作（truth/staging/progress 落盘）。SDD 全流程禁为「验证」目的触发真实 dispatch；LLM 产物相关验收一律用 `tests/fixtures/` 真实产物驱动的测试表达。

---

## 项目补充 rubric（注入 requesting-code-review 子 agent · 贯穿阶段 3/5/6/8）

`requesting-code-review` skill 自带通用 rubric（plan alignment / code quality / architecture / testing / production readiness + Critical/Important/Minor 三级）。**本节是项目特有的补充维度**，协调者派子 agent 时**追加注入**子 agent prompt（非替代 skill rubric）。

> 设计审查（阶段 3 spec / 阶段 5 plan）无代码 diff：BASE_SHA 取空树或 spec/plan 首次 commit、HEAD_SHA 取 spec/plan 文件当前 SHA，scope 由文件清单定义（非 diff）。子 agent 读 spec/plan/AGENTS.md 全文 + 下方补充维度。
>
> 本节所有检查**自包含**：不引用任何外部编号的教训清单（子 agent 是 fresh-context，看不到本仓库其他文档；带编号的悬挂引用 = 无效 rubric）。

### 审查循环 `audit_loop(scope, rubric, sha_range)` ← 可复用 pattern，阶段 3/5/6/8 显式调用

```
入参：
  scope      = 本次审查的文件清单（非 diff，list of paths）
  rubric     = 注入子 agent 的审查维度（下方设计级维度表 + 文件级检查表 + skill 通用 rubric）
  sha_range  = (BASE_SHA, HEAD_SHA)，design review 用 (空树, 文件SHA)；code review 用 (上commit, 本commit) 或 (main, HEAD)

执行（每轮）：
  1. 派 fresh-context 子 agent（不继承上轮），声明 "This is a FULL re-audit of ALL files in scope."
  2. 子 agent prompt 含：scope 文件清单 + 读 spec/plan/AGENTS.md + rubric + grep 调用方
  3. 子 agent 报告所有 🔴C / 🟡I / 🟢M，附文件:行号
  4. 协调者逐条 VERIFY（打开真实文件核对，不轻信子 agent）→ 修复 → 每修一个 issue 单独跑相关测试 → C/I/M 全修

终止：本轮 0 新 C/I → 终止；本轮有新 C/I → 回到第 1 步（fresh-context 重新审）。
不设轮次上限，唯一终止条件是「本轮无新 C/I」。
单 pass review 当全量重审 = 假审。
```

### 设计级维度（每个 task 必查 · 补充 skill 的 architecture 维度）

| # | 维度 | 检查内容 |
|---|------|---------|
| 1 | 一致性+完整性 | spec↔plan↔INDEX 登记无矛盾，每条 finding/验收有对应 task |
| 2 | YAGNI + dead-wire | 无 God Object / 全局可变状态 / 循环依赖；**新增的每个函数/gate/桥必须有生产调用方**——本仓高频失败模式：安全网特性"看似实现"实际零接线静默失效 |
| 3 | 可测试性 | 关键逻辑独立可验证；测试层级（T1/T2/T3）定位明确；外部依赖经 fixtures 注入 |
| 4 | 向后兼容 | CLI 入口（shenbi-validate/score/dispatch/phase/sync-contracts、pipeline 子命令）不破调用方；契约 schema（reads/writes/decisions）变更有迁移路径；deps.json 登记闭包完整 |
| 5 | 成本 | 不新增不必要的 dispatch / 重复上下文注入 / 输出 token 放大（token 是本项目的核心成本维度，重试与冗余审计波是已知放大器） |
| 6 | 依赖图 | task 顺序与 import 依赖、契约依赖（A 写 B 读）一致 |
| 7 | 合规 | 不违反 AGENTS.md（structlog 非 print、pathlib、gate 检查器纯函数幂等、conventional commits、G0.9 fixture 真实性、G3.4 独立评分） |

### 文件级检查（每个 scope 文件必查 · 补充 skill 的 code quality 维度）

| 检查项 | 内容 |
|--------|------|
| 签名一致性 | plan 签名 vs 源码实际（参数名/类型/返回类型） |
| 状态字面量单一信源 | Literal/枚举唯一定义于 `src/shenbi/contracts/enums.py`；新增代码不得引入裸状态字符串（`tools/lint_status_strings.py` 红即 Critical） |
| dead-wire | grep 新增公共函数/gate/校验器的生产调用方 ≥1；"实现但零调用" = Important 起步 |
| 吞错 | 无裸 `except Exception` 吞错降级（本仓已知后果：declared=[] 假阳性 GATE_FAIL、审计静默失效） |
| 测试真实性 | 测试走真实代码路径非纯 mock；scenario 输入引用 `tests/fixtures/` 真实产物（G0.9 禁手写 fixture）；fixture 是源文件副本的须哈希一致（G0.11） |
| 调用方兼容 | grep 调用方，签名/契约变更不破坏已有调用 |
| 框架纯度 | `src/shenbi/` 无 `print()`（用 structlog）；gate 检查器无副作用、幂等 |
| 契约三源同步 | 改 SKILL.md 的 `reads`/`writes`/`writes/decisions` → `just lint-contracts` 绿 + `just generate` 生成物（deps.json/docs/skills）diff 为空；**禁止手改生成物** |
| 并发/序列化 | ThreadPool/ProcessPool/共享 truth 文件写路径须走既有串行化设施（write_safety/WRITE_SHARED 语义），无 lost-update |
| 环境同构 | 验证命令走 `just`/`uv run`（与 CI `uv run --frozen` 同构）；系统 python 跑出的结果不算证据 |

**注入方式**：`audit_loop` 的 `rubric` 参数 = skill 通用 rubric + 本节「设计级维度表 + 文件级检查表」。派子 agent 时将这三者**复制进子 agent prompt 的 rubric 段**（子 agent 是 fresh-context，看不到本文件，禁止只引用章节名）。

---

## 执行流程

**全局规则**：所有阶段「引擎」字段列的 skill **必须实际调用**（Skill tool），**禁止内联等价替代** —— 不允许自己读 spec 替代 `requesting-code-review`、自己跑 ruff 替代 `verification-before-completion`、自己写 plan 替代 `writing-plans`。列了引擎 = 必须用，不是参考。Iron Law 适用：调用 skill 后必须粘贴 skill 的实际输出/返回，"我应该调"≠"调了"。

---

### 阶段 0 · 准备（只读，不建分支）

- 读 spec 全文 + `AGENTS.md` + **spec 引用的证据**（`范围`/`依赖` 字段点名的源码文件、`内容` 里引用的 F 编号 → `docs/superpowers/audit-runs/2026-08-14/findings-ledger.md` 对应条目——全部打开读。spec 是结论压缩，findings-ledger 是全貌）
- 建 `.superpowers/sdd/{progress.md, spec-deviations.md}`（模板见附录 A；`.superpowers/` 已 gitignore，是工作态不是交付物）
- **不建代码分支**：分支在阶段 1 裁决 GO 之后建——REJECT/DEFER 不产生代码分支

### 阶段 1 · 价值门（这份 spec 值得做吗）

- **引擎**：协调者机械核查（步骤 1-2）+ 1 个 fresh-context 驳斥子 agent（步骤 3）
- **步骤 1 · Freshness 分级**（机械）：
  - `git log --oneline --since="$(git log --follow --format=%as -- <SPEC_PATH> | tail -1)" -- <spec 范围/依赖 字段点名的文件集>`
  - **GREEN**：无输出（涉及文件未动）· **YELLOW**：有 commit 但核心符号仍在（grep spec 点名的函数/路径/行号上下文确认）· **RED**：核心文件已删 / 函数重写 / finding 指控的代码形态已不存在（很可能已被其他 PR 修复）
- **步骤 2 · 注册表核对**（机械，对照 `docs/superpowers/specs/INDEX.md`）：
  - **重复**：同文件/同 F 编号族是否已有活跃 spec；解析 `系列` 字段的簇分工交叉引用（同系列子 spec 各管哪些 findings，避免重复修复；从属 finding 如 F312←F397 须归属唯一）
  - **依赖**：`依赖` 字段指向的 spec 是否已归档、指向的 PR 是否已合并（已归档/已合并 = 就绪）
  - **优先级**：本 spec 是否队头（🟥 P0 → 🟠 P1 → 🟡 P2/⚪ 批量）；非队头需豁免理由（用户点名 / 依赖链倒排），记入裁决
- **步骤 3 · 核心主张复核**（fresh-context 子 agent，驳斥方法）：
  - 子 agent prompt 含：spec 全文（至少 `内容` 段 + 各 finding 的证据/修复/验收）+ findings-ledger 对应条目路径 + 指令"在当前 main HEAD **试图驳斥**核心主张"——逐条打开 spec 引用的 file:行号，核对：证据仍存在且语义未变？修复是否已在 main 落地（git log 该文件 + grep 修复后代码形态）？验收条件是否仍可达成？
  - 纪律（核心原则 8）：只读——grep/read/git log；`shenbi-validate G0` 允许（环境自检无副作用）；**禁** `shenbi-dispatch` / `pipeline` 任何子命令（费 token + 写 truth/staging 状态）；禁改任何 tracked 文件；并发测量数字须复跑独立命令核对，不轻信单次读数
  - 产出：存活 / 驳斥 / 降级 / 升级 + 文件:行号证据。协调者**逐条 VERIFY**（打开文件核对）
- **步骤 4 · 裁决**（写入 progress.md `## 价值裁决`，四选一）：

| 裁决 | 触发条件 | 出口 |
|------|---------|------|
| **GO** | freshness GREEN/YELLOW + 主张存活 + 无重复 + 依赖就绪 | 建分支 `fix\|feat\|chore/spec-<N>-<slug>`（🟥🟠 findings 修复→fix，架构/批量清理→chore，新能力→feat；**不用 worktree**——个人单仓库分支隔离已足够）→ 阶段 2 |
| **REJECT** | 主张被驳斥 / main 已含等效修复 / 与活跃 spec 重复 | spec 头 `Status:` 改 `Rejected (<日期> · <一句话理由>)` → 移 `docs/superpowers/specs/archive/` → INDEX 删行（编号不重排）→ docs PR `docs(sdd): reject spec #N — <理由>` → merge → **终止，裁决报告即交付物** |
| **DEFER** | 依赖未就绪 / 优先级让位且无豁免理由 | spec 保持 `Design` 原状（"未执行"即其状态，不改 git）→ 裁决理由记 progress.md → 终止（队列模式取下一份） |
| **REWRITE** | freshness RED / 主张需修正但问题真实 | 修订 spec（证据、F 编号、验收同步更新，`Status:` 加 `Revised <日期>`）→ docs PR → merge → **重跑本阶段** |

- 成本收益提醒：⚪ M/批量清理类 spec × 触及核心 infra（`contracts/`、`gates/`、`pipeline/` 核心模块、3+ 调用方）→ 倾向 DEFER，理由写明
- RED freshness 且主张存活 → 强制 REWRITE（不带着过期证据进设计审查）

### 阶段 2 · 事实核实（机械）

- **引擎**：fresh-context 子 agent
- **审什么**：spec 里**对代码库的引用**（路径/签名/行号±5/import/F 编号 → findings-ledger 条目存在且状态仍为 specced/verified 而非已修）—— 查"对不对"。freshness YELLOW → 受影响引用加倍核对
- **动作**：机械漂移（行号偏移/路径错）→ 修 spec；歧义漂移（签名不符）→ 记 spec-deviations + task 标 BLOCKED；**证据失效（核心引用已不存在 / finding 已被修复）→ 回阶段 1 改判**

### 阶段 3 · Spec 设计审查

- **引擎**：`requesting-code-review`
- **审什么**：spec 的**设计本身**（架构/完整性/YAGNI/dead-wire/合规）—— 查"好不好"
- **动作**：`audit_loop(scope=[spec, AGENTS.md], rubric=项目补充 rubric, sha_range=(空树, spec文件SHA))`
- **退出**：收敛后写 `progress.md ## Spec 审查摘要`

### 阶段 4 · Plan

- **引擎**：`superpowers:writing-plans`
- **输入**：阶段 1 价值裁决 GO + 阶段 2 机械核查过 + 阶段 3 设计审查过的 spec（基于已验证 spec 写 plan，避免 spec 缺陷导致 plan 白写）
- **plan 必填字段**：
  - 实际签名（从源码复制，非伪代码）
  - `复杂度: leaf|infra`
  - `test_kind: tdd_red_green | characterization | regression_guard`
  - 测试层级与 fixture：每个测试声明 T1|T2|T3 归属 + `tests/fixtures/` 引用路径（G0.9：scenario 输入只能引用真实产物）
  - 验收覆盖表（spec 每条 `**验收：**` → task → 可执行验证命令）
  - 涉及评分的场景：声明 G3.4 独立评分子 agent 的调度方式（dispatcher 自评无效；阈值 ≥94 晋级 / ≥90 单项通过）

### 阶段 5 · Plan 审查

- **引擎**：`requesting-code-review`（**独立子 agent，与阶段 3 分离**）
- **动作**：`audit_loop(scope=[plan, spec], rubric=项目补充 rubric + Plan 专属补充 rubric, sha_range=(空树, plan文件SHA))`
- **Plan 专属补充 rubric**（注入时追加到 rubric 参数）：
  - 验收覆盖完整性（每条 spec 验收有 task + 可执行验证）
  - 每个签名的 grep 验证记录
  - test_kind 合理性（新逻辑=tdd_red_green；行为保持重构=characterization/regression_guard）
  - 测试层级与 fixture 真实性（T1/T2/T3 归属合理；fixture 路径真实存在且为真实产物）
  - task 分解正确性（无跨 task 隐式依赖）
  - leaf/infra 分类准确性
- **退出**：收敛后写 `progress.md ## Plan 审查摘要`；plan 登记进 `docs/superpowers/plans/INDEX.md`（`✅ ready`）

### 阶段 6 · 执行

- **引擎**：`subagent-driven-development`（plan 路径：阶段 4 产出的 plan 文件）
- **项目补充**（skill 不知的本项目特有规则）：
  - **leaf/infra 分流**：见下方 —— skill 假设 task 独立可分派，但本项目 infra 类 task（涉及 `src/shenbi/pipeline/` 派发与状态机、`src/shenbi/gates/g4/`、`src/shenbi/contracts/`、`src/shenbi/cost/`、`src/shenbi/audit/`、`src/shenbi/orchestration/` 等）必须协调者亲自实现，不分派
  - **每 task commit 后**：`audit_loop(scope=该 task 改动的文件, rubric=项目补充 rubric + skill task-reviewer 两 verdict, sha_range=(上 task commit, 本 task commit))`，findings 写入 `.superpowers/sdd/audit-T<N>.md`。**无 audit-T<N>.md 不得开始 T<N+1>**（阶段 7 计数核验）
  - **验收可执行化**：spec 每条 `**验收：**` 在对应 task 完成时实际运行其验证命令（pytest 场景 / `just gate` / `shenbi-validate` 等只读入口），命令+输出粘贴 progress.md `## 验收证据`——验收条目"写了但没跑" = task 未完成。LLM 产物验收用 fixtures 驱动测试表达，禁止现场 dispatch 取证（核心原则 8）
  - **前提失效中止**：实施中发现 spec 前提不成立（修复方案套不上 / 代码已根本变化）→ 停当前 task → 回阶段 1 重裁。禁止硬修、禁止绕过

#### leaf/infra 分流（subagent-driven-development 的自定义路由）

- **leaf**：单文件、无跨模块、无并发/序列化、无契约/G4 schema 变更、不涉及 infra 模块
  - skill 分派 implementer 子 agent + task-reviewer（两 verdict + 项目补充 rubric）
  - 逐 task 串行
- **infra**：多文件 / `ThreadPoolExecutor` / `ProcessPool` / 并行审计波 / 契约 `reads`/`writes` 或 G4 schema 变更 / 枚举变更 / 跨 task；或涉及 `src/shenbi/pipeline/`（dispatch_helper、chapter_loop、parallel_dispatch、状态机）、`src/shenbi/gates/g4/`、`src/shenbi/contracts/`、`src/shenbi/cost/`、`src/shenbi/audit/`、`src/shenbi/orchestration/`、`src/shenbi/trace/`，或 `phase_runner.py` / `scoring.py` / `sync_contracts.py` / `safe_write.py` / `recovery.py`；或被 3+ pipeline 模块 import
  - **协调者亲自实现**（不分派）→ TDD → 审查子 agent（审查铁律）
- 分类错误时立即升级（leaf 误判 → 回收 → 协调者接手）

**单模型现实**：协调者即唯一执行模型，infra 必亲自实现；leaf 可分派 implementer 子 agent **或**亲自实现（按上下文长度裁决）。两种路径**都必须**走 task 后 fresh-context 重审（产出 audit-T<N>.md），无例外。

**Infra 强制审查项**：□ 并发实测通过（`parallel_dispatch.py` / `chapter_loop.py` 并行审计波不串扰、无 lost-update）？□ 契约/G4 schema 变更幂等且 `just generate` 同步 `deps.json`/`docs/`/`skills/`（diff 为空）？□ Literal 唯一定义在 `src/shenbi/contracts/enums.py`？□ 跨 task 签名兼容？□ 全量回归绿？

**BLOCKED task**（阶段 2 歧义漂移 / 阶段 10 CI 无法运行）→ 阶段 10 决议：skip（手动实施）或 abort（归档标注未完成）。

### 阶段 7 · 验证

- **引擎**：`verification-before-completion`（**每条声称的 gate，非阶段独占**）
- **门禁命令**（全部跑，完整输出粘贴到 progress.md）：
  - **`justfile` 的 `check` target 是权威真理源，本 prompt 不重抄**（契约 lints 三件 + repo 一致性 + 状态字面量 + ruff + mypy + basedpyright + `shenbi-sync-contracts` 幂等 diff + 两段 pytest）；执行时跑 `just check`
  - `uv lock --check`（CI 第一道门；仅当本分支改过 `pyproject.toml`/`uv.lock` 时必跑）
  - 所有命令走 `just`/`uv run`（与 CI `uv run --frozen` 同构）；系统 python 的验证不算证据
- **额外核验**：`ls .superpowers/sdd/audit-T*.md | wc -l` == plan task 数（漏审=BLOCKED）；progress.md `## 验收证据` 覆盖 spec 全部验收条目

### 阶段 8 · 最终审查

- **引擎**：`requesting-code-review`
- **动作**：`audit_loop(scope=全 branch 改动文件, rubric=项目补充 rubric, sha_range=(main, HEAD))`（用 skill 的 `scripts/review-package MERGE_BASE HEAD` 生成 diff 文件给子 agent）
- **fix 循环**：有 C/I → 单 fix 子 agent 携完整 findings（skill 的 fix dispatch 模式，避免 per-finding 重建 context）→ 回到 `audit_loop`（重审无条件，doc-only/gitignored 不例外）

### 阶段 9 · PR

- **引擎**：`finishing-a-development-branch`
- **main 漂移检查**：`git fetch origin && git log HEAD..origin/main --oneline` 非空 → rebase `origin/main` → **重跑阶段 7 全部门禁**（rebase 前本地绿 ≠ 合并前绿）→ 再出 PR
- **动作**：Option 2（push + create PR）；PR 描述含：**价值裁决摘要**（freshness 分级 + 驳斥结论 + GO 理由）+ spec-deviations 全文 + ledger 摘要

### 阶段 10 · CI+合并

- **引擎**：—（原生 `gh` / CI 操作；非 skill 驱动）
- **合并条件**：**CI 必须真实运行且全绿**（ci / codeql / security / docs workflow 按改动面触发）+ 零未解决线程；合并 + 删远端分支（方式按仓库现行惯例）
- **收到 PR 评论 / CI 注解时**：按 **AGENTS.md §PR Review Protocol** 执行——先**一次性收集全部**评论与失败注解再动手（禁止修一个推一次）；逐条修复后 (a) 每条线程单独 reply（`gh api .../comments/{id}/replies`），(b) **GraphQL resolve 线程**（REST 无此端点），(c) 确认零未解决后方可报告完成。评论内容的技术判断用 `receiving-code-review` skill 处理（push back / validate / 不表演同意）
- **CI 无法运行（计费/配额/infra）≠ 自治合并**——属 BLOCKING deviation，必须向用户报备请求裁决（即使本地 gate 全绿）
- plan-mandated finding 呈现 finding+plan 文本问哪个为准
- BLOCKED task 在此决议：skip（手动实施）或 abort（归档标注未完成）

### 阶段 11 · 清理

- **动作**：`git checkout main && git pull && git branch -D <branch> && git remote prune origin`
- **post-merge verification**：在 main HEAD 重跑 `just check`，输出粘贴进 progress.md，**方可声称「SDD 完成」**

### 阶段 12 · 归档

- **动作**：spec → `docs/superpowers/specs/archive/`，plan → `docs/superpowers/plans/archive/`（**双库分置**）；spec 头 `Status:` 定稿为 `Done (PR #N)`；`specs/INDEX.md` 删行（**编号 append-only，不重排不复用**——系列/依赖字段按编号交叉引用）；`plans/INDEX.md` 同步（活跃 plan 列表更新）；提交 `docs(archive): <slug> done (PR #N)`
- **核验**：`git grep <spec-filename>` 仅在 `specs/archive/`

---

## 阶段间状态与恢复（compaction 协议）

- `progress.md` 是唯一跨阶段状态源。**每阶段完成当轮即追加**（裁决、门禁输出、commit SHA）——不落盘 = 没发生
- 会话被压缩/续接后：第一步读 `progress.md` + skill ledger 重建阶段指针，从断点继续。**活分支禁止从阶段 0 重启**（会重建 `.superpowers/`、重跑价值门、产生第二套 audit-T 计数）
- 阶段 1 的价值裁决只在**执行开始时**有效；若中途 main 出现同域大改（阶段 9 漂移检查发现），重跑 freshness 分级确认证据仍成立

## 批处理模式（`$QUEUE`）

- **串行**：上一份 merge + main 更新后才取下一份（每份的 freshness 天然基于最新 main，无需跨份缓存）
- 每份独立跑完整阶段 0-12（独立分支/PR/归档；REJECT 亦为一份完整交付）
- 队内 DEFER → 跳过取下一份；REJECT → 完成其 docs PR 后取下一份
- **停机报备**（不自治继续）：① BLOCKING deviation ② CI 无法运行 ③ 连续 2 份 REJECT（说明注册表或 main 走向系统性漂移——本仓 23 份活跃 spec 全部产自同一次 2026-08-14 audit，审查方法或覆盖若有系统性偏差会集中暴露，剩余队列裁决可信度存疑，需人工抽查后再放行）
- 跑完输出汇总：done（PR #）/ rejected（理由）/ deferred（依赖）三列清单

---

## Anti-Rationalization 守则

| 模型可能说 | 回应 |
|-----------|------|
| "Minor 可以延后" / "已审查 N 轮可终止" | 禁止。唯一终止条件「本轮无新 C/I」，C/I/M 全修。 |
| "测试应该通过" / "子 agent 报告成功" | 必须运行并粘贴输出，VCS diff + 测试独立验证。 |
| "上一轮跑过 just check" | Iron Law：声称成立的当轮消息必须重跑。上一轮 ≠ 本轮。 |
| "偏差可末尾补" | 每个 task commit 当轮即更新 spec-deviations 的 `### T<N>` 段。 |
| "上轮查过 / diff 里没有" | 每轮全量重审，scope 由 task 定义不由 diff。 |
| "这是 leaf 可分派" | 涉及 infra 模块/并发/契约 schema → 升级。 |
| "这两个 task 改不同文件，可并行分派" | 禁止。共享工作树 → git 冲突。逐 task 串行（skill Red Flag）。 |
| "doc-only 修改/gitignored 文件，不必重审" | 禁止。重审无条件（核心原则 5）。 |
| "本地 gate 全绿，CI 跑不了可直接合并" | 禁止。CI 无法运行 = BLOCKING deviation，必须报备用户。 |
| "task 已完成可直接进下一个" | 禁止。无 `.superpowers/sdd/audit-T<N>.md` 不得开始 T<N+1>。 |
| "CI 失败我修" | 区分：代码失败→修；infra（计费/配额）→ BLOCKING 报备，不自治修。 |
| "我自己造个状态机表追踪进度" | 禁止。用 skill 的 ledger 格式（`Task N: complete (commits ...)`），不另造。 |
| "我自己读 spec/跑 ruff/写 plan 就行，不必调 skill" | 禁止。引擎字段列了 skill = 必须调（执行流程全局规则）。内联等价 = v3 失败模式。 |
| "spec 事实正确 = 必须执行" | 禁止。GO 需 freshness + 驳斥 + 注册表三查全过；硬修一份已失效 spec = 浪费整轮 SDD。 |
| "价值门上次跑过 / INDEX 已排过序" | 每次执行前现查。main 和注册表都在动，昨天的 GO 今天不作数。 |
| "REJECT 显得没产出" | REJECT 附驳斥证据 = 省下一整轮 SDD 的合格交付（核心原则 6）。 |
| "DEFER 的依赖 spec 顺手一起做了" | 禁止。单 spec 原子性（核心原则 7）；依赖 spec 自己走完整流程。 |
| "main 动了但本地门禁绿，直接合并" | 禁止。rebase + 阶段 7 门禁重跑后才可 PR（阶段 9 漂移检查）。 |
| "会话续接了，从阶段 0 重跑一遍保险" | 禁止。读 progress.md + ledger 从断点续；重启 = 双份 audit-T + 脏计数（compaction 协议）。 |
| "fixture 手写一个更快" | 禁止（G0.9）。fixtures 只能是真实 skill 输出或源文件精确副本；造不出来 = 该验收改用 fixtures 驱动测试或回阶段 1 重裁。 |
| "跑一次真实 dispatch / pipeline 验证最真实" | 禁止（核心原则 8）。费 token + 写 truth/staging 状态；用 fixtures 驱动测试 + 静态证据。 |
| "评分我自己看输出估一下" | 禁止（G3.4）。评分必须独立子 agent；dispatcher 自评无效。 |
| "deps.json/生成物我手动补一下就行" | 禁止。改契约源头 + `just generate`；手改生成物会被幂等 diff 打回。 |
| "系统 python 跑得快，就用它验证" | 禁止。验证须 `just`/`uv run` 与 CI 同构；系统 python 的结果不算证据。 |
| "PR 评论回一句就行 / 修完自然算关闭" | 禁止。reply 每条 + GraphQL resolve + 确认零未解决（AGENTS.md §PR Review Protocol）；只回复不 resolve = PR 视觉上仍被阻塞。 |

---

## 附录 A · `progress.md` 模板

```markdown
# SDD #<N> <slug>（<SPEC_PATH>）

## 价值裁决（阶段 1）
- freshness: GREEN|YELLOW|RED（命令 + 输出摘要）
- 注册表: 重复=无|#M · 依赖=就绪|#M 未完成/PR#N 未合并 · 优先级=队头|豁免理由
- 驳斥复核: 存活|驳斥|降级|升级（子 agent 结论 + 协调者 VERIFY 记录）
- **裁决: GO|REJECT|DEFER|REWRITE** — 理由

## Spec 审查摘要（阶段 3）
## Plan 审查摘要（阶段 5）

## 执行 ledger（阶段 6）
Task N: complete (commits ...) · audit-T<N>.md ✓

## 验收证据（阶段 6 逐 task 累积）
spec 验收条目 → 验证命令 + 完整输出（fixtures 驱动测试 / 只读 gate CLI）

## 门禁输出（阶段 7 / 阶段 11 post-merge）
<just check（+ uv lock --check 如适用）完整输出>

## spec-deviations 摘要（全文在 spec-deviations.md，格式 `### T<N>`）

## 最终状态
merged PR #N | REJECTED | DEFERRED — <日期>
```
