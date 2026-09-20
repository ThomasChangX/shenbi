# Spec #68 POC E2E 纵向验收 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 POC E2E 纵向验收判读层——`tools/report_longitudinal.py` 纯解析 verdict 工具（exit 0/1/2 三态）+ 失败分类学映射 + 扩展性观测 + `just e2e-report`/`just e2e-canary` 接线。

**Architecture:** 单文件 tools/ 脚本（零 `src/shenbi/` 修改，import 复用纯函数：`detect_chapter_drift`/`extract_finding_units`/`word_count_md`/`committed_chapter_anchor`/`TokenLedger`），判定顺序钉死（data-error → completeness → quality），三输入面 fail-closed，coverage 披露防静默数据缺口。测试三文件在 `tests/unit/`（tools 测试先例：`test_count_active_specs.py`/`test_lint_audit_run.py`），输入经真实生产写方在 tmp_path 构造（G0.9）。

**Tech Stack:** Python 3.11+ stdlib（json/re/argparse/pathlib/dataclasses/statistics 经由被 import 模块），pytest，justfile shebang recipe。

## Global Constraints（逐条自 spec 抄录，所有 task 隐含遵守）

- **零 LLM、零派发、零 `src/shenbi/` 运行时改动**（import 纯函数不改源头）——spec 边界
- **exit 三态**：0=pass / 1=fail / 2=data error；判定顺序：data-error 先于完整性 fail 先于质量条件——spec §1
- **三输入面 fail-closed 对称**：resonance 缺行/非数值、chapter_states 缺键、chapter-N.md 主文件缺失 → 该章 fail——spec §1 边界语义
- **分段枚举**：r=N mod 3；r=0→(f,f,f)；r=1→(f,f,c)；r=2→(f,c,c)（f=floor(N/3), c=ceil(N/3)）——spec §1
- **N 来源**：N_target=`novel.json` `total_chapters`（缺/0→exit 2）；N_done=`committed_chapter_anchor` 口径；N_done<N_target→fail，>→披露——spec §1
- **exit 2 输入面**：novel.json 缺失/坏 JSON/缺 `total_chapters` 或 `target_word_count` 键或值为 0；pipeline-state.json 缺失/坏 JSON；resonance_trend.md 缺失/无表头/零数据行/重复 `{N}` 键——spec §1
- **观测面输入**（ledger 缺失/空、快照缺失）→ verdict 不受影响 + coverage 披露 0%——spec §1
- **审计发现输入统一 raw glob 优先**：`chapter-N-*.md` + `extract_finding_units` + ~10 行合并 glue；aggregate 仅 raw glob 为空时回退（按其 H2 分节格式解析）+ coverage 标注——spec §2
- **resonance 解析**：工具自带 `{N}` 键行解析器，列绑定按表头名；不复用 `parse_trend`/`parse_resonance_scores`——spec §2
- **保量口径**：`word_count_md`（G4 地板自身口径）；**趋势计数主源**：`checkpoint_history` ESCALATION 事件（`chapter=None` 排除披露；pending 非 NONE 披露不计数）——spec §1
- **verdict JSON schema**：`shenbi-longitudinal-verdict-v1`（本 plan 定稿字段集）——spec §1/§2
- **T201 豁免**：`pyproject.toml:130` `"tools/**" = ["T201"]`——工具可用 print；但 basedpyright 经测试 import 拉入 strict 面——类型注解必须完整
- **e2e-canary 不进 `just check`**（不触发付费派发）；e2e-report 用 shebang 形式保三态传播——spec §5
- **conventional commits** + pathspec 显式列文件（禁 `git add -A`）

## 阶段 4 必填字段（v6 SDD 协议）

**实际签名（从源码复制）**：

```python
# src/shenbi/skill_utils/drift_detection/compute_drift.py:69
def detect_chapter_drift(
    raw: list[float],
    dim: str,
    min_samples_sigma: int = 6,
    exclude_indices: set[int] | None = None,
) -> list[DriftFinding]
# DriftFinding(kind: DriftKind, dim: str, detail: str)  # 冻结 dataclass :48-53

# src/shenbi/pipeline/audit_aggregate.py:72
def extract_finding_units(report_name: str, content: str) -> tuple[list[FindingUnit], list[str]]
# FindingUnit(severity: str, text: str, reporters: tuple[str, ...])  # :51-56

# src/shenbi/gates/shared.py:107
def word_count_md(fp: str | Path) -> int

# src/shenbi/pipeline/chapter_loop.py:329
def committed_chapter_anchor(project_dir: Path) -> int

# src/shenbi/cost/ledger.py:54
class TokenLedger:
    def __init__(self, project_dir: Path | str) -> None  # 读 cost/token-ledger.jsonl
    def iter_records(self) -> Iterator[TokenUsageRecord]  # 跳空行/坏 JSON/坏记录（WARN 不抛）
# TokenUsageRecord(timestamp: str, skill: str, chapter: int, model: str,
#   prompt_tokens: int, completion_tokens: int, total_tokens: int,
#   estimated_cost_usd: float, estimated: bool = False, attempt: int = 1,
#   pricing_status: str = "ok")  # :37-50

# src/shenbi/pipeline/chapter_loop.py:1621
def build_resonance_trend_row(chapter: int, overall: int) -> str

# src/shenbi/pipeline/truth_io.py:158
def write_truth_file(
    project_dir: Path,
    filename: str,
    new_data: str | dict[str, Any] | list[dict[str, Any]],
    *,
    mode: str = "replace",
    key_field: str | None = None,
) -> None  # mode="insert_markdown_row" + key_field="chapter" = {N} 键整格去重插入

# src/shenbi/pipeline/machine.py:61
def save_state(project_dir: Path | str, state: PipelineState) -> None
# src/shenbi/pipeline/state.py:205 PipelineState(project_dir=str)；
#   chapter_loop.chapter_states[str(N)] = ChapterState()；
#   ChapterState.status: ChapterStatus（"complete"）、.audit_retry_count/.revision_count: int
```

**复杂度分类**：全部 task = **leaf**（只新建 `tools/report_longitudinal.py` 与 `tests/unit/` 三个测试文件 + justfile 增量 recipe；零 `src/shenbi/` 修改——import 复用不触发 infra 路由的「涉及 infra 模块」条件）。执行路径：**协调者亲自实现**（单模型现实 + 钉死语义上下文密集；按 v6「leaf 可分派或亲自实现，按上下文长度裁决」）；每 task 后 fresh-context 全量重审产 audit-T<N>.md（两路径都必须，无例外）。

**test_kind**：T1-T5 = `tdd_red_green`（全新逻辑）；T6 = `regression_guard`（接线 + 全量回归）。

**测试层级与 fixture**：全部 T1（unit，tools 面——本仓 tools 测试先例即 unit 层）。fixture 引用：`tests/fixtures/audits/chapter-1-character.md`、`tests/fixtures/audits/chapter-1-consistency.md`（真实审计产物，分类学种子）、`tests/fixtures/snapshots/chapter-025/`（真实 truth 面，增长曲线基准）、`tests/fixtures/canary-3-chapter-seed.md`（recipe 文本引用）。G0.9：测试输入经真实生产写方（`write_truth_file`/`build_resonance_trend_row`/`save_state`/`TokenLedger.record`/`safe_write`）在 tmp_path 构造；契约表头（SKILL.md:174 格式面）由测试代码写入——先例 `tests/unit/skill_utils/test_drift_detection.py:88-135`。

**G3.4 独立评分声明**：N/A——本 spec 无评分场景（零 LLM 产物，无 0-100 分判定面）。

**F947 合规声明**：合规——spec 全部验收为 fixtures 驱动离线形式，无真实 dispatch 依赖（核心原则 8）。

## 验收覆盖表（spec 验收 → task → 命令）

| spec 验收 | task | 验证命令 |
|---|---|---|
| `count_active_specs.py` 通过（1=1） | T6 | `uv run python tools/count_active_specs.py` → PASS |
| `grep -n "spec #68" goal-prompt.md` 命中 | T6（登记时已落，终验） | `grep -n "spec #68" goal-prompt.md` → 行 4 |
| 工具在构造项目目录跑出双报告 + verdict JSON 符合 §1（含边界语义） | T5 | `uv run pytest tests/unit/test_report_longitudinal_report.py -q` 全绿（tmp 项目构造 + 双报告断言 + exit 三态） |
| 新增测试（三段边界/分类映射/ledger 对齐/exit 三态/coverage）全绿 | T1-T5 各自 + T6 汇总 | `uv run pytest tests/unit/test_report_longitudinal*.py -q` |
| `just check` 全绿 | T6 | `just check` → EXIT=0 |

---

### Task 1: 解析层——novel 目标、resonance_trend 行解析、分段

**Files:**
- Create: `tools/report_longitudinal.py`
- Test: `tests/unit/test_report_longitudinal.py`

**Interfaces:**
- Consumes: `write_truth_file`/`build_resonance_trend_row`（测试构造用）；契约表头（SKILL.md:174 格式面，测试写入）
- Produces（后续 task 依赖的精确名）:
  - `class LongitudinalDataError(Exception)`（属性 `reason: str`）
  - `def parse_novel_targets(novel_json: dict[str, object]) -> tuple[int, int]`——返回 `(target_word_count, total_chapters)`；缺键/0/非 dict → raise LongitudinalDataError
  - `@dataclass(frozen=True) class ResonanceRow`——`overall: float`、`excluded: bool`
  - `def parse_resonance_trend(path: Path) -> dict[int, ResonanceRow]`——`{N}` 键行解析器，列绑定按表头名（`chapter` 与 `overall` 与 `human_overridden`）；文件缺失/无表头/零数据行/重复 `{N}` 键 → raise LongitudinalDataError；`overall` 非数值（`pending`/`-`）行不进 dict（缺失章由判层 fail-closed）
  - `def segment_chapters(n_done: int) -> dict[str, list[int]]`——`{"front": [...], "mid": [...], "back": [...]}`，r=0→(f,f,f)/r=1→(f,f,c)/r=2→(f,c,c)；`n_done < 3` → raise LongitudinalDataError("insufficient chapters")

- [ ] **Step 1: 写失败测试**（`tests/unit/test_report_longitudinal.py` 新建）

```python
"""Spec #68 T1: report_longitudinal 解析层（novel 目标 / resonance 行 / 分段）。

G0.9: resonance_trend.md 经真实生产写方构造（build_resonance_trend_row +
write_truth_file insert_markdown_row）；契约表头是 SKILL.md:174 定义的
文件格式面，由测试代码写入（先例 tests/unit/skill_utils/test_drift_detection.py）。
"""
from __future__ import annotations

import pytest
from pathlib import Path

TREND_HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 "
    "| overall | confidence | human_overridden |"
)


def _write_trend(tmp_path: Path, rows: list[tuple[int, int]], header: str = TREND_HEADER) -> Path:
    from shenbi.pipeline.chapter_loop import build_resonance_trend_row
    from shenbi.pipeline.truth_io import write_truth_file

    truth = tmp_path / "truth"
    truth.mkdir(parents=True, exist_ok=True)
    trend = truth / "resonance_trend.md"
    trend.write_text(header + "\n", encoding="utf-8")
    for ch, overall in rows:
        write_truth_file(
            tmp_path, "resonance_trend.md",
            build_resonance_trend_row(ch, overall),
            mode="insert_markdown_row", key_field="chapter",
        )
    return trend


class TestParseNovelTargets:
    def test_ok(self):
        from tools.report_longitudinal import parse_novel_targets
        assert parse_novel_targets({"target_word_count": 200000, "total_chapters": 60}) == (200000, 60)

    @pytest.mark.parametrize("bad", [
        {}, {"target_word_count": 200000}, {"total_chapters": 60},
        {"target_word_count": 0, "total_chapters": 60},
        {"target_word_count": 200000, "total_chapters": 0},
    ])
    def test_missing_or_zero_raises(self, bad):
        from tools.report_longitudinal import LongitudinalDataError, parse_novel_targets
        with pytest.raises(LongitudinalDataError):
            parse_novel_targets(bad)


class TestParseResonanceTrend:
    def test_rows_keyed_by_chapter(self, tmp_path):
        from tools.report_longitudinal import parse_resonance_trend
        trend = _write_trend(tmp_path, [(1, 92), (2, 88), (3, 95)])
        rows = parse_resonance_trend(trend)
        assert sorted(rows) == [1, 2, 3]
        assert rows[1].overall == 92.0 and rows[1].excluded is False

    def test_missing_file_raises(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, parse_resonance_trend
        with pytest.raises(LongitudinalDataError):
            parse_resonance_trend(tmp_path / "truth" / "resonance_trend.md")

    def test_no_header_raises(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, parse_resonance_trend
        trend = _write_trend(tmp_path, [(1, 92)], header="not a table")
        with pytest.raises(LongitudinalDataError):
            parse_resonance_trend(trend)

    def test_zero_rows_raises(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, parse_resonance_trend
        trend = _write_trend(tmp_path, [])
        with pytest.raises(LongitudinalDataError):
            parse_resonance_trend(trend)

    def test_duplicate_key_raises(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, parse_resonance_trend
        trend = _write_trend(tmp_path, [(1, 92)])
        with trend.open("a", encoding="utf-8") as fh:
            fh.write("| 1 | 高潮 | 22 | 20 | 22 | 18 | 84 | high |  |\n")
        with pytest.raises(LongitudinalDataError):
            parse_resonance_trend(trend)

    def test_header_name_binding_survives_column_reorder(self, tmp_path):
        from tools.report_longitudinal import parse_resonance_trend
        header = "| chapter | overall | confidence | human_overridden |"
        trend = tmp_path / "truth" / "resonance_trend.md"
        trend.parent.mkdir(parents=True)
        trend.write_text(header + "\n| 7 | 90 | high | true |\n", encoding="utf-8")
        rows = parse_resonance_trend(trend)
        assert rows[7].overall == 90.0 and rows[7].excluded is True

    def test_nonnumeric_overall_row_excluded(self, tmp_path):
        from tools.report_longitudinal import parse_resonance_trend
        trend = _write_trend(tmp_path, [(1, 92), (2, 88)])
        with trend.open("a", encoding="utf-8") as fh:
            fh.write("| 3 | 高潮 | - | - | - | - | pending | high |  |\n")
        rows = parse_resonance_trend(trend)
        assert 3 not in rows  # 缺章由判层 fail-closed


class TestSegmentChapters:
    @pytest.mark.parametrize("n,expected", [
        (3, [1, 1, 1]), (4, [1, 1, 2]), (5, [1, 2, 2]),
        (6, [2, 2, 2]), (7, [2, 2, 3]), (8, [2, 3, 3]), (60, [20, 20, 20]),
    ])
    def test_enumerated_partition(self, n, expected):
        from tools.report_longitudinal import segment_chapters
        segs = segment_chapters(n)
        lengths = [len(segs["front"]), len(segs["mid"]), len(segs["back"])]
        assert lengths == expected
        assert segs["front"] + segs["mid"] + segs["back"] == list(range(1, n + 1))

    @pytest.mark.parametrize("n", [0, 1, 2])
    def test_insufficient_chapters_raises(self, n):
        from tools.report_longitudinal import LongitudinalDataError, segment_chapters
        with pytest.raises(LongitudinalDataError):
            segment_chapters(n)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_report_longitudinal.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'tools.report_longitudinal'`）

- [ ] **Step 3: 最小实现**（`tools/report_longitudinal.py` 新建——文件头 + 解析层）

```python
"""Longitudinal acceptance report for a pipeline project dir (spec #68).

Read-only verdict layer over already-persisted artifacts: novel.json targets,
truth/resonance_trend.md authoritative per-chapter scores, pipeline-state.json
chapter terminal health, audits/ raw reviewer reports, cost/token-ledger.jsonl.
Zero LLM, zero dispatch, zero src/shenbi/ mutation (pure-function imports only).
Exit codes: 0 pass / 1 fail / 2 data error (fail-closed — never pass silently
on missing data).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from shenbi.cost.ledger import TokenLedger
from shenbi.gates.shared import word_count_md
from shenbi.pipeline.audit_aggregate import FindingUnit, extract_finding_units
from shenbi.pipeline.chapter_loop import build_resonance_trend_row, committed_chapter_anchor
from shenbi.pipeline.machine import load_state
from shenbi.skill_utils.drift_detection.compute_drift import DriftFinding, detect_chapter_drift

SCHEMA_ID = "shenbi-longitudinal-verdict-v1"
TREND_FILENAME = "resonance_trend.md"
STATE_FILENAME = "pipeline-state.json"


class LongitudinalDataError(Exception):
    """Verdict-critical input missing/malformed → exit 2 (fail-closed)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def parse_novel_targets(novel_json: object) -> tuple[int, int]:
    """Return (target_word_count, total_chapters); raise on missing/zero keys."""
    if not isinstance(novel_json, dict):
        raise LongitudinalDataError("novel.json: not a JSON object")
    twc = novel_json.get("target_word_count")
    tc = novel_json.get("total_chapters")
    if not isinstance(twc, int) or twc <= 0:
        raise LongitudinalDataError("novel.json: target_word_count missing/zero")
    if not isinstance(tc, int) or tc <= 0:
        raise LongitudinalDataError("novel.json: total_chapters missing/zero")
    return twc, tc


@dataclass(frozen=True)
class ResonanceRow:
    overall: float
    excluded: bool


def parse_resonance_trend(path: Path) -> dict[int, ResonanceRow]:
    """Parse truth/resonance_trend.md rows keyed by bare {N} chapter cell.

    Column binding is by header name (chapter/overall/human_overridden), never
    by fixed index — a future skill-side column reorder must fail loud, not
    silently misread a numeric neighbour. Framework placeholder rows carry the
    contract header written only by the skill; a file without it is a data
    error (parse_trend would silently return an empty series — forbidden).
    """
    if not path.exists():
        raise LongitudinalDataError(f"{path}: resonance_trend.md missing")
    lines = path.read_text(encoding="utf-8").splitlines()
    header_idx, col = -1, {}
    for idx, line in enumerate(lines):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if "chapter" in cells and "overall" in cells:
            header_idx = idx
            col = {name: i for i, name in enumerate(cells)}
            break
    if header_idx < 0:
        raise LongitudinalDataError(f"{path}: contract header row missing")
    rows: dict[int, ResonanceRow] = {}
    for line in lines[header_idx + 1:]:
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not cells or all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
            continue  # markdown separator row
        try:
            ch = int(cells[col["chapter"]])
        except (ValueError, IndexError, KeyError):
            continue  # non-data row
        if ch in rows:
            raise LongitudinalDataError(f"{path}: duplicate chapter key {ch}")
        try:
            overall = float(cells[col["overall"]])
        except (ValueError, IndexError, KeyError):
            continue  # pending/- cell: chapter absent → fail-closed at verdict layer
        override_col = col.get("human_overridden")
        excluded = (
            cells[override_col].strip().lower() == "true"
            if override_col is not None and override_col < len(cells)
            else False
        )
        rows[ch] = ResonanceRow(overall=overall, excluded=excluded)
    if not rows:
        raise LongitudinalDataError(f"{path}: zero data rows")
    return rows


def segment_chapters(n_done: int) -> dict[str, list[int]]:
    """Enumerated partition: r=0→(f,f,f), r=1→(f,f,c), r=2→(f,c,c)."""
    if n_done < 3:
        raise LongitudinalDataError(f"insufficient chapters: {n_done}")
    f, r = divmod(n_done, 3)
    c = f + (1 if r else 0)
    lengths = [(f, f, f), (f, f, c), (f, c, c), (c, c, c)][r]
    out: dict[str, list[int]] = {"front": [], "mid": [], "back": []}
    start = 1
    for name, ln in zip(("front", "mid", "back"), lengths):
        out[name] = list(range(start, start + ln))
        start += ln
    return out
```

（`from shenbi...` 六个 import 中本 task 实际只用 `build_resonance_trend_row` 无——测试用它；文件头一次性带上全部 import 供后续 task 使用，避免反复改头。`zip(("front","mid","back"), lengths)` 长度对齐。）

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_report_longitudinal.py -q`
Expected: PASS（全部用例）

- [ ] **Step 5: Commit**

```bash
git add tools/report_longitudinal.py tests/unit/test_report_longitudinal.py
git commit -m "feat(tools): report_longitudinal parsing layer (spec #68 T1)"
```

---

### Task 2: 判定核心——三条件、判定顺序、漂移复用、escalation 计数

**Files:**
- Modify: `tools/report_longitudinal.py`（追加判定核心节）
- Test: `tests/unit/test_report_longitudinal.py`（追加 TestEvaluate* 类）

**Interfaces:**
- Consumes: T1 的 `LongitudinalDataError`/`parse_novel_targets`/`parse_resonance_trend`/`segment_chapters`/`ResonanceRow`；`committed_chapter_anchor`/`word_count_md`/`detect_chapter_drift`/`load_state`
- Produces:
  - `@dataclass(frozen=True) class ChapterVerdict`——`chapter: int`、`present: bool`、`status: str | None`、`audit_retry_count: int | None`、`resonance: float | None`、`cjk_chars: int`、`fail_reasons: tuple[str, ...]`
  - `def chapter_verdicts(project_dir: Path, n_done: int, rows: dict[int, ResonanceRow], state: dict) -> list[ChapterVerdict]`——三输入面 fail-closed（缺文件/缺键/缺行 → fail_reasons 记录）
  - `def escalation_counts_by_segment(checkpoint_history: list[dict], segments: dict[str, list[int]]) -> dict[str, int]`——`type == "escalation"` 且 `chapter` 为 int 且在段内才计数；`chapter=None` 计入返回值特殊键 `"unattributed"`（披露用）
  - `def drift_gate(rows: dict[int, ResonanceRow], n_done: int) -> list[DriftFinding]`——overall 序列（1..n_done 顺序）喂 `detect_chapter_drift`，`excluded` 章 index 进 `exclude_indices`
  - `def evaluate(project_dir: Path) -> dict`——判定顺序钉死：①parse_novel_targets/parse_resonance_trend/load_state（任一 LongitudinalDataError 上抛）；②`n_done < 3` 上抛；③逐章 fail-closed + `N_done < N_target` → fail；④质量三条件；返回完整 report dict（schema 见 Step 3）

- [ ] **Step 1: 写失败测试**（追加到 `tests/unit/test_report_longitudinal.py`；构造 helper `_mk_project` 用真实写方）

```python
def _mk_project(tmp_path: Path, *, chapters: list[int], scores: dict[int, int],
                target=200000, total=3, cjk_per_ch=30000,
                statuses: dict[int, str] | None = None,
                escalations: list[dict] | None = None) -> Path:
    """Real-producer construction (G0.9): safe_write novel.json, real trend rows,
    real state machine save, chapter files with prose + meta sections."""
    from shenbi.pipeline.machine import save_state
    from shenbi.pipeline.state import ChapterState, ChapterStatus, PipelineState

    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    novel = {"target_word_count": target, "total_chapters": total}
    (tmp_path / "novel.json").write_text(json.dumps(novel), encoding="utf-8")
    _write_trend(tmp_path, sorted((ch, scores[ch]) for ch in chapters))
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir(exist_ok=True)
    prose = "星" * cjk_per_ch  # CJK U+4E00-9FFF 内
    for ch in chapters:
        (chapters_dir / f"chapter-{ch}.md").write_text(
            f"# 第{ch}章\n\n{prose}\n\n## POST_WRITE_SELF_CHECK\n\n- 检查项\n",
            encoding="utf-8",
        )
    state = PipelineState(project_dir=str(tmp_path))
    for ch in chapters:
        cs = ChapterState()
        cs.status = ChapterStatus((statuses or {}).get(ch, "complete"))
        state.chapter_loop.chapter_states[str(ch)] = cs
    state.checkpoint_history = escalations or []
    save_state(tmp_path, state)
    return tmp_path


class TestChapterVerdicts:
    def test_healthy_chapters(self, tmp_path):
        from tools.report_longitudinal import chapter_verdicts, load_state_dict
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 90, 3: 88})
        rows = None  # filled below
        from tools.report_longitudinal import parse_resonance_trend
        rows = parse_resonance_trend(tmp_path / "truth" / "resonance_trend.md")
        state = load_state_dict(tmp_path)
        verdicts = chapter_verdicts(tmp_path, 3, rows, state)
        assert all(not v.fail_reasons for v in verdicts)
        assert verdicts[0].cjk_chars > 0  # word_count_md 口径（元节不计）

    def test_missing_state_key_fails_closed(self, tmp_path):
        from tools.report_longitudinal import chapter_verdicts, load_state_dict, parse_resonance_trend
        _mk_project(tmp_path, chapters=[1, 2, 4], scores={1: 92, 2: 90, 4: 88})
        state = load_state_dict(tmp_path)
        del state["chapter_loop"]["chapter_states"]["2"]
        rows = parse_resonance_trend(tmp_path / "truth" / "resonance_trend.md")
        verdicts = chapter_verdicts(tmp_path, 4, rows, state)
        v2 = next(v for v in verdicts if v.chapter == 2)
        assert any("chapter_states" in r for r in v2.fail_reasons)

    def test_missing_resonance_row_fails_closed(self, tmp_path):
        from tools.report_longitudinal import chapter_verdicts, load_state_dict, parse_resonance_trend
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 90, 3: 88})
        rows = parse_resonance_trend(tmp_path / "truth" / "resonance_trend.md")
        del rows[3]
        state = load_state_dict(tmp_path)
        verdicts = chapter_verdicts(tmp_path, 3, rows, state)
        assert any("resonance" in r for v in verdicts if v.chapter == 3 for r in v.fail_reasons)

    def test_missing_chapter_file_fails_closed(self, tmp_path):
        from tools.report_longitudinal import chapter_verdicts, load_state_dict, parse_resonance_trend
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 90, 3: 88})
        (tmp_path / "chapters" / "chapter-2.md").unlink()
        rows = parse_resonance_trend(tmp_path / "truth" / "resonance_trend.md")
        state = load_state_dict(tmp_path)
        verdicts = chapter_verdicts(tmp_path, 3, rows, state)
        v2 = next(v for v in verdicts if v.chapter == 2)
        assert v2.present is False and v2.fail_reasons


class TestEscalationCounts:
    def test_counts_by_segment_and_unattributed(self):
        from tools.report_longitudinal import escalation_counts_by_segment
        segs = {"front": [1, 2], "mid": [3, 4], "back": [5, 6]}
        hist = [
            {"type": "escalation", "chapter": 1, "decision": "approve"},
            {"type": "escalation", "chapter": 5, "decision": "reject"},
            {"type": "escalation", "chapter": None, "decision": "modify"},
            {"type": "checkpoint", "chapter": 3, "decision": "approve"},
        ]
        counts = escalation_counts_by_segment(hist, segs)
        assert counts == {"front": 1, "mid": 0, "back": 1, "unattributed": 1}


class TestDriftGate:
    def test_monotonic_decline_fires(self):
        from tools.report_longitudinal import ResonanceRow, drift_gate
        scores = {i: s for i, s in zip(range(1, 7), [95, 94, 93, 80, 78, 70])}
        rows = {ch: ResonanceRow(overall=s, excluded=False) for ch, s in scores.items()}
        assert drift_gate(rows, 6)  # ≥3 章单调下滑 + 累降 ≥3

    def test_excluded_chapters_do_not_poison(self):
        from tools.report_longitudinal import ResonanceRow, drift_gate
        rows = {ch: ResonanceRow(overall=s, excluded=ch in (4, 5, 6))
                for ch, s in zip(range(1, 7), [95, 94, 93, 80, 78, 70])}
        assert drift_gate(rows, 6) == []


class TestEvaluate:
    def test_pass(self, tmp_path):
        from tools.report_longitudinal import evaluate
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 91, 3: 90},
                    target=84000, cjk_per_ch=28000)
        report = evaluate(tmp_path)
        assert report["verdict"] == "pass" and report["exit_code"] == 0

    def test_back_drop_fails_trend(self, tmp_path):
        from tools.report_longitudinal import evaluate
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 95, 2: 80, 3: 79},
                    target=84000, cjk_per_ch=28000)
        report = evaluate(tmp_path)
        assert report["verdict"] == "fail" and any("降幅" in r for r in report["reasons"])

    def test_n_done_below_target_fails(self, tmp_path):
        from tools.report_longitudinal import evaluate
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 91, 3: 90},
                    target=84000, total=5, cjk_per_ch=28000)
        report = evaluate(tmp_path)
        assert report["verdict"] == "fail" and any("N_done" in r for r in report["reasons"])

    def test_n_done_above_target_discloses_not_fails(self, tmp_path):
        from tools.report_longitudinal import evaluate
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 91, 3: 90},
                    target=84000, total=2, cjk_per_ch=28000)
        report = evaluate(tmp_path)
        assert report["verdict"] == "pass"
        assert any("N_done > N_target" in d for d in report["disclosures"])

    def test_insufficient_chapters_data_error(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, evaluate
        _mk_project(tmp_path, chapters=[1], scores={1: 92})
        with pytest.raises(LongitudinalDataError):
            evaluate(tmp_path)

    def test_data_error_precedes_fail(self, tmp_path):
        """判定顺序：novel.json 坏（exit 2 面）优先于任何 fail 语义。"""
        from tools.report_longitudinal import LongitudinalDataError, evaluate
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 91, 3: 90})
        (tmp_path / "novel.json").write_text("{ broken", encoding="utf-8")
        with pytest.raises(LongitudinalDataError):
            evaluate(tmp_path)

    def test_retry_threshold_v1(self, tmp_path):
        """audit_retry_count != 0 → 逐章 fail（v1 从严）。"""
        from tools.report_longitudinal import evaluate
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 91, 3: 90},
                    target=84000, cjk_per_ch=28000, statuses={2: "complete"})
        import json as _json
        st = _json.loads((tmp_path / "pipeline-state.json").read_text(encoding="utf-8"))
        st["chapter_loop"]["chapter_states"]["2"]["audit_retry_count"] = 1
        (tmp_path / "pipeline-state.json").write_text(_json.dumps(st), encoding="utf-8")
        report = evaluate(tmp_path)
        assert report["verdict"] == "fail" and any("audit_retry" in r for r in report["reasons"])
```

（测试文件头部已 import `json`/`Path`/`pytest`；`load_state_dict` 为 T2 新增Produces。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_report_longitudinal.py -q`
Expected: FAIL（`ImportError: cannot import name 'chapter_verdicts'`）

- [ ] **Step 3: 实现**（追加到 `tools/report_longitudinal.py`）

```python
# ---------------------------------------------------------------------------
# Verdict core (spec #68 §1) — decision order: data-error → completeness → quality
# ---------------------------------------------------------------------------

VOLUME_RATIO_FLOOR = 0.95
RESONANCE_CHAPTER_FLOOR = 85.0
RESONANCE_MEAN_FLOOR = 90.0
BACK_DROP_MAX = 5.0
BACK_ESCALATION_FACTOR = 2


def load_state_dict(project_dir: Path) -> dict:
    """Load pipeline-state.json as plain dict (data-error face: exit 2)."""
    path = project_dir / STATE_FILENAME
    if not path.exists():
        raise LongitudinalDataError(f"{path}: pipeline-state.json missing")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LongitudinalDataError(f"{path}: broken JSON ({exc})") from exc
    if not isinstance(state, dict):
        raise LongitudinalDataError(f"{path}: not a JSON object")
    return state


def load_novel_json(project_dir: Path) -> dict:
    path = project_dir / "novel.json"
    if not path.exists():
        raise LongitudinalDataError(f"{path}: novel.json missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LongitudinalDataError(f"{path}: broken JSON ({exc})") from exc
    return data if isinstance(data, dict) else None  # type: ignore[return-value]


@dataclass(frozen=True)
class ChapterVerdict:
    chapter: int
    present: bool
    status: str | None
    audit_retry_count: int | None
    resonance: float | None
    cjk_chars: int
    fail_reasons: tuple[str, ...]


def chapter_verdicts(
    project_dir: Path, n_done: int, rows: dict[int, ResonanceRow], state: dict
) -> list[ChapterVerdict]:
    """Per-chapter terminal health with three-input-face fail-closed semantics."""
    raw_states = ((state.get("chapter_loop") or {}).get("chapter_states") or {})
    out: list[ChapterVerdict] = []
    for ch in range(1, n_done + 1):
        reasons: list[str] = []
        path = project_dir / "chapters" / f"chapter-{ch}.md"
        present = path.exists()
        cjk = word_count_md(path) if present else 0
        if not present:
            reasons.append(f"chapter-{ch}.md main file missing (0-word false-pass guard)")
        cs = raw_states.get(str(ch))
        status = cs.get("status") if isinstance(cs, dict) else None
        retry = cs.get("audit_retry_count") if isinstance(cs, dict) else None
        if cs is None:
            reasons.append(f"chapter_states missing key str({ch}) (mid-range hole)")
        else:
            if status != "complete":
                reasons.append(f"status={status!r} != 'complete'")
            if not isinstance(retry, int) or retry != 0:
                reasons.append(f"audit_retry_count={retry!r} != 0 (v1 strict)")
        row = rows.get(ch)
        if row is None:
            reasons.append(f"resonance row {ch} missing/non-numeric (fail-closed)")
        out.append(ChapterVerdict(
            chapter=ch, present=present, status=status, audit_retry_count=retry,
            resonance=row.overall if row else None, cjk_chars=cjk,
            fail_reasons=tuple(reasons),
        ))
    return out


def escalation_counts_by_segment(
    checkpoint_history: list[dict], segments: dict[str, list[int]]
) -> dict[str, int]:
    counts = {name: 0 for name in ("front", "mid", "back")}
    counts["unattributed"] = 0
    member = {ch: name for name, chs in segments.items() for ch in chs}
    for entry in checkpoint_history:
        if not isinstance(entry, dict) or entry.get("type") != "escalation":
            continue
        ch = entry.get("chapter")
        if isinstance(ch, int) and ch in member:
            counts[member[ch]] += 1
        else:
            counts["unattributed"] += 1
    return counts


def drift_gate(rows: dict[int, ResonanceRow], n_done: int) -> list[DriftFinding]:
    """Reuse compute_drift.detect_chapter_drift on the overall series (authoritative
    semantics live in the imported function — this wrapper only feeds it)."""
    series = [rows[ch].overall for ch in range(1, n_done + 1) if ch in rows]
    exclude = {i for i, ch in enumerate(range(1, n_done + 1))
               if ch in rows and rows[ch].excluded}
    return detect_chapter_drift(series, dim="overall", exclude_indices=exclude or None)


def evaluate(project_dir: Path) -> dict:
    """Full longitudinal verdict; raises LongitudinalDataError → exit 2."""
    target_wc, n_target = parse_novel_targets(load_novel_json(project_dir))
    rows = parse_resonance_trend(project_dir / "truth" / TREND_FILENAME)
    state = load_state_dict(project_dir)
    n_done = committed_chapter_anchor(project_dir)
    segments = segment_chapters(n_done)  # raises on n_done < 3
    verdicts = chapter_verdicts(project_dir, n_done, rows, state)

    reasons: list[str] = []
    disclosures: list[str] = []

    # completeness (exit-1 face, after data-error face above)
    if n_done < n_target:
        reasons.append(f"N_done={n_done} < N_target={n_target} (incomplete run / lost chapters)")
    if n_done > n_target:
        disclosures.append(f"N_done={n_done} > N_target={n_target} (anchor/metadata drift)")
    for v in verdicts:
        for r in v.fail_reasons:
            reasons.append(f"ch{v.chapter}: {r}")

    # quality — condition 1: volume
    cjk_total = sum(v.cjk_chars for v in verdicts)
    ratio = cjk_total / target_wc if target_wc else 0.0
    if cjk_total < target_wc * VOLUME_RATIO_FLOOR:
        reasons.append(f"volume {cjk_total} < {target_wc}×95% (ratio {ratio:.3f})")

    # quality — condition 2 residuals: resonance floors
    scored = [v.resonance for v in verdicts if v.resonance is not None]
    mean = sum(scored) / len(scored) if scored else 0.0
    for v in verdicts:
        if v.resonance is not None and v.resonance < RESONANCE_CHAPTER_FLOOR:
            reasons.append(f"ch{v.chapter}: resonance {v.resonance} < {RESONANCE_CHAPTER_FLOOR}")
    if mean < RESONANCE_MEAN_FLOOR:
        reasons.append(f"resonance mean {mean:.1f} < {RESONANCE_MEAN_FLOOR}")

    # quality — condition 3: trend + drift
    seg_means = {
        name: (lambda xs: sum(xs) / len(xs) if xs else None)(
            [verdicts[ch - 1].resonance for ch in chs if verdicts[ch - 1].resonance is not None]
        )
        for name, chs in segments.items()
    }
    back_drop = None
    if seg_means["front"] is not None and seg_means["back"] is not None:
        back_drop = seg_means["front"] - seg_means["back"]
        if back_drop > BACK_DROP_MAX:
            reasons.append(f"后段降幅 {back_drop:.1f} > {BACK_DROP_MAX}")
    esc = escalation_counts_by_segment(state.get("checkpoint_history") or [], segments)
    if esc["back"] > esc["front"] * BACK_ESCALATION_FACTOR:
        reasons.append(f"后段 escalation 计数 {esc['back']} > 前段 {esc['front']}×2")
    if esc["unattributed"]:
        disclosures.append(f"{esc['unattributed']} escalation 事件 chapter=None，排除出分段计数")
    findings = drift_gate(rows, n_done)
    if findings:
        reasons.extend(f"drift[{f.kind.value}] {f.dim}: {f.detail}" for f in findings)

    pending = state.get("pending_checkpoint") or {}
    if isinstance(pending, dict) and pending.get("type") not in (None, "none"):
        disclosures.append(f"pending_checkpoint={pending.get('type')} (未裁决，不入判据)")

    verdict = "fail" if reasons else "pass"
    return {
        "schema": SCHEMA_ID,
        "verdict": verdict,
        "exit_code": 1 if verdict == "fail" else 0,
        "reasons": reasons,
        "disclosures": disclosures,
        "n_target": n_target, "n_done": n_done,
        "segments": segments,
        "volume": {"target_word_count": target_wc, "cjk_total": cjk_total, "ratio": round(ratio, 4)},
        "per_chapter": [
            {"chapter": v.chapter, "present": v.present, "status": v.status,
             "audit_retry_count": v.audit_retry_count, "resonance": v.resonance,
             "cjk_chars": v.cjk_chars, "fail_reasons": list(v.fail_reasons)}
            for v in verdicts
        ],
        "trend": {"segment_resonance_means": seg_means,
                   "back_drop_vs_front": round(back_drop, 2) if back_drop is not None else None,
                   "escalation_counts": esc},
        "drift_findings": [{"kind": f.kind.value, "dim": f.dim, "detail": f.detail} for f in findings],
        "pending_checkpoint": pending or None,
    }
```

（`lambda` in dict comprehension 换成具名内部函数 `_mean(xs)` 更清晰——实现时用后者；`load_state` import 删除（未用，改 `load_state_dict` 纯 json 面——`machine.load_state` 返回强类型对象，而判层只需 dict 面；保留 json 直读避免 Strat 漂移）。**实现注意**：`from shenbi.pipeline.machine import load_state` 从文件头 import 列表中移除。）

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_report_longitudinal.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/report_longitudinal.py tests/unit/test_report_longitudinal.py
git commit -m "feat(tools): report_longitudinal verdict core (spec #68 T2)"
```

---

### Task 3: 失败分类学——映射表、audits 输入（raw 优先 + aggregate 回退）

**Files:**
- Modify: `tools/report_longitudinal.py`（追加分类学节）
- Test: `tests/unit/test_report_longitudinal_taxonomy.py`（新建）

**Interfaces:**
- Consumes: T1/T2 无新增依赖；`extract_finding_units`/`FindingUnit`
- Produces:
  - `TAXONOMY_RULES: dict[str, re.Pattern[str]]`——8 类（连续性断裂/人物漂移/世界规则违反/伏笔丢失/风格衰减/重复/节奏崩溃/敏感性）中文关键字正则
  - `SUBSYSTEM_ROUTES: dict[str, str]`——类别 → 嫌疑子系统
  - `def merge_units(reports: list[tuple[str, str]]) -> list[FindingUnit]`——raw glob 报告集 → `(severity, text)` 键去重 + reporters 并集（~10 行 glue，同 `write_audit_aggregate` :150-171 语义，无写操作）
  - `def load_audit_units(project_dir: Path, chapter: int) -> tuple[list[FindingUnit], str]`——返回 `(units, source)`，source ∈ `"raw"` | `"aggregate"` | `"none"`；raw glob `chapter-N-*.md` 优先；空则 aggregate（按 `## <SEV> Findings` H2 分节格式解析——`extract_finding_units` 对该格式零命中不可用）；都没有 → `([], "none")`（coverage 披露面）
  - `def classify(units: list[FindingUnit]) -> tuple[dict[str, int], int]`——返回 `(category_counts, unclassified_count)`

- [ ] **Step 1: 写失败测试**（`tests/unit/test_report_longitudinal_taxonomy.py` 新建）

```python
"""Spec #68 T3: failure taxonomy + audits input (raw-glob priority)."""
from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
AUDIT_SEEDS = [
    FIXTURES / "audits" / "chapter-1-character.md",
    FIXTURES / "audits" / "chapter-1-consistency.md",
]


class TestTaxonomyRules:
    def test_all_eight_categories_present(self):
        from tools.report_longitudinal import TAXONOMY_RULES
        assert set(TAXONOMY_RULES) == {
            "连续性断裂", "人物漂移", "世界规则违反", "伏笔丢失",
            "风格衰减", "重复", "节奏崩溃", "敏感性",
        }

    def test_routes_cover_categories(self):
        from tools.report_longitudinal import SUBSYSTEM_ROUTES, TAXONOMY_RULES
        assert set(SUBSYSTEM_ROUTES) == set(TAXONOMY_RULES)
        assert all(v for v in SUBSYSTEM_ROUTES.values())

    def test_classify_known_and_unknown(self):
        from tools.report_longitudinal import classify
        from shenbi.pipeline.audit_aggregate import FindingUnit
        units = [
            FindingUnit("WARNING", "人物语气与既定性格不符，对话脱离人设", ("a.md",)),
            FindingUnit("CRITICAL", "前文伏笔丢失：第2章埋设的金属片不再被提及", ("a.md",)),
            FindingUnit("WARNING", "无法归类的任意发现文本 xyzzy", ("b.md",)),
        ]
        counts, unclassified = classify(units)
        assert counts["人物漂移"] == 1 and counts["伏笔丢失"] == 1
        assert unclassified == 1


class TestMergeUnits:
    def test_dedup_on_severity_text_union_reporters(self):
        from tools.report_longitudinal import merge_units
        line = "- [WARNING] 人物语气与既定性格不符，对话脱离人设\n"
        units = merge_units([("chapter-1-character.md", line), ("chapter-1-consistency.md", line)])
        assert len(units) == 1
        assert units[0].reporters == ("chapter-1-character.md", "chapter-1-consistency.md")

    def test_real_fixture_seeds_produce_units(self):
        from tools.report_longitudinal import merge_units
        reports = [(p.name, p.read_text(encoding="utf-8")) for p in AUDIT_SEEDS]
        units = merge_units(reports)
        assert units, "真实 fixture 审计报告应产出至少一条 severity 发现"


class TestLoadAuditUnits:
    def test_raw_glob_priority(self, tmp_path):
        from tools.report_longitudinal import load_audit_units
        audits = tmp_path / "audits"
        audits.mkdir()
        (audits / "chapter-1-character.md").write_text(
            "- [WARNING] 人物语气与既定性格不符，对话脱离人设\n", encoding="utf-8")
        (audits / "chapter-1.aggregate.md").write_text(
            "# Chapter 1 — Audit Aggregate\n\n## WARNING Findings (1)\n\n- 无关条目\n",
            encoding="utf-8")
        units, source = load_audit_units(tmp_path, 1)
        assert source == "raw" and len(units) == 1

    def test_aggregate_fallback_parsed_by_h2_sections(self, tmp_path):
        from tools.report_longitudinal import load_audit_units
        audits = tmp_path / "audits"
        audits.mkdir()
        (audits / "chapter-1.aggregate.md").write_text(
            "# Chapter 1 — Audit Aggregate\n\n## CRITICAL Findings (1)\n\n"
            "- 人物语气与既定性格不符，对话脱离人设\n  - 报告方: chapter-1-character.md\n",
            encoding="utf-8")
        units, source = load_audit_units(tmp_path, 1)
        assert source == "aggregate" and len(units) == 1
        assert units[0].severity == "CRITICAL"

    def test_none_when_absent(self, tmp_path):
        from tools.report_longitudinal import load_audit_units
        units, source = load_audit_units(tmp_path, 1)
        assert units == [] and source == "none"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_report_longitudinal_taxonomy.py -q`
Expected: FAIL（`ImportError: TAXONOMY_RULES`）

- [ ] **Step 3: 实现**（追加到 `tools/report_longitudinal.py`）

```python
# ---------------------------------------------------------------------------
# Failure taxonomy (spec #68 §3) — deterministic keyword mapping, raw-glob priority
# ---------------------------------------------------------------------------

TAXONOMY_RULES: dict[str, re.Pattern[str]] = {
    "连续性断裂": re.compile(r"连续性|前后矛盾|与前文|时间线|断裂|不一致"),
    "人物漂移": re.compile(r"人物|人设|性格|语气|角色.*(不符|漂移|崩)|OOC"),
    "世界规则违反": re.compile(r"世界观|设定.*(违反|冲突)|规则|体系|魔法|灵能.*(矛盾|冲突)"),
    "伏笔丢失": re.compile(r"伏笔|铺垫.*(丢|断)|呼应.*缺失|回收"),
    "风格衰减": re.compile(r"风格|文笔|笔力|语言.*(退化|衰减)|了字密度|句式"),
    "重复": re.compile(r"重复|冗余|雷同|复用.*过度"),
    "节奏崩溃": re.compile(r"节奏|拖沓|仓促|结构.*失衡|密度"),
    "敏感性": re.compile(r"敏感|安全|合规|暴力|未成年"),
}

SUBSYSTEM_ROUTES: dict[str, str] = {
    "连续性断裂": "state-settling + shenbi-review-consistency",
    "人物漂移": "truth-sync(character_matrix) + shenbi-review-character",
    "世界规则违反": "truth-sync(world) + shenbi-review-worldbuilding",
    "伏笔丢失": "foreshadowing-track + shenbi-review-foreshadowing",
    "风格衰减": "style-learning + shenbi-review-style",
    "重复": "context-assemble + shenbi-review-repetition",
    "节奏崩溃": "context-assemble + shenbi-review-pacing",
    "敏感性": "shenbi-review-safety",
}

RAW_GLOB_RE = re.compile(r"^chapter-(\d+)-.+\.md$")
AGG_RE = re.compile(r"^chapter-(\d+)\.aggregate\.md$")


def merge_units(reports: list[tuple[str, str]]) -> list[FindingUnit]:
    """Same semantics as write_audit_aggregate's inlined loop (:150-171) —
    (severity, text) key dedup + reporters union — without the write."""
    merged: dict[tuple[str, str], FindingUnit] = {}
    for name, content in reports:
        units, _ctx = extract_finding_units(name, content)
        for u in units:
            key = (u.severity, u.text)
            if key in merged:
                prev = merged[key]
                merged[key] = FindingUnit(
                    u.severity, u.text,
                    tuple(dict.fromkeys([*prev.reporters, *u.reporters])),
                )
            else:
                merged[key] = u
    return list(merged.values())


def _parse_aggregate_sections(content: str) -> list[FindingUnit]:
    """Parse aggregate's own render format: `## <SEV> Findings (n)` H2 sections
    with severity-stripped bullets (extract_finding_units returns zero on it)."""
    units: list[FindingUnit] = []
    sev: str | None = None
    for line in content.splitlines():
        m = re.match(r"^## (BLOCKING|CRITICAL|WARNING|ERROR) Findings", line)
        if m:
            sev = m.group(1)
            continue
        if line.startswith("## "):
            sev = None
            continue
        s = line.strip()
        if sev and s.startswith("- ") and not s.startswith("- 报告方"):
            units.append(FindingUnit(sev, s.lstrip("- ").strip(), ("aggregate",)))
    return units


def load_audit_units(project_dir: Path, chapter: int) -> tuple[list[FindingUnit], str]:
    audits = project_dir / "audits"
    raw = sorted(
        p for p in audits.glob(f"chapter-{chapter}-*.md") if RAW_GLOB_RE.match(p.name)
    ) if audits.is_dir() else []
    if raw:
        return merge_units([(p.name, p.read_text(encoding="utf-8")) for p in raw]), "raw"
    agg = audits / f"chapter-{chapter}.aggregate.md"
    if agg.exists():
        return _parse_aggregate_sections(agg.read_text(encoding="utf-8")), "aggregate"
    return [], "none"


def classify(units: list[FindingUnit]) -> tuple[dict[str, int], int]:
    counts = {cat: 0 for cat in TAXONOMY_RULES}
    unclassified = 0
    for u in units:
        hits = [cat for cat, pat in TAXONOMY_RULES.items() if pat.search(u.text)]
        if hits:
            counts[hits[0]] += 1  # first-match v1 (rule order = priority)
        else:
            unclassified += 1
    return counts, unclassified
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_report_longitudinal_taxonomy.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/report_longitudinal.py tests/unit/test_report_longitudinal_taxonomy.py
git commit -m "feat(tools): report_longitudinal failure taxonomy (spec #68 T3)"
```

---

### Task 4: 观测面——ledger 按章聚合、truth 增长、coverage 披露、taxonomy 并网

**Files:**
- Modify: `tools/report_longitudinal.py`（追加观测节 + `evaluate` 扩展）
- Test: `tests/unit/test_report_longitudinal_report.py`（新建）

**Interfaces:**
- Consumes: T2 `evaluate` 返回的 report dict；T3 `load_audit_units`/`classify`；`TokenLedger`
- Produces:
  - `def ledger_stats(project_dir: Path, chapters: list[int], cjk_by_ch: dict[int, int]) -> dict`——`{"per_chapter": [{"chapter", "cost_usd", "wall_clock_s", "cjk_chars", "cost_per_10k", "attempts"}], "skipped_rows": int, "chapters_covered": int}`；skipped_rows = 非空行数 − yield 数（`iter_records` 静默跳行不可见——单独披露）；wall_clock = 章内首末 timestamp 差
  - `def truth_growth(project_dir: Path) -> dict`——`{"current": [{"file", "bytes"}], "snapshots": [{"snapshot", "bytes"}], "note": str}`（条件性：快照由技能步骤写，按实际存在输出 + 覆盖度注记；`tests/fixtures/snapshots/` 是该面真实样例）
  - `def coverage_block(...)`——组装 `report["coverage"]`（resonance 行数比 / audits 章覆盖比 / ledger 章覆盖比 + 跳行数 / 分类命中比）
  - `evaluate()` 扩展返回 dict 追加 `coverage`/`taxonomy`/`scalability` 三键（taxonomy heatmap = 每章 classify 计数 + 全书 unclassified + routing 表）

- [ ] **Step 1: 写失败测试**（`tests/unit/test_report_longitudinal_report.py` 新建）

```python
"""Spec #68 T4: observations — ledger per-chapter, truth growth, coverage."""
from __future__ import annotations

from datetime import datetime, timedelta, UTC
from pathlib import Path


def _record(tmp_path: Path, chapter: int, *, cost=0.01, minutes=0, attempt=1):
    from shenbi.cost.ledger import TokenLedger
    led = TokenLedger(tmp_path)
    usage = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
    ts = datetime(2026, 9, 21, 12, 0, tzinfo=UTC) + timedelta(minutes=minutes)
    rec = led.record("shenbi-chapter-drafting", chapter, usage, attempt=attempt)
    # record() 打真实时钟——测试用回写行保持时间可控（仍经真实写方追加）
    import json as _json
    lines = (tmp_path / "cost" / "token-ledger.jsonl").read_text(encoding="utf-8").splitlines()
    row = _json.loads(lines[-1])
    row["timestamp"] = ts.isoformat()
    row["estimated_cost_usd"] = cost
    lines[-1] = _json.dumps(row, ensure_ascii=False)
    (tmp_path / "cost" / "token-ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestLedgerStats:
    def test_per_chapter_aggregation_and_wallclock(self, tmp_path):
        from tools.report_longitudinal import ledger_stats
        _record(tmp_path, 1, cost=0.01, minutes=0)
        _record(tmp_path, 1, cost=0.02, minutes=30)
        _record(tmp_path, 2, cost=0.03, minutes=90)
        stats = ledger_stats(tmp_path, [1, 2], {1: 10000, 2: 20000})
        by_ch = {e["chapter"]: e for e in stats["per_chapter"]}
        assert by_ch[1]["cost_usd"] == 0.03
        assert by_ch[1]["wall_clock_s"] == 1800.0
        assert by_ch[2]["cost_per_10k"] == pytest_approx(0.015)
        assert by_ch[1]["attempts"] == 2
        assert stats["skipped_rows"] == 0 and stats["chapters_covered"] == 2

    def test_skipped_rows_disclosed(self, tmp_path):
        from tools.report_longitudinal import ledger_stats
        _record(tmp_path, 1)
        led = tmp_path / "cost" / "token-ledger.jsonl"
        led.write_text(led.read_text(encoding="utf-8") + "{corrupt\n", encoding="utf-8")
        stats = ledger_stats(tmp_path, [1], {1: 10000})
        assert stats["skipped_rows"] == 1

    def test_missing_ledger_zero_coverage(self, tmp_path):
        from tools.report_longitudinal import ledger_stats
        stats = ledger_stats(tmp_path, [1], {1: 10000})
        assert stats["per_chapter"] == [] and stats["chapters_covered"] == 0


def pytest_approx(x, tol=1e-9):
    class _A:
        def __eq__(self, other):
            return abs(other - x) < tol
    return _A()


class TestTruthGrowth:
    def test_current_sizes_and_conditional_note(self, tmp_path):
        from tools.report_longitudinal import truth_growth
        truth = tmp_path / "truth"
        truth.mkdir()
        (truth / "current_state.md").write_text("# 状态\n" + "x" * 500, encoding="utf-8")
        out = truth_growth(tmp_path)
        assert {"file": "current_state.md", "bytes": 500 + len("# 状态\n".encode())} in (
            {"file": e["file"], "bytes": e["bytes"]} for e in out["current"]
        )
        assert "快照" in out["note"] or "snapshot" in out["note"]
```

（`_record` 的时间回写注释解释了为何仍算真实写方路径：行由 `TokenLedger.record` 追加、仅 timestamp/cost 字段回写为受控值——与 `iter_records` 兼容契约一致。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_report_longitudinal_report.py -q`
Expected: FAIL（`ImportError: ledger_stats`）

- [ ] **Step 3: 实现**（追加到 `tools/report_longitudinal.py`；`evaluate` 末尾并入观测三键）

```python
# ---------------------------------------------------------------------------
# Observations (spec #68 §4) + coverage disclosure (§2)
# ---------------------------------------------------------------------------

def ledger_stats(project_dir: Path, chapters: list[int], cjk_by_ch: dict[int, int]) -> dict:
    """Per-chapter cost/wall-clock/attempts from cost/token-ledger.jsonl.

    skipped_rows = non-blank lines minus yielded records — iter_records
    silently drops corrupt/malformed rows; intra-chapter row loss is invisible
    to chapter coverage, so it is disclosed separately (spec round-5 ㊱).
    """
    path = project_dir / "cost" / "token-ledger.jsonl"
    per: dict[int, dict] = {}
    skipped = 0
    covered: set[int] = set()
    if path.exists():
        non_blank = sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())
        yielded = 0
        for rec in TokenLedger(project_dir).iter_records():
            yielded += 1
            e = per.setdefault(rec.chapter, {"cost": 0.0, "first": rec.timestamp,
                                             "last": rec.timestamp, "attempts": 0})
            e["cost"] += rec.estimated_cost_usd
            if rec.timestamp < e["first"]:
                e["first"] = rec.timestamp
            if rec.timestamp > e["last"]:
                e["last"] = rec.timestamp
            e["attempts"] = max(e["attempts"], rec.attempt)
            covered.add(rec.chapter)
        skipped = non_blank - yielded
    out = []
    for ch in chapters:
        e = per.get(ch)
        if not e:
            continue
        cjk = cjk_by_ch.get(ch, 0)
        try:
            wall = (
                datetime.fromisoformat(e["last"]) - datetime.fromisoformat(e["first"])
            ).total_seconds()
        except ValueError:
            wall = None
        out.append({
            "chapter": ch, "cost_usd": round(e["cost"], 6), "wall_clock_s": wall,
            "cjk_chars": cjk,
            "cost_per_10k": round(e["cost"] / (cjk / 10000), 8) if cjk else None,
            "attempts": e["attempts"],
        })
    return {"per_chapter": out, "skipped_rows": skipped, "chapters_covered": len(covered)}


def truth_growth(project_dir: Path) -> dict:
    """Truth-file sizes now + snapshot faces when present (conditional: the
    automatic snapshot was removed by spec #26 path 3 — coverage disclosed)."""
    truth = project_dir / "truth"
    current = (
        [{"file": p.name, "bytes": p.stat().st_size} for p in sorted(truth.glob("*.md"))]
        if truth.is_dir() else []
    )
    snaps = project_dir / "snapshots"
    snapshot_files = (
        [{"snapshot": p.name, "bytes": p.stat().st_size}
         for p in sorted(snaps.rglob("truth/*.md"))[:200]]
        if snaps.is_dir() else []
    )
    note = (
        "逐章历史快照由条件技能步骤写，不保证逐章落盘（spec #26 path 3）——按实际存在面输出"
        if not snapshot_files else f"快照面覆盖 {len(snapshot_files)} 个 truth 文件"
    )
    return {"current": current, "snapshots": snapshot_files, "note": note}
```

（`datetime` 需加文件头 import：`from datetime import datetime`。`evaluate()` 末尾追加：

```python
    # observations + coverage + taxonomy 并网（T4）
    chapters_list = list(range(1, n_done + 1))
    cjk_by_ch = {v.chapter: v.cjk_chars for v in verdicts}
    audit_sources: dict[str, int] = {"raw": 0, "aggregate": 0, "none": 0}
    heatmap: dict[tuple[int, str], int] = {}
    unclassified_total = 0
    classified_total = 0
    for v in verdicts:
        units, source = load_audit_units(project_dir, v.chapter)
        audit_sources[source] += 1
        counts, uncl = classify(units)
        unclassified_total += uncl
        classified_total += sum(counts.values())
        for cat, n in counts.items():
            if n:
                heatmap[(v.chapter, cat)] = n
    report["taxonomy"] = {
        "heatmap": [{"chapter": ch, "category": cat, "count": n}
                     for (ch, cat), n in sorted(heatmap.items())],
        "unclassified": unclassified_total,
        "routing": SUBSYSTEM_ROUTES,
        "audit_sources": audit_sources,
    }
    led = ledger_stats(project_dir, chapters_list, cjk_by_ch)
    report["scalability"] = {
        "per_chapter": led["per_chapter"],
        "truth_growth": truth_growth(project_dir),
    }
    report["coverage"] = {
        "resonance_rows": [len(rows), n_done],
        "audits_chapters": [n_done - audit_sources["none"], n_done],
        "ledger_chapters": [led["chapters_covered"], n_done],
        "ledger_skipped_rows": led["skipped_rows"],
        "classified": [classified_total, classified_total + unclassified_total],
    }
    return report
```

——直接嵌进 `evaluate` 原返回语句前组装后统一 return。）

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_report_longitudinal_report.py tests/unit/test_report_longitudinal.py -q`
Expected: PASS（含 T2 回归）

- [ ] **Step 5: Commit**

```bash
git add tools/report_longitudinal.py tests/unit/test_report_longitudinal_report.py
git commit -m "feat(tools): report_longitudinal observations + coverage (spec #68 T4)"
```

---

### Task 5: 渲染 + CLI——双报告、exit 三态、metrics/ 输出根

**Files:**
- Modify: `tools/report_longitudinal.py`（追加渲染 + main）
- Test: `tests/unit/test_report_longitudinal_report.py`（追加 TestCli 类）

**Interfaces:**
- Consumes: T2/T4 的 `evaluate` report dict
- Produces:
  - `def render_markdown(report: dict) -> str`——曲线表（三段均值/escalation）+ 类别×章节热力图 + 责任子系统路由 + coverage 披露 + reasons/disclosures
  - `def write_reports(project_dir: Path, report: dict) -> tuple[Path, Path]`——写 `metrics/longitudinal-report.md` + `.json`（`json.dumps(..., ensure_ascii=False, indent=2)`）
  - `def main(argv: list[str] | None = None) -> int`——argparse `project_dir`；`LongitudinalDataError` → stderr + return 2；verdict fail → return 1；pass → return 0

- [ ] **Step 1: 写失败测试**（追加到 `tests/unit/test_report_longitudinal_report.py`；复用 T2 测试的 `_mk_project`——**从 `tests/unit/test_report_longitudinal.py` import**）

```python
class TestCliEndToEnd:
    def test_pass_project_writes_both_reports_exit0(self, tmp_path, monkeypatch, capsys):
        from tests.unit.test_report_longitudinal import _mk_project
        from tools.report_longitudinal import main
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 91, 3: 90},
                    target=84000, cjk_per_ch=28000)
        rc = main([str(tmp_path)])
        assert rc == 0
        md = tmp_path / "metrics" / "longitudinal-report.md"
        js = tmp_path / "metrics" / "longitudinal-report.json"
        assert md.exists() and js.exists()
        data = json.loads(js.read_text(encoding="utf-8"))
        assert data["schema"] == "shenbi-longitudinal-verdict-v1"
        assert data["verdict"] == "pass" and data["exit_code"] == 0
        assert set(data) >= {"verdict", "exit_code", "reasons", "disclosures", "n_target",
                              "n_done", "segments", "volume", "per_chapter", "trend",
                              "drift_findings", "coverage", "taxonomy", "scalability",
                              "pending_checkpoint"}
        assert "责任子系统" in md.read_text(encoding="utf-8")

    def test_fail_exit1(self, tmp_path):
        from tests.unit.test_report_longitudinal import _mk_project
        from tools.report_longitudinal import main
        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 95, 2: 80, 3: 79},
                    target=84000, cjk_per_ch=28000)
        assert main([str(tmp_path)]) == 1

    def test_data_error_exit2(self, tmp_path, capsys):
        from tools.report_longitudinal import main
        (tmp_path / "novel.json").write_text("{ broken", encoding="utf-8")
        assert main([str(tmp_path)]) == 2
        assert "novel.json" in capsys.readouterr().err
```

（文件头补 `import json`。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_report_longitudinal_report.py -q`
Expected: FAIL（`ImportError: main`）

- [ ] **Step 3: 实现**（追加到 `tools/report_longitudinal.py`）

```python
# ---------------------------------------------------------------------------
# Rendering + CLI (spec #68 §1 判定输出 / §2 输出)
# ---------------------------------------------------------------------------

def render_markdown(report: dict) -> str:
    t = report["trend"]
    lines = [
        "# Longitudinal Report",
        "",
        f"- **verdict**: {report['verdict']} (exit {report['exit_code']})",
        f"- **N**: target={report['n_target']} done={report['n_done']}",
        f"- **保量**: {report['volume']['cjk_total']} / {report['volume']['target_word_count']}"
        f" (ratio {report['volume']['ratio']:.3f})",
        "",
        "## 三段曲线",
        "",
        "| 段 | 章节 | resonance 均值 | escalation 计数 |",
        "|---|---|---|---|",
    ]
    seg_span = {name: f"{v[0]}–{v[-1]}" if v else "-" for name, v in report["segments"].items()}
    for name in ("front", "mid", "back"):
        m = t["segment_resonance_means"].get(name)
        lines.append(
            f"| {name} | {seg_span[name]} | "
            f"{m:.1f}" if m is not None else f"| {name} | {seg_span[name]} | - |"
        )  # 实现时按行拼接均值与计数两列，勿复用此压缩写法
    lines += ["", "## 类别×章节热力图", ""]
    if report["taxonomy"]["heatmap"]:
        lines += ["| 章节 | 类别 | 计数 |", "|---|---|---|"]
        lines += [f"| {e['chapter']} | {e['category']} | {e['count']} |"
                  for e in report["taxonomy"]["heatmap"]]
    else:
        lines.append("（无分类命中）")
    uncl = report["taxonomy"]["unclassified"]
    lines += ["", f"未分类发现: {uncl}", "", "## 责任子系统路由", ""]
    for cat, route in report["taxonomy"]["routing"].items():
        lines.append(f"- {cat} → {route}")
    cov = report["coverage"]
    lines += [
        "", "## Coverage 披露", "",
        f"- resonance 行数: {cov['resonance_rows'][0]}/{cov['resonance_rows'][1]}",
        f"- audits 章覆盖: {cov['audits_chapters'][0]}/{cov['audits_chapters'][1]}"
        f"（raw={report['taxonomy']['audit_sources']['raw']}, "
        f"aggregate 回退={report['taxonomy']['audit_sources']['aggregate']}, "
        f"无={report['taxonomy']['audit_sources']['none']}）",
        f"- ledger 章覆盖: {cov['ledger_chapters'][0]}/{cov['ledger_chapters'][1]}"
        f"（跳行 {cov['ledger_skipped_rows']}）",
        f"- 分类命中: {cov['classified'][0]}/{cov['classified'][1]}",
    ]
    if report["reasons"]:
        lines += ["", "## Fail 原因", ""] + [f"- {r}" for r in report["reasons"]]
    if report["disclosures"]:
        lines += ["", "## 披露", ""] + [f"- {d}" for d in report["disclosures"]]
    scal = report["scalability"]["per_chapter"]
    if scal:
        lines += ["", "## 扩展性（每章）", "",
                  "| 章 | 成本$ | 墙钟s | 万字成本$ | 派发尝试 |", "|---|---|---|---|---|"]
        lines += [
            f"| {e['chapter']} | {e['cost_usd']:.4f} | {e['wall_clock_s']} | "
            f"{e['cost_per_10k'] if e['cost_per_10k'] is not None else '-'} | {e['attempts']} |"
            for e in scal
        ]
    lines += ["", f"> schema: {report['schema']}; 真相增长: "
              f"{report['scalability']['truth_growth']['note']}"]
    return "\n".join(lines) + "\n"


def write_reports(project_dir: Path, report: dict) -> tuple[Path, Path]:
    metrics = project_dir / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    md = metrics / "longitudinal-report.md"
    js = metrics / "longitudinal-report.json"
    js.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md.write_text(render_markdown(report), encoding="utf-8")
    return md, js


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Longitudinal acceptance report (spec #68)")
    parser.add_argument("project_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.project_dir)
    except LongitudinalDataError as exc:
        print(f"data error: {exc.reason}", file=sys.stderr)
        return 2
    write_reports(args.project_dir, report)
    print(f"verdict: {report['verdict']} ({report['exit_code']}) — "
          f"{args.project_dir / 'metrics' / 'longitudinal-report.json'}")
    for r in report["reasons"]:
        print(f"  fail: {r}")
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
```

（`render_markdown` 中三段表格行的注释明示实现时用直白拼接——plan 代码里那段压缩写法有歧义，落地时以「每行四列完整拼接」为准。）

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_report_longitudinal_report.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/report_longitudinal.py tests/unit/test_report_longitudinal_report.py
git commit -m "feat(tools): report_longitudinal rendering + CLI exit tri-state (spec #68 T5)"
```

---

### Task 6: justfile 接线 + plans INDEX 登记 + 终验

**Files:**
- Modify: `justfile`（追加两个 recipe）
- Modify: `docs/superpowers/plans/INDEX.md`（登记本 plan ✅ ready → 执行后状态由阶段 5 更新）
- Test: `tests/unit/test_report_longitudinal_report.py`（追加 recipe 语义断言）

**Interfaces:**
- Consumes: T5 `main` exit 三态
- Produces: `just e2e-report <dir>`（shebang 形式，exec 保三态传播）；`just e2e-canary`（文档化语义，不进 just check）

- [ ] **Step 1: 写失败测试**（追加）

```python
class TestJustfileRecipes:
    def test_e2e_recipes_present_and_semantics_documented(self):
        justfile = Path(__file__).resolve().parent.parent.parent / "justfile"
        text = justfile.read_text(encoding="utf-8")
        assert "e2e-report" in text and "e2e-canary" in text
        assert "#!/usr/bin/env bash" in text.split("e2e-report")[1][:200]  # shebang 形式
        # canary 语义三要素：停机/人工裁决/不进 check
        canary_block = text.split("e2e-canary")[1][:800]
        assert "exit 3" in canary_block or "checkpoint" in canary_block
        assert "pipeline-review" in canary_block

    def test_check_does_not_invoke_e2e(self):
        justfile = Path(__file__).resolve().parent.parent.parent / "justfile"
        text = justfile.read_text(encoding="utf-8")
        check_block = text.split("\ncheck:")[1].split("\n\n")[0] if "\ncheck:" in text else ""
        assert "e2e-report" not in check_block and "e2e-canary" not in check_block
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_report_longitudinal_report.py::TestJustfileRecipes -q`
Expected: FAIL（justfile 无 e2e recipe）

- [ ] **Step 3: 实现**（justfile 末尾 pipeline recipe 区后追加）

```make
# Longitudinal acceptance report: exit 0 pass / 1 fail / 2 data error (spec #68).
# Shebang form so the tool's tri-state exit code propagates (linewise may collapse 2→1).
e2e-report dir:
    #!/usr/bin/env bash
    set -euo pipefail
    exec uv run python tools/report_longitudinal.py "{{dir}}"

# Canary fast loop: 3-chapter/3000-word seed through run_pipeline.sh.
# Stops at first checkpoint (exit 3) — NEVER auto-approves; resolve manually with
# `just pipeline-review <dir> <decision>` then re-run. NOT in `just check` (paid dispatch).
# Expected retry noise: seed ~1000 words/chapter < G4 floor 3000/chapter — every chapter
# walks the G4 fail→corrective-retry→auto-continue path (doubled drafting dispatch cost).
e2e-canary:
    #!/usr/bin/env bash
    set -euo pipefail
    dir="novel-canary-$(date +%Y%m%d-%H%M%S)"
    uv run pipeline init tests/fixtures/canary-3-chapter-seed.md --project-dir "$dir"
    ./run_pipeline.sh "$dir"
    echo "blocked at checkpoint or completed — run 'just pipeline-review $dir <decision>' to continue"
```

plans/INDEX.md 登记（该文件活跃 plan 列表）：

```markdown
### 2026-09-21 · spec68-longitudinal-acceptance

- **文件**：`2026-09-21-spec68-longitudinal-acceptance.md`
- **spec**：#68 | **状态**：✅ ready | **task 数**：6
```

（以 plans/INDEX.md 现行格式为准插入对应列。）

- [ ] **Step 4: 跑测试 + 手工验证三态传播**

Run: `uv run pytest tests/unit/test_report_longitudinal_report.py -q && uv run pytest tests/unit/test_report_longitudinal.py tests/unit/test_report_longitudinal_taxonomy.py -q`
Expected: 全 PASS

三态传播实测（构造 tmp 项目经 `uv run python` 与 `just e2e-report` 双跑对照 exit code）：

```bash
d=$(mktemp -d)/proj && mkdir -p "$d/truth" "$d/chapters" "$d/audits"
printf '{"target_word_count": 3000, "total_chapters": 3}' > "$d/novel.json"
just e2e-report "$d"; echo "exit=$?"   # 期望 2（resonance_trend 缺失 data error）
```

Expected: stderr 含 `resonance_trend.md missing`，`exit=2`

- [ ] **Step 5: 终验 + Commit**

```bash
just check
# EXIT=0 后：
git add justfile docs/superpowers/plans/INDEX.md tests/unit/test_report_longitudinal_report.py
git commit -m "feat(justfile): e2e-report/e2e-canary recipes (spec #68 T6)"
```

---

## Self-Review（写 plan 后自查记录）

1. **Spec 覆盖**：§1 三条件→T2；§1 边界语义全部→T1（分段/缺行）+T2（三面 fail-closed/N/顺序/exit 面）；§2 输入面五条→T1（resonance 解析/表头）+T2（state/novel）+T3（audits raw 优先）；§3→T3；§4→T4（截断观测按 spec 边界不做——复活条件在 spec）；§5→T6；§6 登记→已在注册 commit 落地；验收五条→验收覆盖表。**无缺口**。
2. **Placeholder 扫描**：T5 render_markdown 的三段表行有「压缩写法」注释并声明落地以直白拼接为准——非 placeholder（语义完整）；T6 Step 3 的 plans/INDEX 格式「以现行格式为准」——落地时核对现文件列名。其余步骤均含完整代码。
3. **类型一致性**：`ResonanceRow.overall: float`（T1）↔ T2 `chapter_verdicts` 消费 `rows: dict[int, ResonanceRow]` ✓；`ChapterVerdict` 字段 ↔ T4 `cjk_by_ch` 消费 `.cjk_chars` ✓；`load_audit_units -> tuple[list[FindingUnit], str]` ↔ T4 消费 ✓；`main(argv) -> int` ↔ T6 justfile exec ✓。
4. **G3.4/F947**：N/A / 合规（声明在前）。
5. **执行方式**：全部 leaf、协调者亲自实现（单模型现实 + 语义钉死密集）；每 task commit 后 fresh-context 全量重审 → `.superpowers/sdd/audit-T<N>.md`，无 audit-T<N>.md 不得开始 T<N+1>。
