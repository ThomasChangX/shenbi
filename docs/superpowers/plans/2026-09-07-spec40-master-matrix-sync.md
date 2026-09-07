# Spec #40 总纲矩阵同步维护 pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 master spec §6.4 维护协议，把 PR #148-#171 期间关闭的 9 个批次 C 簇状态回标进 §2.1/§7 矩阵（含 C1/C26 两处 PR #147 遗漏），刷新状态速览行。

**Architecture:** 纯 docs 单文件维护 pass——只改 `docs/superpowers/specs/2026-08-16-audit-remediation-master.md` 一个文件，分两个 task（矩阵标注 / 叙述面刷新），各一个 commit；不改历史计数（§1/§8）、不动 §5 处置表与 F0-06 deviation 注记。

**Tech Stack:** 无代码——markdown 表格行内标注 + grep 验证。

**test_kind:** characterization（文档状态回写，验证 = grep 断言新标注存在 + 旧占位消失）

## Global Constraints

- §6.4 协议：只加行内状态标注与 archive 实名，**不改任何历史计数**（§1 总览、§4 量级、§8 清单原文不动）
- 本仓 spec 文件为纯文本文件名引用（无 markdown 链接）——文件名列写 `archive/<实名>` 纯文本，无 mkdocs 链接风险（阶段 3 已 grep 验证 `](` 零命中）
- Conventional commits，docs 前缀；commit 显式列文件路径（pathspec 保护用户 unstaged 改动）
- C32 用 ❌ Rejected 标注（非 Done），措辞取归档头原文；C28 为双 PR `#153 + #154`

---

### Task 1: §7 附录 + §2.1 矩阵行状态标注

**Files:**
- Modify: `docs/superpowers/specs/2026-08-16-audit-remediation-master.md`（§7 表 L127-166 区、§2.1 表 L26-37 区）

**Interfaces:** 无代码接口；Task 2 依赖本 task 的行内标注已落盘。

- [ ] **Step 1: §7 九行标注 + 文件名改 archive 实名**

逐行编辑（簇号列加标注，文件名列换 archive/ 前缀实名）：

| 行 | 簇号列改为 | 文件名列改为 |
|---|---|---|
| C27 | `C27 ✅ Done (PR #149)` | `archive/2026-08-16-c27-supply-chain-audit-design.md` |
| C28 | `C28 ✅ Done (PR #153 + #154)` | `archive/2026-08-16-c28-perf-antipatterns-design.md` |
| C29 | `C29 ✅ Done (PR #156)` | `archive/2026-08-16-c29-truncation-observability-design.md` |
| C30 | `C30 ✅ Done (PR #158)` | `archive/2026-08-16-c30-chapter-loop-staging-design.md` |
| C31 | `C31 ✅ Done (PR #161)` | `archive/2026-08-16-c31-injection-authorization-design.md` |
| C32 | `C32 ❌ Rejected (2026-09-07 · 11 条成员已由 PR #43 等效修复；F513 残留待新归属)` | `archive/2026-08-16-c32-write-audit-mechanism-design.md` |
| C33 | `C33 ✅ Done (PR #164)` | `archive/2026-08-16-c33-retry-failure-taxonomy-design.md` |
| C34 | `C34 ✅ Done (PR #168 · spec #48 于 #167 重写)` | `archive/2026-08-16-c34-path-layout-contract-design.md` |
| C35 | `C35 ✅ Done (PR #170)` | `archive/2026-08-16-c35-audit-process-hygiene-design.md` |

同表 C26 行文件名列占位 `（批次 B spec；见 INDEX 登记）` → `audit-shell-injection-fix.md`（不带日期前缀、不带 archive/——对齐相邻 C14-C25 活跃行的无日期实名形态；spec 仍活跃不迁移）。

- [ ] **Step 2: §2.1 三处补标**

- `C1` 行 → `C1 ✅ Done (PR #107)`（PR #147 T1 遗漏）
- `C32` 行 → `C32 ❌ Rejected (PR #163 · 已由 PR #43 等效修复)`
- `C34` 行 → `C34 ✅ Done (PR #168)`

- [ ] **Step 3: grep 验证**

```bash
grep -cE "C1 ✅|C2[789] ✅|C3[01345] ✅|C32 ❌" docs/superpowers/specs/2026-08-16-audit-remediation-master.md   # 期望 13（§7 10 含既有 C1 行 L129 + §2.1 新增 3：C1/C34 ✅ + C32 ❌）
grep -cE "archive/2026-08-16-c(2[789]|3[0-5])" docs/superpowers/specs/2026-08-16-audit-remediation-master.md  # 期望 9
grep -c "见 INDEX 登记）" docs/superpowers/specs/2026-08-16-audit-remediation-master.md                     # 期望 0
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-08-16-audit-remediation-master.md
git commit -m "docs(spec40): §2.1/§7 矩阵回标 C27-C35 关闭状态 + C1/C26 补漏（§6.4 维护 pass）"
```

### Task 2: 状态速览 / 头部 Status / §3 链注记刷新

**Files:**
- Modify: `docs/superpowers/specs/2026-08-16-audit-remediation-master.md`（L1 头、L59 状态速览、§2.2 末、§3 链 1）

**Interfaces:** 无。

- [ ] **Step 1: 四处叙述面编辑**

1. L59 状态速览整行替换为：
   `状态速览（2026-09-07）：批次 A（C1-C13）13 簇全部 Done（PR #107-#145）；批次 C（C27-C37）9 簇关闭（C32 Rejected、余 8 Done，PR #149-#170），仅 C36/C37 活跃（#50/#51）；批次 B（C14-C26）活跃。承接关系以 §7 为准。`
2. §2.2 分组表末追加一行说明：`> 簇状态以 §2.1/§7 行内标注为准（本分组表不逐簇标注）。`
3. §3 链 1 条目末追加：`（注：C32 已 Rejected 2026-09-07——R1-R4 已由 PR #43 等效修复；C33 已独立落地 PR #164，本链前提由驳斥轮收口。）`
4. L1 头部 Status 追加：`· §6.4 同步 pass Done — PR <本批>（C27-C35 回标，2026-09-07）`——PR 号开 PR 后回填追加 commit。

- [ ] **Step 2: grep 验证**

```bash
grep -c "状态速览（2026-09-07）" docs/superpowers/specs/2026-08-16-audit-remediation-master.md  # 期望 1
grep -c "状态速览（2026-09-03）" docs/superpowers/specs/2026-08-16-audit-remediation-master.md  # 期望 0
grep -c "C32 已 Rejected 2026-09-07" docs/superpowers/specs/2026-08-16-audit-remediation-master.md  # 期望 1
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-08-16-audit-remediation-master.md
git commit -m "docs(spec40): 状态速览/头部 Status/§3 依赖链注记刷新至 2026-09-07（§6.4 维护 pass）"
```

## 验收覆盖表

| spec 验收来源 | task | 可执行验证 |
|---|---|---|
| §6.4 簇状态变化回标 | T1 | Task 1 Step 3 三条 grep |
| §6.4 不改历史计数 | T1+T2 | `git diff main -- <spec> | grep -E '^[+-]' | grep -vE '✅|❌|archive/2026|C26|状态速览|簇状态以|注：C32|§6.4 同步'` 仅剩表头/上下文行 |
| mkdocs 无断链 | T2 后 | `just check`（docs workflow 本地等价：grep `](` 零命中已预验证） |

## Self-Review

- 覆盖：阶段 3 审查全部吸收项（I1 C26、I2 §3 注记、M3 日期、M4 §2.2 说明）均有 step；历史面（§8 计数、§2.1 C34 归位、F0-06）明确不动 ✅
- 无占位符；PR 号回填为既有仓库惯例（append commit），非 TBD ✅
- 类型一致性：纯文档无接口 ✅
