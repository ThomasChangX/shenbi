# Spec #40 Master 维护 pass（C15-C19 回标 + C19 ledger 回写 + F750/F0-06 归宿 #66）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 master 总纲（spec #40）的记账面与磁盘现实重新对齐：§7 矩阵 4 行回标 + C16 行内注解核销 + 速览刷新 + C19 簇 13 行 ledger 回写补做 + F750/F0-06 两条悬空 deviation 裁决归宿（登记微修 spec #66）。

**Architecture:** 纯 docs 记账 pass（specs/ + INDEX + 两份 findings-ledger + plan 登记面），零生产代码、零 tests 改动、零 dispatch。全部 infra 类（契约/登记/ledger 面），协调者亲自实现。无 TDD 循环——每个 task 的验证 = 机械核对命令（grep/对账 lint）+ 预期输出。

**Tech Stack:** markdown specs、findings-ledger 表、`just check`（含 `tools/count_active_specs.py`）、`just audit-lint`（`tools/lint_audit_run.py`）、git grep。

**复杂度:** 全部 infra（登记/ledger 面，协调者亲自实现）。**test_kind:** 机械核对（无新增 pytest；G3.4 评分不涉及；F947 不涉及——零 LLM dispatch）。**测试层级:** 无新增测试；防线 = `just check` + `just audit-lint` + 本 plan Task 7 的 git grep 断链复查（§7 表格文本引用不受 mkdocs --strict / test_doc_links 覆盖——specs/ 不在 mkdocs nav，且引用非 markdown 链接语法；系统性防线归 C23/spec #61）。

## Global Constraints

- ledger 只改**状态列与 `→` 注记格**，不改任何证据列（标题/严重度/文件/根因/证据/影响/修复建议/方法列原样）；`→` 开头的额外格是 lint 唯一容忍形态（lint_audit_run.py:92-96）
- 不改历史计数（§1 总览/列校验数字不动）、编号 append-only 不重排（#66 = 现最大 #65 + 1）
- pathspec commit：显式列文件路径，禁 `git add -A` / `git add .`
- 禁直推 main：一切改动走分支 + PR + CI 全绿
- Conventional commits：本 pass 用 `docs(spec40): ...` 前缀
- INDEX 头部「活跃 spec 数」10→11 与 #66 落盘必须**同分支同 PR**（Task 2 与 Task 3 分 commit 允许，但首个 push 在 Task 3 完成后——中间态 push 会令 CI ci.yml 的 count_active_specs step 红；pre-push hook 本身不含该项检查）

## 验收覆盖表（spec #40 本 pass 验收 = 8 项漂移全闭合）

| 漂移 | Task | 可执行验证 |
|---|---|---|
| 1-2. C15/C17 行漏标+断链 | Task 1 | `grep -E "^\| C15 |^\| C17 " master.md` 输出含 `✅ Done` + 实名路径；`test -f docs/superpowers/specs/archive/2026-08-16-audit-{zero-coverage,test-infra}-fix.md` |
| 3. C18 行漏标+断链 | Task 1 | 同上（artifact-contamination） |
| 4. C37 次号 | Task 1 | `grep "^\| C37 " master.md` 含 `PR #179 + #180` |
| 5. 速览虚报 | Task 1 | `grep -A1 "状态速览" master.md` 含 `余 C20-C26 共 7 簇` |
| 6. F750 悬空 | Task 2+3+4 | spec #66 存在且 INDEX 登记；ledger F750 行含 `re-homed spec #66` |
| 7. F0-06 悬空 | Task 2+3+5 | 同上（08-14 ledger F0-06 行 `→ re-homed spec #66`，状态 verified 不动） |
| 8. C19 ledger 缺失 | Task 4 | `grep -cE "closed \((C-19|obsolete)" 08-15 ledger` 对 C19 面 = 13 |

---

### Task 1: master spec 五处改动（矩阵回标 + 速览 + §8 裁决追加 + line 1 Status）

**Files:**
- Modify: `docs/superpowers/specs/2026-08-16-audit-remediation-master.md:1`（Status 头）、`:61`（状态速览）、`:145`（C15 行）、`:146`（C16 行前置列）、`:147`（C17 行）、`:148`（C18 行）、`:167`（C37 行）、`:183-185` 后（§8 追加）

**Interfaces:**
- Produces: §7 矩阵 C15-C19/C37 行终态标注（后续 cluster spec 归档 pass 的对账基准）；§8 F750/F0-06 裁决记录（spec #66 的登记依据）；速览「余 7 簇」口径（INDEX 头部同口径）

- [ ] **Step 1: line 1 Status 头追加本 pass 记录**

在 `**Status:** Design（…C14/C16/C37 回标 pass Done — 2026-09-08（C14 #52 PR #183 / C16 #54 PR #174 / C37 #51 PR #179））` 的最后一个 `）` 后追加：

```
 · C15-C18/C37 回标 + C19 速览补录与 ledger 回写 13 行 + F750/F0-06 归宿 #66 pass Done — 2026-09-11
```

- [ ] **Step 2: :61 状态速览整段替换**

旧：
```
状态速览（2026-09-08）：批次 A（C1-C13）13 簇全部 Done（PR #107-#145）；批次 C（C27-C37）11 簇全部关闭（C32 Rejected、余 10 Done，PR #149-#179）；C16 Done（#54，PR #174）、C14 Done（#52，PR #183）——批次 B（C14-C26）余 C15/C17-C26 共 11 簇。承接关系以 §7 为准。
```

新：
```
状态速览（2026-09-11）：批次 A（C1-C13）13 簇全部 Done（PR #107-#145）；批次 C（C27-C37）11 簇全部关闭（C32 Rejected、余 10 Done，PR #149-#179）；批次 B 已关闭 C14（#52，PR #183）、C15（#53，PR #189）、C16（#54，PR #174）、C17（#55，PR #191）、C18（#56，PR #194）、C19（#57，PR #198，T4-only）——余 C20-C26 共 7 簇。承接关系以 §7 为准。
```

- [ ] **Step 3: §7 矩阵五行替换**

C15 行（:145）旧→新：
```
| C15 | 关键零覆盖 | 12 | P2 | archive/audit-zero-coverage-fix.md | B | M | C14/C16 |
→
| C15 ✅ Done (PR #189 · spec #53) | 关键零覆盖 | 12 | P2 | archive/2026-08-16-audit-zero-coverage-fix.md | B | M | C14/C16 ✅ |
```

C16 行（:146）前置列注解旧→新：
```
—（F750 deferred→悬空见 §8、F1154 blocked-on #57/C19）
→
—（F750 → 微修 #66 见 §8、F1154 closed via #57 PR #198）
```

C17 行（:147）旧→新：
```
| C17 | 测试基础设施失效 | 18 | P1 | audit-test-infra-fix.md | B | M | — |
→
| C17 ✅ Done (PR #191 · spec #55) | 测试基础设施失效 | 18 | P1 | archive/2026-08-16-audit-test-infra-fix.md | B | M | — |
```

C18 行（:148）旧→新：
```
| C18 | 生产产物污染 | 17 | P1 | audit-artifact-contamination-fix.md | B | M | — |
→
| C18 ✅ Done (PR #194 · spec #56) | 生产产物污染 | 17 | P1 | archive/2026-08-16-audit-artifact-contamination-fix.md | B | M | — |
```

C37 行（:167）旧→新：
```
| C37 ✅ Done (PR #179 · spec #51) | 死代码零执法 | 43 | P1 | …
→
| C37 ✅ Done (PR #179 + #180 · spec #51) | 死代码零执法 | 43 | P1 | …
```
（仅改第一格，其余列原样）

- [ ] **Step 4: §8 末尾追加三行裁决记录**

在文件末尾（F750 deviation 段之后）追加：

```
裁决（F750 归宿，2026-09-11 本 pass）：候选归宿 C15（#53）/C17（#55）均已关闭且未认领，C20-C26 无测试质量面可挂靠——登记微修 spec #66（与 F0-06 合批），ledger F750 行注记 re-homed，实施由 #66 后续 SDD 承担。

裁决（F0-06 归宿，2026-09-11 本 pass）：C23（#61）为文档面 spec 管不到 pyproject 工具配置，原挂靠失效——并入微修 spec #66（统一值裁决在 #66 spec 内定），08-14 ledger F0-06 行注记 re-homed（状态 verified 不动）。

补录（C19 ledger 回写，2026-09-11 本 pass）：spec #57（C19）Done（PR #198）与归档（PR #199）均未回写 ledger——本 pass 补做 13 行（12 成员 + F1154 唯一归属条），分派依据 = spec #57 归档 T4-only 修订头/验收/已知残留段。
```

- [ ] **Step 5: 机械验证**

```bash
grep -cE "✅ Done" docs/superpowers/specs/2026-08-16-audit-remediation-master.md   # 预期恰 37（当前 34 + C15/C17/C18 新增 3；精确断言，防丢行）
grep -n "状态速览（2026-09-11）" docs/superpowers/specs/2026-08-16-audit-remediation-master.md   # 预期 :61 命中
```

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-08-16-audit-remediation-master.md
git commit -m "docs(spec40): master reannotation — C15-C18/C37 rows + status snapshot + F750/F0-06 adjudication to #66"
```

---

### Task 2: 新 spec #66 落盘

**Files:**
- Create: `docs/superpowers/specs/2026-09-11-leftover-microfix-f750-f006.md`

**Interfaces:**
- Produces: spec #66（INDEX 编号 = #65 + 1，append-only）；F750/F0-06 的唯一活跃归宿（ledger re-homed 注记指向它）

- [ ] **Step 1: 写入 spec 全文**

> **执行注记（audit-T2 两轮修正后）**：以下模板的素材映射表为首版——执行时被 audit-T2 发现素材前提错误（world-*-example.md 等实为 synthetic-sample 而非「真实产物」）并已修正。**spec 终稿以 `docs/superpowers/specs/2026-09-11-leftover-microfix-f750-f006.md` 为权威**（首选路径 = novel-output upstream-copy、载体双形态、truth 四面全有真实产物）。模板保留仅作过程记录。

```markdown
> **Date:** 2026-09-11 | **Status:** Design | **Severity:** 🟡 P2（两 finding 均 P2 · 微修 S 量级）| **方法:** 机械替换 + 配置统一（无需 systematic-debugging——两 finding 根因与修复路径均已定案）
> **系列:** 2026-08-15 审计轮遗留收口（非 37 簇成员——F750 原属 C16 边界争议条被 spec #54 设计审查 deferred 出局、候选归宿 C15/C17 双亡；08-14 轮 F0-06 无簇 squarely 承接；归宿由 spec #40 master 维护 pass 2026-09-11 裁决登记）| **依赖:** F750 素材已在盘（tests/fixtures/ 真实产物，见任务 1 清单）；F0-06 无依赖 | **范围:** tests/integration/test_gate_cli.py 单文件 + pyproject.toml 三处配置值

# 遗留微修批：F750 集成测试真实 fixture 化 + F0-06 python 版本三元统一

## 1. F750：test_gate_cli.py 捏造项目换真实 fixture 拷贝

**根因**（Z7-b:154 原文）：`_make_worldbuilding_project`（:27-97）手写 novel.json/story_bible/rules/locations/truth 模板（占位文本），而 tests/fixtures/ 已有真实产物；本测试是完整 skill 产出形态的场景（PASS 路径的 story_bible 结构即被测语义的一部分），不属 G0.9 豁免类别（gate 内部输入/接线单测豁免先例见 test_g4_directory.py:4-7、test_trigger_context.py:3-5）；手写中文占位过 gate 的方式可能与真实产物分布不同（bullet 密度、字数）。

**修复**（Z7-b 修复建议原样）：story_bible/rules/locations 等替换为真实 fixture 拷贝，仅保留目录组装逻辑。素材映射：

| 捏造面（现 :27-97） | 真实素材（tests/fixtures/） |
|---|---|
| novel.json | novel-example.json |
| genre-config.json | genre-config-example.json |
| world/story_bible.md | world-story-bible-example.md |
| world/rules.md | world-rules-example.md |
| world/locations.md | world-locations-example.md |
| truth/*.md 四模板 | 四面全有真实素材：truth-current_state.md / truth-character_matrix.md / truth-emotional_arcs.md / truth-chapter_summaries.md |
| characters/protagonist.md | character-profile-example.md / characters/ |

**验收：**
- `grep -n "Content here\|这是一个宏大而复杂的世界" tests/integration/test_gate_cli.py` 零命中（捏造文本清除）
- `uv run pytest tests/integration/test_gate_cli.py -v` 全绿（G4 PASS 路径在真实 fixture 拷贝下仍 PASS）
- 新引用的 fixture 均带 provenance 标注或属既有豁免白名单（G0.9/g0_purity 不新增违规）

## 2. F0-06：pyproject python 版本三元统一

**根因**（08-14 ledger F0-06）：`requires-python = ">=3.11"`（:8）vs mypy `python_version = "3.12"`（:379）vs basedpyright `pythonVersion = "3.11"`（:398）——类型检查语义基准漂移（3.11 vs 3.12 语法/API 差异可能漏报/误报）。

**裁决（spec 内定稿）**：统一为 **3.11**（对齐 requires-python 下限——工具链按支持下限校验是保守面；升 3.12 会放宽 requires-python 语义，超出微修边界）。即 mypy :379 `"3.12"` → `"3.11"`；basedpyright :398 已是 3.11 不动；:8 不动。

**验收：**
- `grep -n "python_version\|pythonVersion\|requires-python" pyproject.toml` 三处值一致（3.11 口径）
- `just check` 全绿（mypy/basedpyright 在 3.11 基准下无新报错）

## 边界

不动 src/ 生产代码；不改 ledger 状态（实施 PR 合并时由该 SDD 份回写 F750/F0-06 两行 closed）。
```

- [ ] **Step 2: 验证 + Commit**

```bash
test -f docs/superpowers/specs/2026-09-11-leftover-microfix-f750-f006.md && echo OK
git add docs/superpowers/specs/2026-09-11-leftover-microfix-f750-f006.md
git commit -m "docs(spec): register #66 leftover microfix — F750 real-fixture + F0-06 python triple (re-homed by spec40 pass)"
```

---

### Task 3: INDEX.md 三处（#66 登记 + 头部刷新 + #40 状态字段）

**Files:**
- Modify: `docs/superpowers/specs/INDEX.md:3-4`（头部）、#40 行（状态字段）、#65 行后（#66 登记）

**Interfaces:**
- Consumes: Task 2 的 spec #66 文件（登记行的文件字段指向它）
- Produces: INDEX 活跃计数 11（`just check` count_active_specs 对账基准）

- [ ] **Step 1: 头部两行替换**

```
> **最后更新**：2026-09-08（#57 C19 Done PR #198——快照词面定稿 T4-only）
> **活跃 spec 数**：10（#57 C19 Done PR #198）
→
> **最后更新**：2026-09-11（#66 微修登记 F750/F0-06 归宿；#40 pass：C15-C18/C37 回标 + C19 速览补录与 ledger 回写）
> **活跃 spec 数**：11（#66 微修登记 F750/F0-06 归宿）
```

- [ ] **Step 2: #40 行状态字段追加**

在 `；索引长期保留）` 前插入：
```
；C15-C18/C37 回标 + C19 速览补录与 ledger 回写 13 行 + F750/F0-06 归宿 #66 pass 2026-09-11
```

- [ ] **Step 3: #65 行后追加 #66 登记**

```markdown
### #66 · 遗留微修批：F750 集成测试真实 fixture 化 + F0-06 python 版本三元统一

- **文件**：`2026-09-11-leftover-microfix-f750-f006.md`
- **系列**：2026-08-15 审计轮遗留收口（非 37 簇成员——F750 原簇 C16 边界争议条 deferred 出局、候选归宿 C15/C17 双亡；08-14 轮 F0-06 无簇承接；归宿由 spec #40 master 维护 pass 2026-09-11 裁决）
- **状态**：Design | **优先级**：🟡 P2（两 finding 均 P2 · 微修 S 量级）
- **方法**：机械替换 + 配置统一（两 finding 根因与修复路径均已定案，无需 systematic-debugging）
- **依赖**：F750 素材源在盘（novel-output/xinghuo-ranqiong/ 真实产物全套 + fixtures 既有 upstream-copy/synthetic-sample 面，映射表见 spec）；F0-06 无依赖
- **内容**：(1) F750：test_gate_cli.py `_make_worldbuilding_project`（:27-97）手工捏造换 fixture 拷贝（首选 novel-output upstream-copy 引入、载体双形态，映射表见 spec），仅保留目录组装逻辑；(2) F0-06：pyproject python 版本三元统一为 3.11（mypy :379 改值，其余两处已符）
- **对应 plan**：❌ 未写
```

- [ ] **Step 4: 验证 + Commit**

```bash
uv run python tools/count_active_specs.py   # 预期：INDEX 头 11 == 目录扫描 11（PASS）
git add docs/superpowers/specs/INDEX.md
git commit -m "docs(index): register #66 + spec40 pass status + header refresh (active 10->11)"
```

---

### Task 4: 08-15 ledger 回写（C19 簇 13 行 + F750 re-homed）

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（:70 F306、:81 F317、:214 F750、:252 F348、:254 F350、:255 F351、:330 F792、:441 F1109、:455 F1154、:456 F1155、:575 F890、:698 T1503、:755 T708、:757 T710）

> **行号仅为参考锚点，执行时以 finding ID 定位**（`grep -n "^| <ID> "` 重定位后编辑）——行号若与本表偏移，以 ID 为准。

**Interfaces:**
- Consumes: spec #57 归档（`archive/2026-08-16-audit-snapshot-unify-fix.md`）的 T4-only 修订头/验收/已知残留段 = 分派唯一权威
- Produces: C19 簇 ledger 终态（`just audit-lint` 的行结构合规输入）

- [ ] **Step 1: 13 行状态列替换（12 簇成员 + F1154 唯一归属条；仅状态列，证据列不动）**

| finding ID | 旧状态 | 新状态 |
|---|---|---|
| F306（:70） | verified | `closed (obsolete — spec #57, PR #198; 随 #26 路径 3 移除消解)` |
| F317（:81） | open | `closed (obsolete — spec #57, PR #198; 随 #26 路径 3 移除消解)` |
| F348（:252） | open | `closed (obsolete — spec #57, PR #198; 随 #26 路径 3 移除消解)` |
| F350（:254） | open | `closed (C-19 spec #57, PR #198 · 半存活面已记 spec #57 已知接受残留，下轮勿重复立案)` |
| F351（:255） | open | `closed (obsolete — spec #57, PR #198; 随 #26 路径 3 移除消解)` |
| F792（:330） | open | `closed (C-19 spec #57, PR #198 · 代码面随 #26 路径 3 移除消解 + 词面 T4 定稿)` |
| F1109（:441） | open | `closed (C-19 spec #57, PR #198 · 磁盘遗留面 T4 item 11 处置)` |
| F1154（:455） | open | `closed (C-19 spec #57, PR #198 · 显式缺失报告形态)` + note 格更新（见 Step 2） |
| F1155（:456） | open | `closed (C-19 spec #57, PR #198)` |
| F890（:575） | open | `closed (C-19 spec #57, PR #198)` |
| T1503（:698） | open | `closed (obsolete — spec #57, PR #198; 随 #26 路径 3 移除消解 · =F351 历史面)` |
| T708（:755） | open | `closed (obsolete — spec #57 T2 路径 3 下不执行; 写方随 #26 PR #105 移除消解)` |
| T710（:757） | open | `closed (C-19 spec #57, PR #198)` |

- [ ] **Step 2: F1154 与 F750 的 note 格更新**

F1154（:455）旧 note：
```
→ note: blocked-on #57/C19 布局冻结 per spec54 T4；冻结前不得手工构造 manifest
→
→ note: re-homed resolution — blocked 解除（#57 Done PR #198），验收 3 以显式缺失报告形态达成 per PR #198 遗留处置 commit
```

F750（:214）旧 note 尾部追加：
```
；2026-09-11 re-homed spec #66（master §8 裁决——候选 C15/C17 已关闭未认领），状态保持 open 至 #66 实施
```

- [ ] **Step 3: 机械验证**

```bash
grep -cE "closed \((C-19|obsolete)" docs/superpowers/audit-runs/2026-08-15/findings-ledger.md   # 预期 13
just audit-lint   # 预期 PASS（行数不变、→ 格合规、severity 列未动）
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/audit-runs/2026-08-15/findings-ledger.md
git commit -m "docs(ledger): backfill C19 cluster writeback 13 rows + F750 re-homed to #66 (missed by PR #198/#199)"
```

---

### Task 5: 08-14 ledger F0-06 行追加 re-homed 注记

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-14/findings-ledger.md:12`

**Interfaces:**
- Consumes: Task 2 的 spec #66（注记指向）
- Produces: F0-06 行 12 格形态（状态 verified **不动**）

- [ ] **Step 1: 行尾追加第 12 格**

行尾 `| deep-read | verified |` → `| deep-read | verified | → re-homed spec #66 (2026-09-11 · master §8 裁决；状态保持 verified 至 #66 实施后关闭) |`

- [ ] **Step 2: 验证 + Commit**

```bash
grep -c "re-homed spec #66" docs/superpowers/audit-runs/2026-08-14/findings-ledger.md   # 预期 1
git add docs/superpowers/audit-runs/2026-08-14/findings-ledger.md
git commit -m "docs(ledger): F0-06 re-homed annotation to spec #66 (08-14 run)"
```

---

### Task 6: plan 登记面（plans/INDEX.md）

**Files:**
- Modify: `docs/superpowers/plans/INDEX.md`（活跃登记 + 计数 0→1）

- [ ] **Step 1: 登记**

「## 活跃 Plan」节下追加：
```markdown
- `2026-09-11-spec40-master-reannotation-pass.md` — spec #40 维护 pass（C15-C19 回标 + C19 ledger 回写 + F750/F0-06 归宿 #66）· 执行中
```
头部：`> **最后更新**：2026-09-08（#57 C19 T4 plan 归档——Done PR #198）` → `> **最后更新**：2026-09-11（spec40 回标 pass plan 登记）`；`**活跃 plan 数**：0 | **已归档**：110` → `**活跃 plan 数**：1 | **已归档**：110`。

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/plans/INDEX.md
git commit -m "docs(plans): register spec40 reannotation pass plan (active 0->1)"
```

---

### Task 7: 终验（全部门禁）

- [ ] **Step 1: `just check` 全绿**（含 count_active_specs 11 对账、audit-lint、docs workflow 同构面）

预期：exit 0。若 count FAIL → 检查 Task 3 头部计数与 #66 文件是否同分支。

- [ ] **Step 2: `just audit-lint` 单独复跑**（ledger 双 run 面）

预期：PASS（counts_reconcile 无感——13 行不改行数；carryover 无感——08-15 是最后一个有 ledger 的 run）。

- [ ] **Step 3: §7 断链复查 one-liner**

```bash
grep -E "^\| C[0-9]+ " docs/superpowers/specs/2026-08-16-audit-remediation-master.md | grep -oE "(archive/)?[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-zA-Z0-9-]+\.md|[a-z0-9-]+-fix\.md" | sort -u | while read f; do
  test -f "docs/superpowers/specs/$f" || test -f "docs/superpowers/specs/archive/${f}" || echo "BROKEN: $f"
done
# 预期：无 BROKEN 输出（活跃 C20-C26 指向 specs/ 根实名、已关闭簇指向 archive/ 实名）
```

- [ ] **Step 4: 验收覆盖表逐条跑**（本 plan 头部表格 8 行,每行命令 + 输出粘贴 progress.md `## 验收证据`）

- [ ] **Step 5: 如有修复则 commit，否则记录通过输出**
