"""G3: scoring readiness gate.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19).
"""

from shenbi.status import GateStatus

from shenbi.logging import get_logger

log = get_logger(__name__)


import json
from pathlib import Path
from typing import Any

from shenbi.gates.g3_independence import scoring_independence_status

from shenbi.gates.shared import (
    TESTS,
    fail,
    jload,
    passed,
)
from collections.abc import Mapping

from shenbi.contracts.thresholds import T1_PASS, TEST_PASS


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


def _extract_score_fields(data: Mapping[str, object]) -> tuple[float | None, dict[int, float]]:
    """Extract (top-level score, flat dimension scores) from any producer shape.

    Canonical scoring.py output uses ``final_score`` + nested ``dimensions``
    list; legacy/codex shapes use ``total_score``/``score`` + flat numeric
    keys. Both must work (F130, spec #27).
    """
    score: float | None = None
    for key in ("final_score", "total_score", "score"):
        v = data.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            score = float(v)
            break
    dims: dict[int, float] = {}
    nested = data.get("dimensions")
    if isinstance(nested, list):
        for d in nested:
            if isinstance(d, dict):
                num, val = d.get("num"), d.get("score")
                if (
                    isinstance(num, int)
                    and isinstance(val, (int, float))
                    and 0 <= float(val) <= 100
                ):
                    dims[num] = float(val)
    for k, v in data.items():
        if (
            k.isdigit()
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and 0 <= float(v) <= 100
        ):
            dims.setdefault(int(k), float(v))
    return score, dims


def gate_G3(
    skill_name: str | None = None, test_type: str | None = None, round_dir: str | None = None
) -> str:
    """G3: Pre-scoring dependency check."""
    c: list[Any] = []
    mf: list[Any] = []
    rd = Path(round_dir) if round_dir else None

    if not rd or not rd.exists():
        return fail("G3", [], "scoring", ["G3.0:no_round_dir"])

    # G3.1 — Per-skill prerequisite report check.
    # D19: deps.json never stored per-skill prerequisite data (its top-level
    # keys are phase/pipeline rosters: t2-phases, t3-pipelines, ...), so the
    # old deps.get(skill_name) query was a dead function that always SKIPped
    # via "no prerequisites". The readiness check is fully covered by G3.2
    # (score thresholds). Explicit SKIP documents the modelling decision.
    reports_dir = rd / "t1-reports"
    c.append(
        {
            "id": "G3.1",
            "s": GateStatus.SKIP,
            "r": "per-skill prerequisites not modeled (G3.2 covers readiness)",
        }
    )

    # G3.2 — Prerequisite scores >= threshold from acceptance.json
    accept_path = TESTS / "tiers" / "acceptance.json"
    if accept_path.exists():
        try:
            acceptance = jload(str(accept_path))
            threshold = acceptance.get("t1", T1_PASS)
            if reports_dir.exists():
                for rp in reports_dir.glob("*.json"):
                    # spec #31: sidecar artifacts (collapse-check, dual-scorer
                    # second scores) are not readiness score reports — G3.2
                    # must only judge primary score files, else a legitimate
                    # collapse-check.json (no score fields → score 0) fails
                    # the very rounds this gate protects. Blacklist (not a
                    # -scores whitelist) keeps legacy unsuffixed report names
                    # (find_report's accepted variants) in scope.
                    if rp.name.endswith(("-collapse-check.json", "-scores-subagent-2.json")):
                        continue
                    try:
                        data = jload(str(rp))
                        top_score, flat_dims = _extract_score_fields(data)
                        score = top_score if top_score is not None else 0
                        has_top_score = top_score is not None
                        if not has_top_score:
                            # Try rubric-based weighted score (highest precision)
                            rubric_score = (
                                _compute_rubric_weighted_score(data, skill_name)
                                if skill_name
                                else None
                            )
                            if rubric_score is not None:
                                score = rubric_score
                                threshold = TEST_PASS  # pipeline mode: 90 individual pass (94 = tier advancement)
                            else:
                                # Fallback: min of flat dimension scores
                                # (canonical nested dims + legacy numeric keys)
                                score = min(flat_dims.values()) if flat_dims else 0
                                threshold = TEST_PASS
                        if score < threshold:
                            mf.append(
                                {
                                    "id": "G3.2",
                                    "file": rp.name,
                                    "s": GateStatus.FAIL,
                                    "score": score,
                                    "threshold": threshold,
                                }
                            )
                        else:
                            c.append(
                                {
                                    "id": "G3.2",
                                    "file": rp.name,
                                    "s": GateStatus.PASS,
                                    "score": score,
                                }
                            )
                    except (json.JSONDecodeError, ValueError, OSError):  # F444
                        continue  # malformed score file → skip, score next report
        except (json.JSONDecodeError, ValueError, OSError):  # F444
            c.append({"id": "G3.2", "s": GateStatus.SKIP, "r": "acceptance.json invalid"})
    else:
        c.append({"id": "G3.2", "s": GateStatus.SKIP, "r": "no acceptance.json"})

    # G3.3 — Output files passed G2
    # (F444 boundary: only the codex dispatch route records output_files into
    # progress.json; the pipeline route relies on G4/G6 — G3.3 SKIPs cleanly
    # on materialized progress without fabricated data.)
    pp = rd / "progress.json"
    if pp.exists():
        try:
            progress = jload(str(pp))
            if skill_name:
                skills = progress.get("skills", {})
                skill_data = skills.get(skill_name, {}) if isinstance(skills, dict) else {}
                # F444: producers (dispatcher/modes/codex.py _record_completion)
                # write per-test_type entries: skills[skill][test_type]
                tt_entry = (
                    skill_data.get(test_type or "generative", {})
                    if isinstance(skill_data, dict)
                    else {}
                )
                output_files = (
                    tt_entry.get("output_files", []) if isinstance(tt_entry, dict) else []
                )
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
                        mf.append(
                            {"id": "G3.3", "s": GateStatus.FAIL, "r": "G2 check failed on outputs"}
                        )
                    else:
                        c.append({"id": "G3.3", "s": GateStatus.PASS})
                except json.JSONDecodeError:
                    mf.append({"id": "G3.3", "s": GateStatus.FAIL, "r": "G2 result unparseable"})
            else:
                c.append({"id": "G3.3", "s": GateStatus.SKIP, "r": "no output_files"})
        except (
            json.JSONDecodeError,
            ValueError,
            OSError,
        ):  # F444: jload raises ValueError on non-dict
            mf.append({"id": "G3.3", "s": GateStatus.FAIL, "r": "progress.json invalid"})
    else:
        c.append({"id": "G3.3", "s": GateStatus.SKIP, "r": "no progress.json"})

    # G3.4 — Agent ID isolation: scorer != generator
    if pp.exists():
        try:
            progress = jload(str(pp))
            # Kant I2: call scoring_independence_status (single-source from pillar5)
            verdict, reason = scoring_independence_status(progress, skill_name or "")
            if verdict == "FAIL":
                mf.append({"id": "G3.4", "s": GateStatus.FAIL, "r": reason})
            else:
                c.append({"id": "G3.4", "s": GateStatus.PASS})
        except (json.JSONDecodeError, ValueError, OSError):  # F444: jload ValueError on non-dict
            c.append({"id": "G3.4", "s": GateStatus.SKIP, "r": "progress.json invalid"})
    else:
        c.append({"id": "G3.4", "s": GateStatus.SKIP, "r": "no progress.json"})

    if mf:
        return fail("G3", c, "scoring", [x["id"] + ":" + x.get("file", x.get("r", "")) for x in mf])
    return passed("G3", c)
