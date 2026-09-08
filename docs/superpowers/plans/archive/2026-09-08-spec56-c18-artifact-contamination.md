# SDD #56 C18 生产产物污染清洗 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 断新增（验证派发层捕获模式）→ 产物 lint 四 check → novel-output 存量 52 文件分层清洗与补账，清洗前后 lint 计数对照可复验。

**Architecture:** 新 lint `tools/lint_artifact_contamination.py`（纯函数检查 + 豁免清单 JSON + 退出码语义），挂 `just check`；清洗动作为一次性脚本与手改混合（oneoff 脚本落 run 记录目录 `docs/superpowers/audit-runs/2026-09-08-c18-cleanup/`）；不改 `src/shenbi/` 运行时行为（除删除空壳包）。

**Tech Stack:** Python 3.11+ / pathlib / pytest / just。全部验证走 `just`/`uv run`（CI 同构）。

## Global Constraints

- 禁真实 LLM dispatch / pipeline 子命令（F947 离线化；spec 核心原则 8）
- `src/shenbi/` 无 `print()`（ruff T20）；tools/ 脚本无此约束但保持 argparse + 退出码语义
- 修复不得发明新时间戳（F1163 裁决）；手算分数旧值留档 run 记录，不留 novel-output
- pathspec commit：显式列文件路径，禁 `git add -A`
- 环境同构：验证命令一律 `uv run` / `just`
- run 记录目录：`docs/superpowers/audit-runs/2026-09-08-c18-cleanup/`（README + 基线报告 + 旧值留档 + oneoff 脚本）

## File Structure

- Create: `tools/lint_artifact_contamination.py`（四 check + 豁免清单加载 + CLI）
- Create: `tools/artifact-lint-exemptions.json`（豁免清单：per-check 文件路径列表 + 理由）
- Create: `tests/unit/tools/test_lint_artifact_contamination.py`
- Create: `tests/unit/pipeline/test_dispatch_cli_argv.py`
- Create: `docs/superpowers/audit-runs/2026-09-08-c18-cleanup/`（README.md、baseline-report.json、recalc_resonance_deterministic.py、old-values-archive.md）
- Modify: `justfile`（check 面加一行 lint）
- Modify: `novel-output/xinghuo-ranqiong/**`（清洗）；`novel-output/README.md`（新增）
- Delete: `src/shenbi/skill_utils/review_resonance/`（空壳包）；`DEBUG_USE_MANUAL_CREATE.md`（移 run 记录）；2 个 0 字节 lockfile

---

### Task 1: 派发层验证（T1.1 argv 断言 + T1.2 增量核实）

**复杂度:** infra · **test_kind:** characterization（现状锁定）

**Files:**
- Create: `tests/unit/pipeline/test_dispatch_cli_argv.py`
- Modify: 无源码（纯验证性任务）

**Interfaces:**
- Consumes: `src/shenbi/pipeline/dispatch_helper.py::_find_ide_cli() -> list[str] | None`（L2394，循环 `["codex","zcode"]` 依 `shutil.which` 返回首个命中者，argv 含 `sandbox_permissions=workspace-write`）
- Produces: 无（下游 task 不依赖）；run 记录 `dispatch-verification.md` 由本 task 产出

- [ ] **Step 1: 写测试**（monkeypatch `shutil.which`，不 spawn 子进程）：

```python
"""SDD #56 C18 T1.1: dispatch CLI argv capture-mode verification (F947 offline)."""
import shutil
from unittest import mock

from shenbi.pipeline import dispatch_helper


def test_cli_argv_contains_capture_mode_no_meta_narration_codex():
    with mock.patch.object(shutil, "which", side_effect=lambda n: "/usr/bin/fake" if n == "codex" else None):
        argv = dispatch_helper._find_ide_cli()
    assert argv is not None and argv[0] == "codex"
    joined = " ".join(argv)
    assert "sandbox_permissions=workspace-write" in joined
    for pattern in ("手动复制", "只读沙箱", "无法写入", "请手动", "manually copy", "read-only sandbox", "cannot write"):
        assert pattern not in joined


def test_cli_argv_shared_for_zcode():
    # 现状锁定：zcode 分支返回同一份 codex 专属 argv（专属 flag 未测——spec T1.1 deviation）
    def fake_which(name: str):
        return None if name == "codex" else "/usr/bin/fake-zcode"
    with mock.patch.object(shutil, "which", side_effect=fake_which):
        argv_zcode = dispatch_helper._find_ide_cli()
    with mock.patch.object(shutil, "which", side_effect=lambda n: "/usr/bin/fake" if n == "codex" else None):
        argv_codex = dispatch_helper._find_ide_cli()
    assert argv_zcode is not None and argv_zcode[0] == "zcode"
    assert argv_zcode[1:] == argv_codex[1:]  # 共享 flag 面；zcode 专属适配记 deviation
```

- [ ] **Step 2:** `uv run pytest tests/unit/pipeline/test_dispatch_cli_argv.py -v` → 预期全 PASS（characterization：若 FAIL 说明现状与 spec 描述漂移 → 停，回阶段 1）
- [ ] **Step 3:** T1.2 增量核实（只读 grep）：`grep -rn "audit" src/shenbi/pipeline/ --include="*snapshot*" ; grep -rn "snapshots/" src/shenbi/pipeline/`（**空输出/无写入位点 = 通过**，grep exit 1 非失败）——确认现行代码无「快照写入时嵌埋审计全文」路径；结论写 run 记录 `dispatch-verification.md`（含 zcode deviation + 嵌埋核实结论 + 既有捕获产物 fixture 审查项——人工抽查 `### FILE:` 标记形态的既有 dispatch 产物样本 ≥1 例（既有 fixture 均出自 codex 形态 argv，zcode 独立产物例不可得——**记 deviation**，zcode 分支由 argv 断言测试覆盖），确认无元叙述注入；若发现现行嵌埋路径 → 停，回阶段 1）
- [ ] **Step 4:** 建 `docs/superpowers/audit-runs/2026-09-08-c18-cleanup/README.md`（run 记录索引）+ `dispatch-verification.md`
- [ ] **Step 5:** Commit `git add tests/unit/pipeline/test_dispatch_cli_argv.py docs/superpowers/audit-runs/2026-09-08-c18-cleanup/ && git commit -m "test: C18 T1 dispatch argv capture-mode verification + snapshot-embed audit (spec #56)"`

---

### Task 2: 产物 lint 四 check（tools/lint_artifact_contamination.py）

**复杂度:** infra · **test_kind:** tdd_red_green

**Files:**
- Create: `tools/lint_artifact_contamination.py`
- Create: `tools/artifact-lint-exemptions.json`
- Create: `tests/unit/tools/test_lint_artifact_contamination.py`

**Interfaces:**
- Produces（Task 3/6 依赖，签名固定）:
  - `META_NARRATION_PATTERNS: tuple[str, ...]`（7 模式）
  - `MANUAL_CALC_PATTERNS: tuple[str, ...]` = `("手动计算", "手算")`
  - `load_exemptions(repo_root: Path) -> dict[str, list[dict]]`（键 = check 名 `meta_narration|manual_calc|timestamp|state_reconcile`；条目 `{"path": "...", "reason": "..."}`）
  - `lint_tree(root: Path, *, exemptions: dict) -> list[Finding]`，`Finding = dict`（`check/path/line/detail`）
  - CLI：`uv run python tools/lint_artifact_contamination.py [--tree DIR] [--baseline-out FILE]`（省略 `--tree` 默认 novel-output，repo root 锚定 `__file__`），发现（豁免外）→ exit 1；`--baseline-out` 把全量 findings（含豁免标记）写 JSON
  - 四 check：(a) `meta_narration` 7 模式 grep 全文件类型；(b) `manual_calc`「手动计算|手算」与数字并存于同文件；(c) `timestamp`——同文件内 ISO 时间戳序列非单调（倒挂）+ 跨文件**同完整时间戳签名**（≥2 文件共享**同一完整 ISO 时间戳串**（日期+T+时刻）且时刻为整点零分零秒——完整串相等才算，仅小时相同/日期不同不算；豁免文件跳过）。真实树已知 ~15 组 ~65 文件（以基线实测组数为准）（全部 manual-era 编造族：framework 现行写 `datetime.now(UTC).isoformat()`，见 chapter_loop.py:2066）；(d) `state_reconcile`——`<tree>/pipeline-state.json` 的 `state["chapter_loop"]["chapter_states"][N]["audit_results"]["audit_reports"]`（list[相对路径]）vs 磁盘 `audits/chapter-N-*.md`，两分支：磁盘路径未入账 / 清单容器为空或键缺失（ch56 形态）
  - 豁免语义：文件路径在对应 check 的豁免清单 → 该 check 对该文件跳过；豁免不计入命中

- [ ] **Step 1: 写失败测试**（tmp_path 合成最小树——lint 逻辑单测非 skill 产物测试，G0.9 不适用；真实树冒烟在 Task 3 基线跑批）：覆盖 4 check 各正/负例 + 豁免跳过 + 退出码
- [ ] **Step 2:** `uv run pytest tests/unit/tools/test_lint_artifact_contamination.py -v` → FAIL（模块不存在）
- [ ] **Step 3:** 实现 lint（纯函数、pathlib、argparse；模式族常量与 spec 一字不差）
- [ ] **Step 4:** 同命令 → PASS
- [ ] **Step 5:** `uv run python tools/lint_artifact_contamination.py --tree novel-output`（豁免清单暂空）→ 预期 exit 1，命中报告与 spec 基线核对（meta_narration 52、manual_calc ≥2、state_reconcile 117、timestamp 15 组 ~65 文件）。timestamp 签名按完整串分组：预期 **~15 组 ~65 文件**（最大组 07-17T00:00:00Z×14、07-16T12:00:00Z×14、07-16T00:00:00Z×7；全部为 manual-era 编造族——framework 现行写真实时刻）。与实测组数不一致处记 deviation
- [ ] **Step 6:** Commit `git add tools/lint_artifact_contamination.py tools/artifact-lint-exemptions.json tests/unit/tools/test_lint_artifact_contamination.py && git commit -m "feat: C18 T2 artifact-contamination lint — 4 checks + exemption list (spec #56)"`

---

### Task 3: 全树基线报告（justfile 接线移 Task 7）

**复杂度:** leaf · **test_kind:** regression_guard

**Files:**
- Create: `docs/superpowers/audit-runs/2026-09-08-c18-cleanup/baseline-report.json`

- [ ] **Step 1:** 生成基线：`uv run python tools/lint_artifact_contamination.py --tree novel-output --baseline-out docs/superpowers/audit-runs/2026-09-08-c18-cleanup/baseline-report.json; echo "exit=$?"`（预期 exit=1——清洗未做，属基线态）。**justfile 接线不放本 task**：清洗完成（Task 6/7）前挂进 check 会全仓阻断；接线在 Task 7 Step 3，届时全树已 0 命中
- [ ] **Step 2:** 核对基线计数 vs spec（52/16/117 等）→ 数字与 spec 预期不一致处记 deviation
- [ ] **Step 3:** Commit `git add docs/superpowers/audit-runs/2026-09-08-c18-cleanup/baseline-report.json && git commit -m "chore: C18 T2 lint baseline report for novel-output (spec #56)"`

---

### Task 4: audits 层清洗 + ch49/ch51 确定性层重算（T3.5）

**复杂度:** infra · **test_kind:** characterization（重算脚本）+ 清洗动作

**Files:**
- Create: `docs/superpowers/audit-runs/2026-09-08-c18-cleanup/recalc_resonance_deterministic.py`（oneoff）
- Create: `docs/superpowers/audit-runs/2026-09-08-c18-cleanup/old-values-archive.md`
- Modify: `novel-output/xinghuo-ranqiong/audits/`（27 文件剥元叙述块；ch49/ch51 注记）

**Interfaces:**
- Consumes: `shenbi.skill_utils.calibration.confidence::calibrate_confidence`、`shenbi.pipeline.revision_router`（重算脚本 import 走 `uv run` 环境）

- [ ] **Step 1:** 写 oneoff 重算脚本（dry-run 默认 + `--apply`）：读 ch48-51 resonance 评分明细表 → 重算近3章均值 → 与 ch51 trend 行对照列差异 → apply 时以重算值覆盖 trend 行；ch49/ch51 的 calibration/分流声明行以 `calibrate_confidence`/`revision_router` 重算输出覆写；输出 old→new 对照表
- [ ] **Step 2:** `uv run python docs/superpowers/audit-runs/2026-09-08-c18-cleanup/recalc_resonance_deterministic.py novel-output/xinghuo-ranqiong`（dry-run）→ 对照表存 old-values-archive.md
- [ ] **Step 3:** `--apply` 执行；ch49/ch51 手算自证句替换为 provenance 注记（`> provenance: manual-era score retained; deterministic layer recalibrated 2026-09-08 (calibration/revision_router); dimension scores are LLM-judged, not offline-recomputable. ch50 helper-output citation unverifiable.`）
- [ ] **Step 4:** audits 27 文件剥元叙述块（块级识别：含 7 模式的引用块/段落；保留审计实质——逐文件脚本辅助 + 人工核对，改动清单进 run 记录）
- [ ] **Step 5:** 复验：`uv run python tools/lint_artifact_contamination.py --tree novel-output` → meta_narration 命中降为 snapshots+chapters+plans 层（audits 0）；manual_calc 0
- [ ] **Step 6:** Commit：`git add novel-output/xinghuo-ranqiong/audits/ docs/superpowers/audit-runs/2026-09-08-c18-cleanup/ && git commit -m "fix: C18 T3.5 audits-layer decontamination + ch49/51 deterministic recalc (spec #56)"`

---

### Task 5: snapshots/chapters/plans 清洗 + ch35 补账（T3.6/7）

**复杂度:** infra · **test_kind:** regression_guard（lint 计数）

**Files:**
- Modify: `novel-output/xinghuo-ranqiong/snapshots/`（18）、`chapters/*-decisions.json`（5）、`plans/*-decisions.json`（2）
- Create: `novel-output/xinghuo-ranqiong/chapters/chapter-35-decisions.json`（补 drafting-decisions，F1164）
- Delete: `src/shenbi/skill_utils/review_resonance/`（空壳包 + 其 `__init__.py` docstring 引用检查）

- [ ] **Step 1:** snapshots 18：剥离内嵌审计全文段（保留章正文与头部）；chapters/plans 7 个 json sidecar：定位含 7 模式的字段值剥元叙述子串（json 结构化编辑，保持 schema `shenbi-decisions-v1` 可过 G2——`uv run shenbi-validate G2 <file> decisions` 复验）
- [ ] **Step 2:** ch35 decisions 补生成：以 ch34/36 的 `chapter-N-decisions.json` 结构为模板、内容取自 ch35 正文与 revision-decisions（**不 dispatch**——标注 provenance `synthesized from chapter-35-revision-decisions during C18 cleanup`）
- [ ] **Step 3:** 删 `src/shenbi/skill_utils/review_resonance/`；手删 `tests/tiers/deps.json` 中该包的 stale `_tool_hashes` 条目并跑 `uv run bash tests/lock-tool-hashes.sh` 复验；`grep -rn "skill_utils.review_resonance\|skill_utils\.review_resonance\|skill_utils/review_resonance" src/ tests/ pyproject.toml` 清残留引用（点式亲测 0 命中；slash 形态有 `revision_router.py:64` 注释与 `chapter_loop.py` bare 引用，须同步清注释；**勿用裸 `review_resonance`**——`gates/g4/review_resonance.py` 是活的 G4 检查器，不得误删）
- [ ] **Step 4:** 复验 lint：`uv run python tools/lint_artifact_contamination.py --tree novel-output` → meta_narration 0 命中；timestamp check 仍命中（F1163 豁免清单尚未登记，属预期）；`uv run pytest tests/unit -q` 全绿
- [ ] **Step 5:** Commit：`git add novel-output/xinghuo-ranqiong/ src/shenbi/skill_utils/review_resonance tests/tiers/deps.json src/shenbi/pipeline/revision_router.py src/shenbi/pipeline/chapter_loop.py && git commit -m "fix: C18 T3.6/7 snapshots+sidecars decontamination, ch35 decisions backfill, drop review_resonance shell (spec #56)"`

---

### Task 6: F1163 全组豁免（~15 组 ~65 文件）+ F1165 回填 + F1166/68/74 补账（T3.8）

**复杂度:** infra · **test_kind:** regression_guard

**Files:**
- Create: `docs/superpowers/audit-runs/2026-09-08-c18-cleanup/backfill_audit_reports.py`、`docs/superpowers/audit-runs/2026-09-08-c18-cleanup/regen_truth_index.py`（oneoff）
- Modify: `tools/artifact-lint-exemptions.json`（timestamp check 登记 15 组全部 ~65 文件 + 组理由）
- Modify: `novel-output/xinghuo-ranqiong/` 内签名组 md 文件（provenance 注记；json 保留原值）
- Modify: `novel-output/xinghuo-ranqiong/pipeline-state.json`（117 项回填 + F1174 ch35 verdict 重试补账）
- Modify: `novel-output/xinghuo-ranqiong/gate-markers/`（F1166 marker 删除）、`truth-index.json`（F1168 重生成）

- [ ] **Step 1:** 15 组逐组裁决：以基线报告分组为准，每组核对文件类型与产物链（全部整点零分零秒 = manual-era 编造族）；md 文件在伪时间戳行旁加注记 `<!-- fabricated manual-era timestamp, true time unrecoverable (C18 F1163 adjudication) -->`；全部 ~65 文件登记豁免清单（以基线报告实测分组为准，~15 组；reason: `F1163 manual-era fabricated batch timestamp <完整串>, true time unrecoverable`）
- [ ] **Step 2:** F1165 回填脚本（oneoff，落 run 记录）：扫磁盘 `audits/chapter-N-*.md` → 缺失路径补入对应 `chapter_states[N]["audit_results"]["audit_reports"]`（resonance 55 + review-summary 55 + ch56 7）；回填后 lint(d) 0 命中（不豁免）
- [ ] **Step 3:** F1166 删除 `gate-markers/G4-review-resonance-generative.json`（07-19 验证运行污染 marker）；F1168 truth-index 重生成脚本（从 truth/ 13 文件机械登记；oneoff 落 run 记录）；F1174 在 `retry_feedback` 补 ch35 条目（来源 DEBUG 文档 L82/124 事实，注记 `backfilled from DEBUG_USE_MANUAL_CREATE.md during C18 cleanup`）
- [ ] **Step 4:** 复验：`uv run python tools/lint_artifact_contamination.py --tree novel-output` → **exit 0，四 check 全 0 命中**；整点零分零秒完整串重复组命中文件数 == 豁免清单登记数（初始 ~65/~15 组，快照剥离收缩后同步）
- [ ] **Step 5:** Commit：`git add tools/artifact-lint-exemptions.json novel-output/xinghuo-ranqiong/ docs/superpowers/audit-runs/2026-09-08-c18-cleanup/ && git commit -m "fix: C18 T3.8 F1163 exemption adjudication + F1165 117-item backfill + F1166/68/74 remediation (spec #56)"`

---

### Task 7: 孤儿类收尾（T3.9/10）+ just check 接线

**复杂度:** leaf · **test_kind:** regression_guard

**Files:**
- Delete/Move: `novel-output/xinghuo-ranqiong/DEBUG_USE_MANUAL_CREATE.md` → run 记录目录
- Modify: `novel-output/validation-results/validation-report.md`（头注）、`novel-output/xinghuo-ranqiong/genre-config.json`（texture=false + rule-001 修订）、`novel-output/README.md`（新增）
- Delete: 2 个 0 字节 lockfile
- Modify: `justfile`（check 面加 lint 行）

- [ ] **Step 1:** DEBUG 文档 `git mv` 至 run 记录；validation-report.md 头注 `> historical manual-run record (pre-#56), superseded — see audits/2026-09-08-c18-cleanup/`；genre-config `auditDimensions.texture: false` + customRules 数组移除 rule-001 条目；novel-output/README.md 三树用途声明；`f=$(ls .hypothesis/patches 2>/dev/null | head -1); [ -n "$f" ] && git check-ignore .hypothesis/patches/$f` 确认命中（目录空则记 deviation——F1169 出范围证据入 run 记录）
- [ ] **Step 2:** 删 2 lockfile；`find novel-output -name "*.lockfile" -size 0 | wc -l` → 0
- [ ] **Step 3:** justfile check 加 `uv run python tools/lint_artifact_contamination.py`（此时全树已 0 命中，接线即绿）
- [ ] **Step 4:** `just check` 全绿（lint 行生效）
- [ ] **Step 5:** Commit：`git add novel-output/ docs/superpowers/audit-runs/2026-09-08-c18-cleanup/DEBUG_USE_MANUAL_CREATE.md justfile && git commit -m "chore: C18 T3.9/10 orphan remediation + artifact lint wired into just check (spec #56)"`

---

### Task 8: findings-ledger 回写 + 验收全集复验

**复杂度:** leaf · **test_kind:** regression_guard

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（C18 17 条 specced→merged）

- [ ] **Step 1:** ledger 17 条（F1108/F1117-F1119/F1162-F1174）状态回写 merged + PR 号（`just audit-lint` 过）
- [ ] **Step 2:** 验收 1-4 全集复验（命令 + 输出粘贴 `.superpowers/sdd/progress.md` `## 验收证据` 段——执行协议工件，不入 git）：
  - AC1: lint 全树 exit 0 + 0 命中；基线对照 baseline-report.json
  - AC2: `uv run pytest tests/unit/pipeline/test_dispatch_cli_argv.py -v` 绿 + run 记录 dispatch-verification.md
  - AC3: `uv run python docs/superpowers/audit-runs/2026-09-08-c18-cleanup/recalc_resonance_deterministic.py novel-output/xinghuo-ranqiong`（复跑 dry-run → 0 差异 = 幂等重算闭环）+ old-values-archive.md 在库
  - AC4: `git check-ignore` 命中；`find novel-output -name "*.lockfile" -size 0` 空；整点签名组文件数 == 豁免清单登记数（动态相等）
- [ ] **Step 3:** `just check` 复跑全绿
- [ ] **Step 4:** Commit：`git add docs/superpowers/audit-runs/2026-08-15/findings-ledger.md && git commit -m "docs: C18 findings-ledger 17 findings merged (spec #56)"`

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1 lint 前后对照 | T3 基线 + T8 复验 | lint CLI exit code + baseline-report.json |
| 2 派发层验证 | T1 | pytest argv 断言 + dispatch-verification.md |
| 3 确定性层重算 | T4 + T8 | recalc 脚本幂等复跑 + old-values-archive |
| 4 F1169/70/63 复验 | T6/T7/T8 | check-ignore / find -size 0 / grep 计数==豁免数 |
