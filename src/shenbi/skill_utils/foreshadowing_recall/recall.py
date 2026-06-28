"""recall.py — deterministic overdue-hook filtering (spec §3.6).

This helper wraps the RAG recall layer's final deterministic filter.
The RAG layer (benchmarks/index/) retrieves candidate hooks by semantic
similarity; this function applies the deterministic max_distance
threshold to decide which are genuinely overdue. The threshold check
is pure arithmetic: (current_chapter - last_reinforced) > max_distance.
This keeps the final judgment deterministic regardless of embedding
fluctuations.

Hook dict schema:
    {"id": str,
     "last_reinforced": int,
     "max_distance": int,
     "state": str (optional, e.g. "PLANTED"/"RELEVANT"/"RESOLVED")}

Usage (CLI):
  python -m shenbi.skill_utils.foreshadowing_recall \\
      --hooks-json '[{"id":"H01","last_reinforced":3,"max_distance":20}]' \\
      --current-chapter 66
"""

from __future__ import annotations

import argparse
import json


def recall_overdue_hooks(hooks: list[dict], current_chapter: int) -> list[str]:
    """Return hook_ids whose silence exceeds max_distance (spec §3.6).

    Excludes RESOLVED hooks and hooks without max_distance.
    """
    overdue: list[str] = []
    for hook in hooks:
        state = hook.get("state", "PLANTED")
        if state == "RESOLVED":
            continue
        last_reinforced = hook.get("last_reinforced")
        max_distance = hook.get("max_distance")
        if last_reinforced is None or max_distance is None:
            continue
        silence = current_chapter - last_reinforced
        if silence > max_distance:
            overdue.append(hook["id"])
    return overdue


def main() -> None:
    """CLI: print overdue hook IDs as JSON."""
    parser = argparse.ArgumentParser(prog="foreshadowing_recall", description="Filter overdue hooks (spec §3.6).")
    parser.add_argument("--hooks-json", required=True, help="JSON array of hook dicts.")
    parser.add_argument("--current-chapter", type=int, required=True)
    args = parser.parse_args()
    hooks = json.loads(args.hooks_json)
    overdue = recall_overdue_hooks(hooks, args.current_chapter)
    print(json.dumps(overdue))
