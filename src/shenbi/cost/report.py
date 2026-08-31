"""Cost report CLI (spec §3.5).

Usage: shenbi-cost report <project_dir>
Prints total cost, per-skill breakdown (% of total), per-chapter average, and
cost-per-quality-point when an average G3 score is discoverable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from shenbi.cost.ledger import TokenLedger
from shenbi.logging import get_logger

log = get_logger(__name__)


def _try_avg_g3_score(project_dir: Path) -> float | None:
    """Best-effort average G3 score from scoring files; None if unavailable."""
    # Look for a common scoring output; tolerate any layout. This is a
    # best-effort metric — never fail the report over it.
    candidates = list(project_dir.glob("**/*score*.json"))
    scores: list[float] = []
    # F511 (spec #27 T5): only explicit contract keys count — the old scan
    # averaged every numeric 0-100 value in the file (noise: weights,
    # chapter numbers, token counts that happen to fall in range).
    _SCORE_KEYS = ("final_score", "total_score", "score")
    for c in candidates:
        try:
            data = json.loads(c.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            for key in _SCORE_KEYS:
                v = data.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 100:
                    scores.append(float(v))
                    break  # one score per file — no double counting
    if not scores:
        return None
    return sum(scores) / len(scores)


def render_report(project_dir: Path | str) -> str:
    """Render the cost report as a markdown string."""
    summary = TokenLedger(project_dir).summarize()
    total = summary["total"]
    by_skill = summary["by_skill"]

    if total["calls"] == 0:
        return "# Cost Report\n\nNo token usage recorded for this project.\n"

    total_cost = total["estimated_cost_usd"]
    lines = [
        "# Cost Report",
        "",
        f"- **Total calls**: {total['calls']}",
        f"- **Total tokens**: {total['total_tokens']:,} "
        f"(prompt {total['prompt_tokens']:,} + completion {total['completion_tokens']:,})",
        f"- **Total cost**: ${total_cost:.4f}",
        "",
        "## Per-skill breakdown",
        "",
        "| Skill | Calls | Tokens | Cost | % of total |",
        "|-------|-------|--------|------|------------|",
    ]
    for skill, agg in sorted(by_skill.items(), key=lambda kv: -kv[1]["estimated_cost_usd"]):
        pct = (agg["estimated_cost_usd"] / total_cost * 100) if total_cost else 0.0
        lines.append(
            f"| {skill} | {agg['calls']} | {agg['total_tokens']:,} | "
            f"${agg['estimated_cost_usd']:.4f} | {pct:.1f}% |"
        )

    by_chapter = summary["by_chapter"]
    if by_chapter:
        ch_costs = [c["estimated_cost_usd"] for c in by_chapter.values()]
        avg = sum(ch_costs) / len(ch_costs)
        lines += [
            "",
            f"- **Per-chapter average cost**: ${avg:.4f}",
            "  - note: this equals total cost / chapter count "
            "(by-chapter buckets carry no independent signal)",
        ]

    # C10 spec #36 T5: IDE/subprocess estimate rows are lower bounds ($0
    # priced) — break them out so they never masquerade as metered totals.
    est_rows = [r for r in TokenLedger(project_dir).iter_records() if r.estimated]
    if est_rows:
        est_tokens = sum(r.total_tokens for r in est_rows)
        lines += [
            "",
            f"- **Estimated (lower-bound) rows**: {len(est_rows)} calls / "
            f"{est_tokens:,} tokens (IDE/subprocess paths; $0 priced, not in cost totals)",
        ]

    avg_score = _try_avg_g3_score(Path(project_dir))
    if avg_score and avg_score > 0:
        cpq = total_cost / avg_score
        lines.append(
            f"- **Cost per quality point**: ${cpq:.6f} (total_cost / avg_g3_score={avg_score:.1f})"
        )

    return "\n".join(lines) + "\n"


def write_report(project_dir: Path | str) -> Path | None:
    """Render + persist cost/report.md. Node-level automation (spec #36 T4):

    chapter completion and closure call this so a zero-metering incident is
    visible at node granularity instead of via manual CLI. Fail-safe — a
    report error must never break the chapter loop.
    """
    project_dir = Path(project_dir)
    out = project_dir / "cost" / "report.md"
    try:
        from shenbi.safe_write import safe_write

        safe_write(out, render_report(project_dir))
        return out
    except Exception:
        log.warning("cost_report_write_failed", project_dir=str(project_dir), exc_info=True)
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="shenbi-cost", description="Pipeline cost report.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_report = sub.add_parser("report", help="Print the cost report for a project.")
    p_report.add_argument("project_dir", type=Path)

    args = ap.parse_args(argv)  # subparsers required=True: cmd is always set (F510)
    if not args.project_dir.is_dir():
        print(f"error: project dir not found: {args.project_dir}", file=sys.stderr)
        return 2
    print(render_report(args.project_dir))
    return 0
