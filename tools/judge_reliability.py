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
from tools.report_longitudinal import (  # noqa: E402
    TREND_FILENAME,
    LongitudinalDataError,
    ResonanceRow,
    parse_resonance_trend,
)

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
    any_count: int  # 任一 severity finding 单元数（效度口径「issue 总量」字面）


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
            AuditRecord(
                int(m.group(1)),
                m.group(2),
                1 if units else 0,
                1 if hard else 0,
                hard,
                len(units),
            )
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


# group-character 成员不入 α items（craft 三员留 v1、剔于 v2）
_ALPHA_EXCLUDED = frozenset(SKILL_FAMILY) - {"texture", "reader-pull", "anti-ai"}
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
    """α 六数：item 集两版 × 评级三版；subjects = listwise 完整章."""
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
            matrix = [[fn(by[(c, s)]) for c in chapters] for s in items]  # type: ignore[call-arg]
            out.append((set_name, ver, len(chapters), cronbach_alpha(matrix)))
    return out


def _validity(project_dir: Path, scan: ScanResult, rows: dict[int, ResonanceRow]) -> list[str]:
    """④ 效度相关：join = scored 非 excluded 行 ∧ 该章 ≥1 valid 非 resonance 审计."""
    any_sum: dict[int, int] = {}
    hard_sum: dict[int, int] = {}
    for r in scan.records:
        if r.skill != "resonance":
            any_sum[r.chapter] = any_sum.get(r.chapter, 0) + r.any_count
            hard_sum[r.chapter] = hard_sum.get(r.chapter, 0) + r.hard_count
    joined = sorted(c for c, r in rows.items() if not r.excluded and c in any_sum)
    r_val = pearson([float(rows[c].overall) for c in joined], [float(any_sum[c]) for c in joined])
    r_hard = pearson([float(rows[c].overall) for c in joined], [float(hard_sum[c]) for c in joined])
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
        f"- resonance overall × 其余 issue 总量（any）：r = {fmt(r_val)}（n = {len(joined)}）",
        f"- resonance overall × 其余硬发现总量（hard）：r = {fmt(r_hard)}（n = {len(joined)}）",
        "- join 规则：scored 非 excluded trend 行 ∧ 该章 ≥1 valid 非 resonance 审计（n 如上披露）",
        f"- human_overridden 行剔除：{n_over} 行（不入效度/形状统计）",
        f"- 长度负对照：overall × 章长（去空白字符）r = {fmt(r_len)}（n = {len(lens)}）",
        "- 口径差披露：原证据 r=+0.068/n=28 脚本不在盘不可逐字复现，本行为重派生口径（spec r2.2）",
    ]


def build_report(project_dir: Path) -> str:
    """Assemble the seven-section report; byte-deterministic for a fixed corpus."""
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
    fam = _family_raters(scan.records)
    for name, ratings in fam.items():
        if name.endswith("(OR)"):
            raters.append((name, ratings, fam.get(name.replace("(OR)", "(OR-hard)"), {}), {}))
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
                f"| {s1} × {s2} | {res.n} | {res.agreement:.3f} | {k_any} | {k_hard} | {r_txt} | {note} |",  # noqa: E501
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
    lines += ["", "## 效度相关", *_validity(project_dir, scan, rows)]
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
        f"- 锚点相对位置：相当 {pos.get('相当', 0)} / 更差 {pos.get('更差', 0)} / 更好 {pos.get('更好', 0)}",  # noqa: E501
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


if __name__ == "__main__":
    raise SystemExit(main())
