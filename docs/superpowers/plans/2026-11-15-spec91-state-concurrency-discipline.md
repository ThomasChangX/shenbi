# Spec #91 状态与并发纪律（state-and-concurrency-discipline）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gate_passed 单源+SKIP 显式化+比较侧 lint、失败协议分类器单源迁移+genesis 差异表、两处锁窗口闭合（确定性红绿测）、retry 状态写回归封装（存取器接线）、T5 收尾（改名+semaphore 可选化）。

**Architecture:** 全部任务为 infra 类（动 `src/shenbi/pipeline/`、`src/shenbi/status.py`、`src/shenbi/contracts/`），协调者亲自实现。修法=单源化+锁窗口收拢+存取器接线，行为保持（characterization 钉死）优先，唯一行为变更面（genesis 接线）已挂用户裁定不落码。

**Tech Stack:** Python 3.11+/pytest/ast（新 lint）/threading.Event（确定性并发编排）/justfile。

## Global Constraints

- spec：`docs/superpowers/specs/2026-11-01-spec91-state-concurrency-discipline.md`（r2.3c）——行号锚 2026-11-15 树（deb50f99+工作分支）；**plan 首步 re-anchor 纪律**：每 task 开工前以符号 grep 复核行号（INDEX 行号锚纪律）。
- `src/shenbi/` 禁 `print()`（structlog）；gate 检查器纯函数幂等；`pathlib.Path`；conventional commits；测试结构输入可 inline/tmp_path 构造（G0.9 允许面），禁手写 fixture 冒充真实产物。
- 改 src 文件的 task 提交后**必须重锁工具哈希**：`tests/lock-tool-hashes.sh` + `git add tests/tiers/deps.json`（216 src 文件全锁；#90 教训①——字节级追加[如 noqa]后也须再锁）。
- 全部验收离线（fixtures/结构断言），零真实 dispatch（核心原则 8；F947 无涉）。
- commit 用显式 pathspec，禁 `git add -A`。

---

### Task 1: `gate_passed` 单源 + 11 点 characterization 断言表

**复杂度: infra** ｜ **test_kind: characterization**（钉死现行为——SKIP 分歧逐点快照）

**Files:**
- Modify: `src/shenbi/status.py`（新增公共函数，置于 `GateStatus` 类之后）
- Test: `tests/unit/test_gate_passed_single_source.py`（新）

**Interfaces:**
- Produces: `gate_passed(result: Any, *, accept_skip: bool = False) -> bool`（`shenbi.status`）——Task 2 全部换装点消费此签名；语义：`status = str(result.get("status", ""))`，`accept_skip=True` → `status in (GateStatus.PASS, GateStatus.SKIP)`，默认 → `status == GateStatus.PASS`。

- [ ] **Step 1: 写 characterization 断言表（11 点 × PASS/SKIP/FAIL）**

```python
"""Spec #91 T1: gate_passed single-source characterization.

Pins the CURRENT per-site semantics BEFORE rewiring (spec r2.3c):
- triggers/closure sites: SKIP counts as passed (accept_skip=True target)
- chapter_loop/audit_layer/genesis + phase_runner/cli direct compares:
  only PASS counts (accept_skip=False target)
- chapter_loop:1597 compound: status None also passes
"""

from shenbi.status import GateStatus, gate_passed


def _res(status):
    return {"status": status}


# Target semantics table: (site, input, expected_after_rewire)
SITES = [  # 9 single-compare sites (r3 审查 M2: 1597/4063 pinned in Task 2)
    ("triggers.py:505/_gate_passed", _res("PASS"), True),
    ("triggers.py:505/_gate_passed", _res("SKIP"), True),  # SKIP passes HERE ONLY
    ("triggers.py:505/_gate_passed", _res("FAIL"), False),
    ("closure.py:125/_gate_passed", _res("SKIP"), True),
    ("chapter_loop.py:1446/_gate_passed", _res("SKIP"), False),  # SKIP fails here
    ("audit_layer.py:209/_gate_passed", _res("SKIP"), False),
    ("genesis.py:284/_gate_passed", _res("SKIP"), False),
    ("phase_runner.py:146/'PASS'", _res("SKIP"), False),
    ("phase_runner.py:378/'PASS'", _res("SKIP"), False),
    ("cli.py:223/GateStatus.PASS", _res("SKIP"), False),
    ("cli.py:255/GateStatus.PASS", _res("SKIP"), False),
]


def test_gate_passed_default_rejects_skip():
    assert gate_passed(_res(GateStatus.PASS)) is True
    assert gate_passed(_res(GateStatus.FAIL)) is False
    assert gate_passed(_res(GateStatus.SKIP)) is False
    assert gate_passed({}) is False


def test_gate_passed_accept_skip():
    assert gate_passed(_res(GateStatus.SKIP), accept_skip=True) is True
    assert gate_passed(_res(GateStatus.PASS), accept_skip=True) is True
    assert gate_passed(_res(GateStatus.FAIL), accept_skip=True) is False


# NOTE (r3 审查 M2): table covers the 9 single-compare sites; chapter_loop:1597
# (compound None-passes) and :4063 (negative compare) are pinned by Task 2's
# mapping comments + their post-rewire unit tests, not by this table.
def test_semantics_table_covers_all_sites():
    assert len(SITES) == 9
    for site, res, expected in SITES:
        assert isinstance(expected, bool) and site
```

- [ ] **Step 2: 跑测试确认 FAIL（`ImportError: cannot import name 'gate_passed'`）**

Run: `uv run pytest tests/unit/test_gate_passed_single_source.py -q`
Expected: FAIL（函数未定义）

- [ ] **Step 3: 实现（status.py，GateStatus 类后）**

```python
def gate_passed(result: Any, *, accept_skip: bool = False) -> bool:
    """Single source for gate-result pass/fail decisions (spec #91 T1).

    ``accept_skip`` makes the site's SKIP tolerance explicit: trigger/closure
    sites pass True (SKIP counts as passed — pinned pre-existing behavior);
    all other sites default to PASS-only.
    """
    status = str(result.get("status", ""))
    if accept_skip:
        return status in (GateStatus.PASS, GateStatus.SKIP)
    return status == GateStatus.PASS
```

- [ ] **Step 4: 跑测试确认 PASS**

Run: `uv run pytest tests/unit/test_gate_passed_single_source.py -q`
Expected: 3 passed

- [ ] **Step 5: Commit（含 deps.json 重锁）**

```bash
tests/lock-tool-hashes.sh && git add src/shenbi/status.py tests/unit/test_gate_passed_single_source.py tests/tiers/deps.json
git commit -m "feat: spec #91 T1 gate_passed 单源（status.py）+11 点 characterization 断言表"
```

---

### Task 2: 11 判定点换装 + 五 `_gate_passed` 定义删除

**复杂度: infra** ｜ **test_kind: regression_guard**（换装后语义=Task 1 断言表；`def _gate_passed` 零残留）

**Files:**
- Modify: `src/shenbi/pipeline/triggers.py:505-509`（删 def；调用点 :657/:724 换装）
- Modify: `src/shenbi/pipeline/chapter_loop.py:1446-1448`（删 def；调用点 :1569/:2308/:4257/:4263/:4651/:4655/:4743 换装；复合点 :1597；负比较 :4063）
- Modify: `src/shenbi/pipeline/closure.py:125-129`（删 def；调用点 :309/:317）
- Modify: `src/shenbi/pipeline/audit_layer.py:209-212`（删 def；调用点 :248）
- Modify: `src/shenbi/pipeline/genesis.py:284-287`（删 def；调用点 :644/:649/:708）
- Modify: `src/shenbi/phase_runner.py:146/:378`
- Modify: `src/shenbi/pipeline/cli.py:223/:255`

**Interfaces:**
- Consumes: `shenbi.status.gate_passed`（Task 1）
- Produces: 验收 1 前半——`grep -rn "def _gate_passed" src/` 零残留

**换装 pattern（逐文件代表例 + 穷举清单）：**

triggers.py（SKIP 算过——唯一传 `accept_skip=True` 的文件）：
```python
# 头部 import 区加：from shenbi.status import gate_passed
# :657  if not _gate_passed(g4):        → if not gate_passed(g4, accept_skip=True):
# :724  if not _gate_passed(g3):        → if not gate_passed(g3, accept_skip=True):
# :505-509 def _gate_passed 整体删除
```
closure.py 同 pattern（:309/:317 传 accept_skip=True；:125-129 删）。

chapter_loop.py（默认 PASS-only）：
```python
# 头部：from shenbi.status import gate_passed（GateStatus 若仅剩他用则保留原 import）
# :1569/:2308/:4257/:4263/:4651/:4655/:4743:  _gate_passed(x) → gate_passed(x)
# :1446-1448 def _gate_passed 删除
# :1597 复合判定（语义保持——None 也算过）：
#   旧: if xc.get("status") not in ("PASS", None):
#   新: if xc.get("status") is not None and not gate_passed(xc):
# :4063 负比较:
#   旧: if str(rec["g3"].get("status", "")) != "PASS":
#   新: if not gate_passed(rec["g3"]):
```
audit_layer.py（:248 换装；:209 删）、genesis.py（:644/:649/:708 换装；:284 删）同默认 pattern。
**unused-import 清理（r2 审查 M1）**：triggers.py/closure.py/pipeline-cli.py 的 `GateStatus` import 在 def 删除/换装后若失用（ruff F401）——按 ruff 提示逐文件删除；chapter_loop/genesis 的 GateStatus 若仍有他处消费则保留。

phase_runner.py:
```python
# 头部加 from shenbi.status import gate_passed
# :146  if g5.get("status") == "PASS":   → if gate_passed(g5):
# :378  if g5.get("status") != "PASS":   → if not gate_passed(g5):
```
pipeline/cli.py:
```python
# :223  if str(g4.get("status")) == GateStatus.PASS:  → if gate_passed(g4):
# :255  if str(routed.get("status")) == GateStatus.PASS:  → if gate_passed(routed):
```

- [ ] **Step 1: 逐文件换装（pattern+清单如上；每文件改后跑其单测）**

Run（每文件）: `uv run pytest tests/unit/pipeline/test_triggers.py tests/unit/pipeline/test_chapter_loop.py -q 2>&1 | tail -3`（按文件选既有测试文件名）

- [ ] **Step 2: 验收 grep 零残留**

Run: `grep -rn "def _gate_passed" src/` → 期望空输出（exit 1）

- [ ] **Step 3: 全量回归**

Run: `uv run pytest tests/unit -q -x -m "not slow" 2>&1 | tail -3`（全绿后进 Step 4）

- [ ] **Step 4: Commit**

```bash
tests/lock-tool-hashes.sh && git add src/shenbi/pipeline/triggers.py src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/closure.py src/shenbi/pipeline/audit_layer.py src/shenbi/pipeline/genesis.py src/shenbi/phase_runner.py src/shenbi/pipeline/cli.py tests/tiers/deps.json
git commit -m "refactor: spec #91 T1 11 判定点换装 gate_passed 单源——五 _gate_passed 定义删除+SKIP 容忍逐点显式"
```

---

### Task 3: 比较侧 lint 守卫（tools/lint_gate_status_comparisons.py + justfile 接线）

**复杂度: infra** ｜ **test_kind: tdd_red_green**

**Files:**
- Create: `tools/lint_gate_status_comparisons.py`
- Modify: `justfile:24-50` lint recipe 区（加一行）
- Test: `tests/unit/tools/test_lint_gate_status_comparisons.py`（新）

**Interfaces:**
- Produces: lint 守卫（验收 1 后半）——a) `src/shenbi/pipeline/**`+`src/shenbi/phase_runner.py` 域内 `def *_gate_passed` 模式定义零容忍；b) 同域 Compare 节点中 status 与 PASS/SKIP（`GateStatus.PASS`/`GateStatus.SKIP`/裸 `"PASS"`/`"SKIP"`）比较仅允许出现在 `gate_passed` 单源本体（域外 status.py 天然不在扫描面）。已知残余不拦：反演式（`== "FAIL"`）、变量间接。
- CLI 形态对齐既有 lint：`uv run python tools/lint_gate_status_comparisons.py` → 零违规 exit 0 / 违规逐行打印 exit 1。**scan 签名（r2 审查 I4）**：`scan(roots: list[Path] | None = None) -> list[str]`——None 时内建默认域 `DOMAIN = [Path("src/shenbi/pipeline"), Path("src/shenbi/phase_runner.py")]`（CLI 无参跑默认域；测试 `scan()` 即首跑零红基线——gates/gate_manifest.py:195、g7.py:151 等域外命中不进面）。

- [ ] **Step 1: 红测（违规样本 tmp 构造 + 干净面零违规）**

```python
"""Spec #91 T1 lint: gate-status comparison guard (red-green)."""

from tools.lint_gate_status_comparisons import (
    scan,
    scan_file,
)  # repo convention (test_lint_status_strings.py:8)


def test_clean_tree_zero_violations():
    # against the real repo src face (post-Task-2 rewiring)
    out = scan()  # default domain = pipeline/ + phase_runner.py (I4: domain built-in)
    assert out == []


def test_detects_new_private_definition(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("def _gate_passed(r):\n    return True\n")
    out = scan_file(f.read_text(), str(f))
    assert any("_gate_passed" in v for v in out)


def test_detects_bare_compare(tmp_path):
    f = tmp_path / "bad2.py"
    f.write_text('if g4.get("status") == "PASS":\n    pass\n')
    out = scan_file(f.read_text(), str(f))
    assert any("PASS" in v for v in out)


def test_allows_enum_emit_and_non_status_compare(tmp_path):
    f = tmp_path / "ok.py"
    f.write_text(
        "x = GateStatus.PASS.value  # emit, not compare\n"
        'if name == "PASS-ish":\n    pass\n'  # not a status-keyed compare
    )
    assert scan_file(f.read_text(), str(f)) == []
```

（AST 实现要点：`ast.walk` 收 `Compare` 节点；左侧 `.get("status"/"state"/"classification"/"s")` 调用或 `Subscript` status 键，右侧/左侧常量 `"PASS"/"SKIP"` 或 `GateStatus.PASS/SKIP` 属性 → 违规；`FunctionDef` 名匹配 `*_gate_passed` → 违规；扫描根=`src/shenbi/pipeline`+`src/shenbi/phase_runner.py`；豁免=无（status.py 域外）。`main()` 对齐 lint_status_strings 的 exit 约定。）

- [ ] **Step 2: 跑红** → `uv run pytest tests/unit/tools/test_lint_gate_status_comparisons.py -q` FAIL（模块不存在）

- [ ] **Step 3: 实现 lint** → Step 4: 跑绿（`test_clean_tree_zero_violations` 在 Task 2 完成后必绿=首跑零红基线）

- [ ] **Step 5: justfile 接线**（lint recipe `:44` `lint_audit_run` 行后加）：
```
    uv run python tools/lint_gate_status_comparisons.py
```

- [ ] **Step 6: `just check` 快验证 + Commit**

```bash
git add tools/lint_gate_status_comparisons.py tests/unit/tools/test_lint_gate_status_comparisons.py justfile
git commit -m "feat: spec #91 T1 比较侧 lint 守卫——def *_gate_passed 零容忍+status 比较 held-to-single-source"
```

---

### Task 4: T2 `classify_dispatch_failure` 迁 contracts + re-export + genesis 差异表落盘

**复杂度: infra** ｜ **test_kind: regression_guard**（迁移零行为变化；消费面 8 点零改动）

**Files:**
- Create: `src/shenbi/contracts/failure.py`
- Modify: `src/shenbi/pipeline/dispatch_helper.py:3411-3436`（定义体移出，原位改 re-export）
- Modify: `docs/superpowers/specs/2026-11-01-spec91-state-concurrency-discipline.md`（追加 §4 差异表）
- Test: `tests/unit/contracts/test_failure_classify.py`（新）+ 既有 `tests/unit/pipeline/test_retry_taxonomy.py` 全绿

**Interfaces:**
- Produces: `shenbi.contracts.failure.classify_dispatch_failure(exc: BaseException | None = None, returncode: int | None = None, *, stderr: str = "") -> FailureClass`（逐字迁移，含 docstring；`exc` 形参保留——签名零变化）
- dispatch_helper.py 原位：`from shenbi.contracts.failure import classify_dispatch_failure as classify_dispatch_failure  # noqa: F401, PLC0414`（as-alias 显式 re-export 过 mypy no_implicit_reexport[pyproject strict]——#90 教训④；既有 8 消费点 parallel_dispatch :151/:154 + dispatch_helper :3773/:3794/:4345 + chapter_loop :461/:4233/:4638 零改动）

- [ ] **Step 1: 测试（纯函数分类表 + re-export 同一性）**

```python
"""Spec #91 T2: classify_dispatch_failure relocation (contracts layer)."""

from shenbi.contracts.enums import FailureClass
from shenbi.contracts.failure import classify_dispatch_failure
from shenbi.pipeline.dispatch_helper import classify_dispatch_failure as re_exported


def test_rc2_gate():
    assert (
        classify_dispatch_failure(returncode=2, stderr="write-audit GATE_FAIL x")
        is FailureClass.DETERMINISTIC_GATE
    )


def test_rc2_plain():
    assert classify_dispatch_failure(returncode=2) is FailureClass.DETERMINISTIC_CONTENT


def test_transient_default():
    assert classify_dispatch_failure(returncode=1) is FailureClass.TRANSIENT
    assert classify_dispatch_failure(exc=RuntimeError("x")) is FailureClass.TRANSIENT
    assert classify_dispatch_failure() is FailureClass.TRANSIENT


def test_reexport_identity():
    assert re_exported is classify_dispatch_failure
```

- [ ] **Step 2: 红**（ImportError）→ **Step 3: 迁移**（contracts/failure.py 全文=函数+docstring+`from shenbi.contracts.enums import FailureClass`；dispatch_helper 原位换 re-export）→ **Step 4: 绿 + 既有消费面回归**：

Run: `uv run pytest tests/unit/contracts/test_failure_classify.py tests/unit/pipeline/test_retry_taxonomy.py -q` → 全 PASS

- [ ] **Step 5: genesis 差异表落盘（spec 追加 §4）**

```markdown
## 4. genesis 差异表（r2.3c 落盘——用户裁定输入；验收 4）

| 场景 | genesis 现行为（count-only） | 接线后（failure_class 短路） | 差异 |
|---|---|---|---|
| dispatch rc=2（DETERMINISTIC_CONTENT/GATE） | `genesis._handle_failure` :445 count-only——烧满 `max_revision_retries`（默认 3 次尝试）才 escalation | 首败即 escalation（非 TRANSIENT 短路） | **有**：重试次数 3→0 |
| dispatch rc=1/-1/异常（TRANSIENT） | 同上 count-only 重试 | 不短路，count-only 重试（行为同） | 无 |
| G4/结构失败路径 | 不经 `_handle_failure` dispatch 分支 | 同左 | 无 |

**裁定请求**：rc=2 类确定性失败在 genesis（创世重跑场景）是否切换为零重试直通 escalation。裁定通过 → follow-up 小批落「形参+短路+接线」三件；裁定驳回 → 保持 count-only（差异表归档备查）。
```

- [ ] **Step 6: Commit**

```bash
tests/lock-tool-hashes.sh && git add src/shenbi/contracts/failure.py src/shenbi/pipeline/dispatch_helper.py tests/unit/contracts/test_failure_classify.py tests/tiers/deps.json docs/superpowers/specs/2026-11-01-spec91-state-concurrency-discipline.md
git commit -m "refactor: spec #91 T2 classify_dispatch_failure 迁 contracts/failure.py+re-export——genesis 差异表落盘挂裁定"
```

---

### Task 5: T3a ledger_archive 锁窗口闭合（红绿两测）

**复杂度: infra** ｜ **test_kind: tdd_red_green**（红=丢失更新演示；绿=锁内读结构断言——两测形态不同）

**Files:**
- Modify: `src/shenbi/pipeline/ledger_archive.py:146-252`（`archive_ledger`——:158 读+锚检/拼接整体移入 :251 `with path_lock(live_path):`；归档半边 :260-265 不动=蓝本）
- Modify: `src/shenbi/pipeline/truth_io.py`（新增公共探针 `path_lock_held(path: Path | str) -> bool`——`entry = _PATH_LOCKS.get(str(path)); return entry is not None and entry[0].locked()`；纯读无副作用；供绿测 spy 与后续锁纪律测试用——r2 审查 I2：避免 tests import `_PATH_LOCKS` 撞 lint_private_imports 基线[增量=零政策]）
- Test: `tests/unit/pipeline/test_ledger_archive_lock_window.py`（新）

**Interfaces:**
- Consumes: `truth_io.path_lock`（既有）、`safe_write`（既有）
- Produces: `archive_ledger` 读-合-写全锁内（对外签名 `(project_dir: Path, resolved_through: int, spec: LedgerSpec) -> list[str]` 零变化）

- [ ] **Step 1: 红测（注入 `_section_fields` 编排线程 B 写入——当前码 B 丢失）**

```python
"""Spec #91 T3: ledger_archive lock-window red/green (no sleep, deterministic)."""

import threading
from pathlib import Path
import pytest
from shenbi.pipeline import ledger_archive as la

# spy uses the PUBLIC probe added in this task (r2 审查 I2：tests 私有 import 会撞 lint_private_imports 基线增量=零)
from shenbi.pipeline.truth_io import path_lock_held

# fixture MUST pass POOL_SPEC shape gates: `## 总览` + `## 详情` + a
# 详情-section matching HOOK_HEADING_RE (blueprint: tests/unit/pipeline/test_ledger_archive.py:150-155)
LIVE_TEXT = (
    "---\ntype: truth\n---\n\n# 伏笔池\n\n## 总览\n\n| Hook ID（钩子名） | 当前生命周期 | 种植章 |\n"
    "| MH01（灵印） | RESOLVED | 4 |\n\n## 详情\n\n### MH01（灵印）\n\n"
    "- lifecycle_state: RESOLVED\n- resolve_chapter: 30\n"
)
B_LINE = "- lifecycle_state: RESOLVED-by-b\n"  # B's committed update


def _write_b(path: Path) -> None:
    with la.path_lock(path):  # B takes the lock properly
        text = path.read_text(encoding="utf-8")
        la.safe_write(path, (text + B_LINE).encode("utf-8"))


def test_red_thread_b_update_lost(tmp_path, monkeypatch):
    # RED on current code: A reads OUTSIDE the lock; B's locked write
    # during A's parse window is clobbered by A's blind write.
    live = tmp_path / "truth" / "pending_hooks.md"
    live.parent.mkdir(parents=True)
    live.write_text(LIVE_TEXT, encoding="utf-8")
    gate = threading.Event()
    proceed = threading.Event()
    orig = la._section_fields

    def hooked(spec, section):
        if not gate.is_set():
            gate.set()
            proceed.wait(timeout=5)  # hold A in its lock-free window
        return orig(spec, section)

    monkeypatch.setattr(la, "_section_fields", hooked)
    errors: list[Exception] = []

    def run_a():
        try:
            la.archive_ledger(tmp_path, 30, la.POOL_SPEC)
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=run_a)
    t.start()
    assert gate.wait(timeout=5)
    assert not errors  # shape gates passed; A parked in its lock-free parse window
    _write_b(live)  # B commits inside A's window
    proceed.set()
    t.join(timeout=5)
    assert not errors
    assert B_LINE not in live.read_text(encoding="utf-8")  # B LOST → red asserts the defect
```

（`POOL_SPEC` 为实际模块常量（ledger_archive.py:82）；`resolved_through=30` 使 RESOLVED 判定入窗——若 re-anchor 后窗口判定不同，按 `test_ledger_archive.py` 既有断言调参；红测断言「B 丢失」在当前码为 True=测试通过=缺陷被钉死。）

- [ ] **Step 2: 跑红**（当前码下 B 行丢失 → 断言 `B_LINE not in ...` 通过=缺陷实存证据；若断言失败说明窗口未如预期开——调注入点行号后重试）

- [ ] **Step 3: 绿测（修复后形态——锁内读结构断言）**

```python
def test_green_read_holds_lock(tmp_path, monkeypatch):
    live = tmp_path / "truth" / "pending_hooks.md"
    live.parent.mkdir(parents=True)
    live.write_text(LIVE_TEXT, encoding="utf-8")
    seen: list[bool] = []
    orig = Path.read_text

    def spy(self, *a, **k):
        if self == live:  # only watch the live ledger file
            seen.append(path_lock_held(self))  # public probe imported at module top (r3 审查 I2)
        return orig(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", spy)
    la.archive_ledger(tmp_path, 30, la.POOL_SPEC)
    assert seen and all(seen)  # every live-read happened under the path lock


def test_green_both_writers_survive(tmp_path):  # r2 审查 I5；断言落点 r3 审查 C1 修正
    live = tmp_path / "truth" / "pending_hooks.md"
    live.parent.mkdir(parents=True)
    live.write_text(LIVE_TEXT, encoding="utf-8")
    _write_b(
        live
    )  # B commits first (properly locked) → B's line is INSIDE the section span A reads
    la.archive_ledger(tmp_path, 30, la.POOL_SPEC)  # A archives afterwards
    # archive semantics: the whole section span (INCLUDING B's line) is moved
    # verbatim to the archive file and replaced by a tombstone in live.
    # "Both writers survive" therefore asserts: B's line lives on in the
    # ARCHIVE file, and the live file carries A's tombstone marker.
    archive = tmp_path / "truth" / "pending_hooks_archive.md"
    assert B_LINE in archive.read_text(encoding="utf-8")  # B's committed update preserved
    assert (
        "archived_to" in live.read_text(encoding="utf-8")
    )  # A's tombstone present (marker per ledger_archive tombstone const; re-anchor on implementation)
```

- [ ] **Step 4: 实现（:146-252 重排——`with path_lock(live_path):` 提前到 :158 读之前，函数体其余缩进一级；单写者行为零变化；归档半边不动）→ 跑双测**（红测断言现在**翻转**：修复后 B 不丢→`B_LINE not in` 失败——**将红测断言翻转为 `assert B_LINE in ...` 并改名**？**否**——spec 验收 2 要求「红绿非同一测试翻转」：保留红测文件原断言但在修复 commit 前将其标记 `pytest.mark.xfail(strict=True, reason="defect fixed")`，绿测独立存在。采用 xfail(strict) 形态：修复后红测变 xfail-strict 通过=防回潮哨兵，绿测=结构断言）

Run: `uv run pytest tests/unit/pipeline/test_ledger_archive_lock_window.py -q` → 红(xfail strict)+绿 全 PASS

- [ ] **Step 5: 既有 ledger 测试回归 + Commit**

```bash
uv run pytest tests/unit/pipeline -q -k "ledger or archive" 2>&1 | tail -3
tests/lock-tool-hashes.sh && git add src/shenbi/pipeline/ledger_archive.py src/shenbi/pipeline/truth_io.py tests/unit/pipeline/test_ledger_archive_lock_window.py tests/tiers/deps.json
git commit -m "fix: spec #91 T3 ledger_archive 锁窗口闭合——读-合-写全锁内+确定性红绿双测（xfail 哨兵防回潮）"
```

---

### Task 6: T3b dispatch_helper outline 合并锁内重读重验 + path_lock 不可重入警告

**复杂度: infra** ｜ **test_kind: tdd_red_green**（注入 `_strip_hr_lines`）

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:2592-2644`（`:2596 base_text = target.read_text(...)` 与 `:2599 _strip_hr_lines`、`:2610 check_new_volume_anchor` 移入 `:2618 with path_lock(target):` 内；锁内重读 `base_text = target.read_text(...) if target.exists() else ""` 后再 strip/验锚/合并）
- Modify: `src/shenbi/pipeline/truth_io.py:79-91`（path_lock docstring 追加不可重入警告）
- Test: `tests/unit/pipeline/test_outline_merge_lock_window.py`（新；形态同 Task 5——注入 `_strip_hr_lines` 为编排点，红=锁外读+并发写者行丢失[xfail-strict 哨兵]，绿=Path.read_text spy 断言 `path_lock_held(path)`（Task 5 公共探针——r2 审查 I2/M4））

**Interfaces:**
- Produces: outline 合并读-验-写全锁内；`path_lock` docstring 含「Lock is NOT reentrant (threading.Lock): never call write_truth_file on the same path while holding it」。

- [ ] Step 1-2: 红测（同 Task 5 pattern；`_strip_hr_lines` 注入 Event——编排点在 :2599 锁前窗口）→ 跑红
- [ ] Step 3: 绿测（spy read_text 断言锁内）→ 实现（锁内重读重验锚——`anchor_error` 在锁内基于**重读后**的 base_text 计算）
- [ ] Step 4: 双测绿 + docstring 警告 + 既有 outline/merge 测试回归：

Run: `uv run pytest tests/unit/pipeline -q -k "outline or merge or dispatch_helper" 2>&1 | tail -3`

- [ ] **Step 5: Commit**

```bash
tests/lock-tool-hashes.sh && git add src/shenbi/pipeline/dispatch_helper.py src/shenbi/pipeline/truth_io.py tests/unit/pipeline/test_outline_merge_lock_window.py tests/tiers/deps.json
git commit -m "fix: spec #91 T3 outline 合并锁内重读重验锚+path_lock 不可重入 docstring 警告"
```

---

### Task 7: T4 retry 状态写回归封装（三新存取器 + 全写点换装 + 三组测试）

**复杂度: infra** ｜ **test_kind: tdd_red_green（新 API）+ characterization（charge/feedback 并发语义）**

**Files:**
- Modify: `src/shenbi/pipeline/state.py`（`charge_retry_budget` 后新增五方法——increment_retry_budget/set_retry_feedback/pop_retry_feedback/get_retry_feedback/clear_retry_feedback_prefix）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（全部写点换装——清单见下）
- Modify: `src/shenbi/pipeline/triggers.py:594/:746`、`src/shenbi/pipeline/cli.py:1324-1346`
- Test: `tests/unit/pipeline/test_retry_accessors.py`（新）+ 既有 `test_state_concurrency.py` 全绿

**Interfaces（Produces，state.py——全部 `with self._lock:`；feedback 三存取器收 `key: str`[『chN-skill』形]——调用面 12+ 点全部已持有/手拼 key 字符串[chapter_loop rk 产物 / cli f-string]，二元组形态反而要求每调用点重构；counts/budget 存取器保持 (chapter, skill) 对齐既有三方法惯例——r1 审查 I6 裁定）：**
```python
def increment_retry_budget(self, chapter: int, skill: str) -> int:
    """Thread-safe serial +=1 of retry_budget_consumed (spec #91 T4).

    NOT charge_retry_budget: charge is idempotent max() for wave aggregation
    replay; serial paths need monotonic increments that never lose counts.
    """
    rk = retry_key(chapter, skill)
    with self._lock:
        consumed = self.chapter_loop.retry_budget_consumed.get(rk, 0) + 1
        self.chapter_loop.retry_budget_consumed[rk] = consumed
        return consumed


def set_retry_feedback(self, key: str, feedback: str) -> None:
    """Locked write of retry_feedback[key] (spec #91 T4; key = 'chN-skill')."""
    with self._lock:
        self.chapter_loop.retry_feedback[key] = feedback


def pop_retry_feedback(self, key: str) -> str | None:
    """Locked pop of retry_feedback[key]."""
    with self._lock:
        return self.chapter_loop.retry_feedback.pop(key, None)


def get_retry_feedback(self, key: str) -> str | None:
    """Locked read of retry_feedback[key]."""
    with self._lock:
        return self.chapter_loop.retry_feedback.get(key)
```

**写点换装穷举清单（re-anchor 后逐点）：**
- `retry_counts`：:1954（`_handle_failure` 内 → `count = state.increment_retry(chapter, step.skill)`）；:4726-4727（g4_hard 自动重试路径 → 同）；`:4737` 裸 pop → `state.reset_retry(chapter, step.skill)`；`_reset_retries` :2056-2058 体 → `state.reset_retry(chapter, step.skill)`（7 调用方零改动）
- `retry_budget_consumed` 索引写 3 区域 → `state.increment_retry_budget(chapter, skill)`（:1959-1960 `_handle_failure` 内[返回值供 `consumed` 判断]；:4412-4413 monitor_rewind；:4712-4713 g4_hard）；**事件发射顺序重排（r1 审查 I5；r3 审查 M3：双站点同型都改）**：现码 monitor_rewind（:4402-4405）与 g4_hard（:4704-4708）**两处**均为 `_emit_retry_event` 在增量**前**发射且 `loop_id=.get()+1`——两处都换装为**先 `consumed = state.increment_retry_budget(...)` 再发射、`loop_id=consumed`**（返回值已含 +1，字面「返回值+1」会得旧值+2 的可观测漂移）；不新增 budget 读存取器（spec 未要求）
- `retry_feedback` 赋值 12 点 → `state.set_retry_feedback(rk_or_fstring, accumulate_retry_feedback(state, rk, failures, ...))`（key 形态直传——chapter_loop :1879/:4191/:4220/:4252/:4272/:4387/:4524/:4589/:4629/:4697 + cli :1324-1329/:1345-1350）；裸 pop :2416（章闭 sweep——前缀批量清理，单键存取器接不住：新增 `clear_retry_feedback_prefix(prefix: str) -> None` 锁内批量 pop）；triggers:746 → `state.pop_retry_feedback(f"ch{chapter}-{step.skill}")`；`_clear_retry_feedback` :1244 体 → `state.pop_retry_feedback(retry_key)`（签名收 str key 直传，4 消费点零改动）；读点 :594(triggers)/:1316/:2030-2031 → `state.get_retry_feedback(key)`

**三组测试（tests/unit/pipeline/test_retry_accessors.py；`_fresh_state()` 抄 tests/unit/pipeline/test_state_concurrency.py:11 同名助手形态——r1 审查 M3）：**
```python
def test_increment_retry_concurrent_equals_serial_sum():
    s = _fresh_state()

    def worker():
        for _ in range(200):
            s.increment_retry(1, "x")

    t1, t2 = threading.Thread(target=worker), threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert s.chapter_loop.retry_counts["ch1-x"] == 400  # == serial sum


def test_charge_budget_concurrent_is_max_not_sum():  # characterization
    s = _fresh_state()

    def worker(n):
        for _ in range(100):
            s.charge_retry_budget(1, "x", n)

    ts = [threading.Thread(target=worker, args=(n,)) for n in (3, 7)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert s.chapter_loop.retry_budget_consumed["ch1-x"] == 7  # max, NOT 10


def test_increment_budget_monotonic():  # serial +=1, never loses
    s = _fresh_state()
    assert s.increment_retry_budget(1, "x") == 1
    assert s.increment_retry_budget(1, "x") == 2


def test_feedback_last_writer_wins():  # characterization (STORE_SUBSCR atomic)
    s = _fresh_state()
    s.set_retry_feedback("ch1-x", "a")
    s.set_retry_feedback("ch1-x", "b")
    assert s.get_retry_feedback("ch1-x") == "b"
    assert s.pop_retry_feedback("ch1-x") == "b"
    assert s.get_retry_feedback("ch1-x") is None


def test_clear_prefix_sweep():
    s = _fresh_state()
    s.set_retry_feedback("ch1-a", "x")
    s.set_retry_feedback("ch1-b", "y")
    s.clear_retry_feedback_prefix("ch1-")
    assert s.get_retry_feedback("ch1-a") is None
```

- [ ] Step 1: 写测试（红：五存取器未定义）→ Step 2: 跑红 → Step 3: state.py 实现五方法 → Step 4: 跑绿 → Step 5: 写点换装（清单逐点；每文件换装后跑 `uv run pytest tests/unit/pipeline -q -k "retry or chapter_loop or state"`）→ Step 6: 验收 3 grep 三连零：

```bash
grep -n "retry_budget_consumed\[" src/shenbi/pipeline/chapter_loop.py        # 期望空
grep -nE "retry_counts\[|retry_counts\.pop" src/shenbi/pipeline/chapter_loop.py  # 期望空
grep -nE "retry_feedback\[|retry_feedback\.(pop|get)" src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/triggers.py src/shenbi/pipeline/cli.py | grep -v "genesis.retry_feedback"  # 期望空（r3 审查 M1：面扩到 pop/get；genesis 域 4 写点 r2.3b 挂账排除——过滤后零）
```

- [ ] Step 7: 生产调用方 grep ≥1：

```bash
grep -rn "increment_retry(\|reset_retry(\|increment_retry_budget(" src/shenbi/pipeline/ | grep -v "def \|_reset_retry_budget\|_charge_wave"  # 期望多行
```

- [ ] **Step 8: Commit**

```bash
tests/lock-tool-hashes.sh && git add src/shenbi/pipeline/state.py src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/triggers.py src/shenbi/pipeline/cli.py tests/unit/pipeline/test_retry_accessors.py tests/tiers/deps.json
git commit -m "feat: spec #91 T4 retry 状态写回归封装——三新存取器+前缀清扫+全写点换装（counts/budget/feedback）"
```

---

### Task 8: T5 semaphore 可选化 + `run_post_draft_pair` 改名 + Semaphore(1) 戏法删除

**复杂度: infra** ｜ **test_kind: regression_guard**

**Files:**
- Modify: `src/shenbi/pipeline/parallel_dispatch.py:92-96/:118`（`semaphore: Semaphore | None = None`；体内 `ctx = nullcontext() if semaphore is None else semaphore; with ctx:`；头部 `from contextlib import nullcontext`）
- Modify: `src/shenbi/pipeline/chapter_loop.py:3636`（`run_parallel_post_draft_steps` → `run_post_draft_pair`；docstring 首行保持 SEQUENTIALLY 自述）；:3774-3780（Semaphore import+构造+传参删除——`dispatch_serial_reviews` 内调 `dispatch_with_retry(task, state=state)`）；:4179 调用点改名
- Test: 既有测试接线（grep 枚举：`tests/pipeline/test_parallel_steps.py`、`tests/unit/pipeline/test_chapter_loop.py`、`tests/unit/pipeline/test_retry_taxonomy.py`、`tests/unit/pipeline/test_spec83_stale_declarations.py`、`tests/integration/test_spec83_stale_chain.py`——字符串 monkeypatch/真调用逐点改新名）

**Interfaces:**
- Produces: `dispatch_with_retry(task: ReviewTask, semaphore: Semaphore | None = None, state: Any = None)`（既有必填调用方 parallel_dispatch.py:269 `Semaphore(4)` 传入零影响）；`run_post_draft_pair(state: PipelineState) -> tuple[Any, Any]`

- [ ] Step 1: `grep -rn "run_parallel_post_draft_steps" src/ tests/` 现场枚举接线点（spec r2.3 清单已声明大半失效）→ 逐点改新名
- [ ] Step 2: semaphore 可选化 + 戏法删除 → Step 3: 验收 5 grep：

```bash
grep -rn "Semaphore" src/shenbi/pipeline/chapter_loop.py   # 期望空
```

- [ ] Step 4: 回归 `uv run pytest tests/unit/pipeline tests/pipeline -q -k "parallel or post_draft or serial" 2>&1 | tail -3`（全绿）
- [ ] **Step 5: Commit**

```bash
tests/lock-tool-hashes.sh && git add src/shenbi/pipeline/parallel_dispatch.py src/shenbi/pipeline/chapter_loop.py tests/pipeline/test_parallel_steps.py tests/unit/pipeline/test_chapter_loop.py tests/unit/pipeline/test_retry_taxonomy.py tests/unit/pipeline/test_spec83_stale_declarations.py tests/integration/test_spec83_stale_chain.py tests/tiers/deps.json  # pathspec 收窄（r1 审查 M4；以 Step 1 grep 实际命中为准增删）
git commit -m "refactor: spec #91 T5 semaphore 可选化 nullcontext+run_post_draft_pair 正名+Semaphore(1) 戏法删除"
```

---

### Task 9: 验收汇跑 + INDEX plan 指针

**复杂度: infra** ｜ **test_kind: regression_guard**

**Files:**
- Modify: `docs/superpowers/specs/INDEX.md`（#91「对应 plan」→ 本 plan 路径）

- [ ] Step 1: 验收 1-6 逐条实跑并粘贴输出进 progress.md `## 验收证据`（验收 grep 六连 + `uv run pytest tests/unit/test_gate_passed_single_source.py tests/unit/pipeline/test_ledger_archive_lock_window.py tests/unit/pipeline/test_outline_merge_lock_window.py tests/unit/pipeline/test_retry_accessors.py -q`）
- [ ] Step 2: `just check` EXIT 0（完整输出留 progress.md 门禁输出节）
- [ ] Step 3: INDEX 指针 + Commit：

```bash
git add docs/superpowers/specs/INDEX.md
git commit -m "docs: spec #91 INDEX 登记对应 plan 指针"
```

---

## 验收覆盖表（spec §2 → task → 验证命令）

| 验收 | task | 验证 |
|---|---|---|
| 1 零残留+11 点+lint 首跑零红 | T2/T3 | `grep -rn "def _gate_passed" src/` 空；`uv run python tools/lint_gate_status_comparisons.py` exit 0；断言表 11 点 |
| 2 T3 红绿双测（形态不同） | T5/T6 | `pytest test_ledger_archive_lock_window.py test_outline_merge_lock_window.py`（xfail-strict 哨兵+spy 结构断言） |
| 3 budget/feedback/counts 裸写零+生产调用 ≥1 | T7 | 三连 grep 空 + 调用方 grep 多行 |
| 4 genesis 差异表落盘 | T4 | spec §4 存在+内容=rc=2 单点对比+裁定请求段 |
| 5 Semaphore 零 | T8 | `grep -rn "Semaphore" src/shenbi/pipeline/chapter_loop.py` 空 |
| 6 just check | T9 | exit 0 |

## Self-Review 记录

- 覆盖：spec T1→Task1-3、T2→Task4、T3→Task5-6、T4→Task7、T5→Task8、验收 6→Task9 ✓；genesis 三件挂裁定（不落码）已从任务面剔除 ✓
- 占位符：Task 5 `spec = ...` 处标注 re-anchor 义务（模块常量名开工前 grep——非 TBD，是显式现场枚举步骤）✓
- 类型一致：`gate_passed(result: Any, *, accept_skip: bool = False) -> bool` 全 plan 唯一签名；`increment_retry_budget(chapter, skill) -> int` 与调用点返回值消费一致 ✓
