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
        """G3.1 always emits a SKIP check (D19: per-skill prereqs not modeled).

        Source: deps.json's top-level keys are phase/pipeline rosters
        (t2-phases, t3-pipelines, ...), never per-skill prerequisite data, so
        the old deps.get(skill_name) was a dead function. G3.1 now SKIPs
        explicitly; readiness is covered by G3.2.
        """
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(round_dir)))
        g31 = next((c for c in result["checks"] if c.get("id") == "G3.1"), None)
        assert g31 is not None
        assert g31["s"] == "SKIP"

    def test_g32_emits_check_with_real_acceptance_json(self, tmp_path: Path) -> None:
        """G3.2 reads TESTS/tiers/acceptance.json for threshold; emits check."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        # Add a t1-reports dir with a low-score report to exercise the FAIL branch.
        reports = round_dir / "t1-reports"
        reports.mkdir()
        (reports / "shenbi-test-generative-scores.json").write_text(
            json.dumps({"score": 50}), encoding="utf-8"
        )
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(round_dir)))
        # Gate ran without crash; the low-score report now actually reaches
        # G3.2 (suffixed name, not filtered as a sidecar).
        assert result["status"] == "FAIL"
        assert any("G3.2" in m for m in result.get("must_fix", []))

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
        # F444: production shape — producers write skills[skill][test_type]
        progress = {"skills": {"shenbi-worldbuilding": {"generative": {"output_files": [str(ch)]}}}}
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
        progress = {"skills": {"shenbi-worldbuilding": {"generative": {}}}}
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
        json.dumps(
            {"skills": {"shenbi-chapter-drafting": {"generative": {"output_files": [str(ch)]}}}}
        ),
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


@pytest.mark.unit
def test_compute_rubric_weighted_score_returns_none_when_rubric_missing() -> None:
    """Returns None when the rubric file does not exist."""
    from shenbi.gates.g3 import _compute_rubric_weighted_score

    assert _compute_rubric_weighted_score({}, "shenbi-nonexistent-skill") is None


@pytest.mark.unit
def test_compute_rubric_weighted_score_returns_none_when_no_dimensions_match() -> None:
    """Returns None when no scored dimensions match rubric dimensions."""
    from shenbi.gates.g3 import _compute_rubric_weighted_score

    # data with non-matching keys
    result = _compute_rubric_weighted_score({"99": 80}, "shenbi-worldbuilding")
    assert result is None


# ---------------------------------------------------------------------------
# D19: G3.1 dead-function canary (spec §5.3 DepsDoc)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_g31_does_not_silently_query_missing_key() -> None:
    """D19 canary: G3.1 must not do the dead deps.get(skill_name) query.

    deps.json never stored per-skill prerequisite data (its keys are
    t2-phases/t3-pipelines rosters), so the query was a dead function that
    always SKIPped via "no prerequisites". After deletion G3.1 SKIPs
    explicitly with a reason documenting that readiness is covered by G3.2.

    This canary guards two invariants:
    1. Runtime: G3.1 always emits exactly one SKIP check whose reason names
       the modelling decision (never depends on skill_name or deps.json).
    2. Source: g3.py no longer calls find_report or does a per-skill deps
       lookup in executable code (the dead function must not be reintroduced).
    """
    import ast
    import inspect
    import tempfile
    from pathlib import Path

    # 1. Runtime invariant: SKIP with the documented reason.
    with tempfile.TemporaryDirectory() as td:
        result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", td))
    g31s = [c for c in result["checks"] if c.get("id") == "G3.1"]
    assert len(g31s) == 1, "G3.1 emits exactly one check"
    assert g31s[0]["s"] == "SKIP"
    assert "not modeled" in g31s[0]["r"]
    # The SKIP reason must NOT reference the legacy per-skill deps lookup.
    assert "no prerequisites" not in g31s[0]["r"]
    assert "no deps.json" not in g31s[0]["r"]

    # 2. Source invariant (executable code only, ignoring comments/docstrings):
    #    the dead query primitives must not be reintroduced.
    source_path = Path(inspect.getfile(gate_G3))
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    code_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            code_names.append(node.func.id)
        if isinstance(node, ast.Attribute) and node.attr == "get":
            # detect deps.get(...) calls; ensure the receiver isn't a deps object.
            if isinstance(node.value, ast.Name) and node.value.id == "deps":
                pytest.fail("G3.1 must not call deps.get(...) (D19: dead function deleted)")
    assert "find_report" not in code_names, (
        "G3.1 must not call find_report (D19: dead prereq lookup deleted)"
    )


@pytest.mark.unit
def test_g33_executes_on_real_producer_shape(tmp_path: Path) -> None:
    """F444: progress built by the REAL producer (_record_completion with
    output_files) → G3.3 actually executes (non-SKIP) on the production shape.
    """
    from shenbi.dispatcher.modes.codex import _record_completion

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
    _record_completion(rd, "shenbi-worldbuilding", "generative", 95.0, output_files=[str(ch)])
    result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
    g33 = next((c for c in result["checks"] if c.get("id") == "G3.3"), None)
    assert g33 is not None
    assert g33["s"] == "PASS"


@pytest.mark.unit
def test_g33_non_dict_progress_fails_not_crashes(tmp_path: Path) -> None:
    """F444 follow-on: non-dict JSON progress raises ValueError inside gate_G2's
    jload — g3.py must catch it and record FAIL, not propagate.
    """
    rd = tmp_path / "round"
    rd.mkdir()
    ch = rd / "outline" / "o.json"
    ch.parent.mkdir()
    ch.write_text("[1,2]", encoding="utf-8")  # non-dict JSON → jload ValueError in gate_G2
    (rd / "progress.json").write_text(
        json.dumps(
            {"skills": {"shenbi-worldbuilding": {"generative": {"output_files": [str(ch)]}}}}
        ),
        encoding="utf-8",
    )
    result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
    assert result["status"] == "FAIL"  # caught → FAIL, no exception propagated


@pytest.mark.unit
def test_g32_reads_canonical_scoring_shape(tmp_path: Path) -> None:
    """F130 (spec #27): canonical scoring.py output = final_score + nested
    dimensions list — G3.2 must read final_score / flatten nested dims.
    """
    from shenbi.gates.g3 import _extract_score_fields

    canonical = {
        "final_score": 91.5,
        "classification": "PASS (excellent)",
        "dimensions": [
            {"num": 1, "name": "A", "weight": 10, "score": 90},
            {"num": 2, "name": "B", "weight": 5, "score": 95},
        ],
    }
    score, dims = _extract_score_fields(canonical)
    assert score == 91.5
    assert dims == {1: 90.0, 2: 95.0}
    # legacy flat shape still supported
    legacy = {"total_score": 88, "1": 80, "2": 90}
    score2, dims2 = _extract_score_fields(legacy)
    assert score2 == 88
    assert dims2 == {1: 80.0, 2: 90.0}


@pytest.mark.unit
def test_g32_genuine_zero_score_not_overwritten() -> None:
    """A real final_score of 0 (kill-switch) must NOT be replaced by the
    rubric/min fallback (false-PASS guard, spec #27 T4 review).
    """
    from shenbi.gates.g3 import _extract_score_fields

    score, _ = _extract_score_fields({"final_score": 0, "1": 95})
    assert score == 0.0


@pytest.mark.unit
def test_g32_skips_sidecar_artifacts(tmp_path: Path) -> None:
    """Spec #31: collapse-check / dual-scorer sidecars are not readiness reports.

    A legit round (primary scores PASS) must not fail G3.2 merely because the
    dispatcher's deterministic collapse-check.json (no score fields) sits in
    t1-reports/.
    """
    rd = tmp_path / "round"
    rd.mkdir()
    reports = rd / "t1-reports"
    reports.mkdir()
    (reports / "sk-generative-scores-subagent.json").write_text(
        json.dumps({"score": 95}), encoding="utf-8"
    )
    (reports / "sk-generative-collapse-check.json").write_text(
        json.dumps({"collapse_suspected": False, "signals": []}), encoding="utf-8"
    )
    (reports / "sk-generative-scores-subagent-2.json").write_text(
        json.dumps({"score": 95}), encoding="utf-8"
    )
    result = _result_dict(gate_G3(None, "generative", str(rd)))
    g32 = [c for c in result["checks"] if c.get("id") == "G3.2"]
    assert all(c.get("s") != "FAIL" for c in g32), result["must_fix"]
    assert not any("collapse-check" in m or "subagent-2" in m for m in result.get("must_fix", []))
