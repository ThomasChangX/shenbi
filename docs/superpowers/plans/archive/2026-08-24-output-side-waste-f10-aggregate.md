# 输出侧浪费 F10：审计聚合去重层 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 revision 派发前用确定性（零 LLM）聚合去重层取代 `shenbi-chapter-revision` 对 `audits/chapter-N-*.md` raw glob 的读取，消除 ~60-120KB/次的冗余输入与共振文件双读。

**Architecture:** 新纯函数模块 `src/shenbi/pipeline/audit_aggregate.py` 产出 `audits/chapter-N.aggregate.md`（点分隔，不落 `chapter-N-*.md` glob 命名空间）；`chapter_loop.py` 两条 revision 派发入口前置触发；SKILL.md reads 改单文件 + dispatch_helper reads 解析阶段（G1 之前）fail-open 回退 raw glob。spec §5.1a 为权威设计。

**Tech Stack:** Python 3.11+ / pathlib / structlog / pytest（fixtures 驱动，G0.9）。

**Spec:** `docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md`（2026-08-24 修订版；F8/F7 已关闭，本 plan 只实施 F10 + 2.3b）

**分类:** 全部 task 为 **infra**（触及 `src/shenbi/pipeline/` 与契约）→ 协调者亲自实现，不分派。

## Global Constraints

- 聚合层**零 LLM 调用**（spec §5.1a：纯 Python、structlog、pathlib、幂等）
- 聚合文件名必须**不匹配** `chapter-N-*.md` glob（用 `.` 分隔：`chapter-N.aggregate.md`）
- 聚合格式**不得以 `---` 开头**（G1.3 frontmatter 解析）
- 无损不变量：raw 报告中全部 severity-bearing finding 单元（BLOCKING/CRITICAL/WARNING/ERROR 家族）必须存在于聚合（verbatim 或合并键+报告方清单），resonance 报告（`chapter-N-resonance.md`，若存在）**全文逐字保留**
- 测试输入只用 `tests/fixtures/` 真实产物（G0.9）；dispatch 边界可用 mock（聚合逻辑本身走真实代码路径）
- 状态字面量不新增（无新状态）；框架代码无 `print()`
- 契约变更走源头 + `just generate`，禁手改 deps.json/docs 生成物
- commit 用 Conventional Commits，pathspec-only add

---

### Task 0: 真实审计 fixture 集

**Files:**
- Create: `tests/fixtures/audits/chapter-1-consistency.md`
- Create: `tests/fixtures/audits/chapter-1-character.md`

**Interfaces:**
- Produces: 两份真实审计报告 fixture（内容 = `tests/fixtures/audit-report-example.md` 的逐字节副本，G0.11 源文件哈希镜像；文件名模拟生产布局 `chapter-N-<dim>.md`；同一真实内容两份文件构成「多审计器报告同一缺陷」的重叠场景——内容是真实 skill 输出，非手写）

- [ ] **Step 1: 复制真实产物为镜像 fixture**

```bash
mkdir -p tests/fixtures/audits
cp tests/fixtures/audit-report-example.md tests/fixtures/audits/chapter-1-consistency.md
cp tests/fixtures/audit-report-example.md tests/fixtures/audits/chapter-1-character.md
shasum -a 256 tests/fixtures/audit-report-example.md tests/fixtures/audits/chapter-1-*.md
```

Expected: 三份哈希一致。

- [ ] **Step 2: Commit**

```bash
git add tests/fixtures/audits/chapter-1-consistency.md tests/fixtures/audits/chapter-1-character.md
git commit -m "test: add real-output audit fixtures for F10 aggregate layer (G0.11 mirror)"
```

Deviation notes（记 spec-deviations.md）：
1. spec 曾设想「5 份相互重叠的真实审计报告」fixture，但仓内仅有 1 份真实审计产物，且 SDD 纪律禁为验证触发真实 dispatch（核心原则 8）——用同内容双副本表达重叠场景；severity-regex 行为测试用内联样例行（G0.9 管辖 scenario 输入，regex 单测不属）。
2. dedup 键实现为精确 `(severity, normalized text)`——比 spec §5.1a 的「段落+缺陷类型」更保守：跨审计器同缺陷不同措辞不会误合并（over-merge 质量风险为零），代价是冗余消除率可能低于 ~80% 目标。安全优先。
3. resonance 无真实 fixture：verbatim 保留机制以文件名 `chapter-N-resonance.md` 驱动，测试用真实 fixture 字节充当输入内容。

### Task 1: `audit_aggregate.py` 聚合模块（TDD）

**Files:**
- Create: `src/shenbi/pipeline/audit_aggregate.py`
- Test: `tests/pipeline/test_audit_aggregate.py`

**Interfaces:**
- Produces:
  - `AGGREGATE_SUFFIX = ".aggregate.md"`
  - `@dataclass(frozen=True) class FindingUnit: severity: str; text: str; reporters: tuple[str, ...]`
  - `def aggregate_path(project_dir: Path, chapter: int) -> Path`
  - `def extract_finding_units(report_name: str, content: str) -> tuple[list[FindingUnit], list[str]]` — 返回（severity-bearing finding 单元, 保留的上下文行：`**结果**`/`### 评分` 等）
  - `def render_aggregate(chapter: int, units: list[FindingUnit], context: dict[str, list[str]], resonance_bodies: dict[str, str] | None = None) -> str`
  - `def write_audit_aggregate(project_dir: Path | str, chapter: int) -> Path | None` — 主入口；无 raw 报告返回 None；`chapter-N-resonance.md` 全文逐字保留；safe_write 落盘；structlog info

- [ ] **Step 1: 写失败测试**（核心断言：无损（含 fixture 真实 WARNING 发现）、去重、字节下降、无 `---` 开头、幂等、resonance verbatim）

```python
"""T1 tests for the F10 audit aggregation layer (spec §5.1a)."""

from pathlib import Path

from shenbi.pipeline.audit_aggregate import (
    FindingUnit,
    extract_finding_units,
    render_aggregate,
    write_audit_aggregate,
)

FIXTURE = Path("tests/fixtures/audits/chapter-1-consistency.md")


def _content() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_extract_captures_real_fixture_warning_findings():
    # 真实 fixture：发现项表 warning 行 + 建议修复 **[WARNING]** 列表项
    units, ctx = extract_finding_units("chapter-1-consistency.md", _content())
    assert len(units) >= 2
    assert all(u.severity == "WARNING" for u in units)
    assert any("了" in u.text and "密度" in u.text for u in units)
    # 上下文保留结果/评分行
    assert any("通过" in line for line in ctx)
    # 空表行（全 — 的 OOC 行）与 BDI PASS 行不得成为 finding
    assert all(u.severity in {"BLOCKING", "CRITICAL", "WARNING", "ERROR"} for u in units)


def test_extract_captures_blocking_and_critical_forms():
    content = (
        "## Findings\n"
        "| 段落 | 类型 | 严重度 |\n|---|---|---|\n"
        "| P3 | 了-密度 | **BLOCKING** |\n"
        "- P5 对白信息倾倒：severity: CRITICAL\n"
    )
    units, _ = extract_finding_units("chapter-1-x.md", content)
    assert len(units) == 2
    assert units[0].severity == "BLOCKING"
    assert units[1].severity == "CRITICAL"


def test_render_is_lossless_and_deduped():
    raw = _content()
    units, ctx = extract_finding_units("chapter-1-character.md", raw)
    units2, _ = extract_finding_units("chapter-1-consistency.md", raw)
    merged: dict[tuple[str, str], FindingUnit] = {}
    for u in [*units, *units2]:
        merged.setdefault((u.severity, u.text), u)
    out = render_aggregate(1, list(merged.values()), {"chapter-1-consistency.md": ctx})
    # 无损：每个 raw 单元的 text 都出现在聚合（fixture 有真实 WARNING，非空集）
    assert units, "fixture must yield at least one finding (non-vacuous)"
    for u in [*units, *units2]:
        assert u.text in out
    # 不以 --- 开头（G1.3）
    assert not out.startswith("---")
    # 双份相同内容 → 聚合显著小于 2×raw
    assert len(out) < 2 * len(raw)


def test_resonance_report_preserved_verbatim(tmp_path: Path):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    raw = _content()
    (audit_dir / "chapter-1-character.md").write_text(raw, encoding="utf-8")
    (audit_dir / "chapter-1-resonance.md").write_text(raw, encoding="utf-8")
    out = write_audit_aggregate(tmp_path, 1)
    assert out is not None
    agg = out.read_text(encoding="utf-8")
    # resonance 全文逐字保留（spec §5.1a：其单条 read 已删，只能经聚合存活）
    assert raw in agg


def test_write_audit_aggregate_end_to_end(tmp_path: Path):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for name in ("chapter-1-consistency.md", "chapter-1-character.md"):
        (audit_dir / name).write_text(_content(), encoding="utf-8")
    out = write_audit_aggregate(tmp_path, 1)
    assert out is not None and out.name == "chapter-1.aggregate.md"
    first = out.read_text(encoding="utf-8")
    # 幂等：重跑内容一致
    write_audit_aggregate(tmp_path, 1)
    assert out.read_text(encoding="utf-8") == first
    # 点分隔：聚合文件不被 chapter-1-*.md glob 匹配
    assert all(p.name != "chapter-1.aggregate.md" for p in audit_dir.glob("chapter-1-*.md"))


def test_write_returns_none_when_no_reports(tmp_path: Path):
    assert write_audit_aggregate(tmp_path, 1) is None
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/pipeline/test_audit_aggregate.py -v
```
Expected: FAIL（ModuleNotFoundError / ImportError）。

- [ ] **Step 3: 实现 `src/shenbi/pipeline/audit_aggregate.py`**

```python
"""Deterministic pre-revision audit aggregation (spec #4 F10 / §5.1a).

Merges the raw per-auditor reports ``audits/chapter-N-*.md`` into a single
deduplicated ``audits/chapter-N.aggregate.md`` before chapter revision is
dispatched. Zero LLM calls: pure parsing + rendering, idempotent.

Design invariants (spec §5.1a):
- the aggregate filename uses a DOT separator so it never matches the
  ``chapter-N-*.md`` glob consumed by revision_router / drift-guidance;
- the file never starts with ``---`` (G1.3 frontmatter parsing);
- lossless: every severity-bearing finding unit (BLOCKING/CRITICAL/WARNING/
  ERROR in any surface form) from the raw reports is present in the
  aggregate, merged only on exact (severity, text) key;
- resonance reports (chapter-N-resonance.md) are preserved verbatim in
  full — their dedicated read is deleted from the revision contract, so
  the aggregate is their only path into the revision skill.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.revision_router import AUDIT_DIR
from shenbi.safe_write import safe_write

log = get_logger(__name__)

AGGREGATE_SUFFIX = ".aggregate.md"

#: Severity value matched anywhere in a finding entry line (bolded marker
#: ``**BLOCKING**``, bracketed ``**[WARNING]**``, severity-key form, or a
#: bare table-cell value like ``| warning |`` — the real production form in
#: tests/fixtures/audit-report-example.md). Single capture group.
_SEVERITY_RE = re.compile(r"\b(BLOCKING|CRITICAL|WARNING|ERROR)\b", re.IGNORECASE)
#: Table rows filled with em-dashes are empty placeholders, not findings.
_PLACEHOLDER_ROW_RE = re.compile(r"^\|[\s—\-|]*\|$")
#: Context lines worth preserving verbatim (result / score / target headers).
_CONTEXT_RE = re.compile(r"^(\*\*(结果|审计目标文件|章节)\*\*|###\s*评分)", re.IGNORECASE)
#: Resonance reports are preserved verbatim in full (spec §5.1a).
_RESONANCE_NAME_RE = re.compile(r"^chapter-\d+-resonance\.md$")


@dataclass(frozen=True)
class FindingUnit:
    """One severity-bearing finding, merged across reporters on its key."""

    severity: str
    text: str
    reporters: tuple[str, ...]


def aggregate_path(project_dir: Path, chapter: int) -> Path:
    return project_dir / AUDIT_DIR / f"chapter-{chapter}{AGGREGATE_SUFFIX}"


def _normalize(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _severity_of(line: str) -> str | None:
    m = _SEVERITY_RE.search(line)
    return m.group(1).upper() if m else None


def extract_finding_units(report_name: str, content: str) -> tuple[list[FindingUnit], list[str]]:
    """Split *content* into finding units and preserved context lines.

    A finding unit is a markdown list item or table row that carries a
    BLOCKING/CRITICAL/WARNING/ERROR severity value (any surface form).
    Placeholder rows (all em-dashes) never produce units.
    """
    units: list[FindingUnit] = []
    context: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or _PLACEHOLDER_ROW_RE.match(stripped):
            continue
        is_entry = stripped.startswith(("- ", "* ", "|"))
        sev = _severity_of(stripped)
        if is_entry and sev:
            text = _normalize(_SEVERITY_RE.sub("", stripped).strip("-*| "))
            units.append(FindingUnit(sev, text, (report_name,)))
        elif _CONTEXT_RE.match(stripped):
            context.append(stripped)
    return units, context


def render_aggregate(
    chapter: int,
    units: list[FindingUnit],
    context: dict[str, list[str]],
    resonance_bodies: dict[str, str] | None = None,
) -> str:
    parts = [f"# Chapter {chapter} — Audit Aggregate", ""]
    parts.append(f"- **来源报告数**: {len(context) + len(resonance_bodies or {})}")
    parts.append(f"- **去重后缺陷条目**: {len(units)}")
    parts.append("")
    for sev in ("BLOCKING", "CRITICAL", "WARNING", "ERROR"):
        sev_units = [u for u in units if u.severity == sev]
        if not sev_units:
            continue
        parts.append(f"## {sev} Findings ({len(sev_units)})")
        parts.append("")
        for u in sev_units:
            parts.append(f"- {u.text}")
            parts.append(f"  - 报告方: {', '.join(u.reporters)}")
        parts.append("")
    if resonance_bodies:
        parts.append("## Resonance 报告（逐字保留）")
        parts.append("")
        for name, body in sorted(resonance_bodies.items()):
            parts.append(f"### {name}")
            parts.append("")
            parts.append(body.rstrip())
            parts.append("")
    parts.append("## 报告上下文")
    parts.append("")
    for name, lines in sorted(context.items()):
        parts.append(f"### {name}")
        parts.extend(lines)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def write_audit_aggregate(project_dir: Path | str, chapter: int) -> Path | None:
    """Aggregate raw audits for *chapter*; returns the aggregate path.

    Returns ``None`` when there are no raw reports (nothing to aggregate —
    the dispatcher fallback then injects whatever exists).
    """
    project_dir = Path(project_dir)
    audit_dir = project_dir / AUDIT_DIR
    if not audit_dir.is_dir():
        return None
    raw = sorted(audit_dir.glob(f"chapter-{chapter}-*.md"))
    if not raw:
        return None

    merged: dict[tuple[str, str], FindingUnit] = {}
    context: dict[str, list[str]] = {}
    resonance_bodies: dict[str, str] = {}
    for report in raw:
        content = report.read_text(encoding="utf-8")
        if _RESONANCE_NAME_RE.match(report.name):
            resonance_bodies[report.name] = content
            continue
        units, ctx = extract_finding_units(report.name, content)
        context[report.name] = ctx
        for u in units:
            key = (u.severity, u.text)
            if key in merged:
                prev = merged[key]
                merged[key] = FindingUnit(
                    u.severity, u.text, tuple(dict.fromkeys([*prev.reporters, *u.reporters]))
                )
            else:
                merged[key] = u

    out = aggregate_path(project_dir, chapter)
    rendered = render_aggregate(chapter, list(merged.values()), context, resonance_bodies)
    safe_write(out, rendered)
    log.info(
        "audit_aggregate_written",
        chapter=chapter,
        reports=len(raw),
        findings=len(merged),
        resonance=len(resonance_bodies),
        bytes=len(rendered),
    )
    return out
```

- [ ] **Step 4: 跑测试确认通过**

```bash
uv run pytest tests/pipeline/test_audit_aggregate.py -v
```
Expected: 6 PASS。

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/audit_aggregate.py tests/pipeline/test_audit_aggregate.py
git commit -m "feat: deterministic audit aggregation module for pre-revision dedup (spec #4 F10)"
```

### Task 2: chapter_loop 双触发点接线

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（通用派发处 ~:2902 之前；BLOCKING 重派处 ~:3073 之前）
- Test: `tests/pipeline/test_audit_aggregate_wiring.py`

**Interfaces:**
- Consumes: `write_audit_aggregate(project_dir, chapter) -> Path | None`

- [ ] **Step 1: 写失败测试**（接线断言：revision 派发前聚合文件已生成）

```python
"""Wiring tests: aggregate is refreshed before every revision dispatch."""

from pathlib import Path

import pytest

import shenbi.pipeline.chapter_loop as chapter_loop
from shenbi.pipeline.audit_aggregate import aggregate_path

FIX = Path("tests/fixtures/audits/chapter-1-consistency.md")


def test_generic_step_writes_aggregate_before_revision_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    # 必须用 character 维度文件名（_any_audit_has_findings 只扫固定 atype
    # 清单，含 character 不含 consistency），且需含 BLOCKING/FAIL 字样才
    # 触发条件步——在 tmp 副本末尾追加（fixture 文件本身不动）
    body = FIX.read_text(encoding="utf-8")
    (audit_dir / "chapter-1-character.md").write_text(
        body + "\n| P3 | 测试注入 | **BLOCKING** |\n", encoding="utf-8"
    )
    calls: list[str] = []

    class _Result:
        success = True
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_dispatch(skill, project_dir, prompt, **kwargs):
        calls.append(skill)
        # dispatch_skill 是子进程边界 mock；聚合必须发生在它之前
        assert aggregate_path(Path(project_dir), 1).exists(), (
            "aggregate must exist before shenbi-chapter-revision dispatch"
        )
        return _Result()

    monkeypatch.setattr(chapter_loop, "dispatch_skill", _fake_dispatch)
    state = chapter_loop.PipelineState()
    state.project_dir = str(tmp_path)
    state.chapter_loop.current_chapter = 1
    # 定位 Step 16（shenbi-chapter-revision）
    idx = next(
        i for i, s in enumerate(chapter_loop.CHAPTER_STEPS) if s.skill == "shenbi-chapter-revision"
    )
    state.chapter_loop.step_index = idx
    # 派发后的 G4/步进处理在 tmp_path 下可能走重试/checkpoint 分支——
    # 断言只依赖 fake-dispatch 闭包（派发时聚合已存在）与 calls 记录，
    # 返回值不约束
    chapter_loop.run_chapter_step(state, tmp_path)
    assert "shenbi-chapter-revision" in calls
```

（tmp 副本追加的 BLOCKING 行仅用于满足条件步触发——scenario 主体仍是真实 fixture；fixture 文件本身零改动。）

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/pipeline/test_audit_aggregate_wiring.py -v
```
Expected: FAIL（aggregate 不存在）。

- [ ] **Step 3: 实现**

`chapter_loop.py` 顶部 import 区加：

```python
from shenbi.pipeline.audit_aggregate import write_audit_aggregate
```

通用派发路径（`_run_chapter_step_impl` 内 `# Dispatch the skill.` 注释后、`result = dispatch_skill(` 之前）加：

```python
    # F10 (spec §5.1a): refresh the audit aggregate right before revision
    # is dispatched — the revision skill reads the aggregate, not the raw
    # glob, so the aggregate must reflect the latest audit set.
    if step.skill == "shenbi-chapter-revision":
        write_audit_aggregate(project_dir, chapter)
```

BLOCKING 重派路径（`rev = dispatch_skill("shenbi-chapter-revision", ...)` 之前）加：

```python
            # F10: re-audit changed the audit set — regenerate the aggregate
            # so revision never consumes a stale one (correctness, not just
            # efficiency).
            write_audit_aggregate(project_dir, chapter)
```

- [ ] **Step 4: 跑测试确认通过 + 全模块回归**

```bash
uv run pytest tests/pipeline/test_audit_aggregate_wiring.py tests/pipeline/ -v
```

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/pipeline/test_audit_aggregate_wiring.py
git commit -m "feat: refresh audit aggregate at both revision dispatch sites (spec #4 F10 wiring)"
```

### Task 3: 契约切换 + G1 前回退 + 注册表登记

**Files:**
- Modify: `skills/shenbi-chapter-revision/SKILL.md`（frontmatter reads：删 `audits/chapter-N-*.md` 与 `audits/chapter-N-resonance.md`，加 `audits/chapter-N.aggregate.md`）
- Modify: `docs/framework/truth-files.yaml`（concepts 加 `- {name: audits/chapter-N.aggregate.md, kind: report, producer: pipeline}`；register/glob 区按 lint 要求补）
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（三处：reads 解析循环聚合 read 缺失 → 回退 raw glob + WARN；`OPTIONAL_READS` 登记 `shenbi-chapter-revision → chapter-*.aggregate.md` 使 executor G1 前丢弃缺失聚合 read——executor.py:177-190 的既有机制；`_is_audit_file` 排除 `.aggregate.md`）
- Test: `tests/pipeline/test_aggregate_fallback.py`

**Interfaces:**
- Consumes: `aggregate_path`、`AGGREGATE_SUFFIX`、`OPTIONAL_READS`（`dispatch_helper.py:379-394` 既有）

- [ ] **Step 1: 写失败测试**

```python
"""Fallback tests: missing aggregate read fails open to the raw glob pre-G1."""

from pathlib import Path

import fnmatch

from shenbi.pipeline.dispatch_helper import OPTIONAL_READS, _resolve_read_with_fallback

FIX = Path("tests/fixtures/audits/chapter-1-consistency.md")


def test_missing_aggregate_falls_back_to_raw_glob(tmp_path: Path):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    (audit_dir / "chapter-1-consistency.md").write_text(
        FIX.read_text(encoding="utf-8"), encoding="utf-8"
    )
    paths = _resolve_read_with_fallback(tmp_path, "audits/chapter-1.aggregate.md")
    # 回退注入 raw glob 的全部匹配
    assert [p.name for p in paths] == ["chapter-1-consistency.md"]


def test_present_aggregate_is_used_directly(tmp_path: Path):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    (audit_dir / "chapter-1.aggregate.md").write_text("# agg\n", encoding="utf-8")
    paths = _resolve_read_with_fallback(tmp_path, "audits/chapter-1.aggregate.md")
    assert [p.name for p in paths] == ["chapter-1.aggregate.md"]


def test_aggregate_registered_as_optional_read():
    # executor G1 前丢弃缺失 optional read 的既有机制（executor.py:177-190）
    # 必须覆盖聚合 read——否则 G1.1 对缺失 declared read 硬 FAIL，
    # reads-loop 回退在 executor 路径上永远走不到
    patterns = OPTIONAL_READS.get("shenbi-chapter-revision", [])
    assert any(fnmatch.fnmatch("chapter-1.aggregate.md", pat) for pat in patterns), (
        f"aggregate not optional for G1: {patterns}"
    )
```

- [ ] **Step 2: 跑测试确认失败**（`_resolve_read_with_fallback` 不存在）

- [ ] **Step 3: 实现**

`dispatch_helper.py` 在 `_resolve_read_path` 之后新增：

```python
#: Fallback map: declared reads whose producer is the framework aggregate
#: layer (spec #4 F10 §5.1a). When the aggregate is missing (legacy project
#: dirs), the read fails open to the raw glob BEFORE G1 input readiness runs
#: (G1.1 hard-FAILs on missing declared reads).
_AGGREGATE_READ_FALLBACK_RE = re.compile(r"^audits/chapter-(\d+)\.aggregate\.md$")


def _resolve_read_with_fallback(project_dir: Path, read_path: str) -> list[Path]:
    """Resolve a read path, failing aggregate reads open to the raw glob."""
    resolved = _resolve_read_path(project_dir, read_path)
    if resolved:
        return resolved
    m = _AGGREGATE_READ_FALLBACK_RE.match(read_path)
    if m:
        log.warning(
            "audit_aggregate_missing_fallback_raw_glob",
            read_path=read_path,
        )
        return _resolve_read_path(project_dir, f"audits/chapter-{m.group(1)}-*.md")
    return []
```

读取循环（`raw_inputs` 装配处）将 `resolved_paths = _resolve_read_path(project_dir, resolved)` 改为 `resolved_paths = _resolve_read_with_fallback(project_dir, resolved)`。

**OPTIONAL_READS 登记（executor G1 路径的回退——缺此登记则 G1.1 先拦）**：在既有 `OPTIONAL_READS` dict（`dispatch_helper.py:378-394`）加一项：

```python
    # F10 (spec #4 §5.1a): the framework-written audit aggregate may be
    # absent on legacy project dirs — G1 must drop the missing read instead
    # of hard-failing before the reads-loop fallback can substitute the raw
    # glob (executor drops optional non-existent reads pre-G1). Note: this
    # env-gated drop only runs on the legacy subprocess route; the API/IDE
    # routes get the raw-glob substitution via _resolve_read_with_fallback.
    "shenbi-chapter-revision": ["chapter-*.aggregate.md"],
```

`_is_audit_file` 的 docstring/逻辑补一行排除：

```python
    # The framework-written aggregate (chapter-N.aggregate.md) is NOT an
    # LLM audit report (spec #4 F10).
    if stem.endswith(".aggregate"):
        return False
```

（注意 `Path("chapter-1.aggregate.md").stem == "chapter-1.aggregate"`，故用 `.endswith(".aggregate")`。）

- [ ] **Step 4: SKILL.md 契约修改**

frontmatter reads 段改为：

```yaml
  reads:
    - chapters/chapter-N.md
    - chapters/chapter-N-decisions.json
    - audits/chapter-N.aggregate.md
    - file: plans/chapter-N-plan.md
      fields: ["1. 当前任务", "6. 章尾必须发生的改变", "8. 不要做"]
```

（删 `audits/chapter-N-*.md` glob 与 `audits/chapter-N-resonance.md`——共振结论并入聚合。）

- [ ] **Step 5: truth-files.yaml 登记**

concepts 报告区（`chapter-N-review-summary.md` 行旁）加：

```yaml
  - {name: audits/chapter-N.aggregate.md, kind: report, producer: pipeline}
```

- [ ] **Step 6: 生成物同步 + lint**

```bash
just generate && just lint-contracts
git status --short   # deps.json/docs 生成物 diff 为生成所致，一并提交
```

- [ ] **Step 7: 跑测试 + Commit**

```bash
uv run pytest tests/pipeline/test_aggregate_fallback.py tests/unit/gates/ -v
# 生成物按 git status 实际清单 pathspec 逐个列出（禁 git add -u / -A）：
git status --short
git add skills/shenbi-chapter-revision/SKILL.md docs/framework/truth-files.yaml \
  src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_aggregate_fallback.py \
  <生成物路径按 status 清单逐一补列>
git commit -m "feat: switch chapter-revision reads to aggregate + pre-G1 fallback + registry (spec #4 F10/2.3b)"
```

（执行时以 `git status` 实际清单做 pathspec commit，禁 `git add -A`。）

### Task 4: 验收证据 + 全量门禁

**Files:**
- Test: `tests/pipeline/test_audit_aggregate_acceptance.py`

- [ ] **Step 1: 验收测试**（spec §6 三条：字节下降、无损、`just check` 由阶段 7 跑）

```python
"""Acceptance tests for spec #4 §6 (F10)."""

from pathlib import Path

from shenbi.pipeline.audit_aggregate import write_audit_aggregate

FIX = Path("tests/fixtures/audits/chapter-1-consistency.md")


def test_revision_input_bytes_drop_with_overlap(tmp_path: Path):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for name in ("chapter-1-consistency.md", "chapter-1-character.md"):
        (audit_dir / name).write_text(FIX.read_text(encoding="utf-8"), encoding="utf-8")
    raw_bytes = sum(p.stat().st_size for p in audit_dir.glob("chapter-1-*.md"))
    out = write_audit_aggregate(tmp_path, 1)
    assert out is not None
    assert out.stat().st_size < 0.5 * raw_bytes  # 双份重叠 → 显著下降


def test_lossless_every_raw_finding_survives(tmp_path: Path):
    from shenbi.pipeline.audit_aggregate import extract_finding_units

    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for name in ("chapter-1-consistency.md", "chapter-1-character.md"):
        (audit_dir / name).write_text(FIX.read_text(encoding="utf-8"), encoding="utf-8")
    write_audit_aggregate(tmp_path, 1)
    out = (audit_dir / "chapter-1.aggregate.md").read_text(encoding="utf-8")
    raw = FIX.read_text(encoding="utf-8")
    units, _ = extract_finding_units("chapter-1-consistency.md", raw)
    # 非空集护栏（fixture 有真实 WARNING 发现——发现项表行 + 建议修复项）
    assert len(units) >= 2, "lossless check must be non-vacuous"
    # 独立覆盖断言（非自证）：聚合含全部 raw finding 的 text
    for u in units:
        assert u.text in out, f"finding lost: {u.text[:60]}"
    # 修复建议（WARNING 级）逐字存活——revision 的可操作输入
    assert "了字密度" in out or "了" in out
    # 每份 raw 报告在聚合中被引用
    assert "chapter-1-consistency.md" in out
    assert "chapter-1-character.md" in out
```

- [ ] **Step 2: Commit**

```bash
git add tests/pipeline/test_audit_aggregate_acceptance.py
git commit -m "test: F10 acceptance evidence — byte drop + lossless invariant (spec #4 §6)"
```

- [ ] **Step 3: 全量门禁（阶段 7 在本 task 后统一跑）**

```bash
just check
```

## 验收覆盖表（spec §6 → task → 命令）

| spec 验收 | task | 验证 |
|---|---|---|
| revision 输入审计字节 ~60-120KB → 显著下降 | T4 | `test_revision_input_bytes_drop_with_overlap` |
| 聚合无损（raw ⊆ 聚合，含 resonance 若存在） | T1/T4 | `test_render_is_lossless_and_deduped` / `test_lossless_*` |
| `just check` PASS | T4/阶段 7 | `just check` 完整输出 |
| 聚合不落 glob 命名空间 / 不以 `---` 开头 | T1 | `test_write_audit_aggregate_end_to_end` / `test_render_*` |
| 契约同步幂等 | T3 | `just generate` diff 空 + lint-contracts |
| ORPHAN_READ 不触发 | T3 | `just lint-contracts` / contract-graph lint 在 `just check` 内 |
