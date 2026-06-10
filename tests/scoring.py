#!/usr/bin/env python3
"""Score a test report against its rubric. Output structured JSON."""

import json
import sys
from pathlib import Path


def load_rubric(rubric_path):
    """Parse rubric.md to extract dimensions with weights and kill switches."""
    dimensions = []
    kill_switches = []
    in_table = False
    in_kill_switch = False
    with open(rubric_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("## Kill Switches") or stripped.startswith("## Kill Switch"):
                in_kill_switch = True
                in_table = False
                continue
            if stripped.startswith("## ") and in_kill_switch:
                in_kill_switch = False
            if in_kill_switch and ("total score = 0" in stripped.lower() or "phase = 0" in stripped.lower() or "pipeline = 0" in stripped.lower()):
                kill_switches.append(stripped.lstrip("- ").rstrip())
            if stripped.startswith("| #") or stripped.startswith("|---"):
                in_table = True
                continue
            if in_table and stripped.startswith("|"):
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if len(cells) >= 3 and cells[0].isdigit():
                    try:
                        weight = int(cells[2].rstrip("%"))
                    except ValueError:
                        continue
                    dimensions.append({
                        "num": int(cells[0]),
                        "name": cells[1],
                        "weight": weight,
                    })
            elif in_table and not stripped.startswith("|"):
                in_table = False
    return dimensions, kill_switches


def compute_score(dimensions, scores, kill_switch_triggered=False):
    """Compute weighted score from dimension scores. Kill switch overrides to 0."""
    if kill_switch_triggered:
        return 0
    total_weight = sum(d["weight"] for d in dimensions)
    if total_weight == 0:
        return 0
    weighted_sum = sum(
        scores.get(d["num"], 0) * d["weight"] for d in dimensions
    )
    return round(weighted_sum / total_weight, 2)


def classify(score):
    if score >= 90:
        return "PASS (excellent)"
    elif score >= 75:
        return "PASS (acceptable)"
    elif score >= 60:
        return "CONDITIONAL"
    else:
        return "FAIL"


def main():
    if len(sys.argv) < 3:
        print("Usage: scoring.py <rubric.md> <scores.json> [--kill-switch]")
        print("  scores.json format: {\"1\": 100, \"2\": 95, \"3\": 80, ...}")
        print("  --kill-switch: force final score to 0 (any kill switch triggered)")
        print("  Or: scoring.py <rubric.md> --interactive")
        sys.exit(1)

    rubric_path = sys.argv[1]
    dimensions, kill_switches = load_rubric(rubric_path)

    kill_switch_triggered = "--kill-switch" in sys.argv

    if sys.argv[2] == "--interactive":
        scores = {}
        print(f"Scoring: {rubric_path}")
        print(f"Found {len(dimensions)} dimensions")
        if kill_switches:
            print(f"Kill switches ({len(kill_switches)}):")
            for ks in kill_switches:
                print(f"  - {ks}")
            print()
            try:
                ks_input = input("Kill switch triggered? (y/n): ").strip().lower()
                if ks_input == "y":
                    kill_switch_triggered = True
            except EOFError:
                pass
        print()
        for d in dimensions:
            while True:
                try:
                    val = input(f"  {d['num']}. {d['name']} [{d['weight']}%] (0-100): ")
                    val = int(val)
                    if 0 <= val <= 100:
                        scores[d["num"]] = val
                        break
                    print("    Must be 0-100")
                except ValueError:
                    print("    Enter a number")
                except EOFError:
                    print("\n    Input ended. Using 0 for remaining dimensions.")
                    break
        # Fill any missing dimensions with 0
        for d in dimensions:
            if d["num"] not in scores:
                scores[d["num"]] = 0
    else:
        scores_file = sys.argv[2]
        if scores_file == "--kill-switch":
            scores = {}
        else:
            with open(scores_file) as f:
                scores = {int(k): v for k, v in json.load(f).items()}

    final = compute_score(dimensions, scores, kill_switch_triggered)
    result = {
        "dimensions": [
            {"num": d["num"], "name": d["name"], "weight": d["weight"],
             "score": scores.get(d["num"], 0)}
            for d in dimensions
        ],
        "kill_switch_triggered": kill_switch_triggered,
        "kill_switches": kill_switches,
        "final_score": final,
        "classification": classify(final),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
