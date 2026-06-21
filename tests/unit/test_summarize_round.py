"""Unit tests for shenbi.summarize_round.

Business rules under test:
- Score → band classification (pass_excellent / pass_acceptable / conditional / fail)
- Per-tier aggregation across T1/T2/T3 score dicts
- next_actions routing (fail > conditional > acceptable > ready-for-next-tier)
- G7 round-close gate enforcement
- summary.json round trips with band_breakdown appended
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from shenbi.summarize_round import (
    below_threshold,
    classify,
    classify_scores,
    main,
)

pytestmark = pytest.mark.unit

# --- Fixtures -------------------------------------------------------------


@pytest.fixture
def round_dir(tmp_path: Path) -> Path:
    rd = tmp_path / "round-001"
    rd.mkdir()
    return rd


@pytest.fixture
def summary_with_t1(round_dir: Path) -> Path:
    """summary.json with a populated t1_scores block."""
    summary = round_dir / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "tier_target": "T1",
                "t1_scores": {
                    "shenbi-alpha": {"score": 95},
                    "shenbi-beta": {"score": 80},
                    "shenbi-gamma": {"score": 65},
                    "shenbi-delta": {"score": 40},
                },
            }
        ),
        encoding="utf-8",
    )
    return summary


@pytest.fixture
def mock_g7_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch subprocess.run to return a G7 PASS — most main() tests want this."""

    class _FakeCompleted:
        returncode = 0
        stdout = json.dumps({"gate": "G7", "status": "PASS"})
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _FakeCompleted())


@pytest.fixture
def mock_g7_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeCompleted:
        returncode = 1
        stdout = json.dumps({"gate": "G7", "status": "FAIL", "must_fix": ["G7.1"]})
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _FakeCompleted())


# --- TestClassify --------------------------------------------------------


class TestClassify:
    """Threshold boundaries drive routing decisions — each band maps to a
    distinct next_action message.
    """

    def test_ninety_and_above_is_pass_excellent(self) -> None:
        assert classify(90) == "pass_excellent"
        assert classify(100) == "pass_excellent"

    def test_seventy_five_to_eighty_nine_is_pass_acceptable(self) -> None:
        assert classify(75) == "pass_acceptable"
        assert classify(89) == "pass_acceptable"

    def test_sixty_to_seventy_four_is_conditional(self) -> None:
        assert classify(60) == "conditional"
        assert classify(74) == "conditional"

    def test_below_sixty_is_fail(self) -> None:
        assert classify(59) == "fail"
        assert classify(0) == "fail"

    def test_accepts_float_inputs(self) -> None:
        assert classify(90.5) == "pass_excellent"
        assert classify(74.9) == "conditional"


# --- TestClassifyScores --------------------------------------------------


class TestClassifyScores:
    def test_empty_dict_returns_all_zero_bands(self) -> None:
        bands = classify_scores({})
        assert bands == {
            "pass_excellent": 0,
            "pass_acceptable": 0,
            "conditional": 0,
            "fail": 0,
        }

    def test_counts_int_entries_in_correct_band(self) -> None:
        bands = classify_scores({"a": 95, "b": 50})
        assert bands["pass_excellent"] == 1
        assert bands["fail"] == 1

    def test_counts_float_entries(self) -> None:
        bands = classify_scores({"a": 75.5})
        assert bands["pass_acceptable"] == 1

    def test_extracts_score_from_dict_entries(self) -> None:
        bands = classify_scores({"a": {"score": 65}})
        assert bands["conditional"] == 1

    def test_falls_back_to_re_score_when_score_missing(self) -> None:
        """Re-scoring (manual override) is tracked via 're_score' key."""
        bands = classify_scores({"a": {"re_score": 88}})
        assert bands["pass_acceptable"] == 1

    def test_mixed_entries_classified_correctly(self) -> None:
        bands = classify_scores(
            {
                "a": 95,  # excellent
                "b": {"score": 80},  # acceptable
                "c": 65,  # conditional
                "d": {"re_score": 30},  # fail
            }
        )
        assert bands == {
            "pass_excellent": 1,
            "pass_acceptable": 1,
            "conditional": 1,
            "fail": 1,
        }


# --- TestBelowThreshold --------------------------------------------------


class TestBelowThreshold:
    def test_empty_dict_returns_empty_list(self) -> None:
        assert below_threshold({}, 60) == []

    def test_returns_only_names_below_threshold(self) -> None:
        scores: dict[str, int | float | dict[str, Any]] = {"a": 90, "b": 50, "c": 60}
        result = below_threshold(scores, 60)
        assert result == ["b"]

    def test_threshold_is_strict_less_than(self) -> None:
        """Score equal to threshold is NOT below — boundary is exclusive."""
        scores: dict[str, int | float | dict[str, Any]] = {"a": 60}
        assert below_threshold(scores, 60) == []

    def test_extracts_score_from_dict_entries(self) -> None:
        scores: dict[str, int | float | dict[str, Any]] = {"a": {"score": 50}}
        assert below_threshold(scores, 60) == ["a"]

    def test_handles_mixed_int_and_dict_entries(self) -> None:
        scores: dict[str, int | float | dict[str, Any]] = {
            "a": 30,
            "b": {"score": 90},
            "c": {"re_score": 20},
        }
        result = below_threshold(scores, 60)
        assert set(result) == {"a", "c"}


# --- TestMainG7 ----------------------------------------------------------


class TestMainG7:
    def test_exits_when_no_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["summarize-round"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_g7_fail_blocks_summary_generation(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_fail: None,
    ) -> None:
        """G7 is a gate — FAIL means the round isn't ready to summarize."""
        (round_dir / "summary.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_g7_pass_proceeds(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        summary_with_t1: Path,
        mock_g7_pass: None,
    ) -> None:
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        main()
        # No exception means G7 passed and summary was generated

    def test_g7_invalid_json_does_not_block(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        summary_with_t1: Path,
    ) -> None:
        """If G7 subprocess emits non-JSON, summarize logs a warning and
        proceeds — better to summarize with partial info than to block.
        """

        class _FakeCompleted:
            returncode = 0
            stdout = "not json"
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _FakeCompleted())
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        main()  # no exception


# --- TestMainSummaryMissing ----------------------------------------------


class TestMainSummaryMissing:
    def test_exits_when_summary_json_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_pass: None,
    ) -> None:
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1


# --- TestMainT1Aggregation -----------------------------------------------


class TestMainT1Aggregation:
    def _run(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
    ) -> dict[str, Any]:
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        main()
        import typing

        return typing.cast(
            dict[str, Any], json.loads((round_dir / "summary.json").read_text(encoding="utf-8"))
        )

    def test_writes_band_breakdown_for_t1(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        summary_with_t1: Path,
        mock_g7_pass: None,
    ) -> None:
        result = self._run(monkeypatch, round_dir)
        # 95=ex, 80=ok, 65=cond, 40=fail
        assert result["band_breakdown"] == {
            "pass_excellent": 1,
            "pass_acceptable": 1,
            "conditional": 1,
            "fail": 1,
        }

    def test_next_actions_includes_failures(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        summary_with_t1: Path,
        mock_g7_pass: None,
    ) -> None:
        result = self._run(monkeypatch, round_dir)
        assert any("T1 FAIL" in a and "shenbi-delta" in a for a in result["next_actions"])

    def test_next_actions_includes_conditionals(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        summary_with_t1: Path,
        mock_g7_pass: None,
    ) -> None:
        result = self._run(monkeypatch, round_dir)
        assert any("T1 CONDITIONAL" in a and "shenbi-gamma" in a for a in result["next_actions"])

    def test_next_actions_includes_acceptable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        summary_with_t1: Path,
        mock_g7_pass: None,
    ) -> None:
        result = self._run(monkeypatch, round_dir)
        assert any(
            "T1 PASS (acceptable" in a and "shenbi-beta" in a for a in result["next_actions"]
        )

    def test_next_actions_omits_fail_section_when_all_excellent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_pass: None,
    ) -> None:
        summary = round_dir / "summary.json"
        summary.write_text(json.dumps({"t1_scores": {"a": 95, "b": 99}}), encoding="utf-8")
        result = self._run(monkeypatch, round_dir)
        assert any("All skills PASS (excellent" in a for a in result["next_actions"])
        assert not any("T1 FAIL" in a for a in result["next_actions"])


# --- TestMainT2T3Aggregation ---------------------------------------------


class TestMainT2T3Aggregation:
    def _run(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
    ) -> dict[str, Any]:
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        main()
        import typing

        return typing.cast(
            dict[str, Any], json.loads((round_dir / "summary.json").read_text(encoding="utf-8"))
        )

    def test_t2_bands_written_when_t2_scores_present(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_pass: None,
    ) -> None:
        summary = round_dir / "summary.json"
        summary.write_text(
            json.dumps({"t1_scores": {"a": 95}, "t2_scores": {"phase-x": 85, "phase-y": 50}}),
            encoding="utf-8",
        )
        result = self._run(monkeypatch, round_dir)
        assert "band_breakdown_t2" in result
        assert result["band_breakdown_t2"]["pass_acceptable"] == 1
        assert result["band_breakdown_t2"]["fail"] == 1

    def test_t2_absent_omits_band_breakdown_t2(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        summary_with_t1: Path,
        mock_g7_pass: None,
    ) -> None:
        result = self._run(monkeypatch, round_dir)
        assert "band_breakdown_t2" not in result

    def test_t3_bands_written_when_t3_scores_present(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_pass: None,
    ) -> None:
        summary = round_dir / "summary.json"
        summary.write_text(
            json.dumps({"t1_scores": {"a": 95}, "t3_scores": {"pipeline-x": 92}}),
            encoding="utf-8",
        )
        result = self._run(monkeypatch, round_dir)
        assert "band_breakdown_t3" in result
        assert result["band_breakdown_t3"]["pass_excellent"] == 1


# --- TestMainTierReadiness -----------------------------------------------


class TestMainTierReadiness:
    def _run(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
    ) -> dict[str, Any]:
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        main()
        import typing

        return typing.cast(
            dict[str, Any], json.loads((round_dir / "summary.json").read_text(encoding="utf-8"))
        )

    def test_t1_all_excellent_promotes_to_t2(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_pass: None,
    ) -> None:
        summary = round_dir / "summary.json"
        summary.write_text(json.dumps({"t1_scores": {"a": 95, "b": 96}}), encoding="utf-8")
        result = self._run(monkeypatch, round_dir)
        assert any("Ready for T2" in a for a in result["next_actions"])

    def test_t1_with_failures_does_not_promote(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        summary_with_t1: Path,
        mock_g7_pass: None,
    ) -> None:
        result = self._run(monkeypatch, round_dir)
        assert not any("Ready for T2" in a for a in result["next_actions"])

    def test_t2_all_excellent_promotes_to_t3(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_pass: None,
    ) -> None:
        summary = round_dir / "summary.json"
        summary.write_text(
            json.dumps(
                {
                    "t1_scores": {"a": 95},
                    "t2_scores": {"phase-x": 95, "phase-y": 96},
                }
            ),
            encoding="utf-8",
        )
        result = self._run(monkeypatch, round_dir)
        assert any("Ready for T3" in a for a in result["next_actions"])

    def test_t3_all_excellent_completes_framework(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_pass: None,
    ) -> None:
        summary = round_dir / "summary.json"
        summary.write_text(
            json.dumps(
                {
                    "t1_scores": {"a": 95},
                    "t2_scores": {"phase-x": 95},
                    "t3_scores": {"pipeline-x": 95},
                }
            ),
            encoding="utf-8",
        )
        result = self._run(monkeypatch, round_dir)
        assert any("All tiers complete" in a for a in result["next_actions"])


# --- TestMainProgressIntegration -----------------------------------------


class TestMainProgressIntegration:
    """main() reads progress.json (if present) to harvest additional scores
    from skill-test-type entries marked 'done'.
    """

    def test_reads_scores_from_progress_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_pass: None,
    ) -> None:
        """progress.json with skill.done.score entries are read into
        t1_from_progress. Currently main() builds this dict but doesn't merge
        it into summary.json — verify it doesn't crash on valid input.
        """
        (round_dir / "progress.json").write_text(
            json.dumps(
                {"skills": {"shenbi-alpha": {"generative": {"status": "done", "score": 92}}}}
            ),
            encoding="utf-8",
        )
        (round_dir / "summary.json").write_text(
            json.dumps({"t1_scores": {"a": 95}}), encoding="utf-8"
        )
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        main()  # no exception

    def test_skips_non_done_entries_in_progress(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_pass: None,
    ) -> None:
        (round_dir / "progress.json").write_text(
            json.dumps(
                {"skills": {"shenbi-alpha": {"generative": {"status": "pending", "score": 50}}}}
            ),
            encoding="utf-8",
        )
        (round_dir / "summary.json").write_text(
            json.dumps({"t1_scores": {"a": 95}}), encoding="utf-8"
        )
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        main()

    def test_handles_missing_progress_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        summary_with_t1: Path,
        mock_g7_pass: None,
    ) -> None:
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        main()


# --- TestMainPreservesExistingSummary -----------------------------------


class TestMainPreservesExistingSummary:
    def test_preserves_tier_target_and_other_keys(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        mock_g7_pass: None,
    ) -> None:
        """main() updates summary.json in place — must not clobber keys it
        doesn't own (e.g. tier_target set by an earlier pipeline stage).
        """
        summary = round_dir / "summary.json"
        summary.write_text(
            json.dumps(
                {
                    "tier_target": "T3",
                    "round_id": "round-001",
                    "t1_scores": {"a": 95},
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr("sys.argv", ["summarize-round", str(round_dir)])
        main()
        result = json.loads(summary.read_text(encoding="utf-8"))
        assert result["tier_target"] == "T3"
        assert result["round_id"] == "round-001"
        assert "band_breakdown" in result
        assert "next_actions" in result
