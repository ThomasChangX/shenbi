#!/usr/bin/env python3
"""Score a test report against its rubric. Output structured JSON."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

from shenbi.cli_utils import emit_json
from shenbi.logging import configure_logging, get_logger
from shenbi.status import ScoreClassification, ScoringStatus

log = get_logger(__name__)


class Dimension(TypedDict):
    """A single rubric dimension with number, name, and weight percentage."""

    num: int
    name: str
    weight: int


def load_rubric(rubric_path: str) -> tuple[list[Dimension], list[str]]:
    """Parse rubric.md to extract dimensions with weights and kill switches."""
    dimensions: list[Dimension] = []
    kill_switches: list[str] = []
    in_table = False
    in_kill_switch = False
    with open(rubric_path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("## Kill Switches") or stripped.startswith("## Kill Switch"):
                in_kill_switch = True
                in_table = False
                continue
            # Only exit kill-switch section on a new ## (h2) heading, not ### (h3) sub-sections.
            # h3 sub-sections like "### Bug-Hunt Kill Switches" contain the actual kill switch items.
            if stripped.startswith("## ") and not stripped.startswith("### ") and in_kill_switch:
                in_kill_switch = False
            if in_kill_switch and (
                "total score = 0" in stripped.lower()
                or "phase = 0" in stripped.lower()
                or "pipeline = 0" in stripped.lower()
            ):
                ks_text = stripped.lstrip("- ").rstrip()
                if ks_text not in kill_switches:
                    kill_switches.append(ks_text)
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
                    dimensions.append(
                        {
                            "num": int(cells[0]),
                            "name": cells[1],
                            "weight": weight,
                        }
                    )
            elif in_table and not stripped.startswith("|"):
                in_table = False
    return dimensions, kill_switches


def load_applicability(rubric_path: str) -> dict[str, dict[str, bool]]:
    """Parse rubric.md to extract dimension applicability by test type."""
    applicability: dict[str, dict[str, bool]] = {}
    in_applicability = False
    header_dims = []
    with open(rubric_path, encoding="utf-8") as f:
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
                        applicability[test_type][dim_scope] = (
                            cell_val.strip().lower().startswith("no") is False
                        )
    return applicability


def filter_dimensions_by_test_type(
    dimensions: list[Dimension], rubric_path: str, test_type: str | None
) -> list[Dimension]:
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
    excluded_nums: set[int] = set()
    for scope, applies in applicable_scopes.items():
        if not applies:
            nums = re.findall(r"dim\s+(\d+)", scope, re.IGNORECASE)
            excluded_nums.update(int(n) for n in nums)
            scope_nums = re.findall(r"#?(\d+)", scope)
            excluded_nums.update(int(n) for n in scope_nums if int(n) <= 20)
    if not excluded_nums:
        return dimensions
    filtered = [d for d in dimensions if d["num"] not in excluded_nums]
    return filtered if filtered else dimensions


def validate_scores(scores: dict[int, Any], dimensions: list[Dimension]) -> tuple[bool, list[str]]:
    """Validate scores against rubric dimensions. Returns (is_valid, errors)."""
    errors: list[str] = []
    if not scores:
        errors.append("REJECT: scores is empty — no dimensions scored")
        return False, errors
    expected_nums = {d["num"] for d in dimensions}
    actual_nums = set(scores.keys())
    missing = expected_nums - actual_nums
    extra = actual_nums - expected_nums
    if missing:
        errors.append(f"REJECT: missing dimension scores: {sorted(missing)}")
    if extra:
        errors.append(f"WARNING: unexpected dimension keys (ignored): {sorted(extra)}")
    for num, score in scores.items():
        if not isinstance(score, (int, float)):
            errors.append(f"REJECT: dimension {num} score is not a number: {score}")
        elif score < 0 or score > 100:
            errors.append(f"REJECT: dimension {num} score {score} out of range 0-100")
    is_valid = not any(e.startswith(ScoringStatus.REJECT.value) for e in errors)
    return is_valid, errors


def compute_score(
    dimensions: list[Dimension], scores: dict[int, Any], kill_switch_triggered: bool = False
) -> float:
    """Compute weighted score from dimension scores. Kill switch overrides to 0."""
    if kill_switch_triggered:
        return 0
    total_weight = sum(d["weight"] for d in dimensions)
    if total_weight == 0:
        return 0
    if total_weight != 100:
        log.warning("weight_mismatch", total_weight=total_weight, expected=100)
    weighted_sum: float = sum(float(scores.get(d["num"], 0)) * d["weight"] for d in dimensions)
    return round(weighted_sum / total_weight, 2)


def classify(score: float | int) -> ScoreClassification:
    if score >= 90:
        return ScoreClassification.PASS_EXCELLENT
    if score >= 75:
        return ScoreClassification.PASS_ACCEPTABLE
    if score >= 60:
        return ScoreClassification.CONDITIONAL
    return ScoreClassification.FAIL


def check_gate_markers(rubric_path: str, test_type: str | None, round_dir: str | None) -> list[str]:
    """Verify required gate markers exist. Returns list of missing marker descriptions."""
    if not round_dir:
        return []
    rd = Path(round_dir)
    marker_dir = rd / "gate-markers"
    rubric_p = Path(rubric_path)
    missing: list[str] = []

    if "t1-skill" in rubric_p.parts:
        idx = rubric_p.parts.index("t1-skill")
        skill_name = rubric_p.parts[idx + 1] if idx + 1 < len(rubric_p.parts) else None
        if skill_name:
            marker_file = marker_dir / f"G4-{skill_name}-{test_type}.json"
            if not marker_file.exists():
                missing.append(f"G4-{skill_name}-{test_type}")

    elif "t2-phase" in rubric_p.parts:
        deps_path = Path(__file__).resolve().parents[2] / "tests" / "tiers" / "deps.json"
        if deps_path.exists():
            deps = json.loads(deps_path.read_text(encoding="utf-8"))
            idx = rubric_p.parts.index("t2-phase")
            phase_name = rubric_p.parts[idx + 1] if idx + 1 < len(rubric_p.parts) else None
            if phase_name and phase_name in deps.get("t2-phases", {}):
                for skill in deps["t2-phases"][phase_name].get("prerequisites", []):
                    marker_file = marker_dir / f"G4-{skill}-generative.json"
                    if not marker_file.exists():
                        missing.append(f"G4-{skill}-generative")

    elif "t3-pipeline" in rubric_p.parts:
        idx = rubric_p.parts.index("t3-pipeline")
        pipeline_name = rubric_p.parts[idx + 1] if idx + 1 < len(rubric_p.parts) else None
        if pipeline_name:
            marker_file = marker_dir / f"G6-{pipeline_name}-{test_type}.json"
            if not marker_file.exists():
                missing.append(f"G6-{pipeline_name}-{test_type}")

    return missing


def main() -> dict[str, Any]:
    configure_logging()
    if len(sys.argv) < 3 and "--gate-only" not in sys.argv:
        usage = """Usage: scoring.py <rubric.md> <scores.json> [--kill-switch] [--test-type bug-hunt|clean|generative]
  scores.json format: {"1": 100, "2": 95, "3": 80, ...}
  --kill-switch: force final score to 0 (any kill switch triggered)
  --test-type: filter dimensions by applicability (renormalizes weights)
  --tier T1|T2|T3 --phase <name>: enable gate checks before scoring
  --gate-only <GATE> --files <f1,f2>: run gate check only, no scoring
  Or: scoring.py <rubric.md> --interactive"""
        log.info("usage", message=usage)
        sys.exit(1)

    # --gate-only mode: run gate check, skip scoring entirely
    if "--gate-only" in sys.argv:
        import subprocess

        idx = sys.argv.index("--gate-only")
        gate_type = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "G2"
        idx = sys.argv.index("--files") if "--files" in sys.argv else -1
        files = sys.argv[idx + 1].split(",") if idx >= 0 and idx + 1 < len(sys.argv) else []
        ftype = sys.argv[sys.argv.index("--type") + 1] if "--type" in sys.argv else "chapter"
        vg = str(Path(__file__).resolve().parents[2] / "tests" / "validate-gate.py")
        proc_result = subprocess.run(
            [sys.executable, vg, gate_type, ",".join(files), ftype], capture_output=True, text=True
        )
        emit_json(json.loads(proc_result.stdout))
        sys.exit(0 if proc_result.returncode == 0 else 1)

    rubric_path = sys.argv[1]
    dimensions, kill_switches = load_rubric(rubric_path)

    kill_switch_triggered = "--kill-switch" in sys.argv
    test_type = None
    tier = None
    _phase = None
    round_dir = None
    for i, arg in enumerate(sys.argv):
        if arg == "--test-type" and i + 1 < len(sys.argv):
            test_type = sys.argv[i + 1]
        if arg == "--round-dir" and i + 1 < len(sys.argv):
            round_dir = sys.argv[i + 1]
        if arg == "--tier" and i + 1 < len(sys.argv):
            tier = sys.argv[i + 1]
        if arg == "--phase" and i + 1 < len(sys.argv):
            _phase = sys.argv[i + 1]

    # Gate integration: run pre-scoring dependency checks
    if tier:
        import subprocess

        vg = str(Path(__file__).resolve().parents[2] / "tests" / "validate-gate.py")
        if tier == "T1" and test_type:
            # G3: prerequisite check — extract skill_name from rubric path
            rubric_p = Path(rubric_path)
            skill_name = rubric_p.parent.name if rubric_p.parent.parent.name == "t1-skill" else None
            if skill_name:
                if round_dir:
                    gate_result = subprocess.run(
                        [sys.executable, vg, "G3", skill_name, test_type, round_dir],
                        capture_output=True,
                        text=True,
                    )
                    try:
                        gate_out = json.loads(gate_result.stdout)
                        if gate_out.get("status") == "FAIL":
                            emit_json(gate_out)
                            sys.exit(1)
                    except Exception:
                        pass

    # Gate marker enforcement — MUST pass before scoring can proceed
    if test_type:
        dimensions = filter_dimensions_by_test_type(dimensions, rubric_path, test_type)
        if round_dir:
            missing = check_gate_markers(rubric_path, test_type, round_dir)
            if missing:
                err = {
                    "status": ScoringStatus.MARKER_MISSING,
                    "missing_markers": missing,
                    "message": f"Required gate markers not found: {', '.join(missing)}. "
                    f"Run gates (G4/G6) with --round-dir before scoring.",
                }
                emit_json(err)
                sys.exit(3)

    if sys.argv[2] == "--interactive":
        scores = {}
        log.info("scoring_start", rubric=rubric_path)
        log.info("dimensions_loaded", count=len(dimensions))
        if kill_switches:
            log.info("kill_switches_count", count=len(kill_switches))
            for ks in kill_switches:
                log.info("kill_switch_item", switch=ks)
            try:
                ks_input = input("Kill switch triggered? (y/n): ").strip().lower()
                if ks_input == "y":
                    kill_switch_triggered = True
            except EOFError:
                pass
        for d in dimensions:
            while True:
                try:
                    raw_val = input(f"  {d['num']}. {d['name']} [{d['weight']}%] (0-100): ")
                    val = int(raw_val)
                    if 0 <= val <= 100:
                        scores[d["num"]] = val
                        break
                    log.info("invalid_score_range", message="Must be 0-100")
                except ValueError:
                    log.info("invalid_score_type", message="Enter a number")
                except EOFError:
                    log.info("interactive_prompt_ended", action="using_zero_for_remaining")
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
            with open(scores_file, encoding="utf-8") as f:
                raw = json.load(f)
                scores = {int(k): v for k, v in raw.items() if k.lstrip("-").isdigit()}

    # Always validate scores against rubric dimensions before computing
    is_valid, validation_errors = validate_scores(scores, dimensions)
    if not is_valid:
        err_result = {
            "status": ScoringStatus.REJECT,
            "reason": "score validation failed",
            "errors": validation_errors,
            "expected_dimensions": [{"num": d["num"], "name": d["name"]} for d in dimensions],
            "received_keys": sorted(scores.keys()) if scores else [],
        }
        emit_json(err_result)
        sys.exit(2)

    if validation_errors:
        for e in validation_errors:
            log.error("validation_error", error=str(e))

    final = compute_score(dimensions, scores, kill_switch_triggered)
    result: dict[str, Any] = {
        "_provenance": {
            "scored_by": "subagent" if "--subagent" in sys.argv else "interactive",
            "timestamp": datetime.now(UTC).isoformat(),
            "gate_markers_verified": bool(round_dir and test_type),
            "round_dir": str(round_dir) if round_dir else None,
            "scoring_tool": "scoring.py",
        },
        "dimensions": [
            {
                "num": d["num"],
                "name": d["name"],
                "weight": d["weight"],
                "score": scores.get(d["num"], 0),
            }
            for d in dimensions
        ],
        "kill_switch_triggered": kill_switch_triggered,
        "kill_switches": kill_switches,
        "final_score": final,
        "classification": classify(final),
    }

    emit_json(result)
    return result


if __name__ == "__main__":
    main()
