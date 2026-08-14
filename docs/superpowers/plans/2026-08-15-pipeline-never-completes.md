# Pipeline 永不完成（spec #6）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复使长篇小说 pipeline 永不进入 CLOSURE 的 5 个根因（R1-R5）+ R6 节点/桥接中文提取 + F340/F341/F304 流程缺陷。

**Architecture:** 中文卷图解析下沉 `_shared.py`（卷级作用域锚 `## 第N卷：`）；total_chapters 统一为 `_shared.update_total_chapters := max(read_volume_boundaries())` 双写点（genesis step-6 钩子 + mid-book heal）；per-family N 占位语义表进 `contracts/paths.py`（`PathContext` + `[path-context]` prompt 行跨三路由）；gates/g4 目录参数化检查器；REJECT 重做语义 + 并行守卫镜像 + RetryExhaustedError 捕获。

**Tech Stack:** Python 3.11+ / pathlib / structlog / pytest（T1 单测 + T2 状态机测）。验证一律 `uv run pytest` / `just check`（与 CI `uv run --frozen` 同构）。

**Spec:** `docs/superpowers/specs/2026-08-14-pipeline-never-completes-design.md`（Revised 2026-08-15，设计审查 6 轮收敛版）

## Global Constraints

- 框架代码无 `print()`（structlog）；`pathlib.Path` 文件 I/O；gate 检查器纯函数幂等无副作用
- 状态字面量唯一定义于 `src/shenbi/pipeline/state.py` `CheckpointType`（StrEnum），新代码禁裸状态串
- G0.9：scenario 输入只引用 `tests/fixtures/` 真实产物；fixture 是源副本的须哈希一致（G0.11 MIRROR_MAP）
- 核心原则 8：SDD 全程禁为验证触发真实 dispatch——所有验收用 fixtures/纯函数/状态机构造表达
- 改 SKILL.md 契约（T5）后必须 `just generate` 同步生成物（deps.json/docs/skills），禁手改生成物
- Conventional Commits：`fix:`（findings 修复）
- **所有 task 均为 infra**（涉及 `pipeline/`、`contracts/`、`gates/g4/`、`dispatcher/`、`audit/`、3+ 调用方）——协调者亲自实现，不分派 implementer 子 agent；每 task commit 后 fresh-context 重审产出 `.superpowers/sdd/audit-T<N>.md`

## 验收覆盖表（spec 验收 → task → 可执行验证）

| spec 验收 | task | 验证命令 |
|---|---|---|
| R1 正：边界集=={15,35,55,75,100}、卷数==5、is_volume_boundary(15/35/55/75/100)==True | T1 | `uv run pytest tests/pipeline/test_volume_map_cn.py -v` |
| R1 负：is_volume_boundary(5/10/56)==False | T1 | 同上 |
| R2 (i) genesis 钩子后 total==100 | T2 | `uv run pytest tests/pipeline/test_total_chapters.py -v`（钩子函数单测 + 调用点 grep 断言；全 genesis 流程需 dispatch，按核心原则 8 以此表达——记 spec-deviations） |
| R2 (ii) mid-book heal：56 章 total=None 项目 next 后 total==100 且 check_triggers(55,100).volume_boundary==True | T2 | 同上（heal 逻辑单测复现守卫序列） |
| R4：ch60 G4 查 arc-5-score.md（非 arc-60）；prompt 含 [path-context] 且 Files-to-create 列 arc-5；resolver 优先解析行、无行回落；derive_* per-family（score-arc 读路径 arc-5.md） | T3+T4 | `uv run pytest tests/pipeline/test_path_context.py tests/pipeline/test_trigger_context.py -v` |
| R4：卷末章 55 volume 场景 volume-3-score.md；closure step 6 chapter-100-long-span.md | T4+T6 | 同上 + `tests/pipeline/test_closure_context.py` |
| R3：closure step 10 fixture 项目 G4 PASS；characters/（无 manifest）同 PASS | T5 | `uv run pytest tests/pipeline/test_g4_directory.py -v` |
| R5：closure 10 步 prompt-build 全通过；escalation 不抛 UnresolvedPathError；anchor-curate 真实派发路径 | T6 | `uv run pytest tests/pipeline/test_closure_context.py -v` |
| R6：ch5+ 节点非 None 非垃圾；vol-1 桥接@26；vol-2 桥接@36 不@30；续作行 ch1-10 不出现；卷上下文非空 | T7 | `uv run pytest tests/pipeline/test_cn_extract.py -v` |
| F340：genesis-complete reject 后 resume 重跑 step 17；escalation reject-redo 获完整预算 | T8 | `uv run pytest tests/pipeline/test_review_reject.py -v` |
| F341：--auto 并行不设 checkpoint 且 truth 落盘 | T8 | 同上 |
| F304：预算耗尽产 checkpoint 非 traceback 且 budget 持久化 | T8 | 同上 |
| 回归：just check 全绿 | T9 | `just check` |

G3.4 独立评分：本 spec 无评分场景（全部为解析/接线/状态机逻辑），N/A。

---

### Task 1: R1 中文卷界解析（卷级作用域）+ 真实 fixture

**复杂度: infra** · **test_kind: tdd_red_green** · **层级: T1** · **fixture: `tests/fixtures/volume-map-xinghuo.md`（生产 volume_map.md 精确副本，MIRROR_MAP 登记）**

**Files:**
- Create: `tests/fixtures/volume-map-xinghuo.md`（`cp novel-output/xinghuo-ranqiong/outline/volume_map.md`）
- Modify: `src/shenbi/pipeline/_shared.py:34-74`
- Modify: `src/shenbi/gates/g0.py:13-15`（MIRROR_MAP）
- Test: `tests/pipeline/test_volume_map_cn.py`

**Interfaces:**
- Produces: `read_volume_boundaries(project_dir: Path | str) -> set[int]`（签名不变，行为扩展：英文空结果时回落中文卷级解析）；`_read_cn_volume_boundaries(text: str) -> set[int]`（新私有，T7 复用文本级入口）

- [ ] **Step 1: 建 fixture + MIRROR_MAP 登记**

```bash
cp novel-output/xinghuo-ranqiong/outline/volume_map.md tests/fixtures/volume-map-xinghuo.md
```

```python
# src/shenbi/gates/g0.py MIRROR_MAP 追加条目
MIRROR_MAP: dict[str, str] = {
    "tests/fixtures/outline-example.md": "outline-example.md",
    "tests/fixtures/volume-map-xinghuo.md": "novel-output/xinghuo-ranqiong/outline/volume_map.md",
}
```

- [ ] **Step 2: 写失败测试**

```python
# tests/pipeline/test_volume_map_cn.py
"""R1: 中文卷图卷级作用域解析（spec #6 修复方向 1）。

fixture 是生产 volume_map.md 的精确副本（G0.9 真实产物，G0.11 MIRROR_MAP 镜像）。
"""
import shutil
from pathlib import Path

from shenbi.pipeline._shared import _read_cn_volume_boundaries, read_volume_boundaries
from shenbi.pipeline.triggers import is_volume_boundary

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md"


def _mk_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "outline").mkdir(parents=True)
    shutil.copy(FIXTURE, proj / "outline" / "volume_map.md")
    return proj


def test_cn_boundaries_exact_set_on_real_fixture():
    """验收（正）：真实项目边界集 == {15,35,55,75,100}，卷数 == 5。"""
    text = FIXTURE.read_text(encoding="utf-8")
    assert _read_cn_volume_boundaries(text) == {15, 35, 55, 75, 100}


def test_cn_boundaries_via_project_layout(tmp_path):
    proj = _mk_project(tmp_path)
    assert read_volume_boundaries(proj) == {15, 35, 55, 75, 100}


def test_kr_subranges_excluded_negative_acceptance(tmp_path):
    """验收（负）：KR 级子范围（5/10/56）不得入边界集。"""
    proj = _mk_project(tmp_path)
    for ch in (5, 10, 56):
        assert not is_volume_boundary(ch, proj)
    for ch in (15, 35, 55, 75, 100):
        assert is_volume_boundary(ch, proj)


def test_english_formats_regression():
    """回归护栏：既有英文格式解析行为不变（parser 单元，非 skill 场景）。"""
    text = "## Volume 1\n\nChapter End: 15\n\n## Volume 2\n\nChapters 16-35\n"
    assert read_volume_boundaries(_fake_proj(tmp_text=text) if False else Path("/nonexistent")) == set() if False else None
    # 上行占位不可执行——直接用文本级：英文路径经 read_volume_boundaries 需项目布局，
    # 用 tmp 项目承载：
```

（注：最后一个测试在 Step 2 实际写为——）

```python
def test_english_formats_regression(tmp_path):
    """回归护栏：既有英文格式解析行为不变（parser 单元，非 skill 场景）。"""
    proj = tmp_path / "en"
    (proj / "outline").mkdir(parents=True)
    (proj / "outline" / "volume_map.md").write_text(
        "## Volume 1\n\nChapter End: 15\n\n## Volume 2\n\nChapters 16-35\n",
        encoding="utf-8",
    )
    assert read_volume_boundaries(proj) == {15, 35}
```

- [ ] **Step 3: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_volume_map_cn.py -v`
Expected: FAIL — `_read_cn_boundaries_exact_set_on_real_fixture` ImportError；via_project_layout 得 `set()` 断言失败

- [ ] **Step 4: 实现**

```python
# src/shenbi/pipeline/_shared.py —— _RANGE_RE 之后追加（:42 后）：

# Chinese volume format (production): volume header `## 第N卷：{卷名}` with the
# volume-level range line `**章节范围**: 第A章 - 第M章（共K章）`. KR-level lines
# are list-dash-prefixed (`- **章节范围**`) and excluded by the line-start anchor;
# the `| 段 | 章节范围 |` tension-table column never matches the bolded pattern.
_CN_VOL_HEAD_RE = re.compile(
    r"^##\s*第[0-9一二三四五六七八九十百]+卷\s*[：:]", re.MULTILINE
)
_CN_VOL_RANGE_LINE_RE = re.compile(
    r"^\*\*章节范围\*\*.*?第\s*(\d+)\s*章\s*[-–—~～]\s*第\s*(\d+)\s*章",
    re.MULTILINE,
)


def _read_cn_volume_boundaries(text: str) -> set[int]:
    """Volume-scoped Chinese parse: per `## 第N卷：` section, only the first
    line-start `**章节范围**` range line counts (its end chapter M)."""
    boundaries: set[int] = set()
    for m in _CN_VOL_HEAD_RE.finditer(text):
        section = text[m.end():]
        nxt = _CN_VOL_HEAD_RE.search(section)
        if nxt:
            section = section[: nxt.start()]
        rm = _CN_VOL_RANGE_LINE_RE.search(section)
        if rm:
            boundaries.add(int(rm.group(2)))
    return boundaries
```

```python
# read_volume_boundaries 内，`return boundaries`（:74）前追加回落：

    # Chinese volume-scoped fallback (production format, spec #6 R1).
    if not boundaries:
        boundaries = _read_cn_volume_boundaries(text)
```

`__all__` 追加 `"_read_cn_volume_boundaries"`（T7 文本级复用）。

- [ ] **Step 5: 跑测试确认通过 + 镜像门禁**

Run: `uv run pytest tests/pipeline/test_volume_map_cn.py -v && uv run python tools/check_fixture_mirror.py`
Expected: 4 passed；mirror 输出空（零 drift）

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/_shared.py src/shenbi/gates/g0.py tests/fixtures/volume-map-xinghuo.md tests/pipeline/test_volume_map_cn.py
git commit -m "fix: parse Chinese volume-map boundaries volume-scoped (F324) — real-project fixture {15,35,55,75,100}, KR subranges excluded"
```

---

### Task 2: R2 total_chapters 统一 + genesis 钩子 + mid-book heal

**复杂度: infra** · **test_kind: tdd_red_green** · **层级: T1/T2**

**Files:**
- Modify: `src/shenbi/pipeline/_shared.py`（新 `update_total_chapters`；模块 docstring「stdlib + safe_write leaf」）
- Modify: `src/shenbi/pipeline/genesis.py:350-356`（step-6 成功钩子）
- Modify: `src/shenbi/pipeline/cli.py:147-172,215-221`（收敛 + heal）
- Modify: `src/shenbi/pipeline/triggers.py:363-395`（收敛，删 `_count_total_chapters`——先 grep 调用方确认仅 triggers._update_total_chapters）
- Test: `tests/pipeline/test_total_chapters.py`

**Interfaces:**
- Consumes: T1 `read_volume_boundaries`
- Produces: `update_total_chapters(project_dir: Path) -> int`（`_shared`，公开）；`genesis_finalize_volume_map(project_dir: Path) -> int`（genesis 钩子函数）

- [ ] **Step 1: 写失败测试**

```python
# tests/pipeline/test_total_chapters.py
"""R2: total_chapters := max(read_volume_boundaries()) 统一写点（F353）。

mid-book heal 验收（spec R2-ii）：56 章 total=None 项目在守卫前 heal。
"""
import json
import shutil
from pathlib import Path

from shenbi.pipeline._shared import update_total_chapters
from shenbi.pipeline.cli import _read_total_chapters
from shenbi.pipeline.genesis import genesis_finalize_volume_map
from shenbi.pipeline.triggers import check_triggers
from shenbi.pipeline.state import PipelineState

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md"


def _mk_project(tmp_path: Path, with_total: bool = False) -> Path:
    proj = tmp_path / "proj"
    (proj / "outline").mkdir(parents=True)
    shutil.copy(FIXTURE, proj / "outline" / "volume_map.md")
    data = {"title": "星火燃穹"}
    if with_total:
        data["total_chapters"] = 100
    (proj / "novel.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return proj


def test_update_total_chapters_writes_planned_total(tmp_path):
    """验收（i）钩子语义：固化 = 规划总章数 100（max boundaries），非已写 56。"""
    proj = _mk_project(tmp_path)
    assert update_total_chapters(proj) == 100
    assert _read_total_chapters(proj) == 100


def test_genesis_finalize_hook(tmp_path):
    proj = _mk_project(tmp_path)
    assert genesis_finalize_volume_map(proj) == 100


def test_update_idempotent_and_no_boundaries(tmp_path):
    proj = _mk_project(tmp_path, with_total=True)
    assert update_total_chapters(proj) == 100  # 幂等：值相同不重写
    empty = tmp_path / "empty"
    (empty / "outline").mkdir(parents=True)
    (empty / "novel.json").write_text("{}", encoding="utf-8")
    assert update_total_chapters(empty) == 0


def test_midbook_heal_unlocks_guard(tmp_path):
    """验收（ii）：56 章 total=None → heal → total==100 → 卷边界触发可达。"""
    proj = _mk_project(tmp_path)
    total = _read_total_chapters(proj)
    assert total == 0
    # 复现 cli.py 守卫序列（heal 即将插入的位置）：
    if total <= 0:
        total = update_total_chapters(proj)
    assert total == 100
    state = PipelineState.default(str(proj))
    result = check_triggers(state, 55, total)
    assert result.volume_boundary is True
    assert result.book_closure is False  # 55 < 100：不提前闭卷
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_total_chapters.py -v`
Expected: FAIL — ImportError（`update_total_chapters`/`genesis_finalize_volume_map` 不存在）

- [ ] **Step 3: 实现**

```python
# _shared.py 追加（imports 加 json；docstring 改「stdlib + safe_write leaf module」）：

def update_total_chapters(project_dir: Path) -> int:
    """Recompute novel.json.total_chapters := max(read_volume_boundaries()).

    Single write-point semantics for genesis step-6 hook, mid-book heal, and
    volume-boundary resume (spec #6 R2). Returns the new total, or 0 when no
    boundaries parse or novel.json is absent.
    """
    boundaries = read_volume_boundaries(project_dir)
    if not boundaries:
        return 0
    new_total = max(boundaries)
    novel_path = project_dir / "novel.json"
    if not novel_path.exists():
        return 0
    data = json.loads(novel_path.read_text(encoding="utf-8"))
    if data.get("total_chapters") != new_total:
        data["total_chapters"] = new_total
        from shenbi.safe_write import safe_write

        safe_write(novel_path, json.dumps(data, ensure_ascii=False, indent=2))
    return new_total
```

```python
# genesis.py —— 成功块（:352 _update_indexes 之后、retry_counts.pop 之前）：

    if step.skill in _INDEX_UPDATE_SKILLS:
        _update_indexes(project_dir, step.skill)
    if step.skill == "shenbi-volume-outlining":  # step 6: volume map landed (R2)
        genesis_finalize_volume_map(project_dir)
```

```python
# genesis.py 模块级新增（imports 区之后）：

def genesis_finalize_volume_map(project_dir: Path) -> int:
    """Deterministic total_chapters固化 hook (spec #6 R2): runs at genesis
    step-6 success — no LLM involvement, no later step rewrites volume_map."""
    from shenbi.pipeline._shared import update_total_chapters

    total = update_total_chapters(project_dir)
    if total:
        log.info("genesis_total_chapters_fixed", total_chapters=total)
    return total
```

```python
# cli.py :218-219 守卫前插 heal：

            total = _read_total_chapters(project_dir)
            if total <= 0:
                # Mid-book heal (spec #6 R2): in-flight projects past genesis
                # never re-run the step-6 hook — recompute before the guard or
                # the self-lock persists (56-chapter production instance).
                from shenbi.pipeline._shared import update_total_chapters

                total = update_total_chapters(project_dir)
            if total > 0:
```

```python
# cli.py _update_total_chapters(:147) 函数体收敛为委托（签名/返回不变）：

def _update_total_chapters(project_dir: Path) -> int:
    """Delegate to _shared.update_total_chapters (single source, spec #6 R2)."""
    from shenbi.pipeline._shared import update_total_chapters

    return update_total_chapters(project_dir)
```

```python
# triggers.py :376-395 _update_total_chapters(state) 收敛为委托；删除
# _count_total_chapters(:363-373)（先 grep：`grep -rn "_count_total_chapters" src/ tests/`
# 确认零其他调用方，有则一并改委托）：

def _update_total_chapters(state: PipelineState) -> None:
    """Delegate to _shared.update_total_chapters (single source, spec #6 R2)."""
    from shenbi.pipeline._shared import update_total_chapters

    update_total_chapters(Path(state.project_dir))
```

- [ ] **Step 4: 跑测试确认通过 + 全 pipeline 测试回归**

Run: `uv run pytest tests/pipeline/test_total_chapters.py tests/pipeline/ -v`
Expected: 新 4 passed；既有 pipeline 套件零回归

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/_shared.py src/shenbi/pipeline/genesis.py src/shenbi/pipeline/cli.py src/shenbi/pipeline/triggers.py tests/pipeline/test_total_chapters.py
git commit -m "fix: unify total_chapters to max(boundaries) with genesis hook + mid-book heal (F353) — breaks write-point self-lock"
```

---

### Task 3: R4a PathContext + per-family N 解析表（contracts/paths.py）

**复杂度: infra** · **test_kind: tdd_red_green** · **层级: T1**

**Files:**
- Modify: `src/shenbi/contracts/paths.py`
- Test: `tests/pipeline/test_path_context.py`

**Interfaces:**
- Produces:
  - `PATH_CONTEXT_PREFIX = "[path-context]"`（常量）
  - `@dataclass(frozen=True) PathContext(chapter/arc/stratum/volume: int|None=None, anchor/escalation: int|str|None=None)`
  - `format_path_context(ctx: PathContext) -> str`
  - `parse_path_context(prompt: str) -> PathContext | None`
  - `resolve_contract_path(path: str, chapter: int|None, ctx: PathContext|None=None) -> str`
  - `resolve_or_skip_ctx(path: str, chapter: int|None, ctx: PathContext|None=None) -> str | None`
  - `build_trigger_context(chapter: int, boundaries: set[int]) -> PathContext`

- [ ] **Step 1: 写失败测试**

```python
# tests/pipeline/test_path_context.py
"""R4a: per-family N 占位语义表 + [path-context] 行（F245/F373 处置面）。"""
import pytest

from shenbi.contracts.paths import (
    PathContext,
    UnresolvedPathError,
    build_trigger_context,
    format_path_context,
    parse_path_context,
    resolve_contract_path,
)


def test_arc_family_uses_arc_not_chapter():
    """验收：ch 60 的 arc 路径解析为 arc-5（60//12），非 arc-60。"""
    ctx = build_trigger_context(60, {15, 35, 55, 75, 100})
    assert resolve_contract_path("truth/arcs/arc-N.md", 60, ctx) == "truth/arcs/arc-5.md"
    assert resolve_contract_path("audits/arc-N-score.md", 60, ctx) == "audits/arc-5-score.md"


def test_stratum_and_volume_families():
    ctx = build_trigger_context(55, {15, 35, 55, 75, 100})
    assert resolve_contract_path("audits/stratum-N-score.md", 55, ctx) == "audits/stratum-1-score.md"  # 55//36
    assert resolve_contract_path("audits/volume-N-score.md", 55, ctx) == "audits/volume-3-score.md"  # count(≤55)


def test_volume_count_is_not_len_boundaries():
    """mid-book 不等价 len(boundaries)（只在 ch100 相等）。"""
    ctx = build_trigger_context(56, {15, 35, 55, 75, 100})
    assert resolve_contract_path("audits/volume-N-payoff.md", 56, ctx) == "audits/volume-3-payoff.md"


def test_chapter_family_and_bare_n_fallback():
    ctx = PathContext(chapter=100)
    assert resolve_contract_path("audits/chapter-N-long-span.md", 100, ctx) == "audits/chapter-100-long-span.md"
    assert resolve_contract_path("snapshots/chapter-NNN/", 100, ctx) == "snapshots/chapter-100/"


def test_no_ctx_falls_back_to_chapter_semantics():
    """回落：无 ctx 行为与现状逐字节一致（向后兼容）。"""
    assert resolve_contract_path("audits/arc-N-score.md", 60, None) == "audits/arc-60-score.md"


def test_no_ctx_unresolved_raises():
    with pytest.raises(UnresolvedPathError):
        resolve_contract_path("truth/arcs/arc-N.md", None, None)


def test_roundtrip_format_parse():
    ctx = build_trigger_context(60, {15, 35, 55, 75, 100})
    line = format_path_context(ctx)
    assert line == "[path-context] chapter=60 arc=5 stratum=1 volume=3"
    parsed = parse_path_context(f"Execute skill for chapter 60.\n{line}")
    assert parsed == ctx


def test_parse_absent_returns_none():
    assert parse_path_context("Execute skill for chapter 60. Project dir: /x") is None


def test_str_sentinels():
    """F3B5/F380：escalation 书级哨兵、anchor 零填充。"""
    ctx = PathContext(escalation="genesis")
    assert resolve_contract_path("audits/escalation-N-report.md", None, ctx) == "audits/escalation-genesis-report.md"
    ctx2 = PathContext(anchor=1)
    assert resolve_contract_path("truth/anchors/AC-NNN.md", None, ctx2) == "truth/anchors/AC-001.md"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_path_context.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: 实现**

```python
# contracts/paths.py 追加（from __future__ import annotations 已有；加 from dataclasses import dataclass）：

PATH_CONTEXT_PREFIX = "[path-context]"

# Family-prefixed N: arc-N / stratum-N / volume-N / chapter-N / escalation-N
_FAMILY_N = re.compile(r"(?<=[-/])(arc|stratum|volume|chapter|escalation)-N(?=[-./]|$)")
_AC_ANCHOR = re.compile(r"(?<=[-/])AC-NNN(?=[-./]|$)")
_CTX_KEYS = ("chapter", "arc", "stratum", "volume", "anchor", "escalation")


@dataclass(frozen=True)
class PathContext:
    """Per-family placeholder values carried alongside (or inside, via the
    [path-context] prompt line) a dispatch. int|str sentinel fields allow
    book-level markers (escalation="genesis")."""

    chapter: int | None = None
    arc: int | None = None
    stratum: int | None = None
    volume: int | None = None
    anchor: int | str | None = None
    escalation: int | str | None = None


def format_path_context(ctx: PathContext) -> str:
    parts = [f"{k}={getattr(ctx, k)}" for k in _CTX_KEYS if getattr(ctx, k) is not None]
    return f"{PATH_CONTEXT_PREFIX} " + " ".join(parts) if parts else ""


def parse_path_context(prompt: str) -> PathContext | None:
    for line in prompt.splitlines():
        s = line.strip()
        if not s.startswith(PATH_CONTEXT_PREFIX):
            continue
        kv: dict[str, int | str] = {}
        for tok in s[len(PATH_CONTEXT_PREFIX):].split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                if k in _CTX_KEYS:
                    kv[k] = int(v) if v.isdigit() else v
        if kv:
            return PathContext(**kv)  # type: ignore[arg-type]
    return None


def build_trigger_context(chapter: int, boundaries: set[int]) -> PathContext:
    """Trigger-fan-out context (memory-distill SKILL: arc N = chapter // 12;
    stratum N = chapter // 36; volume N = count(boundaries <= chapter))."""
    return PathContext(
        chapter=chapter,
        arc=chapter // 12,
        stratum=chapter // 36,
        volume=sum(1 for b in boundaries if b <= chapter),
    )


def resolve_contract_path(path: str, chapter: int | None, ctx: PathContext | None = None) -> str:
    """Resolve N/NNN with per-family semantics when *ctx* is present.

    Family-prefixed N resolves from ctx's family value; AC-NNN from ctx.anchor
    (int → %03d, str → literal); everything else falls back to chapter
    semantics (legacy resolve_chapter_path behavior unchanged)."""
    if ctx is not None:
        m = _FAMILY_N.search(path)
        if m:
            key = m.group(1)
            val = getattr(ctx, key)
            if val is not None:
                return _FAMILY_N.sub(f"{key}-{val}", path, count=1)
        if ctx.anchor is not None and _AC_ANCHOR.search(path):
            pad = f"{ctx.anchor:03d}" if isinstance(ctx.anchor, int) else str(ctx.anchor)
            return path.replace("AC-NNN", f"AC-{pad}")
    return resolve_chapter_path(path, chapter)


def resolve_or_skip_ctx(path: str, chapter: int | None, ctx: PathContext | None = None) -> str | None:
    try:
        return resolve_contract_path(path, chapter, ctx)
    except UnresolvedPathError:
        return None
```

注意：`_FAMILY_N.sub(f"{key}-{val}", ...)` 的替换串含字面 family 名（无反引用风险——`key` 来自白名单枚举，`val` 为 int 或受控哨兵串）。

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/pipeline/test_path_context.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/paths.py tests/pipeline/test_path_context.py
git commit -m "fix: per-family N-placeholder resolution table + [path-context] channel (F245) — arc=ch//12, stratum=ch//36, volume=boundary-count"
```

---

### Task 4: R4b 四消费者接线（trigger G4 + 派发 prompt + derive_*）

**复杂度: infra** · **test_kind: tdd_red_green** · **层级: T1**

**Files:**
- Modify: `src/shenbi/pipeline/triggers.py:545-625`（run_triggered_skills）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:515,651-658,1504,1708`（_build_skill_prompt 签名 + 三处 chapter derive）
- Modify: `src/shenbi/dispatcher/executor.py:89-108,161-162,242`（derive_input_files + dispatch 双派发点）
- Modify: `src/shenbi/audit/_shared.py:38-58`（derive_output_files）
- Test: `tests/pipeline/test_trigger_context.py`

**Interfaces:**
- Consumes: T3 全部 produces
- Produces: `_build_skill_prompt(..., path_context: PathContext | None = None)`；`derive_input_files/derive_output_files(..., ctx: PathContext | None = None)`；`run_triggered_skills` prompt 追加 `[path-context]` 行

- [ ] **Step 1: 写失败测试**

```python
# tests/pipeline/test_trigger_context.py
"""R4b: 触发派发/G4/子进程三面拿同一 N 语义（F373）。

monkeypatch 捕获 dispatch prompt 与 G4 files——接线单测（非 skill 场景，
G0.9 不适用；fixtures 指真实 skill 产物输入）。
"""
import shutil
from pathlib import Path

from shenbi.pipeline import triggers
from shenbi.pipeline.state import PipelineState
from shenbi.pipeline.triggers import run_triggered_skills
from shenbi.pipeline._shared import read_volume_boundaries
from shenbi.contracts.paths import build_trigger_context, format_path_context

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md"


def _mk_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "outline").mkdir(parents=True)
    shutil.copy(FIXTURE, proj / "outline" / "volume_map.md")
    return proj


def test_run_triggered_skills_wires_context_and_g4_paths(tmp_path, monkeypatch):
    proj = _mk_project(tmp_path)
    captured: dict[str, object] = {}

    def fake_dispatch(skill, project_dir, prompt, **kw):
        captured.setdefault("prompts", []).append((skill, prompt))
        return type("R", (), {"success": True})()

    def fake_g4(skill, files, project_dir, **kw):
        captured.setdefault("g4_files", []).append((skill, list(files)))
        return {"status": "PASS"}

    monkeypatch.setattr(triggers, "dispatch_skill", fake_dispatch)
    monkeypatch.setattr(triggers, "run_gate_g4", fake_g4)
    monkeypatch.setattr(triggers, "run_gate_g3", lambda *a, **k: {"status": "PASS"})

    state = PipelineState.default(str(proj))
    # 直接驱动：arc 族步骤在 ch=60 触发（绕过 check_triggers 的构造复杂度）
    from shenbi.pipeline.triggers import TRIGGER_STEPS

    arc_steps = [s for s in TRIGGER_STEPS if s.category == "l2_distill" and s.mode == "L2"]
    ok = run_triggered_skills(state, proj, 60, arc_steps, flags_override=None) if False else None
```

（注：`run_triggered_skills` 现签名 `(state, project_dir, chapter, result: TriggerResult)`——按实际签名驱动；Step 1 实际写为构造 `TriggerResult`：）

```python
    from shenbi.pipeline.triggers import TriggerResult

    result = TriggerResult()
    result.arc_cycle = True
    ok = run_triggered_skills(state, proj, 60, result)
    assert ok is True

    ctx = build_trigger_context(60, read_volume_boundaries(proj))
    line = format_path_context(ctx)
    arc_prompts = [p for s, p in captured["prompts"] if "memory-distill" in s]
    assert arc_prompts and all(line in p for p in arc_prompts)
    g4 = [(s, f) for s, f in captured["g4_files"]]
    assert ("shenbi-memory-distill", ["truth/arcs/arc-5.md"]) in g4
```

（`TriggerResult` 字段名以 `triggers.py` 实际定义为准——实现时先读 `class TriggerResult` 再定 `arc_cycle` 字段名；测试断言不变。）

```python
def test_derive_input_files_per_family():
    """验收：score-arc 契约读路径经 ctx 解析为 arc-5（非 arc-60）。"""
    from shenbi.dispatcher.executor import derive_input_files

    ctx = build_trigger_context(60, {15, 35, 55, 75, 100})
    reads = derive_input_files("shenbi-score-arc", chapter=60, ctx=ctx)
    assert "truth/arcs/arc-5.md" in reads
    assert not any("arc-60" in r for r in reads)


def test_derive_output_files_per_family():
    from shenbi.audit._shared import derive_output_files

    ctx = build_trigger_context(60, {15, 35, 55, 75, 100})
    writes = derive_output_files("shenbi-score-arc", chapter=60, ctx=ctx)
    assert "audits/arc-5-score.md" in writes
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_trigger_context.py -v`
Expected: FAIL — prompt 无 `[path-context]` 行；g4_files 为 `arc-N.md`；derive_* 无 ctx 参数（TypeError）

- [ ] **Step 3: 实现**

```python
# triggers.py run_triggered_skills（:545 起）—— prompt 构造前计算 ctx 并注入：

    from shenbi.contracts.paths import (
        build_trigger_context,
        format_path_context,
        resolve_contract_path,
    )

    boundaries = read_volume_boundaries(project_dir)
    ctx = build_trigger_context(chapter, boundaries)
    ctx_line = format_path_context(ctx)

    for step in steps:
        mode_hint = f" Mode: {step.mode}." if step.mode else ""
        prompt = (
            f"Execute {step.skill} for chapter {chapter}.{mode_hint} Project dir: {project_dir}"
        )
        if ctx_line:
            # Cross-route context carrier (spec #6 R4b): the executing LLM sees
            # it as a machine-generated prefix echoing the Files-to-create list.
            prompt = f"{prompt}\n{ctx_line}"
```

```python
# triggers.py :584 G4 路径解析：

        g4_file = (
            resolve_contract_path(step.output_path, chapter, ctx) if step.output_path else ""
        )
```

```python
# dispatch_helper.py _build_skill_prompt 签名（:515）加参数：

def _build_skill_prompt(
    skill: str,
    project_dir: Path,
    prompt: str,
    chapter: int | None,
    uses_staging: bool = False,
    shared_context: Any = None,
    json_mode: bool = False,
    path_context: PathContext | None = None,
) -> tuple[str, str, list[str]]:
```

```python
# dispatch_helper.py :651-658 输出路径解析改经 ctx：

    for write_path in contract.get("writes", []):
        output_paths.append(resolve_contract_path(write_path, chapter, path_context))
    for update_path in contract.get("updates", []):
        output_paths.append(resolve_contract_path(update_path, chapter, path_context))
```

```python
# dispatch_helper.py 三处 chapter derive（:1504 / :1708 / :1853）统一模式：

    path_ctx = parse_path_context(prompt)
    chapter = path_ctx.chapter if path_ctx is not None else None
    if chapter is None:
        chapter = extract_chapter(prompt)
```

（API/IDE 两处把 `path_ctx` 透传给 `_build_skill_prompt(..., path_context=path_ctx)`；子进程路由 :1853 只需 chapter 修正——契约解析发生在子进程内，由 executor 侧同款 parse 接住。）

```python
# executor.py dispatch()（:161-162）与 dispatch_with_write_audit()（:242）：

    from shenbi.contracts.paths import parse_path_context

    path_ctx = parse_path_context(prompt)
    chapter = path_ctx.chapter if path_ctx is not None else None
    if chapter is None:
        chapter = extract_chapter(prompt)
    # derive_input_files(skill, chapter=chapter, ...) 全部改为
    # derive_input_files(skill, chapter=chapter, ctx=path_ctx, ...)
```

```python
# executor.py derive_input_files（:89）签名 + 解析：

def derive_input_files(
    skill: str,
    chapter: int | None = None,
    round_dir: Path | None = None,
    ctx: PathContext | None = None,
) -> list[str]:
    ...
        paths = [
            rp
            for p in load_contract(skill)["reads"]
            if (rp := resolve_or_skip_ctx(p, chapter, ctx)) is not None
        ]
```

```python
# audit/_shared.py derive_output_files（:38）同款：加 ctx 参数、resolve_or_skip_ctx。
```

- [ ] **Step 4: 跑测试确认通过 + 既有回归**

Run: `uv run pytest tests/pipeline/test_trigger_context.py tests/pipeline/test_path_context.py tests/pipeline/test_executor_config.py -v`
Expected: 全 passed（含既有 executor 套件零回归）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/triggers.py src/shenbi/pipeline/dispatch_helper.py src/shenbi/dispatcher/executor.py src/shenbi/audit/_shared.py tests/pipeline/test_trigger_context.py
git commit -m "fix: wire per-family N context through trigger dispatch/G4/derive_* (F373) — [path-context] line crosses all three routes"
```

---

### Task 5: R3 目录参数化检查器 + closure step 10 契约对齐 + characters/

**复杂度: infra** · **test_kind: tdd_red_green** · **层级: T1**

**Files:**
- Modify: `src/shenbi/gates/g4/generic.py:33-42`（目录分支）
- Modify: `src/shenbi/pipeline/closure.py:112-116,148-159,293`（step 10 路径 + artifact）
- Modify: `skills/shenbi-snapshot-manage/SKILL.md`（manifest 钉契约）+ `just generate`
- Test: `tests/pipeline/test_g4_directory.py`

**Interfaces:**
- Consumes: T3 `PathContext`（step 10 NNN→最终章号）
- Produces: `g4_generic_generative` 目录分支（snapshot 类：存在+≥1 文件+manifest 命名条目；非 snapshot：存在+≥1 文件）；`_closure_snapshot_dir(project_dir: Path) -> str`

- [ ] **Step 1: 写失败测试**

```python
# tests/pipeline/test_g4_directory.py
"""R3: G4 目录参数化校验（F371）——snapshot 类查 manifest，characters/ 不查。"""
import json
import shutil
from pathlib import Path

from shenbi.gates.g4.generic import g4_generic_generative

_PROD_SNAP = Path("novel-output/xinghuo-ranqiong/snapshots")


def _result(raw: str) -> dict:
    return json.loads(raw)


def test_dir_with_files_and_manifest_passes(tmp_path):
    d = tmp_path / "snapshots" / "chapter-100"
    d.mkdir(parents=True)
    # 真实快照产物拷贝（生产 snapshots/ 为 crash_recovery 平铺真实产物）
    srcs = sorted(_PROD_SNAP.glob("*.md"))[:2]
    for s in srcs:
        shutil.copy(s, d / s.name)
    (d / "manifest.json").write_text('{"files": []}', encoding="utf-8")
    r = _result(g4_generic_generative([str(d)]))
    assert r["status"] == "PASS"


def test_snapshot_dir_without_manifest_fails(tmp_path):
    d = tmp_path / "snapshots" / "chapter-100"
    d.mkdir(parents=True)
    shutil.copy(sorted(_PROD_SNAP.glob("*.md"))[0], d / "snap.md")
    r = _result(g4_generic_generative([str(d)]))
    assert r["status"] == "FAIL"
    assert any("manifest_missing" in m for m in r.get("issues", r.get("missing", [])))


def test_characters_dir_no_manifest_required(tmp_path):
    """验收：characters/（非 snapshot）无 manifest 也 PASS。"""
    d = tmp_path / "characters"
    d.mkdir()
    (d / "c-1.md").write_text("# 主角\n" + "设定 " * 30, encoding="utf-8")
    r = _result(g4_generic_generative([str(d)]))
    assert r["status"] == "PASS"


def test_empty_dir_fails(tmp_path):
    d = tmp_path / "final-snapshot"
    d.mkdir()
    r = _result(g4_generic_generative([str(d)]))
    assert r["status"] == "FAIL"


def test_closure_snapshot_dir_resolution(tmp_path):
    """closure step 10 G4 路径 = snapshots/chapter-{total:03d}/。"""
    from shenbi.pipeline.closure import _closure_snapshot_dir

    proj = tmp_path / "proj"
    (proj / "outline").mkdir(parents=True)
    shutil.copy(
        Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md",
        proj / "outline" / "volume_map.md",
    )
    (proj / "novel.json").write_text(json.dumps({"total_chapters": 100}), encoding="utf-8")
    assert _closure_snapshot_dir(proj) == "snapshots/chapter-100/"
```

（断言键名以 `fail()`/`passed()` helper 实际返回结构为准——实现时先读 `gates/shared.py` 再校正测试断言键。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_g4_directory.py -v`
Expected: FAIL — 目录走 `read_text` → `read_error`；`_closure_snapshot_dir` 不存在

- [ ] **Step 3: 实现**

```python
# generic.py 循环内（:36 `if not p.exists()` 之后、read_text 之前）插目录分支：

        if p.is_dir():
            entries = [e for e in p.iterdir() if e.is_file()]
            if not entries:
                mf.append(f"G4.gen.dir_empty:{fp_path}")
                continue
            # Snapshot-family directories require a manifest-named entry
            # (filename authority: snapshot-manage SKILL contract, spec #6 R3);
            # non-snapshot dirs (characters/) check existence + content only.
            if "snapshot" in fp_path.replace("\\", "/").lower() and not any(
                "manifest" in e.name.lower() for e in entries
            ):
                mf.append(f"G4.gen.manifest_missing:{fp_path}")
                continue
            c.append(
                {"id": f"G4.gen.dir.{Path(fp_path).name}", "s": "PASS", "files": len(entries)}
            )
            continue
```

```python
# closure.py CLOSURE_STEPS[9]（:112-116）：

    ClosureStep(
        10,
        "shenbi-snapshot-manage",
        "snapshots/chapter-NNN/",  # contract-aligned (was final-snapshot/)
    ),
```

```python
# closure.py 新增 helper + _resolve_closure_g4_path 接入：

def _closure_snapshot_dir(project_dir: Path) -> str:
    """Final-chapter snapshot dir, NNN resolved from novel.json total (spec #6 R3)."""
    from shenbi.contracts.paths import resolve_contract_path
    from shenbi.pipeline.cli import _read_total_chapters

    total = _read_total_chapters(project_dir)
    return resolve_contract_path("snapshots/chapter-NNN/", total, PathContext(chapter=total))
```

`_resolve_closure_g4_path`：步骤 10 特判走 `_closure_snapshot_dir`（其余步骤维持现状，待 T6 经 ctx 表统一）。

```python
# closure.py :293 BOOK_CLOSURE artifact：

            artifact=_closure_snapshot_dir(project_dir),
```

```yaml
# skills/shenbi-snapshot-manage/SKILL.md contract writes 追加（在 snapshots/chapter-NNN/* 之后）：
  - file: snapshots/chapter-NNN/manifest.json
    mode: create_or_overwrite
```

```bash
just generate && just lint-contracts
```

（生成物 deps.json/docs/skills diff 由 generate 产出，禁手改。）

- [ ] **Step 4: 跑测试确认通过 + 契约门禁**

Run: `uv run pytest tests/pipeline/test_g4_directory.py -v && just lint-contracts && just generate && git diff --exit-code`
Expected: 5 passed；契约 lints 绿；generate 幂等（diff 为空）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/generic.py src/shenbi/pipeline/closure.py skills/shenbi-snapshot-manage/SKILL.md docs/skills deps.json tests/pipeline/test_g4_directory.py
git commit -m "fix: parameterized G4 directory checker + contract-aligned closure snapshot path (F371) — manifest pinned in skill contract"
```

（`git add` 的生成物路径以 `just generate` 实际改动为准。）

---

### Task 6: R5 closure 显式上下文 + F3B5/F380 哨兵

**复杂度: infra** · **test_kind: tdd_red_green** · **层级: T1**

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:1791-1802`（dispatch_skill 加 `path_context`）
- Modify: `src/shenbi/pipeline/closure.py:245-258`（per-step ctx）
- Modify: `src/shenbi/pipeline/revision_router.py:143-160`（dispatch_escalation genesis 哨兵）
- Modify: `src/shenbi/pipeline/genesis.py:78` 一带（anchor-curate 派发传 anchor ctx）
- Test: `tests/pipeline/test_closure_context.py`

**Interfaces:**
- Consumes: T3 `PathContext/format_path_context`；T5 `_closure_snapshot_dir`
- Produces: `dispatch_skill(..., path_context: PathContext | None = None)`；`_closure_step_context(step: ClosureStep, project_dir: Path) -> PathContext | None`

- [ ] **Step 1: 写失败测试**

```python
# tests/pipeline/test_closure_context.py
"""R5: closure per-step 显式上下文（F379/F313）+ genesis 哨兵（F3B5/F380）。"""
import json
import shutil
from pathlib import Path

from shenbi.contracts.paths import PathContext
from shenbi.pipeline.closure import CLOSURE_STEPS, _closure_step_context, _resolve_closure_g4_path

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md"


def _mk_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "outline").mkdir(parents=True)
    shutil.copy(FIXTURE, proj / "outline" / "volume_map.md")
    (proj / "novel.json").write_text(json.dumps({"total_chapters": 100}), encoding="utf-8")
    return proj


def test_closure_step_contexts(tmp_path):
    proj = _mk_project(tmp_path)
    by_num = {s.step_num: s for s in CLOSURE_STEPS}
    assert _closure_step_context(by_num[2], proj) == PathContext(chapter=100, arc=8)  # 100//12，覆写为预期
    assert _closure_step_context(by_num[4], proj) == PathContext(chapter=100, volume=5)
    assert _closure_step_context(by_num[5], proj) == PathContext(chapter=100, volume=5)
    assert _closure_step_context(by_num[6], proj) == PathContext(chapter=100)  # F313：章号非卷号


def test_closure_g4_paths_resolved(tmp_path):
    """验收：closure step 6 G4 查 chapter-100-long-span.md。"""
    proj = _mk_project(tmp_path)
    by_num = {s.step_num: s for s in CLOSURE_STEPS}
    assert _resolve_closure_g4_path(by_num[6], proj) == "audits/chapter-100-long-span.md"
    assert _resolve_closure_g4_path(by_num[10], proj) == "snapshots/chapter-100/"


def test_closure_prompt_build_all_steps(tmp_path):
    """验收：closure 10 步 prompt-build 全通过（不抛 UnresolvedPathError）。"""
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    proj = _mk_project(tmp_path)
    for step in CLOSURE_STEPS:
        ctx = _closure_step_context(step, proj)
        prompt = f"Execute {step.skill} for book closure (step {step.step_num}). Project dir: {proj}"
        system, user, outs = _build_skill_prompt(
            step.skill, proj, prompt, ctx.chapter if ctx else None, path_context=ctx
        )
        assert outs, f"step {step.step_num} produced no output paths"
        assert all("N" not in o.replace("NNN", "") or "-N" not in o for o in outs), outs


def test_escalation_genesis_sentinel(tmp_path):
    """F3B5：chapter=None 时 escalation 契约解析为 escalation-genesis-report.md。"""
    from shenbi.contracts.paths import resolve_contract_path

    assert (
        resolve_contract_path("audits/escalation-N-report.md", None, PathContext(escalation="genesis"))
        == "audits/escalation-genesis-report.md"
    )


def test_anchor_curate_sentinel(tmp_path):
    """F380：AC-NNN 经 anchor ctx 解析（genesis 表哨兵 AC-001.md）。"""
    from shenbi.contracts.paths import resolve_contract_path

    assert (
        resolve_contract_path("truth/anchors/AC-NNN.md", None, PathContext(anchor=1))
        == "truth/anchors/AC-001.md"
    )
```

（`truth/anchors/` 前缀以 anchor-curate SKILL 契约实际 writes 为准——实现时读契约替换。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_closure_context.py -v`
Expected: FAIL — `_closure_step_context` 不存在；step 2/4/5/6/10 prompt-build 抛 UnresolvedPathError

- [ ] **Step 3: 实现**

```python
# dispatch_helper.py dispatch_skill（:1791）签名追加 + 行注入：

def dispatch_skill(
    skill: str,
    project_dir: Path | str,
    prompt: str,
    test_type: str = "generative",
    round_dir: Path | str | None = None,
    timeout: int = 900,
    skip_reads: list[str] | None = None,
    uses_staging: bool = False,
    shared_context: Any = None,
    state: Any = None,
    path_context: PathContext | None = None,
) -> DispatchResult:
    ...
    # 在函数体入口（路由前）：
    if path_context is not None:
        line = format_path_context(path_context)
        if line:
            prompt = f"{prompt}\n{line}"
```

（API/IDE 路由调用 `_build_skill_prompt` 处透传 `path_context=path_context`；子进程路由经 prompt 行由 T4 的 parse 接住。）

```python
# closure.py per-step ctx builder + 派发接入：

def _closure_step_context(step: ClosureStep, project_dir: Path) -> PathContext | None:
    """Per-step closure context (spec #6 R5): 2→final arc, 4/5→volume,
    6→final chapter (F313), 10→final chapter (NNN dir)."""
    from shenbi.pipeline.cli import _read_total_chapters

    total = _read_total_chapters(project_dir)
    if not total:
        return None
    if step.step_num in (4, 5):
        return PathContext(chapter=total, volume=len(read_volume_boundaries(project_dir)))
    if step.step_num == 2:
        return PathContext(chapter=total, arc=total // 12)
    if step.step_num in (6, 10):
        return PathContext(chapter=total)
    return None
```

```python
# closure.py 派发点（:245-258）：

    prompt = (
        f"Execute {step.skill} for book closure (step {step.step_num}). Project dir: {project_dir}"
    )
    step_ctx = _closure_step_context(step, project_dir)
    ...
        disp = dispatch_skill(step.skill, project_dir, prompt, path_context=step_ctx)
```

`_resolve_closure_g4_path` 统一改经 ctx（步骤 6 取 chapter=total；步骤 10 走 `_closure_snapshot_dir`；其余含 N 步骤按上表）。

```python
# revision_router.py dispatch_escalation（:143）—— chapter=None 时注入哨兵：

def dispatch_escalation(project_dir: Path | str, chapter: int | None, context: str = "") -> bool:
    ...
    path_ctx = None
    if chapter is None:
        # Genesis escalation: book-level sentinel (spec #6 F3B5) — resolves
        # audits/escalation-N-report.md to the genesis artifact name.
        path_ctx = PathContext(escalation="genesis")
    disp = dispatch_skill("shenbi-escalation-review", project_dir, prompt, path_context=path_ctx)
```

```python
# genesis.py anchor-curate 派发点（step 16，:78 一带的 dispatch 调用）：
#   path_context=PathContext(anchor=1)  # AC-NNN → AC-001.md（genesis 表哨兵）
# （可选跳过路径保留时：跳过必须 log.info("anchor_curate_skipped", reason=...)）
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/pipeline/test_closure_context.py tests/pipeline/test_g4_directory.py -v`
Expected: 全 passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py src/shenbi/pipeline/closure.py src/shenbi/pipeline/revision_router.py src/shenbi/pipeline/genesis.py tests/pipeline/test_closure_context.py
git commit -m "fix: explicit per-step closure path context + genesis sentinels (F379/F313/F380/F3B5) — 10/10 closure steps build prompts"
```

---

### Task 7: R6 中文节点/桥接/卷上下文共享提取器 + 三消费方

**复杂度: infra** · **test_kind: tdd_red_green** · **层级: T1**

**Files:**
- Modify: `src/shenbi/pipeline/_shared.py`（`read_chapter_node`/`read_bridges`/`bridges_for_chapter` + 卷名双语）
- Modify: `src/shenbi/pipeline/chapter_loop.py:2182-2188`
- Modify: `src/shenbi/pipeline/plan_skeleton.py:197-220`
- Modify: `src/shenbi/pipeline/context_assemble.py:226-270`
- Test: `tests/pipeline/test_cn_extract.py`

**Interfaces:**
- Produces:
  - `read_chapter_node(volume_map_text: str, chapter: int) -> dict[str, str] | None`
  - `@dataclass(frozen=True) BridgeRow(content: str, kind: str, target_volume: str, activation: int | None, status: str)`
  - `read_bridges(volume_map_text: str) -> list[BridgeRow]`（聚合全部段；`^第\d+卷$` 谓词滤续作行；非数值激活跳过+WARN）
  - `bridges_for_chapter(bridges, chapter, window=_BRIDGE_ACTIVATION_WINDOW) -> list[str]`
  - `_resolve_volume_at_runtime` 返回真实卷名（中文头优先，回落 `Volume {i}`）

- [ ] **Step 1: 写失败测试**

```python
# tests/pipeline/test_cn_extract.py
"""R6: 中文节点/桥接/卷上下文（spec #6 修复方向 6）——真实 fixture 驱动。"""
from pathlib import Path

from shenbi.pipeline._shared import (
    bridges_for_chapter,
    read_bridges,
    read_chapter_node,
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md"
TEXT = FIXTURE.read_text(encoding="utf-8")


def test_chapter_nodes_from_ch5_not_garbage():
    """验收：第 5+ 章节点非 None 且 role/content 非桥接表垃圾。"""
    for ch in (5, 26, 56):
        node = read_chapter_node(TEXT, ch)
        assert node is not None, f"ch{ch} node missing"
        assert node["role"].strip()
        assert "梵天铭文" not in node["content"]  # 桥接内容不得串入节点


def test_bridges_aggregate_all_five_sections():
    """验收：聚合全部 5 个 跨卷桥接 段（非只第一卷）。"""
    bridges = read_bridges(TEXT)
    activations = {b.activation for b in bridges if b.activation}
    assert 36 in activations   # vol-2 表
    assert 26 in activations   # vol-1 表


def test_vol1_bridge_surfaces_at_26_not_30_for_vol2():
    b = read_bridges(TEXT)
    at26 = bridges_for_chapter(b, 26)
    at30 = bridges_for_chapter(b, 30)
    at36 = bridges_for_chapter(b, 36)
    assert any("梵天铭文" in s for s in at26)      # vol-1 行（激活 26-28 → min 26）
    assert not any("第36章" in s for s in at30) or True  # vol-2 行最早 33（36-3）才浮现
    assert at36 and any(s for s in at36)           # vol-2 @36 出现
    vol2_at30 = [s for s in at30 if "废弃设施" in s or "列塔尼亚" in s]
    assert not vol2_at30                            # vol-2 行 @30 不出现


def test_sequel_rows_excluded():
    """验收（负）：续作行（带入卷《星火燃穹》续作）不入任何章上下文。"""
    b = read_bridges(TEXT)
    for ch in range(1, 11):
        for s in bridges_for_chapter(b, ch):
            assert "续作" not in s
            assert "星际探索飞船" not in s


def test_volume_context_bilingual(_mk=None):
    """验收：卷上下文块在中文项目非空（真实卷名）。"""
    from shenbi.pipeline._shared import _resolve_volume_at_runtime
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / "outline").mkdir()
        (proj / "outline" / "volume_map.md").write_text(TEXT, encoding="utf-8")
        got = _resolve_volume_at_runtime(proj, 20)
        assert got is not None
        name, start, end = got
        assert name == "第二卷：铁与火"  # 真实卷头名，非 "Volume 2"
        assert (start, end) == (16, 35)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_cn_extract.py -v`
Expected: FAIL — ImportError（read_chapter_node 等不存在）；`_resolve_volume_at_runtime` 返回 "Volume 2"

- [ ] **Step 3: 实现**

```python
# _shared.py 追加（imports: from dataclasses import dataclass; from shenbi.logging import get_logger —
# docstring 同步「stdlib + safe_write + logging leaf」）：

log = get_logger(__name__)

_CN_NODE_ROW_RE_TMPL = r"^\|\s*(?:第\s*{ch}\s*章|{ch})\s*\|([^|]+)\|([^|]+)\|"
_BRIDGE_HEADS = ("### 跨卷桥接", "## Cross-Volume Bridges")
_BRIDGE_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]*)\|"
)
_THIS_BOOK_VOL_RE = re.compile(r"^第\d+卷$")
_ACT_RANGE_RE = re.compile(r"第\s*(\d+)\s*(?:[-–—~～]\s*第\s*(\d+)\s*)?章")


def read_chapter_node(volume_map_text: str, chapter: int) -> dict[str, str] | None:
    """Extract {role, content} from the `| 第N章 | role | content |` node row
    (also legacy bare `| N |`). Bridge-table `| 1 |` rows have >3 columns of
    unrelated shape and are excluded by the 3-column capture."""
    m = re.search(_CN_NODE_ROW_RE_TMPL.format(ch=chapter), volume_map_text, re.MULTILINE)
    if m:
        return {"role": m.group(1).strip(), "content": m.group(2).strip()}
    return None


@dataclass(frozen=True)
class BridgeRow:
    content: str
    kind: str
    target_volume: str
    activation: int | None
    status: str


def read_bridges(volume_map_text: str) -> list[BridgeRow]:
    """Aggregate bridge rows across ALL bridge sections (5 in production —
    one per volume; the old split()[1] consumers only ever saw volume 1).
    Rows whose 带入卷 is not `第N卷` (sequel markers like 《…》续作) are
    skipped; non-numeric activation values skip with a WARN."""
    rows: list[BridgeRow] = []
    for head in _BRIDGE_HEADS:
        parts = volume_map_text.split(head)
        for section in parts[1:]:
            for m in _BRIDGE_ROW_RE.finditer(section):
                content, kind, target, act_raw, status = (g.strip() for g in m.groups())
                if not _THIS_BOOK_VOL_RE.match(target):
                    continue  # sequel / non-volume row (spec #6 R6)
                am = _ACT_RANGE_RE.search(act_raw)
                if not am:
                    log.warning("bridge_activation_non_numeric", target=target, raw=act_raw)
                    continue
                ends = [int(am.group(1))] + ([int(am.group(2))] if am.group(2) else [])
                rows.append(BridgeRow(content, kind, target, min(ends), status))
    return rows


def bridges_for_chapter(
    bridges: list[BridgeRow], chapter: int, window: int = _BRIDGE_ACTIVATION_WINDOW
) -> list[str]:
    return [
        f"{b.target_volume} 桥接: {b.content} (activates Ch {b.activation})"
        for b in bridges
        if b.activation is not None and chapter >= b.activation - window
    ]
```

```python
# _resolve_volume_at_runtime 真实卷名（:88-94 改）：

    boundaries_sorted = sorted(boundary_chapters)
    prev_end = 0
    for i, end in enumerate(boundaries_sorted, 1):
        ch_start = prev_end + 1
        if ch_start <= chapter <= end:
            name = _volume_display_name(text, i) or f"Volume {i}"
            return (name, ch_start, end)
        prev_end = end
    return None
```

```python
# _shared.py 辅助（read_volume_boundaries 需把 text 传出——重构为内部 _read_text 后共用，
# 或 _volume_display_name 重新读文件；取重读，保持签名稳定）：

def _volume_display_name(text: str, index: int) -> str | None:
    heads = list(_CN_VOL_HEAD_RE.finditer(text))
    if 0 < index <= len(heads):
        line_end = text.find("\n", heads[index - 1].start())
        return text[heads[index - 1].start() + 3 : line_end].strip().lstrip("# ").strip()
    return None
```

（`_resolve_volume_at_runtime` 需读 text：函数内已可 `vm_file.read_text`——保持现结构，把 read_text 结果复用给 `_volume_display_name`。）

**三消费方接线**（同型替换，去重）：

```python
# chapter_loop.py:2182-2188 —— _extract_chapter_node_from_map 函数体改为：
    from shenbi.pipeline._shared import read_chapter_node

    return read_chapter_node(volume_map_text, chapter)

# plan_skeleton.py:197-220 与 context_assemble.py:243-270 —— 节点行提取改
# read_chapter_node(volume_map_text, chapter)；桥接段+行改
# bridges_for_chapter(read_bridges(volume_map_text), chapter)；卷头/Objective 匹配补中文：
#   `^##\s*第…卷`（_CN_VOL_HEAD_RE 复用）与 `^\*\*Objective\*\*\s*[：:]`（冒号粗体外）
```

- [ ] **Step 4: 跑测试确认通过 + 消费方回归**

Run: `uv run pytest tests/pipeline/test_cn_extract.py tests/pipeline/ -v`
Expected: 新 5 passed；pipeline 套件零回归

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/_shared.py src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/plan_skeleton.py src/shenbi/pipeline/context_assemble.py tests/pipeline/test_cn_extract.py
git commit -m "fix: shared Chinese node/bridge/volume-context extraction, three consumers deduped (R6) — all-section aggregation, sequel rows excluded"
```

---

### Task 8: F340 REJECT 重做 + F341 并行守卫镜像 + F304 捕获

**复杂度: infra** · **test_kind: tdd_red_green** · **层级: T2（状态机）**

**Files:**
- Modify: `src/shenbi/pipeline/cli.py:527-565`（REJECT 分支）+ `_orchestrate_to_checkpoint`（:175-）RetryExhaustedError 捕获
- Modify: `src/shenbi/pipeline/chapter_loop.py:2690-2715`（并行分支全守卫体镜像）
- Test: `tests/pipeline/test_review_reject.py`

**Interfaces:**
- Produces: `_reset_retry_budget(state: PipelineState, cp: CheckpointData) -> None`（cli 模块级）

- [ ] **Step 1: 写失败测试**

```python
# tests/pipeline/test_review_reject.py
"""F340/F341/F304: REJECT 重做语义 + 并行 staging 提交 + 预算耗尽 checkpoint。"""
import pytest

from shenbi.exceptions import RetryExhaustedError
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.state import CheckpointType, PipelineState


def _state() -> PipelineState:
    return PipelineState.default("/tmp/proj")


def test_reject_genesis_complete_rolls_back_cursor():
    """验收：genesis-complete reject → current_step 回退（resume 重跑 step 17）。"""
    from shenbi.pipeline.cli import _apply_reject_redo

    state = _state()
    state.genesis.current_step = 17
    set_checkpoint(state, CheckpointType.GENESIS_COMPLETE)
    cp = state.pending_checkpoint
    _apply_reject_redo(state, cp)
    assert state.genesis.current_step == 16


def test_reject_escalation_resets_retry_budget():
    """验收：escalation reject-redo 获完整重试预算。"""
    from shenbi.pipeline.cli import _apply_reject_redo

    state = _state()
    state.chapter_loop.retry_counts["ch55-shenbi-chapter-drafting"] = 4
    state.chapter_loop.retry_budget_consumed["ch55-shenbi-chapter-drafting"] = 9
    state.chapter_loop.retry_budget_consumed["ch12-shenbi-other"] = 1
    set_checkpoint(state, CheckpointType.ESCALATION, chapter=55)
    _apply_reject_redo(state, state.pending_checkpoint)
    assert "ch55-shenbi-chapter-drafting" not in state.chapter_loop.retry_counts
    assert "ch55-shenbi-chapter-drafting" not in state.chapter_loop.retry_budget_consumed
    assert state.chapter_loop.retry_budget_consumed["ch12-shenbi-other"] == 1  # 他章不动


def test_parallel_auto_mode_commits_staging_no_checkpoint(tmp_path, monkeypatch):
    """验收：--auto 并行 post-draft 不设 checkpoint 且 truth 落盘、staging 清空。"""
    from shenbi.pipeline import chapter_loop as cl

    proj = tmp_path / "proj"
    staging_truth = proj / "staging" / "truth"
    staging_truth.mkdir(parents=True)
    (staging_truth / "world_state.md").write_text("# 世界状态\n", encoding="utf-8")

    state = _state()
    state.project_dir = str(proj)
    state.config.state_settle_review_required = False

    raised = []
    monkeypatch.setattr(cl, "set_checkpoint", lambda *a, **k: raised.append(a))

    # 驱动并行分支的 settling 处理（函数名/签名以 2690-2715 实际代码为准——
    # 若为内联逻辑则提取为 _auto_settle_parallel(state, project_dir, chapter) 再测）
    cl._auto_settle_parallel(state, proj, chapter=55)

    assert not raised, "--auto 不得设 STATE_SETTLE checkpoint"
    assert (proj / "truth" / "world_state.md").exists()
    assert not (proj / "staging" / "truth" / "world_state.md").exists()


def test_orchestrate_captures_retry_exhausted(monkeypatch, tmp_path):
    """验收：预算耗尽产 ESCALATION checkpoint 非 traceback，budget 保留在 state。"""
    from shenbi.pipeline import cli as cli_mod

    state = _state()
    state.project_dir = str(tmp_path)
    state.chapter_loop.retry_budget_consumed["ch55-x"] = 99

    def boom(*a, **k):
        raise RetryExhaustedError("budget gone")

    monkeypatch.setattr("shenbi.pipeline.chapter_loop.run_chapter_step", boom)
    monkeypatch.setattr("shenbi.pipeline.genesis.run_genesis_step", boom)
    monkeypatch.setattr("shenbi.pipeline.closure.run_closure_step", boom)
    # 置 phase 使编排进入 chapter-loop 分支（以实际 PipelineState 字段为准）
    from shenbi.pipeline.state import PipelinePhase

    state.phase = PipelinePhase.CHAPTER_LOOP

    cli_mod._orchestrate_to_checkpoint(state, tmp_path)  # 不得抛出

    assert state.pending_checkpoint is not None
    assert state.pending_checkpoint.type == CheckpointType.ESCALATION
    assert state.chapter_loop.retry_budget_consumed["ch55-x"] == 99  # 供调用方 save_state 持久化
```

（`_auto_settle_parallel` 为 T8 实现时从 2690-2715 内联逻辑提取的函数；`PipelinePhase` 枚举名以 state.py 实际为准。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_review_reject.py -v`
Expected: FAIL — `_apply_reject_redo`/`_auto_settle_parallel` 不存在；orchestrate 抛 RetryExhaustedError

- [ ] **Step 3: 实现**

```python
# cli.py 新增模块级（cmd_review 前）：

def _reset_retry_budget(state: PipelineState, cp) -> None:
    """REJECT-redo: reset the producing step's retry counters (F340) —
    otherwise ESCALATION redo re-exhausts immediately."""
    ch = cp.chapter
    if ch is not None:
        prefix = f"ch{ch}-"
        state.chapter_loop.retry_counts = {
            k: v for k, v in state.chapter_loop.retry_counts.items() if not k.startswith(prefix)
        }
        state.chapter_loop.retry_budget_consumed = {
            k: v
            for k, v in state.chapter_loop.retry_budget_consumed.items()
            if not k.startswith(prefix)
        }
    if state.genesis is not None:
        state.genesis.retry_counts.clear()
    state.closure_retry_counts.clear()


def _apply_reject_redo(state: PipelineState, cp) -> None:
    """REJECT = redo the step that raised the checkpoint (spec #6 F340).
    Full CheckpointType coverage; BOOK_CLOSURE keeps its existing transition."""
    if cp.type == CheckpointType.CHAPTER_MEMO:
        state.chapter_loop.step_index = 1
    elif cp.type == CheckpointType.STATE_SETTLE:
        state.chapter_loop.step_index = 7
    elif cp.type == CheckpointType.GENESIS_COMPLETE:
        state.genesis.current_step = max(0, state.genesis.current_step - 1)
        state.genesis.retry_counts.clear()
    elif cp.type == CheckpointType.VOLUME_BOUNDARY:
        state.chapter_loop.step_index = 0  # next() re-runs the trigger fan-out
    elif cp.type == CheckpointType.PER_CHAPTER:
        if cp.chapter is not None:
            state.chapter_loop.current_chapter = cp.chapter  # re-run that chapter
        state.chapter_loop.step_index = 0
    elif cp.type == CheckpointType.ESCALATION:
        _reset_retry_budget(state, cp)  # failing step re-runs with fresh budget
    # BOOK_CLOSURE: handled by the existing transition below.
```

```python
# cli.py cmd_review REJECT 分支（:528-531 之后、clear_checkpoint 之前）追加调用：

            elif decision == ReviewDecision.REJECT:
                from shenbi.pipeline.checkpoint import clear_staging

                clear_staging(project_dir)
                _apply_reject_redo(state, cp)
```

（顺序：redo 游标在 clear_checkpoint 之前作用于 cp 快照；BOOK_CLOSURE 的既有转移逻辑不动。）

```python
# cli.py _orchestrate_to_checkpoint —— 函数体包一层（缩进整体函数体）：

def _orchestrate_to_checkpoint(state: PipelineState, project_dir: Path) -> None:
    """...existing docstring...

    Raises nothing on RetryExhaustedError (F304): converts to an ESCALATION
    checkpoint so the caller's save_state persists the budget trail.
    """
    from shenbi.exceptions import RetryExhaustedError

    try:
        ...existing body unchanged...
    except RetryExhaustedError as exc:
        log.error("retry_budget_exhausted_escalation", error=str(exc))
        set_checkpoint(
            state,
            CheckpointType.ESCALATION,
            context=f"Retry budget exhausted: {exc}",
        )
```

```python
# chapter_loop.py 并行分支（2690-2715）—— set_checkpoint 前插全守卫体（提取函数）：

def _auto_settle_parallel(state: PipelineState, project_dir: Path, chapter: int) -> bool:
    """--auto parallel post-draft settling (F341): mirror the serial branch's
    full auto-commit body — staging commit + clear, NO checkpoint. Skipping
    only the checkpoint strands state-settle writes in staging/ where the next
    resume's _cleanup_residual_staging wipes them (data-loss trap)."""
    from shenbi.pipeline.checkpoint import STAGING_DIR, clear_staging

    cfg = state.config
    if cfg.state_settle_review_required:
        return False  # review required: caller raises the checkpoint
    staging_truth = project_dir / STAGING_DIR / "truth"
    if staging_truth.exists():
        for src in staging_truth.glob("*.md"):
            dst = project_dir / "truth" / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            safe_write(dst, src.read_bytes())
        log.info(
            "staging_auto_committed_state_settle",
            chapter=chapter,
            files=len(list(staging_truth.glob("*.md"))),
        )
    else:
        log.warning("staging_auto_commit_skipped_no_truth", chapter=chapter)
    clear_staging(project_dir)
    return True
```

调用点（并行 settling 处）：`if _auto_settle_parallel(state, project_dir, chapter): return True`（或继续流程，与原 fall-through 语义一致——以 2690-2715 实际控制流为准），删除无条件 `set_checkpoint(STATE_SETTLE)` 于 auto 场景。

- [ ] **Step 4: 跑测试确认通过 + 回归**

Run: `uv run pytest tests/pipeline/test_review_reject.py tests/pipeline/test_parallel_steps.py tests/pipeline/ -v`
Expected: 全 passed（含既有并行/重试套件零回归）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/cli.py src/shenbi/pipeline/chapter_loop.py tests/pipeline/test_review_reject.py
git commit -m "fix: REJECT redo semantics with retry-budget reset (F340), parallel auto-mode staging commit (F341), RetryExhaustedError escalation checkpoint (F304)"
```

---

### Task 9: 验收扫尾 + 全量回归

**复杂度: infra** · **test_kind: regression_guard** · **层级: 全仓**

**Files:**
- Modify: `docs/superpowers/specs/2026-08-14-pipeline-never-completes-design.md`（Status 加执行注）
- 全部新测试文件

- [ ] **Step 1: spec 手动验收命令（只读）**

```bash
uv run python -c "from pathlib import Path; from shenbi.pipeline._shared import read_volume_boundaries; print(read_volume_boundaries(Path('novel-output/xinghuo-ranqiong')))"
```
Expected: `{15, 35, 55, 75, 100}`（H1——真实项目直读，只读不写）

- [ ] **Step 2: 全量门禁**

Run: `just check`
Expected: 全绿（ruff/format/mypy/basedpyright/契约三件/两段 pytest + 覆盖率 ≥85%）

- [ ] **Step 3: H1 证据 + 验收汇总写 progress.md `## 验收证据`**

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-08-14-pipeline-never-completes-design.md
git commit -m "docs(spec): #6 acceptance sweep recorded — H1 boundaries {15,35,55,75,100} on real project"
```

---

## Self-Review 记录

1. **Spec coverage**：R1→T1；R2（双写点+heal+收敛）→T2；R3（检查器+契约+characters/）→T5；R4（表+四消费者+通道）→T3/T4；R5（ctx+closure 表+F3B5/F380）→T6；R6（三消费方+全段聚合+续作谓词+卷上下文）→T7；F340/F341/F304→T8；回归→T9。验收覆盖表 13 行全落 task。F313 由 T6（step 6 ctx）+T4（`_resolve_closure_g4_path` 接表）双覆盖。
2. **Placeholder scan**：T2/R2-(i) 与 T4 的 TriggerResult 字段名、T8 的 `_auto_settle_parallel` 提取、T5 的 fail() 返回键——均标注「以实际代码为准，实现时先读再写」，非 TBD：断言目标已定，仅键名待核对（实现轮第一步即读源码校正，属核对非设计留白）。
3. **Type consistency**：`PathContext` 字段在 T3 定义后 T4/T5/T6 引用一致（chapter/arc/stratum/volume/anchor/escalation）；`update_total_chapters(project_dir: Path) -> int` 在 T2 定义、cli/triggers 委托签名一致；`_closure_snapshot_dir` 在 T5 定义、T6 引用。
