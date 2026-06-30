"""Unit tests for G7: round close validation."""

from __future__ import annotations

import json
import sys
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
    checks the tests/rounds/CHANGELOG.md writability, and re-runs PASS
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

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod permissions not honored on Windows")
    @pytest.mark.unit
    def test_g7_changelog_not_writable_fails(self, tmp_path: Path, monkeypatch) -> None:
        """When the CHANGELOG's parent dir exists but is not writable and the
        CHANGELOG.md file itself is absent -> G7.7:no_changelog_and_cannot_create.

        The gate resolves CHANGELOG as `TESTS / 'rounds' / 'CHANGELOG.md'`.
        We monkeypatch the g7 module's TESTS to a tmp path whose rounds/
        subdir is non-writable and contains no CHANGELOG.md.
        """
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        fake_tests = tmp_path / "fake-tests"
        rounds_dir = fake_tests / "rounds"
        rounds_dir.mkdir(parents=True)
        rounds_dir.chmod(0o555)  # non-writable
        monkeypatch.setattr("shenbi.gates.g7.TESTS", fake_tests)
        try:
            result = _result_dict(gate_G7(str(round_dir)))
            # Tightened: this exercises the no-file + non-writable-parent branch
            # (g7.py mf.append("G7.7:no_changelog_and_cannot_create")), not the
            # changelog_not_writable branch the test name implies. Relies on
            # chmod(0o555) being honored, which may not hold under root.
            assert any("G7.7:no_changelog_and_cannot_create" in mf for mf in result["must_fix"])
        finally:
            # Restore writability so tmp_path cleanup can remove the dir.
            rounds_dir.chmod(0o755)

    @pytest.mark.unit
    def test_g7_marker_pass_rerun_mismatch_fails(self, tmp_path: Path) -> None:
        """A G4 marker claiming PASS but with empty files_checked ->
        G7.13:{stem}:empty_files_checked (deterministic mismatch case).
        """
        round_dir = tmp_path / "round"
        marker_dir = round_dir / "gate-markers"
        marker_dir.mkdir(parents=True)
        (marker_dir / "G4-shenbi-chapter-drafting-generative.json").write_text(
            json.dumps({"status": "PASS", "files_checked": []}), encoding="utf-8"
        )
        result = _result_dict(gate_G7(str(round_dir)))
        assert any("G7.13:" in mf and "empty_files_checked" in mf for mf in result["must_fix"])

    def test_returns_str_result(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G7(str(round_dir))
        assert isinstance(result_str, str)
        assert json.loads(result_str)

    def test_handles_round_dir_with_partial_state(self, tmp_path: Path) -> None:
        """A round in progress (markers, partial summaries) should not crash."""
        round_dir = tmp_path / "round"
        (round_dir / "gate-markers").mkdir(parents=True)
        (round_dir / "gate-markers" / "G0-seed-generative.json").write_text(
            json.dumps({"status": "PASS"}), encoding="utf-8"
        )
        result_str = gate_G7(str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed

    @pytest.mark.unit
    def test_g7_changelog_writable_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CHANGELOG.md exists and is writable -> G7.7 PASS."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        fake_tests = tmp_path / "fake-tests"
        rounds_dir = fake_tests / "rounds"
        rounds_dir.mkdir(parents=True)
        (rounds_dir / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        monkeypatch.setattr("shenbi.gates.g7.TESTS", fake_tests)
        result = _result_dict(gate_G7(str(round_dir)))
        g77 = next((c for c in result["checks"] if c.get("id") == "G7.7"), None)
        assert g77 is not None
        assert g77["s"] == "PASS"

    @pytest.mark.unit
    def test_g7_phase_state_missing_fails(self, tmp_path: Path) -> None:
        """summary.json with t2_scores but no phase-state file -> G7.16 FAIL."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        (round_dir / "summary.json").write_text(
            json.dumps({"t2_scores": {"genesis": {"score": 95}}, "t3_scores": {}}),
            encoding="utf-8",
        )
        result = _result_dict(gate_G7(str(round_dir)))
        assert any("G7.16:phase:genesis:no_state_file" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g7_pipeline_missing_g6_marker_fails(self, tmp_path: Path) -> None:
        """summary.json with t3_scores but no G6 marker -> G7.16 FAIL."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        (round_dir / "gate-markers").mkdir()
        (round_dir / "summary.json").write_text(
            json.dumps({"t2_scores": {}, "t3_scores": {"pipeline-A": {"score": 90}}}),
            encoding="utf-8",
        )
        result = _result_dict(gate_G7(str(round_dir)))
        assert any("G7.16:pipeline:pipeline-A:no_G6_marker" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g7_changelog_parent_writable_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CHANGELOG.md missing but parent writable -> G7.7 PASS with note."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        fake_tests = tmp_path / "fake-tests"
        rounds_dir = fake_tests / "rounds"
        rounds_dir.mkdir(parents=True)
        monkeypatch.setattr("shenbi.gates.g7.TESTS", fake_tests)
        result = _result_dict(gate_G7(str(round_dir)))
        g77 = next((c for c in result["checks"] if c.get("id") == "G7.7"), None)
        assert g77 is not None
        assert g77["s"] == "PASS"

    @pytest.mark.unit
    def test_g7_no_placeholders_passes(self, tmp_path: Path) -> None:
        """skill-output/ with clean output files -> G7.5 PASS."""
        round_dir = tmp_path / "round"
        so = round_dir / "skill-output" / "proj"
        so.mkdir(parents=True)
        (so / "chapter.md").write_text("正文内容。已完成的内容。\n", encoding="utf-8")
        result = _result_dict(gate_G7(str(round_dir)))
        g75 = next((c for c in result["checks"] if c.get("id") == "G7.5"), None)
        assert g75 is not None
        assert g75["s"] == "PASS"

    @pytest.mark.unit
    def test_g7_no_pending_truth_passes(self, tmp_path: Path) -> None:
        """truth/ files without pending status -> G7.6 PASS."""
        round_dir = tmp_path / "round"
        truth = round_dir / "skill-output" / "proj" / "truth"
        truth.mkdir(parents=True)
        (truth / "current_state.md").write_text(
            "---\nstatus: active\n---\n# Current State\n", encoding="utf-8"
        )
        result = _result_dict(gate_G7(str(round_dir)))
        g76 = next((c for c in result["checks"] if c.get("id") == "G7.6"), None)
        assert g76 is not None
        assert g76["s"] == "PASS"

    @pytest.mark.unit
    def test_g7_g75_skips_when_no_skill_output(self, tmp_path: Path) -> None:
        """No skill-output/ dir -> G7.5 SKIP."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result = _result_dict(gate_G7(str(round_dir)))
        g75 = next((c for c in result["checks"] if c.get("id") == "G7.5"), None)
        assert g75 is not None
        assert g75["s"] == "SKIP"

    @pytest.mark.unit
    def test_g7_g76_skips_when_no_truth_in_skill_output(self, tmp_path: Path) -> None:
        """skill-output exists but truth subdir missing -> G7.6 SKIP."""
        round_dir = tmp_path / "round"
        so = round_dir / "skill-output" / "proj"
        so.mkdir(parents=True)
        result = _result_dict(gate_G7(str(round_dir)))
        g76 = next((c for c in result["checks"] if c.get("id") == "G7.6"), None)
        assert g76 is not None
        assert g76["s"] == "SKIP"

    @pytest.mark.unit
    def test_g7_timeline_consistent_when_no_reports(self, tmp_path: Path) -> None:
        """No t1/t2/t3-reports dirs -> G7.14 PASS."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result = _result_dict(gate_G7(str(round_dir)))
        g714 = next((c for c in result["checks"] if c.get("id") == "G7.14"), None)
        assert g714 is not None
        assert g714["s"] == "PASS"

    @pytest.mark.unit
    def test_g7_g716_passes_when_no_t2_t3_scores(self, tmp_path: Path) -> None:
        """summary.json without t2/t3 scores -> G7.16 PASS."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        (round_dir / "summary.json").write_text(
            json.dumps({"t1_scores": {"skill-x": {"generative": 95}}}),
            encoding="utf-8",
        )
        result = _result_dict(gate_G7(str(round_dir)))
        g716 = next((c for c in result["checks"] if c.get("id") == "G7.16"), None)
        assert g716 is not None
        assert g716["s"] == "PASS"

    @pytest.mark.unit
    def test_g7_g715_passes_with_unique_vectors(self, tmp_path: Path) -> None:
        """Score files with different score vectors -> G7.15 PASS."""
        round_dir = tmp_path / "round"
        reports = round_dir / "t1-reports"
        reports.mkdir(parents=True)
        (reports / "skill-a-generative-scores.json").write_text(
            json.dumps({"dimensions": [{"num": 1, "score": 90}]}), encoding="utf-8"
        )
        (reports / "skill-b-generative-scores.json").write_text(
            json.dumps({"dimensions": [{"num": 1, "score": 95}]}), encoding="utf-8"
        )
        result = _result_dict(gate_G7(str(round_dir)))
        g715 = next((c for c in result["checks"] if c.get("id") == "G7.15"), None)
        assert g715 is not None
        assert g715["s"] == "PASS"

    @pytest.mark.unit
    def test_g7_g716_passes_with_phase_state(self, tmp_path: Path) -> None:
        """summary.json with t2_scores and valid phase-state -> G7.16 PASS."""
        round_dir = tmp_path / "round"
        phase_state = round_dir / "phase-state"
        phase_state.mkdir(parents=True)
        (phase_state / "genesis.json").write_text(
            json.dumps({"state": "finalized"}), encoding="utf-8"
        )
        (round_dir / "summary.json").write_text(
            json.dumps({"t2_scores": {"genesis": {"score": 95}}, "t3_scores": {}}),
            encoding="utf-8",
        )
        result = _result_dict(gate_G7(str(round_dir)))
        g716 = next((c for c in result["checks"] if c.get("id") == "G7.16"), None)
        assert g716 is not None
        assert g716["s"] == "PASS"

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod permissions not honored on Windows")
    @pytest.mark.unit
    def test_g7_changelog_exists_not_writable_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CHANGELOG.md exists but read-only -> G7.7:changelog_not_writable."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        fake_tests = tmp_path / "fake-tests"
        rounds_dir = fake_tests / "rounds"
        rounds_dir.mkdir(parents=True)
        changelog = rounds_dir / "CHANGELOG.md"
        changelog.write_text("# Changelog\n", encoding="utf-8")
        changelog.chmod(0o444)
        monkeypatch.setattr("shenbi.gates.g7.TESTS", fake_tests)
        try:
            result = _result_dict(gate_G7(str(round_dir)))
            assert any("changelog_not_writable" in mf for mf in result.get("must_fix", []))
        finally:
            changelog.chmod(0o644)


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
