#!/usr/bin/env python3
"""Aggregate per-skill scores into a round summary with band breakdown."""

import json
import sys
from pathlib import Path


def classify(score):
    if score >= 90:
        return "pass_excellent"
    elif score >= 75:
        return "pass_acceptable"
    elif score >= 60:
        return "conditional"
    else:
        return "fail"


def main():
    if len(sys.argv) < 2:
        print("Usage: summarize-round.py <round-dir>")
        sys.exit(1)

    round_dir = Path(sys.argv[1])
    summary_path = round_dir / "summary.json"

    if not summary_path.exists():
        print(f"No summary.json found in {round_dir}")
        sys.exit(1)

    with open(summary_path) as f:
        summary = json.load(f)

    # Compute band breakdown from t1_scores
    t1 = summary.get("t1_scores", {})
    bands = {"pass_excellent": 0, "pass_acceptable": 0, "conditional": 0, "fail": 0}
    for skill, score in t1.items():
        bands[classify(score)] += 1

    summary["band_breakdown"] = bands
    summary["next_actions"] = []

    fail_skills = [s for s, v in t1.items() if v < 60]
    cond_skills = [s for s, v in t1.items() if 60 <= v < 75]
    acceptable_skills = [s for s, v in t1.items() if 75 <= v < 90]

    if fail_skills:
        summary["next_actions"].append(f"Fix failing skills: {', '.join(fail_skills)}")
    if cond_skills:
        summary["next_actions"].append(f"Improve conditional skills: {', '.join(cond_skills)}")
    if acceptable_skills:
        summary["next_actions"].append(f"Improve acceptable skills: {', '.join(acceptable_skills)}")
    if not fail_skills and not cond_skills and not acceptable_skills:
        summary["next_actions"].append("All T1 skills at 100. Ready for T2.")

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"Round summary updated: {bands['pass_excellent']} PASS (excellent), "
          f"{bands['pass_acceptable']} PASS (acceptable), "
          f"{bands['conditional']} CONDITIONAL, {bands['fail']} FAIL")


if __name__ == "__main__":
    main()
