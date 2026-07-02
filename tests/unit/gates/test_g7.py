"""Unit tests for G7: round close validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from shenbi.gates.g7 import gate_G7


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


pytestmark = pytest.mark.unit


class TestG7RoundClose:
    def test_emits_valid_json_for_empty_round(self, tmp_path: Path) -> None:
        """G7 must return a parseable result for any round_dir, even empty."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G7(str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed
        assert parsed["gate"] == "G7"


class TestG7ErrorPaths:
    """Error-path coverage for G7 round-close (PR-52 Step 7).

    G7 reads ALL_SKILLS (from skills/) to validate summary.json coverage,
    scans round_dir/skill-output/ for placeholders and pending truth files,
    re-runs PASS
    gate markers. Tests use a round_dir under tmp_path and, where the gate
    references module-level constants, monkeypatch them.
    """

    @pytest.mark.unit
    def test_g7_hallucinated_skill_in_summary_fails(self, tmp_path: Path) -> None:
        """A summary.json listing a skill not in ALL_SKILLS -> G7.1:hallucinated."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        (round_dir / "summary.json").write_text(
            json.dumps({"t1_scores": {"shenbi-not-a-real-skill": {"generative": 95}}}),
            encoding="utf-8",
        )
        result = _result_dict(gate_G7(str(round_dir)))
        assert result["status"] == "FAIL"
        assert any("G7.1:hallucinated" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g7_missing_coverage_field_fails(self, tmp_path: Path) -> None:
        """Reverse coverage: summary.json missing real skills -> G7.1:missing_coverage.

        A summary.json with NO t1_scores means every ALL_SKILLS entry is
        reported as missing coverage.
        """
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        (round_dir / "summary.json").write_text(json.dumps({"t1_scores": {}}), encoding="utf-8")
        result = _result_dict(gate_G7(str(round_dir)))
        assert result["status"] == "FAIL"
        assert any("G7.1:missing_coverage" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g7_template_placeholders_in_skill_output_fails(self, tmp_path: Path) -> None:
        """An output file with >10% '待填充' placeholder lines -> G7.5:placeholders."""
        round_dir = tmp_path / "round"
        so = round_dir / "skill-output" / "proj"
        so.mkdir(parents=True)
        (so / "chapter.md").write_text(
            "\n".join(["待填充内容" for _ in range(5)] + ["正文内容。"]),
            encoding="utf-8",
        )
        result = _result_dict(gate_G7(str(round_dir)))
        assert any("G7.5:placeholders" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g7_pending_truth_files_after_state_settling_fails(self, tmp_path: Path) -> None:
        """A truth/*.md with frontmatter status: pending -> G7.6:pending_truth."""
        round_dir = tmp_path / "round"
        truth = round_dir / "skill-output" / "proj" / "truth"
        truth.mkdir(parents=True)
        (truth / "current_state.md").write_text(
            "---\nstatus: pending\n---\n# Current State\n", encoding="utf-8"
        )
        result = _result_dict(gate_G7(str(round_dir)))
        assert any("G7.6:pending_truth" in mf for mf in result["must_fix"])


# ---------------------------------------------------------------------------
# G7.1 / G7.13 / G7.14 / G7.15 / G7.16 branch coverage (PR-56 coverage fill)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_g7_corrupt_summary_json_invalid(tmp_path: Path) -> None:
    """Malformed summary.json -> G7.1:summary.json_invalid, not a crash.

    Covers the G7.1/G7.1b except branches (g7.py:50-51, 63-64). jload
    propagates json.JSONDecodeError on unparseable JSON, which G7 catches.
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    (round_dir / "summary.json").write_text("{not valid json", encoding="utf-8")
    result = _result_dict(gate_G7(str(round_dir)))
    assert any("G7.1:summary.json_invalid" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_g713_g4_marker_pass_but_rerun_fails(tmp_path: Path) -> None:
    """A G4 marker claiming PASS whose re-run FAILs -> G7.13:marker_PASS_rerun_FAIL.

    Covers the G4 re-run branch (g7.py:172-177): files_checked points at a
    non-existent file so gate_G4 returns FAIL on re-run.
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    marker_dir = round_dir / "gate-markers"
    marker_dir.mkdir()
    (marker_dir / "G4-shenbi-chapter-drafting-generative.json").write_text(
        json.dumps({"status": "PASS", "files_checked": ["/nonexistent/chapter-001.md"]}),
        encoding="utf-8",
    )
    result = _result_dict(gate_G7(str(round_dir)))
    assert any("G7.13:" in mf and "marker_PASS_rerun_FAIL" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_g713_g6_marker_rerun_runs(tmp_path: Path) -> None:
    """A G6 marker claiming PASS triggers a gate_G6 re-run (G7.13 G6 branch).

    Covers g7.py:178-186. The re-run targets rd/project-output (empty) so
    gate_G6 fails on missing chapters -> mismatch recorded.
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    marker_dir = round_dir / "gate-markers"
    marker_dir.mkdir()
    (marker_dir / "G6-long-form-generative.json").write_text(
        json.dumps({"status": "PASS", "files_checked": []}), encoding="utf-8"
    )
    result = _result_dict(gate_G7(str(round_dir)))
    assert any("G7.13:" in mf and "marker_PASS_rerun_FAIL" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_g714_timeline_warns_when_marker_newer_than_score(tmp_path: Path) -> None:
    """A gate marker newer than a score file -> G7.14 WARN.

    Covers the timeline-warning branch (g7.py:204-214). Uses a G0 marker name
    so G7.13's G4/G6 parsing skips it, isolating the G7.14 path.
    """
    import os

    round_dir = tmp_path / "round"
    round_dir.mkdir()
    reports = round_dir / "t1-reports"
    reports.mkdir()
    score = reports / "skill-a-generative-scores.json"
    score.write_text(json.dumps({"dimensions": [{"num": 1, "score": 90}]}), encoding="utf-8")
    marker_dir = round_dir / "gate-markers"
    marker_dir.mkdir()
    marker = marker_dir / "G0-seed-generative.json"
    marker.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    # Force marker mtime strictly later than the score file's.
    later = score.stat().st_mtime + 100
    os.utime(marker, (later, later))
    result = _result_dict(gate_G7(str(round_dir)))
    g714_warns = [c for c in result["checks"] if c.get("id") == "G7.14" and c.get("s") == "WARN"]
    assert g714_warns


@pytest.mark.unit
def test_g715_duplicate_score_pattern_warns_and_writes_audit(tmp_path: Path) -> None:
    """Three skills sharing an identical score vector -> G7.15 DUPLICATE_PATTERN WARN.

    Covers g7.py:243-254 (pattern detection + WARN append) and the
    audit_warnings write-back to summary.json (g7.py:286, 294-300), which
    fires because a G7.15 WARN exists alongside a summary.json.
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    reports = round_dir / "t1-reports"
    reports.mkdir()
    vec = json.dumps({"dimensions": [{"num": 1, "score": 90}, {"num": 2, "score": 85}]})
    for skill in ("skill-a", "skill-b", "skill-c"):
        (reports / f"{skill}-generative-scores.json").write_text(vec, encoding="utf-8")
    (round_dir / "summary.json").write_text(json.dumps({"t1_scores": {}}), encoding="utf-8")
    result = _result_dict(gate_G7(str(round_dir)))
    g715_warns = [c for c in result["checks"] if c.get("id") == "G7.15" and c.get("s") == "WARN"]
    assert g715_warns
    # G7 is now pure: audit_warnings are returned in the gate JSON, NOT written
    # to summary.json (spec: gates must not have write side-effects).
    audit_check = next((chk for chk in result["checks"] if chk.get("id") == "G7.AUDIT"), None)
    assert audit_check is not None
    assert audit_check.get("audit_warnings")
    # summary.json must be untouched by the gate
    assert "audit_warnings" not in json.loads(
        (round_dir / "summary.json").read_text(encoding="utf-8")
    )


@pytest.mark.unit
def test_g715_raw_score_file_vector(tmp_path: Path) -> None:
    """A score file without a 'dimensions' key uses the raw-vector branch.

    Covers g7.py:237 (else branch building the vector from numeric keys).
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    reports = round_dir / "t1-reports"
    reports.mkdir()
    (reports / "skill-a-generative-scores.json").write_text(
        json.dumps({"1": 90, "2": 85}), encoding="utf-8"
    )
    result = _result_dict(gate_G7(str(round_dir)))
    g715 = next((c for c in result["checks"] if c.get("id") == "G7.15"), None)
    assert g715 is not None  # raw-vector branch ran without crashing


@pytest.mark.unit
def test_g716_phase_state_not_finalized_fails(tmp_path: Path) -> None:
    """A phase-state file whose state is not 'finalized' -> G7.16 FAIL.

    Covers g7.py:269 (the state-mismatch branch).
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    ps = round_dir / "phase-state"
    ps.mkdir()
    (ps / "genesis.json").write_text(json.dumps({"state": "in_progress"}), encoding="utf-8")
    (round_dir / "summary.json").write_text(
        json.dumps({"t2_scores": {"genesis": {"score": 90}}, "t3_scores": {}}),
        encoding="utf-8",
    )
    result = _result_dict(gate_G7(str(round_dir)))
    assert any("G7.16:phase:genesis:state=in_progress" in mf for mf in result["must_fix"])
