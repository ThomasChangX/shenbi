"""Longitudinal acceptance report for a pipeline project dir (spec #68).

Read-only verdict layer over already-persisted artifacts: novel.json targets,
truth/resonance_trend.md authoritative per-chapter scores, pipeline-state.json
chapter terminal health, audits/ raw reviewer reports, cost/token-ledger.jsonl.
Zero LLM, zero dispatch, zero src/shenbi/ mutation (pure-function imports only).
Exit codes: 0 pass / 1 fail / 2 data error (fail-closed — never pass silently
on missing data).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from shenbi.cost.ledger import TokenLedger
from shenbi.gates.shared import word_count_md
from shenbi.pipeline.audit_aggregate import FindingUnit, extract_finding_units
from shenbi.pipeline.chapter_loop import committed_chapter_anchor
from shenbi.skill_utils.drift_detection.compute_drift import (
    DriftFinding,
    detect_chapter_drift,
)

SCHEMA_ID = "shenbi-longitudinal-verdict-v1"
TREND_FILENAME = "resonance_trend.md"
STATE_FILENAME = "pipeline-state.json"
MIN_SEGMENTS = 3  # 前/中/后三段各至少 1 章（canary N=3 为退化下界）


class LongitudinalDataError(Exception):
    """Verdict-critical input missing/malformed → exit 2 (fail-closed)."""

    def __init__(self, reason: str) -> None:
        """Carry the machine-readable reason alongside the message."""
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
    """One parsed trend row: overall score + human-override exclusion flag."""

    overall: float
    excluded: bool


def parse_resonance_trend(path: Path) -> dict[int, ResonanceRow]:
    """Parse truth/resonance_trend.md rows keyed by bare {N} chapter cell.

    Column binding is by header name (chapter/overall/human_overridden), never
    by fixed index — a future skill-side column reorder must fail loud, not
    silently misread a numeric neighbour. The contract header is written only
    by the skill; a file without it is a data error (parse_trend would
    silently return an empty series — forbidden).
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
    for line in lines[header_idx + 1 :]:
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
    if n_done < MIN_SEGMENTS:
        raise LongitudinalDataError(f"insufficient chapters: {n_done}")
    f, r = divmod(n_done, 3)
    c = f + (1 if r else 0)
    lengths = [(f, f, f), (f, f, c), (f, c, c), (c, c, c)][r]
    out: dict[str, list[int]] = {"front": [], "mid": [], "back": []}
    start = 1
    for name, ln in zip(("front", "mid", "back"), lengths, strict=True):
        out[name] = list(range(start, start + ln))
        start += ln
    return out


# ---------------------------------------------------------------------------
# Verdict core (spec #68 §1) — decision order: data-error → completeness → quality
# ---------------------------------------------------------------------------

VOLUME_RATIO_FLOOR = 0.95
RESONANCE_CHAPTER_FLOOR = 85.0
RESONANCE_MEAN_FLOOR = 90.0
BACK_DROP_MAX = 5.0
BACK_ESCALATION_FACTOR = 2
MIN_SAMPLES_SIGMA = 6  # detect_chapter_drift 的 min_samples_sigma 缺省——
# 章数低于此值 mean-2σ 检测不触发，同时段分辨率最低（spec §1 报告注明）


def load_state_dict(project_dir: Path) -> dict[str, Any]:
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


def load_novel_json(project_dir: Path) -> dict[str, Any]:
    """Load novel.json as plain dict (data-error face: exit 2)."""
    path = project_dir / "novel.json"
    if not path.exists():
        raise LongitudinalDataError(f"{path}: novel.json missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LongitudinalDataError(f"{path}: broken JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise LongitudinalDataError(f"{path}: not a JSON object")
    return data


@dataclass(frozen=True)
class ChapterVerdict:
    """Per-chapter terminal health row with three-input-face fail reasons."""

    chapter: int
    present: bool
    status: str | None
    audit_retry_count: int | None
    resonance: float | None
    cjk_chars: int
    fail_reasons: tuple[str, ...]


def chapter_verdicts(
    project_dir: Path, n_done: int, rows: dict[int, ResonanceRow], state: dict[str, Any]
) -> list[ChapterVerdict]:
    """Per-chapter terminal health with three-input-face fail-closed semantics."""
    raw_states = (state.get("chapter_loop") or {}).get("chapter_states") or {}
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
        out.append(
            ChapterVerdict(
                chapter=ch,
                present=present,
                status=status,
                audit_retry_count=retry,
                resonance=row.overall if row else None,
                cjk_chars=cjk,
                fail_reasons=tuple(reasons),
            )
        )
    return out


def escalation_counts_by_segment(
    checkpoint_history: list[dict[str, Any]], segments: dict[str, list[int]]
) -> dict[str, int]:
    """Count ESCALATION events per segment.

    chapter=None entries are excluded from segments and counted under
    'unattributed' (disclosure face). Type contract is authoritative
    (list[dict[str, Any]] — no redundant isinstance; malformed state is the
    exit-2 face upstream).
    """
    counts: dict[str, int] = dict.fromkeys(("front", "mid", "back"), 0)
    counts["unattributed"] = 0
    member = {ch: name for name, chs in segments.items() for ch in chs}
    for entry in checkpoint_history:
        if entry.get("type") != "escalation":
            continue
        ch = entry.get("chapter")
        if isinstance(ch, int) and ch in member:
            counts[member[ch]] += 1
        else:
            counts["unattributed"] += 1
    return counts


def drift_gate(rows: dict[int, ResonanceRow], n_done: int) -> list[DriftFinding]:
    """Reuse compute_drift.detect_chapter_drift on the overall series.

    Authoritative semantics live in the imported function; this wrapper only
    feeds it. Series and exclude indices derive from the SAME filtered
    enumeration so a gapped series never misaligns excluded flags.
    """
    present = [ch for ch in range(1, n_done + 1) if ch in rows]
    series = [rows[ch].overall for ch in present]
    exclude = {i for i, ch in enumerate(present) if rows[ch].excluded}
    return detect_chapter_drift(series, dim="overall", exclude_indices=exclude or None)


def _mean(xs: list[float]) -> float | None:
    """Mean of a non-empty float list, else None."""
    return sum(xs) / len(xs) if xs else None


def _completeness(
    n_done: int, n_target: int, verdicts: list[ChapterVerdict]
) -> tuple[list[str], list[str]]:
    """Completeness face (exit-1): N shortfall + per-chapter fail reasons."""
    reasons: list[str] = []
    disclosures: list[str] = []
    if n_done < n_target:
        reasons.append(f"N_done={n_done} < N_target={n_target} (incomplete run / lost chapters)")
    if n_done > n_target:
        disclosures.append(f"N_done={n_done} > N_target={n_target} (anchor/metadata drift)")
    for v in verdicts:
        reasons.extend(f"ch{v.chapter}: {r}" for r in v.fail_reasons)
    return reasons, disclosures


def _quality_reasons(verdicts: list[ChapterVerdict], target_wc: int) -> list[str]:
    """Quality conditions 1-2 residuals: volume floor + resonance floors."""
    reasons: list[str] = []
    cjk_total = sum(v.cjk_chars for v in verdicts)
    if cjk_total < target_wc * VOLUME_RATIO_FLOOR:
        reasons.append(f"volume {cjk_total} < {target_wc}x95%")
    scored = [v.resonance for v in verdicts if v.resonance is not None]
    mean = _mean(scored)
    reasons.extend(
        f"ch{v.chapter}: resonance {v.resonance} < {RESONANCE_CHAPTER_FLOOR}"
        for v in verdicts
        if v.resonance is not None and v.resonance < RESONANCE_CHAPTER_FLOOR
    )
    if mean is not None and mean < RESONANCE_MEAN_FLOOR:
        reasons.append(f"resonance mean {mean:.1f} < {RESONANCE_MEAN_FLOOR}")
    return reasons


def _trend_block(
    segments: dict[str, list[int]],
    verdicts: list[ChapterVerdict],
    checkpoint_history: list[dict[str, Any]],
    rows: dict[int, ResonanceRow],
    n_done: int,
) -> tuple[list[str], list[str], dict[str, Any], list[DriftFinding]]:
    """Quality condition 3: segment means/drop, escalation cap, drift gate.

    Returns (reasons, disclosures, block, findings); findings feed the
    report's drift_findings key.
    """
    reasons: list[str] = []
    disclosures: list[str] = []
    seg_means: dict[str, float | None] = {}
    for name, chs in segments.items():
        vals: list[float] = []
        for ch in chs:
            row = verdicts[ch - 1]
            if row.resonance is not None:
                vals.append(row.resonance)
        seg_means[name] = _mean(vals)
    back_drop = None
    if seg_means["front"] is not None and seg_means["back"] is not None:
        back_drop = seg_means["front"] - seg_means["back"]
        if back_drop > BACK_DROP_MAX:
            reasons.append(f"后段降幅 {back_drop:.1f} > {BACK_DROP_MAX}")
    esc = escalation_counts_by_segment(checkpoint_history, segments)
    if esc["back"] > esc["front"] * BACK_ESCALATION_FACTOR:
        reasons.append(f"后段 escalation 计数 {esc['back']} > 前段 {esc['front']}x2")
    if esc["unattributed"]:
        disclosures.append(f"{esc['unattributed']} escalation 事件 chapter=None，排除出分段计数")
    findings = drift_gate(rows, n_done)
    reasons.extend(f"drift[{f.kind.value}] {f.dim}: {f.detail}" for f in findings)
    member = {ch: name for name, chs in segments.items() for ch in chs}
    ckpt_counts: dict[str, int] = {"front": 0, "mid": 0, "back": 0}
    for entry in checkpoint_history:
        ch = entry.get("chapter")
        if entry.get("type") != "escalation" and isinstance(ch, int) and ch in member:
            ckpt_counts[member[ch]] += 1
    block: dict[str, Any] = {
        "segment_resonance_means": seg_means,
        "back_drop_vs_front": round(back_drop, 2) if back_drop is not None else None,
        "escalation_counts": esc,
        "checkpoint_counts": ckpt_counts,
    }
    return reasons, disclosures, block, findings


def evaluate(project_dir: Path) -> dict[str, Any]:
    """Full longitudinal verdict; LongitudinalDataError → exit 2 (caller maps)."""
    target_wc, n_target = parse_novel_targets(load_novel_json(project_dir))
    rows = parse_resonance_trend(project_dir / "truth" / TREND_FILENAME)
    state = load_state_dict(project_dir)
    n_done = committed_chapter_anchor(project_dir)
    segments = segment_chapters(n_done)  # raises on n_done < 3
    verdicts = chapter_verdicts(project_dir, n_done, rows, state)

    reasons, disclosures = _completeness(n_done, n_target, verdicts)
    reasons += _quality_reasons(verdicts, target_wc)
    trend_reasons, trend_disc, trend_block, findings = _trend_block(
        segments, verdicts, state.get("checkpoint_history") or [], rows, n_done
    )
    reasons += trend_reasons
    disclosures += trend_disc

    pending = state.get("pending_checkpoint") or {}
    if isinstance(pending, dict) and pending.get("type") not in (None, "none"):
        disclosures.append(f"pending_checkpoint={pending.get('type')} (未裁决，不入判据)")
    if n_done < MIN_SAMPLES_SIGMA:
        disclosures.append(
            f"N={n_done} < {MIN_SAMPLES_SIGMA}：mean-2σ 检测不触发、每段最多 "
            f"{(n_done + 2) // 3} 章——分辨率最低（canary 退化情形，spec §1 报告注明）"
        )

    # observations + coverage + taxonomy 并网（T4）
    chapters_list = list(range(1, n_done + 1))
    cjk_by_ch = {v.chapter: v.cjk_chars for v in verdicts}
    audit_sources = {"raw": 0, "aggregate": 0, "none": 0}
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
    led = ledger_stats(project_dir, chapters_list, cjk_by_ch)

    verdict = "fail" if reasons else "pass"
    cjk_total = sum(v.cjk_chars for v in verdicts)
    ratio = cjk_total / target_wc if target_wc else 0.0
    return {
        "schema": SCHEMA_ID,
        "verdict": verdict,
        "exit_code": 1 if verdict == "fail" else 0,
        "reasons": reasons,
        "disclosures": disclosures,
        "n_target": n_target,
        "n_done": n_done,
        "segments": segments,
        "volume": {
            "target_word_count": target_wc,
            "cjk_total": cjk_total,
            "ratio": round(ratio, 4),
        },
        "per_chapter": [
            {
                "chapter": v.chapter,
                "present": v.present,
                "status": v.status,
                "audit_retry_count": v.audit_retry_count,
                "resonance": v.resonance,
                "cjk_chars": v.cjk_chars,
                "fail_reasons": list(v.fail_reasons),
            }
            for v in verdicts
        ],
        "trend": trend_block,
        "drift_findings": [
            {"kind": f.kind.value, "dim": f.dim, "detail": f.detail} for f in findings
        ],
        "taxonomy": {
            "heatmap": [
                {"chapter": ch, "category": cat, "count": n}
                for (ch, cat), n in sorted(heatmap.items())
            ],
            "unclassified": unclassified_total,
            "routing": SUBSYSTEM_ROUTES,
            "audit_sources": audit_sources,
        },
        "scalability": {
            "per_chapter": led["per_chapter"],
            "truth_growth": truth_growth(project_dir),
        },
        "coverage": {
            "resonance_rows": [len(rows), n_done],
            "audits_chapters": [n_done - audit_sources["none"], n_done],
            "ledger_chapters": [led["chapters_covered"], n_done],
            "ledger_skipped_rows": led["skipped_rows"],
            "classified": [classified_total, classified_total + unclassified_total],
        },
        "pending_checkpoint": pending or None,
    }


# ---------------------------------------------------------------------------
# Failure taxonomy (spec #68 §3) — deterministic keyword mapping, raw-glob priority
# ---------------------------------------------------------------------------

TAXONOMY_RULES: dict[str, re.Pattern[str]] = {
    "连续性断裂": re.compile(r"连续性|前后矛盾|与前文|时间线|断裂|不一致"),
    "人物漂移": re.compile(r"人物|人设|性格|语气|角色.*(不符|漂移|崩)|OOC"),
    "世界规则违反": re.compile(r"世界观|设定.*(违反|冲突)|规则|体系|灵能.*(矛盾|冲突)"),
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
RESONANCE_NAME_RE = re.compile(r"^chapter-\d+-resonance\.md$")  # _RESONANCE_NAME_RE 同语义


def merge_units(reports: list[tuple[str, str]]) -> list[FindingUnit]:
    """Same semantics as write_audit_aggregate's inlined loop (:150-171).

    (severity, text) key dedup + reporters union — without the write.
    """
    merged: dict[tuple[str, str], FindingUnit] = {}
    for name, content in reports:
        units, _ctx = extract_finding_units(name, content)
        for u in units:
            key = (u.severity, u.text)
            if key in merged:
                prev = merged[key]
                merged[key] = FindingUnit(
                    u.severity,
                    u.text,
                    tuple(dict.fromkeys([*prev.reporters, *u.reporters])),
                )
            else:
                merged[key] = u
    return list(merged.values())


def _parse_aggregate_sections(content: str) -> list[FindingUnit]:
    """Parse the aggregate render format into finding units.

    Sections are `## <SEV> Findings (n)` H2 blocks with severity-stripped
    bullets (extract_finding_units returns zero on this format). Breaks at
    the FIRST non-severity H2 — verbatim resonance bodies may contain their
    own `## ` lines that would re-arm severity.
    """
    units: list[FindingUnit] = []
    sev: str | None = None
    for line in content.splitlines():
        m = re.match(r"^## (BLOCKING|CRITICAL|WARNING|ERROR) Findings", line)
        if m:
            sev = m.group(1)
            continue
        if line.startswith("## "):
            break  # Resonance 报告/报告上下文等非 severity 分节：终止解析
        s = line.strip()
        if sev and s.startswith("- ") and not s.startswith("- 报告方"):
            units.append(FindingUnit(sev, s.lstrip("- ").strip(), ("aggregate",)))
    return units


def load_audit_units(project_dir: Path, chapter: int) -> tuple[list[FindingUnit], str]:
    """Load audit findings for one chapter.

    Raw reviewer glob first (resonance reports excluded), aggregate only as
    empty-glob fallback.
    """
    audits = project_dir / "audits"
    raw = (
        sorted(
            p
            for p in audits.glob(f"chapter-{chapter}-*.md")
            if RAW_GLOB_RE.match(p.name) and not RESONANCE_NAME_RE.match(p.name)
        )
        if audits.is_dir()
        else []
    )
    if raw:
        return merge_units([(p.name, p.read_text(encoding="utf-8")) for p in raw]), "raw"
    agg = audits / f"chapter-{chapter}.aggregate.md"
    if agg.exists():
        return _parse_aggregate_sections(agg.read_text(encoding="utf-8")), "aggregate"
    return [], "none"


def classify(units: list[FindingUnit]) -> tuple[dict[str, int], int]:
    """Map finding texts to categories (first-match v1); count unclassified."""
    counts = dict.fromkeys(TAXONOMY_RULES, 0)
    unclassified = 0
    for u in units:
        hits = [cat for cat, pat in TAXONOMY_RULES.items() if pat.search(u.text)]
        if hits:
            counts[hits[0]] += 1  # first-match v1 (rule order = priority)
        else:
            unclassified += 1
    return counts, unclassified


def ledger_stats(
    project_dir: Path, chapters: list[int], cjk_by_ch: dict[int, int]
) -> dict[str, Any]:
    """Per-chapter cost/wall-clock/attempts from cost/token-ledger.jsonl.

    skipped_rows = non-blank lines minus yielded records — iter_records
    silently drops corrupt/malformed rows; intra-chapter row loss is
    invisible to chapter coverage, so it is disclosed separately.
    """
    path = project_dir / "cost" / "token-ledger.jsonl"
    per: dict[int, dict[str, Any]] = {}
    covered: set[int] = set()
    skipped = 0
    if path.exists():
        non_blank = sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())
        yielded = 0
        for rec in TokenLedger(project_dir).iter_records():
            yielded += 1
            e = per.setdefault(
                rec.chapter,
                {"cost": 0.0, "first": rec.timestamp, "last": rec.timestamp, "attempts": 0},
            )
            e["cost"] += rec.estimated_cost_usd
            e["first"] = min(e["first"], rec.timestamp)
            e["last"] = max(e["last"], rec.timestamp)
            e["attempts"] = max(e["attempts"], rec.attempt)
            covered.add(rec.chapter)
        skipped = non_blank - yielded
    covered &= set(chapters)
    out: list[dict[str, Any]] = []
    for ch in chapters:
        e = per.get(ch)
        if not e:
            continue
        cjk = cjk_by_ch.get(ch, 0)
        try:
            wall = (
                datetime.fromisoformat(e["last"]) - datetime.fromisoformat(e["first"])
            ).total_seconds()
        except (ValueError, TypeError):
            wall = None
        out.append(
            {
                "chapter": ch,
                "cost_usd": round(e["cost"], 6),
                "wall_clock_s": wall,
                "cjk_chars": cjk,
                "cost_per_10k": round(e["cost"] / (cjk / 10000), 8) if cjk else None,
                "attempts": e["attempts"],
            }
        )
    return {"per_chapter": out, "skipped_rows": skipped, "chapters_covered": len(covered)}


def truth_growth(project_dir: Path) -> dict[str, Any]:
    """Truth-file sizes now + snapshot faces when present.

    Conditional: the automatic snapshot was removed by spec #26 path 3 —
    coverage disclosed.
    """
    truth = project_dir / "truth"
    current = (
        [{"file": p.name, "bytes": p.stat().st_size} for p in sorted(truth.glob("*.md"))]
        if truth.is_dir()
        else []
    )
    snaps = project_dir / "snapshots"
    snapshot_files = (
        [
            {"snapshot": str(p.relative_to(project_dir)), "bytes": p.stat().st_size}
            for p in sorted(snaps.rglob("truth/*.md"))[:200]
        ]
        if snaps.is_dir()
        else []
    )
    note = (
        "逐章历史快照由条件技能步骤写，不保证逐章落盘（spec #26 path 3）——按实际存在面输出"
        if not snapshot_files
        else f"快照面覆盖 {len(snapshot_files)} 个 truth 文件"
    )
    return {"current": current, "snapshots": snapshot_files, "note": note}
