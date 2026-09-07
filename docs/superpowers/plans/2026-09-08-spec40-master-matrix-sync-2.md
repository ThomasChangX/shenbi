# #40 总纲 master 维护 pass（C14/C16/C37 回标 + ledger 回写）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 master spec §6.1/§6.4 协议，把 C14/C16/C37 三簇的关闭事实回写到 §2/§7 矩阵与 findings-ledger，并刷新 INDEX #40 状态行——docs-only，零生产代码改动。

**Architecture:** 单次维护 pass，三个文件面（findings-ledger.md / master spec / INDEX.md）+ 验证命令（audit-lint 计数对照、mkdocs 链接面经 CI docs workflow 把关）。全部为文本编辑，无代码逻辑。

**Tech Stack:** 纯 Markdown 编辑 + grep/awk 机械核对 + `just check` 门禁。

## Global Constraints

- ledger 只改状态列（追加 `→ closed (...)` 段或改 open→注记），**不改任何证据列**（master §6.1 / §8 T2 先例）
- 注记格式统一 `→ closed (C-14 spec #52, PR #183)` / `→ closed (C-16 spec #54, PR #174)` / `→ closed (C-37 spec #51, PR #179)`（对齐既有 `closed (C-36 spec #50, PR #176)` 先例）
- master §2/§7 回标**不改历史计数**（条数列原样）；文件列改 archive/ 实名（三个文件均 ls 确认实存：`archive/2026-09-08-spec52-c14-weak-assertions-Done-PR183.md`、`archive/2026-08-16-audit-fixture-authenticity-fix.md`、`archive/2026-09-07-spec51-c37-dead-code-Done-PR179.md`）
- 编号 append-only；INDEX 活跃数 14 不变（#40 长期保留，master §5）
- commit 显式列文件路径（pathspec），禁 `git add -A`
- Conventional Commits：`docs(...)`

---

### Task 1: findings-ledger 回写（55 行 closed + 2 行 open 加注）

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（行 171-212、214、265-268、275-277、314-328、429、455、761-769、194）

**Interfaces:**
- Consumes: 阶段 2 核实的成员清单（权威源 `phase4-clustering.md:41,44`）
- Produces: ledger 中 C14/C16/C37 三簇成员状态全部落定，供 Task 2 矩阵引用与 audit-lint 计数核对

回写清单（逐条，共 55 closed + 2 open 加注）：

1. **C14 — 25 条** `open`/`verified` 状态尾追加 `→ closed (C-14 spec #52, PR #183)`：
   F701、F702、F703、F704、F705、F712、F713、F715、F716、F718、F719、F728、F729、F731、F733、F734、F735、F739、F740、F743、F744、F745、F746、F747、F748
   - F739/F740 追加短语 `(redirected to audit/snapshot.py per spec52 revision)`
   - F743 追加 `(file migrated to tests/unit/pipeline/test_state_heal.py)`
   - F728 追加 `(self-proof shell only; prod coverage via PR #43)`
2. **F730 单条**（ledger :194）追加 `→ closed (C-37 spec #51, PR #179) (volume_align module deleted in C37 PR)`
3. **C16 — 29 条** 追加 `→ closed (C-16 spec #54, PR #174)`：
   F751、F752、F753、F754、F761、F762、F763、F776、F777、F778、F779、F780、F781、F784、F785、F786、F787、F789、F790、F947、T801、T802、T803、T804、T805、T806、T807、T808、T809
4. **F750（:214）** 行尾追加注记格（不改原 `| open |` 字面量）：` | → note: deferred——G0.9 边界归属悬空（spec54 踢给 C37 R0 分桶表，但 c37-triage.md 43 成员清单未含 F750；候选归宿 C15 #53/C17 #55，见 master §8 deviation 2026-09-08） |`
5. **F1154（:455）** 行尾追加注记格：` | → note: blocked-on #57/C19 布局冻结 per spec54 T4；冻结前不得手工构造 manifest |`

**禁止触碰**：F782/F783（C17/F001 簇）、F767（已 closed C-35）。

- [ ] **Step 1: 记录回写前基线计数**

Run: `grep -c "closed (C-" docs/superpowers/audit-runs/2026-08-15/findings-ledger.md && grep -cE "^\| (F7(0[1-5]|1[23]|1[56]|1[89]|2[89]|3[1345]|39|40|4[3-8])) " docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`
Expected: 第一数记为 N0（回写前总数，当前 347）；第二数 = 25（C14 成员行命中，含 F743——`4[3-8]`）

- [ ] **Step 2: 用 python 脚本批量追加回写段**（只动目标行的最后一个 `| ... |` 状态格；逐 F 编号白名单，禁正则误伤）

采用 **C37 追加式**（最小 diff、不碰原状态字面量，与 ledger 既有 `| open | → closed (C-37 spec #51) (...)` 形态一致）：在行尾追加新表格格。

```bash
uv run python - <<'EOF'
import pathlib, re
p = pathlib.Path('docs/superpowers/audit-runs/2026-08-15/findings-ledger.md')
lines = p.read_text().splitlines(keepends=True)
c14 = {f"F{n}" for n in [701,702,703,704,705,712,713,715,716,718,719,728,729,731,733,734,735,739,740,743,744,745,746,747,748]}
c16 = {f"F{n}" for n in [751,752,753,754,761,762,763,776,777,778,779,780,781,784,785,786,787,789,790,947]} | {f"T{n}" for n in range(801,810)}
extra = {"F739":" (redirected to audit/snapshot.py per spec52 revision)","F740":" (redirected to audit/snapshot.py per spec52 revision)","F743":" (file migrated to tests/unit/pipeline/test_state_heal.py)","F728":" (self-proof shell only; prod coverage via PR #43)"}
def tag_for(fid):
    if fid in c14: return f"→ closed (C-14 spec #52, PR #183){extra.get(fid,'')}"
    if fid in c16: return "→ closed (C-16 spec #54, PR #174)"
    if fid == "F730": return "→ closed (C-37 spec #51, PR #179) (volume_align module deleted in C37 PR)"
    return None
notes = {
 "F750": "→ note: deferred——G0.9 边界归属悬空（spec54 踢给 C37 R0 分桶表，但 c37-triage.md 43 行未含 F750；候选归宿 C15 #53/C17 #55，见 master §8 deviation 2026-09-08）",
 "F1154": "→ note: blocked-on #57/C19 布局冻结 per spec54 T4；冻结前不得手工构造 manifest",
}
changed = 0
for i, ln in enumerate(lines):
    m = re.match(r"^\| (F\d+|T\d+) \|", ln)
    if not m: continue
    fid = m.group(1)
    stripped = ln.rstrip("\n")
    if not stripped.endswith(("| open |", "| verified |")): continue  # 只动 open/verified 行
    if fid in notes:
        lines[i] = stripped + " " + notes[fid] + " |\n"; changed += 1
    else:
        t = tag_for(fid)
        if t:
            lines[i] = stripped + " " + t + " |\n"; changed += 1
assert changed == 57, f"expected 57 rows changed, got {changed}"
p.write_text("".join(lines))
print("changed:", changed)
```

- [ ] **Step 3: 机械核对**

Run: `grep -c "closed (C-14 spec #52, PR #183)" docs/superpowers/audit-runs/2026-08-15/findings-ledger.md; grep -c "closed (C-16 spec #54, PR #174)" docs/superpowers/audit-runs/2026-08-15/findings-ledger.md; grep -c "closed (C-37 spec #51, PR #179)" docs/superpowers/audit-runs/2026-08-15/findings-ledger.md; grep -c "closed (C-" docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`
Expected: 25 / 29 / 1 / N0+55

- [ ] **Step 4: 跑 audit-lint 确认未破坏对账**

Run: `uv run python tools/lint_audit_run.py docs/superpowers/audit-runs/2026-08-15/ 2>/dev/null || just audit-lint`
Expected: exit 0（回写只加注记不改证据列，计数对账不受影响）

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/audit-runs/2026-08-15/findings-ledger.md
git commit -m "docs(ledger): writeback C14 25 + F730->C37 + C16 29 closures; F750/F1154 open annotations (spec #40 master pass)"
```

### Task 2: master spec 矩阵回标 + §8 deviation + §6.2 注记

**Files:**
- Modify: `docs/superpowers/specs/2026-08-16-audit-remediation-master.md`（:1 头部、:36 §2.1 C16 行、:61 §2.3 速览、:116 §6.2、:144/:146/:167 §7 三行、§8 末尾）

**Interfaces:**
- Consumes: Task 1 的 ledger 终态（注记文本与 PR 号引用一致）
- Produces: master 矩阵与现实一致，供 Task 3 INDEX 引用

- [ ] **Step 1: 五处编辑**

1. :1 头部 Status 尾部（`）` 前）追加：` · C14/C16/C37 回标 pass Done — 2026-09-08（C14 #52 PR #183 / C16 #54 PR #174 / C37 #51 PR #179）`
2. :36 `| C16 | fixture 真实性失真/G0.9 零执法 | 31 | B | L | 无（C14 重写断言的输入） |` → 簇列改 `C16 ✅ Done (PR #174 · spec #54)`
3. :61 §2.3 速览：日期戳改 `（2026-09-08）`，末句改为 `……C37 亦 Done（#51，PR #179）——批次 C（C27-C37）10 簇全部关闭；C16 Done（#54，PR #174）、C14 Done（#52，PR #183）；批次 B 余 C15/C17-C26 共 11 簇`
4. §7 三行：
   - :144 C14 行 → `| C14 ✅ Done (PR #183 · spec #52) | 弱断言/自证测试 | 26 | P1 | archive/2026-09-08-spec52-c14-weak-assertions-Done-PR183.md | B | M-L | C16 ✅（F730 剔除归 C37） |`
   - :146 C16 行 → `| C16 ✅ Done (PR #174 · spec #54) | fixture 真实性失真 | 31 | P0 | archive/2026-08-16-audit-fixture-authenticity-fix.md | B | L | —（F750 deferred→悬空见 §8、F1154 blocked-on #57/C19） |`
   - :167 C37 行 → `| C37 ✅ Done (PR #179 · spec #51) | 死代码零执法 | 43 | P1 | archive/2026-09-07-spec51-c37-dead-code-Done-PR179.md | C | L | C3/C7/C19/C28 裁决 |`
5. §6.2（:116）行尾追加注记：`（执行注记 2026-09-08：C16+C14 实际以 PR #174→#183 串行两 PR 合入，等效依据=C16 真实 fixture 先落、C14 断言重写以其为输入，序已满足）`
6. §8 末尾追加 deviation 段：

```markdown
Deviation（F750 归宿悬空，2026-09-08 本 pass）：spec54（C16）设计审查把 F750（集成测试手工捏造 worldbuilding 项目 vs 真实 world fixture，G0.9 边界争议）踢给「C37 R0 分桶表随写安全面定」，但 c37-triage.md 43 行未含 F750（F750 非 C37 成员），C37 关闭时未裁决——现保持 open，候选归宿 C15（#53）/C17（#55），待下次维护 pass 或对应簇 spec 认领（对齐 F0-06 先例）。
```

- [ ] **Step 2: 核对 archive 文件名引用实存**

Run: `ls docs/superpowers/specs/archive/2026-09-08-spec52-c14-weak-assertions-Done-PR183.md docs/superpowers/specs/archive/2026-08-16-audit-fixture-authenticity-fix.md docs/superpowers/specs/archive/2026-09-07-spec51-c37-dead-code-Done-PR179.md`
Expected: 三个文件均在

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-08-16-audit-remediation-master.md
git commit -m "docs(spec40): matrix re-annotation C14/C16/C37 + F750 deviation + C16+C14 serial-merge note (master maintenance pass)"
```

### Task 3: INDEX.md #40 状态行刷新

**Files:**
- Modify: `docs/superpowers/specs/INDEX.md`（:1 头注、:16-17 #40 状态行）

- [ ] **Step 1: 两处编辑**

1. 头注「最后更新」行（INDEX.md:2，:1 是页标题）改为：`2026-09-08（#40 总纲维护 pass：C14/C16/C37 回标 + ledger 回写，见 PR 描述；此前 #52 C14 Done PR #183）`
2. #40 状态行改为：`- **状态**：Design（记账 pass Done PR #147；§6.4 矩阵同步 pass Done PR #172；C14/C16/C37 回标 pass 2026-09-08——C14 #52 PR #183、C16 #54 PR #174、C37 #51 PR #179；索引长期保留） | **优先级**：🔴 P0（总纲）`
   （PR #172 补注属上一 pass 在 INDEX 侧的遗漏回填，PR 描述中注明来源——阶段 3 审查 M4）

- [ ] **Step 2: 核对活跃数仍一致**

Run: `grep -c "^### #" docs/superpowers/specs/INDEX.md`
Expected: 14（不变）

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/INDEX.md
git commit -m "docs(index): spec40 status line — C14/C16/C37 re-annotation pass + PR #172 backfill note"
```

### Task 4: 门禁验证 + 验收（证据型 task，零 commit）

- [ ] **Step 1: just check 全绿**

Run: `just check`
Expected: exit 0（docs workflow 的 mkdocs --strict 由 CI 把关，本地 check 覆盖 lint/test 面）

- [ ] **Step 2: 验收命令组**（spec §6 协议的机械验证）

```bash
grep -c "closed (C-" docs/superpowers/audit-runs/2026-08-15/findings-ledger.md   # = N0+55（347→402）
grep -c "✅ Done" docs/superpowers/specs/2026-08-16-audit-remediation-master.md   # = 回写前基线（29）+ 本 pass 新增 4（§2.1 C16、§7 C14/C16/C37 三行）= 33
git diff --stat main...HEAD  # 3 个被编辑文件 + 本 plan 文件自身，纯 docs
```

- [ ] **Step 3: 输出粘贴 progress.md `## 验收证据`**
