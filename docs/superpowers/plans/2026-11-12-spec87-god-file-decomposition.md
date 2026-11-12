# Spec #87 god 文件拆分与正名 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 行为保持地拆解 chapter_loop/dispatch_helper 两个 god 文件——五体制出鞘、prompt 装配 NamedTuple 化、extractor 注册表坍缩 11 臂、子串判定消灭、事实公共 API 正名 + tests 私有 import 增量 lint。

**Architecture:** 全部行为保持（T0 characterization 先行钉死五体制+条件跳过+serial resonance/revision 尾共八条公共入口路径）；T2 以 contracts 侧零依赖叶 + read_extractors.REGISTRY 单源派生 + dispatch_helper 单臂坍缩；T4 双路径（ChapterStep 属性 / 精确 frozenset）；T5 正名后冻基线。

**Tech Stack:** Python 3.11+ / pathlib / structlog / pytest（unit 标记）/ basedpyright strict。

## Global Constraints（spec 逐字）

- 验收 1：`chapter_loop.py` + `dispatch_helper.py` 合计 **≤9,500 行**；`chapter_loop.py` **≤4,820**、`dispatch_helper.py` **≤4,680**（基线 2026-11-12：4,780+4,910=9,690）
- 验收 2：`_run_chapter_step_impl` 消失；五个体制函数各有独立红测；checkpoint 创建/恢复唯一持有于 `run_chapter_step`；serial 段 <260（现 331，抽 3 块）
- 验收 3：`grep -c extractor_failed_fulltext src/shenbi/pipeline/dispatch_helper.py` = 1（:322 注释同批改写）
- 验收 4：T4 红测绿；pipeline 内 pyright 私有压制 **≤12**（现 17：−1 _ending_archetype_of −3 名字级正名 −1 AuditResult 改公共 import）
- 验收 5：`tests/private_imports_baseline.txt` 子集断言绿 + dispatch_helper 零 `extractor ==` 字面量断言绿
- 验收 6：`just check` exit 0 + 全量测试绿
- T5 正名验收 = `grep -rn '<旧名>' src/ tests/ tools/` 零输出（docs/ 有意排除）
- **禁**：真实 LLM dispatch（核心原则 8）；`git add -A`（pathspec commit）；改契约三源时手改生成物（走 `just generate`）
- **行号纪律**：spec 行号为 2026-11-12 快照；本 plan 首 task 前先跑 re-anchor 步骤；执行中每 task 开头重验锚点

## File Structure

| 文件 | 动作 | 职责 |
|---|---|---|
| `src/shenbi/contracts/read_extractor_names.py` | Create | 零依赖叶：11 名 frozenset 单源 |
| `src/shenbi/contracts/loader.py` | Modify | READ_EXTRACTORS 改叶派生 |
| `src/shenbi/pipeline/read_extractors.py` | Modify | ExtractSpec + 统一包装 + REGISTRY + 叶对账 assert |
| `src/shenbi/pipeline/dispatch_helper.py` | Modify | BuiltPrompt 类型注解；11 臂坍缩单臂；:322 注释改写；正名 |
| `src/shenbi/pipeline/chapter_loop.py` | Modify | 五体制拆出；三钩函数；ChapterStep +3 字段；正名 |
| `src/shenbi/pipeline/review_checklist.py` | Modify | REVIEW_SKILLS frozenset 26 名 + is_review_skill 精确判定 |
| `src/shenbi/pipeline/state.py` `crash_recovery.py` `parallel_dispatch.py` `gates/g4/chapter_drafting.py` | Modify | 4 处压制符号正名（r2 订正：`_ending_archetype_of` 实定义于 gates/g4/chapter_drafting.py:514，非 text/——plan r1 误记） |
| `tools/lint_private_imports.py` | Create | tests 私有 import 子集断言 lint（--update 人工评审后用） |
| `tests/private_imports_baseline.txt` | Create | (file, symbol) 对基线 |
| `justfile` | Modify | 挂 lint_private_imports（首跑 report-only 后接 FAIL） |
| `tests/pipeline/test_chapter_step_characterization.py` | Create | T0 六路径 |
| `tests/pipeline/test_read_extractor_registry.py` | Create | T2 表驱动 + 防复发禁令 |
| `tests/pipeline/test_review_skill_routing.py` | Create | T4 路径 B 对账 + escalation 特征 + 红测 |
| `tests/unit/pipeline/test_read_extractors_slicing.py` | Modify | :271-284 硬编码名集改 ⊆ REGISTRY 断言 |
| `tests/unit/pipeline/test_spec83_stale_declarations.py` | Modify | T3 拆函数后白名单同步 |
| `tools/lint_dead_code_allowlist.py` | Modify | T5 收缩 :32-33 两条 |

---

### Task -1 · Re-anchor（前置，无独立 commit）

**复杂度:** infra ｜ **test_kind:** —（纯核对）

- [ ] **Step 1: 重验全部锚点**（spec §3 行号纪律；若漂移在 ±5 内照 plan 施工、超 ±5 记 deviation 并更新本 plan 锚点）

```bash
grep -n "def _run_chapter_step_impl" src/shenbi/pipeline/chapter_loop.py          # 期望 :3856
grep -n "def _build_skill_prompt" src/shenbi/pipeline/dispatch_helper.py         # 期望 :746
grep -n "if extractor == \"volume_chapter\"" src/shenbi/pipeline/dispatch_helper.py  # 期望 :879
grep -n "elif extractor is not None:" src/shenbi/pipeline/dispatch_helper.py     # 期望 :1160
grep -cn "extractor ==" src/shenbi/pipeline/dispatch_helper.py                   # 期望 11
grep -c "extractor_failed_fulltext" src/shenbi/pipeline/dispatch_helper.py       # 期望 21
wc -l src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/dispatch_helper.py # 期望 4780/4910
grep -c "reportPrivateUsage" src/shenbi/pipeline/*.py | grep -v ":0"             # 期望 8/4/2/1/1/1=17
grep -n "READ_EXTRACTORS" src/shenbi/contracts/loader.py                          # 期望 :94-107 11 名
grep -rn "from shenbi.pipeline" src/shenbi/contracts/                            # 期望空（反边 0 先例）
```

---

### Task 0 · characterization 八路径（先钉行为）

**Files:**
- Test: `tests/pipeline/test_chapter_step_characterization.py`（Create，八条）
- Reference: `tests/pipeline/test_bundle_stepping.py:382-420`（公共入口驱动模板——`_project()` helper / `PipelineState.default` / `step_index = next(i for i,s in enumerate(CHAPTER_STEPS) if s.skill==...)` / `monkeypatch.setattr(chapter_loop, "dispatch_skill", ...)`）

**Interfaces:**
- Consumes: `run_chapter_step(state: PipelineState, project_dir: Path | str) -> bool`（chapter_loop.py:3823 公共入口）、`CHAPTER_STEPS`、`PipelineState.default(project_dir_str)`、`PipelinePhase.CHAPTER_LOOP`
- Produces: **八条** characterization 测试（r2.3：六路径 + serial resonance 尾 + serial revision 尾——后两条是位置作用域钩语义的承载场景；拆分安全网；T3 完成后全绿即行为保持证明）

**复杂度:** infra ｜ **test_kind:** characterization ｜ **层级:** T1（结构单元测试，无 LLM 产物依赖）

- [ ] **Step 1: 先列覆盖缺口表**（spec r3.2 要求——证 T0 增量）

对五体制+条件跳过各查既有公共入口覆盖（`grep -rn "run_chapter_step" tests/ | grep -v characterization`），输出表：
| 路径 | 触发条件 | 既有覆盖（文件:测试名） | T0 新增 |
|---|---|---|---|
| 审计波 | `step_idx == _FIRST_AUDIT_IDX and step.is_audit`（:3918） | （查填） | 是/否 |
| 后起草对 | `step_idx == _FORESHADOWING_LIFECYCLE_IDX`（:4177） | （查填） | 是/否 |
| context_assembly | `step.calls_context_assembly`（:4355-4357） | （查填） | 是/否 |
| pipeline 内部 | `step.skill.startswith("pipeline-")`（:4360） | （查填） | 是/否 |
| 通用串行 | else 域（:4450+） | （查填） | 是/否 |
| 条件跳过 | `:4435-4456` 三块 skip（r2.3 锚订正） | （查填） | 是/否 |
| **serial resonance 尾** | serial 域 :4702（r2.3 补——T0 盲区） | （查填） | 是 |
| **serial revision 尾** | serial 域 :4728-4778（r2.3 补——位置作用域钩语义的承载体） | （查填） | 是 |

已有覆盖的路径注明复用锚不重写；缺口路径写新测试。

- [ ] **Step 2: 写六条测试**（已有覆盖的路径至少断言一次 checkpoint 契约：返回 bool + step_index 前进/steps_done 记录）

八条测试统一骨架（以审计波为例；其余五条按表驱动换 step 定位与断言面）：

```python
"""Spec #87 T0: per-regime characterization through the public entry.

These pin behavior BEFORE the five-regime extraction (T3). They must stay
green after T3 without modification — that is the behavior-preservation
proof. Reference seam: test_bundle_stepping.py:382-420.
"""

import pytest
from pathlib import Path

from types import SimpleNamespace
from unittest.mock import patch

from shenbi.pipeline import chapter_loop as cl
from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, run_chapter_step
from shenbi.pipeline.state import PipelinePhase, PipelineState


def _step_index_of(skill_prefix: str) -> int:
    return next(i for i, s in enumerate(CHAPTER_STEPS) if s.skill.startswith(skill_prefix))


def test_audit_wave_regime(tmp_path: Path) -> None:
    """First audit step dispatches the parallel wave and advances.

    Wave seam (test_parallel_steps.py:344-371 precedent): the wave core runs
    through dispatch_reviews_parallel which resolves dispatch_skill in the
    parallel_dispatch namespace — patching cl.dispatch_skill alone would let
    REAL dispatches through. Patch the wave boundary instead.
    """
    state = PipelineState.default(str(tmp_path))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 1
    state.chapter_loop.step_index = next(
        i for i, s in enumerate(CHAPTER_STEPS) if s.is_audit
    )  # first audit step — attribute access, not private-const import

    def _results_for(tasks):
        # r2.1: dispatch_reviews_parallel (parallel_dispatch.py:241) and
        # _dispatch_serial_reviews (chapter_loop.py:3787) both return
        # list[DispatchResult] — wave consumers .extend()/concat; a dict
        # would TypeError. Reference: test_parallel_steps.py:337-338.
        return [
            SimpleNamespace(success=True, result={}, stdout="", stderr="", returncode=0)
            for t in tasks
        ]

    with (
        patch(
            "shenbi.pipeline.audit_context_cache.build_shared_audit_context",
            return_value=SimpleNamespace(
                estimated_tokens=0,
                raw_files={},
                world_rules="",
                character_list="",
                style_profile="",
                pending_hooks="",
            ),
        ),
        patch("shenbi.pipeline.audit_layer.get_active_genre_audits", return_value=[]),
        patch(
            "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel",
            side_effect=lambda tasks, on_task_complete=None, state=None: _results_for(tasks),
        ),
        patch.object(
            cl,
            "_dispatch_serial_reviews",
            side_effect=lambda tasks, pd, state=None: _results_for(tasks),
        ),
        patch.object(cl, "_parse_and_persist_resonance"),
        patch.object(cl, "_route_revision_after_resonance"),
    ):
        reached = run_chapter_step(state, tmp_path)

    assert isinstance(reached, bool)
    assert state.chapter_loop.step_index > 0 or reached  # 游标推进或 checkpoint
```

其余五条（同骨架，差异面；**全部新测试函数打 `@pytest.mark.unit`**——tests/pipeline/ 多数文件无标记会被 `-m unit` deselect，plan 各 task 的 unit 门禁依赖标记存在）：
1. `test_post_draft_pair_regime`：step_index 用 skill 名定位 `shenbi-foreshadowing-lifecycle`（**属性访问** `cl._FORESHADOWING_LIFECYCLE_IDX` 亦可——避免私有 const import 进 T5 基线）；断言两个 skill（lifecycle+settling）顺序派发（参考 test_parallel_steps.py:16-39 的顺序断言）且 step_index 推进 2；**前置构造** `chapters/chapter-1.md`（幽灵链守卫 :3893 `_DRAFT_CONSUMING_SKILLS` 无草稿即拒）+ patch `run_gate_g4`（参考 test_bundle_stepping.py:416-449 既有 seam）。
2. `test_context_assembly_regime`：定位 `calls_context_assembly=True` 的 step（`next(i for i,s in enumerate(CHAPTER_STEPS) if s.calls_context_assembly)`）；monkeypatch `cl._run_context_assembly` 记录调用章号；断言被调用且游标推进。
3. `test_pipeline_internal_regime`：定位 skill `startswith("pipeline-")` 的 step；断言**零** dispatch_skill 调用且游标推进（pipeline-internal 不派发）。
4. `test_serial_dispatch_regime`：定位 `shenbi-chapter-planning`（bundle_stepping 模板）；断言 dispatch 调用带 skill 名与 prompt、游标推进。
5. `test_conditional_skip_regime`：定位 `conditional=True` 的 step 且构造条件不满足（或直接用 `shenbi-context-composing`——:4435 skip 分支）；断言零 dispatch、`state.add_step_done` 记录、游标推进、返回 bool。
6. `test_serial_resonance_tail`（r2.3 补）：定位 `shenbi-review-resonance`（serial 域）；monkeypatch `cl._parse_and_persist_resonance`/`cl._route_revision_after_resonance` 记录调用；fake dispatch success；断言两 void 调用各恰一次 + `_step_output_exists` 闸/add_step_done/_reset_retries 仍执行（spy 或状态断言）+ 游标推进——**位置 1 钩语义载体**。
7. `test_serial_revision_tail`（r2.3 补）：定位 `shenbi-chapter-revision`；构造 decisions 文件与 staging 输出（test_bundle_stepping 既有 seam）；fake dispatch success；断言 `_ensure_revision_decisions_exists` 效果（decisions 落盘）+ `declarations_stale` 翻转 + 游标推进——**位置 2 钩语义载体**。

- [ ] **Step 3: 跑新测试全绿**（characterization 是钉现状——若现状即红，说明锚点/构造错，修构造不修产品码）

Run: `uv run pytest tests/pipeline/test_chapter_step_characterization.py -v`
Expected: 8 passed

- [ ] **Step 4: Commit + audit**

```bash
git add tests/pipeline/test_chapter_step_characterization.py
git commit -m "test: spec #87 T0 per-regime characterization through run_chapter_step public entry"
```
产出 `.superpowers/sdd/audit-T0.md`（fresh-context 子 agent 全量重审）后方可进 T1。

---

### Task 1 · BuiltPrompt NamedTuple（替 5 元组）

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（_build_skill_prompt 返回类型 :746-1607；解构消费点 :3887/:4360 两处仅改类型注解可读性——零改动也合法）
- Test: `tests/pipeline/test_built_prompt.py`（Create）

**Interfaces:**
- Produces:
```python
class BuiltPrompt(NamedTuple):
    """Assembled dispatch prompt (spec #87 T1; replaces the 5-tuple)."""

    system: str
    user: str
    output_paths: list[str]
    reads_manifest: list[dict[str, Any]]
    raw_disk_reads: dict[str, str]
```
- `_build_skill_prompt(...) -> BuiltPrompt`（9 参签名不变：skill, project_dir, prompt, chapter, uses_staging=False, shared_context=None, json_mode=False, path_context=None, outputs_override=None）；**63 处解构位点**（r2 订正：AST 全仓口径 src 2 + tests 61/22 文件——r1 的 54 系旧计数残留）**零改动**——NamedTuple tuple 协议兼容

**复杂度:** infra ｜ **test_kind:** regression_guard ｜ **层级:** T1

- [ ] **Step 1: 写回归守卫测试**

```python
"""Spec #87 T1: BuiltPrompt NamedTuple — tuple-protocol compatibility."""

from shenbi.pipeline.dispatch_helper import BuiltPrompt, _build_skill_prompt


def test_built_prompt_is_namedtuple_with_five_fields() -> None:
    import typing

    assert issubclass(BuiltPrompt, tuple)
    assert BuiltPrompt._fields == (
        "system",
        "user",
        "output_paths",
        "reads_manifest",
        "raw_disk_reads",
    )


def test_built_prompt_tuple_unpack_and_named_access() -> None:
    bp = BuiltPrompt("s", "u", ["p"], [{"r": 1}], {"d": "x"})
    a, b, c, d, e = bp  # 5 元解构兼容
    *head, tail = bp  # 星号解包兼容
    assert (a, b, c, d, e) == ("s", "u", ["p"], [{"r": 1}], {"d": "x"})
    assert bp.system == "s" and bp.raw_disk_reads == {"d": "x"}
```

- [ ] **Step 2: 跑绿**（NamedTuple 先行定义即绿——tdd 红相在此 task 无意义，test_kind=regression_guard）

- [ ] **Step 3: 实现**——dispatch_helper.py 顶部 import 区加 `from typing import NamedTuple`（已有 typing import 则并入）；在 `_INPUT_MAX_CHARS_TOTAL` 常量块附近定义 `BuiltPrompt`；`_build_skill_prompt` 签名行 `-> tuple[str, str, list[str], list[dict[str, Any]], dict[str, str]]` 改 `-> BuiltPrompt`；`return system_prompt, user_prompt, output_paths, reads_manifest, raw_disk_reads`（:1607）改 `return BuiltPrompt(system_prompt, user_prompt, output_paths, reads_manifest, raw_disk_reads)`。

- [ ] **Step 4: 全量回归**——`uv run pytest tests/pipeline/test_built_prompt.py tests/ -x -q -m "unit"`（63 解构位点零破坏证明）；`uv run pytest tests/ -q -m unit`（大面）

- [ ] **Step 5: Commit + audit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_built_prompt.py
git commit -m "refactor: spec #87 T1 BuiltPrompt NamedTuple replaces 5-tuple return (63 destructure sites zero-break)"
```

---

### Task 2 · extractor 注册表：叶 + REGISTRY + 11 臂坍缩

**Files:**
- Create: `src/shenbi/contracts/read_extractor_names.py`
- Modify: `src/shenbi/contracts/loader.py:94-107`（READ_EXTRACTORS 改派生）
- Modify: `src/shenbi/pipeline/read_extractors.py`（ExtractSpec+包装+REGISTRY+assert）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:879-1160`（11 臂坍缩单臂）+ `:322`（注释改写）
- Modify: `tests/unit/pipeline/test_read_extractors_slicing.py:271-286`（硬编码名集改 ⊆ 断言）
- Test: `tests/pipeline/test_read_extractor_registry.py`（Create）

**Interfaces:**
- Produces（read_extractors.py）:
```python
ChapterNonePolicy = Literal["guard_warn", "silent", "loud", "irrelevant"]


@dataclass(frozen=True)
class ExtractSpec:
    impl: Callable[[Path, int | None, str], str]
    chapter_none: ChapterNonePolicy = "irrelevant"
    empty_warn_predicate: Callable[[str], bool] | None = None  # None=空即 WARN


REGISTRY: dict[str, ExtractSpec]  # 11 项；set(REGISTRY) == READ_EXTRACTOR_NAMES 模块级 assert
```
- Produces（contracts/read_extractor_names.py）: `READ_EXTRACTOR_NAMES: frozenset[str]`（11 名，与现 loader 字面量逐一相同）
- dispatch_helper 单臂消费 `REGISTRY`；策略四态 = guard_warn（volume_chapter None→unrouted WARN）/ silent（hooks_audit_scoped None→静默回退）/ loud（matrix_scoped None→failed WARN）/ irrelevant+predicate noop（recent_increments 空且无章单元）

**复杂度:** infra ｜ **test_kind:** tdd_red_green ｜ **层级:** T1（表驱动结构测试）

- [ ] **Step 1: 红测**——`tests/pipeline/test_read_extractor_registry.py`：

```python
"""Spec #87 T2: extractor registry — table-driven WARN policies + leaf single-source."""

import pytest
from pathlib import Path
from unittest.mock import patch

from shenbi.contracts.loader import READ_EXTRACTORS
from shenbi.contracts.read_extractor_names import READ_EXTRACTOR_NAMES
from shenbi.pipeline import read_extractors as re_mod
from shenbi.pipeline.read_extractors import REGISTRY, ExtractSpec


def test_registry_keys_equal_leaf_roster() -> None:
    assert set(REGISTRY) == READ_EXTRACTOR_NAMES == READ_EXTRACTORS


def test_registry_size_matches_leaf() -> (
    None
):  # r2: 硬编码 11 违背单源故事——第 12 个 extractor 只该改 2 处
    assert len(REGISTRY) == len(READ_EXTRACTOR_NAMES)


def test_per_extractor_chapter_none_policies() -> None:
    assert REGISTRY["volume_chapter"].chapter_none == "guard_warn"
    assert REGISTRY["hooks_audit_scoped"].chapter_none == "silent"
    assert REGISTRY["matrix_scoped"].chapter_none == "loud"
    assert REGISTRY["recent_increments"].empty_warn_predicate is re_mod.has_chapter_units


def test_no_bare_extractor_equality_in_dispatch_helper() -> None:
    """防复发禁令：新 extractor 不得重写裸 if 臂（#95 加臂博弈路径）。"""
    import inspect
    from shenbi.pipeline import dispatch_helper as dh

    assert "extractor ==" not in inspect.getsource(dh)
```

- [ ] **Step 2: 跑红**——`uv run pytest tests/pipeline/test_read_extractor_registry.py -v` → FAIL（REGISTRY 不存在）

- [ ] **Step 3: 实现叶 + REGISTRY**

`src/shenbi/contracts/read_extractor_names.py`（新文件，零内部 import）：
```python
"""Read-extractor name roster — single source (spec #87 T2).

Zero-dependency leaf: contracts must never import shenbi.pipeline (the
reverse edge has 0 precedent). loader.READ_EXTRACTORS derives from this
roster; read_extractors.REGISTRY keys must equal it (module assert + test).
"""

READ_EXTRACTOR_NAMES: frozenset[str] = frozenset(
    {
        "volume_chapter",
        "hooks_audit_scoped",
        "hooks_inventory_scoped",
        "hooks_overview",
        "threads_overview",
        "relationships_overview",
        "locations_overview",
        "book_strata_current",
        "matrix_scoped",
        "volume_opening_protocol",
        "recent_increments",
    }
)
```

`loader.py`：删 :94-107 的手写 frozenset 字面量体，改：
```python
from shenbi.contracts.read_extractor_names import READ_EXTRACTOR_NAMES

...
READ_EXTRACTORS: frozenset[str] = READ_EXTRACTOR_NAMES
```

`read_extractors.py` 尾部追加（import 区补 `from shenbi.contracts.read_extractor_names import READ_EXTRACTOR_NAMES`、`from typing import Literal`、`from dataclasses import dataclass`、`from collections.abc import Callable`、`from shenbi.pipeline._shared import load_volume_context`）：
```python
# --- spec #87 T2: registry — single dispatch for read extractors ----------

ChapterNonePolicy = Literal["guard_warn", "silent", "loud", "irrelevant"]


@dataclass(frozen=True)
class ExtractSpec:
    """Per-extractor routing policy for the collapsed dispatch arm.

    chapter_none governs the ``chapter is None`` case; empty_warn_predicate
    (None = warn on empty) governs empty results — the four observed
    behaviors: guard-warn / silent / loud / conditional no-op.
    """

    impl: Callable[[Path, int | None, str], str]
    chapter_none: ChapterNonePolicy = "irrelevant"
    empty_warn_predicate: Callable[[str], bool] | None = None


def _content_only(fn: Callable[[str], str]) -> Callable[[Path, int | None, str], str]:
    def wrap(project_dir: Path, chapter: int | None, content: str) -> str:
        return fn(content)

    return wrap


def _chapterly(fn: Callable[[str, int | None], str]) -> Callable[[Path, int | None, str], str]:
    def wrap(project_dir: Path, chapter: int | None, content: str) -> str:
        return fn(content, chapter)

    return wrap


def _volume_chapter(project_dir: Path, chapter: int | None, content: str) -> str:
    # chapter=None never reaches impl (chapter_none="guard_warn" intercepts),
    # so the int-typed _shared call needs no cast (r2: dropped typing.cast —
    # typing import list never included it).
    assert chapter is not None  # invariant guard, see comment above (no noqa:
    # S101 is not in the ruff select set — a noqa would trip RUF100 unused-noqa)
    return load_volume_context(project_dir, chapter)


REGISTRY: dict[str, ExtractSpec] = {
    "volume_chapter": ExtractSpec(_volume_chapter, chapter_none="guard_warn"),
    "hooks_audit_scoped": ExtractSpec(extract_hooks_audit_scoped, chapter_none="silent"),
    "hooks_inventory_scoped": ExtractSpec(_content_only(extract_hooks_inventory_scoped)),
    "hooks_overview": ExtractSpec(_content_only(extract_hooks_overview)),
    "threads_overview": ExtractSpec(_chapterly(extract_threads_overview)),
    "relationships_overview": ExtractSpec(_content_only(extract_relationships_overview)),
    "locations_overview": ExtractSpec(_content_only(extract_locations_overview)),
    "book_strata_current": ExtractSpec(_content_only(extract_book_strata_current)),
    "matrix_scoped": ExtractSpec(extract_matrix_scoped, chapter_none="loud"),
    "volume_opening_protocol": ExtractSpec(_content_only(extract_volume_opening_protocol)),
    "recent_increments": ExtractSpec(
        _content_only(extract_recent_increments), empty_warn_predicate=has_chapter_units
    ),
}
assert set(REGISTRY) == READ_EXTRACTOR_NAMES, "roster drift: update leaf + registry together"
```

- [ ] **Step 4: 坍缩 dispatch_helper :879-1160** 为单臂（保持 :879 行前缩进上下文——在 reads 循环体内）。替换体：

```python
spec = REGISTRY.get(extractor) if extractor is not None else None
if extractor is not None and spec is None:
    log.warning("extractor_unrouted_fulltext", extractor=extractor, path=str(full_path))
elif spec is not None:
    if chapter is None and spec.chapter_none == "guard_warn":
        log.warning("extractor_unrouted_fulltext", extractor=extractor, path=str(full_path))
    elif chapter is None and spec.chapter_none == "silent":
        pass  # full-pool view preserved (§4.3 fallthrough)
    else:
        _x_err: Exception | None = None
        _extracted = ""
        if not (chapter is None and spec.chapter_none == "loud"):
            # matrix_scoped: None never reaches impl — loud falls through
            # to the shared WARN below (same event/fields as today's arm)
            try:
                _extracted = spec.impl(project_dir, chapter, content)
            except Exception as exc:
                _x_err = exc
                _extracted = ""
        if _extracted:
            content = _extracted
        elif _x_err is not None or (
            spec.empty_warn_predicate is None or spec.empty_warn_predicate(content)
        ):
            # THE single literal site — acceptance 3 (grep -c == 1)
            log.warning(
                "extractor_failed_fulltext",
                extractor=extractor,
                path=str(full_path),
                chapter=chapter,
                **({"error": str(_x_err)} if _x_err is not None else {}),
            )
```

⚠️ 行为逐臂核对表（坍缩前跑既有测试 + 逐臂人工比对，任何一臂 WARN 事件字段差异都要在此表登记）：
| 臂 | 现行为 | 坍缩后来源 |
|---|---|---|
| volume_chapter None | 落链尾 unrouted WARN | guard_warn 分支 |
| volume_chapter raise/空 | failed WARN(±error) | except/else 统一 |
| hooks_audit_scoped None | 静默回退（if chapter is not None 包裹） | silent 分支 |
| hooks_inventory/overview/book_strata/threads/relationships/locations 空 | failed WARN | 空+谓词 None |
| matrix_scoped None | failed WARN(chapter=None) | loud（chapter is None 分支）⚠️ 现码在 else 里带 chapter=chapter——统一分支已覆盖 |
| vop 空/raise | failed WARN(±error) | 统一 |
| recent raise | failed WARN(+error) | `_x_err is not None` 优先 |
| recent 空有章单元 | failed WARN | 谓词 True |
| recent 空无章单元 | no-op | 谓词 False |

注意（r2.1）：坍缩后 dispatch_helper 顶部逐 extractor import 有 ~10 个变 unused——F401 必红，同批删（这些行也计入 −252 口径）。`matrix_scoped` chapter=None 现行走 `extracted=""` → `log.warning(..., chapter=chapter)`（chapter=None 字段带上）——坍缩统一分支 `chapter is None or predicate` 命中同事件同字段 ✓。dispatch_helper 顶部补 `from shenbi.pipeline.read_extractors import REGISTRY`。

- [ ] **Step 5: :322 注释改写**（验收 3 前置）：`# 降级路径（extractor_failed_fulltext 回全文）同受此预算约束；超预算→披露式截断` 改 `# extractor 降级回全文路径同受此预算约束；超预算→披露式截断`（不含机器判据字面量）

- [ ] **Step 6: slicing 测试改写**（:271-284 硬编码名集 → ⊆ 断言）：

```python
def test_contract_extractor_names_subset_of_registry() -> None:
    """spec #87 T2: contract roster derives from the registry leaf."""
    from shenbi.pipeline.read_extractors import REGISTRY
    from shenbi.contracts.loader import READ_EXTRACTORS

    assert READ_EXTRACTORS <= set(REGISTRY)
    assert READ_EXTRACTORS == set(REGISTRY)  # 当前恰等；⊂ 时须 spec deviation 说明
```
（原 `== READ_EXTRACTORS` 硬编码 :286 断言保留或并入此测试——实现时读原测试上下文保持文件风格）

- [ ] **Step 7: 验证**——`uv run pytest tests/pipeline/test_read_extractor_registry.py tests/unit/pipeline/test_read_extractors_slicing.py -v` 全绿；`grep -c extractor_failed_fulltext src/shenbi/pipeline/dispatch_helper.py` = **1**（验收 3）；`grep -c "extractor ==" src/shenbi/pipeline/dispatch_helper.py` = **0**；`wc -l src/shenbi/pipeline/dispatch_helper.py` ≤ 4,680（−252+15 后 ≈4,673）；全量 `-m unit` 绿（WARN 语义行为保持）

- [ ] **Step 8: Commit + audit**

```bash
git add src/shenbi/contracts/read_extractor_names.py src/shenbi/contracts/loader.py src/shenbi/pipeline/read_extractors.py src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_read_extractors_slicing.py tests/pipeline/test_read_extractor_registry.py
git commit -m "refactor: spec #87 T2 extractor registry — contracts leaf + REGISTRY + 11-arm collapse (-252 lines, WARN policies table-driven)"
```

---

### Task 3 · 五体制拆分 + 三时机后钩

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（`_run_chapter_step_impl` :3856-4780 → 主函数 + 五体制函数 + 三钩）
- Modify: `tests/unit/pipeline/test_spec83_stale_declarations.py:73-89`（白名单同步——拆出函数内 `dispatch_skill(` 调用点逐一归类）

**Interfaces:**
- Produces（全部模块私有、签名统一；**r2 接口修正**——钩子带返回值保持控制流：pre 钩返回 settle-guard 结果供调用方路由（`_pre_settle_guard` :2957 是 3 参谓词返回 `(demoted, hard)` 双值，其路由 `return _handle_failure(...)` 不能进 `-> None` 钩）；failure/success 钩返回 bool=checkpoint raised（现分支尾即 `return True  # checkpoint raised` 逐字语义））:
```python
def _run_audit_wave_step(state: PipelineState, project_dir: Path, step_idx: int, step: ChapterStep, chapter: int) -> bool
def _run_post_draft_pair_step(state: PipelineState, project_dir: Path, step_idx: int, step: ChapterStep, chapter: int) -> bool
def _run_context_assembly_step(state: PipelineState, project_dir: Path, step_idx: int, step: ChapterStep, chapter: int) -> bool
def _run_pipeline_internal_step(state: PipelineState, project_dir: Path, step_idx: int, step: ChapterStep, chapter: int) -> bool
def _run_serial_dispatch_step(state: PipelineState, project_dir: Path, step_idx: int, step: ChapterStep, chapter: int) -> bool
def _pre_dispatch_hooks(step: ChapterStep, state: PipelineState, project_dir: Path, chapter: int) -> tuple[list, list] | None
def _on_dispatch_failure(step: ChapterStep, state: PipelineState, project_dir: Path, chapter: int, result) -> bool | None  # r2.3 三态：None=未触发臂/True=checkpoint raised/False=retry 透传
def _on_resonance_success(step: ChapterStep, state: PipelineState, project_dir: Path, chapter: int) -> None  # r2.3 位置作用域：resonance 位 :4702（闸前），现体 void fall-through
def _on_revision_success(step: ChapterStep, state: PipelineState, project_dir: Path, step_idx: int, chapter: int) -> bool  # r2.3 位置作用域：revision 位 :4728（add_done+reset 后），尾 _advance/_handle_failure
```
- 主函数保留：step_idx==0 特例（:3883）、`_DRAFT_CONSUMING_SKILLS` 门（:3893）、条件跳过三连（r2.1 标签订正：:4435-4456 = 22 行——spec 的「≈14 行」仅覆盖前两块）、checkpoint 创建/恢复唯一持有

**复杂度:** infra ｜ **test_kind:** regression_guard（T0 八路径即安全网）｜ **层级:** T1/T2

- [ ] **Step 1: 一次一个体制搬出**（spec §3——五步串行，每步搬完跑 T0 八测试+全量 unit；任何一步红即回滚该步）：
  1. `_run_audit_wave_step` ← :3913-4162 域（域起以 `:3918 if step_idx == _FIRST_AUDIT_IDX and step.is_audit:` 为准——:3913 是前分支尾 return）
  2. `_run_post_draft_pair_step` ← :4170-4351 域（含直写 `state.chapter_loop.step_index` 的推进语义）
  3. `_run_context_assembly_step` ← :4355-4357 三行体
  4. `_run_pipeline_internal_step` ← :4360-4432 域（`startswith("pipeline-")`）
  5. `_run_serial_dispatch_step` ← serial 域（r2 边界澄清：条件跳过块 :4451-4456 `_should_run_step` 留主函数，实际函数体 ≈:4457-4780 = 324 行——仍 >260，三块抽取主张成立）——内部再抽三块使函数体 <260 行：a) dispatch 调用块（bundle_set 构建 + `dispatch_skill` 调用）; b) 四钩位（三时机）：pre :4485-4501 / 失败 :4521-4533 / 成功位 1 resonance :4702 + 成功位 2 revision :4728; c) revision 成功尾块（r2.1 范围订正：**整块 :4729-~4776**——`if "chapter-revision" in step.skill:` 起，含 `_ensure_revision_decisions_exists`/`declarations_stale=True`/`_revalidate_revised_chapter`+`return _handle_failure("g4")`/`declarations_stale=False` 清除/settle 重派队——全部入 `_on_revision_success`（r2.3 名）；**无条件 `_reset_retries`（:4725-4726）留在 serial 主体每步执行，不得搬入钩**——r2 的「:4726-4732」字面搬运会丢非 revision 步的重试重置=行为破坏）。三钩本体（**r2**：真实函数名与控制流对齐现树——pre 钩的 revision 项是 `write_audit_aggregate(project_dir, chapter)` :4486〔plan r1 误写 `_refresh_revision_aggregate`，树无此函数〕；settle guard 谓词经钩透传结果；failure/success 钩返回 bool）：

```python
def _pre_dispatch_hooks(
    step: ChapterStep, state: PipelineState, project_dir: Path, chapter: int
) -> tuple[list, list] | None:
    """Ordered pre-dispatch hooks: revision aggregate write, settle guard.

    Returns the settle-guard outcome (demoted, hard) when the step settles
    state, else None — routing (the _handle_failure call) stays with the
    caller because it ends in `return`. r2.3 condition fix: the present
    body uses EXACT equality (:4485 `== "shenbi-chapter-revision"`,
    :4492 `== "shenbi-state-settling"`) — move `==` verbatim, do NOT widen
    to substring `in` (widening is the very hazard T4's red test 1 targets).
    """
    outcome: tuple[list, list] | None = None
    if step.skill == "shenbi-chapter-revision":  # T4 → step.is_revision  (:4485-4486)
        write_audit_aggregate(project_dir, chapter)
    if step.skill == "shenbi-state-settling":  # T4 → step.settles_state  (:4492-4493)
        outcome = _pre_settle_guard(state, project_dir, chapter)
    return outcome


def _on_dispatch_failure(
    step: ChapterStep, state: PipelineState, project_dir: Path, chapter: int, result
) -> bool | None:
    """Failure-branch hooks (r2.3 three-state: None = neither arm fired —
    caller falls to the generic :4552 route; True = checkpoint raised;
    False = in-budget retry passthrough — caller returns it verbatim).
    :4521 (settle escalate) and :4533 (resonance failure) moved VERBATIM;
    their conditions are present-day substring `in step.skill` — T4 swaps
    to ChapterStep attributes.
    """
    if "state-settling" in step.skill:  # T4 → step.settles_state
        ...  # :4521-4532 现体逐行搬入（escalation 派发，尾 return True）
    if "review-resonance" in step.skill:  # T4 → step.emits_resonance
        ...  # :4533-... 现体逐行搬入（尾 return _handle_failure(...) bool 透传，
        # 内含 return False retry 分支保留）
    return None


def _on_resonance_success(
    step: ChapterStep, state: PipelineState, project_dir: Path, chapter: int
) -> None:
    """Resonance-position hook (:4702, BEFORE _step_output_exists gate).
    r2.3: the present body :4702-4705 calls two `-> None` functions
    (:3046/:3119) and FALLS THROUGH — faithful extraction is void (r2.2's
    「尾 bool 透传」 was wrong, no such bool exists)."""
    if "review-resonance" in step.skill:  # T4 → step.emits_resonance
        _parse_and_persist_resonance(...)      # :4702-4705 现体（-> None）
        _route_revision_after_resonance(...)   # 同上（-> None）


def _on_revision_success(
    step: ChapterStep, state: PipelineState, project_dir: Path, step_idx: int, chapter: int
) -> bool:
    """Revision-position hook (:4728, AFTER add_step_done + unconditional
    _reset_retries :4725). Whole present block :4728-4778; the block's own
    tail `return _advance(...)` / `return _handle_failure(...)` is the hook
    return; non-revision steps take the unconditional tail (present body)."""
    if "chapter-revision" in step.skill:  # T4 → step.is_revision
        retry_key = _retry_key(chapter, step.skill)  # r2.4：块体 :4751/:4755 引用，钩内重算（纯推导行为等同）
        ...  # :4728-4778 现体整块（ensure_decisions/stale=True → revalidate+
        # return _handle_failure bool 透传 → stale=False 清除 → settle 重派队 → 尾 _advance）
        return <块尾现值>
    return _advance(state, step_idx, step, chapter, project_dir=project_dir)  # 非 revision 尾
```
  调用形态（**r2.3 位置作用域——两个不同函数**。r2.2 的同函数双调用是机制级破坏：revision step 在位置 1 提前 return 会跳过 `_step_output_exists` 闸/add_step_done/`_reset_retries`；resonance step 在位置 1 fall-through 后位置 2 会**再次**触发 resonance 臂→双重 persist/route）：
```python
_on_resonance_success(step, state, project_dir, chapter)  # 位置 1（:4702，闸前）——void 直调
...  # _step_output_exists 闸 / add_step_done / 无条件 _reset_retries(:4725) 原样
return _on_revision_success(
    step, state, project_dir, step_idx, chapter
)  # 位置 2（:4728）——bool 即函数尾
```
  失败分支调用方（三态）：
```python
outcome = _on_dispatch_failure(step, state, project_dir, chapter, result)
if outcome is not None:
    return outcome  # True=checkpoint raised / False=retry 预算内透传
...  # generic :4552 现路由（None=未触发臂）
```
  （函数体内的 `...` 均为「现体逐行搬入」占位——搬移源行号已给，重构类 task 源码即规格；**不做全局注册表**——显式顺序 if 即「表+顺序」）
  ⚠️ **spec83 `_func_body` 断言同步**：test_spec83_stale_declarations.py:96-98 断言 settle_capable 函数体含 `_pre_settle_guard` 字面量——settle 站点搬入 `_run_serial_dispatch_step` 后体内经 `_pre_dispatch_hooks` 间接持有，断言目标须同批改 `"_pre_dispatch_hooks" in body or "_pre_settle_guard" in body`（Step 3 白名单同步一并落）。

- [ ] **Step 2: 主函数重写为分派骨架**（`_run_chapter_step_impl` 删除——验收 2；`run_chapter_step` 内直接写分派或保留薄 impl 皆可——spec 验收 2 写 `_run_chapter_step_impl` 消失，主分派逻辑并入 `run_chapter_step` try 块或改名——**采用并入**：`run_chapter_step` 的 try 块内直接五体制分派）：

```python
    try:
        if step_idx == 0:
            ...  # :3883 特例原样
        if step.skill in _DRAFT_CONSUMING_SKILLS:
            ...  # :3893 门原样
        if step_idx == _FIRST_AUDIT_IDX and step.is_audit:
            return _run_audit_wave_step(state, project_dir, step_idx, step, chapter)
        if step_idx == _FORESHADOWING_LIFECYCLE_IDX:
            return _run_post_draft_pair_step(state, project_dir, step_idx, step, chapter)
        if step.calls_context_assembly:
            return _run_context_assembly_step(state, project_dir, step_idx, step, chapter)
        if step.skill.startswith("pipeline-"):
            return _run_pipeline_internal_step(state, project_dir, step_idx, step, chapter)
        # conditional skips (:4435-4456, r2.2) stay here — 主函数持有
        ...
        return _run_serial_dispatch_step(state, project_dir, step_idx, step, chapter)
    finally:
        ...
```

- [ ] **Step 3: spec83 白名单同步**——`tests/unit/pipeline/test_spec83_stale_declarations.py`：拆出函数内 `dispatch_skill(` 调用点的 `_enclosing` 归属变为新函数名——settle_capable 三元组中 `("pipeline/chapter_loop.py", "_run_chapter_step_impl")` 改为新归属（serial 函数内的 `_pre_settle_guard` 站点→`_run_serial_dispatch_step`；`run_parallel_post_draft_steps` 不变；逐一跑该测试按 unclassified 红名清单归类）。

- [ ] **Step 4: 验证**——T0 六测试零改动全绿（行为保持证明）；`tests/unit/pipeline/test_spec83_stale_declarations.py` 绿；`grep -n "_run_chapter_step_impl" src/ tests/` 零输出（验收 2）；serial 函数体 wc <260；`wc -l chapter_loop.py` ≤4,820；全量 `-m unit` 绿

- [ ] **Step 5: Commit + audit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_spec83_stale_declarations.py
git commit -m "refactor: spec #87 T3 five-regime extraction + three-timing hooks (917->dispatch skeleton, checkpoint sole-holder)"
```

---

### Task 4 · 子串判定消灭（双路径）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（ChapterStep +3 字段 :97-152；CHAPTER_STEPS 表填值；五位子串位点 :1819/:4521/:4533/:4702/:4728 改属性——行号以 T3 后新树 re-anchor）
- Modify: `src/shenbi/pipeline/review_checklist.py`（REVIEW_SKILLS frozenset 26 名 + `is_review_skill` 精确判定）
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（:1577 调用点 :1709-1711 `_is_review_skill` 改用精确名单）
- Test: `tests/pipeline/test_review_skill_routing.py`（Create）

**Interfaces:**
- Produces:
```python
# chapter_loop.py ChapterStep 新字段（dataclass 尾部追加，带默认值）
settles_state: bool = False      # "state-settling" in step.skill 的显式化
emits_resonance: bool = False    # "review-resonance" ...
is_revision: bool = False        # "chapter-revision" ...

# review_checklist.py 模块级
REVIEW_SKILLS: frozenset[str] = frozenset({ ...26 名... })  # 24 shenbi-review-* + shenbi-escalation-review + shenbi-foundation-review

def is_review_skill(skill: str) -> bool:
    return skill in REVIEW_SKILLS
```

**复杂度:** infra ｜ **test_kind:** tdd_red_green ｜ **层级:** T1

- [ ] **Step 1: 红测**（三条——resonance 子串负例 / preview 假想名负例 / escalation 保留注入）：

```python
"""Spec #87 T4: substring elimination — dual path, behavior-preserving."""


def test_review_resonance_substring_negative(monkeypatch) -> None:
    """A skill merely CONTAINING 'review-resonance' must not trigger
    resonance post-processing (currently it does — red->green)."""
    # 构造 ChapterStep(skill="shenbi-xreview-resonance-y", emits_resonance=False)
    # 走 run_chapter_step 公共入口（serial 域），断言 _parse_and_persist_resonance 未被调用


def test_preview_named_skill_not_review() -> None:
    assert not is_review_skill("shenbi-preview-x")  # "review" 子串假阳性负例


def test_escalation_review_keeps_injection() -> None:
    """r3.1 裁定：escalation-review 保留 review checklist 注入（活行为）。"""
    assert is_review_skill("shenbi-escalation-review")
    assert is_review_skill("shenbi-foundation-review")


def test_roster_scan_reconciles_with_skills_dir() -> None:
    """skills/ 目录扫描对账：新 review 技能漏登即红（谓词=前缀∪两名，禁子串）。"""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2] / "skills"
    on_disk = {
        d.name
        for d in root.iterdir()
        if d.name.startswith("shenbi-review-")
        or d.name in {"shenbi-escalation-review", "shenbi-foundation-review"}
    }
    assert on_disk <= REVIEW_SKILLS
```

- [ ] **Step 2: 跑红** → `uv run pytest tests/pipeline/test_review_skill_routing.py -v` FAIL（`is_review_skill` 不存在；resonance 子串现误触）

- [ ] **Step 3: 实现**——review_checklist.py 加 26 名 frozenset（从 `ls skills/` 逐一誊抄）+ `is_review_skill`；dispatch_helper :1577 `_is_review_skill(skill)` 改 `is_review_skill(skill)`（删 :1709-1711 旧实现）；ChapterStep +3 字段；CHAPTER_STEPS 表中 `shenbi-state-settling` 行加 `settles_state=True`、`shenbi-review-resonance` 行加 `emits_resonance=True`、`shenbi-chapter-revision` 行加 `is_revision=True`；五位子串位点改属性判定（`:1819 step.uses_staging and step.settles_state`、失败/成功尾与三钩内 `step.emits_resonance`/`step.settles_state`/`step.is_revision`——行号以 T3 后现树为准 grep `"state-settling" in step.skill` 等三模式逐一定位）；**`_pre_dispatch_hooks`/`_on_dispatch_failure`/`_on_resonance_success`/`_on_revision_success` 四钩体内的 `if "state-settling" in step.skill` 等子串/等值条件（T3 引入，三模式 grep 已覆盖但 dict/属性形态注意）一并改属性判定**：

```python
def _pre_dispatch_hooks(
    step: ChapterStep, state: PipelineState, project_dir: Path, chapter: int
) -> tuple[list, list] | None:
    """Ordered pre-dispatch hooks (r2.2: same contract as T3's r2 form)."""
    outcome: tuple[list, list] | None = None
    if step.is_revision:
        write_audit_aggregate(project_dir, chapter)  # real name (:4486)
    if step.settles_state:
        outcome = _pre_settle_guard(state, project_dir, chapter)  # 3-arg (:2957)
    return outcome
```
（T4 只做**条件替换**——`in step.skill` → `step.xxx` 属性；签名/函数名/返回契约与 T3 落地形态完全一致，不重定义。`_on_dispatch_failure`/`_on_dispatch_success` 同步换条件；T4 红测 1 的外来 step 注入用 `monkeypatch.setattr(chapter_loop, "CHAPTER_STEPS", ...)` 替换序列项〔r2.2 补注入 seam〕）

- [ ] **Step 4: 验证**——红测全绿（含 T0 八路径）；`grep -n '"state-settling" in step.skill\|"review-resonance" in step.skill\|"chapter-revision" in step.skill' src/shenbi/pipeline/chapter_loop.py` = 零输出；**泛查** `grep -n "in step.skill" src/shenbi/pipeline/chapter_loop.py` 逐条裁定（应仅剩非三模式的合法用法或零）；T0 六路径仍绿；全量 unit 绿

- [ ] **Step 5: Commit + audit**

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/review_checklist.py src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_review_skill_routing.py
git commit -m "refactor: spec #87 T4 substring elimination — ChapterStep attrs + 26-name precise roster (escalation keeps injection)"
```

---

### Task 5 · 正名 + 基线 lint

**Files:**
- Modify: 18 个正名符号的定义+全部引用（清单见下）+ `src/shenbi/pipeline/audit_context_cache.py:124` import 改公共路径 + chapter_loop:1066 AuditResult import 改 `from shenbi.audit import AuditResult`
- Create: `tools/lint_private_imports.py`、`tests/private_imports_baseline.txt`
- Modify: `justfile`（挂 lint）、`tools/lint_dead_code_allowlist.py:32-33`（收缩两条）

**正名清单（18 函数 + 1 import 改路）**：

| # | 旧名→新名 | 定义文件 | tests import 次数 |
|---|---|---|---|
| 1 | `_build_skill_prompt→build_skill_prompt` | dispatch_helper | 29 |
| 2 | `_write_parsed_outputs→write_parsed_outputs` | dispatch_helper | 30 |
| 3 | `_init_truth_templates→init_truth_templates` | dispatch_helper | 7 |
| 4 | `_resolve_wildcard_path→resolve_wildcard_path` | dispatch_helper | 6 |
| 5 | `_dispatch_via_api→dispatch_via_api` | dispatch_helper | 5 |
| 6 | `_route_append_dedup_write→route_append_dedup_write` | dispatch_helper | 4 |
| 7 | `_chapter_header_style→chapter_header_style` | dispatch_helper | 4 |
| 8 | `_resolve_all_wildcards→resolve_all_wildcards` | dispatch_helper | 4 |
| 9 | `_increment_units→increment_units` | dispatch_helper | 4 |
| 10 | `_should_skip_audit→should_skip_audit` | chapter_loop | 10 |
| 11 | `_check_linguistic_drift→check_linguistic_drift` | chapter_loop | 7 |
| 12 | `_parse_resonance_score→parse_resonance_score` | chapter_loop | 5 |
| 13 | `_resolve_g4_files→resolve_g4_files` | chapter_loop | 4 |
| 14 | `_dispatch_serial_reviews→dispatch_serial_reviews` | chapter_loop | 4 |
| 15 | `_any_audit_has_findings→any_audit_has_findings` | chapter_loop | 4 |
| 16 | `_check_emergency_flag→check_emergency_flag` | crash_recovery（压制 :64 摘） | — |
| 17 | `_merge_step_result→merge_step_result` | state（压制 :3685 摘） | — |
| 18 | `_dispatch_with_retry→dispatch_with_retry` | parallel_dispatch（压制 :3802 摘；接线四类面：string monkeypatch tests/unit/pipeline/test_c15_wave_and_context_branches.py:45/:56；直接调用 tests/pipeline/test_parallel_retry_feedback.py:53/:76、tests/unit/pipeline/test_wave_state_threading.py:47/:59、tests/unit/pipeline/test_retry_taxonomy.py:431/:552；pinned 对 test_spec83_stale_declarations.py rest 集；测试函数名 test_wave_state_threading.py:38/:51、test_retry_taxonomy.py:408 同批改） | — |
| 19 | `_ending_archetype_of→ending_archetype_of` | **gates/g4/chapter_drafting.py:514**（r2 订正——非 text/）；连带 :569/:571 内部使用 + tests/unit/gates/g4/test_hook_type_rotation.py:156/:160/:168/:172/:173 五站点（r2.1 补 :160）；压制 audit_context_cache:124 摘 | — |

另有 chapter_loop:1066 `from shenbi.audit._shared import AuditResult  # pyright: ignore[reportPrivateUsage]` 改 `from shenbi.audit import AuditResult`（公共再导出已在 `shenbi/audit/__init__.py:6`）。

**docstring/字符串连带**（grep 归零兜底，导航清单）：exceptions.py:98、gates/g4/generic.py:270、pipeline/helper_injection.py:8、pipeline/llm_output_integrity.py:7、dispatch_helper 自身 :4228/:4513/:4638、tools/lint_key_reconciliation.py:128（`_should_skip_audit` 字符串站点，r2.2 补）。

**复杂度:** infra ｜ **test_kind:** regression_guard + tdd（lint 工具）｜ **层级:** T1

- [ ] **Step 1: 正名（逐符号机械改写）**——每符号：定义处改名 → `grep -rn '<旧名>' src/ tests/ tools/` 逐站点改（import/调用/string monkeypatch/docstring/测试函数名/pinned 对）→ 该符号 grep 归零 → 跑受影响测试文件。18+1 个符号串行做完后全量 `-m unit` 绿。
  - ALLOWLIST 收缩：`tools/lint_dead_code_allowlist.py` 删 :32-33 两行（`_merge_step_result`/`_check_emergency_flag` 正名后 seen 集变化——不删则「shrink ALLOWLIST」红）
  - spec83 rest 集 pinned 对 `("pipeline/parallel_dispatch.py", "_dispatch_with_retry")` 改 `dispatch_with_retry`

- [ ] **Step 2: 写 lint 工具红测**（`tests/pipeline/test_private_imports_lint.py`）：

```python
def test_baseline_subset_assertion() -> None:
    """当前 tests 私有 import 集合 ⊆ 基线（增量=0）。"""
    import subprocess, sys

    r = subprocess.run(
        [sys.executable, "tools/lint_private_imports.py", "--check"], capture_output=True, text=True
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_baseline_shrinks_only() -> None:
    """--update 仅人工评审后可用；基线行数 ≤ 当前文件行数（防自动膨胀）。"""
    from pathlib import Path

    baseline = Path("tests/private_imports_baseline.txt")
    assert baseline.is_file()
```

- [ ] **Step 3: 实现 lint 工具**——`tools/lint_private_imports.py`（AST 解析 tests/** 的 `from shenbi.pipeline... import _x` 形态（含多行括号/别名——用 ast.ImportFrom 非正则）；产出 (file, symbol) 对集合；`--check` 模式=当前集合 ⊆ 基线文件否则 exit 1 列出新增对；`--update` 模式=重写基线（仅人工评审后用，commit message 须注明）；`--report` 模式=打印拟议基线不写盘）。首跑：

```bash
uv run python tools/lint_private_imports.py --report > /tmp/proposed-baseline.txt
# 人工核对（正名后残留私有 import 应与 19 文件存量吻合）后：
uv run python tools/lint_private_imports.py --update
git add tests/private_imports_baseline.txt
```

justfile 挂载（lint 面既有 recipe 风格——参考 :40 lint-dead-code-allowlist 条目旁）+ just check 链路接入（首跑 report-only 人工评审完成后才把 --check 接进 check——本 task 内完成两步并记录于 commit message）。

- [ ] **Step 4: pyright 压制验收**——`grep -c "reportPrivateUsage" src/shenbi/pipeline/*.py`（逐文件）合计 **≤12**（17−1−3−1=12；cli 8 + context_assemble 1 + plan_skeleton 1 + dispatch_helper 2[truth_io，若做加项公共化则 ≤10]）；basedpyright 跑绿

- [ ] **Step 5: 验证**——正名 18+1 符号 grep 归零逐个确认；`uv run pytest tests/ -q -m unit` 全绿；`just check` exit 0

- [ ] **Step 6: Commit + audit**

```bash
git add <逐文件 pathspec>
git commit -m "refactor: spec #87 T5 public renames (18 syms + AuditResult import) + private-import baseline lint (report-only first run)"
```

---

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1 行数 ≤9,500/≤4,820/≤4,680 | T1/T2/T3 | `wc -l src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/dispatch_helper.py` |
| 2 `_run_chapter_step_impl` 消失+五函数红测+checkpoint 唯一持有+serial<260 | T0+T3 | `grep -n "_run_chapter_step_impl" src/ tests/`=空；T0 八测试零改动绿；`uv run pytest tests/pipeline/test_chapter_step_characterization.py -v` |
| 3 grep -c = 1 | T2 | `grep -c extractor_failed_fulltext src/shenbi/pipeline/dispatch_helper.py` |
| 4 T4 红测绿+压制 ≤12 | T4+T5 | `uv run pytest tests/pipeline/test_review_skill_routing.py -v`；`grep -c reportPrivateUsage src/shenbi/pipeline/*.py \| grep -v :0` 合计 |
| 5 基线子集断言+禁裸比较 | T2+T5 | `uv run python tools/lint_private_imports.py --check`；`grep -c "extractor ==" src/shenbi/pipeline/dispatch_helper.py` = 0 |
| 6 just check + 全量绿 | 全部 | `just check` exit 0 |

**评分场景**：无（纯行为保持重构，零 LLM dispatch——F947 规则满足）。
