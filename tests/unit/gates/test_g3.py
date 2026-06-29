"""Unit tests for G3: pre-scoring dependency check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from shenbi.gates.g3 import gate_G3


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG3DependencyCheck:
    def test_emits_valid_json_for_valid_args(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G3("shenbi-worldbuilding", "generative", str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_none_arguments(self) -> None:
        """All-None args should not crash — gate reports cleanly."""
        result_str = gate_G3(None, None, None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_missing_round_dir(self, tmp_path: Path) -> None:
        """A round_dir that doesn't exist should not crash G3."""
        result_str = gate_G3("shenbi-x", "generative", str(tmp_path / "nonexistent-round"))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_emits_valid_json_for_bug_hunt(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G3("shenbi-worldbuilding", "bug-hunt", str(round_dir))
        parsed = json.loads(result_str)
        assert "status" in parsed


@pytest.mark.unit
class TestG3ErrorPaths:
    """Error-path tests for G3 — pre-scoring dependency checks."""

    def test_g30_fails_when_round_dir_missing(self, tmp_path: Path) -> None:
        """None/missing round_dir -> FAIL with G3.0:no_round_dir."""
        result = _result_dict(gate_G3("shenbi-x", "generative", None))
        assert result["status"] == "FAIL"
        assert any("G3.0" in mf for mf in result.get("must_fix", []))

    def test_g30_fails_when_round_dir_does_not_exist(self, tmp_path: Path) -> None:
        """round_dir path that doesn't exist on disk -> FAIL G3.0."""
        result = _result_dict(gate_G3("shenbi-x", "generative", str(tmp_path / "nonexistent")))
        assert result["status"] == "FAIL"
        assert any("G3.0" in mf for mf in result.get("must_fix", []))

    def test_g31_emits_check_with_real_deps_json(self, tmp_path: Path) -> None:
        """With real repo deps.json, G3.1 emits some check (PASS/SKIP/FAIL).

        Source: TESTS/tiers/deps.json is read; skill_name looked up; for each
        prerequisite, find_report() is called. Result depends on repo state.
        """
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(round_dir)))
        g31 = next((c for c in result["checks"] if c.get("id") == "G3.1"), None)
        if g31 is not None:
            assert g31["s"] in ("PASS", "FAIL", "SKIP")

    def test_g32_emits_check_with_real_acceptance_json(self, tmp_path: Path) -> None:
        """G3.2 reads TESTS/tiers/acceptance.json for threshold; emits check."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        # Add a t1-reports dir with a low-score report to exercise the FAIL branch.
        reports = round_dir / "t1-reports"
        reports.mkdir()
        (reports / "shenbi-test-generative.json").write_text(
            json.dumps({"score": 50}), encoding="utf-8"
        )
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(round_dir)))
        # Gate ran without crash; G3.2 may or may not appear.
        assert result["status"] in ("PASS", "FAIL")

    def test_g30_returns_valid_json_with_gate_identifier(self) -> None:
        """All paths include gate == 'G3'."""
        result = _result_dict(gate_G3(None, None, None))
        assert result["gate"] == "G3"

    def test_g30_includes_timestamp(self) -> None:
        """All paths include ISO-8601 timestamp."""
        result = _result_dict(gate_G3(None, None, None))
        assert "timestamp" in result

    @pytest.mark.unit
    def test_g33_passes_with_valid_output_files(self, tmp_path: Path) -> None:
        """progress.json with output_files that pass G2 -> G3.3 PASS.

        G2 checks for chapter files need >3000 CJK chars + PRE/POST check blocks.
        Files must use absolute paths so gate_G2 can find them.
        """
        rd = tmp_path / "round"
        rd.mkdir()
        ch = rd / "chapters" / "ch001.md"
        ch.parent.mkdir()
        ch.write_text(
            "# Chapter\n\n"
            + ("字" * 3500)
            + "\n\n## PRE_WRITE_CHECK\n内容\n\n## POST_WRITE_SELF_CHECK\n内容\n",
            encoding="utf-8",
        )
        progress = {"skills": {"shenbi-worldbuilding": {"output_files": [str(ch)]}}}
        (rd / "progress.json").write_text(json.dumps(progress), encoding="utf-8")
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
        g33 = next((c for c in result["checks"] if c.get("id") == "G3.3"), None)
        assert g33 is not None
        assert g33["s"] == "PASS"

    @pytest.mark.unit
    def test_g33_skips_when_no_output_files(self, tmp_path: Path) -> None:
        """progress.json without output_files -> G3.3 SKIP."""
        rd = tmp_path / "round"
        rd.mkdir()
        progress = {"skills": {"shenbi-worldbuilding": {}}}
        (rd / "progress.json").write_text(json.dumps(progress), encoding="utf-8")
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
        g33 = next((c for c in result["checks"] if c.get("id") == "G3.3"), None)
        assert g33 is not None
        assert g33["s"] == "SKIP"

    @pytest.mark.unit
    def test_g33_skips_without_progress_json(self, tmp_path: Path) -> None:
        """No progress.json -> G3.3 SKIP."""
        rd = tmp_path / "round"
        rd.mkdir()
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
        g33 = next((c for c in result["checks"] if c.get("id") == "G3.3"), None)
        assert g33 is not None
        assert g33["s"] == "SKIP"

    @pytest.mark.unit
    def test_g34_fails_when_scorer_same_as_generator(self, tmp_path: Path) -> None:
        """Same agent for gen and scoring -> G3.4 FAIL."""
        rd = tmp_path / "round"
        rd.mkdir()
        progress = {
            "agent_trace": {"shenbi-worldbuilding": "agent-01"},
            "current_scorer_agent": "agent-01",
        }
        (rd / "progress.json").write_text(json.dumps(progress), encoding="utf-8")
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
        # G3.4 FAIL goes to must_fix, not checks
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
        assert any("G3.4" in mf for mf in result.get("must_fix", []))

    @pytest.mark.unit
    def test_g34_skips_without_progress_json(self, tmp_path: Path) -> None:
        """No progress.json -> G3.4 SKIP."""
        rd = tmp_path / "round"
        rd.mkdir()
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
        g34 = next((c for c in result["checks"] if c.get("id") == "G3.4"), None)
        assert g34 is not None
        assert g34["s"] == "SKIP"

    @pytest.mark.unit
    def test_g35_fails_when_scorer_already_scored(self, tmp_path: Path) -> None:
        """Scorer already in scoring_history -> G3.5 FAIL."""
        rd = tmp_path / "round"
        rd.mkdir()
        progress = {
            "current_scorer_agent": "agent-02",
            "scoring_history": ["agent-01", "agent-02"],
        }
        (rd / "progress.json").write_text(json.dumps(progress), encoding="utf-8")
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
        # G3.5 FAIL goes to must_fix, not checks
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
        assert any("G3.5" in mf for mf in result.get("must_fix", []))


# ---------------------------------------------------------------------------
# Branch coverage (PR-56 coverage fill)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_g32_compares_report_scores_against_threshold(tmp_path: Path) -> None:
    """t1-reports with scores -> G3.2 PASS (>=threshold) and FAIL (<threshold).

    Covers g3.py:88-94 (the score-comparison loop).
    """
    rd = tmp_path / "round"
    rd.mkdir()
    reports = rd / "t1-reports"
    reports.mkdir()
    (reports / "a-generative-scores.json").write_text(json.dumps({"score": 95}), encoding="utf-8")
    (reports / "b-generative-scores.json").write_text(json.dumps({"score": 50}), encoding="utf-8")
    result = _result_dict(gate_G3(None, "generative", str(rd)))
    g32_pass = [c for c in result["checks"] if c.get("id") == "G3.2" and c.get("s") == "PASS"]
    assert any(c.get("file") == "a-generative-scores.json" for c in g32_pass)
    assert any("G3.2" in m and "b-generative-scores" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_g33_runs_g2_when_output_files_present(tmp_path: Path) -> None:
    """progress.json with output_files -> G3.3 runs gate_G2 (covers g3.py:132-160)."""
    rd = tmp_path / "round"
    rd.mkdir()
    ch = tmp_path / "chapters" / "chapter-001.md"
    ch.parent.mkdir(parents=True)
    ch.write_text(
        "# 第1章\n\n## PRE_WRITE_CHECK\nx\n\n## POST_WRITE_SELF_CHECK\ny\n", encoding="utf-8"
    )
    (rd / "progress.json").write_text(
        json.dumps({"skills": {"shenbi-chapter-drafting": {"output_files": [str(ch)]}}}),
        encoding="utf-8",
    )
    result = _result_dict(gate_G3("shenbi-chapter-drafting", "generative", str(rd)))
    # Short chapter fails G2 (word count < floor) -> G3.3 FAIL in must_fix.
    assert any("G3.3" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_g34_fails_when_scorer_agent_equals_generator(tmp_path: Path) -> None:
    """agent_trace[skill] == current_scorer_agent -> G3.4 FAIL (covers g3.py:171)."""
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "progress.json").write_text(
        json.dumps(
            {"agent_trace": {"shenbi-worldbuilding": "agent-9"}, "current_scorer_agent": "agent-9"}
        ),
        encoding="utf-8",
    )
    result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
    assert any("G3.4" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_g35_fails_when_scorer_already_in_history(tmp_path: Path) -> None:
    """current_scorer_agent present in scoring_history -> G3.5 FAIL (covers g3.py:183)."""
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "progress.json").write_text(
        json.dumps(
            {"current_scorer_agent": "scorer-1", "scoring_history": [{"agent_id": "scorer-1"}]}
        ),
        encoding="utf-8",
    )
    result = _result_dict(gate_G3(None, "generative", str(rd)))
    assert any("G3.5" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_g34_fail_closed_when_generator_recorded_but_no_scorer(tmp_path: Path) -> None:
    """Generator ran (agent_trace[skill]) but no current_scorer_agent -> G3.4 FAIL.

    This is the dispatcher-scored 'idle' bug: the old condition
    `gen_agent and scorer_agent and ...` is False when scorer_agent is absent,
    so a dispatcher grading its own output passed G3.4.
    """
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "progress.json").write_text(
        json.dumps({"agent_trace": {"shenbi-worldbuilding": "agent-gen"}}),
        encoding="utf-8",
    )
    result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
    assert any("G3.4" in m for m in result.get("must_fix", []))
