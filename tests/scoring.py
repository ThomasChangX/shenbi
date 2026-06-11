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


def load_applicability(rubric_path):
    """Parse rubric.md to extract dimension applicability by test type."""
    applicability = {}
    in_applicability = False
    header_dims = []
    with open(rubric_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("## Dimension Applicability"):
                in_applicability = True
                continue
            if in_applicability and stripped.startswith("## "):
                in_applicability = False
            if in_applicability and stripped.startswith("|"):
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if len(cells) >= 4 and cells[0] == "Dimension scope":
                    header_dims = cells[1:]
                elif len(cells) >= 4 and not cells[0].startswith("---"):
                    dim_scope = cells[0]
                    for i, test_type in enumerate(header_dims):
                        if test_type not in applicability:
                            applicability[test_type] = {}
                        cell_val = cells[i + 1] if i + 1 < len(cells) else "Yes"
                        applicability[test_type][dim_scope] = cell_val.strip().lower().startswith("no") is False
    return applicability


def filter_dimensions_by_test_type(dimensions, rubric_path, test_type):
    """Remove dimensions not applicable to the given test type.

    Strategy: Build an exclusion set of dimension numbers from rows
    where the cell value starts with "No". Then filter those dimensions
    out and renormalize weights.
    """
    import re
    if not test_type:
        return dimensions
    applicability = load_applicability(rubric_path)
    if not applicability:
        return dimensions
    type_key = test_type
    if type_key not in applicability:
        type_key = test_type.capitalize()
    if type_key not in applicability:
        type_key = test_type.lower()
    if type_key not in applicability:
        return dimensions
    applicable_scopes = applicability[type_key]
    excluded_nums = set()
    for scope, applies in applicable_scopes.items():
        if not applies:
            nums = re.findall(r'dim\s+(\d+)', scope, re.IGNORECASE)
            excluded_nums.update(int(n) for n in nums)
            scope_nums = re.findall(r'#?(\d+)', scope)
            excluded_nums.update(int(n) for n in scope_nums if int(n) <= 20)
    if not excluded_nums:
        return dimensions
    filtered = [d for d in dimensions if d["num"] not in excluded_nums]
    return filtered if filtered else dimensions


def compute_score(dimensions, scores, kill_switch_triggered=False):
    """Compute weighted score from dimension scores. Kill switch overrides to 0."""
    if kill_switch_triggered:
        return 0
    total_weight = sum(d["weight"] for d in dimensions)
    if total_weight == 0:
        return 0
    if total_weight != 100:
        print(f"WARNING: total dimension weight is {total_weight}% (expected 100%)", file=sys.stderr)
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
    if len(sys.argv) < 3 and "--gate-only" not in sys.argv:
        print("Usage: scoring.py <rubric.md> <scores.json> [--kill-switch] [--test-type bug-hunt|clean|generative]")
        print("  scores.json format: {\"1\": 100, \"2\": 95, \"3\": 80, ...}")
        print("  --kill-switch: force final score to 0 (any kill switch triggered)")
        print("  --test-type: filter dimensions by applicability (renormalizes weights)")
        print("  --tier T1|T2|T3 --phase <name>: enable gate checks before scoring")
        print("  --gate-only <GATE> --files <f1,f2>: run gate check only, no scoring")
        print("  Or: scoring.py <rubric.md> --interactive")
        sys.exit(1)

    # --gate-only mode: run gate check, skip scoring entirely
    if "--gate-only" in sys.argv:
        import subprocess
        gate_type = sys.argv[sys.argv.index("--gate-only") + 1] if len(sys.argv) > sys.argv.index("--gate-only") + 1 else "G2"
        files = sys.argv[sys.argv.index("--files") + 1].split(",") if "--files" in sys.argv else []
        ftype = sys.argv[sys.argv.index("--type") + 1] if "--type" in sys.argv else "chapter"
        vg = str(Path(__file__).parent / "validate-gate.py")
        result = subprocess.run([sys.executable, vg, gate_type, ",".join(files), ftype],
                               capture_output=True, text=True)
        print(result.stdout)
        sys.exit(0 if result.returncode == 0 else 1)

    rubric_path = sys.argv[1]
    dimensions, kill_switches = load_rubric(rubric_path)

    kill_switch_triggered = "--kill-switch" in sys.argv
    test_type = None
    tier = None
    phase = None
    for i, arg in enumerate(sys.argv):
        if arg == "--test-type" and i + 1 < len(sys.argv):
            test_type = sys.argv[i + 1]
        if arg == "--tier" and i + 1 < len(sys.argv):
            tier = sys.argv[i + 1]
        if arg == "--phase" and i + 1 < len(sys.argv):
            phase = sys.argv[i + 1]

    # Gate integration: run pre-scoring dependency checks
    if tier:
        import subprocess
        vg = str(Path(__file__).parent / "validate-gate.py")
        if tier == "T1" and test_type:
            # G3: prerequisite check — extract skill_name from rubric path
            rubric_p = Path(rubric_path)
            skill_name = rubric_p.parent.name if rubric_p.parent.parent.name == "t1-skill" else None
            if skill_name:
                # Derive round_dir from rubric path or accept as flag
                round_dir = None
                for j, a in enumerate(sys.argv):
                    if a == "--round-dir" and j + 1 < len(sys.argv):
                        round_dir = sys.argv[j + 1]
                if round_dir:
                    result = subprocess.run([sys.executable, vg, "G3", skill_name, test_type, round_dir],
                                           capture_output=True, text=True)
                    try:
                        gate_out = json.loads(result.stdout)
                        if gate_out.get("status") == "FAIL":
                            print(json.dumps(gate_out, indent=2, ensure_ascii=False))
                            sys.exit(1)
                    except: pass

    if test_type:
        dimensions = filter_dimensions_by_test_type(dimensions, rubric_path, test_type)

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
