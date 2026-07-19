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


def _try_avg_g3_score(project_dir: Path) -> float | None:
    """Best-effort average G3 score from scoring files; None if unavailable."""
    # Look for a common scoring output; tolerate any layout. This is a
    # best-effort metric — never fail the report over it.
    candidates = list(project_dir.glob("**/*score*.json"))
    scores: list[float] = []
    for c in candidates:
        try:
            data = json.loads(c.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, (int, float)) and 0 <= v <= 100:
                    scores.append(float(v))
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
        lines += ["", f"- **Per-chapter average cost**: ${avg:.4f}"]

    avg_score = _try_avg_g3_score(Path(project_dir))
    if avg_score and avg_score > 0:
        cpq = total_cost / avg_score
        lines.append(
            f"- **Cost per quality point**: ${cpq:.6f} (total_cost / avg_g3_score={avg_score:.1f})"
        )

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="shenbi-cost", description="Pipeline cost report.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_report = sub.add_parser("report", help="Print the cost report for a project.")
    p_report.add_argument("project_dir", type=Path)

    args = ap.parse_args(argv)
    if args.cmd == "report":
        if not args.project_dir.is_dir():
            print(f"error: project dir not found: {args.project_dir}", file=sys.stderr)
            return 2
        print(render_report(args.project_dir))
        return 0
    return 2
