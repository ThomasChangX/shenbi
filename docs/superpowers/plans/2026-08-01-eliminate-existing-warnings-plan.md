# 消除项目既有 test error 与 warning 根因 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 PR #23 postmortem 承诺但从未实施的清理全部落地——消 21 pip-audit 漏洞、装 3 个本地拦截守卫、negative test 证明守卫工作、清 94 条 CodeQL 告警。

**Architecture:** 四个独立 PR（Phase 1-4），按 spec §7 路线图。Phase 3 Task 3.0 须排在 Phase 1 前（时序约束，依赖 docs 组含漏洞包）。守卫机制：pre-push-check.sh 锁 `--group dev` + mkdocs 链接检查；pre-commit 新增 fixture-mirror-sync hook（从 g0.py 模块级常量单一源读取）。

**Tech Stack:** bash（pre-push/pre-commit hooks）、Python 3.11+（check_fixture_mirror.py、g0.py）、uv（依赖组管理）、mkdocs（文档构建）、CodeQL（告警清理）、Dependabot（漏洞修复）。

**Spec:** `docs/superpowers/specs/2026-08-01-pr23-debugging-postmortem-design.md`（阶段 2 audit_loop 5 轮收敛，设计已批准）

## Global Constraints

- AGENTS.md：Conventional Commits（`feat:`/`fix:`/`test:`/`docs:`/`chore:`）
- AGENTS.md：framework 代码无 `print()`，用 structlog；gate checkers idempotent（pure validation，no side effects on output files）
- AGENTS.md：commit/push 只在用户要求时；在默认分支先切分支（本 plan 在 `spec/eliminate-existing-warnings` 分支执行）
- spec §9：只做"消除 warning + 装守卫"；不重构 skill 契约、不动业务逻辑、不改 CodeQL 扫描配置、不处理 libcairo
- spec 铁律 5：既有技术债集中在独立 chore PR（Phase 4），不分散夹带进 feature PR
- spec 铁律 6：守卫装完必须 negative test 证明它能拦
- spec 铁律 7：mirror_map 单一源（g0.py 模块级常量，gate 与守卫同源读取）
- `just check` 基线 = 2787 passed，每个 Task 后须保持

## AC 覆盖表（每 spec §6 判据 → task → test）

| spec §6 AC | 目标值 | 实施Task | 验证Task/方式 |
|-----------|--------|---------|--------------|
| CodeQL open alerts | 0 | T9-T12（Phase 4 四批） | `gh api ... \| jq length` |
| pip-audit 漏洞 | 0（或注明 pymdown 回退） | T7（Phase 1 合 Dependabot） | `uv run pip-audit` |
| pre-push 审计基准 = CI | `--group dev` 锁定 | T3（Task 2.1） | T8（Task 3.0 negative test，须在 T7 前） |
| fixture 漂移本地拦截 | pre-commit 触发 | T4-T5（Task 2.2/2.3） | T8（Task 3.1 negative test） |
| mkdocs 死链本地拦截 | docs 变更触发 | T6（Task 2.4） | T8（Task 3.2 negative test） |
| `just check` | 2787 passed 保持 | 每 Task | 每 Task 后 `just check` |
| mkdocs build 死链基线 | 0（libcairo 除外） | —（现状已 0） | `mkdocs build --strict 2>&1 \| grep 'contains a link'` |

---

## Phase 2 · 装本地拦截守卫（先于 Phase 1，因 Task 3.0 时序约束）

> **执行顺序说明**：spec §7 原列 Phase 1→2→3→4，但 spec Task 3.0 时序约束（R4 I1 纠正）要求 Task 3.0 须在 Phase 1 合 Dependabot 之前执行（否则 docs 组漏洞已修，negative test 空洞化）。故本 plan 把 Phase 2 守卫安装 + Phase 3 negative test（含 Task 3.0）排在 Phase 1 之前。Phase 1（合 Dependabot）放最后。

### Task 1: pre-push pip-audit 锁 dev 组（spec Task 2.1，缺口 B / Issue 2 根治）

**复杂度: leaf**
**test_kind: regression_guard**（守 Issue 2 复发；negative test 在 Task 8 Task 3.0）

**Files:**
- Modify: `tools/pre-push-check.sh:37-38`
- Test: 无自动化测试文件（守卫是 bash 脚本；验证靠 Task 8 negative test + `bash -n` 语法检查）

**Interfaces:**
- Consumes: 无
- Produces: pre-push-check.sh 的 pip-audit 块改为 `uv sync --frozen --group dev` 后再 audit

**当前代码**（`tools/pre-push-check.sh:37-38`，已核实）：
```bash
echo "--- pip-audit ---"
uv run pip-audit
```

- [ ] **Step 1: 改 pip-audit 块**

```bash
# 改 tools/pre-push-check.sh L37-38 为：
echo "--- pip-audit (dev group, mirroring CI security.yml) ---"
uv sync --frozen --group dev >/dev/null
uv run pip-audit
```

- [ ] **Step 2: 语法检查**

Run: `bash -n tools/pre-push-check.sh`
Expected: 无输出（exit 0）

- [ ] **Step 3: 跑 just check 保持基线**

Run: `just check`
Expected: 2787 passed + 4 last-marked passed，85.03% coverage

- [ ] **Step 4: Commit**

```bash
git add tools/pre-push-check.sh
git commit -m "fix(pre-push): lock pip-audit to --group dev (Issue 2 根治)

CI security.yml 用 uv sync --frozen --group dev 后 audit；pre-push
裸跑 pip-audit 审 venv 现状，本地装过 docs 组就脏。显式 sync dev
组对齐 CI 基准，本地绿 = CI 绿。spec §4 Task 2.1 / 缺口 B。"
```

---

### Task 2: 新建 check_fixture_mirror.py + 注册 pre-commit hook（spec Task 2.2，缺口 C / Issue 7 根治）

**复杂度: leaf**（新脚本 + hook 注册；g0.py 改动在 Task 3）
**test_kind: regression_guard**（守 Issue 7 复发；negative test 在 Task 8 Task 3.1）

> **执行顺序（审查 I2 纠正）**：先做 **Task 3**（g0.py 提 MIRROR_MAP 到模块级），**再做本 Task 2**（脚本 import MIRROR_MAP + 注册 hook）。这样 import 立即解析，无 ImportError 红窗（违反 Global Constraint "每 Task 后 just check 基线"）。两 Task 紧耦合一并 commit（Task 3 Step 6 的 commit 含两者）。

**Files:**
- Create: `tools/check_fixture_mirror.py`
- Modify: `.pre-commit-config.yaml`（在 contract-sync-idempotency hook 后加新 hook）

**Interfaces:**
- Consumes: `shenbi.gates.g0.MIRROR_MAP`（Task 3 提到模块级后；此 Task 的脚本 import 它）
- Produces: `tools/check_fixture_mirror.py` 的 `main() -> int`（无参数，读 MIRROR_MAP，漂移返回 1）

> **注意**：此 Task 的脚本 `from shenbi.gates.g0 import MIRROR_MAP`。**执行顺序：先 Task 3（g0.py 提常量）→ 再本 Task 2**（脚本 + hook 注册）。这样 import 立即解析，无 ImportError 红窗。两 Task 一并 commit（Task 3 Step 6）。

- [ ] **Step 1: 写 check_fixture_mirror.py**

```python
#!/usr/bin/env python3
"""Pre-commit guard: fixture mirrors must match source hashes (G0.11 本地版).

单源读取 shenbi.gates.g0.MIRROR_MAP（spec Task 2.3），避免与 gate 两处定义漂移。
"""
import hashlib
import sys
from pathlib import Path

from shenbi.gates.g0 import MIRROR_MAP  # Task 2.3 提模块级后生效

ROOT = Path(__file__).resolve().parent.parent


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    drift: list[tuple[str, str]] = []
    for fixture_rel, source_rel in MIRROR_MAP.items():
        fp, sp = ROOT / fixture_rel, ROOT / source_rel
        if not sp.exists():
            # 源不存在不报（可能未创建），但记日志供 debug
            print(f"fixture mirror: source {source_rel} absent, skip", file=sys.stderr)
            continue
        if not fp.exists() or _sha256(fp) != _sha256(sp):
            drift.append((fixture_rel, source_rel))
    if drift:
        for f, s in drift:
            print(
                f"fixture mirror drift: {f} != {s}\n  fix: cp {s} {f}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 注册 pre-commit hook**

在 `.pre-commit-config.yaml` 的 `contract-sync-idempotency` hook 块后（L78 `pass_filenames: false` 后），加：

```yaml
      - id: fixture-mirror-sync
        name: fixture mirror integrity (G0.11 local)
        entry: uv run python tools/check_fixture_mirror.py
        language: system
        pass_filenames: false
```

- [ ] **Step 3: 跑 just check（Task 3 已先完成，MIRROR_MAP 就位，hook 应工作）**

Run: `just check`
Expected: 2787 passed + 4 last-marked passed（import 解析，fixture 当前一致）

- [ ] **Step 4: 暂不单独 commit（与 Task 3 一起 commit，因两者紧耦合）**

---

### Task 3: g0.py mirror_map 提模块级常量（spec Task 2.3，单一源去重）

**复杂度: infra**（触及 gate 源码 `src/shenbi/gates/g0.py`，跨 Task 影响 G0.11 + 守卫，协调者亲实现）
**test_kind: characterization**（行为保持重构——mirror_map 从函数内移到模块级，G0.11 行为不变）

**Files:**
- Modify: `src/shenbi/gates/g0.py`（mirror_map 从 gate_G0() 函数内 L474-476 移到模块级；原位置改 import 引用）

**Interfaces:**
- Consumes: 无
- Produces: `shenbi.gates.g0.MIRROR_MAP`（模块级 dict，Task 2 的脚本 import 它）

**当前代码**（`src/shenbi/gates/g0.py:474-476`，已核实）：
```python
    mirror_map = {
        "tests/fixtures/outline-example.md": "outline-example.md",
    }
```

- [ ] **Step 1: 提 MIRROR_MAP 到模块级**

在 `src/shenbi/gates/g0.py` 模块级（其他模块级常量附近，如 `log = ...` 附近）加：

```python
# G0.11 fixture mirror map — single source of truth (spec Task 2.3 铁律 7).
# tools/check_fixture_mirror.py 与 gate_G0() 都读此常量，避免两处漂移。
MIRROR_MAP: dict[str, str] = {
    "tests/fixtures/outline-example.md": "outline-example.md",
}
```

- [ ] **Step 2: gate_G0() 函数内改用 MIRROR_MAP**

把 L474-476 的函数内 `mirror_map = {...}` 删除，函数内引用处（L478 `for fixture_rel, source_rel in mirror_map.items()`）改为 `MIRROR_MAP.items()`。

- [ ] **Step 3: 跑 G0 相关测试**

Run: `uv run pytest tests/unit/gates/ -k "g0 or G0" -v`
Expected: 全绿（G0.11 行为不变）

- [ ] **Step 4: 跑 pre-commit fixture-mirror-sync hook（此时 MIRROR_MAP 已就位，Task 2 的脚本应工作）**

Run: `uv run pre-commit run fixture-mirror-sync --all-files`
Expected: PASS（fixture 与源当前一致，spec §3.1 核实）

- [ ] **Step 5: 跑 just check 保持基线**

Run: `just check`
Expected: 2787 passed + 4 last-marked passed

- [ ] **Step 6: Commit（Task 2 + Task 3 一起，紧耦合）**

```bash
git add tools/check_fixture_mirror.py .pre-commit-config.yaml src/shenbi/gates/g0.py
git commit -m "feat(guards): add fixture-mirror pre-commit hook + single-source MIRROR_MAP

- 新建 tools/check_fixture_mirror.py：G0.11 本地版，漂移时提示 cp 命令
- g0.py mirror_map 提模块级 MIRROR_MAP，gate 与 hook 同源读取（铁律 7）
- 注册 fixture-mirror-sync pre-commit hook
spec §4 Task 2.2/2.3 / 缺口 C / Issue 7 根治。"
```

---

### Task 4: pre-push mkdocs 链接本地拦截（spec Task 2.4，缺口 A / Issue 1 防复发）

**复杂度: leaf**
**test_kind: regression_guard**（守 Issue 1 复发；negative test 在 Task 8 Task 3.2）

**Files:**
- Modify: `tools/pre-push-check.sh`（pip-audit 块后加 mkdocs docs 变更条件块）

**Interfaces:**
- Consumes: 无
- Produces: pre-push-check.sh 的 mkdocs docs 变更检查块

- [ ] **Step 1: 加 mkdocs docs 检查块**

在 `tools/pre-push-check.sh` 的 pip-audit 块（Task 1 改后）后，加（spec §4 Task 2.4 经 R1-R5 审查收敛的最终版）：

```bash
# 4c. mkdocs link check (only when docs change)
# 触发：检测待 push 的 docs 变更。pre-push 阶段已 commit，--cached 和 HEAD diff 都恒空，
#   正确 idiom 是 main...HEAD（推送范围）。
if git diff --name-only main...HEAD 2>/dev/null | grep -qE '^(docs/|mkdocs\.yml)'; then
  echo "--- mkdocs link check (docs changed) ---"
  uv sync --group docs >/dev/null
  # 单次 build 捕获输出与 exit code
  if ! out="$(uv run mkdocs build --strict 2>&1)"; then
    # (a) 死链 → 必失败
    if echo "$out" | grep -q 'contains a link'; then
      echo "$out" | grep 'contains a link'; exit 1
    fi
    # 判 libcairo-only：剥离 libcairo 归因行后若仍有 WARNING/ERROR 则真失败
    # set -euo pipefail 下 grep -vE 空匹配 exit 1 会 abort，故 || true
    non_cairo_problems="$(echo "$out" | grep -E '^(WARNING|ERROR)' \
      | grep -vE 'cairosvg|no library called.*cairo|cairo-2|libcairo' || true)"
    if [ -z "$non_cairo_problems" ]; then
      echo "--- mkdocs: libcairo-only warnings tolerated (§9 out-of-scope) ---"
    else
      echo "$non_cairo_problems"; exit 1
    fi
  fi
fi
```

- [ ] **Step 2: 语法检查**

Run: `bash -n tools/pre-push-check.sh`
Expected: 无输出（exit 0）

- [ ] **Step 3: 跑 just check 保持基线**

Run: `just check`
Expected: 2787 passed + 4 last-marked passed

- [ ] **Step 4: Commit**

```bash
git add tools/pre-push-check.sh
git commit -m "feat(pre-push): add mkdocs link check on docs change (Issue 1 防复发)

仅 docs/ 或 mkdocs.yml 变更时触发 mkdocs build --strict；死链必失败；
libcairo-only 告警容忍（§9 声明不处理）；其他真错误必失败。
触发用 main...HEAD（pre-push 时 --cached/HEAD diff 恒空）。
spec §4 Task 2.4 / 缺口 A（经 R1-R5 audit_loop 收敛）。"
```

---

## Phase 3 · negative test 证明守卫工作（spec Phase 3，须在 Phase 1 前）

### Task 8: negative tests（spec Task 3.0/3.1/3.2/3.3）

**复杂度: leaf**（测试，不改源码；但须手动操作 + 还原）
**test_kind: regression_guard**

**Files:**
- 无新文件（手动操作 + 输出记录到 PR 描述）

**Interfaces:**
- Consumes: Task 1/2/3/4 的守卫
- Produces: PR 描述里的 4 个测试输出

> **时序**：Task 3.0 须在 Phase 1（Task 7 合 Dependabot）前。本 Task 排在 Phase 2 后、Phase 1 前。

#### Task 3.0: pip-audit dev-group 锁 negative test

**关键语义**：pip-audit 审计 installed 包。Issue 2 症状 = 本地装 docs 组后 venv 脏，裸 pip-audit **误判失败**（报 21 漏洞），`--group dev` 锁 reconcile 回 dev 组才 0 漏洞。

- [ ] **Step 1: 确认基线（Phase 1 前，docs 组含漏洞）**

Run: `uv sync --group docs && uv run pip-audit; echo "exit=$?"`
Expected: exit=1 + `Found 21 known vulnerabilities`（pillow 12.2.0 + pymdown 10.21.3）

> **grep matcher（审查 I3）**：用 pip-audit 退出码（1=有漏洞）判断，非 `grep -c vulnerabilities`（后者对"Found N"和"No vulnerabilities"都返回 1，无法区分）。
> 若 exit=0，说明 Phase 1 已先跑——须用注入法（spec Task 3.0 时序约束：临时在非 dev 组 pin 已知漏洞包）。

- [ ] **Step 2: 模拟 Issue 2 复发（注释锁，用副本保护原文件）**

**保护原文件（审查 I4）**：不直接改 `tools/pre-push-check.sh`，而是复制副本测试：
```bash
cp tools/pre-push-check.sh /tmp/pp-nolock-test.sh
# 在副本里把 uv sync --frozen --group dev >/dev/null 注释掉
```
这样无论测试中发生什么（中断、意外输出），原文件不受污染。

- [ ] **Step 3: 跑副本 pre-push，预期误判失败**

Run: `bash /tmp/pp-nolock-test.sh 2>&1 | grep -A2 pip-audit; echo "exit=$?"`
Expected: 报 21 漏洞，exit 1（误判失败——审脏 venv）

- [ ] **Step 4: 跑原文件（锁在），预期 0 漏洞**

Run: `bash tools/pre-push-check.sh 2>&1 | grep -A2 pip-audit; echo "exit=$?"`
Expected: `No known vulnerabilities found`，exit 0（锁 reconcile venv 回 dev 组）

- [ ] **Step 5: 清理副本 + 还原 venv**

Run: `rm /tmp/pp-nolock-test.sh && uv sync --frozen --group dev`

- [ ] **Step 6: 记录输出到 PR 描述**

#### Task 3.1: fixture mirror drift negative test

- [ ] **Step 1: 造漂移（改源不改 fixture）**

在 `outline-example.md` 末尾加一行空格。

- [ ] **Step 2: 跑 hook，预期 FAIL**

Run: `uv run pre-commit run fixture-mirror-sync --all-files`
Expected: exit 1，提示 `fixture mirror drift: tests/fixtures/outline-example.md != outline-example.md` + `fix: cp outline-example.md tests/fixtures/outline-example.md`

- [ ] **Step 3: 还原**

Run: `git checkout outline-example.md`

#### Task 3.2: mkdocs dead link negative test

- [ ] **Step 1: 造死链（用 throwaway 文件，审查 M2，不污染 tracked spec）**

新建 `docs/_tmp_deadlink_test.md`，内容含死链（**完整 markdown 格式**，spec-deviation 修正：`](path)` 不完整，mkdocs 不识别为链接）：
```markdown
# temp dead link test

[dead link](../nonexistent-test-link.md)
```

Run: `git add docs/_tmp_deadlink_test.md && git commit -m "test(temp): inject dead link for Task 3.2"`

- [ ] **Step 2: 跑 pre-push docs 块，预期 FAIL**

Run: `bash tools/pre-push-check.sh 2>&1 | grep -A2 "mkdocs link"`
Expected: exit 1，输出 `contains a link` 行

- [ ] **Step 3: 还原**

Run: `git reset --hard HEAD~1 && rm docs/_tmp_deadlink_test.md`

#### Task 3.3: positive test（干净树全绿）

- [ ] **Step 1: 跑 pre-commit all + pre-push**

Run: `uv run pre-commit run --all-files && bash tools/pre-push-check.sh`
Expected: 全绿

- [ ] **Step 2: 跑 just check**

Run: `just check`
Expected: 2787 passed + 4 last-marked passed

- [ ] **Step 3: 记录 4 个测试输出到 PR 描述，标 negative tests 通过**

---

## Phase 1 · 合 Dependabot（消 21 条真漏洞，spec Phase 1）

### Task 7: 合 Dependabot PR #21/#22（spec Task 1.1/1.2）

**复杂度: leaf**（合 PR，跑验证命令）
**test_kind: characterization**（依赖升级，行为保持）

**Files:**
- Modify: `uv.lock`（Dependabot PR 改）

**Interfaces:**
- Consumes: Dependabot PR #21（pillow 12.2.0→12.3.0）、#22（pymdown 10.21.3→11.0.0）
- Produces: pip-audit 归 0

> **前置**：Task 8（Task 3.0）须已完成（时序约束）。

- [ ] **Step 1: 合 PR #21（pillow）**

```bash
gh pr merge 21 --merge --delete-branch
```

- [ ] **Step 2: 验证 pillow 漏洞归 0**

Run: `uv sync --group docs && uv run pip-audit 2>&1 | grep pillow`
Expected: 空（pillow 已修）；或仅剩 pymdown

- [ ] **Step 3: 合 PR #22（pymdown 10→11，大版本，有兼容风险）**

```bash
gh pr merge 22 --merge --delete-branch
```

- [ ] **Step 4: 兼容性验证（spec Task 1.2）**

Run: `uv sync --group docs && uv run mkdocs build 2>&1 | grep -iE 'pymdown|extension.*error'`
Expected: 空（无 pymdown 相关错）

若不兼容（grep 非空）：回退 PR #22（`gh pr revert 22`），pymdown 漏洞留至 mkdocs-material 升级支持后再合，PR 描述注明部分完成。

- [ ] **Step 5: 验证 pip-audit 全归 0**

Run: `uv sync --group docs && uv run pip-audit`
Expected: `No known vulnerabilities found`（或仅剩 pymdown 若回退）

- [ ] **Step 6: 跑 just check**

Run: `just check`
Expected: 2787 passed + 4 last-marked passed

---

## Phase 4 · 清 94 条 CodeQL（独立 chore PR，遵铁律 5）

### Task 9: audit_script.py 裁决 + 移除（spec Task 4.1，Option A）

**复杂度: leaf**（git rm 单文件，零 .gitignore 改动——R1 C1 核实 negation lines 承重 1261 文件）
**test_kind: characterization**

**Files:**
- Remove: `novel-output/audit_script.py`

**裁决**：spec Task 4.1 Option A（纯 git rm，不改 .gitignore）。理由：硬编码 `/Users/xiaotiac/...` 绝对路径、无人 import（`grep -rn audit_script src/ tests/` 空）、一次性审计脚本。**关键**：`.gitignore` 的 `!novel-output/` + `!novel-output/**`（L93-94）negation 承重 1261 文件（含 xinghuo-ranqiong 1229 个，被 test_production_config_coherence.py 守卫），删 negation 会让未来新增文件静默 untracked——故只 git rm 单文件。

- [ ] **Step 1: 确认无 import（裁决前置）**

Run: `grep -rn audit_script src/ tests/`
Expected: 空

- [ ] **Step 2: git rm（零 .gitignore 改动）**

```bash
git rm novel-output/audit_script.py
```

- [ ] **Step 3: 确认 negation lines 原样保留**

Run: `grep -n "novel-output" .gitignore`
Expected: L88 `novel-output/` + L93 `!novel-output/` + L94 `!novel-output/**` 全在

- [ ] **Step 4: 跑 just check（确认无测试依赖此文件）**

Run: `just check`
Expected: 2787 passed（若有测试引用 audit_script，此处会 FAIL，记 spec-deviation）

- [ ] **Step 5: Commit**

```bash
git commit -m "chore(codeql): remove novel-output/audit_script.py (17 alerts)

硬编码本地绝对路径的一次性审计脚本，无人 import。纯 git rm，
不改 .gitignore（negation lines 承重 1261 文件）。
spec §4 Task 4.1 Option A。消 17 条 CodeQL。"
```

---

### Task 10: Phase 4.2a 清 tests/ 下 36 条（leaf，机械修）

**复杂度: leaf**
**test_kind: characterization**（测试码 except 收窄，行为保持）

**Files:**
- Modify: `tests/` 下相关文件（test_gate_cli.py 12 + test_character_design.py 5 + 其余散落 19）

**修复模式**（spec §4 Task 4.2）：
- `empty-except`：bare `except:` → specific 或 `except Exception` + 注释
- `catch-base-exception`：`except BaseException` → `except Exception`
- `unused-local-variable`：删除或 `_` 前缀
- `import-and-import-from` / `repeated-import`：合并/删重复

- [ ] **Step 1: 取 tests/ 下 36 条告警清单**

Run: `gh api 'repos/ThomasChangX/shenbi/code-scanning/alerts?ref=main&state=open&tool_name=CodeQL' --paginate | jq -r '[.[]|select(.most_recent_instance.location.path|startswith("tests/"))] | .[] | "\(.most_recent_instance.location.path):\(.most_recent_instance.location.start_line) \(.rule.id)"'`

> **字段名**：GitHub Code Scanning API 用 snake_case `start_line`（非 camelCase `startLine`，后者产出 `:null`）。

- [ ] **Step 2: 逐文件修（按规则，每文件 commit 或整批 commit）**

逐个 empty-except / catch-base / unused-local 按 spec 模式修。

- [ ] **Step 3: 跑 just check（测试码改动，确认无回归）**

Run: `just check`
Expected: 2787 passed（测试 except 收窄不改变测试断言）

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "chore(codeql): clean 36 alerts in tests/ (empty-except/unused-local)

spec §4 Task 4.2a（leaf，机械修）。"
```

---

### Task 11: Phase 4.2b 清 gates/ 18 条（infra，逐 site，禁止 bulk sed）

**复杂度: infra**（触及 gate 源码，R1 I4 警示 except 收窄语义负载）
**test_kind: characterization**

**Files:**
- Modify: `src/shenbi/gates/`（g7 5 + g5 4 + g6_checks 2 + g0 2 + shared 1 + g6 1 + g4/chapter_drafting 1 + g3 1 + g1 1）

**特别警示（R1 I4）**：gates 的 `except BaseException` / bare `except:` 是**语义负载的**——可能意在捕 `KeyboardInterrupt`/`SystemExit` 做清理。**每个 except 收窄点必须逐 site 审查原意图，禁止 bulk sed**。AGENTS.md："gate checkers idempotent—pure validation, no side effects"。

- [ ] **Step 1: 取 gates/ 下 18 条清单**

Run: `gh api '...' | jq -r '[.[]|select(.most_recent_instance.location.path|startswith("src/shenbi/gates/"))] | .[] | "\(.most_recent_instance.location.path):\(.most_recent_instance.location.start_line) \(.rule.id)"'`

- [ ] **Step 2: 逐 site 审查 + 修**

每个 except 收窄点：
1. 读上下文，判断原 `except BaseException` 是否在捕 KeyboardInterrupt 做清理
2. 若是 → 保留或显式 `except (Exception, KeyboardInterrupt)` + 注释
3. 若否 → 收窄为 `except Exception` 或 specific

- [ ] **Step 3: 跑 gate 测试**

Run: `uv run pytest tests/unit/gates/ tests/integration/test_gate_cli.py -v`
Expected: 全绿

- [ ] **Step 4: 跑 just check**

Run: `just check`
Expected: 2787 passed

- [ ] **Step 5: 跨 Phase AC（R1 I1）—— 重跑 fixture-mirror hook 确认 g0.py import 仍解析**

Run: `uv run pre-commit run fixture-mirror-sync --all-files`
Expected: PASS（Task 3 的 MIRROR_MAP import 未被 gates 改动震断）

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/gates/
git commit -m "chore(codeql): clean 18 alerts in gates/ (per-site except review)

逐 site 审查 except BaseException/bare except 语义（R1 I4），
非 bulk sed。spec §4 Task 4.2b（infra）。"
```

---

### Task 12: Phase 4.2c/4.2d/4.3 清 pipeline 14 + 其余 9 + cyclic-import 10

**复杂度: 4.2c/4.3 = infra（pipeline 框架码 + cyclic-import 设计决策）；4.2d = leaf**
**test_kind: characterization**

**Files:**
- Modify: `src/shenbi/pipeline/`（scr_extractor 4 + crash_recovery 3 + dispatch_helper 2 + 其余 5）
- Modify: `src/shenbi/` 其余 9
- cyclic-import 10 条跨多文件

**cyclic-import 处置（spec Task 4.3 + R1 I5 预算）**：
- 惰性 import 可解 → 函数内 import
- 模块边界设计问题 → `# noqa` + 注释 + **开 follow-up issue**（每个 noqa 必须附 issue 链接）
- PR 描述列"已修复 X / 已抑制 Y"比例

- [ ] **Step 1: 取 pipeline/ + 其余 + cyclic-import 清单**

Run: `gh api '...' | jq -r '[.[]|select(.most_recent_instance.location.path|startswith("src/shenbi/pipeline/") or .rule.id=="py/cyclic-import")] | .[] | "\(.most_recent_instance.location.path):\(.most_recent_instance.location.start_line) \(.rule.id)"'`

- [ ] **Step 2: 逐文件修（pipeline 按 except/unused 模式；cyclic 逐个判断）**

cyclic-import 逐个：
1. 判断能否惰性 import
2. 不能 → `# noqa` + 注释 `# cyclic-import: see follow-up issue #NNN` + 开 issue

- [ ] **Step 3: 跑 pipeline 测试**

Run: `uv run pytest tests/unit/pipeline/ -v`
Expected: 全绿（cyclic 改动易触发 import error，密切观察）

- [ ] **Step 4: 跨 Phase AC —— 重跑 fixture-mirror hook**

Run: `uv run pre-commit run fixture-mirror-sync --all-files`
Expected: PASS

- [ ] **Step 5: 跑 just check**

Run: `just check`
Expected: 2787 passed

- [ ] **Step 6: Commit（按批次，pipeline / 其余 / cyclic 分开或合并）**

```bash
git add src/shenbi/
git commit -m "chore(codeql): clean pipeline 14 + misc 9 + cyclic-import 10

cyclic-import: X fixed (lazy import) / Y suppressed (noqa + follow-up #NNN).
spec §4 Task 4.2c/4.2d/4.3（4.2c/4.3 infra, 4.2d leaf）。"
```

- [ ] **Step 7: 最终验证 CodeQL 归 0（审查 I1）**

**分两阶段验证**（`ref=main` 只报 main 分支告警，feature 分支修复在合并 + 重扫后才反映）：
1. **分支验证**（push 后，待 CodeQL 在本分支重扫完成）：`gh api 'repos/ThomasChangX/shenbi/code-scanning/alerts?ref=spec/eliminate-existing-warnings&state=open&tool_name=CodeQL' --paginate | jq length` → 期望趋近 0（CodeQL push 触发，重扫延迟数分钟-数小时）
2. **合并后验证**（Phase 4 PR 合并到 main 后）：`gh api 'repos/ThomasChangX/shenbi/code-scanning/alerts?ref=main&state=open&tool_name=CodeQL' --paginate | jq length` → 期望 0

> 若分支查询返回 94（CodeQL 未重扫），等 workflow 完成（`gh run list -w codeql -L1`）后再查。**禁止把"main 仍 94"误判为清理失败**——合并前 main 必然保持旧值。
Expected: `0`（待 CodeQL 重扫后；可能需 push 触发）

---

## Self-Review

**1. Spec coverage:**
- §1.2 CodeQL 0 → T9-T12 ✓
- §1.2 pip-audit 0 → T7 ✓
- §1.2 pre-push 锁 → T1 + T8(Task3.0) ✓
- §1.2 fixture 拦截 → T2-T3 + T8(Task3.1) ✓
- §1.2 mkdocs 拦截 → T4 + T8(Task3.2) ✓
- §1.2 just check 保持 → 每 Task ✓
- §2 Issue 1/2/6/7 根治 → T1/T4/T7/T9-T12/T2-T3 ✓
- §5 铁律 5（chore PR 集中）→ Phase 4 独立 ✓
- §5 铁律 6（negative test）→ T8 ✓
- §5 铁律 7（单一源）→ T3 ✓
- §6 AC 全覆盖 → AC 覆盖表 ✓

**2. Placeholder scan:** 无 TBD/TODO；每个 code step 含完整代码。

**3. Type consistency:** `MIRROR_MAP: dict[str, str]`（T3 定义）↔ check_fixture_mirror.py `MIRROR_MAP.items()`（T2 用）一致；`main() -> int` 一致。

**Gap:** Task 编号 5/6 跳过（合并到 Task 2/3 紧耦合 + Task 4 独立），无遗漏。
