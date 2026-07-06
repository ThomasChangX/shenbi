"""G3: scoring readiness gate.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19).
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


import json
from pathlib import Path
from typing import Any

from shenbi.gates.g3_independence import scoring_independence_status

from shenbi.gates.shared import (
    TESTS,
    find_report,
    fail,
    jload,
    passed,
)
from shenbi.contracts.thresholds import T1_PASS


def _compute_rubric_weighted_score(data: dict[str, object], skill_name: str) -> float | None:
    """Compute weighted score from rubric for dimensions present in subagent scores.

    Tries to load the skill's T1 rubric and compute a weighted score using only
    the dimensions that the subagent actually scored. Returns None when the rubric
    is unavailable or no dimensions match (caller falls back to min() estimate).
    """
    from shenbi.gates.shared import TESTS

    rubric_path = TESTS / "tiers" / "t1-skill" / skill_name / "rubric.md"
    if not rubric_path.exists():
        return None
    try:
        from shenbi.scoring import load_rubric

        dimensions, _ = load_rubric(str(rubric_path))
        dim_scores: dict[int, float] = {}
        for k, v in data.items():
            try:
                num = int(k)
                if isinstance(v, (int, float)) and 0 <= v <= 100:
                    dim_scores[num] = float(v)
            except (ValueError, TypeError):
                pass  # non-numeric key → skip, not a dimension score
        if not dimensions or not dim_scores:
            return None
        weight_sum = 0
        weighted = 0.0
        for d in dimensions:
            d_num = d.get("num", 0)
            d_weight = d.get("weight", 0)
            if d_num in dim_scores:
                weighted += dim_scores[d_num] * d_weight
                weight_sum += d_weight
        if weight_sum == 0:
            return None
        return round(weighted / weight_sum, 2)
    except Exception:
        return None


def gate_G3(
    skill_name: str | None = None, test_type: str | None = None, round_dir: str | None = None
) -> str:
    """G3: Pre-scoring dependency check."""
    c: list[Any] = []
    mf: list[Any] = []
    rd = Path(round_dir) if round_dir else None

    if not rd or not rd.exists():
        return fail("G3", [], "scoring", ["G3.0:no_round_dir"])

    # G3.1 — Read deps.json, check prerequisite skills have t1-reports
    deps_path = TESTS / "tiers" / "deps.json"
    reports_dir = rd / "t1-reports"
    if deps_path.exists():
        try:
            deps = jload(str(deps_path))
            skill_deps: dict[str, Any] = deps.get(skill_name, {}) if skill_name else {}
            prereqs_raw = skill_deps.get("prerequisites", [])
            prereqs: list[str] = prereqs_raw if isinstance(prereqs_raw, list) else []
            for prereq in prereqs:
                rp = find_report(reports_dir, prereq, test_type)
                if not rp or not rp.exists():
                    mf.append(
                        {
                            "id": "G3.1",
                            "file": str(rp),
                            "s": "FAIL",
                            "r": f"missing t1-report for {prereq}",
                        }
                    )
                else:
                    c.append({"id": "G3.1", "file": str(rp), "s": "PASS"})
            if not prereqs:
                c.append({"id": "G3.1", "s": "SKIP", "r": "no prerequisites"})
        except (json.JSONDecodeError, OSError):
            mf.append({"id": "G3.1", "s": "FAIL", "r": "deps.json invalid"})
    else:
        c.append({"id": "G3.1", "s": "SKIP", "r": "no deps.json"})

    # G3.2 — Prerequisite scores >= threshold from acceptance.json
    accept_path = TESTS / "tiers" / "acceptance.json"
    if accept_path.exists():
        try:
            acceptance = jload(str(accept_path))
            threshold = acceptance.get("t1", T1_PASS)
            if reports_dir.exists():
                for rp in reports_dir.glob("*.json"):
                    try:
                        data = jload(str(rp))
                        score = data.get("total_score", data.get("score", 0))
                        if not isinstance(score, (int, float)) or score == 0:
                            # Try rubric-based weighted score (highest precision)
                            rubric_score = (
                                _compute_rubric_weighted_score(data, skill_name)
                                if skill_name
                                else None
                            )
                            if rubric_score is not None:
                                score = rubric_score
                                threshold = 90  # pipeline mode
                            else:
                                # Fallback: min of dimension-score entries only
                                # (numeric keys with 0..100 values, not unrelated fields)
                                dims = [
                                    float(v)
                                    for k, v in data.items()
                                    if k.isdigit()
                                    and isinstance(v, (int, float))
                                    and 0 <= float(v) <= 100
                                ]
                                score = min(dims) if dims else 0
                                threshold = 90
                        if score < threshold:
                            mf.append(
                                {
                                    "id": "G3.2",
                                    "file": rp.name,
                                    "s": "FAIL",
                                    "score": score,
                                    "threshold": threshold,
                                }
                            )
                        else:
                            c.append({"id": "G3.2", "file": rp.name, "s": "PASS", "score": score})
                    except (json.JSONDecodeError, OSError):
                        pass
        except (json.JSONDecodeError, OSError):
            c.append({"id": "G3.2", "s": "SKIP", "r": "acceptance.json invalid"})
    else:
        c.append({"id": "G3.2", "s": "SKIP", "r": "no acceptance.json"})

    # G3.3 — Output files passed G2
    pp = rd / "progress.json"
    if pp.exists():
        try:
            progress = jload(str(pp))
            if skill_name:
                skills = progress.get("skills", {})
                skill_data = skills.get(skill_name, {}) if isinstance(skills, dict) else {}
                output_files = skill_data.get("output_files", [])
            else:
                output_files = []
            if output_files and isinstance(output_files, list):
                # Derive file_type from first output file path: truth/ → truth,
                # chapters/ → chapter, otherwise use "report"
                ftype = "chapter"
                if output_files:
                    fp0 = str(output_files[0])
                    if "/truth/" in fp0 or "truth/" in fp0:
                        ftype = "truth"
                    elif (
                        "/audits/" in fp0
                        or "audits/" in fp0
                        or "/plans/" in fp0
                        or "plans/" in fp0
                        or "/outline/" in fp0
                        or "outline/" in fp0
                        or "/context/" in fp0
                        or "context/" in fp0
                    ):
                        ftype = "report"
                from shenbi.gates.g2 import gate_G2

                g2_raw = gate_G2(output_files, ftype, str(rd))
                try:
                    g2_data = json.loads(g2_raw)
                    if g2_data.get("status") == "FAIL":
                        mf.append({"id": "G3.3", "s": "FAIL", "r": "G2 check failed on outputs"})
                    else:
                        c.append({"id": "G3.3", "s": "PASS"})
                except json.JSONDecodeError:
                    mf.append({"id": "G3.3", "s": "FAIL", "r": "G2 result unparseable"})
            else:
                c.append({"id": "G3.3", "s": "SKIP", "r": "no output_files"})
        except (json.JSONDecodeError, OSError):
            mf.append({"id": "G3.3", "s": "FAIL", "r": "progress.json invalid"})
    else:
        c.append({"id": "G3.3", "s": "SKIP", "r": "no progress.json"})

    # G3.4 — Agent ID isolation: scorer != generator
    if pp.exists():
        try:
            progress = jload(str(pp))
            # Kant I2: call scoring_independence_status (single-source from pillar5)
            verdict, reason = scoring_independence_status(progress, skill_name or "")
            if verdict == "FAIL":
                mf.append({"id": "G3.4", "s": "FAIL", "r": reason})
            else:
                c.append({"id": "G3.4", "s": "PASS"})
        except (json.JSONDecodeError, OSError):
            c.append({"id": "G3.4", "s": "SKIP", "r": "progress.json invalid"})
    else:
        c.append({"id": "G3.4", "s": "SKIP", "r": "no progress.json"})

    # G3.5 — Scoring history: scorer not in prior scoring_history
    if pp.exists():
        try:
            progress = jload(str(pp))
            prior_agents = set()
            for entry in progress.get("scoring_history", []):
                if isinstance(entry, dict):
                    aid = entry.get("agent_id", "")
                elif isinstance(entry, str):
                    aid = entry
                else:
                    continue
                if aid:
                    prior_agents.add(str(aid))
            scorer = progress.get("current_scorer_agent", "")
            if scorer and str(scorer) in prior_agents:
                mf.append({"id": "G3.5", "s": "FAIL", "r": "scorer already scored"})
            else:
                c.append({"id": "G3.5", "s": "PASS", "note": f"{len(prior_agents)} prior scorers"})
        except (json.JSONDecodeError, OSError):
            c.append({"id": "G3.5", "s": "SKIP", "r": "progress.json invalid"})
    else:
        c.append({"id": "G3.5", "s": "SKIP", "r": "no progress.json"})

    if mf:
        return fail("G3", c, "scoring", [x["id"] + ":" + x.get("file", x.get("r", "")) for x in mf])
    return passed("G3", c)
