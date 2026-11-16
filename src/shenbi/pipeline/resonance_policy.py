"""Dynamic resonance floor policy (spec #106).

Single module for the trailing-window P25 floor computation, the policy
normalization, and the would-route trace event. The quantile convention is
PINNED to linear interpolation (``statistics.quantiles(method="inclusive")``)
— nearest-rank yields 0 ignitions on the vol1 replay while interpolation
yields 2/24=8.3%, so any convention drift silently defangs the floor.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import quantiles
from typing import TYPE_CHECKING, Any

from shenbi.config.thresholds import DEFAULT_THRESHOLDS
from shenbi.contracts.enums import ResonancePolicyMode
from shenbi.logging import get_logger

if TYPE_CHECKING:
    from shenbi.pipeline.state import PipelineConfig

log = get_logger(__name__)

#: Clamp lower bound (spec #106 T1; sanity floor, distinct from the config floor).
_FLOOR_CLAMP_MIN = 50.0
TREND_REL = "truth/resonance_trend.md"
#: Override-header family — same semantics as compute_drift._OVERRIDE_HEADERS
#: (spec #106 reuses its exclusion filter, values compared case-insensitively).
_OVERRIDE_HEADERS = ("human_overridden", "human_override", "overridden")


@dataclass(frozen=True)
class FloorComputation:
    """The dynamic floor for one chapter plus its provenance.

    ``source``: ``"p25"`` — trailing window had enough scored rows, floor is
    the clamped P25; ``"config_fallback"`` — cold start (prior rows below the
    minimum), floor falls back to ``config.resonance_global_floor`` (the E11
    single source — never the legacy ``DEFAULT_RESONANCE_FLOOR=50``);
    ``"window_starved"`` — the fallback fired because overrides excluded
    rows, disclosed via the ``resonance_window_starved`` WARN.
    """

    floor: float
    source: str  # "p25" | "config_fallback" | "window_starved"
    window_rows: int
    overridden_in_window: int


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.split("|")[1:-1]]


def _try_float(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def _try_int(text: str) -> int | None:
    try:
        return int(text)
    except ValueError:
        return None


def scored_trend_rows(project_dir: Path | str) -> list[tuple[int, float, bool]]:
    """Parse truth/resonance_trend.md into (chapter, overall, overridden) triples.

    Semantics mirror compute_drift.parse_trend: ``pending`` / non-numeric
    overall rows are dropped; ``human_overridden`` rows are KEPT with their
    flag so the floor can exclude them (chapter ids retained — the window is
    chapter-ordered, not file-ordered).
    """
    path = Path(project_dir) / TREND_REL
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    header_idx, header_cells = -1, []
    for idx, line in enumerate(lines):
        if "|" not in line:
            continue
        cells = _split_row(line)
        if "chapter" in cells and "overall" in cells:
            header_idx, header_cells = idx, cells
            break
    if header_idx < 0:
        return []
    col = {name: i for i, name in enumerate(header_cells)}
    overall_col = col["overall"]
    override_col = next((col[h] for h in _OVERRIDE_HEADERS if h in col), None)
    rows: list[tuple[int, float, bool]] = []
    for line in lines[header_idx + 1 :]:
        if "|" not in line:
            continue
        cells = _split_row(line)
        if not cells or all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
            continue
        ch = _try_int(cells[0]) if cells else None
        if ch is None or overall_col >= len(cells):
            continue
        overall = _try_float(cells[overall_col])
        if overall is None:
            continue  # pending / non-numeric — not a scored row
        overridden = False
        if override_col is not None and override_col < len(cells):
            overridden = cells[override_col].strip().lower() == "true"
        rows.append((ch, overall, overridden))
    return rows


def resonance_policy_of(config: PipelineConfig) -> dict[str, Any]:
    """Normalize ``config.resonance_policy`` against QualityThresholds defaults.

    An absent, partial, or invalid-value dict yields the safe defaults; an
    invalid ``mode`` degrades to SHADOW with a WARN (never armed by accident).
    """
    # Any at the guard seam: runtime JSON round-trips can violate the
    # dataclass annotation (hand-edited state.json) — never crash routing.
    raw: Any = config.resonance_policy
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        log.warning("resonance_policy_invalid_type", value=repr(raw), fallback="defaults")
        raw = {}
    mode: ResonancePolicyMode
    raw_mode = raw.get("mode", ResonancePolicyMode.SHADOW.value)
    try:
        mode = ResonancePolicyMode(raw_mode)
    except ValueError:
        log.warning("resonance_policy_mode_invalid", value=repr(raw_mode), fallback="shadow")
        mode = ResonancePolicyMode.SHADOW
    percentile = raw.get("percentile", DEFAULT_THRESHOLDS.resonance_floor_percentile)
    if isinstance(percentile, bool) or not isinstance(percentile, int) or not 1 <= percentile <= 99:
        log.warning("resonance_policy_percentile_invalid", value=repr(percentile), fallback=25)
        percentile = DEFAULT_THRESHOLDS.resonance_floor_percentile
    return {
        "mode": mode,
        "percentile": percentile,
        "window": raw.get("window", DEFAULT_THRESHOLDS.resonance_floor_window),
        "cap": raw.get("cap", DEFAULT_THRESHOLDS.resonance_floor_cap),
    }


def effective_resonance_floor(
    project_dir: Path | str, chapter: int, config: PipelineConfig
) -> FloorComputation:
    """Compute the dynamic floor for *chapter* (spec #106 T1).

    Window = PRIOR scored rows only (chapter id < *chapter*), human_overridden
    rows excluded (compute_drift filter semantics), trailing ``window`` of
    them. Fewer than ``resonance_floor_cold_start_min`` eligible rows → fall
    back to ``config.resonance_global_floor`` (the E11 single source — never
    ``DEFAULT_RESONANCE_FLOOR=50``); when the shortfall is caused by override
    exclusion, disclose via ``resonance_window_starved`` WARN.
    """
    policy = resonance_policy_of(config)
    window_size = int(policy["window"])
    cap = float(policy["cap"])
    percentile = int(policy["percentile"])
    prior = [(ch, s, ov) for ch, s, ov in scored_trend_rows(project_dir) if ch < chapter]
    # chapter-ordered by sort, not by file order (backfill can insert rows
    # out of sequence) — audit-T1 M4.
    eligible = sorted(((ch, s) for ch, s, ov in prior if not ov))
    overridden_in_window = sum(1 for _, _, ov in prior[-window_size:] if ov)
    fallback = float(config.resonance_global_floor)
    if len(eligible) < DEFAULT_THRESHOLDS.resonance_floor_cold_start_min:
        if len(prior) >= DEFAULT_THRESHOLDS.resonance_floor_cold_start_min:
            log.warning(
                "resonance_window_starved",
                chapter=chapter,
                window_rows=len(eligible),
                overridden_in_window=overridden_in_window,
            )
            return FloorComputation(fallback, "window_starved", len(eligible), overridden_in_window)
        return FloorComputation(fallback, "config_fallback", len(eligible), overridden_in_window)
    window_vals = [s for _, s in eligible[-window_size:]]
    # percentile consumed (audit-T1 I-2): quantiles(n=100, inclusive)[p-1] is
    # the same linear-interpolation math as the pinned n=4 P25 at p=25.
    p = quantiles(window_vals, n=100, method="inclusive")[percentile - 1]
    floor = min(cap, max(_FLOOR_CLAMP_MIN, p))
    return FloorComputation(float(floor), "p25", len(window_vals), overridden_in_window)


def emit_resonance_would_route_trace(
    project_dir: Path | str, chapter: int, payload: dict[str, Any]
) -> None:
    """Append-only trace event for would-route decisions (spec #106 T2).

    Fire-and-forget via the #81 trace face: a trace-side failure must never
    block the loop (shape copied from gates/g4/shadow.emit_shadow_warn_trace).
    """
    import structlog

    trace_log = structlog.get_logger("shenbi.pipeline.resonance_policy")
    try:
        from shenbi.trace.writer import TraceWriter

        TraceWriter(Path(project_dir)).append(
            actor="chapter-loop",
            actor_role="SYSTEM",
            action="WARN",
            target=f"ch{chapter}",
            gate="resonance",
            payload={
                "chapter": chapter,
                "floor": payload.get("floor"),
                "score": payload.get("score"),
                "reason": payload.get("reason"),
                "would_route": payload.get("would_route"),
            },
        )
    except Exception:  # noqa: BLE001 -- observability must not break the loop
        trace_log.warning("resonance_trace_emit_failed", chapter=chapter)


def resonance_cap_confirm_escalate(
    project_dir: Path | str, chapter: int, floor: float
) -> bool | None:
    """Armed cap 护栏(spec #106 T1). 重派前先把首份 below 报告复制为
    ``audits/chapter-N-resonance-first.md``(重派会覆写原报告——升级审阅须见双报告), 再重派 review-resonance 解析新分. True=两次均 below(升级); False=复评 >=floor(pass); None=派发失败(保守升级——噪声成本 < 漏放行).
    真实派发为付费调用——仅 armed 生产路径触达; 测试 monkeypatch
    ``shenbi.pipeline.dispatch_helper.dispatch_skill``(本函数函数级局部 import).
    """
    from shenbi.safe_write import safe_write

    # 函数级局部 import（F947：monkeypatch 源模块属性即生效）
    from shenbi.pipeline.chapter_loop import parse_resonance_score
    from shenbi.pipeline.dispatch_helper import dispatch_skill

    project_dir = Path(project_dir)
    report = project_dir / "audits" / f"chapter-{chapter}-resonance.md"
    if report.exists():
        # evidence copy routed through safe_write (atomic), mirroring the
        # _create_pre_revision_backup precedent — purity lint forbids raw copy2.
        safe_write(
            project_dir / "audits" / f"chapter-{chapter}-resonance-first.md",
            report.read_bytes(),
        )
    result = dispatch_skill(
        "shenbi-review-resonance",
        project_dir,
        f"Re-evaluate chapter {chapter} resonance (cap guard).",
    )
    if not result.success:
        return None
    fresh = parse_resonance_score(report)
    if fresh is None:
        return None
    return fresh < floor
