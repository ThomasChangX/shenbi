#!/usr/bin/env python3
"""Aggregate per-skill scores into a round summary with band breakdown."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from shenbi.logging import configure_logging, get_logger

from shenbi.safe_write import safe_write

log = get_logger(__name__)


def classify(score: float | int) -> str:
    if score >= 90:
        return "pass_excellent"
    if score >= 75:
        return "pass_acceptable"
    if score >= 60:
        return "conditional"
    return "fail"


def classify_scores(scores_dict: dict[str, int | float | dict[str, Any]]) -> dict[str, int]:
    bands = {"pass_excellent": 0, "pass_acceptable": 0, "conditional": 0, "fail": 0}
    for _name, entry in scores_dict.items():
        score = (
            entry
            if isinstance(entry, (int, float))
            else entry.get("score", entry.get("re_score", 0))
        )
        bands[classify(score)] += 1
    return bands


def below_threshold(
    scores_dict: dict[str, int | float | dict[str, Any]], threshold: float | int
) -> list[str]:
    result: list[str] = []
    for name, entry in scores_dict.items():
        score = (
            entry
            if isinstance(entry, (int, float))
            else entry.get("score", entry.get("re_score", 0))
        )
        if score < threshold:
            result.append(name)
    return result


def main() -> None:
    configure_logging()
    if len(sys.argv) < 2:
        log.info("usage", message="Usage: summarize-round.py <round-dir>")
        sys.exit(1)

    round_dir = Path(sys.argv[1])
    summary_path = round_dir / "summary.json"

    # G7: Round close validation
    vg = str(Path(__file__).resolve().parents[2] / "tests" / "validate-gate.py")
    g7_result = subprocess.run(
        [sys.executable, vg, "G7", str(round_dir)], capture_output=True, text=True
    )
    try:
        g7_out = json.loads(g7_result.stdout)
        if g7_out.get("status") == "FAIL":
            log.error("g7_failed", g7_result=g7_out)
            log.error("g7_fix_required", message="Fix G7 issues before closing round.")
            sys.exit(1)
        else:
            log.info("g7_status", status=g7_out.get("status"))
    except Exception as e:
        log.warning("g7_skipped", error=str(e))

    # Read progress.json for additional score data
    progress_path = round_dir / "progress.json"
    t1_from_progress: dict[str, dict[str, Any]] = {}
    if progress_path.exists():
        try:
            with open(progress_path, encoding="utf-8") as f:
                progress = json.load(f)
            for sn, sd in progress.get("skills", {}).items():
                for tt, td in sd.items():
                    if isinstance(td, dict) and td.get("status") == "done" and "score" in td:
                        t1_from_progress[f"{sn}-{tt}"] = {
                            "score": td["score"],
                            "band": classify(
                                td["score"] if isinstance(td["score"], (int, float)) else 0
                            ),
                        }
        except Exception:
            pass

    if not summary_path.exists():
        log.error("summary_not_found", round_dir=str(round_dir))
        sys.exit(1)

    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)

    _tier_target = summary.get("tier_target", "T1")
    next_actions: list[str] = []

    # T1 scores
    t1 = summary.get("t1_scores", {})
    if t1:
        t1_bands = classify_scores(t1)
        t1_fail = below_threshold(t1, 60)
        t1_cond = below_threshold(t1, 75)
        t1_accept = [s for s in below_threshold(t1, 90) if s not in t1_fail and s not in t1_cond]

        if t1_fail:
            next_actions.append(f"T1 FAIL: {', '.join(t1_fail)}")
        if t1_cond:
            next_actions.append(f"T1 CONDITIONAL: {', '.join(t1_cond)}")
        if t1_accept:
            next_actions.append(f"T1 PASS (acceptable, needs improvement): {', '.join(t1_accept)}")
        if not t1_fail and not t1_cond and not t1_accept:
            next_actions.append("T1: All skills PASS (excellent, 90+).")
    else:
        t1_bands = {"pass_excellent": 0, "pass_acceptable": 0, "conditional": 0, "fail": 0}

    # T2 scores
    t2 = summary.get("t2_scores", {})
    if t2:
        t2_bands = classify_scores(t2)
        t2_fail = below_threshold(t2, 60)
        t2_cond = below_threshold(t2, 75)
        t2_accept = [s for s in below_threshold(t2, 90) if s not in t2_fail and s not in t2_cond]

        if t2_fail:
            next_actions.append(f"T2 FAIL: {', '.join(t2_fail)}")
        if t2_cond:
            next_actions.append(f"T2 CONDITIONAL: {', '.join(t2_cond)}")
        if t2_accept:
            next_actions.append(f"T2 PASS (acceptable): {', '.join(t2_accept)}")
        if not t2_fail and not t2_cond and not t2_accept:
            next_actions.append("T2: All phases PASS (excellent, 90+).")
    else:
        t2_bands = None

    # T3 scores
    t3 = summary.get("t3_scores", {})
    if t3:
        t3_bands = classify_scores(t3)
        t3_fail = below_threshold(t3, 60)
        t3_cond = below_threshold(t3, 75)
        t3_accept = [s for s in below_threshold(t3, 90) if s not in t3_fail and s not in t3_cond]

        if t3_fail:
            next_actions.append(f"T3 FAIL: {', '.join(t3_fail)}")
        if t3_cond:
            next_actions.append(f"T3 CONDITIONAL: {', '.join(t3_cond)}")
        if t3_accept:
            next_actions.append(f"T3 PASS (acceptable): {', '.join(t3_accept)}")
        if not t3_fail and not t3_cond and not t3_accept:
            next_actions.append("T3: All pipelines PASS (excellent, 90+).")
    else:
        t3_bands = None

    # Tier readiness
    if t1 and not below_threshold(t1, 90) and not t2:
        next_actions.append("T1 complete. Ready for T2 phase testing.")
    if t2 and not below_threshold(t2, 90) and not t3:
        next_actions.append("T2 complete. Ready for T3 pipeline testing.")
    if t3 and not below_threshold(t3, 90):
        next_actions.append("All tiers complete. Framework validated.")

    summary["band_breakdown"] = t1_bands
    if t2_bands:
        summary["band_breakdown_t2"] = t2_bands
    if t3_bands:
        summary["band_breakdown_t3"] = t3_bands
    summary["next_actions"] = next_actions

    safe_write(summary_path, json.dumps(summary, indent=2, ensure_ascii=False))

    parts = [
        f"T1: {t1_bands['pass_excellent']}ex {t1_bands['pass_acceptable']}ok {t1_bands['conditional']}cond {t1_bands['fail']}fail"
    ]
    if t2_bands:
        parts.append(f"T2: {t2_bands['pass_excellent']}ex")
    if t3_bands:
        parts.append(f"T3: {t3_bands['pass_excellent']}ex")
    log.info("round_summary", summary=" | ".join(parts))


if __name__ == "__main__":
    main()
