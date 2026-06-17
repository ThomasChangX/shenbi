"""Unit tests for G_RECONCILE: cross-skill score reconciliation.

G_RECONCILE reads `progress.json` from round_dir and iterates
`progress["skills"][<skill>][<test_type>]["status"]`. Only skills whose
status == "DONE" require a matching report file under t1-reports/.

Note on filename convention: `find_report` in `src/shenbi/gates/shared.py`
accepts three patterns (`<skill>-<test_type>-scores.json`,
`<skill>-<test_type>.json`, `<skill>.json`). GR.2's on-disk filename
parser does NOT strip the `-scores` suffix, so reports named with the
production convention `<skill>-generative-scores.json` falsely trigger
GR.2 `status=?` FAILs even when progress.json has matching DONE entries.
Spec Non-Goal #3 forbids fixing the parser, so tests that exercise the
GR.1 happy path use the `<skill>-<test_type>.json` naming to sidestep
the parser bug.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g_reconcile import gate_G_RECONCILE


def _result_dict(result_str: str) -> dict[str, Any]:
    return json.loads(result_str)


def _write_pattern2_report(
    round_dir: Path, skill: str, test_type: str, payload: dict[str, Any]
) -> None:
    """Write a report using `<skill>-<test_type>.json` naming.

    This is find_report's pattern 2. Using it (instead of pattern 1's
    `-scores.json` suffix) sidesteps the GR.2 parser bug described in the
    module docstring while still exercising GR.1's DONE-skill lookup.
    """
    reports = round_dir / "t1-reports"
    reports.mkdir(exist_ok=True)
    (reports / f"{skill}-{test_type}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


@pytest.mark.unit
def test_g_reconcile_passes_when_done_skills_have_reports(
    make_project,
) -> None:
    """DONE skills with matching t1-reports -> PASS."""
    _, round_dir = make_project(
        progress={
            "skills": {
                "shenbi-worldbuilding": {"generative": {"status": "DONE"}},
                "shenbi-chapter-drafting": {"generative": {"status": "DONE"}},
            }
        },
    )
    _write_pattern2_report(round_dir, "shenbi-worldbuilding", "generative", {"score": 85})
    _write_pattern2_report(round_dir, "shenbi-chapter-drafting", "generative", {"score": 80})
    result = _result_dict(gate_G_RECONCILE(str(round_dir)))
    assert result["status"] == "PASS"
    assert result.get("must_fix", []) == []


@pytest.mark.unit
def test_g_reconcile_passes_when_no_done_skills(make_project) -> None:
    """progress.json present but no skill has status=DONE -> PASS (nothing to verify)."""
    _, round_dir = make_project(progress={"skills": {}})
    result = _result_dict(gate_G_RECONCILE(str(round_dir)))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_g_reconcile_fails_when_no_progress(make_project) -> None:
    """Missing progress.json -> FAIL with no_progress in must_fix."""
    _, round_dir = make_project()  # no progress.json
    result = _result_dict(gate_G_RECONCILE(str(round_dir)))
    assert result["status"] == "FAIL"
    assert "no_progress" in result["must_fix"]


@pytest.mark.unit
def test_g_reconcile_fails_when_done_skill_lacks_report(make_project) -> None:
    """DONE skill without matching t1-report -> FAIL with GR.1 reason."""
    _, round_dir = make_project(
        progress={
            "skills": {
                "shenbi-worldbuilding": {"generative": {"status": "DONE"}},
            }
        },
        # No t1_reports — report file missing.
    )
    result = _result_dict(gate_G_RECONCILE(str(round_dir)))
    assert result["status"] == "FAIL"
    assert any("GR.1" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_g_reconcile_returns_valid_json_for_empty_round(tmp_path: Path) -> None:
    """Non-existent round_dir -> FAIL JSON with no_progress, no exception."""
    result = _result_dict(gate_G_RECONCILE(str(tmp_path / "empty")))
    assert result["gate"] == "G_RECONCILE"
    assert result["status"] == "FAIL"
    assert "no_progress" in result["must_fix"]


@pytest.mark.unit
def test_g_reconcile_unknown_skill_in_progress_handled_gracefully(make_project) -> None:
    """progress.json skills map referencing an unknown skill name must not crash.


    The gate iterates skills entries by status; an unknown skill name simply
    never matches a real report, so it returns FAIL with GR.1 because the
    DONE skill lacks a report. Crucially, no AttributeError or crash occurs.
    """
    _, round_dir = make_project(
        progress={
            "skills": {
                "shenbi-totally-fake-skill": {"generative": {"status": "DONE"}},
            }
        },
    )
    # No report written for the unknown skill. The DONE branch looks for a
    # report file; absence -> GR.1, but crucially no crash/AttributeError.
    result = _result_dict(gate_G_RECONCILE(str(round_dir)))
    assert result["gate"] == "G_RECONCILE"
    assert result["status"] == "FAIL"
    assert any(
        "GR.1:shenbi-totally-fake-skill-generative:no_report" in mf for mf in result["must_fix"]
    )


@pytest.mark.unit
def test_g_reconcile_gr1_missing_report_carries_skill_and_test_type(make_project) -> None:
    """GR.1 reason must embed both <skill> and <test_type> for traceability."""
    _, round_dir = make_project(
        progress={
            "skills": {
                "shenbi-worldbuilding": {
                    "generative": {"status": "DONE"},
                    "bug-hunt": {"status": "DONE"},
                },
            }
        },
    )
    result = _result_dict(gate_G_RECONCILE(str(round_dir)))
    must_fix = result["must_fix"]
    assert any(mf == "GR.1:shenbi-worldbuilding-generative:no_report" for mf in must_fix)
    assert any(mf == "GR.1:shenbi-worldbuilding-bug-hunt:no_report" for mf in must_fix)


@pytest.mark.unit
def test_g_reconcile_non_dict_progress_propagates_jload_error(make_project) -> None:
    """A progress.json that is valid JSON but not an object -> jload raises
    ValueError (spec Non-Goal #3: pin current behavior; do not modify source).

    The gate does not catch ValueError, so it propagates rather than producing
    a FAIL result.
    """
    _, round_dir = make_project()
    (round_dir / "progress.json").write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError):
        gate_G_RECONCILE(str(round_dir))  # pins current behavior
