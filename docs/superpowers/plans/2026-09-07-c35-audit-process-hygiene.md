# C35 审计过程自身卫生 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为审计闭环自身建立机械校验：ledger/记账 lint、跨轮承接机制、审计 prompt 规则补丁、分支与 INDEX 卫生清偿，关闭 C35 全部 18 条 findings。

**Architecture:** 三个新工具脚本（`tools/lint_audit_run.py`、`tools/generate_carryover.py`、`tools/count_active_specs.py`）全部接入 `just check`（CI ci.yml 已含逐条 lint 命令，同步补登）；冻结历史 run（2026-08-14/15）只加豁免注记不改行；ledger 回写沿用既有 `→ closed (C-35 spec #49) (merged-into-F1177, spec #49, PR #N)` 注记格式。

**Tech Stack:** Python 3.11+（tools/ 脚本，同仓既有 lint_* 模式：argparse + sys.exit(0/1) + print 输出；tools/ 不受 structlog 约束——AGENTS.md:114 该规则限 src/shenbi/）、pytest（tests/unit/）、just。

## Global Constraints

- tools/ 脚本模式：`uv run python tools/<name>.py`，无参或 `--check` = 全量模式，输出 PASS/FAIL 行，失败 `sys.exit(1)`（对齐 lint_repo_consistency.py 先例）
- 冻结 run 目录（docs/superpowers/audit-runs/2026-08-14、2026-08-15）：**只新增文件**（carryover.md、audit-lint-exemptions.json、注记列追加），**不修改既有行内容**
- 豁免 schema（spec R1）：`{"exemptions": [{"check": str, "id": str, "reason": str, "date": "YYYY-MM-DD"}]}`；`id` 为 F/T 编号、行标识或 run 级 `run:<check>`；豁免不命中=FAIL
- 测试引用真实审计产物路径 `docs/superpowers/audit-runs/2026-08-14|15/`（G0.9：真实产物，非手写 mock）；单元测试造的临时 run 目录用 tmp_path 组装（测试输入非 fixture 声明面）
- ledger 行格式：11 列管道表 `| ID | 标题 | 类别 | 严重度 | 证据 | 根因 | 验证 | 影响 | 建议方向 | 深度 | 状态 |`，回写注记以追加列形态（既有先例：`... | open | → closed (...) (...) |`）
- 全程禁 `shenbi-dispatch` / `pipeline`（核心原则 8）；验证命令一律 `uv run` / `just`

---

### Task 1: `tools/lint_audit_run.py` — 行格式 lint + 豁免机制

**Files:**
- Create: `tools/lint_audit_run.py`
- Test: `tests/unit/test_lint_audit_run.py`

**Interfaces:**
- Produces: `lint_run(run_dir: Path) -> list[Finding]`（Finding: dataclass{check, id, message}）；`load_exemptions(run_dir: Path) -> dict[str, set[str]]`（check → ids 集合，`run:<check>` 键并入）；`validate_exemptions(run_dir, exemptions, findings) -> list[Finding]`（schema 校验 + 不命中豁免=FAIL）；CLI：无参=lint 全部 `docs/superpowers/audit-runs/*/`；`<run-dir>` 参数=单目录；`--verify-carryover` 开关（Task 3 实现 diff 前，先保留参数占位并 pass-through）
- 检查项（check 名）：`row_columns`（主体列数≠11，**或**第 12+ 列不匹配注记列语法 `→ closed (…)`/`→ merged-into-…` 白名单——既有回写先例是追加列，11 列硬约束会让 Task 5/6 回写后 check 自爆）、`pipe_escape`（单元格拉管道）、`id_unique`（同 ID 复现）、`dup_row`（整行重复）、`title_placeholder`（标题==ID，F979）
- 豁免 id 形态：`F/T 编号`、`row:<ledger 行号>`、`run:<check>`（run 级整检查豁免——08-14 的 16 条 F972 畸形行整组用 run:row_columns，避免逐行豁免爆炸）

- [ ] **Step 1: 写失败测试**（row_columns/pipe_escape/id_unique/dup_row/title_placeholder 各一例 + 豁免加载/消音/不命中=FAIL + run 级豁免；输入用 tmp_path 组装的 11 列管道表与真实 08-15 run 目录引用）

```python
# tests/unit/test_lint_audit_run.py 关键用例骨架（全部 @pytest.mark.unit）
import pytest
from pathlib import Path
from tools.lint_audit_run import lint_run, load_exemptions, validate_exemptions, apply_exemptions

GOOD = "| F1 | 标题 | error | P1 | e | r | v | i | s | d | open |"
def test_row_columns(tmp_path):
    d = tmp_path / "run"; d.mkdir()
    (d / "findings-ledger.md").write_text("| ID | t |\n|---|---|\n| F1 | x |\n")
    f = lint_run(d)
    assert any(x.check == "row_columns" for x in f)

def test_exemption_mutes(tmp_path):
    ...  # exemptions json 消音 row_columns:F1；剩余 findings 为空
def test_stale_exemption_fails(tmp_path):
    ...  # 豁免 id 无对应命中 → validate_exemptions 产出 stale-exemption FAIL
def test_real_0815_run_lint():
    raw = lint_run(Path("docs/superpowers/audit-runs/2026-08-15"))
    assert raw  # 豁免前原始命中非空（豁免落地前的事实 pin）
def test_real_0815_run_after_exemptions():
    raw = lint_run(Path("docs/superpowers/audit-runs/2026-08-15"))
    exemptions = load_exemptions(Path("docs/superpowers/audit-runs/2026-08-15"))
    assert not apply_exemptions(raw, exemptions)  # Task 3 豁免落地后消音为空
```

- [ ] **Step 2: 跑测试确认失败** `uv run pytest tests/unit/test_lint_audit_run.py -v` → ModuleNotFoundError
- [ ] **Step 3: 实现** `tools/lint_audit_run.py`：markdown 表逐行 `line.strip().strip('|').split('|')`（注意 `\|` 转义先保护再切分）；豁免文件 `<run-dir>/audit-lint-exemptions.json`；CLI argparse（无参默认全目录 glob）；输出 `PASS <run>`/`FAIL <run>: <check> <id> <msg>` 行
- [ ] **Step 4: 跑测试通过** `uv run pytest tests/unit/test_lint_audit_run.py -v`
- [ ] **Step 5: Commit** `git add tools/lint_audit_run.py tests/unit/test_lint_audit_run.py && git commit -m "feat: audit-run ledger format lint with exemption mechanism (spec #49 R1, C35)"`

### Task 2: 三方计数对账检查（zones ↔ ledger ↔ final-report）

**Files:**
- Modify: `tools/lint_audit_run.py`
- Test: `tests/unit/test_lint_audit_run.py`（追加）

**Interfaces:**
- Consumes: Task 1 `lint_run` 骨架
- Produces: `reconcile(run_dir: Path) -> list[Finding]`，检查名 `counts_reconcile`（run 级聚合，豁免 id=`run:counts_reconcile`）：
  - ledger 条目数（按 ID 前缀 F/T/D 分组）↔ final-report 统计（**双格式抽取**：代码块 `F=… T=… D=… G=… total=…` 行与 markdown 表 `| P0 | n |`/`**总 findings: N**` 行——08-14 报告无机械统计段，数字全在表与 prose 里）
  - zones 并集 = `cat zones/*.files | sort -u`（glob 钉死 `*.files`，排除 d2-drift-sampling.txt 类杂项）↔ final-report 表 A/tracked 声称数（08-14 实测 2755 vs 2738 即 F973 命中形态；报告侧单数字也须与并集一致）
- Produces: `report_internal(run_dir: Path) -> list[Finding]`，检查名 `report_internal`（run 级聚合）：
  - 报告声称 total/severity 分布 ↔ **计算出的 ledger 现值**（08-14 报告 781 vs ledger 786 = F969 命中形态）
  - severity 单元格归一化：剥离全/半角括号后缀（`M（升级证据已具备…）`→`M`）
  - final-report 内同量两处声称须相等 + `sum=N` 行须等于分量之和（F1176 历史形态——**注意 08-15 报告该矛盾已被修正**（:40「含 F1176 修正（1083）」），F1176 以核实注记闭合，不造豁免）
- **F975/F1176 均无现存机械命中面**：闭环口径为「执行期核实注记 + 随簇回写关闭」（spec 验收已同步降级），不造豁免——豁免不命中=FAIL 纪律下，无命中就不许有豁免条目
- **豁免清单冻结程序**：豁免 json 不许按 plan 预写——实现后先 dry-run `uv run python tools/lint_audit_run.py`（全目录）拿真实命中清单，再按「命中项 → spec 成员映射」生成豁免（08-15 的 report_internal 命中系 PR #147 严重度校准后报告冻结的历史漂移，run 级豁免 reason 注明）；pipe 击伤行（severity 列含「漏报」等错位）按实际命中入豁免

- [ ] **Step 1: 失败测试**：tmp_path 组装 mini run（ledger 3 行 + zones 2 文件 + final-report 双格式统计（表+代码块）数字故意错 1 处）→ `counts_reconcile`/`report_internal` 命中；真实 08-14 run 引用 → 至少命中 F969（781↔786）与 F973（2755↔2738）（豁免前）
- [ ] **Step 2: 确认失败 → 实现 → 通过**（正则抽取 final-report 代码块内统计行；zones 并集去重计数）
- [ ] **Step 3: Commit** `test: count reconciliation checks zones↔ledger↔final-report (spec #49 R1)`

### Task 3: carryover 生成器 + verify-carryover + 冻结 run 豁免落地 + just 接线

**Files:**
- Create: `tools/generate_carryover.py`
- Create: `docs/superpowers/audit-runs/2026-08-14/carryover.md`（真实生成物）
- Create: `docs/superpowers/audit-runs/2026-08-14/audit-lint-exemptions.json`、`docs/superpowers/audit-runs/2026-08-15/audit-lint-exemptions.json`
- Modify: `tools/lint_audit_run.py`（`--verify-carryover` 实现：run 目录有 carryover.md 时，逐条目 grep 本轮 ledger 承接状态注记，未承接=FAIL；无 carryover.md=显式 skip log）
- Modify: `justfile`（`audit-lint` recipe + `check` 增行）、`.github/workflows/ci.yml`（lint 步骤增行，对齐既有 lint_repo_consistency 位置）
- Test: `tests/unit/test_generate_carryover.py`、`tests/unit/test_lint_audit_run.py`（追加 verify-carryover 用例）

**Interfaces:**
- Produces: `generate_carryover(prev_ledger: Path, out: Path) -> int`（抽取 status ∈ {verified, open} 全 severity 条目，行格式 `<ID> <severity> <status> <标题>`）；CLI `uv run python tools/generate_carryover.py <prev-run-dir>` 默认写 `<prev-run-dir>/carryover.md`
- `--verify-carryover` 语义：run 目录含 carryover.md 时，next-run = `docs/superpowers/audit-runs/` 下字典序**下一个** run 目录（08-14→08-15；末轮无 next = 显式 skip log）；逐条目 grep next-run ledger 的承接注记/同 ID 行，未承接=FAIL（08-14 演示文件的断链本体以 run:verify-carryover 豁免）
- 验收演示（spec R2）：`grep -Ecw "F1301|F1302|F1320" docs/superpowers/audit-runs/2026-08-14/carryover.md` ≥3
- 豁免内容（从 dry-run 真实命中生成，非预写）：08-14 run（run:row_columns=F972 畸形行组 + 既有 12 列 specced/verified 行、F969/F973 对账缺口、run:verify-carryover 演示豁免）；08-15 run（run:report_internal=PR #147 校准后报告冻结漂移 + dry-run 实际命中的 pipe/列错位行）

- [ ] **Step 1: 失败测试**：generate_carryover 用真实 08-14 ledger → 输出含 F1301/F1302/F1320 verified 行、不含 closed/merged 条目；verify-carryover：tmp mini run carryover 2 条 1 条未承接 → FAIL 1；无 carryover.md → skip 不 FAIL
- [ ] **Step 2: 实现两脚本 + 落两份豁免 json（reason 注明冻结历史 run + spec #49）**
- [ ] **Step 3: 实跑验收**：`uv run python tools/generate_carryover.py docs/superpowers/audit-runs/2026-08-14` + grep ≥3；`uv run python tools/lint_audit_run.py`（全目录无参）→ 全 PASS（豁免生效）
- [ ] **Step 4: justfile/ci.yml 接线**：`audit-lint: uv run python tools/lint_audit_run.py`（无参=全目录+verify-carryover）；`check` 与 ci.yml lint 步骤各增一行
- [ ] **Step 5: `uv run pytest tests/unit/test_generate_carryover.py tests/unit/test_lint_audit_run.py -v` 通过**
- [ ] **Step 6: Commit** `feat: cross-round carryover generator + verify-carryover + frozen-run exemptions + just/ci wiring (spec #49 R1/R2)`

### Task 4: ID 命名空间裁决注记 + `tools/count_active_specs.py`

**Files:**
- Create: `docs/superpowers/audit-runs/ID-NAMESPACE-MIGRATION.md`（裁决：新轮采用 `<轮日期>-F<NN>` 前缀（`2026-08-16-F117` 形态），旧轮与既有 spec 引用不动，新轮生效；记录 F978/F956 证据）
- Create: `tools/count_active_specs.py`
- Modify: `justfile`、`.github/workflows/ci.yml`（各增一行）
- Test: `tests/unit/test_count_active_specs.py`

**Interfaces:**
- Produces: `count_active(path: str) -> int`（**文件数口径**：`docs/superpowers/specs/*.md` 顶层 .md 文件数、排除 INDEX.md；archive/ 子目录不被该 glob 命中）；CLI 核对 INDEX 头计数——**抽取规则钉死：`活跃 spec 数**：` 之后、`（` 之前的第一个整数**（prose 括注防误parse）；差值非零 → exit 1

- [ ] **Step 1: 失败测试**：tmp specs 目录（3 spec + INDEX 头写 3 → PASS；写 4 → FAIL）；真实 main 当前应 PASS（19==19）
- [ ] **Step 2: 实现 + 接线 + `just check` 局部跑通**
- [ ] **Step 3: Commit** `feat: active-spec count lint + ID namespace migration note (spec #49 R2/R4)`

### Task 5: R3 审计 prompt 两规则 + R4 卫生（分支删除、triage 记录、severity 注记、T1502 记录）

**Files:**
- Modify: `docs/superpowers/full-project-audit-prompt.md`（补两规则：①跨段重复立案须显式 merged 标注；②「N tests」类声称必须附文件名与命令——置于 Iron Law 段后）
- Create: `docs/superpowers/audit-runs/2026-08-15/dependabot-triage-2026-09-07.md`（10 条 PR 逐条 upgrade/close + 理由；安全补丁类标 urgent 建议另开 chore PR）
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（F771/F772 行附 phase4 §4 提案引用注记，不改严重度列）

**动作：**
- [ ] **Step 1**: prompt 两规则落文，验收 `grep -n "跨段重复立案须显式\|必须附文件名与命令" docs/superpowers/full-project-audit-prompt.md` 命中
- [ ] **Step 2**: `gh pr view <N>` 逐条核对 10 个 dependabot PR 内容 → 写 triage 记录（决策口径：主版本升级=close 待专门批次；补丁级=upgrade 建议；安全公告=urgent）
- [ ] **Step 3**: F771/F772 注记 + T1502 处置记录写入（progress.md + 本 task commit message 附裁决）
- [ ] **Step 4**: `git push origin --delete docs/archive-spec44-c30`（唯一已合并残留；操作后 `git branch -r --merged origin/main` 除 main/HEAD 外为空——核验输出粘贴 progress）
- [ ] **Step 5: Commit** `docs: audit prompt assertion rules + dependabot triage record + severity proposal annotations (spec #49 R3/R4)`

### Task 6: C35 簇回写关闭（18 条）+ AGENTS.md 命令补登

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（18 条成员行追加 `→ closed (C-35 spec #49) (merged-into-F1177, spec #49, PR #<N>)` 注记列——PR 号在阶段 9 开 PR 后回填该 commit；F1176 软残条保留原文仅附注记）
- Modify: `AGENTS.md`（Key Commands 增 `just audit-lint` 一行）
- Modify: `docs/superpowers/specs/INDEX.md`（#49 条目状态改 Done（PR 回填）→ 归档在阶段 12，本 task 只改状态字段）

**验收（spec 簇级）：** `just check` 全绿；18 条 closed 注记 grep 计数 = 18
- [ ] **Step 4**: PR 号回填 = 开 PR 后**追加 commit**（禁 amend/force-push，pre-push hook 在）
- [ ] **Step 1**: 回写 18 条 + grep 核验 `grep -c "closed (C-35 spec #49)" findings-ledger.md` = 18
- [ ] **Step 2**: AGENTS.md 增行
- [ ] **Step 3**: `just check` 全绿 → Commit `docs: close C35 cluster — 18 findings merged-into F1177 writeback (spec #49)`

## 验收覆盖表（spec 验收 → task → 命令）

| spec 验收 | task | 验证 |
|---|---|---|
| R1 lint 抓出 F969/F972/F973/F975/F1176 且豁免闭合 | T2/T3 | `just audit-lint`（无参）全 PASS；豁免 json 五 id 在列 |
| R1 just check 接线 | T3/T4 | `just check` 含 audit-lint 行且全绿 |
| R2 承接演示 ≥3 | T3 | `grep -Ecw "F1301|F1302|F1320" docs/superpowers/audit-runs/2026-08-14/carryover.md` ≥3 |
| R3 prompt 两规则 | T5 | grep 两规则字符串命中 |
| R4 分支无残留 | T5 | `git branch -r --merged origin/main` 仅 main/HEAD |
| R4 INDEX 计数机械核对 | T4 | `uv run python tools/count_active_specs.py` PASS |
| R4 severity 12 项核实注记 | T5 | F771/F772 注记 + 12 项逐项对照 phase4 §4 表 |
| 簇级 18 条关闭 | T6 | grep 计数 18 |
