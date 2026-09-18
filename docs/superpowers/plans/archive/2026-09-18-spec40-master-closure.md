# Spec #40 收官 pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 2026-08-15/08-14 两份 findings-ledger 的回写缺口（44 行编辑：08-15 侧 37 行 + 08-14 侧 7 行）、登记孤儿残留微修 spec #67、终稿归档审计修复总纲（spec #40）——37 簇修复计划的收官。

**Architecture:** 纯 docs 变更、单 PR（Task 0 登记 commit + 四个 task commit + PR 号定稿 commit）。T1/T2 用确定性 python 脚本改写 ledger 行（按行 ID 定位、状态单元格改写或追加 `→` 列，映射表钉死新注记全文）；T3 登记 #67（spec 文件 + INDEX 行）；T4 总纲终稿（§9 收官记录 + §7 归档前注 + 头部 sunset）+ 双库归档移动 + INDEX/plans-INDEX 终态。所有注记文案以归档簇 spec 的回写/出账/驳斥修订节为权威源逐字转录。

**Tech Stack:** bash + python3（stdlib only，与仓库工具同构）；验证走 `just`/`uv run`。

**复杂度:** 全 leaf（单文件 docs 编辑，无 src/ 改动，协调者亲做）· **test_kind:** regression_guard（钉死终态 grep 断言 + 既有 lint 工具回归，无新逻辑）· **测试层级:** N/A（docs-only；验收 = 可执行 grep/lint 命令）· **G3.4:** N/A（无评分场景）· **F947:** N/A（零 LLM dispatch）

## Global Constraints

- 注记追加列必须以 `→` 起始（`tools/lint_audit_run.py:93` row_columns 规则）；注记文本禁止裸 `|` 字符
- 08-14 ledger 属 frozen run（run 级 row_columns/pipe_escape 豁免）——lint 不覆盖本 pass 的 08-14 编辑，grep 判据承担验证负担
- ledger 只改状态列与追加注记列，**不改证据列/标题列/严重度列**（#42 出账协议「ledger 只改状态列与注记」）
- 编号 append-only：#67 = 现有最大号 66 + 1；INDEX 删 #40 行不重排
- 本 plan 文件与 #67 spec 正文引用总纲一律用「spec #40 总纲」措辞——除 Task 4 内部外**不得出现总纲裸文件名**（防额外引用 locus）
- 禁 `git add -A`/`git add .`；所有 commit 显式列文件路径；conventional commits 前缀 `docs:`
- 分支：`chore/spec40-master-closure`；全程零真实 dispatch

## 逐行注记映射表（权威表——T1/T2 脚本的字面源）

### 08-15 ledger（37 行编辑：34 关闭 + 3 改注；另 F401/F408 接受终态不编辑）

| ID | 现状尾（grep 亲验 2026-09-18） | 动作 | 新注记全文 |
|---|---|---|---|
| T1601 | `verified`（11 列裸） | 状态列改写 | `closed (C-28 spec #42, PR #153 · I/O 面吸收 T1614/F312；token 面 29% 冗余出账为产品决策非目标——产品裁决后另立 spec，记 spec #40 §8 deviation)` |
| T1603 | `open` 裸 | 改写 | `closed (C-28 spec #42, PR #153)` |
| T1604 | `open` 裸 | 改写 | `closed (C-28 spec #42, PR #153 · 吸收 F415-0814 行号锚点面)` |
| T1606 | `open` 裸 | 改写 | `closed (C-28 spec #42, PR #153)` |
| T1607 | `open` 裸 | 改写 | `closed (resolved-by-#26——差分快照随 spec #26 路径 3 整体移除（66e7f69d/PR #105），per C-28 spec #42 出账)` |
| T1608 | `open` 裸 | 改写 | `closed (transferred-to-#44 per C-28 spec #42 出账；spec #44 归档未提及 save_state 增量化——全量写为 #44 Done 终态，增量收益未裁决，记 spec #40 §8 deviation 可复活)` |
| T1609 | `open` 裸 | 改写 | `closed (C-28 spec #42, PR #153)` |
| T1610 | `open` 裸 | 改写 | `closed (C-28 spec #42, PR #153)` |
| T1613 | `open` 裸 | 改写 | `closed (C-28 spec #42, PR #153 · 吸收 F215)` |
| T1614 | `open` 裸 | 改写 | `closed (C-28 spec #42, PR #153)` |
| F215 | `open` 裸 | 改写 | `closed (C-28 spec #42, PR #153)` |
| F328 | `open` 裸 | 改写 | `closed (C-28 spec #42, PR #153)` |
| F415 | `open` 裸 | 改写 | `closed (C-28 spec #42, PR #153 · content_uniqueness 面（进程内范围注记）；g5.5 逐对重排面出账——随门禁进程内化才有意义，per #42 出账)` |
| F361 | `open` 裸（C29 代表） | 改写 | `closed (C-29 spec #43, PR #156)` |
| F235 | `open` 裸 | 改写 | `closed (C-29 spec #43, PR #156)` |
| F326 | `open` 裸 | 改写 | `closed (C-29 spec #43, PR #156)` |
| F330 | `open` 裸 | 改写 | `closed (C-29 spec #43, PR #156)` |
| F362 | `open` 裸 | 改写 | `closed (C-29 spec #43, PR #156)` |
| F459 | `open` 裸 | 改写 | `closed (C-29 spec #43, PR #156)` |
| F620 | `open` 裸 | 改写 | `closed (C-29 spec #43, PR #156)` |
| T1615 | `open` 裸 | 改写 | `closed (C-29 spec #43, PR #156 · 观测面已交付（R4）；量化消费方 C10/C28 未建——非缺陷，记 spec #40 §8)` |
| F764 | `open` 裸 | 改写 | `closed (C-24 spec #62 驳斥剔除——已被 PR #174/#132 系修复，per 2026-09-13 修订记录)` |
| F788 | `open` 裸 | 改写 | `closed (C-24 spec #62 驳斥剔除——已被 PR #174/#132 系修复，per 2026-09-13 修订记录)` |
| F937 | `open` 裸 | 改写 | `closed (C-24 spec #62 驳斥剔除——§2.9 已改，per 2026-09-13 修订记录)` |
| F940 | `open` 裸 | 改写 | `closed (C-24 spec #62 驳斥剔除——计数漂移已内联自洽披露，per 2026-09-13 修订记录)` |
| F944 | `open` 裸 | 改写 | `closed (C-24 spec #62 驳斥剔除——#3 已实际入 archive，标签不失实，per 2026-09-13 修订记录)` |
| F945 | `open` 裸 | 改写 | `closed (C-24 spec #62 驳斥剔除——矛盾文本已不存在，per 2026-09-13 修订记录)` |
| F954 | `open` 裸 | 改写 | `closed (C-24 spec #62 驳斥剔除——plans/INDEX 已刷新（PR #210/#211），per 2026-09-13 修订记录)` |
| F1025 | `open` 裸 | 改写 | `closed (C-24 spec #62 驳斥剔除——mutate-check 守卫已删除，对象消失，per 2026-09-13 修订记录)` |
| F1024 | `open` 裸 | 改写 | `closed (spec #66 PR #230 同体——Z10:275 所指 mypy python_version 3.12>3.11 已统一 3.11，numpy <2.5 封顶伴生；per C-24 spec #62 重归属 + #66 实施)` |
| F519 | `open` + 追加列 `→ out-of-cluster: fixed by prior PR (verified 2026-09-07, spec #48 value gate)` | **替换追加列** | `→ 纠偏（2026-09-18 · spec #40 收官 pass）：2026-09-07 out-of-cluster「fixed by prior PR」注记不实——仅生产面（dispatch_helper Tier B wrapper）修复；legacy CLI 路由残留（executor.py PROJECT_DIR=REPO_ROOT + test_executor_audit.py monkeypatch 掩蔽）→ re-homed spec #67（C32 边界注记 F513 同面）` |
| F311 | `open (P1 错位已修 PR #120 链；零消费面视 C37 R0 裁决)` | 状态列收窄 + 追加列 | 状态列 → `open (P1 错位已修 PR #120 链)`；追加列 → `→ curated 零消费者面 re-homed spec #67（wire-or-remove 裁决 · 2026-09-18 spec #40 收官 pass——C30↔C37 循环移交就此终结）` |
| T1108 | `open (移交：独立设计裁决，spec #44 尾注)` | 状态列收窄 + 追加列 | 状态列 → `open (移交：离线可执行模式设计裁决)`；追加列 → `→ 移交目标钉 spec #67（2026-09-18 spec #40 收官 pass——原 spec #44 尾注移交无目标，就此终结）` |
| G601 | `open` 裸 | 改写 | `closed (裁决落账 4 项本批已补落——g6-meta-audit.md G601（:217）；严重度列已回写 F201/F340/F601/F401)` |
| G602 | `open` 裸 | 改写 | `closed (勘误已录 g6-meta-audit.md 复核表（:91/:142）——字符数误标字节：F777 4503-4504 实为字符（字节 12825）、F778 2494 实为字符（字节 6980）)` |
| G603 | `open` 裸 | 改写 | `closed (勘误已录 g6-meta-audit.md 复核表（:111）——「must_fix 全部 no_valid_verdict」实测 30/35)` |
| G604 | `open` 裸 | 改写 | `closed (注记已录 g6-meta-audit.md §7.2 限制声明（:209）——route 分布子声称不可机械复现，核心面已精确复现)` |

（F401/F408 无动作——out-of-cluster 注记终态，§8 记录接受。）

### 08-14 ledger（7 行）

| ID | 现状尾 | 动作 | 新注记全文 |
|---|---|---|---|
| T12-01 | `verified` 裸 | 改写 | `closed (08-15 重立 T1206 双面闭合：属性注入面随 spec #22 R1 关闭（PR #91）、内容侧让渡 spec #45 R2 关闭（PR #161）——per #22 修订记录 + #45 归档承接注记)` |
| T12-02 | `verified` 裸 | 改写 | `closed (写审计接线面已由 C32 R3 修复（commit 26db756）；判定伪造/env/路径/symlink 面随 spec #45 R3/R4 关闭（PR #161）——per spec #22 修订记录让渡链)` |
| T12-03 | `verified` 裸 | 改写 | `closed (run_pipeline.sh 半面随 C26 spec #64 关闭（PR #220，F003/F1013/T1205 族）；round-exec.sh 半面随 spec #22 R2 关闭（PR #91）——per #22 修订记录让渡链)` |
| T12-04 | `verified` 裸 | 改写 | `closed (08-15 重立 T1207 随 C31 spec #45 R4 关闭，PR #161)` |
| T12-05 | `verified` 裸 | 改写 | `closed (08-15 重立 T1204 随 C31 spec #45 R3 关闭，PR #161；safe_write 零规范化边界注记同随 #45)` |
| T12-06 | `verified` 裸 | 改写 | `closed (随 spec #22 R3 词法防御关闭，PR #91——per #45 归档承接注记)` |
| F513 | `specced` 裸（11 列） | 状态列保持 + 追加列 | `→ re-homed spec #67（2026-09-18 · spec #40 收官 pass；残留面 = legacy CLI 路由快照根 PROJECT_DIR=REPO_ROOT（executor.py）+ 掩蔽测试——与 08-15 F519 同面，C32 边界注记原指向 spec #46 已 Rejected；状态 specced 至 #67 实施后关闭）` |

---

### Task 0: 计划登记（前置——否则 Task 4 的 `git mv` 对未跟踪文件报错）

- [x] **Step 1: Commit 本 plan + plans/INDEX.md 登记**（commit 21e7c9d1）

```bash
git add docs/superpowers/plans/2026-09-18-spec40-master-closure.md docs/superpowers/plans/INDEX.md
git commit -m "docs(plans): register spec #40 closure-pass plan (backfill + spec #67 + master archival)"
```

### Task 1: 08-15 ledger 回写补齐（34 关闭 = 30 簇行 + G×4；+ 3 改注）

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（37 行）

**Interfaces:** Consumes: 逐行注记映射表（08-15 节）。Produces: 终态 grep 基线（bare-open==0 / bare-verified==0 / `spec #67` 计数==3）。

- [x] **Step 1: 预检基线**

```bash
L15=docs/superpowers/audit-runs/2026-08-15/findings-ledger.md
grep -cE '\| open \| *$' $L15   # 期望 33（29 簇行 + G×4）
grep -cE '\| verified \| *$' $L15  # 期望 1（T1601）
grep -c 'spec #67' $L15         # 期望 0
grep -c 'closed (' $L15         # 期望 721
```

- [x] **Step 2: 执行改写脚本（heredoc，映射表字面源）**

python3 脚本逐行处理：按 `^\| <ID> ` 定位行；「改写」= 用映射表新注记替换状态单元格（保留行内其余列原样）；「替换追加列」= 将既有 `→ out-of-cluster…` 追加列文本整段替换为新文本；「状态列收窄 + 追加列」= 先替换状态单元格、再在行尾追加 ` | <新注记>`。脚本断言：每个目标 ID 恰好命中 1 行、改后行含新注记子串、列数变化按动作断言精确值：改写=0、追加列=+1、F519 替换=0（split('|') 长度差逐行校验）。37 个 ID 全部处理或 assert 失败。

- [x] **Step 3: 终态验证**

```bash
grep -cE '\| open \| *$' $L15    # 期望 0
grep -cE '\| verified \| *$' $L15 # 期望 0
grep -c 'spec #67' $L15          # 期望 3（F519/F311/T1108 各一）
grep -c 'closed (' $L15          # 期望较基线 +34（30 改写 + F311/T1108 保持 open 不计 + G×4 计入 → 30+4=34）
just audit-lint  # 期望绿（08-15 面在豁免清单内仍受 row_columns 规则约束）
```

- [x] **Step 4: Commit**

```bash
git add docs/superpowers/audit-runs/2026-08-15/findings-ledger.md
git commit -m "docs(ledger): backfill 08-15 closure notes — C28/C29/C24/G rows + F519 correction + F311/T1108 re-home (spec #40 closure pass)"
```

- [x] **Step 5: 产出 `.superpowers/sdd/audit-T1.md`**（fresh-context 重审，见执行协议）

### Task 2: 08-14 ledger 跨轮卫生（T12×6 镜像关闭 + F513 re-home）

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-14/findings-ledger.md`（7 行）

**Interfaces:** Consumes: 映射表 08-14 节。Produces: 08-14 T12-xx 零无注记基线。

- [x] **Step 1: 预检** `grep -cE '^\| T12-0[1-6] ' docs/superpowers/audit-runs/2026-08-14/findings-ledger.md` == 6，六行状态均裸 `verified`；F513 行 `specced` 裸。
- [x] **Step 2: 执行改写脚本**（同 T1 机制；T12 六行状态列改写、F513 状态保持 + 行尾追加 ` | → re-homed …`）
- [x] **Step 3: 终态验证**

```bash
L14=docs/superpowers/audit-runs/2026-08-14/findings-ledger.md
for id in T12-01 T12-02 T12-03 T12-04 T12-05 T12-06; do grep -E "^\| $id " $L14 | grep -c 'closed ('; done  # 每行期望 1
grep -E '^\| F513 ' $L14 | grep -c 'spec #67'  # 期望 1
```

- [x] **Step 4: Commit** `docs(ledger): mirror-close 08-14 T12-01~06 via #22/#45/#64 chains + re-home F513 to spec #67 (frozen-run hygiene, spec #40 closure pass)`（显式列文件）
- [x] **Step 5: 产出 audit-T2.md**

### Task 3: 登记 spec #67（孤儿残留收口）

**Files:**
- Create: `docs/superpowers/specs/2026-09-18-orphan-residuals-closure.md`
- Modify: `docs/superpowers/specs/INDEX.md`（#67 行 + 头部）

**Interfaces:** Produces: INDEX 活跃含 #67（与 #40 并存，活跃数暂 2——T4 删 #40 后回到 1）。

- [x] **Step 1: 写 #67 spec 文件**——头部（Date: 2026-09-18 | Status: Design | Severity: 🟠 P1（最高面 F513 P1）| 方法: 孤儿残留收口 | 系列: 2026-08-15 审计修复 · spec #40 收官 pass 登记 | 依赖: 无 | 范围: legacy CLI 写审计快照根、curated 层零消费者、离线可执行模式 | 核心洞察: 三个被已闭 spec 循环移交或被 Rejected spec 遗留的残留面）+ 三节内容（每节：finding 证据 file:line、修复方向、可执行验收）：
  - **F519/F513 legacy 路由快照根**：证据 `src/shenbi/dispatcher/executor.py:31-32`（`PROJECT_DIR = REPO_ROOT`）、`:309/:334`（`snapshot_tree(PROJECT_DIR, …)`）、`dispatcher/cli.py:11` legacy import、`tests/unit/dispatcher/test_executor_audit.py:18/:42` monkeypatch 掩蔽；方向 = 快照根对齐派发项目目录（生产面 dispatch_helper Tier B wrapper 已正确的语义）+ 揭掩蔽测试；验收 = `uv run pytest tests/unit/dispatcher/ -q` 绿 + 新断言不 monkeypatch PROJECT_DIR 也能定位项目根
  - **F311 curated 零消费者**：证据 `chapter_loop.py:1562`、`cli.py:1078-1080` 只写不读（grep 全仓零读方）；方向 = wire（context assembly 消费）或 remove（连写方一并清理）二选一裁决；验收 = 裁决落 spec 修订 + 对应接线/删除的回归测试
  - **T1108 离线可执行模式**：设计裁决项（internal 硬拒无 LLM、replay 非派发 stub）；方向 = 裁决做/不做/DEFER；验收 = 裁决记录 + 若做则离线 stub 的 T1 测试
  - 正文引用总纲一律「spec #40 收官 pass」措辞（无裸文件名）
- [x] **Step 2: INDEX 登记**——`### #67 · 孤儿残留收口（F519/F513 + F311 + T1108）` 节（文件/系列/状态 Design/优先级 🟠 P1/方法/依赖 无/内容 三行摘要）插入 #40 节之后；头部「活跃 spec 数」1→2、最后更新行追加登记注记
- [x] **Step 3: 验证** `uv run python tools/count_active_specs.py` 期望输出活跃 2 一致；`grep -c '2026-09-18-orphan-residuals-closure' docs/superpowers/specs/INDEX.md` == 1
- [x] **Step 4: Commit** `docs(specs): register spec #67 orphan-residuals closure (F519/F513 + F311 + T1108) — spec #40 closure pass registration)`（显式列两文件）
- [x] **Step 5: 产出 audit-T3.md**

### Task 4: 总纲终稿 + 双库归档 + INDEX 终态

**Files:**
- Modify: `docs/superpowers/specs/2026-08-16-audit-remediation-master.md`（头部 Status 定稿、§7 归档前注、§8→新增收官记录节）
- Move: 该文件 → `docs/superpowers/specs/archive/`；本 plan → `docs/superpowers/plans/archive/`
- Modify: `docs/superpowers/specs/INDEX.md`（#40 删行、头部终态）、`docs/superpowers/plans/INDEX.md`（归档计数 121→122、头部）

**Interfaces:** Consumes: T1-T3 终态。Produces: 活跃队列仅 #67；归档核验基线。

- [x] **Step 1: 总纲三处编辑**
  - 头部 Status 链尾追加：` · 收官 pass Done — 2026-09-18（37 簇全闭 + 回写补齐 44 行 + 孤儿裁决登记 #67；§5「直到全部簇关闭」保留条件到期，随本 PR 归档）`
  - §7 节首（`spec 文件名为 2026-08-16 落盘实名` 行前）插入：`> 归档注记（2026-09-18）：本文件自 specs/ 移入 specs/archive/；下文 archive/<name> 引用为作者时点相对路径，基名不变仍可检索。`
  - 文件末尾新增 `## 9. 收官记录（2026-09-18 · 收官 pass）`：回写补齐清单（08-15 侧 37 行处置：34 关闭（30 簇行 + G×4）+ 3 改注（F519 纠偏/F311/T1108 re-home）；F401/F408 接受 out-of-cluster 终态不编辑；08-14 侧 T12×6 镜像关闭 + F513 re-home + F1204/F1205 frozen-run 出界声明一句——合计 44 行编辑；08-14 F415 行号漂移面已由 #42 R4 吸收（08-15 F415 孪生已关），frozen-run 政策不出回写面）；孤儿清单映射（legacy 快照根→#67、curated 零消费者→#67、T1108→#67、T1608 增量化→deviation 可复活、C28 token 架构→deviation（产品裁决后另立 spec））；终态约定（08-15 非 closed 字样行 = 3 re-homed open + 17 C18 merged 记法 + 2 out-of-cluster 终态；零 bare verified）；#67 登记声明（仅登记不实施，先例 2026-09-11 登记 #66）；文件名引用处置（6 处 append-only 历史引用：4 归档 plan + final-report.md + 本 pass plan（随本 PR 归档），基名可寻不改写）
- [x] **Step 2: 归档移动**

```bash
git mv docs/superpowers/specs/2026-08-16-audit-remediation-master.md docs/superpowers/specs/archive/2026-08-16-audit-remediation-master.md
git mv docs/superpowers/plans/2026-09-18-spec40-master-closure.md docs/superpowers/plans/archive/2026-09-18-spec40-master-closure.md
```

- [x] **Step 3: INDEX 终态**——specs/INDEX.md：删 #40 整节；头部活跃 2→1、最后更新改写（收官注记 + 现序 #67）。plans/INDEX.md：头部活跃（此时无活跃 plan——本 plan 随 PR 归档）与已归档 121→122、最近归档项追加本 plan。
- [x] **Step 4: 全量验证（阶段 7 前置 + 验收覆盖）**

```bash
uv run python tools/count_active_specs.py        # 期望 1（#67）
git grep -l '2026-08-16-audit-remediation-master.md' # 期望恰 6 文件 = {4 旧归档 plan, 本 pass 归档 plan, final-report.md}；specs/INDEX.md 与 plans/（活跃区）不得出现
just audit-lint                                   # 绿
just check                                        # EXIT=0（含 docs workflow 面 mkdocs --strict）
```

（基线实测 2026-09-18：pass 前 7 处 = 4 旧归档 plan + final-report + 活跃 INDEX #40 行 + 本 plan 自身（Task 0 已跟踪）；pass 后仍 6 处，组成换为本 plan（随 PR 归档）替换 INDEX 行。总纲自身零自引。）
- [x] **Step 5: Commit + PR 流**——commit `docs(archive): spec #40 master closure done — 37-cluster program complete, ledger backfilled, spec #67 registered`（显式列全部涉及文件）；PR 描述含价值裁决摘要 + spec-deviations 全文 + ledger 摘要；`gh pr create` 取得 PR 号后，追加一个小 commit 将总纲头部 Status 链尾的「随本 PR 归档」补为「随 PR #N 归档」再 push（CI 重跑）
- [x] **Step 6: 产出 audit-T4.md**

## 验收覆盖表（spec/设计验收 → task → 验证命令）

| 验收 | Task | 命令 |
|---|---|---|
| 08-15 回写补齐（37 行编辑全处置） | T1 | Step 3 三 grep（0/0/3）+ closed 增量 +34 |
| 08-14 跨轮卫生（T12×6 + F513） | T2 | Step 3 逐行 grep |
| #67 登记且仅登记 | T3 | count_active_specs==2（中间态）+ INDEX grep |
| 总纲终稿归档 + 活跃队列正确 | T4 | count_active_specs==1 + git grep locus 集合 + just check EXIT=0 |
| lint 不回归 | T1/T4 | just audit-lint 绿 |

## Self-Review

- 覆盖：设计 v4 全部行动项（33+2+4+6+1 行、#67、终稿、归档、终态约定）均有 task 与命令 ✓
- 无占位符：注记全文在映射表，脚本机制明确 ✓
- 一致性：`spec #67` 计数判据与映射表三处出现点吻合；T4 中间态活跃数 2 与终态 1 区分声明 ✓
