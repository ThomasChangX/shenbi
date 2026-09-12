# C23 文档机械漂移批量修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清零 spec #61（C23）33 条活成员的文档机械漂移：断链、计数残留、行号锚点、过期 docstring、冗余 .gitkeep，并以 doc-links CI 为机械验收。

**Architecture:** 纯文档/docstring/归档区机械修复，零生产逻辑改动。src/shenbi docstring 改动必须同步重锁 G0.13 哈希（tests/lock-tool-hashes.sh）。归档区改动收敛为单个可 revert 的 codemod commit。

**Tech Stack:** grep/python3 codemod/pytest（tests/integration/test_doc_links.py 承载断链防线）/just

**Spec:** `docs/superpowers/specs/2026-08-16-audit-docs-mechanical-drift-fix.md`（2026-09-13 收敛版，活成员 33）

## Global Constraints

- 全程禁真实 LLM dispatch（`shenbi-dispatch`/`pipeline`）——验收全部离线可复验（F947）
- 凡 commit 触及 `src/shenbi/**/*.py`：commit 前 `bash tests/lock-tool-hashes.sh` 重锁 deps.json（G0.13）
- commit 一律 pathspec 显式列文件，禁 `git add -A`
- Conventional Commits；本机全套件命令统一 `PATH="/tmp/shim-bin2:/usr/bin:/bin:/usr/sbin:/sbin"`（规避 PATH 中 codex/zcode 触发真实 dispatch 的本机 deviation）
- 测试层级：全部 T1/characterization（grep 断言 + doc_links 回归），无新生产逻辑

## 验收覆盖表（spec 验收 → task → 命令）

| spec 验收 | task | 命令 |
|---|---|---|
| 1. doc-links 0 断链 | T5 | `uv run pytest tests/integration/test_doc_links.py -q`（550 项）|
| 2. 入口断链/计数 grep 0 命中 | T1/T5 | `grep -rn "dispatch-subagent" command-to-give.md AGENTS.md README.md`；`grep -c "validate-gate" command-to-give.md`==0；`git grep -n "69 total\|67 functional" -- AGENTS.md README.md docs/framework/` |
| 3. 锚点抽查符号可解析 | T2/T5 | `grep -n make_composite_checker src/shenbi/gates/g4/decisions_validator.py` 唯一命中；hooks.py 锚点指向 :162 实况 |
| 4. just check 全绿 + F968 红转绿 | T5 | `just check`；codemod 自带校验输出 |

---

### Task 1: command-to-give.md 入口文档清零（F901/F461/F1034/F952/F951/F906/F953）

**Files:**
- Modify: `command-to-give.md:1,24,26-27,48,85`

**Interfaces:** 无代码接口。产出：入口文档零死链零硬计数。

- [ ] **Step 1: 修 :1 归档 plan 引用（F951）**

```diff
- 在 /Users/xiaotiac/Documents/GitHub/shenbi 根目录，按 docs/superpowers/plans/2026-06-11-test-framework.md 执行测试轮次。
+ 在 /Users/xiaotiac/Documents/GitHub/shenbi 根目录，按 docs/superpowers/plans/archive/2026-06-11-test-framework.md 执行测试轮次。
```

- [ ] **Step 2: 修 :24 已删工具名（F952）**

```diff
- **注意**：修改 validate-gate.py / scoring.py / phase-runner.py 后，必须运行 `bash tests/lock-tool-hashes.sh` 更新 `deps.json` 中的 SHA256 锁定值，否则 G0.13 阻断。
+ **注意**：修改 `src/shenbi/gates/` 下任何 gate 模块 / scoring.py / phase-runner.py 后，必须运行 `bash tests/lock-tool-hashes.sh` 更新 `deps.json` 中的 SHA256 锁定值，否则 G0.13 阻断。
```

- [ ] **Step 3: 修 :48 已删脚本（F901/F461/F1034）**

```diff
- 6. **只在 G2 和 G4 都通过后**，新开独立 subagent 评分（使用 `bash tests/dispatch-subagent.sh <skill> generative <round_dir> "<prompt>"`）。**Dispatcher 不得评分。**
+ 6. **只在 G2 和 G4 都通过后**，新开独立 subagent 评分（使用 `shenbi-dispatch <skill> generative <round_dir> "<prompt>"`）。**Dispatcher 不得评分。**
```

- [ ] **Step 4: 修 :85 计数（F906/F1033 残留）**

```diff
- **全部 59 个 skill 的 generative、bug-hunt、clean 均 ≥ 94 → 开始 T2。**
+ **全部 skill（以 `tools/lint_registry_reconcile.py` 对账口径为准）的 generative、bug-hunt、clean 均 ≥ 94 → 开始 T2。**
```

- [ ] **Step 5: 修 :26-27 空节（F953）**——`### 第二步：确认进度` 节补最小内容（或并入第一步尾部）：

```markdown
### 第二步：确认进度

检查 `tests/rounds/` 既有轮次目录与 `.superpowers/sdd/progress.md`（如存在），确定本轮起点；无进行中轮次则从新 round 目录开始。
```

- [ ] **Step 6: 修 AGENTS.md:16 结构树（F917）**

```diff
- │   ├── rounds/             # Active + archived rounds
+ （删除该行——tests/rounds 已不存在；结构树与磁盘对齐）
```

- [ ] **Step 7: 验证 grep 归零**

```bash
grep -rn "dispatch-subagent" command-to-give.md AGENTS.md README.md   # 期望 0
grep -c "validate-gate" command-to-give.md                             # 期望 0
```

- [ ] **Step 8: Commit**

```bash
git add command-to-give.md AGENTS.md
git commit -m "docs: command-to-give dead-link/count/empty-section + AGENTS tree fixes (F901/F461/F1034/F952/F951/F906/F953/F917, spec #61 T1)"
```

### Task 2: src docstring/注释清零 + G0.13 重锁（F236/F714/F117/F127/D103/F334/F335/F126/F612/F428/F429/F440/F426/hooks.py 锚点 + gates.md F423 + F909）

**Files:**
- Modify: `src/shenbi/contracts/registry.py:62`、`tests/unit/test_logging.py:6`、`src/shenbi/__init__.py:3-10`、`src/shenbi/pipeline/chapter_loop.py:18-24`、`src/shenbi/pipeline/dispatch_helper.py:111`、`src/shenbi/pipeline/llm_output_integrity.py:54`、`src/shenbi/scoring.py:392`、`src/shenbi/skill_utils/revision_routing/preserve_check.py:16-19`、`src/shenbi/gates/g2.py:242`、`src/shenbi/gates/g6.py:526`、`src/shenbi/gates/g0.py:711`、`src/shenbi/gates/g4/chapter_revision.py:8`、`src/shenbi/contracts/schemas/hooks.py:6,31`、`docs/framework/gates.md:3`、`docs/basedpyright-overrides.md`
- Regenerate: `tests/tiers/deps.json`（lock-tool-hashes.sh）

**Interfaces:** 无签名变更（仅注释/docstring 文本）。

- [ ] **Step 1: 逐条修改（协调者亲自，infra）**

| # | 位置 | 旧 → 新 |
|---|---|---|
| F236 | registry.py:62 | `contract.py 仍负责` → `contracts/ 包仍负责`（删已亡模块名） |
| F714 | test_logging.py:6 | `tests/logging.py` → `src/shenbi/logging.py` |
| F117 | __init__.py:8-9 | 删 `(forwarder until PR-19)` / `(forwarder until PR-20)` 两处括注 |
| F127 | __init__.py:3-10 | 子模块清单改为 `See docs/framework/overview.md 与包内各模块 docstring（模块数随演进变化，不在此枚举）` |
| D103 | chapter_loop.py:18-24 | 删 W3T4/W3T5 迁移 TODO 措辞（保留模块功能描述） |
| F334 | dispatch_helper.py:111 | `base = 300s (5 min)` → `base = 900s（见 _compute_dispatch_timeout 实值）` |
| F335 | src/shenbi/pipeline/llm_output_integrity.py:54 | `real audits are > 500 bytes` → `real audits exceed _AUDIT_MIN_BYTES` |
| F126 | scoring.py:391-392 | usage 串首 `scoring.py` → `shenbi-score`（其余参数文案保留；以实际行文本为准） |
| F612 | preserve_check.py:16-19 | 删除不存在的 `python -m` CLI usage 块（该模块无入口） |
| F428 | g2.py:242 | `chapter files only` → `all file types`（与实际行为一致；G7.5 重复注记一并删） |
| F429 | g6.py:526 | `round INCOMPLETE` → `non-blocking skip`（SKIP 语义） |
| F440 | g0.py:711 | `20 skills` → `G4_CHECKER_SKILLS 条目数（以 G4_CHECKER_SKILLS 为准）` |
| F426 | chapter_revision.py:8 | `decisions_validator.py:87` → `decisions_validator.py::make_composite_checker`（符号引用） |
| hooks 锚 | hooks.py:6,31 | `SKILL.md:87` → `SKILL.md 的 status 表（shenbi-foreshadowing-lifecycle）`，或直接引 :162 实况并注明快照日期 |
| F423 | gates.md:3 | `8 validation gates` → `11 validation gates`（G0-G7 + G_TRANSITION/G_DISPATCH/G_RECONCILE，与 gates/cli.py 一致） |
| F909 | basedpyright-overrides.md | 三处失实声明改写对齐 pyproject 实值（reportMissingTypeStubs 等为 "none"；删 skill_utils executionEnvironment 声明；mypy 镜像段核对后改写） |

- [ ] **Step 2: G0.13 重锁**

```bash
bash tests/lock-tool-hashes.sh
git diff --stat tests/tiers/deps.json   # 期望仅哈希变更
```

- [ ] **Step 3: 锚点符号可解析验证（spec 验收 3）**

```bash
grep -n "def make_composite_checker" src/shenbi/gates/g4/decisions_validator.py   # 唯一命中
```

- [ ] **Step 4: 回归**

```bash
PATH="/tmp/shim-bin2:/usr/bin:/bin:/usr/sbin:/sbin" uv run pytest tests/unit -q -m "not last" --no-cov -x -q 2>&1 | tail -3
```

- [ ] **Step 5: Commit（pathspec 显式列全部触及文件 + deps.json）**

```bash
git add <上表全部文件> tests/tiers/deps.json
git commit -m "docs: src docstring/comment drift batch + G0.13 relock (D103/F117/F126/F127/F236/F334/F335/F426/F428/F429/F440/F612/F714/hooks-anchors/F423/F909, spec #61 T3)"
```

### Task 3: 归档区 codemod——spec 路径可达性 + coverage-ledger 锚点（F968/F955/F331/T1001/F970/F971）

**Files:**
- Modify: `docs/superpowers/plans/archive/*.md`（32 条 spec 前归档路径）、`docs/superpowers/specs/archive/2026-08-13-full-project-audit-prompt-design.md:226`、`docs/superpowers/audit-runs/2026-08-14/coverage-ledger.md`、`docs/superpowers/audit-runs/2026-08-14/final-report.md:15`

- [ ] **Step 1: codemod 归档 plan 的 spec 引用**

```bash
uv run python - <<'EOF'
import re, pathlib
root = pathlib.Path("docs/superpowers/plans/archive")
fixed = []
for f in root.glob("*.md"):
    t = f.read_text()
    def repl(m):
        p = pathlib.Path("docs/superpowers/specs") / pathlib.Path(m.group(0)).name
        return f"docs/superpowers/specs/archive/{m.group(0).split('/')[-1]}" if p.exists() else m.group(0)
    # 仅改「指向已不在 specs/ 顶层、但 basename 存在于 specs/archive/ 的引用」
    new = t
    for m in set(re.findall(r"docs/superpowers/specs/[\w-]+\.md", t)):
        if not pathlib.Path(m).exists():
            cand = pathlib.Path("docs/superpowers/specs/archive") / pathlib.Path(m).name
            if cand.exists():
                new = new.replace(m, str(cand))
                fixed.append((f.name, m))
    if new != t:
        f.write_text(new)
for x in fixed: print(x)
print(f"total: {len(fixed)}")
EOF
```
期望 total ≥ 32（F968 记载 32 条；实际以跑出数为准记入验收证据）。

- [ ] **Step 2b: F331 核实后处置**——F331 载体（2026-08-14 轮活跃 spec 的 file:line 引用）已随该轮 specs 归档：按 spec「归档 spec 只在可达性上修，不逐行追号」豁免逐行追号，记 deviation；若 Step 1 codemod 碰巧触及含漂移行号的归档文件则顺带改符号引用，否则不单独开步骤

- [ ] **Step 2c: F955 归档 spec 预写目录路径**——`archive/2026-08-13-full-project-audit-prompt-design.md:226` 的 `audit-runs/2026-08-13/` → `audit-runs/2026-08-14/`（实际产出目录）。

- [ ] **Step 3: F970 coverage-ledger 死锚**——`zone-reports/Z7.md#…`/`Z8.md#…` → 实际分片文件（Z7-a~d/Z8-a~c，按 heading 内容定位）。F971：`final-report.md:15` 的 `85.16%` 改注 `87.28%（coverage.xml line-rate，2026-08-14 快照）`。

- [ ] **Step 4: doc-links 回归**

```bash
PATH="/tmp/shim-bin2:/usr/bin:/bin:/usr/sbin:/sbin" uv run pytest tests/integration/test_doc_links.py -q --no-cov 2>&1 | tail -2   # 全 pass
```

- [ ] **Step 5: Commit（单批可 revert）**

```bash
git add docs/superpowers/plans/archive docs/superpowers/specs/archive/2026-08-13-full-project-audit-prompt-design.md docs/superpowers/audit-runs/2026-08-14/coverage-ledger.md docs/superpowers/audit-runs/2026-08-14/final-report.md
git commit -m "docs: archived-area codemod — spec path resolvability + coverage-ledger anchors (F968/F955/F331/T1001/F970/F971, spec #61)"
```

### Task 4: 冗余 .gitkeep 清理（F804/F854）

**Files:** 非空目录中的 `.gitkeep`（全仓 ~47 处中属冗余者；空目录保留）

- [ ] **Step 1: 识别非空目录中的 .gitkeep**

```bash
for f in $(git ls-files | grep '\.gitkeep$'); do d=$(dirname "$f"); [ -n "$(git ls-files "$d" | grep -v '\.gitkeep$' | head -1)" ] && echo "$f"; done
```

- [ ] **Step 2: 确认无消费方**——`grep -rn "\.gitkeep" src/ tools/ justfile .github/` 中既有消费者（g0.py 等）均为排除性引用（设计审查已核：g0.py:155,176 等显式 exclude），删除为 no-op。若发现非排除性引用 → 停，记 deviation。

- [ ] **Step 3: 删除 + 验证**

```bash
git rm <上步清单>
PATH="/tmp/shim-bin2:/usr/bin:/bin:/usr/sbin:/sbin" uv run pytest tests/unit/gates -q --no-cov 2>&1 | tail -2
```

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove redundant .gitkeep in populated dirs (F804/F854, spec #61)"
```

### Task 5: 验收 sweep + 全量回归（spec 验收 1-4）

**Files:** 无新改动（验证 task）

- [ ] **Step 1: 验收命令逐条实跑**（spec 验收覆盖表全四条），输出粘贴 progress.md `## 验收证据`。

- [ ] **Step 2: `just check` 全绿**

```bash
PATH="/tmp/shim-bin2:/usr/bin:/bin:/usr/sbin:/sbin" just check 2>&1 | tail -5   # EXIT=0
```

- [ ] **Step 3: F974 豁免注记**——spec-deviations 记「归档 plan 复选框不回填（已裁决豁免）」。

- [ ] **Step 4: Commit（如有 ledger 回写等收尾文件）**

```bash
git commit -m "test: acceptance sweep green — C23 mechanical drift zeroed (spec #61)"
```
