"""compute_drift.py — smoothing + chapter/volume drift triggers (spec §8.3).

Deterministic helpers powering the per-chapter positive-quality scorer's
cross-chapter and cross-volume drift detection. Supports the drift-guidance
gate: a non-zero finding set blocks tier advancement until the decline is
addressed. All computation is deterministic.

Usage (CLI):
  python -m shenbi.skill_utils.drift_detection \
      --resonance truth/resonance_trend.md \
      --arc-payoff truth/arc_payoff_trend.md
  python -m shenbi.skill_utils.drift_detection ... --write-audit-drift
"""

from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

# --- trend-file column schemas (contract: SKILL.md writers <-> drift CLI) ---

RESONANCE_DIMS = ["情感落地", "场景临场感", "文笔质感", "读者回报", "overall"]
ARC_PAYOFF_DIMS = [
    "弧情感交付",
    "伏笔兑现质量",
    "线索收束",
    "期待债务结算",
    "角色弧推进",
    "overall",
]

# accepted header names for the human-override flag column
_OVERRIDE_HEADERS = {"human_overridden", "human_override", "overridden"}


class DriftKind(StrEnum):
    MONOTONIC_DECLINE = "monotonic_decline"
    BELOW_MEAN_2SIGMA = "below_mean_2sigma"
    VOLUME_DECLINE = "volume_decline"


@dataclass(frozen=True)
class DriftFinding:
    kind: DriftKind
    dim: str
    detail: str


def smooth(scores: list[float]) -> list[float]:
    """3-point moving average; 2-point at boundaries."""
    n = len(scores)
    if n == 0:
        return []
    if n == 1:
        return [scores[0]]
    out = [(scores[0] + scores[1]) / 2]
    for i in range(1, n - 1):
        out.append((scores[i - 1] + scores[i] + scores[i + 1]) / 3)
    out.append((scores[n - 2] + scores[n - 1]) / 2)
    return out


def detect_chapter_drift(
    raw: list[float],
    dim: str,
    min_samples_sigma: int = 6,
    exclude_indices: set[int] | None = None,
) -> list[DriftFinding]:
    """Spec §8.3 drift triggers for a single chapter-level dimension.

    exclude_indices = chapters flagged human_overridden (excluded from trigger
    stats so overrides do not poison detection). Two triggers:
      (a) monotonic decline >= 3 consecutive non-excluded chapters with a
          cumulative smoothed drop >= 3 points.
      (b) smoothed score below mean - 2σ for >= 2 consecutive non-excluded
          chapters (requires >= min_samples_sigma non-excluded samples).
    """
    excl = exclude_indices or set()
    s = smooth(raw)
    findings: list[DriftFinding] = []

    # (a) monotonic decline >= 3 consecutive non-excluded, cumulative >= 3
    run = 0
    start = 0
    prev: float | None = None
    for i, v in enumerate(s):
        if i in excl:
            run, start, prev = 0, i + 1, None
            continue
        if prev is not None and v < prev:
            run += 1
        else:
            run, start = 1, i
        prev = v
        if run >= 3 and (s[start] - v) >= 3:
            findings.append(
                DriftFinding(
                    DriftKind.MONOTONIC_DECLINE,
                    dim,
                    f"{dim} declined {s[start]:.1f}->{v:.1f} over chapters {start + 1}-{i + 1}",
                )
            )
            break

    # (b) below mean - 2σ over non-excluded, >= 2 consecutive non-excluded
    kept = [v for i, v in enumerate(s) if i not in excl]
    if len(kept) >= min_samples_sigma:
        mean = statistics.mean(kept)
        sd = statistics.pstdev(kept) or 1e-9
        threshold = mean - 2 * sd
        below_run = 0
        for i, v in enumerate(s):
            if i in excl:
                below_run = 0
                continue
            if v < threshold:
                below_run += 1
                if below_run >= 2:
                    findings.append(
                        DriftFinding(
                            DriftKind.BELOW_MEAN_2SIGMA,
                            dim,
                            f"{dim} < mean-2σ ({threshold:.1f}) for >=2 consecutive chapters",
                        )
                    )
                    break
            else:
                below_run = 0
    return findings


def detect_volume_drift(volume_scores: list[float]) -> list[DriftFinding]:
    """Spec §8.3: consecutive 2-volume decline in overall triggers a finding."""
    if len(volume_scores) >= 2 and volume_scores[-1] < volume_scores[-2]:
        return [
            DriftFinding(
                DriftKind.VOLUME_DECLINE,
                "overall",
                f"volume overall declined {volume_scores[-2]}->{volume_scores[-1]}",
            )
        ]
    return []


def parse_trend(path: str | Path, dims: list[str]) -> dict[str, list[tuple[float, bool]]]:
    """Parse a markdown trend table into per-dimension ``(score, excluded)`` lists.

    Maps header -> column index, then walks data rows. For each requested dim,
    collects ``(score, human_overridden)``. Rows whose dim cell is non-numeric
    (e.g. ``pending`` from a failed dispatch) are skipped for that dim — not
    coerced, not counted toward sample N. The ``human_overridden`` flag (truthy
    ``true``) marks excluded entries per spec §8.3.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    # locate the header row: first table line containing a requested dim
    header_idx = -1
    header_cells: list[str] = []
    for idx, line in enumerate(lines):
        if "|" not in line:
            continue
        cells = _split_row(line)
        if any(d in cells for d in dims):
            header_idx = idx
            header_cells = cells
            break
    if header_idx < 0:
        return {d: [] for d in dims}

    col = {name: i for i, name in enumerate(header_cells)}
    override_col = next((col[h] for h in _OVERRIDE_HEADERS if h in col), None)

    result: dict[str, list[tuple[float, bool]]] = {d: [] for d in dims}
    for line in lines[header_idx + 1 :]:
        if "|" not in line:
            continue
        cells = _split_row(line)
        if not cells:
            continue
        # skip markdown separator rows like | --- | :---: |
        if all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
            continue
        excluded = False
        if override_col is not None and override_col < len(cells):
            excluded = cells[override_col].strip().lower() == "true"
        for d in dims:
            ci = col.get(d)
            if ci is None or ci >= len(cells):
                continue
            score = _try_float(cells[ci].strip())
            if score is None:
                continue  # non-numeric (e.g. pending) — skip for this dim
            result[d].append((score, excluded))
    return result


def _split_row(line: str) -> list[str]:
    """Split a markdown table row into stripped cell values."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _try_float(text: str) -> float | None:
    """Return ``float(text)``, or None if not a finite numeric value."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _append_audit(findings: list[DriftFinding], audit_path: Path) -> None:
    """Append drift findings to the audit-trail markdown file."""
    lines = ["\n## drift findings\n\n"]
    for f in findings:
        lines.append(f"- [{f.kind.value}] {f.dim}: {f.detail}\n")
    lines.append("\n")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.writelines(lines)


def main() -> None:
    """CLI: read trend files, print DriftFindings, optionally audit + gate."""
    parser = argparse.ArgumentParser(
        prog="compute_drift",
        description="Detect cross-chapter and cross-volume resonance drift (spec §8.3).",
    )
    parser.add_argument(
        "--resonance",
        default="truth/resonance_trend.md",
        help="Path to resonance_trend.md (chapter-level scores).",
    )
    parser.add_argument(
        "--arc-payoff",
        default="truth/arc_payoff_trend.md",
        help="Path to arc_payoff_trend.md (volume-level scores).",
    )
    parser.add_argument(
        "--write-audit-drift",
        action="store_true",
        help="Append findings to truth/audit_drift.md.",
    )
    args = parser.parse_args()

    findings: list[DriftFinding] = []

    resonance_path = Path(args.resonance)
    if resonance_path.exists():
        parsed = parse_trend(resonance_path, RESONANCE_DIMS)
        for dim in RESONANCE_DIMS:
            series = parsed.get(dim, [])
            if len(series) < 2:
                continue
            raw = [score for score, _ in series]
            excl = {i for i, (_, e) in enumerate(series) if e}
            findings.extend(detect_chapter_drift(raw, dim=dim, exclude_indices=excl))

    arc_path = Path(args.arc_payoff)
    if arc_path.exists():
        parsed = parse_trend(arc_path, ARC_PAYOFF_DIMS)
        overall_series = parsed.get("overall", [])
        if len(overall_series) >= 2:
            volume_scores = [score for score, _ in overall_series]
            findings.extend(detect_volume_drift(volume_scores))

    for f in findings:
        sys.stdout.write(f"- [{f.kind.value}] {f.dim}: {f.detail}\n")

    if args.write_audit_drift and findings:
        _append_audit(findings, Path("truth/audit_drift.md"))

    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
