"""Judge inter-rater reliability harness (spec #110) — offline, deterministic, zero LLM.

Observation-plane instrument, NOT a gate: nothing in src/shenbi/ may read
its reports (repo discipline, #108 T3 precedent). Replay semantics are
pinned HERE in executable form; spec prose is a gloss.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

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

_MIN_ITEMS = 2  # PLR2004：最小 item/样本数守卫（命名常量）
_MIN_PAIR = 2
_SLOPE_MIN_N = 3
_COLD_START_MIN = 8
_PREVALENCE_EPS = 0.999
_ANCHOR_POSITIONS = ("相当", "更差", "更好")


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
