# Spec #110 · judge-reliability-harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 判官间信度/分布形状离线确定性报告工具 `just judge-reliability`（κ/α/效度相关/形状五件，零 LLM）+ #107/#103/resonance SKILL 三处判据营养接线。

**Architecture:** 薄壳工具 `tools/judge_reliability.py`：卫生判定复用 `check_audit_starve_verdict`（#109 T4 单源）、issue 计数复用 `extract_finding_units`、trend 解析复用并扩展 `parse_resonance_trend`（confidence 列）；新建仅统计核心（κ/α/相关/形状纯函数）。报告落 `reports/judge-reliability-<ts>.md`，观测面不进生产读面。T2/T3 接线为三处一行级 spec/SKILL 文本修订。

**Tech Stack:** Python 3.11+ / pathlib / argparse / 标准库 statistics（无第三方依赖）；tests/pytest；justfile recipe。

## Global Constraints（spec 项目级约束逐字块——每次审查派发注入）

- **复用钉死**：卫生判定=复用 `check_audit_starve_verdict`（`src/shenbi/pipeline/llm_output_integrity.py:405`——#109 T4 单源分类器，全判定行值段匹配+散文提及豁免；词族常量由该函数内部消费自 `audit_starve_family` 单源，禁自写词表/自写扫描循环）；issue 计数=复用 `extract_finding_units`（`src/shenbi/pipeline/audit_aggregate.py:114`）；trend 解析=复用 `parse_resonance_trend`（`tools/report_longitudinal.py:68`——tools 互引走仓内既有 sys.path+E402 noqa 先例，无 lint 拦截）
- **κ 口径**：评级变量=「有无硬发现」二值（与 α 同源；硬发现=severity ∈ {BLOCKING, CRITICAL}——`src/shenbi/contracts/enums.py:9` Severity 词表）+ 计数版并报；族级聚合=OR；join 面=成对完整例+报告逐对披露 n；同派发族对（group-character 四成员互对/group-craft 成员互对）κ 行附「同派发伪影」注记
- **α 口径**：全 10 always-on items 与剔除 craft 族成员（texture/reader-pull/anti-ai）的 7 items 两版并报；「有无硬发现」二值+计数两版
- **分布形状**：模值频率表、sd、极差、相当/更差/更好计数（Route A 八列表按列名「相对位置」绑定）、通胀 slope（章号回归）、confidence 基率
- **冷启动披露**：实评行 <8 时分布形状节输出「样本不足」披露行，不输出误导值
- **报告双报义务**（#115 T4 对齐）：报告须同时含「分布形状」与「外部锚定效度引用」两节——后者未就绪时输出披露行「#115 T3 外部锚定未执行」，κ/α 不得单独作为判官可用性结论
- **报告是仪表不是 gate**：命名与文档明确「观测面，不进生产读面」；生产代码禁读 `reports/`
- **G0.9 边界**：红测合成输入 inline/tmp_path 构造不入 `tests/fixtures/`（结构性豁免——构造结构输入不冒充真实技能产物）
- **域约束**：真实 LLM dispatch 付费且写状态——本 plan 全程零派发零 LLM；deps.json 等生成物禁手改
- **tools 纪律**：`tools/**` print 豁免（pyproject T201）；pathlib；E402 noqa 于 sys.path 修改后
- **T3 接线落点**：#103 spec 文本一行引用（本件自证段）；plan 前置检查单由 #103 plan 期承接（本件不代写他件 plan）；resonance SKILL 改动过 `just lint-contracts`（纯散文面零契约变更预期 diff 空）

**测试层级声明**：全部 T1 层（tests/unit/tools/ 单元测试；构造语料 tmp_path）。vol1 基线回放为本地验收运行（语料 gitignored 不入 CI），输出粘 progress.md `## 验收证据`。
**G3.4 声明**：不适用——本 spec 零 LLM 评分场景（纯确定性统计）。
**F947 声明**：天然合规——验收全离线可复验（构造语料测试+vol1 本地回放），无真实 dispatch 依赖。

---

### Task 1: `parse_resonance_trend` confidence 列扩展

**Files:**
- Modify: `tools/report_longitudinal.py:60-115`（ResonanceRow + parse_resonance_trend）
- Test: `tests/unit/test_report_longitudinal.py`（追加测试）

**Interfaces:**
- Consumes: `parse_resonance_trend(path: Path) -> dict[int, ResonanceRow]`（现有：列名绑定、pending 行跳过、重复章号 raise）
- Produces: `ResonanceRow(overall: float, excluded: bool, confidence: str = "")`——新字段带默认值，现有 6 个调用点（report_longitudinal :397/:842 + 3 个测试文件）属性访问不受影响；Task 4 读 `row.confidence`

**复杂度: leaf · test_kind: tdd_red_green**

- [ ] **Step 1: 写失败测试**（追加到 `tests/unit/test_report_longitudinal.py`；该文件用函数内 import 风格——沿用）

```python
def test_parse_resonance_trend_confidence_column(tmp_path) -> None:
    from tools.report_longitudinal import parse_resonance_trend

    trend = tmp_path / "truth" / "resonance_trend.md"
    trend.parent.mkdir()
    trend.write_text(
        "---\ntype: truth\n---\n\n# 共鸣趋势\n\n"
        "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        "| 1 | 推进 | 23 | 20 | 20 | 15 | 78 | mid |  |\n"
        "| 2 | 过渡 | 22 | 25 | 22 | 10 | 79 | high |  |\n"
        "| 3 | 推进 | - | - | - | - | pending | low |  |\n",
        encoding="utf-8",
    )
    rows = parse_resonance_trend(trend)
    assert sorted(rows) == [1, 2]  # pending 行跳过（现有语义）
    assert rows[1].confidence == "mid"
    assert rows[2].confidence == "high"


def test_resonance_row_confidence_default_backcompat(tmp_path) -> None:
    """旧构造（无 confidence）与缺列文件仍工作——向后兼容钉死。"""
    from tools.report_longitudinal import ResonanceRow

    r = ResonanceRow(overall=78.0, excluded=False)
    assert r.confidence == ""
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/unit/test_report_longitudinal.py -k confidence -v`
Expected: FAIL with `TypeError` / `AttributeError: 'ResonanceRow' object has no attribute 'confidence'`

- [ ] **Step 3: 最小实现**——`tools/report_longitudinal.py` 三处：

```python
# :60 附近 dataclass 加字段（默认值保旧构造）
@dataclass(frozen=True)
class ResonanceRow:
    """One parsed trend row: overall score + human-override exclusion flag."""

    overall: float
    excluded: bool
    confidence: str = ""
```

parse 循环内（`override_col = ...` 同段之后、构造 ResonanceRow 处）：

```python
        conf_col = col.get("confidence")
        confidence = cells[conf_col].strip() if conf_col is not None and conf_col < len(cells) else ""
```

构造行改 `ResonanceRow(overall=overall, excluded=excluded, confidence=confidence)`。

- [ ] **Step 4: 跑新旧测试**

Run: `uv run pytest tests/unit/test_report_longitudinal.py tests/unit/tools/test_spec83_longitudinal.py -v`
Expected: 全 PASS（新 2 + 既有全绿——向后兼容证明）

- [ ] **Step 5: Commit**

```bash
git add tools/report_longitudinal.py tests/unit/test_report_longitudinal.py
git commit -m "feat: spec #110 T1 前置——parse_resonance_trend 扩展 confidence 列（向后兼容默认值）"
```

---

### Task 2: 语料扫描层——卫生剔除+族分组+评级矩阵

**Files:**
- Create: `tools/judge_reliability.py`
- Test: `tests/unit/tools/test_judge_reliability.py`（新文件）

**Interfaces:**
- Consumes: `check_audit_starve_verdict(path: Path) -> list[str]`（非空=invalid）；`extract_finding_units(report_name: str, content: str) -> tuple[list[FindingUnit], list[str]]`，`FindingUnit(severity: str, text: str, reporters: tuple[str, ...])`
- Produces（Task 3/4 消费，签名钉死）:
  - `HARD_SEVERITIES: frozenset[str]` = `frozenset({"BLOCKING", "CRITICAL"})`
  - `SKILL_FAMILY: dict[str, str]`——craft/character 族映射（pov/dialogue/character/motivation → "group-character"；texture/reader-pull/anti-ai → "group-craft"）
  - `@dataclass(frozen=True) class AuditRecord: chapter: int; skill: str; binary: int; hard_count: int`
  - `@dataclass(frozen=True) class ScanResult: records: tuple[AuditRecord, ...]; invalid: tuple[str, ...]; file_total: int`
  - `scan_audits(audits_dir: Path) -> ScanResult`——遍历 `chapter-<N>-<skill>.md`（排除 `review-summary`/`.aggregate`），invalid 剔除（调 `check_audit_starve_verdict`），valid 记 binary/hard_count（`extract_finding_units` 后按 HARD_SEVERITIES 聚合计数）

**复杂度: leaf · test_kind: tdd_red_green**

- [ ] **Step 1: 写失败测试**（新文件 `tests/unit/tools/test_judge_reliability.py`；构造语料 tmp_path——G0.9 结构性豁免）

```python
"""Unit tests for tools/judge_reliability.py (spec #110). Constructed
structural corpora under tmp_path — G0.9 structural-input exemption."""

from __future__ import annotations

from pathlib import Path


def _write(dir_: Path, name: str, body: str) -> None:
    p = dir_ / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


HARD_LINE = "- [BLOCKING] 时序矛盾：ch3 与 ch5 对同一事件的日期记述冲突\n"
MINOR_LINE = "- [MINOR] 用词重复\n"
STARVE_BODY = "**判定**：无法验证（输入缺失）\n"


def test_scan_audits_ratings_and_hygiene(tmp_path) -> None:
    from tools.judge_reliability import scan_audits

    audits = tmp_path / "audits"
    _write(audits, "chapter-1-texture.md", f"**判定**：有瑕疵\n{HARD_LINE}{MINOR_LINE}")
    _write(audits, "chapter-1-sensitivity.md", "**判定**：通过\n（零发现）")
    _write(audits, "chapter-2-texture.md", STARVE_BODY)  # 饿死形态→invalid
    _write(audits, "chapter-1-review-summary.md", "汇总（不参与）")
    res = scan_audits(audits)
    assert res.file_total == 3  # summary 排除
    from tools.judge_reliability import AuditRecord

    assert [r for r in res.records if r.skill == "texture" and r.chapter == 1] == [
        AuditRecord(chapter=1, skill="texture", binary=1, hard_count=1)
    ]
    by = {(r.chapter, r.skill): r for r in res.records}
    assert by[(1, "sensitivity")].binary == 0 and by[(1, "sensitivity")].hard_count == 0
    assert (2, "texture") not in by  # invalid 剔除
    assert len(res.invalid) == 1 and "chapter-2-texture.md" in res.invalid[0]
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.judge_reliability'`

- [ ] **Step 3: 实现扫描层**——`tools/judge_reliability.py`：

```python
"""Judge inter-rater reliability harness (spec #110) — offline, deterministic, zero LLM.

Observation-plane instrument, NOT a gate: nothing in src/shenbi/ may read
its reports (repo discipline, #108 T3 precedent). Replay semantics are
pinned HERE in executable form; spec prose is a gloss.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from shenbi.pipeline.audit_aggregate import extract_finding_units  # noqa: E402
from shenbi.pipeline.llm_output_integrity import check_audit_starve_verdict  # noqa: E402

HARD_SEVERITIES = frozenset({"BLOCKING", "CRITICAL"})
# 单源派发族（SKILL writes 声明的单次派发产物——同族两两 κ 为伪影）
SKILL_FAMILY: dict[str, str] = {
    "pov": "group-character",
    "dialogue": "group-character",
    "character": "group-character",
    "motivation": "group-character",
    "texture": "group-craft",
    "reader-pull": "group-craft",
    "anti-ai": "group-craft",
}
_AUDIT_FORM = re.compile(r"chapter-(\d+)-([\w-]+)\.md$")


@dataclass(frozen=True)
class AuditRecord:
    chapter: int
    skill: str
    binary: int
    hard_count: int


@dataclass(frozen=True)
class ScanResult:
    records: tuple[AuditRecord, ...]
    invalid: tuple[str, ...]
    file_total: int


def scan_audits(audits_dir: Path) -> ScanResult:
    records: list[AuditRecord] = []
    invalid: list[str] = []
    file_total = 0
    for path in sorted(audits_dir.glob("chapter-*.md")):
        m = _AUDIT_FORM.match(path.name)
        if not m or m.group(2) == "review-summary" or m.group(2).endswith(".aggregate"):
            continue
        file_total += 1
        issues = check_audit_starve_verdict(path)  # #109 T4 单源判定
        if issues:
            invalid.extend(issues)
            continue
        units, _ = extract_finding_units(path.name, path.read_text(encoding="utf-8"))
        hard = sum(1 for u in units if u.severity in HARD_SEVERITIES)
        records.append(AuditRecord(int(m.group(1)), m.group(2), 1 if hard else 0, hard))
    return ScanResult(tuple(records), tuple(invalid), file_total)
```

- [ ] **Step 4: 跑测通过**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/judge_reliability.py tests/unit/tools/test_judge_reliability.py
git commit -m "feat: spec #110 T1——judge_reliability 语料扫描层（#109 T4 卫生单源+族映射+二值/计数评级）"
```

---

### Task 3: 统计核心——κ/α/效度相关/形状纯函数

**Files:**
- Modify: `tools/judge_reliability.py`（追加统计函数）
- Test: `tests/unit/tools/test_judge_reliability.py`（追加）

**Interfaces:**
- Consumes: Task 2 的 `AuditRecord`/`ScanResult`/`SKILL_FAMILY`
- Produces（Task 4 消费）:
  - `cohen_kappa(a: Sequence[int], b: Sequence[int]) -> KappaResult`，`KappaResult(kappa: float | None, agreement: float, n: int, warning: str | None)`——同族对 warning=「同派发伪影」由调用侧（Task 4）注入；本函数在 p_e ≥ 0.999 或 n == 0 时 kappa=None + warning=「prevalence 退化——不输出误导值」
  - `cronbach_alpha(items: Sequence[Sequence[float]]) -> float | None`（rows=items，cols=subjects；σ²_total=0 → None）
  - `pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None`
  - `slope_regression(xs: Sequence[float], ys: Sequence[float]) -> SlopeResult(slope: float, r: float, t: float)`（OLS 一元；t = r·sqrt((n-2)/(1-r²))，n<3 → t=0.0 并由调用侧披露）
  - `shape_stats(overalls: Sequence[float], confidences: Sequence[str]) -> dict`（mode 频率表降序/sd 样本/极差/high 基率；len<8 附 `insufficient: True`）
  - `anchor_position_counts(audits_dir: Path) -> Counter`——resonance 文件 Route A 八列表按列名「相对位置」绑定计 相当/更差/更好

**复杂度: leaf · test_kind: tdd_red_green**

- [ ] **Step 1: 写失败测试**（追加；含 spec 红测三件：同分→α=1、独立→α≈0、prevalence 警示）

```python
def test_cohen_kappa_identical_raters() -> None:
    from tools.judge_reliability import cohen_kappa

    res = cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0])
    assert res.kappa == 1.0 and res.agreement == 1.0 and res.n == 4 and res.warning is None


def test_cohen_kappa_prevalence_degenerate_warns() -> None:
    from tools.judge_reliability import cohen_kappa

    res = cohen_kappa([0, 0, 0, 0], [0, 0, 0, 0])  # 全零 flag 技能对
    assert res.kappa is None and res.warning is not None and "prevalence" in res.warning


def test_cronbach_alpha_identical_items_is_one() -> None:
    from tools.judge_reliability import cronbach_alpha

    assert cronbach_alpha([[1, 0, 1, 1], [1, 0, 1, 1], [1, 0, 1, 1]]) == 1.0


def test_cronbach_alpha_independent_items_near_zero() -> None:
    import random

    from tools.judge_reliability import cronbach_alpha

    rng = random.Random(110)
    items = [[float(rng.randint(0, 1)) for _ in range(400)] for _ in range(8)]
    assert abs(cronbach_alpha(items)) < 0.10  # 独立→α≈0


def test_pearson_and_slope(tmp_path) -> None:
    from tools.judge_reliability import pearson, slope_regression

    assert abs(pearson([1, 2, 3, 4], [2, 4, 6, 8]) - 1.0) < 1e-9
    sr = slope_regression([1.0, 2.0, 3.0, 4.0], [78.0, 78.7, 79.4, 80.1])
    assert abs(sr.slope - 0.7) < 1e-9 and abs(sr.r - 1.0) < 1e-9


def test_shape_stats_mode_sd_and_cold_start() -> None:
    from tools.judge_reliability import shape_stats

    st = shape_stats([79.0] * 12 + [78.0] * 3 + [86.0, 74.0], ["high"] * 15 + ["mid"] * 2)
    assert st["mode"] == (79.0, 12) and st["sd"] > 0 and st["range"] == (74.0, 86.0)
    assert st["high_rate"] == 15 / 17 and st.get("insufficient") is None
    cold = shape_stats([79.0, 78.0, 77.0], ["high", "mid", "low"])
    assert cold.get("insufficient") is True


def test_anchor_position_counts_binds_by_column(tmp_path) -> None:
    from tools.judge_reliability import anchor_position_counts

    audits = tmp_path / "audits"
    _write(
        audits,
        "chapter-1-resonance.md",
        "| 维度 | 得分 | 满分 | 置信度 | 对照锚点 | 相对位置 | 证据 | 裁判理由 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 情感落地 | 22 | 30 | high | AC-001 | 相当 | L45 | show 充分 |\n"
        "| 场景临场感 | 20 | 25 | mid | AC-004 | 更差 | L12 | 概述偏多 |\n",
    )
    c = anchor_position_counts(audits)
    assert c["相当"] == 1 and c["更差"] == 1 and c["更好"] == 0
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -v`
Expected: FAIL with `ImportError: cannot import name 'cohen_kappa'`

- [ ] **Step 3: 实现统计核心**（追加到 `tools/judge_reliability.py`；全部纯函数零 IO——anchor_position_counts 除外）

```python
from collections import Counter
from math import sqrt
from typing import Sequence


@dataclass(frozen=True)
class KappaResult:
    kappa: float | None
    agreement: float
    n: int
    warning: str | None


def cohen_kappa(a: Sequence[int], b: Sequence[int]) -> KappaResult:
    pairs = [(x, y) for x, y in zip(a, b, strict=True)]
    n = len(pairs)
    p_o = sum(1 for x, y in pairs if x == y) / n if n else 0.0
    ca = sum(1 for x, _ in pairs if x) / n if n else 0.0
    cb = sum(1 for _, y in pairs if y) / n if n else 0.0
    p_e = ca * cb + (1 - ca) * (1 - cb)
    if n == 0:
        return KappaResult(None, p_o, n, "零重叠章——不输出 κ")
    if p_e >= 0.999:
        return KappaResult(
            None, p_o, n, "prevalence 退化（边缘分布极端）——κ 不输出误导值，附原始 agreement"
        )
    return KappaResult((p_o - p_e) / (1 - p_e), p_o, n, None)


def cronbach_alpha(items: Sequence[Sequence[float]]) -> float | None:
    """Cronbach alpha — items are rows (k), subjects are columns (n)."""
    k = len(items)
    n = len(items[0]) if k else 0
    if k < 2 or n < 2 or any(len(row) != n for row in items):
        return None
    sigma_i = 0.0
    for row in items:
        mean = sum(row) / n
        sigma_i += sum((v - mean) ** 2 for v in row) / n
    totals = [sum(col) for col in zip(*items, strict=True)]
    tm = sum(totals) / n
    sigma_t = sum((t - tm) ** 2 for t in totals) / n
    if sigma_t == 0:
        return None
    return (k / (k - 1)) * (1 - sigma_i / sigma_t)
```

```python
def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sxy / sqrt(sxx * syy)


@dataclass(frozen=True)
class SlopeResult:
    slope: float
    r: float
    t: float


def slope_regression(xs: Sequence[float], ys: Sequence[float]) -> SlopeResult:
    r = pearson(xs, ys) or 0.0
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = (sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx) if sxx else 0.0
    t = r * sqrt((n - 2) / (1 - r * r)) if n > 2 and abs(r) < 1 else 0.0
    return SlopeResult(slope, r, t)


def shape_stats(overalls: Sequence[float], confidences: Sequence[str]) -> dict[str, object]:
    n = len(overalls)
    result: dict[str, object] = {"n": n}
    if n < 8:
        result["insufficient"] = True
        result["disclosure"] = f"样本不足（实评行 {n}<8）——分布形状节不输出指标，仅此披露行"
        return result
    counts = Counter(overalls)
    (mode_val, mode_n) = counts.most_common(1)[0]
    mean = sum(overalls) / n
    sd = sqrt(sum((v - mean) ** 2 for v in overalls) / (n - 1))  # 样本 sd
    high = sum(1 for c in confidences if c == "high")
    result.update(
        mode=(mode_val, mode_n),
        mode_table=counts.most_common(),
        sd=round(sd, 2),
        range=(min(overalls), max(overalls)),
        high_rate=high / n,
    )
    return result


_ROUTEA_HEADER = "| 维度 | 得分 | 满分 | 置信度 | 对照锚点 | 相对位置 | 证据 | 裁判理由 |"


def anchor_position_counts(audits_dir: Path) -> Counter:
    """Count Route-A anchor relative positions (相当/更差/更好), bound by
    header column name — resilient to column reordering."""
    counts: Counter = Counter()
    for path in sorted(audits_dir.glob("chapter-*-resonance.md")):
        idx: int | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if "相对位置" in cells:
                idx = cells.index("相对位置")
                continue
            if idx is not None and len(cells) > idx and cells[idx] in ("相当", "更差", "更好"):
                counts[cells[idx]] += 1
    return counts
```

- [ ] **Step 4: 跑测通过**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -v`
Expected: 全 PASS（Task 2 + Task 3 测试）

- [ ] **Step 5: Commit**

```bash
git add tools/judge_reliability.py tests/unit/tools/test_judge_reliability.py
git commit -m "feat: spec #110 T1——统计核心（κ+prevalence 警示/α/效度相关/形状+冷启动门/锚点相对位置计数）"
```

---

### Task 4: 报告组装+justfile recipe+vol1 基线回放

**Files:**
- Modify: `tools/judge_reliability.py`（build_report + main）
- Modify: `justfile`（judge-reliability recipe，加在 gate-power 配方后）
- Test: `tests/unit/tools/test_judge_reliability.py`（追加报告级测试）

**Interfaces:**
- Consumes: Task 1 `ResonanceRow.confidence`；Task 2 `scan_audits`/`SKILL_FAMILY`；Task 3 全部统计函数
- Produces:
  - `build_report(project_dir: Path) -> str`——纯内容确定性（同输入同输出字节）
  - `main(argv: Sequence[str] | None = None) -> int`——写 `reports/judge-reliability-<UTCts>.md`（时间戳只在文件名）；exit 0
  - justfile：`judge-reliability DIR *ARGS:` → `uv run python tools/judge_reliability.py "$1" "${@:2}"`

**复杂度: infra · test_kind: tdd_red_green（报告组装）+ characterization（vol1 回放带宽数字断言不入 CI——本地验收）**

报告节序（模板钉死）：①前置卫生行（file_total/invalid 剔除计数逐文件）②两两 κ 表（逐对 n/agreement/κ；同族对注记「同派发伪影——不作判官间一致性解读」；prevalence 退化行）③Cronbach α 四数（10 items×二值、10 items×计数、7 items×二值、7 items×计数——items 剔除 craft 成员=剔 texture/reader-pull/anti-ai）④效度相关（r(overall, 其余硬发现总量)+n+join 披露行；负对照 r(overall, 章长)）⑤分布形状（shape_stats+通胀 slope/r/t+锚点相对位置计数）⑥**外部锚定效度引用**（固定披露行「#115 T3 外部锚定未执行——κ/α 不得单独作为判官可用性结论」）⑦方法论注记（低 κ 的一半是分工；本报告是观测面不是 gate，不进生产读面）。

效度相关取数规则（钉死）：join = 既有 scored trend 行 ∧ 该章 ≥1 份 valid 非 resonance 审计；「其余 issue 总量」= 该章全部非 resonance valid 审计的 hard_count 之和；「章长」= `chapters/chapter-N.md` 去空白字符数（文件缺失→该章不入负对照）。

- [ ] **Step 1: 写失败测试**（报告级——构造迷你语料断言关键行存在+确定性）

```python
MINI_TREND = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
    + "".join(f"| {i} | 推进 | 20 | 20 | 20 | 15 | {75 + i} | high |  |\n" for i in range(1, 9))
)


def _mini_project(tmp_path: Path) -> Path:
    (tmp_path / "truth").mkdir()
    (tmp_path / "truth" / "resonance_trend.md").write_text(
        "---\ntype: truth\n---\n\n# 共鸣趋势\n\n" + MINI_TREND, encoding="utf-8"
    )
    audits = tmp_path / "audits"
    for ch in range(1, 9):
        _write(
            audits,
            f"chapter-{ch}-sensitivity.md",
            f"**判定**：有瑕疵\n{HARD_LINE}" if ch % 2 else "**判定**：通过\n",
        )
        _write(
            audits,
            f"chapter-{ch}-resonance.md",
            "**判定**：通过 (80/100)\n"
            "| 维度 | 得分 | 满分 | 置信度 | 对照锚点 | 相对位置 | 证据 | 裁判理由 |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| 情感落地 | 22 | 30 | high | AC-001 | 相当 | L1 | x |\n",
        )
        _write(
            audits, f"chapter-{ch}-world-rules.md", "**判定**：通过\n"
        )  # 全零对→prevalence 退化行
        _write(audits, f"chapter-{ch}-pacing.md", "**判定**：通过\n")
    (tmp_path / "chapters").mkdir()
    for ch in range(1, 9):
        (tmp_path / "chapters" / f"chapter-{ch}.md").write_text(
            "字" * (1000 * ch), encoding="utf-8"
        )
    return tmp_path


def test_build_report_sections_and_determinism(tmp_path) -> None:
    from tools.judge_reliability import build_report

    report = build_report(_mini_project(tmp_path))
    for needle in (
        "前置数据卫生",
        "同派发伪影",
        "Cronbach α",
        "效度相关",
        "外部锚定未执行",
        "观测面",
        "prevalence",
    ):
        assert needle in report, f"报告缺节：{needle}"
    assert build_report(_mini_project(tmp_path)) == report  # 同输入同输出


def test_group_pair_not_degrouped_emits_artifact_warning(tmp_path) -> None:
    """④(c) 红测：同族对（pov×dialogue）必须带伪影注记。"""
    from tools.judge_reliability import build_report

    proj = _mini_project(tmp_path)
    for ch in range(1, 9):
        _write(proj / "audits", f"chapter-{ch}-pov.md", "**判定**：通过\n")
        _write(proj / "audits", f"chapter-{ch}-dialogue.md", "**判定**：通过\n")
    report = build_report(proj)
    assert "dialogue × pov" in report and "同派发伪影" in report  # 表行按字母序 s1<s2
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -k build_report -v`
Expected: FAIL with `ImportError: cannot import name 'build_report'`

- [ ] **Step 3: 实现 build_report + main + recipe**

```python
_ALPHA_EXCLUDED = frozenset(SKILL_FAMILY) - {
    "texture",
    "reader-pull",
    "anti-ai",
}  # group-character 成员不入 α items
_CRAFT_TRIO = ("texture", "reader-pull", "anti-ai")


def _alpha_versions(scan: ScanResult) -> list[tuple[str, str, int, float | None]]:
    """α 四数：item 集两版（全 always-on / 剔 craft 三员）× 评级两版（二值/计数）。

    subjects = listwise 完整章（该 item 集每一技能都有 valid 记录的章交集）。"""
    by: dict[tuple[int, str], AuditRecord] = {(r.chapter, r.skill): r for r in scan.records}
    skills = sorted({r.skill for r in scan.records})
    item_sets = [
        ("always-on 全 items", [s for s in skills if s not in _ALPHA_EXCLUDED]),
        (
            "剔 craft 族 7 items",
            [s for s in skills if s not in _ALPHA_EXCLUDED and s not in _CRAFT_TRIO],
        ),
    ]
    out: list[tuple[str, str, int, float | None]] = []
    for set_name, items in item_sets:
        if len(items) < 2:
            out.append((set_name, "二值", 0, None))
            out.append((set_name, "计数", 0, None))
            continue
        chapters = sorted(
            set.intersection(
                *(  # listwise：全 item 覆盖章交集
                    {c for c, sk in by if sk == s} for s in items
                )
            )
        )
        bin_items = [[float(by[(c, s)].binary) for c in chapters] for s in items]
        cnt_items = [[float(by[(c, s)].hard_count) for c in chapters] for s in items]
        out.append((set_name, "二值", len(chapters), cronbach_alpha(bin_items)))
        out.append((set_name, "计数", len(chapters), cronbach_alpha(cnt_items)))
    return out


def _validity(project_dir: Path, scan: ScanResult, rows: dict[int, ResonanceRow]) -> list[str]:
    """④ 效度相关：join = scored trend 行 ∧ 该章 ≥1 valid 非 resonance 审计。"""
    hard_sum: dict[int, int] = {}
    for r in scan.records:
        if r.skill != "resonance":
            hard_sum[r.chapter] = hard_sum.get(r.chapter, 0) + r.hard_count
    joined = sorted(set(rows) & set(hard_sum))
    r_val = pearson([float(rows[c].overall) for c in joined], [float(hard_sum[c]) for c in joined])
    lens: list[float] = []
    overs: list[float] = []
    for c in joined:
        text_file = project_dir / "chapters" / f"chapter-{c}.md"
        if text_file.exists():
            lens.append(float(len("".join(text_file.read_text(encoding="utf-8").split()))))
            overs.append(float(rows[c].overall))
    r_len = pearson(overs, lens) if lens else None
    return [
        f"- resonance overall × 其余审计硬发现总量：r = {('%.3f' % r_val) if r_val is not None else '—'}（n = {len(joined)}）",
        f"- join 规则：scored trend 行 ∧ 该章 ≥1 valid 非 resonance 审计（缺行不入，n 如上披露）",
        f"- 长度偏差负对照：overall × 章长（去空白字符数）r = {('%.3f' % r_len) if r_len is not None else '—'}（n = {len(lens)}）",
    ]


def build_report(project_dir: Path) -> str:
    from tools.report_longitudinal import TREND_FILENAME, parse_resonance_trend

    audits_dir = project_dir / "audits"
    scan = scan_audits(audits_dir)
    rows = parse_resonance_trend(project_dir / "truth" / TREND_FILENAME)
    scored = {c: r for c, r in rows.items()}
    lines: list[str] = ["# Judge Reliability Report（观测面——非 gate，不进生产读面）", ""]
    # ① 前置卫生
    lines += [
        "## 前置数据卫生（#109 T4 invalid 剔除）",
        "",
        f"- 语料文件总数：{scan.file_total}；invalid 剔除：{len(scan.invalid)}",
    ]
    lines += [f"  - {msg}" for msg in scan.invalid] or ["  - （零 invalid）"]
    # ② 两两 κ（同章成对完整例；评级=有无硬发现二值 + 计数版 hard-count 相关列）
    skills = sorted({r.skill for r in scan.records})
    by: dict[tuple[int, str], AuditRecord] = {(r.chapter, r.skill): r for r in scan.records}
    lines += [
        "",
        "## 跨技能两两 Cohen κ（评级=有无硬发现；成对完整例）",
        "",
        "| 技能对 | n | agreement | κ（二值） | 计数版 r（hard-count） | 注记 |",
        "|---|---|---|---|---|---|",
    ]
    for i, s1 in enumerate(skills):
        for s2 in skills[i + 1 :]:
            common = sorted({c for c, sk in by if sk == s1} & {c for c, sk in by if sk == s2})
            res = cohen_kappa(
                [by[(c, s1)].binary for c in common], [by[(c, s2)].binary for c in common]
            )
            r_cnt = pearson(
                [float(by[(c, s1)].hard_count) for c in common],
                [float(by[(c, s2)].hard_count) for c in common],
            )
            fam1, fam2 = SKILL_FAMILY.get(s1), SKILL_FAMILY.get(s2)
            note = (
                "同派发伪影——不作判官间一致性解读" if fam1 and fam1 == fam2 else (res.warning or "")
            )
            kappa_txt = "—" if res.kappa is None else f"{res.kappa:+.3f}"
            r_txt = "—" if r_cnt is None else f"{r_cnt:+.3f}"
            lines.append(
                f"| {s1} × {s2} | {res.n} | {res.agreement:.3f} | {kappa_txt} | {r_txt} | {note} |"
            )
    # ③ Cronbach α 四数
    lines += ["", "## Cronbach α（always-on 审计族 items × listwise 完整章 subjects）", ""]
    for set_name, ver, n, alpha in _alpha_versions(scan):
        a_txt = "—" if alpha is None else f"{alpha:.3f}"
        lines.append(f"- {set_name} × {ver}：α = {a_txt}（n = {n}）")
    # ④ 效度相关
    lines += ["", "## 效度相关"] + _validity(project_dir, scan, scored)
    # ⑤ 分布形状
    overs = [float(r.overall) for r in scored.values()]
    confs = [r.confidence for r in scored.values()]
    st = shape_stats(overs, confs)
    lines += ["", "## 分布形状", f"- 实评行：{st['n']}"]
    if st.get("insufficient"):
        lines.append(f"- ⚠️ {st['disclosure']}")
    else:
        mode_val, mode_n = st["mode"]  # type: ignore[misc]
        lines += [
            f"- 模值：{mode_val:g} × {mode_n}/{st['n']}；频率表（降序）："
            + "、".join(f"{v:g}×{c}" for v, c in st["mode_table"]),  # type: ignore[misc]
            f"- sd（样本）：{st['sd']}；极差：{st['range'][0]:g}-{st['range'][1]:g}",  # type: ignore[index]
            f"- confidence=high 基率：{st['high_rate']:.3f}",  # type: ignore[index]
        ]
        if len(overs) >= 3:
            sr = slope_regression([float(c) for c in scored], overs)
            lines.append(f"- 通胀 slope：{sr.slope:+.4f} 分/章（r = {sr.r:+.3f}，t = {sr.t:+.2f}）")
    pos = anchor_position_counts(audits_dir)
    lines += [
        f"- 锚点相对位置计数：相当 {pos.get('相当', 0)} / 更差 {pos.get('更差', 0)} / 更好 {pos.get('更好', 0)}"
    ]
    # ⑥ 外部锚定效度引用（#115 T4 对齐——未就绪披露）
    lines += [
        "",
        "## 外部锚定效度引用（#115 T4 对齐）",
        "- 披露：#115 T3 外部锚定未执行——本报告的 κ/α 为判官间信度，"
        "不得单独作为判官可用性结论（判官可用性须外部 criterion validity 一并裁定）",
    ]
    # ⑦ 方法论注记
    lines += [
        "",
        "## 方法论注记",
        "- 低 κ 的一半是分工：各审计技能测不同构念属设计，κ/α 低未必是判官病",
        "- 本报告是观测面不是 gate：生产代码禁读 reports/（#108 T3 同款纪律）",
    ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Judge inter-rater reliability report (spec #110)")
    parser.add_argument("project_dir", type=Path)
    args = parser.parse_args(argv)
    report = build_report(args.project_dir)
    out_dir = args.project_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%SZ", time.gmtime())
    out = out_dir / f"judge-reliability-{ts}.md"
    out.write_text(report, encoding="utf-8")
    print(out)
    return 0
```

（文件顶部 import 补 `import time` 与 `from tools.report_longitudinal import TREND_FILENAME, parse_resonance_trend` 的函数内 import 形态按 Task 1 先例；`ResonanceRow` 类型注解 import 同源。）justfile 追加：

```
# Judge reliability offline report (spec #110) — observation plane, not a gate
judge-reliability DIR *ARGS:
    uv run python tools/judge_reliability.py "$1" "${@:2}"
```

- [ ] **Step 4: 跑测通过+全量门禁**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -v && just check`
Expected: 全 PASS（含既有套件零回归）

- [ ] **Step 5: vol1 基线回放（本地验收，不入 CI）**

Run: `just judge-reliability novel-xinghuo-vol1`
Expected: 报告落 `novel-xinghuo-vol1/reports/judge-reliability-<ts>.md`；人工核对关键数字带：α∈[0.26,0.36]、效度 r∈[0.02,0.12]、更好=0、模值 79×12、high 24/32——输出与核对结论粘 progress.md `## 验收证据`（带外即记 deviation 调查口径差，不静默放过）

- [ ] **Step 6: Commit**

```bash
git add tools/judge_reliability.py justfile tests/unit/tools/test_judge_reliability.py
git commit -m "feat: spec #110 T1——报告组装（七节模板+双报义务+伪影/退化注记）+just recipe+vol1 基线回放验收"
```

---

### Task 5: T2 接线——#107 spec 加 McNemar 引用行

**Files:**
- Modify: `docs/superpowers/specs/2026-11-15-spec107-reviewer-model-tier.md:34`（T2 判据行后加一行）
- Test: `tests/unit/tools/test_judge_reliability.py`（追加 grep 断言）

**Interfaces:**
- Consumes: spec #110 r2.1 T2 义务文本
- Produces: #107 spec 文本含 #110 引用行（grep 可证——AC 自证段）

**复杂度: leaf · test_kind: characterization（grep 级断言）**

- [ ] **Step 1: 写失败测试**

```python
def test_spec107_references_110_mcnemar() -> None:
    from pathlib import Path

    spec107 = (
        Path(__file__).resolve().parents[3]
        / "docs/superpowers/specs/2026-11-15-spec107-reviewer-model-tier.md"
    )
    text = spec107.read_text(encoding="utf-8")
    assert "#110" in text and "McNemar" in text, "#107 T2 须含 #110 McNemar 配对设计引用行"
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -k spec107 -v`
Expected: FAIL with AssertionError

- [ ] **Step 3: 加引用行**（#107 T2 判据行 `**判据**：预注册文档落盘…` 之前，作为 T2 末 bullet 追加）：

```markdown
  - **判据设计（spec #110 T2 接线）**：A/B 判据须为 **McNemar 配对设计**（同变异两臂同测）+ 功效核算表入预注册文档（27/臂起步 power 0.56-0.60、45-63/臂达 0.8+；15pp 效应明示不可检）——核算口径引用 spec #110（judge-reliability-harness）；
```

- [ ] **Step 4: 跑测通过**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -k spec107 -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-11-15-spec107-reviewer-model-tier.md tests/unit/tools/test_judge_reliability.py
git commit -m "docs: spec #110 T2——#107 A/B 判据接 McNemar 配对+功效核算引用行"
```

---

### Task 6: T3 接线——#103 spec 裁定路径行 + resonance SKILL 校准口径

**Files:**
- Modify: `docs/superpowers/specs/2026-11-15-spec103-highlight-distill.md:24`（T1 选章判据行后）
- Modify: `skills/shenbi-review-resonance/SKILL.md:120-125`（置信度守护节内加一行）
- Test: `tests/unit/tools/test_judge_reliability.py`（追加 grep 断言）

**Interfaces:**
- Consumes: spec #110 r2.1 T3 双闸语义（基率 >50% 或 ρ<0.3 → confidence 降参考列）
- Produces: #103 spec 引用行（AC 自证段）；SKILL 校准口径行；`just lint-contracts` 预期 diff 空

**复杂度: leaf · test_kind: characterization（grep 级断言）**

- [ ] **Step 1: 写失败测试**

```python
def test_spec103_references_110_confidence_gate() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    spec103 = root / "docs/superpowers/specs/2026-11-15-spec103-highlight-distill.md"
    assert "#110" in spec103.read_text(encoding="utf-8"), (
        "#103 T1 须含 #110 confidence 双闸裁定路径引用行"
    )
    skill = root / "skills/shenbi-review-resonance/SKILL.md"
    assert "锚点集内可比证据行" in skill.read_text(encoding="utf-8"), (
        "resonance SKILL 须含校准口径行"
    )
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -k spec103 -v`
Expected: FAIL with AssertionError

- [ ] **Step 3: 两处文本**——

#103 spec T1 选章判据行（`…overall ≥ 全书 running median + 5`（**相对阈值抗通胀**））后追加一句：

```markdown
（**confidence 前置校准——spec #110 T3 接线**：judge-reliability 报告 confidence=high 基率 >50%，或 #115 T3 外部锚 ρ<0.3 回退成立，两闸任一触发 → confidence 从合取判据降为参考列，相对阈值单独承担；#103 plan 前置检查单须含此条）
```

resonance SKILL「## 置信度守护（框架自动，spec #33 T1b）」节首段后加一行：

```markdown
> **校准口径（spec #110 T3）**：自报 `high` 必须附「本锚点集内可比证据行」——至少一条与 AC-NNN 锚点段对照的具体依据（维度/方向/差距），裸 `high` 不可信；框架侧基率与外部锚校准见 `just judge-reliability` 报告。
```

- [ ] **Step 4: 跑测通过 + lint-contracts**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -k spec103 -v && just lint-contracts && just generate`
Expected: PASS；lint-contracts 绿；`just generate` 生成物 diff 空（纯散文面零契约变更——#119 T2 同款预期）

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-11-15-spec103-highlight-distill.md skills/shenbi-review-resonance/SKILL.md tests/unit/tools/test_judge_reliability.py
git commit -m "docs: spec #110 T3——#103 confidence 双闸裁定路径行+resonance SKILL 校准口径（lint-contracts 预期 diff 空）"
```

---

## AC 覆盖表

| spec AC | task | 验证 |
|---|---|---|
| T1 判据：vol1 回放关键数字一致（α≈0.31/r≈0.07/更好=0/模值 79×12） | Task 4 Step 5 | 本地回放+带宽数字核对粘 progress.md |
| T1 判据：红测（同分→α=1/独立→α≈0/prevalence 警示/饿死剔除/group 反例/冷启动） | Task 2/3/4 测试 | pytest 全绿 |
| T2 判据：#107 引用行 grep 可证 | Task 5 | test_spec107_references_110_mcnemar |
| T2 判据：报告含外部锚定效度引用节+未就绪披露 | Task 4 | test_build_report_sections（「外部锚定未执行」needle） |
| T3 判据：#103 spec 引用行（自证段）+SKILL 校准口径行 | Task 6 | test_spec103_references_110_confidence_gate |
| 验收 2：报告落盘数字可重放（同输入同输出） | Task 4 | test_build_report_sections_and_determinism |
| 验收 3：bug-hunt 四件（饿死剔除/prevalence 陷阱/group 反例/冷启动） | Task 2/3/4 | 对应四测试 |
| T3 承接段（#103 plan 检查单） | 不在本件生命周期 | deviations 移交 #103 plan 审查核验 |
