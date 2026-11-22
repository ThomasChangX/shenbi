<!-- sdd-core:start v8.1 -->
# Single-Model SDD Workflow Prompt v8.1（自治版 · 价值门 + 解法门 + 回归 skill 机制）



---

## Variables

| 变量 | 值 |
|------|----|
| `$SPEC_PATH` | `<填入 spec 绝对路径>`（必填） |

> 无 `$QUEUE` 变量（v6.2 删）：批处理 = 用户重复执行 `/sdd-next`，见文末「批处理」节。

## 使用方式与交付物

- **单 spec 模式**：填 `$SPEC_PATH`，从阶段 0 执行到终止条件（GO 路线跑到阶段 12；REJECT/OPS 终止并出 docs PR；DEFER 只记 progress.md 不改 git；REWRITE 修订出 docs PR 后重跑阶段 1）。
- **批处理**：重复执行 `/sdd-next`——每份一个新会话：freshness 天然基于最新 main、上下文零污染、每份之间留人工检查点（见文末「批处理」节）。
- **交付物**：GO → 合并的 PR + 归档记录；REJECT → 驳斥证据 + 注册表更新（docs PR）；DEFER → 裁决报告（progress.md，不改 git）；OPS → 执行证据 + 注册表更新（docs PR）；REWRITE → 修订后的 spec（docs PR）+ 重跑。**一份失效 spec 被裁决 REJECT，与一份 spec 被修复合并，是同等合格的交付。**

---

## 核心原则（v6 强化）

1. **证据先于断言（Iron Law · 每条消息级，非阶段级）**：**任何**含「通过/完成/就绪/绿/done/已修」字样的消息，该断言的具体验证命令**必须在同一条消息内运行过并粘贴输出**。上一轮跑过 ≠ 本轮成立。
2. **审查不可绕过（机制化）**：所有审查（阶段 3/5/6/8）走 `superpowers:requesting-code-review` skill 调度 + **`docs/superpowers/review-rubric.md` 单源路径注入**（回执协议见该节，v6.3）。每个 task commit 后**必须**产出 `<workspace>/audit-T<N>.md`（fresh-context 子 agent 首审 findings 表）。阶段 7 核验 `audit-T*.md` 数量 == task 数，缺失即 BLOCKED。**progress.md 与 audit-T<N>.md 分工**：progress.md（首行为 skill ledger 身份，兼具 SDD 裁决/门禁记录）是权威进度追踪——compaction 恢复与 skill 的 resume 检查读**同一文件**，答"task 完成了吗"；audit-T<N>.md 是审查产物（本项目特有，阶段 7 计数核验用，答"task 审过了吗"）。两者并存不冲突。
3. **基础设施代码由协调者亲自实现**：子 agent 只做叶子任务。
4. **偏差实时记录**：每个 task commit 当轮即更新 `spec-deviations.md` 的 `### T<N>` 段。
5. **每轮修复必被重审（scoped）**：任一 C/I 修复后必须跑 scoped re-review（只验 ADDRESSED/NOT_ADDRESSED + fix diff 内新破坏，不漫游全量）——不存在未经重审的修复。全量重审保留在两处：task 首审、阶段 8 终审。修复轮 5 轮封顶，封顶后熔断裁决（见 audit_loop）。
6. **价值先于投入**：阶段 1 裁决 GO 之前零实施动作（不建代码分支、不写测试、不改 spec 以外的文件）。REJECT/DEFER/OPS 是合法且期望的产出——硬修一份已失效 spec、或为纯运维工作硬走 12 阶段，都是浪费整轮 SDD。
7. **单 spec 原子性**：一次只执行一份 spec（其 §2 簇策略内的联动项除外，以 spec 文本声明为准）。执行中发现应合并/应拆分/前提失效 → 停下回阶段 1 重裁，不就地膨胀 scope。
8. **域约束纪律**：本仓 §Profile·域约束 声明的红线（如付费/写状态操作禁为验证目的触发、fixture 真实性、生成物禁手改）全程有效——SDD 任何阶段不得为"验证"目的触犯。

---

## 项目补充 rubric（单源注入 · v6.3）

`requesting-code-review` skill 自带通用 rubric（plan alignment / code quality / architecture / testing / production readiness + Critical/Important/Minor 三级）。**本项目的补充维度单源在 `docs/superpowers/review-rubric.md`**（设计级维度表 1-8＋文件级检查表＋设计审查 SHA 约定——I/L 教训编号已改写为 fresh-context 子 agent 可见的自包含描述）。

**注入方式（v6.3，废除本文件内嵌副本）**：`audit_loop` 的 rubric 参数 = skill 通用 rubric + `review-rubric.md` **路径注入**（＋plan 的 Global Constraints 逐字块）。派子 agent 时 prompt 附「先 Read `docs/superpowers/review-rubric.md`，报告开头回执其节标题清单」——**无回执 = 未注入，该轮审查无效**。禁止手工复制 rubric 文本进 prompt（派发副本不可审计：rubric 改版后副本与单源漂移无察）。编辑审查维度只改 `review-rubric.md`。

> 设计审查（阶段 3 spec / 阶段 5 plan）无代码 diff：BASE_SHA 取空树或 spec/plan 首次 commit、HEAD_SHA 取 spec/plan 文件当前 SHA，scope 由文件清单定义（非 diff）。子 agent 读 spec/plan/AGENTS.md 全文 + `review-rubric.md`。


### 审查循环 `audit_loop(scope, rubric, sha_range)` ← 可复用 pattern，阶段 3/5/6/8 显式调用（v6.2 对齐 skill 6.2.0 协议）

```
入参：
  scope      = 本次审查的文件清单（非 diff，list of paths）
  rubric     = skill 通用 rubric + `docs/superpowers/review-rubric.md` 路径注入（先读＋报告开头
               回执节标题——无回执=未注入，该轮无效）+ plan 的 Global Constraints 逐字块（注意力透镜）
  sha_range  = (BASE_SHA, HEAD_SHA)，design review 用 (空树, 文件SHA)；code review 用 (上 task commit, 本commit) 或 (merge-base main, HEAD)

首审（每 scope 一次，全量）：
  1. 有 commit 范围 → 生成 diff 包：skill 的 `scripts/review-package PLAN_FILE BASE HEAD`
     （diff 走文件，不过协调者上下文；**无 diff 文件禁止派审查者**）；design review（阶段 3/5）
     无 commit 范围 → scope 文件直读，跳过 diff 包
  2. 派 fresh-context 子 agent（不继承上轮），声明 "This is a FULL audit of ALL files in scope."
  3. 子 agent prompt 含：scope 文件清单 + diff 包路径（如有）+ 读 spec/plan/AGENTS.md + rubric + grep 调用方
  4. 子 agent 报告所有 🔴C / 🟡I / 🟢M（附文件:行号）+ ⚠️"Cannot verify from diff"项
     + **末尾覆盖清单**——读过的文件、执行过的 grep/命令、rubric 逐维度一行结论（✅/发现编号）
  5. 协调者逐条 VERIFY（打开真实文件核对，不轻信子 agent）+ 对覆盖清单抽查 ≥1 项复跑核验
     ——**无覆盖清单的空报告 = 无效轮，重派**（覆盖清单义务只约束全量轮：首审/终审）；
     ⚠️ 项由协调者亲自消解（持有跨 task 上下文）——确认属实按 spec ❌ 进修复轮

修复轮（每轮 = 一次修复 + 一次 scoped re-review；5 轮封顶）：
  - 修复：leaf task R1-3 复用原 implementer（上下文在，知道自己的代码）、R4-5 换新 implementer
    并升模型档（三轮复用仍不收敛 = 看不见自己的问题）；infra task 协调者亲自修
    （本协议唯一例外：修复者=协调者，重审照走）
  - 重审：scoped re-review（skill re-review-prompt 模板）——只验各 finding ADDRESSED/NOT_ADDRESSED
    + fix diff 内新破坏；**未触碰代码的新发现 → ledger 暂存，不入循环**（防漫游）
  - Minor：本轮顺手修；不修则记 `Task <N>: minor (deferred): <一句话>` → 阶段 8 终审统一 triage
  - 修复者每轮必须：改 → 跑覆盖测试 → 报告附命令与输出 → 才派重审
  - 每轮 ledger 追加：`Task <N>: fix round <R>/5 (<X> addressed, <Y> open; commits <a>..<b>)`

熔断（两个独立出口，触发者必须写进裁决）：
  - **打摆熔断（v6.3）**：连续 3 个 fix round 每轮都出新 C/I 且分布跨模块 → 停止修复循环记
    BLOCKING 报备——设计/架构问题不是审查问题，继续修只会互相打出新 finding
  - **5 轮封顶**（第 5 轮仍有 open finding）：
  - 逐条裁决：审查者错/可争议 → park（`Task <N>: parked — <finding> — ruling: <为何代码成立>`）；
    真实但无下游依赖 → park 并注明 deferred；真实且 load-bearing（后续 task 建于其上 / plan 缺陷）
    → STOP 报备用户（带着 finding、冲突的 plan 原文、修复史）
  - 裁决只能发生在封顶后；每条裁决必入 ledger——静默丢弃禁止

终止：scoped re-review 全 ADDRESSED 且 fix diff 无新 C/I → complete；或封顶后全部 park/STOP。
单 pass 冒充全量 = 假审（C-3）；但 scoped re-review 明示只验增量，不是冒充。
```

---

## 执行流程

**全局规则**：所有阶段「引擎」字段列的 skill **必须实际调用**（Skill tool），**禁止内联等价替代** —— 不允许自己读 spec 替代 `requesting-code-review`、自己跑 ruff 替代 `verification-before-completion`、自己写 plan 替代 `writing-plans`。列了引擎 = 必须用，不是参考。Iron Law 适用：调用 skill 后必须粘贴 skill 的实际输出/返回，"我应该调"≠"调了"。

**全局规则 2（commit pathspec 保护）**：worktree 常有用户未提交的 docs/配置修改——**所有 commit 显式列文件路径，禁 `git add -A` / `git add .`**；用户 unstaged 改动全程原样保留（代码 commit 与归档/裁决的 docs PR 一律适用）。

---

### 阶段 0 · 准备（只读，不建分支）

- 读 spec 全文 + `AGENTS.md` + **spec 引用的证据文件**（证据指针、头部 `Depends on` 字段——全部打开读。spec 是结论压缩，证据文件是全貌）
- **证据源路由**：证据按来源定核验方式——版本库内文件 → git/磁盘直开；gitignored 运行工件（§Profile·证据源路由细节）→ 磁盘三层核验（存在性/内容形态/时间）；报告/裁决书类 → 打开对应文档。三类之外（仅存会话记忆）= 不可核验——**核心主张证据不可核验 → 判 DEFER**（证据落盘后重进价值门）；次要主张不可核验 → 记 deviation
- **缺位主张登记**：spec 含「零存在/无检查/未消费/未接线」类否定主张时先列清单——它们没有 file:行号 锚，阶段 1 步骤 4 须主动造锚（穷尽 grep 反查）；阶段 0 不登记 = 步骤 4 大概率静默跳过
- 建工作态目录：**plan 文件名基名 = spec 基名**（确定性映射），用 skill 的 `scripts/sdd-workspace <PLAN_PATH>` 产出/确保 `.superpowers/sdd/<plan-basename>/`（gitignored，是工作态不是交付物；plan 阶段 4 才写，目录与 ledger 阶段 0 即按此规则建）。`progress.md` 首行**必须是** `# SDD ledger — plan: <PLAN_PATH>`——这是 subagent-driven-development resume 检查的身份契约；缺了这行，技能会把你的 ledger 当 stray 另起炉灶 → 已完成 task 被整段重派（skill 标注的"最昂贵失败"）。SDD 各节跟在首行之后（模板见附录 A）
- **不建代码分支**：分支在阶段 1 裁决 GO 之后建——REJECT/DEFER 不产生代码分支

### 阶段 1 · 价值门（这份 spec 值得做吗）

- **引擎**：协调者机械核查 + 价值两问（步骤 1-3）+ 1 个 fresh-context 驳斥子 agent（步骤 4）
- **步骤 1 · Freshness 分级**（机械）：
  - spec 带 §0 → 原样执行该命令；不带（手写 spec）→ `git log --oneline --since="$(git log --follow -1 --format=%cI -- <SPEC_PATH>)" -- <spec 点名的文件集>`——**锚点=spec 最后修订落地时刻（%cI 全时刻，v6.3：日粒度锚会把同日 commit 留在窗外）**
  - **GREEN**：无输出（涉及文件未动）· **YELLOW**：有 commit 但核心符号仍在（grep spec 点名的函数/列名/文件:行 上下文确认）· **RED**：核心文件已删 / 函数重写 / 符号消失
  - **Scope 落点核对**（v6.1 防假阴性 GREEN）：§0 命令之外，另跑 `git log --oneline --since="<spec 日期>" -- <Scope 行全部文件>`——Scope 文件有 commit 而 §0 文件无 → 按 YELLOW 处理并记"方案落点漂移"。证据未过期 ≠ 方案落点未漂移（实例：#229 §0 未列 `run.py`，#228 恰好改了它 55 行）
  - **GREEN-via-invisibility 禁令**（v6.3）：§0/Scope 引用集含 git 不可见路径（gitignored 如 `data/reports/`、`logs/`）→ 该文件**禁判 GREEN**——git 无输出只证明 git 看不见，不证明未动。降 YELLOW 改磁盘核验：① 文件仍存在？② 内容与 spec 引用形态一致？③ mtime 是否晚于 spec 修订日？——①②任一不过 → RED；②过而③晚 → 维持 YELLOW 记 deviation（mtime 对活跃写入面是噪声，语义交步骤 4 复核）；**不得单凭 mtime 判 RED**
- **步骤 2 · 注册表核对**（机械，对照 `specs/INDEX.md`）：
  - **重复**：同文件/同症状是否已有活跃 spec（含簇 sibling）；解析 §2 簇策略交叉引用（如 #30 声明"#28簇策略"→ 查 #28 状态，避免重复修复）
  - **依赖**：头部 `Depends on` 指向的 spec 是否已完成/归档；指向已 **REJECT** 的 spec = 前提失效，进 REWRITE/REJECT 评估，而非仅 DEFER
  - **优先级**：本 spec 是否队头；非队头需豁免理由（用户点名 / 依赖链倒排），记入裁决
  - **资源冲突**（v6.1）：§Profile·资源槽 所列共享槽（迁移版本号/契约常量/枚举/新增 config key）被 ≥2 活跃 spec 同时声明，或 Scope 同文件重叠 → 记冲突入裁决，后执行者 plan 期改号/换槽
  - **任务级交叉引用对账**（v6.3）：`grep -nE '#[0-9]+ T[0-9]+' <SPEC_PATH>` 提取正文引用的它 spec 任务号（正则未触发的"描述隔开续写"读行上下文人工归属），协调者逐条裁定：承载**依赖语义**（验收引用其产出/执行前提/顺序受制）→ 必须在 `Depends on` 声明，缺失=REWRITE 触发点；**纯提及**（口径引用/解耦声明/先例）→ progress.md 记裁定备查。逐条记录，不得整类豁免
  - **GATED 呈报**（v6.1）：命中 `Status: Proposed (Gated)` 或 DEFER 理由为"待用户裁决"、且门控条件当前已可裁决 → 向用户呈决策简报（选项+事实+推荐），**不静默跳过**。单 spec 模式：停下等裁决；队列模式：呈报后按 DEFER（待用户）跳过取下一份——普通 DEFER 跳过条款不免除呈报义务
- **步骤 3 · 价值两问**（v6.1，协调者作答并写入 progress.md，各 ≤2 句、须引证据；**先于驳斥**——双空可省一次子 agent 派发）：
  - **Q1 do-nothing**：若 90 天不做，具体什么坏、多坏、多大概率？——答不出具体损害 = 价值存疑
  - **Q2 consumer**：产出的下游消费者是谁、改变哪个决策/流程？——🔴 豁免条件：损害属"资产损失/数据错误"级；🔵/🎨/优化类答不出具体消费者 → 视同低收益
  - **早退**：Q1/Q2 双空（无具体损害且无具体消费者）→ 可直接 DEFER；**REJECT 不得以两问替代驳斥**——仍须步骤 4 证据
  - 目的：把"值得做"与"问题存在"（步骤 4）分开——SDD 一轮本身是成本支出
- **步骤 4 · 核心主张复核（v6.3 三问→五问）**（fresh-context 子 agent，审计 P7.5 驳斥方法——**既驳问题主张，也驳解法主张**）：
  - 子 agent prompt 含：spec §1 全文（或手写 spec 的问题陈述段）+ 证据文件路径 + 指令"在当前 main HEAD **试图驳斥**核心主张——先独立枚举 main HEAD 上所有可能已缓解该症状的机制（含 spec 未预期的路径），再核对 spec 证据，不得把 spec 的根因分析当搜索起点（去锚定）"。五问：
    - **① 证据仍在且语义未变？**（逐条打开 file:行号；gitignored 引用按步骤 1 磁盘核验）
    - **② 修复是否已在 main 落地？**（git log 该文件 + grep 修复后代码形态——**自己 vs 他人 PR 的归因分界见步骤 5 ARCHIVE-AS-DONE**）
    - **③ 验收条件仍可达成？**（bug spec → 仍复现？优化 spec → 低效仍在？设计 spec → 症状仍在？）
    - **④ 解法对抗回放**：假设 spec 修法已全部实施，沿 spec 自诊断的根因路径反向推演博弈路径（配置开关关闭/降级路径绕过/新旧行并存/只修症状不修根因等）能否让根因复发？任一路径仍通 → 判"改道"。**无论结论为何必须列出测试过的博弈路径清单**——只写"闭环"两字 = 无效复核
    - **⑤ 替代路径（buy-before-build）**：对 spec 每个新建机制 grep 同域既有实现（同义词/中英/相近职责），覆盖 ≥60% 职责 → 主张"升格既有"而非新建。**必须列出候选机制枚举清单**＋各自覆盖估计——无清单 = 无效复核；spec 自称"升格既有"的修法必须过 ④ 证明改写 ≠ 重建
    - **测量语义五问（v8.1 触及面启用）**：spec §1 或任务触及**指标／阈值／门／评分／统计量**（新建或依赖既有）时，上列五问之外逐问加答：
      - **L1 构念与口径**：数的是什么、在哪个单位上数——在 A 层级测的量被拿去在 B 层级做决策（如整体分数选局部材料）=层级错位（生态谬误）；分位≠绝对水平（趋势序列上的分位下限只是跟踪趋势自身）；「单源」须覆盖**谓词与输入**，不只常量；作为真值的量自身有无独立核验
      - **L2 闭环与污染**：选材信号=评价信号吗（打分→高分选材→生成→同一打分者闭环）；参照标准是否被流水线自己制造；top-k 选择的赢家诅咒；修订稿与原件同表=标签泄漏
      - **L3 活性与负荷去路**：真实分布上会点火吗（阈值与中位/众数的距离；clamp/cap 终局——触顶后永久熄火路径）；点火后的负载落到哪个预算、余量多少
      - **L4 可判别性**：判据分支互斥且穷尽吗；给定 n 每档可达吗（最小可测效应的算术，非直觉）；证据规则区分证伪与确认吗
      - **L5 时点保真**：离线验收回放的信息集=在线决策时刻的信息集吗（walk-forward——无未来行、无前瞻窗口）
      - 分工边界（防与既有问重复计分）：③只管「规则→主张」推导，分布上行为归 L3；博弈回路归 ④，L2 只管测量回路。产出义务同 ④⑤：触及面命中任一问 → 复核产出附 L1-L5 逐问一行结论（未触及的问标「未触及」），无逐问回执=无效复核
  - **缺位主张穷尽反查**：否定主张（"零存在/无检查/未消费"）无锚可开——子 agent 必须穷尽 grep（中文标签/英文标识/同义机制）并**粘贴命令与输出**；找不到反证时输出反查命令清单供协调者复验
  - 纪律：只读——读文件 + DB 仅 SELECT；禁写端点 / 触发扫描/回测/训练 / LLM 真调用；大 DB 禁整体加载进内存；密钥不入任何产物
  - 产出：存活 / 驳斥 / 降级 / 升级 / **改道** + 文件:行号证据 + ④⑤清单。协调者**逐条 VERIFY**（打开文件核对；DB 数字用独立 SELECT 复查关键值——审计 EP-1 教训：并发测量曾把稳态误判为慢；缺位主张反查命令至少抽查一条复跑）
- **步骤 5 · 裁决**（写入 progress.md `## 价值裁决`，六选一）：

| 裁决 | 触发条件 | 出口 |
|------|---------|------|
| **GO** | freshness GREEN/YELLOW + 主张存活 + 无重复 + 依赖就绪 | 建分支（命名见 §Profile·分支命名；🔴/🟡→fix，🔵/🎨→feat/refactor）→ 阶段 2 |
| **REJECT** | 主张被驳斥 / main 已含等效修复（**他人或不可追溯**——本 spec 自己的已合 PR 走 ARCHIVE-AS-DONE）/ 与活跃 spec 重复 | spec 头 `Status:` 改 `Rejected (<日期> · <一句话理由>)` → **归档动作按 §Profile·归档策略**（驳斥证据由 docs PR 描述 + commit 承载）→ INDEX 删行 + 计数/最后更新行 → docs PR `docs(sdd): reject spec #N — <理由>` → merge → **终止，裁决报告即交付物** |
| **ARCHIVE-AS-DONE**（v6.3） | 步骤 4 ② 命中"修复已在 main 落地"**且**可追溯为**本 spec 自己的已合 PR**（`git log --oneline origin/main \| grep -E "s<N>([^0-9]\|$\)\|spec ?#?<N>"` 主题匹配）——spec 已被自己的批次完成、仅收尾遗留 | spec 头 `Status:` 定稿 `Done (PR #M)` → **归档动作按 §Profile·归档策略** → INDEX 删行 + 计数/最后更新行 → docs PR `docs(archive): <N> done (PR #M)` → merge → **终止，清偿即交付，不再走阶段 12**。与 REJECT 分界 = 归因：REJECT=失败（驳斥），本裁决=成功欠收尾。无法确认主题匹配 → 不适用，回 REJECT 常规判断 |
| **DEFER** | 依赖未就绪 / 优先级让位且无豁免理由 | spec 保持 `Proposed` 原状（"未执行"即其状态，不改 git）→ 裁决理由记 progress.md → 终止（队列模式取下一份） |
| **REWRITE** | freshness RED / 主张需修正但问题真实 / 任务级交叉引用失声明 / ④⑤ 判改道 | 修订 spec（§0/§1 证据同步更新，`Status:` 加 `Revised <日期>`，`Depends on` 补失声明项）→ docs PR → merge → **重跑本阶段** |
| **OPS（出队直办）** | 步骤 1-4 全过，但剩余工作为纯运维动作（无代码/测试面，如"运行既有脚本+写文档"）。此类主张常可由协调者以单命令直接验证（`ls`/`grep` 级）替代步骤 4 子 agent——证据粘贴进 progress.md | 直办并贴执行证据（命令+输出）→ docs PR（删 INDEX 行+spec 文件，**PR 描述贴执行证据——此 PR 即归档，不再走阶段 12**）→ merge → 终止。直办中发现仍需代码（>10 行）→ 回本阶段改判 GO（实例：#232——脚本/保留策略/配置/测试自 #189 齐备，剩余=跑一次+一行文档） |

- 成本收益提醒：高风险**形状** = schema 迁移 / 核心路径行为变更 / 历史回放或回填 / 日期-时区语义（L6·B5 事故类）/ touch `migrations.py`·`enums.py`·`llm/client.py` / 3+ 调用方。低收益（Q2 无具体消费者）× 任一高风险形状 → 倾向 DEFER，理由写明
- 多 task spec 逐 task 问"砍掉损失多少"——低价值 task 在裁决中记 **DEFER-scope**，实施前以 docs PR 修订 spec（保持单 spec 原子性；实例：#230-T2 历史补期限深）
- RED freshness 且主张存活 → 强制 REWRITE（不带着过期证据进设计审查）
- **REWRITE 循环熔断**（v6.3）：同一份 spec 连续 2 次 REWRITE → 停止，报备用户裁决——证据长期漂移或 spec 结构性问题，第三轮重写大概率仍是 REWRITE

### 阶段 2 · 事实核实（机械）

- **引擎**：fresh-context 子 agent
- **审什么**：spec 里**对代码库的引用**（路径/签名/行号±3 硬容差/import——±5 实证放行过恰好 5 行的偏移）—— 查"对不对"。freshness YELLOW → 受影响引用加倍核对
- **动作**：机械漂移（行号偏移/路径错）→ 修 spec；歧义漂移（签名不符）→ 记入 spec-deviations `### 阶段2` 段（此时 plan/task 尚不存在，不标 task 号），作为阶段 4 plan 的约束传入——受影响 task 在 plan 中标 BLOCKED，plan 期仍无法消解 → 回阶段 1 重裁；**证据失效（核心引用已不存在）→ 回阶段 1 改判**

### 阶段 3 · Spec 设计审查

- **引擎**：`requesting-code-review`
- **审什么**：spec 的**设计本身**（架构/完整性/YAGNI/合规）—— 查"好不好"
- **动作**：`audit_loop(scope=[spec, AGENTS.md]（内容型 spec 的证据文件追加进 scope，gitignored 工件磁盘直读）, rubric=review-rubric.md 单源注入, sha_range=(空树, spec文件SHA))`
- **退出**：收敛后写 `progress.md ## Spec 审查摘要`

### 阶段 4 · Plan

- **引擎**：`superpowers:writing-plans`
- **输入**：阶段 1 价值裁决 GO + 阶段 2 机械核查过 + 阶段 3 设计审查过的 spec（基于已验证 spec 写 plan，避免 spec 缺陷导致 plan 白写）
- **plan 文件名**：`docs/superpowers/plans/<spec 基名>.md`（= spec 文件名——workspace 派生与 ledger 身份都依赖此映射，禁自起别名）
- **plan 必填**（skill 契约 + 项目加项）：
  - 头部：REQUIRED SUB-SKILL 行 + Goal/Architecture/Tech Stack + **Global Constraints 段**（spec 的项目级约束**逐字复制**——它是 task reviewer 的注意力透镜，注入阶段 6/8 每次审查派发）
  - 每 task：Files（精确路径:行）+ **Interfaces Consumes/Produces**（真实签名，从源码复制非伪代码——I1；跨 task 签名漂移的防线）+ **bite-sized 步骤**（checkbox；代码步骤含真实代码；测试步骤含命令与**期望输出**，如 `Expected: FAIL with "NameError"`——红绿烧进 plan）
  - `复杂度: leaf|infra` · `test_kind: tdd_red_green | characterization | regression_guard` · AC 覆盖表（每 AC → task → test）
  - No placeholders："TBD / 类似 Task N / 适当的错误处理 / 写测试覆盖上述（无测试代码）" = plan 失败
  - §Profile·plan 加项 声明的额外必填字段（测试层级/fixture 真实性/独立评分/离线可复验改写等）

### 阶段 5 · Plan 审查

- **引擎**：`requesting-code-review`（**独立子 agent，与阶段 3 分离**）
- **动作**：`audit_loop(scope=[plan, spec], rubric=review-rubric.md 单源注入 + Plan 专属补充 rubric, sha_range=(空树, plan文件SHA))`
- **Plan 专属补充 rubric**（注入时追加到 rubric 参数）：
  - AC 覆盖完整性（每 spec AC 有 task + test）
  - 每个签名的 grep 验证记录
  - test_kind 合理性（新逻辑=tdd_red_green；行为保持重构=characterization/regression_guard）
  - task 分解正确性（无跨 task 隐式依赖）
  - leaf/infra 分类准确性
- **退出**：收敛后写 `progress.md ## Plan 审查摘要`

### 阶段 6 · 执行

- **引擎**：`subagent-driven-development`（plan 路径：阶段 4 产出的 plan 文件）
- **项目补充**（skill 不知的本项目特有规则）：
  - **leaf/infra 分流**：见下方 —— skill 假设 task 独立可分派，但本项目 infra 类 task（涉及 §Profile·infra 模块 清单）必须协调者亲自实现，不分派
  - **上下文卫生（用 skill 机器，勿手搓）**：task 文本走 `scripts/task-brief PLAN_FILE N`（implementer 只读 brief 文件，禁读整个 plan；精确值只存在于 brief）；diff 走 `scripts/review-package PLAN_FILE BASE HEAD`（BASE = 派发前记录的 `git rev-parse HEAD`，**禁 `HEAD~1`**——多 commit task 会被截断）；implementer 报告落 `<workspace>/task-N-report.md`，返回只带状态契约四值之一：**DONE / DONE_WITH_CONCERNS**（先读 concerns 再进审查）**/ NEEDS_CONTEXT**（补上下文重派同 agent）**/ BLOCKED**（按 skill 四分支处置，禁无视或原样重试）
  - **每 task commit 后首审**：`audit_loop(scope=该 task 改动文件, rubric=review-rubric.md 单源注入 + Global Constraints 逐字块, sha_range=(BASE, 本 task commit))`，findings 写入 `<workspace>/audit-T<N>.md`；修复轮按 audit_loop 协议（scoped re-review + 5 轮熔断）。**无 audit-T<N>.md 不得开始 T<N+1>**（阶段 7 计数核验）
  - **模型分档**：按 §Profile·模型分档 执行（ON：派发显式指定档位＋R4-5 升档＋终审最强档；OFF：单血统全同档——经用户裁定的仓库）
  - **infra 路径 TDD**：infra task 的 `test_kind: tdd_red_green` → 协调者实现时**必须调用** `superpowers:test-driven-development`（红→绿→重构；禁先写实现后补测试）
  - **验收可执行化**：spec 每条 AC 在对应 task 完成时**实际运行**其验证命令（测试/只读 CLI/脚本），命令+输出粘贴 progress.md `## 验收证据`——AC"写了但没跑" = task 未完成
  - **UI spec 附加验收**（§Profile·验收形态 为 UI 的仓库）：spec 涉及 UI 行为/视觉 → 用当前环境可用的浏览器技能（如 `browser-use:web-gui-tester` / chrome-devtools 截图）做改动前后截图对比，存 `<workspace>/ui/`，progress.md 引用——UI 回归肉眼可察但断言难写，截图是最低成本证据。**不绑定具体 skill 名**（环境技能集会变；v6.1 修正失效引用 `webapp-testing`）
  - **前提失效中止**：实施中发现 spec 前提不成立（修复方案套不上 / 代码已根本变化）→ 停当前 task → 回阶段 1 重裁。禁止硬修、禁止绕过

#### leaf/infra 分流（subagent-driven-development 的自定义路由）

- **leaf**：单文件、无跨模块、无并发/序列化、无 DB schema、不涉及 infra 模块
  - skill 分派 implementer 子 agent + task-reviewer（两 verdict + 项目补充 rubric）
  - 逐 task 串行
- **infra**：多文件 / ProcessPool / threading / DB migration / 枚举/契约变更 / 跨 task；或涉及 §Profile·infra 清单模块；或被 3+ 消费方 import
  - **协调者亲自实现**（不分派）→ TDD → 审查子 agent（审查铁律）
- 分类错误时立即升级（leaf 误判 → 回收 → 协调者接手）

**单模型现实**：协调者即唯一执行模型，infra 必亲自实现；leaf 可分派 implementer 子 agent **或**亲自实现（按上下文长度裁决）。两种路径**都必须**走 task 后 fresh-context 重审（产出 audit-T<N>.md），无例外。

**Infra 强制审查项**：□ pickle 实测通过？□ migration 幂等+SCHEMA_VERSION？□ 枚举唯一定义+前端 regenerate？□ 跨 task 签名兼容？□ 全量回归绿？

**BLOCKED task**（阶段 2 歧义漂移在 plan/执行期未消解 / 阶段 10 CI 无法运行）→ 阶段 10 决议：skip（手动实施）或 abort（归档标注未完成）。

### 阶段 7 · 验证

- **引擎**：`verification-before-completion`（**每条声称的 gate，非阶段独占**）
- **门禁命令**（全部跑，完整输出粘贴到 progress.md；**命令以 AGENTS.md 为权威真理源，本 prompt 一律不重抄**——重抄必漂移，v6.1 审核已发现本节旧抄本与 AGENTS.md 实际命令不一致）：
  - **输出首行指纹（v6.3）**：每段门禁输出首行粘贴 `git rev-parse --short HEAD && date +%s` 的实际输出——事后对账可复推（同轮伪造引述可检出）
  - §Profile·门禁 声明的提交前全量命令（各仓权威源：AGENTS.md §验证 或 justfile check），原样执行
  - §Profile·门禁附加项 逐条原样执行（有输出须 `git log main..HEAD -- <file>` 证 pre-existing 非本分支）
- **额外核验**：`ls <workspace>/audit-T*.md | wc -l` == plan task 数（漏审=BLOCKED）；UI spec → `<workspace>/ui/` 前后截图齐全
- **回归红绿回撤验证**（test_kind=regression_guard 必做——L2"零交易回测"的机械解药）：写测试→过→**撤掉修复**→测试**必须红**→复原→过；四步输出全贴 progress.md。只红绿各跑一次 ≠ 回归测试有牙

### 阶段 8 · 最终审查

- **引擎**：`requesting-code-review`
- **动作**：`audit_loop(scope=全 branch 改动文件, rubric=review-rubric.md 单源注入 + Global Constraints 逐字块, sha_range=(merge-base main, HEAD))`，`scripts/review-package PLAN_FILE MERGE_BASE HEAD` 生成 diff 文件。**火力按 §Profile·模型分档**（ON 时最强档——skill 明文 final review "not the session default"）——合并前最后一道门；并指向 ledger 的 minor(deferred)/parked 行做 triage（哪些必须修后才可合并）
- **fix 循环（恰好一波）**：有 C/I → **单** fix 子 agent 携完整 findings（禁 per-finding 多 fixer——各自重建上下文的成本曾超过全部 task 之和）→ 一次 scoped re-review → 余项按熔断裁决（park-with-ruling / STOP 报备）。**没有第二波**——load-bearing 余项在阶段 9/10 呈报用户

### 阶段 9 · PR

- **引擎**：`finishing-a-development-branch`
- **main 漂移检查**：`git fetch origin && git log HEAD..origin/main --oneline` 非空 → rebase `origin/main` → **重跑阶段 7 全部门禁**（rebase 前本地绿 ≠ 合并前绿）→ 再出 PR
- **动作**：Option 2（push + create PR）——finishing 的三选项菜单在本项目**已常设裁决为 Option 2**，不现场问用户；PR 描述含：**价值裁决摘要**（freshness 分级 + 价值两问答案 + 驳斥结论 + GO 理由）+ spec-deviations 全文 + ledger 摘要

### 阶段 10 · CI+合并

- **引擎**：—（原生 `gh` / CI 操作；非 skill 驱动）
- **合并条件**：**CI 必须真实运行且全绿** + 零未解决线程；合并方式 `gh pr merge <PR号> --squash --delete-branch`（PR 号放最前、只写数字**不带 `#`**——`#123` 会被 shell 当注释吞掉参数；squash + 删远端分支一步到位；网页端合并则必须同步点 Delete branch）
- **CI 无法运行（计费/配额/infra）≠ 自治合并**——属 BLOCKING deviation，必须向用户报备请求裁决（即使本地 gate 全绿）
- **收到 PR 评论时**：先一次性收集全部评论与失败注解再动手（禁修一个推一次）；用 `receiving-code-review` skill 处理（push back / validate / 不表演同意）；线程级 reply+resolve 纪律按 §Profile·PR 协议（零未解决方可报告完成）
- plan-mandated finding 呈现 finding+plan 文本问哪个为准

### 阶段 11 · 清理

- **动作**：`git checkout main && git pull && git branch -D <branch> && git remote prune origin`；随后**远端删除兜底**：单独执行 `git push origin --delete <branch>`（不并入上方 `&&` 链），失败**不吞错**——用 `git ls-remote --heads origin <branch>` 核实：无输出 = 阶段 10 已删（正常收尾）；有输出 = 真失败（权限/分支保护/网络）→ WARN 报备人工处理（L3：静默吞错）
- `git remote prune origin` 只清本地跟踪引用，**不会删远端分支**——远端删除只发生在阶段 10 `--delete-branch` 或上面的兜底命令
- **post-merge verification**：在 main HEAD 重跑 ruff/mypy/pytest，输出粘贴进 progress.md，**方可声称「SDD 完成」**

### 阶段 12 · 归档

- **动作**：归档按 §Profile·归档策略 执行（删除式：删 spec+plan 文件；双库式：移 specs/archive/ 与 plans/archive/）；更新 INDEX（删行 + 计数 + 「最后更新」行，编号策略见 §Profile）；提交 `docs(archive): <N> done (PR #M)`
- **归档分支同规**：归档提交走 `docs/<slug>-archive` 分支出 PR，合并与清理同阶段 10/11（`--delete-branch` + 远端删除兜底）——归档分支不豁免
- **核验**：`git grep <spec-filename>` 应无输出（文件已删；历史查 `git log --oneline -- <spec-path>`）
- **workspace 保留**：`<workspace>/` 不在阶段 12 删除（偏离 skill 的即删语义，有意保留）——留待下一次 `/sdd-next` 开新份时移入 prior-runs，期间可做事后审计

---

## 阶段间状态与恢复（compaction 协议）

- `<workspace>/progress.md` 是唯一跨阶段状态源（首行 = skill ledger 身份，SDD 各节跟后——SDD compaction 协议与 skill resume 检查读**同一文件**，互认）。**每阶段完成当轮即追加**（裁决、门禁输出、commit SHA）——不落盘 = 没发生
- 会话被压缩/续接后：第一步读 `<workspace>/progress.md`（含 skill ledger 行）重建阶段指针，从断点继续。**活分支禁止从阶段 0 重启**（会重建 workspace、重跑价值门、产生第二套 audit-T 计数）。遇旧 flat 路径 `.superpowers/sdd/progress.md`（v6.1 遗留）= 历史工作态，按 prior-runs 处理，不覆盖不续跑
- 阶段 1 的价值裁决只在**执行开始时**有效；若中途 main 出现同域大改（阶段 9 漂移检查发现），重跑 freshness 分级确认证据仍成立
- **步骤指针（v6.3）**：阶段 0-5 无 skill ledger，各**步骤**完成当轮在 progress.md 落一行（如 `阶段1·步骤2 注册表核对 ✓`）——中断续跑时阶段内定位不靠猜（执行段粒度仍由 ledger＋audit-T 计数承担）
- **跨 session 残留对账**：progress.md 已终态（或已移 prior-runs）但仍存在未删分支 / 未合并 PR（含 `docs/*-archive` 归档 PR——`fix|feat/s<N>-*` glob 不覆盖它，须单查）→ 只收尾阶段 11/12，**不开新份**——INDEX 行在归档 PR 合并前仍在，开新份可能重取同一 spec

## 批处理

批处理 = **用户重复执行 `/sdd-next`**（v6.2 删 `$QUEUE` 单会话队列模式——它失去每份独立 freshness、烧上下文、且无人工检查点）：

- **串行由分支状态保证**：上一份 merge + 归档 PR 合并 + main 更新之后，`/sdd-next` 的断点/残留检测才会放行取下一份（见该命令）
- 每份独立跑完整阶段 0-12（独立会话/分支/PR/归档；REJECT/OPS 亦为一份完整交付）；单份内 DEFER/GATED/REJECT/OPS 终止语义见阶段 1 裁决表
- **连续 REJECT 刹车**（原队列停机条件的无状态化）：`/sdd-next` 启动时查 `git log --oneline --grep="docs(sdd): reject"`——最近两次 SDD 终态均为 REJECT → 先提示用户"注册表或 main 走向系统性漂移，建议人工抽查剩余队列"，确认后再继续

---

## Anti-Rationalization 守则

| 模型可能说 | 回应 |
|-----------|------|
| "Minor 可以静默丢弃" | 禁止。Minor 当轮顺手修，或记 `minor (deferred)` 入 ledger 由终审 triage——任何丢弃必须显式裁决入 ledger。 |
| "已审查 N 轮可终止" / "再修一轮就收敛" | 修复轮 5 轮封顶：到顶逐条裁决（park-with-ruling / STOP）——不无限循环，也不提前放弃。 |
| "终审再修一波" | 禁止。终审 fix 恰好一波 + 一次 scoped re-review，余项走裁决——第二波是上下文与回归的放大器。 |
| "测试应该通过" / "子 agent 报告成功" | 必须运行并粘贴输出，VCS diff + 测试独立验证。 |
| "上一轮跑过 ruff/pytest" | Iron Law：声称成立的当轮消息必须重跑。上一轮 ≠ 本轮。 |
| "偏差可末尾补" | 每个 task commit 当轮即更新 spec-deviations 的 `### T<N>` 段。 |
| "上轮查过 / diff 里没有" | 每轮全量重审，scope 由 task 定义不由 diff。 |
| "这是 leaf 可分派" | 涉及 infra 模块/并发/DB schema → 升级。 |
| "这两个 task 改不同文件，可并行分派" | 禁止。共享工作树 → git 冲突。逐 task 串行（skill Red Flag）。 |
| "doc-only 修改/gitignored 文件，不必重审" | 禁止。每轮修复必被 scoped re-review（核心原则 5）——doc-only 修复同样进重审。 |
| "本地 gate 全绿，CI 跑不了可直接合并" | 禁止。CI 无法运行 = BLOCKING deviation，必须报备用户。 |
| "task 已完成可直接进下一个" | 禁止。无 `<workspace>/audit-T<N>.md` 不得开始 T<N+1>。 |
| "CI 失败我修" | 区分：代码失败→修；infra（计费/配额）→ BLOCKING 报备，不自治修。 |
| "我自己造个状态机表追踪进度" | 禁止。用 skill 的 ledger 格式（`Task N: complete (commits ...)`），不另造。 |
| "我自己读 spec/跑 ruff/写 plan 就行，不必调 skill" | 禁止。引擎字段列了 skill = 必须调（执行流程全局规则）。内联等价 = v3 失败模式。 |
| "spec 事实正确 = 必须执行" | 禁止。GO 需 freshness + 驳斥 + 注册表三查全过；硬修一份已失效 spec = 浪费整轮 SDD。 |
| "问题真实 = 值得做" | 禁止。价值两问（do-nothing/consumer）不过的 spec，问题再真也 DEFER/OPS 出队——SDD 一轮本身是成本支出。 |
| "价值门上次跑过 / INDEX 已排过序" | 每次执行前现查。main 和注册表都在动，昨天的 GO 今天不作数。 |
| "REJECT 显得没产出" | REJECT 附驳斥证据 = 省下一整轮 SDD 的合格交付（核心原则 6）。 |
| "REJECT/OPS 收尾直接改 INDEX，不出 docs PR" | 禁止。INDEX 是 git 文件，任何裁决的注册表变更都走 docs PR（禁直推 main）；OPS 的执行证据就贴在该 PR 描述。 |
| "DEFER 的依赖 spec 顺手一起做了" | 禁止。单 spec 原子性（核心原则 7）；依赖 spec 自己走完整流程。 |
| "main 动了但本地门禁绿，直接合并" | 禁止。rebase + 阶段 7 门禁重跑后才可 PR（阶段 9 漂移检查）。 |
| "会话续接了，从阶段 0 重跑一遍保险" | 禁止。读 progress.md + ledger 从断点续；重启 = 双份 audit-T + 脏计数（compaction 协议）。 |

---

## 附录 A · `progress.md` 模板

```markdown
# SDD ledger — plan: docs/superpowers/plans/<spec 基名>.md
# SDD #<N> <slug>（<SPEC_PATH>）· workspace = .superpowers/sdd/<spec 基名>/

## 价值裁决（阶段 1）
- freshness: GREEN|YELLOW|RED（命令 + 输出摘要 + Scope 落点核对结果）
- do-nothing: <90 天不做的具体损害 + 概率>
- consumer: <下游消费者 + 改变的决策>
- 注册表: 重复=无|#M · 依赖=就绪|#M 未完成|前提失效 · 优先级=队头|豁免理由 · 资源冲突=无|<冲突项与改号方> · 任务级交叉引用=对账一致|失声明清单
- 驳斥复核: ①②③=存活|驳斥|降级|升级 · ④对抗回放=闭环（附博弈路径清单）|仍通路径清单 · ⑤=候选机制枚举清单（子 agent 结论 + 协调者 VERIFY 记录；缺位主张附反查命令清单）
- **裁决: GO|REJECT|DEFER|REWRITE|OPS|ARCHIVE-AS-DONE** — 理由

## Spec 审查摘要（阶段 3）
## Plan 审查摘要（阶段 5）

## 执行 ledger（阶段 6）
Task N: complete (commits <base7>..<head7>, review clean | <K> parked) · audit-T<N>.md ✓
Task N: fix round R/5 (<X> addressed, <Y> open; commits ...)（有修复轮时）
Task N: minor (deferred): <一句话>（有暂存时）

## 门禁输出（阶段 7 / 阶段 11 post-merge）
<命令 + 完整输出>

## spec-deviations 摘要（全文在 spec-deviations.md，格式 `### T<N>`）

## UI 证据（仅 UI spec）
前/后截图路径 + 差异说明

## 审查成本（v6.3）
各阶段 audit_loop 轮数 / audit-T 计数 / 子 agent 会话数 / 熔断与裁决触发计数（门禁命中率观察窗数据源）

## 最终状态
merged PR #N | REJECTED | DEFERRED | OPS（直办，docs PR #M）| ARCHIVE-AS-DONE (PR #M) — <日期>
```

---

<!-- sdd-core:end -->

## Profile（本仓差异 · 标记区之外，跨仓不同步）

- **门禁**：权威源 `just check`（契约 lints + repo 一致性 + ruff + mypy + basedpyright + sync 幂等 diff + 两段 pytest）；**附加项**：`uv lock --check`（本分支改过 pyproject/uv.lock 时）；全部走 `just`/`uv run` 与 CI `uv run --frozen` 同构——系统 python 的验证不算证据
- **infra 模块**：`src/shenbi/pipeline/`（dispatch_helper · chapter_loop · parallel_dispatch · 状态机）· `gates/g4/` · `contracts/` · `cost/` · `audit/` · `orchestration/` · `trace/`，及 `phase_runner.py` · `scoring.py` · `sync_contracts.py` · `safe_write.py` · `recovery.py`
- **模型分档**：**OFF——2026-11-15 用户裁定单血统定案**（协调、infra 实现、四裁决、逐条 VERIFY 同源；异血统多样性归立项/元审会话层，先例 #115-#117，不入 SDD 执行环路）
- **归档策略**：**双库分置**——spec → `docs/superpowers/specs/archive/`，plan → `docs/superpowers/plans/archive/`；`specs/INDEX.md` 删行（**编号 append-only 不重排不复用**——系列/依赖按编号交叉引用）+ `plans/INDEX.md` 同步
- **分支命名**：`fix|feat|chore/spec-<N>-<slug>`（🟥🟠 findings 修复→fix，架构/批量清理→chore，新能力→feat；**不用 worktree**——个人单仓库分支隔离已足够）
- **验收形态**：无前端——验收一律可执行化（fixtures 驱动测试 / 只读 gate CLI），无截图类证据
- **plan 加项**：测试层级声明（T1|T2|T3 归属）+ `tests/fixtures/` 真实产物引用（G0.9：scenario 输入只能引用真实产物，禁手写 fixture）；涉及评分场景声明 G3.4 独立评分子 agent 调度方式（dispatcher 自评无效；阈值 ≥94 晋级 / ≥90 单项通过）；**F947**：验收若依赖真实 LLM dispatch 或手写 mock，plan 期必须改写为可离线复验形式（fixtures 回放/结构断言）——不改写即该 task BLOCKED
- **域约束**：真实 LLM dispatch（`shenbi-dispatch` / `pipeline init|resume|review`）**付费且写状态**（truth/staging/progress 落盘）——SDD 全流程禁为「验证」目的触发（`shenbi-validate G0` 允许：无副作用）；deps.json 等生成物禁手改（改契约源头 + `just generate`，幂等 diff 会打回）
- **资源槽**：Literal 单源 `src/shenbi/contracts/enums.py`；契约常量；新增 config key（无迁移版本槽——schema 走契约同步）
- **PR 协议**：`AGENTS.md §PR Review Protocol`——一次性收集全部评论与失败注解再动手；每线程单独 reply（`gh api .../comments/{id}/replies`）；GraphQL resolve（REST 无此端点）；零未解决方可报告完成
- **证据源路由细节**：F 编号 → `docs/superpowers/audit-runs/2026-08-14/findings-ledger.md` 对应条目；运行项目工件（`novel-*/` 等 gitignored，`.gitignore` 的 `/novel-*/` 规则）→ 磁盘直核（存在性/内容/行号三层）；盲审/复盘报告/G3.4 裁决书 → 打开对应文档

---

## 变更史（执行者不读历史）

> **v8.1 变更**（2026-11-22 · 测量语义五问）：阶段 1 步骤 4 五问之外新增**触及面条件加问 L1-L5**（构念与口径／闭环与污染／活性与负荷去路／可判别性／时点保真）——spec 触及指标、阈值、门、评分、统计量时逐问必答，产出附逐问回执（同 ④⑤ 清单义务）。同批：`review-rubric.md` 设计级维度表增**维度 9 测量语义**（同一五问，阶段 3/5 子 agent 注入面）；元审层第三方席位协议另立 `docs/superpowers/meta-review-protocol.md`（不入执行环路，2026-11-15 裁定⑥维持）。**动机底账**：2026-11-22 四臂盲测（GLM×五问基线／GLM×五问+lens／DS-flash×lens／MiniMax×lens，四段脱敏材料）——基线五问强（历史缺陷类 6 中 5）但漏三类：**上限触顶后永久熄火**、**层级错位（A 级度量用于 B 级决策）**、**判据可达性算术**（n=12 下 0.3-0.5 档 CI 必跨 0=与撤回档重叠、0.575-0.695 无档可落；基线臂用不可行反例撑对结论=该弱点的活标本）；修订五问经 DS-flash/MiniMax 独立读数＋同日另两个独立会话三轮收敛定型。

> **v8.0 变更**（2026-11-17 · 双仓统一核心）：通用流程与 a-stock 收敛为**字节级同源核心区**（`<!-- sdd-core:start v8.0 -->` … `<!-- sdd-core:end -->`，a-stock 侧 CI 抓取本仓 raw 比对执法）。本仓随核心获得：价值两问（步骤 3）· Scope 落点核对 · GATED 呈报 · OPS 第六裁决（纯运维出队直办）· **B1 落地：per-plan workspace**（`scripts/sdd-workspace` → `.superpowers/sdd/<plan-basename>/`，progress.md 首行 = skill ledger 身份——替代 flat 多批次账本与末块提取；旧 flat 文件按 prior-runs 归置）· plan 基名=spec 基名映射 · 终审单波修复已在 v7.2。项目差异全部在 §Profile（单血统裁定/双库归档/append-only 编号/F947/G0.9/核心域约束等保留不动）。门禁指纹与 overnight 五重终态校验的衔接：外部 overnight 脚本若重启，须按 per-plan 路径适配后再启用。


> **v7.1 变更**（2026-11-15 · /sdd-next 多专家深审 14 findings 全修，启动面变更见 `docs/superpowers/sdd-next.md` 头部）：①新裁决 **ARCHIVE-AS-DONE**——步骤 3 ②命中「修复已落地」且可追溯为本 spec 自己的已合 PR 时走清偿归档（Done 归因），杜绝把成功 spec 错标 Rejected（实证：#97 完结后归档欠账半月、靠 PR #349 人工清偿）；②**audit_loop 空报告覆盖清单义务＋协调者覆盖抽查**——0 C/I 终止须附完整覆盖清单（读过的文件／跑过的命令／逐维度结论），无清单=无效轮（封「报少即收敛」博弈面，对齐 #116「能失败≠会失败」教训）；③审查轮预算警告线（单 task/阶段累计 >4 轮记 warning）；④**rubric 单源抽离**至 `docs/superpowers/review-rubric.md`——废除三源复制义务，子 agent 路径注入＋节标题回执；⑤门禁输出首行指纹（`git rev-parse --short HEAD`＋`date +%s`，供 overnight 五重终态校验机器复推）；⑥**单模型架构升格为用户裁定定案**——异血统多样性归立项／元审会话层（#115-#117 先例），不入 SDD 执行环路；⑦progress.md 模板增审查成本行；⑧阶段 0-5 步骤指针义务（无 ledger 阶段的 compaction 粒度）；⑨外部内容定界前导（规则在 `review-rubric.md` 头部）。补记：v7 后未升版补丁一笔——2026-11-10 `3b60895f`（阶段 10/11 分支删除硬化），现并入本版基线。

> **v7 变更**（2026-10-30）：新增**解法门**——阶段 1 步骤 3 驳斥三问扩**五问**（④解法主张对抗回放 ⑤替代路径 buy-before-build）＋**缺位主张穷尽反查义务**＋证据源路由（findings-ledger 之外：运行项目工件/盲审报告）；freshness 修两缺陷（锚点改 spec 最后修订日（%cI 全时刻）；**GREEN-via-invisibility 禁令**——gitignored 路径 git 无输出 ≠ 未动，降级磁盘核验）；步骤 2 加正文 `#<N> T<N>` **任务级交叉引用对账**（机械提取＋语义裁定，失声明=REWRITE 触发）；阶段 2 范围扩运行项目工件＋行号容差 ±5→±3；rubric 升级（维度 2 **双向 dead-wire**／维度 5 新 FAIL 门**误报成本** shadow 纪律／新维度 8 **解法最小性**）；audit_loop 加**打摆熔断**（连续 3 轮新 C/I 跨模块→BLOCKING 报备）；REWRITE 连续 2 次停机；Plan rubric 加跨 spec 联动项归属检查；`$QUEUE` 标注遗留模式（现行无人值守批处理=外部 overnight 脚本）；Anti-Rationalization 增 6 行；progress.md 模板同步。**动机**：spec #82-#84 r1 外部审核 backtest——8 项缺陷（同域重复建设/门读可变数据源/gitignored 证据死胎/任务级依赖失声明等）中旧管线机制必拦 0 项；根因=价值门为 findings 型 repo 内 spec 设计，#72 起出现运行项目内容 spec 新属种＋「解法最优性」维度在全部阶段整体缺位（本仓历史 REJECT 全为失效型，无一为解法质量型）。

> **v6 变更**（2026-08-15）：新增阶段 1 价值门（freshness / 注册表 / 驳斥三查 + GO·REJECT·DEFER·REWRITE 四裁决）；阶段重编号 0-12（无外部文档引用旧编号，无需同步）；新增队列模式、compaction 恢复协议、main 漂移 rebase 协议、验收可执行化（本项目无前端，以可执行验收替代截图类证据）、PR 线程 reply+resolve 协议（接入 AGENTS.md §PR Review Protocol）。**修正 v5 三处缺陷**：① 归档路径 `docs/superpowers/archive/` 不存在 → 实际为 `specs/archive/` + `plans/archive/` 双库；② rubric 引用的 I1/L1-L4/C-3 教训编号在本仓库无定义（fresh-context 子 agent 不可见）→ 全部改写为自包含检查描述；③ 补入本仓高频失败模式（dead-wire、契约三源同步、状态字面量单一信源、成本与状态纪律、环境同构）；④ INDEX 改为**仅追踪活跃 spec**（不维护归档计数），编号 append-only 不重编号（对齐 INDEX 登记与编号约定）。
