# Drift 检测干预链修复（SDD #11）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复语言漂移检测干预链的 5 处失效（R1 baseline 接线 / R2 off-by-one / R3 severity 门控 / R4 吞异常 / R5 pending_hooks 双源格式链），使 ESCALATE 暂停安全网真实可达。

**Architecture:** R1-R4 是 `src/shenbi/skill_utils/drift_detection/` 与 `src/shenbi/pipeline/chapter_loop.py` 内的小面修改；R5 新增 `src/shenbi/records/writer.py`（canonical 双源写 + 并集迁移），`hook_planting._append_to_pending_hooks` 改走它。执行顺序 R1→R2→R3→R4→R5（R3/R4 验收依赖 R1/R2 先落地）。

**Tech Stack:** Python 3.11+，pathlib/yaml/json，structlog，pytest；验证一律 `uv run pytest`（与 CI `uv run --frozen` 同构）。

## Global Constraints

- 框架代码无 `print()`（structlog）；`pathlib.Path` 文件 I/O；gate/检查器纯函数幂等
- 测试 scenario 输入只引用 `tests/fixtures/` 真实产物（G0.9 禁手写 fixture；复制到 tmp_path 使用是合法形态）
- 状态字面量不新增裸字符串（既有 `"NONE"/"WARN"/"HARD"/"ESCALATE"`、`"PLANTED"/"PENDING"` 均为现行字面量，沿用）
- 每个 task 独立 conventional commit（`fix: R<N> …`）；commit 显式列文件路径，禁 `git add -A`
- 全部 task 属 **infra**（触及 pipeline/、records/、被多模块 import）→ 协调者亲自实现，不派 implementer 子 agent；每 task commit 后 fresh-context 重审产出 `.superpowers/sdd/audit-T<N>.md`
- 真实签名（源码核对 2026-08-24，commit cc477cc 基线）：
  - `establish_baseline(project_dir: Path | str, chapters: list[int]) -> dict[str, float]`（baseline.py:24）
  - `detect_drift(current: dict[str, float], baseline: dict[str, float]) -> DriftResult`（linguistic_drift.py:182）
  - `_check_linguistic_drift(project_dir: Path, chapter: int) -> DriftResult | None`（chapter_loop.py:2026）
  - `parse_records(text: str) -> list[dict[str, Any]]` / `serialize_records(records) -> str`（records/parser.py:48/53）
  - `parse_markdown_table(text: str) -> dict[str, dict[str, str]]` / `detect_cross_section_drift(yaml_records, md_rows) -> list[str]`（records/drift.py:26/72）
  - `_append_to_pending_hooks(project_dir: Path, entries: list[dict[str, Any]], chapter: int) -> int`（hook_planting.py:204）

---

### Task 1: R1 — establish_baseline 接线（F602）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:2044-2050`（`_check_linguistic_drift` baseline 加载段）
- Test: `tests/unit/pipeline/test_drift_baseline_wiring.py`（新建）

**Interfaces:**
- Consumes: `establish_baseline`（现有，不改）
- Produces: chapter ≥ 4 且 `style/linguistic_baseline.json` 缺失时惰性建立 baseline（chapters [1,2,3]）；chapter ≤ 3 保持现状（warning + return None）

- [ ] **Step 1: 写失败测试**

```python
"""R1 (F602): establish_baseline wiring — baseline exists from chapter 4 on."""

import shutil
from pathlib import Path

import pytest

FIXTURE_CHAPTERS = Path("tests/fixtures/multi-chapter-example")  # 真实章节产物 (G0.9)


def _make_project(tmp_path: Path) -> Path:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    for ch in (1, 2, 3, 4):
        shutil.copy(FIXTURE_CHAPTERS / f"chapter-{ch}.md", chapters / f"chapter-{ch}.md")
    return tmp_path


def test_baseline_lazily_established_from_ch4(tmp_path):
    from shenbi.pipeline.chapter_loop import _check_linguistic_drift

    project = _make_project(tmp_path)
    assert not (project / "style" / "linguistic_baseline.json").exists()

    result = _check_linguistic_drift(project, 4)

    baseline_file = project / "style" / "linguistic_baseline.json"
    assert baseline_file.exists()  # 验收：第 4 章起 baseline 文件存在
    assert result is not None  # 检查真实执行（非 no_linguistic_baseline 早退）


def test_baseline_not_established_before_ch4(tmp_path):
    from shenbi.pipeline.chapter_loop import _check_linguistic_drift

    project = _make_project(tmp_path)
    assert _check_linguistic_drift(project, 3) is None  # ch1-3 无 baseline 属预期
    assert not (project / "style" / "linguistic_baseline.json").exists()


def test_baseline_reused_not_rebuilt(tmp_path):
    from shenbi.pipeline.chapter_loop import _check_linguistic_drift

    chapters = tmp_path / "chapters"
    chapters.mkdir()
    for ch in (1, 2, 3, 4, 5):  # 含 ch5，否则 ch5 检查在文件存在性早退、断言空转
        shutil.copy(FIXTURE_CHAPTERS / f"chapter-{ch}.md", chapters / f"chapter-{ch}.md")
    _check_linguistic_drift(tmp_path, 4)
    baseline_file = tmp_path / "style" / "linguistic_baseline.json"
    first = baseline_file.read_text(encoding="utf-8")
    # 篡改章节后重跑：已存在的 baseline 不重建
    (tmp_path / "chapters" / "chapter-1.md").write_text("完全不同的文本", encoding="utf-8")
    _check_linguistic_drift(tmp_path, 5)
    assert baseline_file.read_text(encoding="utf-8") == first
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_drift_baseline_wiring.py -v`
Expected: `test_baseline_lazily_established_from_ch4` FAIL（baseline 不存在，`_check_linguistic_drift` 在 no_linguistic_baseline 早退）；`test_baseline_not_established_before_ch4` PASS；`test_baseline_reused_not_rebuilt` ERROR（首次 `_check(…,4)` 未建 baseline，随后 read_text 抛 FileNotFoundError——同样由 Step 3 转绿）

- [ ] **Step 3: 实现**（chapter_loop.py `_check_linguistic_drift` 内，替换现有 baseline 加载段）

```python
    # Load baseline (established from first 3 chapters — see Task 6 / spec §3.5).
    # R1 (F602): lazily establish the canonical baseline (style/) once chapter 4
    # is reached; chapters 1-3 ARE the baseline corpus, absence is expected.
    baseline_file = project_dir / "style" / "linguistic_baseline.json"
    if not baseline_file.exists():
        if chapter >= 4:
            from shenbi.skill_utils.drift_detection.baseline import establish_baseline

            establish_baseline(project_dir, [1, 2, 3])
        else:
            log.warning("no_linguistic_baseline", chapter=chapter)
            return None
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
```

（删除原 `if baseline_file.exists(): ... else: log.warning(...); return None` 块。）

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/pipeline/test_drift_baseline_wiring.py -v`
Expected: 3 PASS

- [ ] **Step 5: 跑邻近回归**

Run: `uv run pytest tests/unit/pipeline/test_drift_intervention.py tests/unit/skill_utils/drift_detection/ -v`
Expected: 全 PASS

- [ ] **Step 6: Commit + audit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_drift_baseline_wiring.py
git commit -m "fix: R1 (F602) wire establish_baseline into chapter_loop — ch4+ lazy baseline"
```
→ fresh-context 审查写 `.superpowers/sdd/audit-T1.md`

---

### Task 2: R2 — 对话塌陷 off-by-one（F601）

**Files:**
- Modify: `src/shenbi/skill_utils/drift_detection/linguistic_drift.py:191-218`（`detect_drift`）
- Test: `tests/unit/skill_utils/drift_detection/test_linguistic_drift.py`（追加）

**Interfaces:**
- Produces: 模块级常量 `_DEVIATION_DRIFT_THRESHOLD: Final[float] = 5.0`；对话塌陷时 `max_deviation_ratio` 置为该常量且 `is_drift` 判据改 `>=`（塌陷可触发）；比值类超阈（>500%）行为不变

- [ ] **Step 1: 写失败测试**

```python
def test_dialogue_collapse_triggers_drift():
    """R2 (F601): dialogue ratio < 0.2 must set is_drift=True (was unreachable)."""
    baseline = {"dialogue_density": 50.0, "system_term_density": 1.0}
    current = {"dialogue_density": 5.0, "system_term_density": 1.0}  # ratio 0.1 < 0.2
    result = detect_drift(current, baseline)
    assert result.is_drift is True
    assert result.deviations["dialogue_density"] == 0.1


def test_drift_threshold_semantics_unchanged_for_ratios():
    """比值恰在 5.0x（非塌陷路径）不触发——塌陷用 >=，比值路径语义保持。"""
    baseline = {"dialogue_density": 10.0, "system_term_density": 1.0}
    current = {"dialogue_density": 6.0, "system_term_density": 1.0}  # ratio 0.6 正常
    assert detect_drift(current, baseline).is_drift is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/skill_utils/drift_detection/test_linguistic_drift.py::test_dialogue_collapse_triggers_drift -v`
Expected: FAIL（is_drift False——`max(...,5.0)` 后 `>5.0` 恒假）

- [ ] **Step 3: 实现**（linguistic_drift.py；模块顶部 import 区后加常量，`detect_drift` 内两处改）

```python
from typing import Final, Literal
# ...
# R2 (F601): single source for the drift threshold. Dialogue collapse sets the
# deviation ratio to exactly this value, so the trigger test must be >=.
_DEVIATION_DRIFT_THRESHOLD: Final[float] = 5.0
```

`detect_drift` 内：
```python
        if dialogue_ratio < 0.2:
            max_deviation_ratio = max(max_deviation_ratio, _DEVIATION_DRIFT_THRESHOLD)
            trigger_metric = trigger_metric or "dialogue_density"

    is_drift = max_deviation_ratio >= _DEVIATION_DRIFT_THRESHOLD
```

- [ ] **Step 4: 跑测试确认通过 + 全模块回归**

Run: `uv run pytest tests/unit/skill_utils/drift_detection/ -v && uv run pytest tests/unit/pipeline/test_drift_intervention.py -v`
Expected: 全 PASS（含 Task 2 Step 1 两条与既有用例）

- [ ] **Step 5: Commit + audit**

```bash
git add src/shenbi/skill_utils/drift_detection/linguistic_drift.py tests/unit/skill_utils/drift_detection/test_linguistic_drift.py
git commit -m "fix: R2 (F601) dialogue-collapse drift reachable — shared threshold constant, >= semantics"
```
→ `.superpowers/sdd/audit-T2.md`

---

### Task 3: R3 — severity 阶梯解除 is_drift 门控（F612）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:2056`（`if result.is_drift:` → `if result.severity != "NONE":`）
- Modify: `src/shenbi/skill_utils/drift_detection/linguistic_drift.py:231-238`（message 按 severity 生成）
- Test: `tests/unit/pipeline/test_drift_intervention.py`（追加）

**Interfaces:**
- Consumes: Task 2 的 `detect_drift`（不变签名）
- Produces: 干预由 `severity != "NONE"` 驱动；`DriftResult.message` 在 severity ≠ NONE 时描述 severity 而非"未检出"

- [ ] **Step 1: 写失败测试**

```python
def test_escalate_without_is_drift_raises():
    """R3 (F612): stm >100‰ (ESCALATE) must intervene even when is_drift=False.
    baseline stm=30 使比值 110/30≈3.7 不越阈——正是 F612 的「baseline 污染」场景。"""
    baseline = {"dialogue_density": 50.0, "system_term_density": 30.0}
    current = {"dialogue_density": 30.0, "system_term_density": 110.0}  # 比值正常, stm 超标
    result = detect_drift(current, baseline)
    assert result.severity == "ESCALATE"
    assert result.is_drift is False  # 正是 F612 场景


def test_is_drift_implies_at_least_warn():
    """R3 安全前提（须固化）：is_drift=True ⇒ severity ≥ WARN——门控改 severity 不放大 NONE 面。"""
    import itertools
    from shenbi.skill_utils.drift_detection.linguistic_drift import detect_drift as dd

    for stm, dlg in itertools.product([0.0, 35.0, 60.0, 110.0], [50.0, 5.0, 0.0]):
        base = {"dialogue_density": 50.0, "system_term_density": 1.0}
        cur = {"dialogue_density": dlg, "system_term_density": stm}
        r = dd(cur, base)
        if r.is_drift:
            assert r.severity in ("WARN", "HARD", "ESCALATE"), (stm, dlg, r)


def test_escalate_message_reflects_severity():
    """R3 附带：severity=ESCALATE + is_drift=False 时 message 不得称'未检出'。"""
    baseline = {"dialogue_density": 50.0, "system_term_density": 30.0}
    current = {"dialogue_density": 30.0, "system_term_density": 110.0}
    r = detect_drift(current, baseline)
    assert "No linguistic drift" not in r.message
    assert "ESCALATE" in r.message
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_drift_intervention.py -v`
Expected: `test_escalate_message_reflects_severity` FAIL（message 现为 "No linguistic drift detected."）；`test_escalate_without_is_drift_raises` PASS（detect_drift 层 ESCALATE 已可达——该条固化 F612 场景）

- [ ] **Step 3: 实现**

chapter_loop.py:2056：
```python
    if result.severity != "NONE":
```
（其上 log.warning 的 `severity=result.severity` 不变；ESCALATE/HARD/WARN 分支不动。）

linguistic_drift.py message 段：
```python
    if is_drift:
        message = (
            f"Drift detected: {trigger_metric} deviated {max_deviation_ratio:.1f}x "
            f"from baseline. System term density: {stm_density:.1f} per mille."
        )
    elif severity != "NONE":
        message = (
            f"Severity {severity}: system term density {stm_density:.1f} per mille "
            f"(absolute threshold breach; ratio metrics within bounds)."
        )
    else:
        message = "No linguistic drift detected."
```

- [ ] **Step 4: 跑测试确认通过 + 回归**

Run: `uv run pytest tests/unit/pipeline/test_drift_intervention.py tests/unit/skill_utils/drift_detection/ tests/unit/pipeline/test_drift_baseline_wiring.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit + audit**

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/skill_utils/drift_detection/linguistic_drift.py tests/unit/pipeline/test_drift_intervention.py
git commit -m "fix: R3 (F612) drive drift intervention by severity, not is_drift; severity-aware message"
```
→ `.superpowers/sdd/audit-T3.md`

---

### Task 4: R4 — DriftEscalationError 不再被吞（F620）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（新增模块级 helper `_run_linguistic_drift_check`；调用点 2853-2861 改调它）
- Test: `tests/unit/pipeline/test_drift_escalation_propagation.py`（新建）

**Interfaces:**
- Consumes: Task 1/3 后的 `_check_linguistic_drift` + `DriftEscalationError`（chapter_loop.py:533，同模块）
- Produces: `_run_linguistic_drift_check(project_dir: Path, chapter: int) -> None`——ESCALATE 异常向外传播（到达暂停逻辑）；其余异常保持 non-blocking warning。调用点 2853-2861 改为一行 `_run_linguistic_drift_check(project_dir, chapter)`

- [ ] **Step 1: 写失败测试**

```python
"""R4 (F620): DriftEscalationError must escape the step call site; other
exceptions stay non-blocking. Tested via the extracted helper
``_run_linguistic_drift_check`` (the production call-site handler)."""

import shutil
from pathlib import Path

import pytest

FIXTURE_CHAPTERS = Path("tests/fixtures/multi-chapter-example")


def _make_project(tmp_path: Path, ch4_text: str) -> Path:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    for ch in (1, 2, 3):
        shutil.copy(FIXTURE_CHAPTERS / f"chapter-{ch}.md", chapters / f"chapter-{ch}.md")
    (chapters / "chapter-4.md").write_text(ch4_text, encoding="utf-8")
    return tmp_path


DEGRADED = "冷在场于第七层深度。冷值7.3，在场度0.89。系统阈值参数格式串。" * 30


def test_escalation_propagates_out_of_check(tmp_path):
    from shenbi.pipeline.chapter_loop import DriftEscalationError, _check_linguistic_drift

    project = _make_project(tmp_path, DEGRADED)
    # 直接断言底层可达（stm>100‰ → ESCALATE → raise）
    with pytest.raises(DriftEscalationError):
        _check_linguistic_drift(project, 4)


def test_call_site_helper_rethrows_escalation(tmp_path, monkeypatch):
    """R4 核心：调用点 helper 不得把 DriftEscalationError 降级为 warning。"""
    from shenbi.pipeline import chapter_loop
    from shenbi.pipeline.chapter_loop import DriftEscalationError

    def fake_check(project_dir, chapter):
        raise DriftEscalationError("escalated")

    monkeypatch.setattr(chapter_loop, "_check_linguistic_drift", fake_check)
    with pytest.raises(DriftEscalationError):
        chapter_loop._run_linguistic_drift_check(tmp_path, 4)


def test_call_site_helper_swallows_other_exceptions(tmp_path, monkeypatch):
    from shenbi.pipeline import chapter_loop

    def fake_check(project_dir, chapter):
        raise RuntimeError("transient")

    monkeypatch.setattr(chapter_loop, "_check_linguistic_drift", fake_check)
    # 不外抛即通过（helper 内部 log.warning 降级）
    chapter_loop._run_linguistic_drift_check(tmp_path, 4)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_drift_escalation_propagation.py -v`
Expected: `test_call_site_helper_rethrows_escalation` / `test_call_site_helper_swallows_other_exceptions` FAIL（`_run_linguistic_drift_check` 不存在）

- [ ] **Step 3: 实现**（chapter_loop.py：新增模块级 helper，放在 `DriftEscalationError` 定义之后；调用点 2853-2861 的 try/except 块整体替换为一行调用）

```python
def _run_linguistic_drift_check(project_dir: Path, chapter: int) -> None:
    """Run the linguistic drift check for a pipeline-internal step.

    R4 (F620): ESCALATE must pause the pipeline — DriftEscalationError
    propagates to the checkpoint logic. Any other failure stays
    non-blocking (warning only).
    """
    try:
        _check_linguistic_drift(project_dir, chapter)
    except DriftEscalationError:
        raise
    except Exception:
        log.warning(
            "linguistic_drift_check_failed",
            chapter=chapter,
            exc_info=True,
        )
```

调用点（2853-2861）替换为：

```python
        if step.skill == "pipeline-linguistic-drift-check":
            _run_linguistic_drift_check(project_dir, chapter)
```

- [ ] **Step 4: 跑测试确认通过 + 回归**

Run: `uv run pytest tests/unit/pipeline/test_drift_escalation_propagation.py tests/unit/pipeline/test_drift_intervention.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit + audit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_drift_escalation_propagation.py
git commit -m "fix: R4 (F620) re-raise DriftEscalationError at call site — ESCALATE reaches pause logic"
```
→ `.superpowers/sdd/audit-T4.md`

---

### Task 5: R5 — pending_hooks 双源 canonical 格式链（F637）

**Files:**
- Create: `src/shenbi/records/writer.py`
- Modify: `src/shenbi/pipeline/hook_planting.py:204-276`（`_append_to_pending_hooks` 走 writer）
- Test: `tests/unit/records/test_writer.py`（新建；`tests/unit/records/__init__.py` 如缺则建）
- Test: `tests/unit/pipeline/test_hook_planting_canonical.py`（新建）

**Interfaces:**
- Consumes: `parse_records`/`serialize_records`（records/parser.py）、`parse_markdown_table`/`detect_cross_section_drift`/`_MD_HEADER_TO_KEY`（records/drift.py）、`safe_write`
- Produces（writer.py 公共 API，hook_planting 与测试依赖）:
  - `TABLE_COLUMNS: list[str]` — 8 列键序 `["id","type","dimension","subtlety","escalation_curve","plant_chapter","operation","state"]`（值 = `list(_MD_HEADER_TO_KEY.values())`，与 drift.py 表头映射同源）
  - `normalize_record(rec: dict[str, Any]) -> dict[str, Any]` — 8 列集补齐（缺列 `""`；无 `state` 的 ID-only 记录补 `"PENDING"`；保留富字段）
  - `collect_records(text: str) -> list[dict[str, Any]]` — 并集迁移源：frontmatter `hooks` ∪ body `## hooks` 块（`parse_records`）∪ body 自由文本 ID 扫描（`_HOOK_ID_RE = re.compile(r"(?:[HM]\d+|P\d*-\d+)")`，与 truth_index.py:32 同式）∪ `## 活跃伏笔` 表（`parse_markdown_table`，值转 str 后并入 field-level 合并）；冲突 field-level 合并、按键有值者优先，来源优先序 body-YAML > frontmatter > 表 > ID-only；列表序 = 首次出现序（frontmatter 先、body 后）；全部过 `normalize_record`
  - `render_pending_hooks(records: list[dict[str, Any]]) -> str` — 三段 canonical：YAML frontmatter（`{"hooks": <原序原样 dict 列表>}`，`yaml.safe_dump(..., sort_keys=True, allow_unicode=True)`）+ `\n## hooks\n\n` + `serialize_records(records)` + `\n\n## 活跃伏笔\n\n` + 8 列 markdown 表（表头中文列名 = `_MD_HEADER_TO_KEY` 逆映射；单元格 = 记录列值的 str 形式，`plant_chapter`/`subtlety` 保持 YAML 解析原值的 `str()`；表由同一记录集生成故与 YAML 同源）
  - `preserve_keys(text: str) -> dict[str, Any]` — 返回 frontmatter 中非 `hooks` 键（project/last_updated/version 等），重写时经 `render_pending_hooks(records, preserve_frontmatter=...)` 保留
  - `write_pending_hooks(project_dir: Path, records, preserve_frontmatter: dict | None = None) -> None` — `safe_write(project_dir / "truth" / "pending_hooks.md", render_pending_hooks(records, preserve_frontmatter=preserve_frontmatter))`

- [ ] **Step 1: 写失败测试**（`tests/unit/records/test_writer.py`）

```python
"""R5 (F637): pending_hooks dual-source canonical writer + union migration."""

from pathlib import Path

from shenbi.records.drift import detect_cross_section_drift, parse_markdown_table
from shenbi.records.parser import parse_records
from shenbi.records.writer import collect_records, render_pending_hooks

FIXTURE = Path("tests/fixtures/truth-pending_hooks.md")  # 真实产物 (G0.9)


def test_collect_records_union_all_sources():
    """fixture（frontmatter 无、body YAML+表全）→ 三源并入不丢记录。"""
    records = collect_records(FIXTURE.read_text(encoding="utf-8"))
    ids = {r["id"] for r in records}
    assert {"hook-ch1-001", "hook-ch1-002", "hook-ch1-003"} <= ids


def test_collect_records_body_only_freetext():
    """body-only 自由文本生产态：ID 扫描兜底得 PENDING 记录，非空集。
    （合成 stimulus：collect_records 纯函数输入，非 fixture 产物）"""
    text = "# 伏笔池\n\n主角提到 H7 与 P0-3 已种下。\n"
    records = collect_records(text)
    ids = {r["id"] for r in records}
    assert {"H7", "P0-3"} <= ids
    for r in records:
        if r["id"] in ("H7", "P0-3"):
            assert r["state"] == "PENDING"
            assert r["type"] == ""


def test_collect_records_field_level_merge_body_wins():
    """同 id 双源：body 值优先，frontmatter 富字段保留。"""
    text = (
        "---\nhooks:\n- id: H1\n  state: PLANTED\n  content: 富字段\n---\n\n"
        "## hooks\n\n- id: H1\n  state: RESOLVED\n"
    )
    records = collect_records(text)
    assert len(records) == 1
    assert records[0]["state"] == "RESOLVED"
    assert records[0]["content"] == "富字段"


def test_render_roundtrip_idempotent_and_drift_free():
    """验收：writer 往返幂等 + append 后 detect_cross_section_drift == []。"""
    text = FIXTURE.read_text(encoding="utf-8")
    once = collect_records(text)
    rendered = render_pending_hooks(once)
    twice = collect_records(rendered)
    assert [r["id"] for r in once] == [r["id"] for r in twice]  # 首现序稳定
    assert detect_cross_section_drift(
        parse_records(rendered), parse_markdown_table(rendered)
    ) == []


def test_render_resembles_real_fixture_shape():
    rendered = render_pending_hooks(collect_records(FIXTURE.read_text(encoding="utf-8")))
    assert rendered.startswith("---\n")
    assert "## hooks" in rendered
    assert "## 活跃伏笔" in rendered
    assert "| Hook ID |" in rendered
```

（`tests/unit/pipeline/test_hook_planting_canonical.py`：）

```python
"""R5: _append_to_pending_hooks preserves body sections + dual-source write."""

import shutil
from pathlib import Path

from shenbi.records.drift import detect_cross_section_drift, parse_markdown_table
from shenbi.records.parser import parse_records

from shenbi.pipeline.hook_planting import _append_to_pending_hooks

FIXTURE = Path("tests/fixtures/truth-pending_hooks.md")


def test_append_preserves_existing_body_and_table(tmp_path):
    """破坏性整写禁止：append 后既有 body/表仍在且新增记录三段同步。"""
    truth = tmp_path / "truth"
    truth.mkdir()
    target = truth / "pending_hooks.md"
    shutil.copy(FIXTURE, target)

    entries = [{"hook_id": "H99", "description": "新伏笔", "type": None, "category": None}]
    planted = _append_to_pending_hooks(tmp_path, entries, chapter=5)

    assert planted == 1
    text = target.read_text(encoding="utf-8")
    assert "## hooks" in text and "## 活跃伏笔" in text  # body 段保留
    records = parse_records(text)
    ids = {r["id"] for r in records}
    assert {"hook-ch1-001", "H99"} <= ids  # 旧记录未丢 + 新记录入 body
    fm_ids = _frontmatter_ids(text)
    assert "H99" in fm_ids  # frontmatter 同步（三个 frontmatter 读取方继续可用）
    assert detect_cross_section_drift(records, parse_markdown_table(text)) == []


def _frontmatter_ids(text: str) -> set[str]:
    import yaml
    parts = text.split("---", 2)
    fm = yaml.safe_load(parts[1]) or {}
    return {h["id"] for h in fm.get("hooks", []) if isinstance(h, dict) and "id" in h}


def _frontmatter_only_variant() -> str:
    """历史生产 writer 形态：真实 body 记录整体移入 frontmatter，body 全丢
    （派生自真实 skill 输出，G0.9 合法变体）。"""
    import yaml

    from shenbi.records.parser import parse_records as pr

    real = FIXTURE.read_text(encoding="utf-8")
    records = pr(real)
    return (
        "---\n"
        + yaml.safe_dump({"hooks": records}, allow_unicode=True, sort_keys=False)
        + "---\n"
    )


def _body_freetext_only_variant() -> str:
    """body-only 自由文本生产态（truth_index Source-2 记载）。ID 用
    _HOOK_ID_RE 实际匹配的形态（H<N>），映射自真实 fixture 的表行序。"""
    real = FIXTURE.read_text(encoding="utf-8")
    n_rows = sum(1 for ln in real.splitlines() if ln.startswith("| hook-ch"))
    prose_ids = [f"H{i}" for i in range(1, n_rows + 1)]
    return (
        "# 伏笔池\n\n"
        + "\n".join(f"主角注意到 {hid} 的伏笔已种下。" for hid in prose_ids)
        + "\n"
    )


def test_append_migrates_frontmatter_only_legacy(tmp_path):
    """frontmatter-only 存量 append 后自动迁移为三段，frontmatter 记录不丢。"""
    truth = tmp_path / "truth"
    truth.mkdir()
    target = truth / "pending_hooks.md"
    target.write_text(_frontmatter_only_variant(), encoding="utf-8")
    entries = [{"hook_id": "H99", "description": "x", "type": None, "category": None}]
    _append_to_pending_hooks(tmp_path, entries, chapter=1)
    text = target.read_text(encoding="utf-8")
    assert "## hooks" in text and "## 活跃伏笔" in text
    ids = {r["id"] for r in parse_records(text)}
    assert {"hook-ch1-001", "hook-ch1-002", "hook-ch1-003", "H99"} <= ids
    assert detect_cross_section_drift(parse_records(text), parse_markdown_table(text)) == []


def test_append_dedup_reads_union_source(tmp_path):
    """去重走并集源：body-only 自由文本记录的 id 也算已存在，不重复植入。"""
    truth = tmp_path / "truth"
    truth.mkdir()
    target = truth / "pending_hooks.md"
    target.write_text(_body_freetext_only_variant(), encoding="utf-8")
    entries = [{"hook_id": "H1", "description": "x", "type": None, "category": None}]
    assert _append_to_pending_hooks(tmp_path, entries, chapter=2) == 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/records/test_writer.py tests/unit/pipeline/test_hook_planting_canonical.py -v`
Expected: writer 用例 FAIL（ModuleNotFoundError: shenbi.records.writer）；hook_planting 用例 FAIL（body 段被整写摧毁）

- [ ] **Step 3: 实现 `src/shenbi/records/writer.py`**

```python
"""pending_hooks.md canonical dual-source writer (SDD #11 R5 / F637).

Canonical three-part format, same shape as the real fixture
``tests/fixtures/truth-pending_hooks.md``:
  1. YAML frontmatter ``hooks`` list — read by pipeline/context_curation.py,
     pipeline/review_checklist.py, chapter_loop._count_triggered_hooks;
  2. ``## hooks`` YAML body block — read by records/parser.parse_records
     (authority per spec New-F), audit/write_audit.py;
  3. ``## 活跃伏笔`` markdown table — read by records/drift.parse_markdown_table.

Table and YAML block are generated from ONE record set, so
detect_cross_section_drift is empty by construction. Migration
(collect_records) is a union over all legacy shapes — frontmatter-only,
body-YAML-block, and body free-text (the production state per
truth_index.py) — with field-level merge and first-appearance ordering;
serialization is deterministic, so migration is idempotent.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from shenbi.records.drift import _MD_HEADER_TO_KEY, parse_markdown_table
from shenbi.records.parser import parse_records, serialize_records
from shenbi.safe_write import safe_write

# Same pattern as pipeline/truth_index.py _HOOK_ID_RE (body free-text IDs).
_HOOK_ID_RE = re.compile(r"(?:[HM]\d+|P\d*-\d+)")

# 8 canonical table columns, sourced from the drift checker's header map.
TABLE_COLUMNS: list[str] = list(_MD_HEADER_TO_KEY.values())
_KEY_TO_HEADER: dict[str, str] = {v: k for k, v in _MD_HEADER_TO_KEY.items()}

_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = _FM_RE.match(text)
    if m is None:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    return fm if isinstance(fm, dict) else {}, text[m.end():]


def normalize_record(rec: dict[str, Any]) -> dict[str, Any]:
    """Pad every record to the 8-column set; ID-only records get PENDING.

    _values_equal(None, "") is False, so a missing column would fabricate
    drift against the generated table's empty cell.
    """
    out = dict(rec)
    has_state = bool(str(out.get("state") or "").strip())
    for col in TABLE_COLUMNS:
        if col == "state":
            if not has_state:
                out["state"] = "PENDING"
        elif out.get(col) is None:
            out[col] = ""
    return out


def collect_records(text: str) -> list[dict[str, Any]]:
    """Union-migrate all record sources in ``text`` into normalized records.

    Value precedence per key (field-level merge, first non-empty wins):
    body-YAML > frontmatter > markdown table > ID-only. Appearance order
    (output list order): frontmatter order first, then first appearance in
    body sources — stable across round-trips.
    """
    fm, body = _split_frontmatter(text)

    fm_records = [
        h for h in (fm.get("hooks") or []) if isinstance(h, dict) and h.get("id")
    ] if isinstance(fm.get("hooks"), list) else []
    body_block = parse_records(text)
    table_rows = parse_markdown_table(text)
    free_ids = _HOOK_ID_RE.findall(body)

    # Appearance order: frontmatter first, then body block, then remaining
    # table-only / free-text IDs in scan order.
    order: list[str] = []
    for rec in fm_records + body_block:
        rid = str(rec.get("id"))
        if rid not in order:
            order.append(rid)
    for rid in list(table_rows) + list(free_ids):
        if rid not in order:
            order.append(rid)

    # Value precedence: apply lowest-priority sources first, then overwrite.
    layered: list[list[dict[str, Any]]] = [
        [{"id": hid} for hid in free_ids],
        [{"id": rid, **row} for rid, row in table_rows.items()],
        fm_records,
        body_block,  # authoritative — applied last
    ]
    merged: dict[str, dict[str, Any]] = {}
    for source in layered:
        for rec in source:
            rid = str(rec.get("id") or "")
            if not rid:
                continue
            target = merged.setdefault(rid, {})
            for k, v in rec.items():
                if v is None or (isinstance(v, str) and not v.strip()):
                    continue  # empty values never overwrite richer ones
                target[k] = v

    return [normalize_record(merged[rid]) for rid in order]


def _render_table(records: list[dict[str, Any]]) -> str:
    header = "| " + " | ".join(_KEY_TO_HEADER[c] for c in TABLE_COLUMNS) + " |"
    sep = "|" + "|".join("---" for _ in TABLE_COLUMNS) + "|"
    lines = [header, sep]
    for rec in records:
        cells = [str(rec.get(c, "")) for c in TABLE_COLUMNS]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_pending_hooks(
    records: list[dict[str, Any]], *, preserve_frontmatter: dict[str, Any] | None = None
) -> str:
    """Render the canonical three-part document from one record set.

    ``preserve_frontmatter`` carries non-hooks frontmatter keys (project /
    last_updated / ...) from the file being rewritten so they survive.
    """
    fm: dict[str, Any] = dict(preserve_frontmatter or {})
    fm["hooks"] = records
    frontmatter = yaml.safe_dump(
        fm, sort_keys=True, allow_unicode=True, default_flow_style=False
    )
    return (
        "---\n"
        + frontmatter
        + "---\n\n"
        + "## hooks\n\n"
        + serialize_records(records)
        + "\n\n## 活跃伏笔\n\n"
        + _render_table(records)
        + "\n"
    )


def preserve_keys(text: str) -> dict[str, Any]:
    """Non-hooks frontmatter keys of ``text`` (to survive a canonical rewrite)."""
    fm, _ = _split_frontmatter(text)
    return {k: v for k, v in fm.items() if k != "hooks"}


def write_pending_hooks(
    project_dir: Path,
    records: list[dict[str, Any]],
    preserve_frontmatter: dict[str, Any] | None = None,
) -> None:
    safe_write(
        project_dir / "truth" / "pending_hooks.md",
        render_pending_hooks(records, preserve_frontmatter=preserve_frontmatter),
    )
```

- [ ] **Step 4: 改 `_append_to_pending_hooks`**（hook_planting.py）

替换 222-269 段的读取与写回：

```python
    hooks_file = project_dir / "truth" / "pending_hooks.md"

    # R5 (F637): union-source read (frontmatter ∪ body block ∪ table ∪ body IDs)
    # — dedup must see records written by any legacy shape.
    existing_hooks: list[dict[str, Any]] = []
    existing_ids: set[str] = set()

    if hooks_file.exists():
        from shenbi.records.writer import collect_records, preserve_keys

        _old_text = hooks_file.read_text(encoding="utf-8")
        _preserve = preserve_keys(_old_text)
        existing_hooks = collect_records(_old_text)
        existing_ids = {h["id"] for h in existing_hooks if "id" in h}

    # Collect new hooks (skip duplicates).
    new_hooks: list[dict[str, Any]] = []
    for entry in entries:
        hook_id = entry["hook_id"]
        if hook_id in existing_ids:
            log.info("hook_plant_duplicate_skipped", hook_id=hook_id, chapter=chapter)
            continue
        new_hooks.append(_generate_hook_yaml(entry, chapter))
        existing_ids.add(hook_id)

    if not new_hooks:
        # Still migrate a legacy-shaped file to canonical form (idempotent).
        if hooks_file.exists() and existing_hooks:
            from shenbi.records.writer import render_pending_hooks

            safe_write(
                hooks_file,
                render_pending_hooks(existing_hooks, preserve_frontmatter=_preserve),
            )
        return 0

    all_hooks = existing_hooks + new_hooks
    safe_write(hooks_file, render_pending_hooks(all_hooks, preserve_frontmatter=_preserve))
    log.info(
        "hook_plant_appended_to_pending_hooks",
        chapter=chapter,
        new_count=len(new_hooks),
        total_count=len(all_hooks),
    )
    return len(new_hooks)
```

（顶部补 `from shenbi.records.writer import collect_records, render_pending_hooks` 可改为模块级 import——按文件既有 import 风格放模块顶部更佳。）

- [ ] **Step 5: 跑测试确认通过 + 全量回归**

Run: `uv run pytest tests/unit/records/ tests/unit/pipeline/test_hook_planting_canonical.py -v && uv run pytest tests/unit -q -k "hook or pending or truth_index or context_curation or review_checklist"`
Expected: 全 PASS（含 truth_index 双源读取对新格式的兼容）

- [ ] **Step 6: Commit + audit**

```bash
git add src/shenbi/records/writer.py src/shenbi/pipeline/hook_planting.py tests/unit/records/ tests/unit/pipeline/test_hook_planting_canonical.py
git commit -m "fix: R5 (F637) pending_hooks canonical dual-source writer — union migration, body-preserving append"
```
→ `.superpowers/sdd/audit-T5.md`

---

## 验收覆盖表

| spec 验收 | task | 可执行验证 |
|---|---|---|
| R1 第 4 章起 baseline 文件存在 | T1 | `uv run pytest tests/unit/pipeline/test_drift_baseline_wiring.py -v` |
| R2 dialogue ratio<0.2 → is_drift=True | T2 | `uv run pytest tests/unit/skill_utils/drift_detection/test_linguistic_drift.py::test_dialogue_collapse_triggers_drift -v` |
| R3 stm 110‰ 触发 ESCALATE | T3 | `uv run pytest tests/unit/pipeline/test_drift_intervention.py::test_escalate_without_is_drift_raises -v` |
| R4 ESCALATE 到达暂停逻辑 | T4 | `uv run pytest tests/unit/pipeline/test_drift_escalation_propagation.py -v` |
| R5 真实文件检出 drift / 往返幂等 | T5 | `uv run pytest tests/unit/records/test_writer.py tests/unit/pipeline/test_hook_planting_canonical.py -v` |

不涉及评分场景，无需 G3.4 子 agent。全部 task = infra（pipeline/records），协调者亲实现。
