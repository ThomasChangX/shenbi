# 消除 cyclic-import 簇 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 pipeline 4-节点环 + dispatcher/audit 2-节点环改造为 DAG，消除 10 条 `py/cyclic-import` + 1 条 `py/unused-import`（共 11 条 CodeQL 告警），通过下沉纯函数/常量/frozen dataclass 到两个新 `_shared.py` 中性模块，行为零变更。

**Architecture:** 识别环内被多方依赖但自身不依赖任何环内成员的符号，迁移到 `_shared.py`；原模块对 `_shared` 形成单向依赖，回边消失。Cluster 1（pipeline）下沉 volume-map 解析域 6 符号到 `pipeline/_shared.py`；Cluster 2（audit）下沉 `derive_output_files` + `AuditResult` 到 `audit/_shared.py`。Re-export 守住 `closure.py`/`cli.py`/`chapter_loop.py`/`phase_runner.py` 等运行时消费者 + 测试锚点 + `__init__.py` 公开 API。第 11 条告警（`write_truth_file` vacuous re-export）单独删除。

**Tech Stack:** Python 3.11+，`pathlib.Path`，`dataclasses`，`re`。无新依赖。

## Global Constraints

（来自 spec §1-§8 + AGENTS.md，每 task 隐式包含）
- Python 3.11+，框架代码用 `pathlib.Path` 做文件 I/O，无 `print()`（用 structlog）。
- 纯重构，**行为零变更**——不优化 volume_map 解析逻辑、不改 `AuditResult` 字段、不动 `__init__.py` 公开 API 声明（只改内部 import 来源）。
- Conventional Commits：`refactor:` 前缀。
- Gate checkers 保持幂等纯函数。本 plan 不动 G4 schema / 契约 `reads`/`writes`。
- 测试基线（V1/V2）：≥2787 passed + 4 last-marked，coverage ≥85.03%（PR #25 后 main 实测值）。**不回归**。
- 每个 task commit 后必须产 `.superpowers/sdd/audit-T<N>.md`（fresh-context 全量重审），无 audit-T<N>.md 不得开始 T<N+1>。

**Spec:** `docs/superpowers/specs/2026-08-02-issue24-cyclic-import-refactor-design.md`（Phase 1 已核实、Phase 2 已设计审查收敛）

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/shenbi/pipeline/_shared.py` | **新建** | Cluster 1 中性模块：volume-map 解析域（6 符号） |
| `src/shenbi/audit/_shared.py` | **新建** | Cluster 2 中性模块：`derive_output_files` + `AuditResult` |
| `src/shenbi/pipeline/triggers.py` | 改 | 删 `read_volume_boundaries`/`VOLUME_MAP_PATH`/`_END_RE`/`_RANGE_RE` 定义，顶部加 re-export |
| `src/shenbi/pipeline/context_assemble.py` | 改 | 删 `_BRIDGE_ACTIVATION_WINDOW`/`_resolve_volume_at_runtime` 定义，顶部 import 自 `_shared`，L208 回边改指 `_shared` |
| `src/shenbi/pipeline/plan_skeleton.py` | 改 | L31-32/L199-200 的 `context_assemble` import 改指 `_shared`（L200 上移顶部） |
| `src/shenbi/pipeline/dispatch_helper.py` | 改 | 删 L688 cyclic 注释（import 语句保留——`triggers↔dispatch_helper` 与 `dispatch_helper→plan_skeleton` 边 T1 后变 acyclic，注释成 stale suppression） |
| `src/shenbi/dispatcher/executor.py` | 改 | 删 `derive_output_files` 定义，顶部加 re-export |
| `src/shenbi/audit/write_audit.py` | 改 | 删 `AuditResult` 定义加 re-export，L31 回边改指 `_shared` |
| `src/shenbi/audit/record.py` | 改 | L17 TYPE_CHECKING import 改指 `_shared` |
| `src/shenbi/pipeline/dispatch_helper.py` | 改 | 删 L53-57 `write_truth_file` re-export 块 |
| `tests/unit/pipeline/test_dispatch_write_semantics.py` | 改 | 删 vacuous `patch(...)` 块，保留正面断言 |

**复杂度分类**：3 task 全部 `infra`（多文件、跨包 import 重构、被 3+ pipeline 模块 import）→ 协调者亲自实现，不分派子 agent（SDD leaf/infra 分流规则）。

**test_kind**：3 task 全部 `regression_guard`——纯重构、行为保持，既有测试是回归网，不写新 TDD 测试。

---

## AC 覆盖表（每 spec §5 验证标准 → task → test）

| spec AC | task | 验证 test/命令 |
|---------|------|----------------|
| V1 `just check` 全绿 ≥2787 passed | T1+T2+T3 后 Phase 6 | `just check` 末尾 pytest |
| V2 coverage ≥85.03% | T1+T2+T3 后 Phase 6 | `just check` 覆盖率行 |
| V3 codebase 零 `# py/cyclic-import` 注释 | T1+T2+T3 | `grep -rn "py/cyclic-import" src/shenbi/` 返回空 |
| V4 CodeQL `py/cyclic-import` = 0 | PR 的 CodeQL 扫描 | Phase 8-9 |
| V5 CodeQL `py/unused-import`(dispatch_helper.py)=0 | PR 的 CodeQL 扫描 | Phase 8-9 |
| V6 被迁移符号既有测试全绿 | T1/T2/T3 各阶段 pytest | 各 task 验证步 |
| V7 ruff/mypy/basedpyright 对 `_shared` 全绿 | T1+T2 后 | `just check` lint 段 |
| V8 `from shenbi.audit import AuditResult` 不变 | T2 后 | `python -c "from shenbi.audit import AuditResult"` |

---

## Task 1: 新建 `pipeline/_shared.py`，下沉 volume-map 解析域（Cluster 1）

**复杂度:** infra（跨 4 个 pipeline 模块 import 重构）→ 协调者亲自实现

**Files:**
- Create: `src/shenbi/pipeline/_shared.py`
- Modify: `src/shenbi/pipeline/triggers.py`（删 L78/316/320/326-355 定义，顶部加 re-export）
- Modify: `src/shenbi/pipeline/context_assemble.py`（删 L45/201-222 定义，顶部 import 自 `_shared`，L208-209 回边改指 `_shared`）
- Modify: `src/shenbi/pipeline/plan_skeleton.py`（L31-32/L199-200 import 改指 `_shared`，L200 上移顶部）
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（删 L688 cyclic 注释，import 语句保留）
- Modify: `src/shenbi/pipeline/triggers.py`（额外：删 L54/L644 cyclic 注释，import 语句保留）
- Test（回归网）: `tests/unit/pipeline/test_triggers.py`、`tests/unit/pipeline/test_context_assemble.py`、`tests/unit/pipeline/test_plan_skeleton.py`

**Interfaces:**
- Consumes: 无（`_shared.py` 是叶子模块，只 import `re` + `pathlib.Path`）
- Produces: `read_volume_boundaries(project_dir: Path | str) -> set[int]`、`_resolve_volume_at_runtime(project_dir: Path, chapter: int) -> tuple[str, int, int] | None`、`_BRIDGE_ACTIVATION_WINDOW: int`（=3）、`VOLUME_MAP_PATH: str`、`_END_RE: re.Pattern`、`_RANGE_RE: re.Pattern`

- [ ] **Step 1: 新建 `src/shenbi/pipeline/_shared.py`**（迁移 6 符号，从源码逐字复制）

```python
"""Volume-map 解析域共享符号（Cluster 1 cyclic-import 重构中性模块）。

本模块是叶子模块——只依赖标准库（re/pathlib），不 import 任何 pipeline 环内成员
（triggers/context_assemble/plan_skeleton/dispatch_helper）。原 4-节点环
（triggers → dispatch_helper → plan_skeleton → context_assemble → triggers）
的回边（context_assemble → triggers）通过把共享符号下沉到本模块打断。

迁移自：triggers.py（read_volume_boundaries/VOLUME_MAP_PATH/_END_RE/_RANGE_RE）+
context_assemble.py（_BRIDGE_ACTIVATION_WINDOW/_resolve_volume_at_runtime）。
行为零变更（spec §3.2）。
"""

from __future__ import annotations

import re
from pathlib import Path

#: Bridge activation window: chapters before activation to start surfacing bridges.
_BRIDGE_ACTIVATION_WINDOW = 3

#: Path to the volume map (relative to project_dir).
VOLUME_MAP_PATH = "outline/volume_map.md"

# "Chapter N-M" / "Chapters N-M" / "N-M" patterns in volume sections.
_END_RE = re.compile(
    r"(?:chapter\s*)?(?:end|chapter_end|end_chapter)\s*[:\uff1a]\s*(\d+)",
    re.IGNORECASE,
)
_RANGE_RE = re.compile(
    r"(?:chapters?|ch)\s*(\d+)\s*[-\u2013\u2014~\u301c]\s*(\d+)",
    re.IGNORECASE,
)


def read_volume_boundaries(project_dir: Path | str) -> set[int]:
    """Parse ``outline/volume_map.md`` and return last-chapter numbers per volume.

    Supports two markdown formats:

    1. Section with ``Chapter End: N`` (or ``End: N``).
    2. ``Chapters N-M`` range notation.

    Returns an empty set if the file does not exist or cannot be parsed.
    """
    if not project_dir:
        raise ValueError("read_volume_boundaries: project_dir is required")
    project_dir = Path(project_dir)
    vm_file = project_dir / VOLUME_MAP_PATH
    if not vm_file.exists():
        return set()

    text = vm_file.read_text(encoding="utf-8")
    boundaries: set[int] = set()

    # Try "Chapter End: N" patterns first.
    for m in _END_RE.finditer(text):
        boundaries.add(int(m.group(1)))

    # Fall back to "Chapters N-M" ranges.
    if not boundaries:
        for m in _RANGE_RE.finditer(text):
            boundaries.add(int(m.group(2)))

    return boundaries


def _resolve_volume_at_runtime(project_dir: Path, chapter: int) -> tuple[str, int, int] | None:
    """Resolve (volume_name, ch_start, ch_end) for a chapter at runtime.

    Parses volume_map.md via read_volume_boundaries() which
    returns a set of last-chapter numbers per volume. We build the
    (start, end) ranges from that set.
    """
    boundary_chapters = read_volume_boundaries(project_dir)
    if not boundary_chapters:
        return None

    boundaries_sorted = sorted(boundary_chapters)
    prev_end = 0
    for i, end in enumerate(boundaries_sorted, 1):
        ch_start = prev_end + 1
        if ch_start <= chapter <= end:
            return (f"Volume {i}", ch_start, end)
        prev_end = end
    return None
```

- [ ] **Step 2: 改 `src/shenbi/pipeline/triggers.py`**——删 `VOLUME_MAP_PATH`(L78)、`_END_RE`/`_RANGE_RE`(L316-323)、`read_volume_boundaries`(L326-355) 定义；顶部加 re-export（MANDATORY：closure.py:30 顶层 + chapter_loop.py:976/cli.py:154/triggers.py:360/context_assemble.py:209 运行时消费者 + test_triggers.py:40 测试锚点）。

删除 L78 区块：
```python
# 删除（原 L75-79）：
DRIFT_THRESHOLD = 3

#: Path to the volume map (relative to project_dir).
VOLUME_MAP_PATH = "outline/volume_map.md"

#: Path to the audit drift log (relative to project_dir, section 6.7).
AUDIT_DRIFT_PATH = "truth/audit_drift.md"
```
替换为（只留 DRIFT_THRESHOLD + AUDIT_DRIFT_PATH，VOLUME_MAP_PATH 走 re-export）：
```python
DRIFT_THRESHOLD = 3

#: Path to the audit drift log (relative to project_dir, section 6.7).
AUDIT_DRIFT_PATH = "truth/audit_drift.md"

# Re-export from _shared (MANDATORY: closure.py top-level import + 4 runtime
# consumers + test anchor — see spec §3.2). Volume-map parsing domain was
# extracted to break the Cluster 1 cycle (context_assemble → triggers back-edge).
from shenbi.pipeline._shared import (  # noqa: F401
    VOLUME_MAP_PATH,
    _END_RE,
    _RANGE_RE,
    read_volume_boundaries,
)
```

删除 L315-323（`_END_RE`/`_RANGE_RE` 定义区块，已迁 `_shared`）：
```python
# 删除整块（原 L315-323）：
# "Chapter N-M" / "Chapters N-M" / "N-M" patterns in volume sections.
_END_RE = re.compile(
    r"(?:chapter\s*)?(?:end|chapter_end|end_chapter)\s*[:\uff1a]\s*(\d+)",
    re.IGNORECASE,
)
_RANGE_RE = re.compile(
    r"(?:chapters?|ch)\s*(\d+)\s*[-\u2013\u2014~\u301c]\s*(\d+)",
    re.IGNORECASE,
)
```

删除 L326-355（`read_volume_boundaries` 定义，已迁 `_shared`）。

> **`import re` 必须保留**（已核实）：triggers.py 仍在用 `re.search`（L120）、`_WARNING_RE = re.compile`（L367）、`re.compile`（L412 `_extract_chapter_node`）。只 `_END_RE`/`_RANGE_RE` 搬走，其他正则留原地。

**额外删 cyclic 注释（保留 import 语句）**：T1 必须清 Cluster 1 全部 6 条 cyclic 注释。本步删 triggers.py 的 2 条（`triggers↔dispatch_helper` 边 T1 后变 acyclic——回边 `context_assemble→triggers` 已断）：
- L54 cyclic 注释行（`# py/cyclic-import (CodeQL): cycle with dispatch_helper ...`）——**只删注释行**，下方 `from shenbi.pipeline.dispatch_helper import dispatch_skill, run_gate_g4`（L55）保留。
- L644 cyclic 注释行（同上，缩进在 `if step.requires_g3:` 块内）——**只删注释行**，下方 `from shenbi.pipeline.dispatch_helper import run_gate_g3`（L645）保留。

> 删除顺序：**自下而上**（先 L644-645 区的注释、再 L326-355 `read_volume_boundaries`、再 L316-323 正则常量、再 L78 `VOLUME_MAP_PATH`、最后 L54-55 区的注释），避免行号漂移。或用 Edit 唯一字符串匹配（行号仅供参考）。

- [ ] **Step 3: 改 `src/shenbi/pipeline/context_assemble.py`**——删 `_BRIDGE_ACTIVATION_WINDOW`(L44-45)、`_resolve_volume_at_runtime`(L201-222) 定义；顶部加 import 自 `_shared`；L208-209 回边改指 `_shared`；删 L208 cyclic 注释。

删除 L44-45：
```python
# 删除（原 L44-45）：
# Bridge activation window: chapters before activation to start surfacing bridges.
_BRIDGE_ACTIVATION_WINDOW = 3
```

顶部（与其他 `from shenbi...` import 同区，L13 附近 `from shenbi.audit.snapshot import ...` 之后）加：
```python
from shenbi.pipeline._shared import (
    _BRIDGE_ACTIVATION_WINDOW,
    _resolve_volume_at_runtime,
)
```
> **只 import 这 2 个符号**（均已核实 context_assemble.py 自用）：`_BRIDGE_ACTIVATION_WINDOW` 在 L287 `_load_volume_context` 用；`_resolve_volume_at_runtime` 在 L240 用。**不 import `read_volume_boundaries`**——它只被 `_resolve_volume_at_runtime`（已迁 `_shared`）调用，context_assemble.py 本体无其他消费者，import 它是 dead weight。**无需 `# noqa: F401`**——两符号均被使用。

L208-209 区块：
```python
# 删除整块（原 L196-209，含注释 + cyclic 注释 + lazy import）：
# Volume boundaries are parsed at runtime from volume_map.md via
# triggers.py:read_volume_boundaries() -- NEVER hard-coded. Hard-coding
# ('Volume 1', (1, 15)) duplicates the map and will diverge.


def _resolve_volume_at_runtime(...):
    """..."""
    # py/cyclic-import (CodeQL): ...
    from shenbi.pipeline.triggers import read_volume_boundaries
    ...
```
替换为（`_resolve_volume_at_runtime` 定义移除，文档注释保留在 `_shared.py`；顶部 import 已提供符号）：
```python
# Volume boundaries are parsed at runtime from volume_map.md via
# _shared.read_volume_boundaries() -- NEVER hard-coded. Hard-coding
# ('Volume 1', (1, 15)) duplicates the map and will diverge.
```

删除 L201-222（`_resolve_volume_at_runtime` 定义，已迁 `_shared`）。

> 关键（C1 修复）：L287 的 `_load_volume_context` 仍用 `_BRIDGE_ACTIVATION_WINDOW`——顶部 import 已覆盖，不报 NameError。

- [ ] **Step 4: 改 `src/shenbi/pipeline/plan_skeleton.py`**——L31-32/L199-200 的 `context_assemble` import 改指 `_shared`，删 cyclic 注释。

L29-32 区块（与 L199-200 合并，见下）：
```python
# 删除（原 L28-32）：
# Volume boundaries are parsed at runtime via triggers.py:read_volume_boundaries()
# -- NEVER hard-coded. See _resolve_volume_at_runtime().

# py/cyclic-import (CodeQL): cycle with context_assemble — lazy import where needed; see follow-up. Spec §9 no refactor.
from shenbi.pipeline.context_assemble import _BRIDGE_ACTIVATION_WINDOW  # pyright: ignore[reportPrivateUsage]
```

L199-200 区块：
```python
# 删除整块（原 L198-200，含 `# imported from context_assemble` 注释 + cyclic 注释 + import）：
# _resolve_volume_at_runtime imported from context_assemble (canonical definition)
# py/cyclic-import (CodeQL): cycle with context_assemble — lazy import where needed; see follow-up. Spec §9 no refactor.
from shenbi.pipeline.context_assemble import _resolve_volume_at_runtime  # pyright: ignore[reportPrivateUsage]
```
**上移到顶部 import 区**（与 L31-32 的 `_BRIDGE_ACTIVATION_WINDOW` import 合并，符合 plan_skeleton.py 顶部 import 惯例——L200 原在 `_SKELETON_TEMPLATE` 赋值后属 mid-file，是 cyclic 规避的遗留，T1 后无环可上移）。合并后顶部 import 块：
```python
from shenbi.pipeline._shared import (
    _BRIDGE_ACTIVATION_WINDOW,
    _resolve_volume_at_runtime,
)
```
（替换原 L29-32 的 `# Volume boundaries...` 注释 + `_BRIDGE_ACTIVATION_WINDOW` 单行 import + cyclic 注释，整块合并为上面的多行 import。）

- [ ] **Step 4b: 改 `src/shenbi/pipeline/dispatch_helper.py`**——删 L688 cyclic 注释（`dispatch_helper→plan_skeleton` 边 T1 后变 acyclic，注释成 stale suppression）。**只删注释行，import 语句保留。**

L687-689 区块：
```python
# 删除注释行（原 L688），保留 import（原 L689）：
                # py/cyclic-import (CodeQL): cycle with plan_skeleton — lazy import where needed; see follow-up. Spec §9 no refactor.
                from shenbi.pipeline.plan_skeleton import generate_plan_skeleton
```
替换为（只留 import，删 cyclic 注释）：
```python
                from shenbi.pipeline.plan_skeleton import generate_plan_skeleton
```

- [ ] **Step 5: 跑回归测试**（V6 Cluster 1）

Run:
```bash
uv run pytest tests/unit/pipeline/test_triggers.py tests/unit/pipeline/test_context_assemble.py tests/unit/pipeline/test_plan_skeleton.py -v
```
Expected: 全绿（与重构前同 test 数 passed，0 failed）。若 `_BRIDGE_ACTIVATION_WINDOW` NameError → Step 3 顶部 import 漏了（C1 类回归）。

- [ ] **Step 6: lint + cyclic 注释核查**（V3/V7 Cluster 1）

Run:
```bash
uv run ruff check src/shenbi/pipeline/_shared.py src/shenbi/pipeline/triggers.py src/shenbi/pipeline/context_assemble.py src/shenbi/pipeline/plan_skeleton.py src/shenbi/pipeline/dispatch_helper.py
uv run ruff format --check src/shenbi/pipeline/_shared.py src/shenbi/pipeline/triggers.py src/shenbi/pipeline/context_assemble.py src/shenbi/pipeline/plan_skeleton.py src/shenbi/pipeline/dispatch_helper.py
grep -rn "py/cyclic-import" src/shenbi/pipeline/
```
Expected: ruff 全绿；**grep 返回空**（Cluster 1 的 **6 条** cyclic 注释全删：triggers.py L54/L644 + plan_skeleton.py L31/L199 + context_assemble.py L208 + dispatch_helper.py L688）。
> 注：本步 grep 扫 `src/shenbi/pipeline/`（Cluster 1 范围）。Cluster 2 的 4 条注释（`dispatcher/executor.py` + `audit/`）在 T2 后才清——本步不扫那些目录。

- [ ] **Step 7: DAG 核验**（import 图无环）

Run:
```bash
uv run python -c "import shenbi.pipeline.triggers, shenbi.pipeline.context_assemble, shenbi.pipeline.plan_skeleton, shenbi.pipeline.dispatch_helper, shenbi.pipeline._shared; print('Cluster 1 imports OK')"
```
Expected: 打印 `Cluster 1 imports OK`（无 ImportError）。

- [ ] **Step 8: Commit**

```bash
git add src/shenbi/pipeline/_shared.py src/shenbi/pipeline/triggers.py src/shenbi/pipeline/context_assemble.py src/shenbi/pipeline/plan_skeleton.py src/shenbi/pipeline/dispatch_helper.py
git commit -m "refactor(pipeline): extract volume-map domain to _shared — break Cluster 1 cycle (6/10 py/cyclic-import)

- new pipeline/_shared.py: read_volume_boundaries, _resolve_volume_at_runtime,
  _BRIDGE_ACTIVATION_WINDOW, VOLUME_MAP_PATH, _END_RE, _RANGE_RE (leaf module)
- triggers.py: re-export read_volume_boundaries/VOLUME_MAP_PATH/_END_RE/_RANGE_RE
  (MANDATORY: closure.py top-level + 4 runtime consumers); delete L54/L644
  cyclic comments (triggers↔dispatch_helper edge now acyclic)
- context_assemble.py: import _BRIDGE_ACTIVATION_WINDOW/_resolve_volume_at_runtime
  from _shared (L287 _load_volume_context still uses _BRIDGE_ACTIVATION_WINDOW)
- plan_skeleton.py: merge L31+L200 imports to top-level multi-line from _shared
- dispatch_helper.py: delete L688 cyclic comment (dispatch_helper→plan_skeleton
  edge now acyclic)
- delete all 6 Cluster-1 py/cyclic-import comments (CodeQL ignores them anyway)
- behavior unchanged (pure relocation)

Spec: docs/superpowers/specs/2026-08-02-issue24-cyclic-import-refactor-design.md §3.2"
```

---

## Task 2: 新建 `audit/_shared.py`，下沉 derive_output_files + AuditResult（Cluster 2）

**复杂度:** infra（跨 dispatcher/audit 两包 import 重构）→ 协调者亲自实现

**Files:**
- Create: `src/shenbi/audit/_shared.py`
- Modify: `src/shenbi/dispatcher/executor.py`（删 L110-130 `derive_output_files` 定义，顶部加 re-export）
- Modify: `src/shenbi/audit/write_audit.py`（删 L19-24 `AuditResult` 定义加 re-export，L30-31 回边改指 `_shared`，删 cyclic 注释）
- Modify: `src/shenbi/audit/record.py`（L16-17 TYPE_CHECKING import 改指 `_shared`，删 cyclic 注释）
- Modify: `src/shenbi/dispatcher/executor.py`（L259/L263 cyclic 注释删除——import 语句本身保留，是合法单向依赖）
- Test（回归网）: `tests/unit/test_dispatcher_executor.py`、`tests/unit/audit/test_record.py`

**Interfaces:**
- Consumes: `shenbi.contracts.load_contract`、`shenbi.contracts.ContractError`、`shenbi.contracts.paths.resolve_or_skip`（全部 contracts 包，非环内）
- Produces: `derive_output_files(skill: str, chapter: int | None = None, round_dir: Path | None = None) -> list[str]`、`AuditResult`（frozen dataclass: `skill`/`violations`/`drift`/`checked_files`）

- [ ] **Step 1: 新建 `src/shenbi/audit/_shared.py`**（迁移 `derive_output_files` + `AuditResult`，从源码逐字复制）

```python
"""审计共享符号（Cluster 2 cyclic-import 重构中性模块）。

本模块是叶子模块——只 import shenbi.contracts.* + 标准库，不 import
dispatcher/audit.write_audit/audit.record。原 dispatcher/audit 环
（executor ⇄ write_audit + record → write_audit TYPE_CHECKING）的回边
通过把共享符号下沉到本模块打断。

迁移自：dispatcher/executor.py（derive_output_files）+
audit/write_audit.py（AuditResult）。行为零变更（spec §3.3）。

依赖方向说明：executor.py（dispatcher 包）将顶部 import derive_output_files
自本模块，使 dispatcher → audit 包级依赖出现。这是有意接受的——本模块是
叶子（不回 import dispatcher/audit.write_audit/audit.record），audit 前缀
是组织性的（包内私有 _shared），非语义层。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shenbi.contracts import ContractError, load_contract
from shenbi.contracts.paths import resolve_or_skip


@dataclass(frozen=True)
class AuditResult:
    skill: str
    violations: tuple[str, ...]
    drift: tuple[str, ...]
    checked_files: tuple[str, ...]


def derive_output_files(
    skill: str, chapter: int | None = None, round_dir: Path | None = None
) -> list[str]:
    """Return the skill's contract writes+updates, resolving chapter placeholders.
    When *chapter* is provided, N/NNN placeholders are resolved.
    Paths with unresolvable placeholders (genesis mode) are skipped via
    resolve_or_skip → None → filtered. When *round_dir* is provided,
    relative paths are made absolute.
    """
    try:
        c = load_contract(skill)
        paths = [
            rp
            for p in [*c["writes"], *c["updates"]]
            if (rp := resolve_or_skip(p, chapter)) is not None
        ]
        if round_dir is not None:
            paths = [str((round_dir / p).resolve()) for p in paths]
        return paths
    except ContractError:
        return []
```

- [ ] **Step 2: 改 `src/shenbi/dispatcher/executor.py`**——删 L110-130 `derive_output_files` 定义；顶部加 re-export（MANDATORY：phase_runner.py:190 + write_audit.py:31 运行时消费者 + test_dispatcher_executor.py:13 测试锚点 + executor.py:218/245 自调）；删 L259/L263 cyclic 注释（import 语句本身保留）。

顶部 import 区（L16-19 附近，`from shenbi.contracts...` 之后）加：
```python
from shenbi.audit._shared import derive_output_files
```
> **无需 `# noqa: F401`**（已核实）：`derive_output_files` 在 executor.py L218/L245 自用（`dispatch_with_write_audit` 内），不是纯 re-export。ruff/basedpyright 见使用即不报 unused。

删除 L110-130（`derive_output_files` 定义，已迁 `_shared`）。注意：`load_contract`/`ContractError`/`resolve_or_skip` 的 import 在 executor.py 体内其他地方还用（如 L16 `from shenbi.contracts import ContractError, load_contract`、L18 `resolve_or_skip` 用于 `derive_input_files` 等）——**保留这些 import**，只 `derive_output_files` 定义搬走。grep 确认 `load_contract`/`resolve_or_skip` 其他调用点后再定（实际 executor.py 多处用，不会变 unused）。

L259-260 区块（cyclic 注释 + lazy import record）：
```python
# 删除注释行（原 L259），保留 import（原 L260）：
    # py/cyclic-import (CodeQL): cycle with record — lazy import where needed; see follow-up. Spec §9 no refactor.
    from shenbi.audit.record import record_audit_outcome
```
替换为（只留 import，删 cyclic 注释）：
```python
    from shenbi.audit.record import record_audit_outcome
```

L263-264 区块（cyclic 注释 + lazy import write_audit）：
```python
# 删除注释行（原 L263），保留 import（原 L264）：
    # py/cyclic-import (CodeQL): cycle with write_audit — lazy import where needed; see follow-up. Spec §9 no refactor.
    from shenbi.audit.write_audit import audit_writes
```
替换为：
```python
    from shenbi.audit.write_audit import audit_writes
```

- [ ] **Step 3: 改 `src/shenbi/audit/write_audit.py`**——删 L19-24 `AuditResult` 定义加 re-export；L30-31 回边（`_declared_patterns` 内 lazy import）改指 `_shared`，删 cyclic 注释。

L19-24 区块（`AuditResult` 定义）：
```python
# 删除（原 L19-24）：
@dataclass(frozen=True)
class AuditResult:
    skill: str
    violations: tuple[str, ...]
    drift: tuple[str, ...]
    checked_files: tuple[str, ...]
```
替换为（顶部 import 区，L13 `from shenbi.audit.snapshot import ...` 之后加）：
```python
from shenbi.audit._shared import AuditResult
```
> **无需 `# noqa: F401`**（已核实）：`AuditResult` 在 write_audit.py 本体自用——L50 `audit_writes` 返回类型注解、L74 构造返回值。既是 re-export（守 `__init__.py:8` + `test_record.py:7`）又自用。
> **同步删 `from dataclasses import dataclass`（L11）**（已 grep 确认：`@dataclass` 仅 L19 用于 `AuditResult`，搬走后无其他 `@dataclass` 使用）。不删会留 F401 unused-import（ruff 会报）。

L30-31 区块（`_declared_patterns` 内回边）：
```python
# 删除注释 + 改 import 源（原 L30-31）：
        # py/cyclic-import (CodeQL): cycle with executor — lazy import where needed; see follow-up. Spec §9 no refactor.
        from shenbi.dispatcher.executor import derive_output_files
```
替换为（回边消失，改指 `_shared`）：
```python
        from shenbi.audit._shared import derive_output_files
```
> **必须保留 lazy import**（已核实）：`_declared_patterns`（L27 def）用 `try: ... except Exception: return []` 容错——contracts 注册表 bootstrap 失败 / skill 无契约时，`derive_output_files(skill)` 抛 `ContractError`（被 `except` 兜底返回 `[]`）。**禁止改顶部 import**：顶部 import 会在 `write_audit.py` import 期触发 `audit/_shared` → `contracts` 链解析，若 contracts 注册表 bootstrap 失败，整个 `write_audit` 模块不可 import，连带破坏 `audit/__init__.py:8` 公开 API + `record.py` TYPE_CHECKING。lazy import 把失败隔离在 `_declared_patterns` 调用点，`audit_writes` 其他路径不受影响。cyclic 注释删（环已断），import 语句留 lazy。

- [ ] **Step 4: 改 `src/shenbi/audit/record.py`**——L16-17 TYPE_CHECKING import 改指 `_shared`，删 cyclic 注释。

L15-17 区块：
```python
# 删除注释 + 改 import 源（原 L15-17）：
if TYPE_CHECKING:
    # py/cyclic-import (CodeQL): cycle with write_audit — lazy import where needed; see follow-up. Spec §9 no refactor.
    from shenbi.audit.write_audit import AuditResult
```
替换为（类型注解环消失，改指 `_shared`）：
```python
if TYPE_CHECKING:
    from shenbi.audit._shared import AuditResult
```
> `record.py:24` 的 `result: AuditResult` 注解在 `from __future__ import annotations` 下是字符串，TYPE_CHECKING import 足够，**不要**加运行时 import（会重建环）。

- [ ] **Step 5: 跑回归测试**（V6 Cluster 2）

Run:
```bash
uv run pytest tests/unit/test_dispatcher_executor.py tests/unit/audit/test_record.py -v
```
Expected: 全绿。`test_dispatcher_executor.py` 覆盖 `derive_output_files`（L13 import）；`test_record.py` 覆盖 `write_audit.AuditResult`（L7 import，cycle 内 AuditResult 真实消费者）。

- [ ] **Step 6: 公开 API 核验**（V8）

Run:
```bash
uv run python -c "from shenbi.audit import AuditResult; print(AuditResult)"
uv run python -c "from shenbi.dispatcher.executor import derive_output_files; print(derive_output_files)"
uv run python -c "from shenbi.audit.write_audit import AuditResult; print(AuditResult)"
```
Expected: 3 行均打印类对象（无 ImportError）。

- [ ] **Step 7: lint + cyclic 注释核查**（V3/V7 Cluster 2）

Run:
```bash
uv run ruff check src/shenbi/audit/_shared.py src/shenbi/dispatcher/executor.py src/shenbi/audit/write_audit.py src/shenbi/audit/record.py
grep -rn "py/cyclic-import" src/shenbi/
```
Expected: ruff 全绿；grep 返回空（Cluster 1 + 2 共 10 条 cyclic 注释全删）。

- [ ] **Step 8: DAG 核验**

Run:
```bash
uv run python -c "import shenbi.dispatcher.executor, shenbi.audit.write_audit, shenbi.audit.record, shenbi.audit._shared, shenbi.phase_runner; print('Cluster 2 imports OK')"
```
Expected: 打印 `Cluster 2 imports OK`。

- [ ] **Step 9: Commit**

```bash
git add src/shenbi/audit/_shared.py src/shenbi/dispatcher/executor.py src/shenbi/audit/write_audit.py src/shenbi/audit/record.py
git commit -m "refactor(audit): extract derive_output_files + AuditResult to _shared — break Cluster 2 cycle (4/10 py/cyclic-import)

- new audit/_shared.py: derive_output_files, AuditResult (leaf module, only
  imports shenbi.contracts.*)
- executor.py: re-export derive_output_files (MANDATORY: phase_runner.py:190 +
  write_audit.py:31 + test anchor + self-call L218/L245)
- write_audit.py: re-export AuditResult (public API via __init__.py:8 +
  test_record.py:7); _declared_patterns back-edge → _shared
- record.py: TYPE_CHECKING import → _shared (no runtime import, preserves
  string annotation under from __future__ import annotations)
- delete 4 py/cyclic-import suppression comments
- behavior unchanged (pure relocation)

Spec: docs/superpowers/specs/2026-08-02-issue24-cyclic-import-refactor-design.md §3.3"
```

---

## Task 3: 删除 `write_truth_file` vacuous re-export（第 11 条告警）

**复杂度:** infra（改测试断言结构）→ 协调者亲自实现

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（删 L53-57 re-export 块）
- Modify: `tests/unit/pipeline/test_dispatch_write_semantics.py`（删 vacuous `patch(...)` 块，保留正面断言）
- Test（回归网）: `tests/unit/pipeline/test_dispatch_write_semantics.py`

**Interfaces:**
- Consumes: 无
- Produces: 无（纯删除）

- [ ] **Step 1: 改 `src/shenbi/pipeline/dispatch_helper.py`**——删 L53-57 整块（4 行解释注释 + 1 行 re-export）。

删除（原 L53-57）：
```python
# write_truth_file is imported so tests can verify it is NOT routed through
# the generic dispatch write path. Truth-file upsert is the state-settling
# skill's (caller's) responsibility (the state-settling skill calls
# write_truth_file directly with a real key).
from shenbi.pipeline.truth_io import write_truth_file  # noqa: F401  # pyright: ignore[reportUnusedImport]
```
> 前置确认（spec §3.4 Phase 1 已核实）：`grep -n "write_truth_file" dispatch_helper.py` 返回 4 hit——L57（本 re-export）+ L1034/L1137/L1214（docstring/comment 文本，非可执行调用）。运行时零调用，删除安全。

- [ ] **Step 2: 改 `tests/unit/pipeline/test_dispatch_write_semantics.py`**——`TestAppendDedupNotRoutedInDispatch.test_append_dedup_truth_file_is_written_whole_not_upserted`（L37-58）删 vacuous `patch(...)` 块，保留正面断言。

L37-58 区块替换为：
```python
    def test_append_dedup_truth_file_is_written_whole_not_upserted(self, tmp_path: Path):
        """A truth/ path declared mode: append_dedup is written as a whole file
        by _write_parsed_outputs (safe_write), NOT routed to write_truth_file.
        Upsert is the caller's (state-settling skill's) responsibility.
        """
        truth = tmp_path / "truth" / "current_state.md"
        truth.parent.mkdir(parents=True)
        truth.write_text("# Current State\n\n- chapter: ch0\n", encoding="utf-8")

        out = _write_parsed_outputs(
            response="### FILE: truth/current_state.md\nrow\n",
            output_paths=["truth/current_state.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )
        # The file is written whole via safe_write (write_truth_file is not
        # routed through the dispatch path — verified by the whole-file content).
        assert "truth/current_state.md" in out
        assert (tmp_path / "truth" / "current_state.md").read_text() == "row"
```
> 删除内容：`with patch("shenbi.pipeline.dispatch_helper.write_truth_file") as mock_wtf:` + `mock_wtf.return_value = None` 包裹层 + 缩进 + `mock_wtf.assert_not_called()`。该 patch 本就是 vacuous negative-assertion（`_write_parsed_outputs` 从不调 `write_truth_file`，patch 拦截的符号永不分发）。改后测试仍验证真实信号（whole-file 写入经 safe_write，L57-58 断言）。
> **同步删顶部 `from unittest.mock import patch`（L6）**（已 grep 确认：本文件仅 L46 用 `patch`，删 with 块后无其他引用——L15/26/27/34/54 是注释/字符串，非调用）。

- [ ] **Step 3: 跑回归测试**（V6 第 11 条）

Run:
```bash
uv run pytest tests/unit/pipeline/test_dispatch_write_semantics.py -v
```
Expected: 全绿（test_append_dedup 仍 pass，正面断言 whole-file 写入成立）。

- [ ] **Step 4: lint + re-export 核查**

Run:
```bash
uv run ruff check src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_write_semantics.py
grep -n "import.*write_truth_file" src/shenbi/pipeline/dispatch_helper.py
```
Expected: ruff 全绿；grep 返回空（re-export 行已删；docstring/comment 文本提及不在 grep 模式内）。

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_write_semantics.py
git commit -m "refactor(dispatch_helper): remove write_truth_file vacuous re-export (1/1 py/unused-import)

- delete L53-57 re-export block (write_truth_file had zero runtime calls in
  dispatch_helper — only L1034/L1137/L1214 docstring/comment mentions)
- test_dispatch_write_semantics: delete vacuous patch() negative-assertion
  block (patched a symbol that was never dispatched); keep positive whole-file
  write assertions (real signal via safe_write)
- behavior unchanged; CodeQL py/unused-import on dispatch_helper.py:57 → 0

Spec: docs/superpowers/specs/2026-08-02-issue24-cyclic-import-refactor-design.md §3.4"
```

---

## 全量验证（Phase 6，3 task 全 commit 后）

- [ ] `just check` 全绿，测试数 ≥2787 passed + 4 last-marked，coverage ≥85.03%（V1/V2）
- [ ] `ls .superpowers/sdd/audit-T*.md | wc -l` == 3（T1/T2/T3 各一，阶段 5 每_task 后产出）
- [ ] `grep -rn "py/cyclic-import" src/shenbi/` 返回空（V3）
- [ ] `uv run python -c "from shenbi.audit import AuditResult; from shenbi.pipeline.triggers import read_volume_boundaries; from shenbi.dispatcher.executor import derive_output_files; print('public API stable')"`（V8 + re-export 守护）

## Self-Review

**Spec coverage:** §3.2（Cluster 1）→ T1；§3.3（Cluster 2）→ T2；§3.4（第 11 条）→ T3；§4 四 Phase → T1/T2/T3 + Phase 6；§5 V1-V8 → AC 覆盖表 + 各 task 验证步；§6.1 命名（`_shared.py` Option A）→ 已定；§6.2 re-export（两 `_`-前缀符号 Option A 保留）→ T1 Step 2 re-export 含 `_BRIDGE_ACTIVATION_WINDOW`/`_resolve_volume_at_runtime`；§6.3（Option A）→ T3；§6.4（单 PR）→ Phase 8。无遗漏。

**Placeholder scan:** 无 TBD/TODO；每步含实际代码或实际命令 + expected output。grep 确认项（`re` import、`dataclass` import、`patch` import）已标注"grep 确认后再定"，非占位符而是 conditional lint 决策。

**Type consistency:** `read_volume_boundaries(project_dir: Path | str) -> set[int]`（T1 `_shared` 定义 + triggers.py re-export 一致）；`_resolve_volume_at_runtime(project_dir: Path, chapter: int) -> tuple[str, int, int] | None`（T1 一致）；`derive_output_files(skill: str, chapter: int | None = None, round_dir: Path | None = None) -> list[str]`（T2 `_shared` 定义 + executor.py re-export 一致）；`AuditResult`（frozen dataclass 4 字段，T2 `_shared` 定义 + write_audit.py re-export + record.py TYPE_CHECKING 一致）。
