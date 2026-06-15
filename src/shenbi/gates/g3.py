"""G3: scoring readiness gate.

Extracted from tests/validate-gate.py in PR-19 (P-1.E).
"""

import json
from pathlib import Path
from typing import Any

from shenbi.gates.shared import (  # noqa: F401
    ALL_SKILLS,
    CHAPTER_WORD_CEILING,
    CHAPTER_WORD_FLOOR,
    FATIGUE_BASE,
    FIXTURES,
    G4_CHECKER_SKILLS,
    META_NARRATIVE,
    PROJECT,
    SKILLS,
    TESTS,
    TRANSITION_SPECIFIC,
    _find_report,
    _normalize_file_paths,
    count_transition_words,
    fail,
    jload,
    passed,
    read_genre_config,
    unimplemented,
    word_count_md,
    write_gate_marker,
    yload,
)


def gate_G3(skill_name: str | None = None, test_type: str | None = None, round_dir: str | None = None) -> str:
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
            if isinstance(deps, dict):
                skill_deps = deps.get(skill_name, {}) if skill_name else {}
                prereqs = (
                    skill_deps.get("prerequisites", []) if isinstance(skill_deps, dict) else []
                )
                if not isinstance(prereqs, list):
                    prereqs = []
                for prereq in prereqs:
                    rp = _find_report(reports_dir, prereq, test_type)
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
            threshold = acceptance.get("t1", 94)
            if reports_dir.exists():
                for rp in reports_dir.glob("*.json"):
                    try:
                        data = jload(str(rp))
                        score = data.get("total_score", data.get("score", 0))
                        if not isinstance(score, (int, float)):
                            score = 0
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
            agent_trace = progress.get("agent_trace", {})
            gen_agent = (
                agent_trace.get(skill_name)
                if isinstance(agent_trace, dict) and skill_name
                else None
            )
            scorer_agent = progress.get("current_scorer_agent")
            if gen_agent and scorer_agent and str(gen_agent) == str(scorer_agent):
                mf.append({"id": "G3.4", "s": "FAIL", "r": "scorer agent same as generator"})
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
