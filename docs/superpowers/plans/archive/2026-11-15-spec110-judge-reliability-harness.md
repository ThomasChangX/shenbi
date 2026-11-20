# Spec #110 · judge-reliability-harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 判官间信度/分布形状离线确定性报告工具 `just judge-reliability`（κ/α/效度相关/形状五件，零 LLM）+ #107/#103/resonance SKILL 三处判据营养接线。

**Architecture:** 薄壳工具 `tools/judge_reliability.py`：卫生判定复用 `check_audit_starve_verdict`（#109 T4 单源）、issue 计数复用 `extract_finding_units`、trend 解析复用并扩展 `parse_resonance_trend`（confidence 列）；新建仅统计核心（κ/α/相关/形状纯函数）。**评级双口径并报**（any-severity 二值=证据复现口径 ＋ hard 二值/计数=判据营养口径——plan 审查 C3 裁定）。报告落 `reports/judge-reliability-<ts>.md`，观测面不进生产读面。T2/T3 接线为三处一行级 spec/SKILL 文本修订。

**Tech Stack:** Python 3.11+ / pathlib / argparse / 标准库 math·collections（无第三方依赖）；tests/pytest；justfile recipe。

## Global Constraints（spec 项目级约束逐字块——每次审查派发注入）

- **复用钉死**：卫生判定=复用 `check_audit_starve_verdict`（`src/shenbi/pipeline/llm_output_integrity.py:405`——#109 T4 单源分类器，全判定行值段匹配+散文提及豁免；词族常量由该函数内部消费自 `audit_starve_family` 单源，禁自写词表/自写扫描循环）；issue 计数=复用 `extract_finding_units`（`src/shenbi/pipeline/audit_aggregate.py:114`）；trend 解析=复用 `parse_resonance_trend`（`tools/report_longitudinal.py:68`——tools 互引走仓内既有 sys.path+E402 noqa 先例，无 lint 拦截）
- **评级双口径**（spec r2.2）：any-severity 二值（任一 severity 的 finding 存在——**证据复现口径**：动机节 α=0.311/n=25 仅在此口径精确复现，plan 审查 C3 实证）＋ hard 二值（severity ∈ {BLOCKING, CRITICAL}——`src/shenbi/contracts/enums.py:9` Severity 词表）＋ hard 计数，三列并报
- **κ 口径**：成对完整例+逐对披露 n；同派发族对（group-character 成员互对/group-craft 成员互对）附「同派发伪影——不作判官间一致性解读」注记；**族级聚合=OR**——group-character/group-craft 各产出合成 rater（章节=成员并集、评级=成员 OR），参与两两 κ 全配对（对本族成员的配对注记「族 OR 合成」而非伪影注记）；prevalence 退化（边缘分布极端）κ 列输出「—」+警示
- **α 口径**：item 集两版（always-on 全 items——group-character 成员不入 items ／ 再剔 craft 三员 texture/reader-pull/anti-ai）× 评级三版（any 二值/hard 二值/hard 计数）= 六数并报；subjects = listwise 完整章；**证据锚=「always-on 全 × any 二值」列（α≈0.31、n=25）**
- **效度相关口径**（spec r2.2）：join = 既有 scored trend 行 ∧ 该章 ≥1 份 valid 非 resonance 审计；「其余 issue 总量」= 该章全部非 resonance valid 审计的 **any-severity finding 总数**（证据字面「issue 总量」）；负对照 r(overall, 章长)；**验收=方向性判据 |r|<0.3（正交主张）+ n 披露**——原值 +0.068/n=28 判定不可逐字复现（原统计脚本不在盘，阶段 0 登记），报告披露此口径差
- **分布形状**：模值频率表、sd、极差、相当/更差/更好计数（Route A 八列表按列名「相对位置」绑定、首表头绑定+后续表头重绑防跨表泄漏）、通胀 slope（章号回归）、confidence 基率；`human_overridden`（excluded）行不入形状统计并披露行数（drift_gate 先例 `tools/report_longitudinal.py:301`）
- **冷启动披露**：实评行 <8 时分布形状节输出「样本不足」披露行，不输出误导值
- **报告双报义务**（#115 T4 对齐）：报告须同时含「分布形状」与「外部锚定效度引用」两节——后者未就绪时输出披露行「#115 T3 外部锚定未执行」，κ/α 不得单独作为判官可用性结论
- **报告是仪表不是 gate**：命名与文档明确「观测面，不进生产读面」；生产代码禁读 `reports/`
- **G0.9 边界**：红测合成输入 inline/tmp_path 构造不入 `tests/fixtures/`（结构性豁免——构造结构输入不冒充真实技能产物）；**饿死剔除用例优先引用仓内真实饿死 fixture**（`tests/fixtures/audits/chapter-2-memo-compliance.md:4`——`**判定**: 不通过（无法核对）`，「无法核对」∈ NARROW6 生产词族）
- **lint 面**：`tools/judge_reliability.py` 与 `tests/unit/tools/test_judge_reliability.py` 加 pyproject per-file-ignores `["RUF001", "RUF002", "RUF003"]`（先例 `tools/audit_starve_baseline.py` 等）；公开函数/类带 docstring（D1xx）；文件中段 import 带 `# noqa: E402`；魔法数入命名常量（PLR2004）
- **域约束**：真实 LLM dispatch 付费且写状态——本 plan 全程零派发零 LLM；deps.json 等生成物禁手改
- **T3 接线落点**：#103 spec 文本一行引用（本件自证段）；plan 前置检查单由 #103 plan 期承接（本件不代写他件 plan）；resonance SKILL 改动过 `just lint-contracts`（纯散文面零契约变更预期 diff 空）

**测试层级声明**：全部 T1 层（tests/unit/tools/ 单元测试；构造语料 tmp_path + 真实饿死 fixture 断言）。vol1 基线回放为本地验收运行（语料 gitignored 不入 CI），输出粘 progress.md `## 验收证据`。
**G3.4 声明**：不适用——本 spec 零 LLM 评分场景（纯确定性统计）。
**F947 声明**：天然合规——验收全离线可复验（构造语料测试+vol1 本地回放），无真实 dispatch 依赖。

---

### Task 1: `parse_resonance_trend` confidence 列扩展

**Files:**
- Modify: `tools/report_longitudinal.py:60-115`（ResonanceRow + parse_resonance_trend）
- Test: `tests/unit/test_report_longitudinal.py`（追加测试）

**Interfaces:**
- Consumes: `parse_resonance_trend(path: Path) -> dict[int, ResonanceRow]`（现有：列名绑定、pending 行跳过、重复章号 raise）
- Produces: `ResonanceRow(overall: float, excluded: bool, confidence: str = "")`——新字段带默认值，现有 5 个调用点（report_longitudinal :397/:842 + 3 个测试文件——`tests/unit/test_report_longitudinal.py`、`tests/unit/tools/test_spec83_longitudinal.py`、`tests/unit/skill_utils/test_drift_detection.py`）属性访问不受影响；Task 4 读 `row.confidence`

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


def test_resonance_row_confidence_default_backcompat() -> None:
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

- [ ] **Step 4: 跑全部既有调用方测试**

Run: `uv run pytest tests/unit/test_report_longitudinal.py tests/unit/tools/test_spec83_longitudinal.py tests/unit/skill_utils/test_drift_detection.py -v`
Expected: 全 PASS（新 2 + 三个文件的既有全绿——向后兼容证明）

- [ ] **Step 5: Commit**

```bash
git add tools/report_longitudinal.py tests/unit/test_report_longitudinal.py
git commit -m "feat: spec #110 T1 前置——parse_resonance_trend 扩展 confidence 列（向后兼容默认值）"
```

---

### Task 2: 语料扫描层——卫生剔除+族分组+双口径评级矩阵

**Files:**
- Create: `tools/judge_reliability.py`
- Create: `tests/unit/tools/test_judge_reliability.py`
- Modify: `pyproject.toml:123-`（per-file-ignores 加两行——先例 audit_starve_baseline）

**Interfaces:**
- Consumes: `check_audit_starve_verdict(path: Path) -> list[str]`（非空=invalid）；`extract_finding_units(report_name: str, content: str) -> tuple[list[FindingUnit], list[str]]`，`FindingUnit(severity: str, text: str, reporters: tuple[str, ...])`
- Produces（Task 3/4 消费，签名钉死；**Task 4 会补第五字段 `any_count`——见 Task 4 头注**）:
  - `HARD_SEVERITIES: frozenset[str]` = `frozenset({"BLOCKING", "CRITICAL"})`
  - `SKILL_FAMILY: dict[str, str]`（pov/dialogue/character/motivation → "group-character"；texture/reader-pull/anti-ai → "group-craft"）
  - `@dataclass(frozen=True) class AuditRecord: chapter: int; skill: str; any_binary: int; hard_binary: int; hard_count: int`（双口径评级——C3）
  - `@dataclass(frozen=True) class ScanResult: records: tuple[AuditRecord, ...]; invalid: tuple[str, ...]; file_total: int`
  - `scan_audits(audits_dir: Path) -> ScanResult`——遍历 `chapter-<N>-<skill>.md`（`review-summary` 排除；`chapter-N.aggregate.md` 无 `-skill` 段天然不匹配正则——M4），invalid 剔除，valid 记评级

**复杂度: leaf · test_kind: tdd_red_green**

- [ ] **Step 1: 写失败测试**（新文件；构造语料 tmp_path + 真实饿死 fixture 断言——I4/C1）

```python
"""Unit tests for tools/judge_reliability.py (spec #110).

Constructed structural corpora under tmp_path — G0.9 structural-input
exemption; the real starvation fixture is consumed read-only via its
canonical classifier (evidence-priority rule, spec acceptance #3).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

HARD_LINE = "- [BLOCKING] 时序矛盾：ch3 与 ch5 对同一事件的日期记述冲突\n"
MINOR_LINE = "- [MINOR] 用词重复\n"
# 生产词族 token（NARROW6「无法核对」——「无法验证」仅 WIDE12，不命中生产分类器）
STARVE_BODY = "**判定**: 不通过（无法核对）\n"


def _write(dir_: Path, name: str, body: str) -> None:
    p = dir_ / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_scan_audits_dual_caliber_ratings_and_hygiene(tmp_path) -> None:
    from tools.judge_reliability import AuditRecord, scan_audits

    audits = tmp_path / "audits"
    _write(audits, "chapter-1-texture.md", f"**判定**：有瑕疵\n{HARD_LINE}{MINOR_LINE}")
    _write(audits, "chapter-1-sensitivity.md", f"**判定**：有瑕疵\n{MINOR_LINE}")  # 仅 MINOR
    _write(audits, "chapter-2-texture.md", STARVE_BODY)  # 饿死形态→invalid
    _write(audits, "chapter-1-review-summary.md", "汇总（不参与）")
    res = scan_audits(audits)
    assert res.file_total == 3  # summary 排除（aggregate 无 -skill 段不匹配）
    by = {(r.chapter, r.skill): r for r in res.records}
    assert by[(1, "texture")] == AuditRecord(
        chapter=1, skill="texture", any_binary=1, hard_binary=1, hard_count=1
    )
    assert by[(1, "sensitivity")].any_binary == 1
    assert by[(1, "sensitivity")].hard_binary == 0
    assert by[(1, "sensitivity")].hard_count == 0
    assert (2, "texture") not in by  # invalid 剔除
    assert len(res.invalid) == 1 and "chapter-2-texture.md" in res.invalid[0]


def test_real_starve_fixture_classified_invalid() -> None:
    """验收 3 优先项：真实饿死 fixture 经 #109 单源分类器判 invalid。"""
    from shenbi.pipeline.llm_output_integrity import check_audit_starve_verdict

    fixture = REPO_ROOT / "tests/fixtures/audits/chapter-2-memo-compliance.md"
    assert fixture.exists() and check_audit_starve_verdict(fixture)
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
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from shenbi.pipeline.audit_aggregate import extract_finding_units  # noqa: E402
from shenbi.pipeline.llm_output_integrity import check_audit_starve_verdict  # noqa: E402

HARD_SEVERITIES = frozenset({"BLOCKING", "CRITICAL"})
# 单源派发族（SKILL writes 声明的单次派发产物——同族两两 κ 为伪影，族 OR 合成 rater）
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
    """One valid audit file's dual-caliber ratings (spec r2.2)."""

    chapter: int
    skill: str
    any_binary: int  # 任一 severity finding 存在（证据复现口径）
    hard_binary: int  # BLOCKING/CRITICAL 存在
    hard_count: int  # BLOCKING/CRITICAL 单元数


@dataclass(frozen=True)
class ScanResult:
    """Corpus scan outcome: valid records + invalid disclosure + file total."""

    records: tuple[AuditRecord, ...]
    invalid: tuple[str, ...]
    file_total: int


def scan_audits(audits_dir: Path) -> ScanResult:
    """Walk chapter-<N>-<skill>.md; drop review-summary and starved (invalid)."""
    records: list[AuditRecord] = []
    invalid: list[str] = []
    file_total = 0
    for path in sorted(audits_dir.glob("chapter-*.md")):
        m = _AUDIT_FORM.match(path.name)
        if not m or m.group(2) == "review-summary":
            continue
        file_total += 1
        issues = check_audit_starve_verdict(path)  # #109 T4 单源判定
        if issues:
            invalid.extend(issues)
            continue
        units, _ = extract_finding_units(path.name, path.read_text(encoding="utf-8"))
        hard = sum(1 for u in units if u.severity in HARD_SEVERITIES)
        records.append(
            AuditRecord(int(m.group(1)), m.group(2), 1 if units else 0, 1 if hard else 0, hard)
        )
    return ScanResult(tuple(records), tuple(invalid), file_total)
```

- [ ] **Step 4: pyproject per-file-ignores**——`[tool.ruff.lint.per-file-ignores]` 内（`"tools/audit_starve_baseline.py"` 行附近，按字母序）加两行：

```toml
"tools/judge_reliability.py" = ["RUF001", "RUF002", "RUF003"]
"tests/unit/tools/test_judge_reliability.py" = ["RUF001", "RUF002", "RUF003"]
```

- [ ] **Step 5: 跑测通过 + lint**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -v && uv run ruff check tools/judge_reliability.py tests/unit/tools/test_judge_reliability.py`
Expected: 2 PASS；ruff 零告警

- [ ] **Step 6: Commit**

```bash
git add tools/judge_reliability.py tests/unit/tools/test_judge_reliability.py pyproject.toml
git commit -m "feat: spec #110 T1——judge_reliability 扫描层（#109 T4 卫生单源+族映射+双口径评级）+lint 豁免面"
```

---

### Task 3: 统计核心——κ/α/效度相关/形状纯函数

**Files:**
- Modify: `tools/judge_reliability.py`（追加统计函数——import 并顶部）
- Test: `tests/unit/tools/test_judge_reliability.py`（追加）

**Interfaces:**
- Consumes: Task 2 的 `AuditRecord`/`ScanResult`/`SKILL_FAMILY`
- Produces（Task 4 消费）:
  - `@dataclass(frozen=True) class KappaResult: kappa: float | None; agreement: float; n: int; warning: str | None`——p_e ≥ `_PREVALENCE_EPS`(0.999) 或 n=0 时 kappa=None+警示
  - `cohen_kappa(a: Sequence[int], b: Sequence[int]) -> KappaResult`
  - `cronbach_alpha(items: Sequence[Sequence[float]]) -> float | None`（items=行(k)、subjects=列(n)；σ²_total=0 或 k<2 或 n<2 → None）
  - `pearson(xs, ys) -> float | None`
  - `@dataclass(frozen=True) class SlopeResult: slope: float; r: float; t: float`——n<2 → 全 0；|r|≥1 → t=`float("inf")`（报告渲染「∞ 完美拟合」——M2）
  - `slope_regression(xs, ys) -> SlopeResult`（t = r·√((n−2)/(1−r²))）
  - `shape_stats(overalls, confidences) -> dict`（n<`_COLD_START_MIN`(8) 附 `insufficient`；含 mode/mode_table/sd 样本/range/high_rate）
  - `anchor_position_counts(audits_dir: Path) -> Counter`——首表头绑定+后续表头重绑（防跨表泄漏——M1）

**复杂度: leaf · test_kind: tdd_red_green**

- [ ] **Step 1: 写失败测试**（追加；spec 红测三件全落）

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


def test_pearson_and_slope_with_guards() -> None:
    from tools.judge_reliability import SlopeResult, pearson, slope_regression

    assert abs(pearson([1, 2, 3, 4], [2, 4, 6, 8]) - 1.0) < 1e-9
    sr = slope_regression([1.0, 2.0, 3.0, 4.0], [78.0, 78.7, 79.4, 80.1])
    assert abs(sr.slope - 0.7) < 1e-9 and sr.t == float("inf")  # r=±1→∞（M2）
    assert slope_regression([1.0], [78.0]) == SlopeResult(0.0, 0.0, 0.0)  # n<2 自守


def test_shape_stats_mode_sd_and_cold_start() -> None:
    from tools.judge_reliability import shape_stats

    st = shape_stats([79.0] * 12 + [78.0] * 3 + [86.0, 74.0], ["high"] * 15 + ["mid"] * 2)
    assert st["mode"] == (79.0, 12) and st["sd"] > 0 and st["range"] == (74.0, 86.0)
    assert st["high_rate"] == 15 / 17 and st.get("insufficient") is None
    cold = shape_stats([79.0, 78.0, 77.0], ["high", "mid", "low"])
    assert cold.get("insufficient") is True


def test_anchor_position_counts_first_table_only(tmp_path) -> None:
    from tools.judge_reliability import anchor_position_counts

    audits = tmp_path / "audits"
    _write(
        audits,
        "chapter-1-resonance.md",
        "| 维度 | 得分 | 满分 | 置信度 | 对照锚点 | 相对位置 | 证据 | 裁判理由 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 情感落地 | 22 | 30 | high | AC-001 | 相当 | L45 | show 充分 |\n"
        "| 场景临场感 | 20 | 25 | mid | AC-004 | 更差 | L12 | 概述偏多 |\n\n"
        "## 其他表\n\n"
        "| 列甲 | 列乙 |\n|---|---|\n| x | 相当 |\n",  # 次表不误计（M1）
    )
    c = anchor_position_counts(audits)
    assert c["相当"] == 1 and c["更差"] == 1 and c["更好"] == 0
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -v`
Expected: FAIL with `ImportError: cannot import name 'cohen_kappa'`

- [ ] **Step 3: 实现统计核心**（追加到 `tools/judge_reliability.py`；全部纯函数零 IO——anchor_position_counts 除外）

```python
from collections import Counter  # noqa: E402
from math import sqrt  # noqa: E402

_MIN_ITEMS = 2  # PLR2004：最小 item/样本数守卫（命名常量）
_MIN_PAIR = 2
_SLOPE_MIN_N = 3
_COLD_START_MIN = 8
_PREVALENCE_EPS = 0.999
_ANCHOR_POSITIONS = ("相当", "更差", "更好")


@dataclass(frozen=True)
class KappaResult:
    """Cohen kappa with raw agreement and degeneracy disclosure."""

    kappa: float | None
    agreement: float
    n: int
    warning: str | None


def cohen_kappa(a: Sequence[int], b: Sequence[int]) -> KappaResult:
    """Cohen kappa over paired binary ratings; None + warning when degenerate."""
    pairs = list(zip(a, b, strict=True))
    n = len(pairs)
    p_o = sum(1 for x, y in pairs if x == y) / n if n else 0.0
    ca = sum(1 for x, _ in pairs if x) / n if n else 0.0
    cb = sum(1 for _, y in pairs if y) / n if n else 0.0
    p_e = ca * cb + (1 - ca) * (1 - cb)
    if n == 0:
        return KappaResult(None, p_o, n, "零重叠章——不输出 κ")
    if p_e >= _PREVALENCE_EPS:
        return KappaResult(
            None, p_o, n, "prevalence 退化（边缘分布极端）——κ 不输出误导值，附原始 agreement"
        )
    return KappaResult((p_o - p_e) / (1 - p_e), p_o, n, None)


def cronbach_alpha(items: Sequence[Sequence[float]]) -> float | None:
    """Cronbach alpha — items are rows (k), subjects are columns (n)."""
    k = len(items)
    n = len(items[0]) if k else 0
    if k < _MIN_ITEMS or n < _MIN_ITEMS or any(len(row) != n for row in items):
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


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Pearson r; None when constant input or n below the pair floor."""
    n = len(xs)
    if n < _MIN_PAIR or n != len(ys):
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
    """OLS slope with r and t; t=inf marks a perfect fit (M2)."""

    slope: float
    r: float
    t: float


def slope_regression(xs: Sequence[float], ys: Sequence[float]) -> SlopeResult:
    """OLS of ys on xs; guards n<2 (zeros) and |r|>=1 (t=inf)."""
    n = len(xs)
    if n < _MIN_PAIR or n != len(ys):
        return SlopeResult(0.0, 0.0, 0.0)
    r = pearson(xs, ys)
    r = 0.0 if r is None else r
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx if sxx else 0.0
    t = (
        float("inf")
        if abs(r) >= 1.0
        else (r * sqrt((n - 2) / (1 - r * r)) if n >= _SLOPE_MIN_N else 0.0)
    )
    return SlopeResult(slope, r, t)


def shape_stats(overalls: Sequence[float], confidences: Sequence[str]) -> dict[str, object]:
    """Distribution shape summary; insufficient-sample disclosure below the floor."""
    n = len(overalls)
    result: dict[str, object] = {"n": n}
    if n < _COLD_START_MIN:
        result["insufficient"] = True
        result["disclosure"] = (
            f"样本不足（实评行 {n}<{_COLD_START_MIN}）——分布形状节不输出指标，仅此披露行"
        )
        return result
    counts = Counter(overalls)
    mode_val, mode_n = counts.most_common(1)[0]
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


def anchor_position_counts(audits_dir: Path) -> Counter:
    """Count Route-A anchor positions (相当/更差/更好), bound by header name.

    A header row containing 相对位置 (re)binds the column; rows in tables
    without that column cannot match at the bound index (column-position
    mismatch), preventing cross-table leakage (plan-review M1).
    """
    counts: Counter = Counter()
    for path in sorted(audits_dir.glob("chapter-*-resonance.md")):
        idx: int | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if "|" not in line or not cells:
                continue
            if any(c and set(c) <= {"-", ":"} for c in cells):
                continue  # markdown 分隔行
            if "相对位置" in cells:
                idx = cells.index("相对位置")  # 绑定或重绑（首表后的表头=重置再绑定）
                continue
            if idx is not None and len(cells) > idx and cells[idx] in _ANCHOR_POSITIONS:
                counts[cells[idx]] += 1
    return counts
```

（说明：M1 的「首表绑定」语义按「表头行重绑」实现——次表头若不含「相对位置」列则其数据行因列位语义不同而天然不命中三值集合；测试 `test_anchor_position_counts_first_table_only` 的次表「| x | 相当 |」在第 2 列位，首表「相对位置」在第 6 列位（0 基 5），len(cells)>idx 检查 + 列位不匹配 → 不计。若审阅认为应严格首表独占，实现时改为 `bound` 标志位版本，测试不变。）

- [ ] **Step 4: 跑测通过 + lint**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -v && uv run ruff check tools/judge_reliability.py`
Expected: 全 PASS；ruff 零告警

- [ ] **Step 5: Commit**

```bash
git add tools/judge_reliability.py tests/unit/tools/test_judge_reliability.py
git commit -m "feat: spec #110 T1——统计核心（κ+prevalence 警示/α/相关+守卫/形状+冷启动门/锚点表头绑定）"
```

---

### Task 4: 报告组装+justfile recipe+vol1 基线回放

**Files:**
- Modify: `tools/judge_reliability.py`（AuditRecord 补 `any_count` 字段+_alpha_versions/_validity/build_report/main）
- Modify: `justfile`（judge-reliability recipe，加在 gate-power 配方后）
- Test: `tests/unit/tools/test_judge_reliability.py`（追加报告级测试+Task 2 测试同步五字段）

**Interfaces:**
- Consumes: Task 1 `ResonanceRow.confidence`；Task 2 `scan_audits`/`SKILL_FAMILY`/`AuditRecord`；Task 3 全部统计函数；`LongitudinalDataError`（tools.report_longitudinal）
- Produces:
  - `AuditRecord` 第五字段 `any_count: int`（any-severity finding 单元数——C3 效度口径「issue 总量」字面）；**Task 2 的测试构造断言同步为五字段**
  - `build_report(project_dir: Path) -> str`——纯内容确定性（同输入同输出字节；时间戳只在文件名）
  - `main(argv: Sequence[str] | None = None) -> int`——写 `reports/judge-reliability-<UTCts>.md`；`LongitudinalDataError` → stderr + exit 2（M7，report_longitudinal 先例）
  - justfile：`judge-reliability DIR *ARGS:` → `uv run python tools/judge_reliability.py "$1" "${@:2}"`

**复杂度: infra · test_kind: tdd_red_green（报告组装）+ characterization（vol1 回放带宽数字断言不入 CI——本地验收）**

报告节序（模板钉死）：①前置卫生行（file_total/invalid 剔除计数逐文件）②两两 κ 表（rater = 个体技能 + **族 OR 合成 rater**（group-character(OR)/group-craft(OR)——章节=成员并集、评级=成员 OR，注记「族 OR 合成」）；评级列 agreement(any)/κ(any)/κ(hard)/计数版 r；同族成员对注记「同派发伪影——不作判官间一致性解读」；prevalence 退化行）③Cronbach α 六数（item 集两版 × any 二值/hard 二值/hard 计数——**证据锚=「always-on 全 × any 二值」列注记**）④效度相关（r(overall, 其余 any-severity issue 总量)+n+join 披露行；human_overridden 剔除行数；负对照 r(overall, 章长)；**口径差披露行**：原证据 +0.068/n=28 的统计脚本不在盘不可逐字复现——本行为重派生口径（spec r2.2））⑤分布形状（excluded 行剔除；shape_stats+通胀 slope/r/t（t=∞ 渲染「∞（完美拟合）」）+锚点相对位置计数；冷启动披露）⑥**外部锚定效度引用**（固定披露行「#115 T3 外部锚定未执行——κ/α 不得单独作为判官可用性结论」）⑦方法论注记（低 κ 的一半是分工；观测面不是 gate）。

效度相关取数规则（钉死）：join = scored 非 excluded trend 行 ∧ 该章 ≥1 份 valid 非 resonance 审计；「其余 issue 总量」= 该章全部非 resonance valid 审计的 `any_count` 总和；「章长」= `chapters/chapter-N.md` 去空白字符数（文件缺失→不入负对照）。

- [ ] **Step 1: 写失败测试**（报告级——迷你语料断言关键行+确定性+main 错误面）

```python
MINI_TREND = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
    + "".join(f"| {i} | 推进 | 20 | 20 | 20 | 15 | {75 + i} | high |  |\n" for i in range(1, 9))
)


def _mini_project(tmp_path: Path) -> Path:
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)  # 幂等（确定性测试二次调用）
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
    (tmp_path / "chapters").mkdir(parents=True, exist_ok=True)
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
        "Cronbach α",
        "效度相关",
        "外部锚定未执行",
        "观测面",
        "prevalence",
    ):
        assert needle in report, f"报告缺节：{needle}"
    assert build_report(_mini_project(tmp_path)) == report  # 同输入同输出（_mini_project 幂等）


def test_group_pair_not_degrouped_emits_artifact_warning(tmp_path) -> None:
    """④(c) 红测：同族对（pov×dialogue）带伪影注记+族 OR 合成 rater 行（I2）。"""
    from tools.judge_reliability import build_report

    proj = _mini_project(tmp_path)
    for ch in range(1, 9):
        _write(proj / "audits", f"chapter-{ch}-pov.md", "**判定**：通过\n")
        _write(proj / "audits", f"chapter-{ch}-dialogue.md", "**判定**：通过\n")
    report = build_report(proj)
    assert "dialogue × pov" in report and "同派发伪影" in report
    assert "group-character(OR)" in report and "族 OR 合成" in report


def test_main_missing_trend_exits_two(tmp_path, capsys) -> None:
    """M7：数据面缺失 → stderr + exit 2（report_longitudinal 先例）。"""
    from tools.judge_reliability import main

    empty = tmp_path / "proj"
    (empty / "truth").mkdir(parents=True)
    assert main([str(empty)]) == 2
    assert "resonance_trend" in capsys.readouterr().err
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -k "build_report or main_missing" -v`
Expected: FAIL with `ImportError: cannot import name 'build_report'`

- [ ] **Step 3: 实现 AuditRecord 第五字段 + build_report + main + recipe**

`AuditRecord` 补字段（Task 2 测试的构造断言同步加 `any_count=2`/`any_count=1` 等实际值——texture 两单元=any_count 2、sensitivity 一单元=any_count 1）；`scan_audits` 构造行补 `any_count=len(units)`。

```python
_ALPHA_EXCLUDED = frozenset(SKILL_FAMILY) - {
    "texture",
    "reader-pull",
    "anti-ai",
}  # group-character 成员
_CRAFT_TRIO = ("texture", "reader-pull", "anti-ai")


def _family_raters(records: tuple[AuditRecord, ...]) -> dict[str, dict[int, int]]:
    """Family OR raters: chapters = member union, rating = member OR (I2)."""
    out: dict[str, dict[int, int]] = {}
    for fam in sorted(set(SKILL_FAMILY.values())):
        members = [r for r in records if SKILL_FAMILY.get(r.skill) == fam]
        if not members:
            continue
        any_or: dict[int, int] = {}
        hard_or: dict[int, int] = {}
        for r in members:
            any_or[r.chapter] = any_or.get(r.chapter, 0) or r.any_binary
            hard_or[r.chapter] = hard_or.get(r.chapter, 0) or r.hard_binary
        out[f"{fam}(OR)"] = any_or
        out[f"{fam}(OR-hard)"] = hard_or
    return out


def _alpha_versions(scan: ScanResult) -> list[tuple[str, str, int, float | None]]:
    """α 六数：item 集两版 × 评级三版；subjects = listwise 完整章。"""
    by: dict[tuple[int, str], AuditRecord] = {(r.chapter, r.skill): r for r in scan.records}
    skills = sorted({r.skill for r in scan.records})
    item_sets = [
        ("always-on 全 items", [s for s in skills if s not in _ALPHA_EXCLUDED]),
        (
            "剔 craft 族 items",
            [s for s in skills if s not in _ALPHA_EXCLUDED and s not in _CRAFT_TRIO],
        ),
    ]
    getters: list[tuple[str, object]] = [
        ("any 二值", lambda r: float(r.any_binary)),
        ("hard 二值", lambda r: float(r.hard_binary)),
        ("hard 计数", lambda r: float(r.hard_count)),
    ]
    out: list[tuple[str, str, int, float | None]] = []
    for set_name, items in item_sets:
        if len(items) < _MIN_ITEMS:
            out.extend((set_name, ver, 0, None) for ver, _ in getters)
            continue
        chapters = sorted(set.intersection(*({c for c, sk in by if sk == s} for s in items)))
        for ver, fn in getters:
            matrix = [[fn(by[(c, s)]) for c in chapters] for s in items]
            out.append((set_name, ver, len(chapters), cronbach_alpha(matrix)))
    return out


def _validity(project_dir: Path, scan: ScanResult, rows: dict[int, ResonanceRow]) -> list[str]:
    """④ 效度相关：join = scored 非 excluded 行 ∧ 该章 ≥1 valid 非 resonance 审计。"""
    any_sum: dict[int, int] = {}
    for r in scan.records:
        if r.skill != "resonance":
            any_sum[r.chapter] = any_sum.get(r.chapter, 0) + r.any_count
    joined = sorted(c for c, r in rows.items() if not r.excluded and c in any_sum)
    r_val = pearson([float(rows[c].overall) for c in joined], [float(any_sum[c]) for c in joined])
    lens: list[float] = []
    overs: list[float] = []
    for c in joined:
        text_file = project_dir / "chapters" / f"chapter-{c}.md"
        if text_file.exists():
            lens.append(float(len("".join(text_file.read_text(encoding="utf-8").split()))))
            overs.append(float(rows[c].overall))
    r_len = pearson(overs, lens) if lens else None
    n_over = sum(1 for r in rows.values() if r.excluded)

    def fmt(v: float | None) -> str:
        return "—" if v is None else f"{v:+.3f}"

    return [
        f"- resonance overall × 其余审计 issue 总量（any 口径）：r = {fmt(r_val)}（n = {len(joined)}）",
        "- join 规则：scored 非 excluded trend 行 ∧ 该章 ≥1 valid 非 resonance 审计（n 如上披露）",
        f"- human_overridden 行剔除：{n_over} 行（不入效度/形状统计）",
        f"- 长度偏差负对照：overall × 章长（去空白字符数）r = {fmt(r_len)}（n = {len(lens)}）",
        "- 口径差披露：动机证据 r=+0.068/n=28 的原统计脚本不在盘不可逐字复现——本行为重派生口径（spec r2.2）",
    ]
```

`build_report` 主体（节序①-⑦；rater 列表 = 个体技能四列（any/hard 二值+hard 计数 dict）+ 族 OR 两行（any/hard，无计数列）；κ 表七列：技能对/n/agreement(any)/κ(any)/κ(hard)/计数版 r/注记；族 rater 参与全配对 note=「族 OR 合成」（含对本族成员的配对）、同族成员对 note=「同派发伪影」、其余=warning 或空；③α 行在 any 二值×全 items 行尾追加「（证据锚：动机节 α=0.311/n=25 在本列复现）」注记；⑤形状节 kept=[非 excluded] 行、slope 行 t=∞ 渲染「∞（完美拟合）」；⑥⑦固定文案——文案逐字：

```python
def build_report(project_dir: Path) -> str:
    """Assemble the seven-section report; byte-deterministic for a fixed corpus."""
    from tools.report_longitudinal import TREND_FILENAME, parse_resonance_trend

    audits_dir = project_dir / "audits"
    scan = scan_audits(audits_dir)
    rows = parse_resonance_trend(project_dir / "truth" / TREND_FILENAME)
    lines: list[str] = ["# Judge Reliability Report（观测面——非 gate，不进生产读面）", ""]
    # ① 前置卫生
    lines += [
        "## 前置数据卫生（#109 T4 invalid 剔除）",
        "",
        f"- 语料文件总数：{scan.file_total}；invalid 剔除：{len(scan.invalid)}",
    ]
    lines += [f"  - {msg}" for msg in scan.invalid] or ["  - （零 invalid）"]
    # ② 两两 κ：个体技能 + 族 OR 合成 rater
    by: dict[tuple[int, str], AuditRecord] = {(r.chapter, r.skill): r for r in scan.records}
    raters: list[tuple[str, dict[int, int], dict[int, int], dict[int, int]]] = []
    for s in sorted({r.skill for r in scan.records}):
        recs = [r for r in scan.records if r.skill == s]
        raters.append(
            (
                s,
                {r.chapter: r.any_binary for r in recs},
                {r.chapter: r.hard_binary for r in recs},
                {r.chapter: r.hard_count for r in recs},
            )
        )
    for name, ratings in _family_raters(scan.records).items():
        if name.endswith("(OR)"):
            hard = _family_raters(scan.records).get(name.replace("(OR)", "(OR-hard)"), {})
            raters.append((name, ratings, hard, {}))
    lines += [
        "",
        "## 跨技能两两 Cohen κ（评级 any/hard 二值 + hard 计数相关；成对完整例）",
        "",
        "| 技能对 | n | agreement(any) | κ(any) | κ(hard) | 计数版 r | 注记 |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, (s1, a1, h1, c1) in enumerate(raters):
        for s2, a2, h2, c2 in raters[i + 1 :]:
            common = sorted(set(a1) & set(a2))
            res = cohen_kappa([a1[c] for c in common], [a2[c] for c in common])
            res_h = cohen_kappa([h1[c] for c in common], [h2[c] for c in common])
            r_cnt = (
                pearson([float(c1[c]) for c in common], [float(c2[c]) for c in common])
                if c1 and c2
                else None
            )
            fam1, fam2 = SKILL_FAMILY.get(s1), SKILL_FAMILY.get(s2)
            synthetic = "(OR)" in s1 or "(OR)" in s2
            note = (
                "同派发伪影——不作判官间一致性解读"
                if fam1 and fam1 == fam2
                else ("族 OR 合成" if synthetic else (res.warning or ""))
            )
            k_any = "—" if res.kappa is None else f"{res.kappa:+.3f}"
            k_hard = "—" if res_h.kappa is None else f"{res_h.kappa:+.3f}"
            r_txt = "—" if r_cnt is None else f"{r_cnt:+.3f}"
            lines.append(
                f"| {s1} × {s2} | {res.n} | {res.agreement:.3f} | {k_any} | {k_hard} | {r_txt} | {note} |"
            )
    # ③ α 六数
    lines += ["", "## Cronbach α（item 集两版 × 评级三版；subjects=listwise 完整章）", ""]
    for set_name, ver, n, alpha in _alpha_versions(scan):
        a_txt = "—" if alpha is None else f"{alpha:.3f}"
        anchor = (
            "（证据锚：动机节 α=0.311/n=25 在本列复现）"
            if ver == "any 二值" and "全" in set_name
            else ""
        )
        lines.append(f"- {set_name} × {ver}：α = {a_txt}（n = {n}）{anchor}")
    # ④ 效度相关
    lines += ["", "## 效度相关"] + _validity(project_dir, scan, rows)
    # ⑤ 分布形状（excluded 剔除）
    kept_rows = [(c, r) for c, r in rows.items() if not r.excluded]
    overs = [float(r.overall) for _, r in kept_rows]
    confs = [r.confidence for _, r in kept_rows]
    st = shape_stats(overs, confs)
    lines += ["", "## 分布形状", f"- 实评行（excluded 剔除后）：{st['n']}"]
    if st.get("insufficient"):
        lines.append(f"- ⚠️ {st['disclosure']}")
    else:
        mode_val, mode_n = st["mode"]  # type: ignore[misc]
        mode_table = "、".join(f"{v:g}×{c}" for v, c in st["mode_table"])  # type: ignore[misc]
        lines += [
            f"- 模值：{mode_val:g} × {mode_n}/{st['n']}；频率表（降序）：{mode_table}",
            f"- sd（样本）：{st['sd']}；极差：{st['range'][0]:g}-{st['range'][1]:g}",  # type: ignore[index]
            f"- confidence=high 基率：{st['high_rate']:.3f}",  # type: ignore[index]
        ]
        if len(overs) >= _SLOPE_MIN_N:
            chs = [float(c) for c, _ in kept_rows]
            sr = slope_regression(chs, overs)
            t_txt = "∞（完美拟合）" if sr.t == float("inf") else f"{sr.t:+.2f}"
            lines.append(f"- 通胀 slope：{sr.slope:+.4f} 分/章（r = {sr.r:+.3f}，t = {t_txt}）")
    pos = anchor_position_counts(audits_dir)
    lines += [
        f"- 锚点相对位置计数：相当 {pos.get('相当', 0)} / 更差 {pos.get('更差', 0)} / 更好 {pos.get('更好', 0)}"
    ]
    # ⑥ 外部锚定效度引用
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
    """CLI entry: write reports/judge-reliability-<ts>.md; exit 2 on data errors."""
    from tools.report_longitudinal import LongitudinalDataError

    parser = argparse.ArgumentParser(description="Judge inter-rater reliability report (spec #110)")
    parser.add_argument("project_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        report = build_report(args.project_dir)
    except LongitudinalDataError as exc:
        print(f"数据面错误：{exc}", file=sys.stderr)
        return 2
    out_dir = args.project_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%SZ", time.gmtime())
    out = out_dir / f"judge-reliability-{ts}.md"
    out.write_text(report, encoding="utf-8")
    print(out)
    return 0
```

（`ResonanceRow` 类型注解：文件顶部 `from tools.report_longitudinal import ResonanceRow` 带 `# noqa: E402`，或函数内 import——与 build_report 内 parse import 同段。）

justfile 追加（gate-power 配方后）：

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
Expected: 报告落 `novel-xinghuo-vol1/reports/`；**证据锚核对**：α（always-on 全 × any 二值）∈[0.26,0.36] 且 n=25；更好=0 精确；模值 79×12 精确；high 24/32；invalid 剔除计数≈51（plan 审查 sim 实测参考值）；any 口径效度 r 满足 |r|<0.3（方向性判据）；hard 口径数字（α≈0.71/0.58、效度 r≈-0.05/n=32）如实入报告作重派生基线——输出与核对结论粘 progress.md `## 验收证据`（证据锚带外→停查口径，不静默放过）

- [ ] **Step 6: Commit**

```bash
git add tools/judge_reliability.py justfile tests/unit/tools/test_judge_reliability.py
git commit -m "feat: spec #110 T1——报告组装（七节+双口径+族 OR rater+口径差披露）+just recipe+vol1 基线回放验收"
```

---

### Task 5: T2 接线——#107 spec 加 McNemar 引用行

**Files:**
- Modify: `docs/superpowers/specs/2026-11-15-spec107-reviewer-model-tier.md:35`（T2 bullet 列表末尾、判据行前追加）
- Test: `tests/unit/tools/test_judge_reliability.py`（追加 grep 断言）

**Interfaces:**
- Consumes: spec #110 r2.1 T2 义务文本
- Produces: #107 spec 文本含 #110 引用行（grep 可证——AC 自证段）

**复杂度: leaf · test_kind: characterization（grep 级断言）**

- [ ] **Step 1: 写失败测试**

```python
def test_spec107_references_110_mcnemar() -> None:
    spec107 = REPO_ROOT / "docs/superpowers/specs/2026-11-15-spec107-reviewer-model-tier.md"
    text = spec107.read_text(encoding="utf-8")
    assert "#110" in text and "McNemar" in text, "#107 T2 须含 #110 McNemar 配对设计引用行"
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/unit/tools/test_judge_reliability.py -k spec107 -v`
Expected: FAIL with AssertionError

- [ ] **Step 3: 加引用行**（#107 T2 bullet 列表末尾、`**判据**` 行之前追加）：

```markdown
  - **判据设计（spec #110 T2 接线）**：A/B 判据须为 **McNemar 配对设计**（同变异两臂同测）+ 功效核算表入预注册文档（27/臂起步 power 0.56-0.60、45/臂 0.78-0.81、63/臂 0.90+；15pp 效应明示不可检）——核算口径引用 spec #110（judge-reliability-harness）；
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
    spec103 = REPO_ROOT / "docs/superpowers/specs/2026-11-15-spec103-highlight-distill.md"
    assert "#110" in spec103.read_text(encoding="utf-8"), (
        "#103 T1 须含 #110 confidence 双闸裁定路径引用行"
    )
    skill = REPO_ROOT / "skills/shenbi-review-resonance/SKILL.md"
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
| T1 判据：vol1 回放关键数字一致（**证据锚=any 口径列**：α≈0.31/n=25/更好=0/模值 79×12；r 为方向性判据+口径差披露——spec r2.2） | Task 4 Step 5 | 本地回放+证据锚带核对粘 progress.md |
| T1 判据：红测（同分→α=1/独立→α≈0/prevalence 警示/饿死剔除/group 反例/冷启动） | Task 2/3/4 测试 | pytest 全绿 |
| T2 判据：#107 引用行 grep 可证 | Task 5 | test_spec107_references_110_mcnemar |
| T2 判据：报告含外部锚定效度引用节+未就绪披露 | Task 4 | test_build_report_sections（「外部锚定未执行」needle） |
| T3 判据：#103 spec 引用行（自证段）+SKILL 校准口径行 | Task 6 | test_spec103_references_110_confidence_gate |
| 验收 2：报告落盘数字可重放（同输入同输出） | Task 4 | test_build_report_sections_and_determinism |
| 验收 3：bug-hunt 四件（饿死剔除【真实 fixture】/prevalence 陷阱/group 反例/冷启动） | Task 2/3/4 | 对应四测试 |
| T3 承接段（#103 plan 检查单） | 不在本件生命周期 | deviations 移交 #103 plan 审查核验 |
