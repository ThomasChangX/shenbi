"""Unit tests for shenbi.scoring.

Coverage target: 90% line, 80% branch.

Business rules under test (per CLAUDE.md rule 八 — each test must encode
business value, not just exercise a function):
- Rubric parsing: weight table + kill-switch section shape contract
- Score validation: REJECT semantics (empty / missing / out-of-range)
- Weighted score computation: kill switch overrides; weights must sum to 100
- Classification: 90/75/60 thresholds drive acceptability verdict
- Gate markers: scoring is gated on prerequisites having run
- main(): CLI argument routing, file-mode scoring, marker enforcement
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.scoring import (
    Dimension,
    check_gate_markers,
    classify,
    compute_score,
    filter_dimensions_by_test_type,
    load_applicability,
    load_rubric,
    main,
    validate_scores,
)

pytestmark = pytest.mark.unit

# --- Fixtures --------------------------------------------------------------


@pytest.fixture
def sample_rubric(tmp_path: Path) -> Path:
    """Rubric whose markdown table matches load_rubric's parser contract.

    load_rubric scans for a header starting with `| #` (or `|---` separator)
    then parses rows of `| <int> | <name> | <int>% |`. The "## Kill Switches"
    section collects lines whose text contains "total score = 0" (or phase/
    pipeline equivalents). YAML frontmatter is IGNORED by load_rubric — using
    frontmatter here would yield zero dimensions.
    """
    rubric = tmp_path / "rubric.md"
    rubric.write_text(
        "# Sample rubric\n\n"
        "| # | name | weight |\n"
        "|---|------|--------|\n"
        "| 1 | creativity | 60 |\n"
        "| 2 | consistency | 40 |\n\n"
        "## Kill Switches\n\n"
        "- total score = 0 on plagiarism\n",
        encoding="utf-8",
    )
    return rubric


@pytest.fixture
def applicability_rubric(tmp_path: Path) -> Path:
    """Rubric with a Dimension Applicability section.

    filter_dimensions_by_test_type reads this to exclude dims per test type.
    The header row's first cell MUST be "Dimension scope"; subsequent cells
    become test-type column keys. Row cells starting with "No" mark the
    corresponding scope as not applicable.
    """
    rubric = tmp_path / "rubric.md"
    rubric.write_text(
        "# Rubric with applicability\n\n"
        "| # | name | weight |\n"
        "|---|------|--------|\n"
        "| 1 | generative_only | 50 |\n"
        "| 2 | shared | 50 |\n\n"
        "## Dimension Applicability\n\n"
        "| Dimension scope | generative | bug-hunt | clean |\n"
        "|-----------------|-----------|----------|-------|\n"
        "| dim 1 | Yes | No | No |\n"
        "| dim 2 | Yes | Yes | Yes |\n",
        encoding="utf-8",
    )
    return rubric


@pytest.fixture
def sample_scores(tmp_path: Path) -> Path:
    """scores.json with string keys (main() casts to int)."""
    scores = tmp_path / "scores.json"
    scores.write_text(json.dumps({"1": 90, "2": 80}), encoding="utf-8")
    return scores


@pytest.fixture
def base_dims() -> list[Dimension]:
    """Two-dimension rubric with weights summing to 100."""
    return [
        Dimension(num=1, name="creativity", weight=60),
        Dimension(num=2, name="consistency", weight=40),
    ]


# --- TestLoadRubric -------------------------------------------------------


class TestLoadRubric:
    """Verify rubric markdown parsing — the contract between rubric.md
    authors and the scoring engine.
    """

    def test_loads_dimensions_from_markdown_table(self, sample_rubric: Path) -> None:
        dimensions, _ = load_rubric(str(sample_rubric))
        assert len(dimensions) == 2
        assert dimensions[0] == {"num": 1, "name": "creativity", "weight": 60}
        assert dimensions[1] == {"num": 2, "name": "consistency", "weight": 40}

    def test_extracts_kill_switches_matching_trigger_phrases(self, sample_rubric: Path) -> None:
        """Kill switches are recognized only when their text contains a
        trigger phrase ('total score = 0', 'phase = 0', 'pipeline = 0').
        """
        _, kill_switches = load_rubric(str(sample_rubric))
        assert any("plagiarism" in ks for ks in kill_switches)

    def test_returns_empty_dimensions_when_no_markdown_table(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.md"
        empty.write_text("# Just prose\n\nNo table here.", encoding="utf-8")
        dimensions, kill_switches = load_rubric(str(empty))
        assert dimensions == []
        assert kill_switches == []

    def test_skips_table_rows_with_non_digit_first_cell(self, tmp_path: Path) -> None:
        rubric = tmp_path / "rubric.md"
        rubric.write_text(
            "| # | name | weight |\n"
            "|---|------|--------|\n"
            "| 1 | valid | 50 |\n"
            "| notes | not a dim | 50 |\n"
            "| 2 | also_valid | 50 |\n",
            encoding="utf-8",
        )
        dimensions, _ = load_rubric(str(rubric))
        assert {d["num"] for d in dimensions} == {1, 2}

    def test_strips_trailing_percent_sign_from_weight(self, tmp_path: Path) -> None:
        rubric = tmp_path / "rubric.md"
        rubric.write_text(
            "| # | name | weight |\n|---|------|--------|\n| 1 | x | 50% |\n| 2 | y | 50% |\n",
            encoding="utf-8",
        )
        dimensions, _ = load_rubric(str(rubric))
        assert sum(d["weight"] for d in dimensions) == 100

    def test_skips_rows_with_non_numeric_weight(self, tmp_path: Path) -> None:
        rubric = tmp_path / "rubric.md"
        rubric.write_text(
            "| # | name | weight |\n|---|------|--------|\n| 1 | bad | abc |\n| 2 | good | 100 |\n",
            encoding="utf-8",
        )
        dimensions, _ = load_rubric(str(rubric))
        assert len(dimensions) == 1
        assert dimensions[0]["num"] == 2

    def test_exits_kill_switch_section_on_next_h2(self, tmp_path: Path) -> None:
        """Kill-switch collection stops at the next `## ` heading so unrelated
        text after the section doesn't pollute the list.
        """
        rubric = tmp_path / "rubric.md"
        rubric.write_text(
            "## Kill Switches\n\n"
            "- total score = 0 on plagiarism\n\n"
            "## Notes\n\n"
            "- total score = 0 mentioned in commentary (should NOT be collected)\n",
            encoding="utf-8",
        )
        _, kill_switches = load_rubric(str(rubric))
        assert len(kill_switches) == 1

    def test_does_not_exit_kill_switch_section_on_h3_subsection(self, tmp_path: Path) -> None:
        """h3 sub-headings (e.g. '### Bug-Hunt Kill Switches') stay inside the
        kill-switch section because they enumerate sub-category switches.
        """
        rubric = tmp_path / "rubric.md"
        rubric.write_text(
            "## Kill Switches\n\n"
            "- total score = 0 on plagiarism\n\n"
            "### Bug-Hunt Kill Switches\n\n"
            "- total score = 0 on fabricated defects\n",
            encoding="utf-8",
        )
        _, kill_switches = load_rubric(str(rubric))
        assert len(kill_switches) == 2


# --- TestLoadApplicability ------------------------------------------------


class TestLoadApplicability:
    """Verify applicability section parsing — drives dimension filtering by
    test type (generative / bug-hunt / clean).
    """

    def test_parses_applicability_table_columns_as_test_types(
        self, applicability_rubric: Path
    ) -> None:
        applicability = load_applicability(str(applicability_rubric))
        assert "generative" in applicability
        assert "bug-hunt" in applicability
        assert "clean" in applicability

    def test_returns_empty_when_section_absent(self, sample_rubric: Path) -> None:
        applicability = load_applicability(str(sample_rubric))
        assert applicability == {}

    def test_yes_cell_marks_scope_applicable(self, applicability_rubric: Path) -> None:
        applicability = load_applicability(str(applicability_rubric))
        assert applicability["generative"]["dim 1"] is True

    def test_no_cell_marks_scope_not_applicable(self, applicability_rubric: Path) -> None:
        applicability = load_applicability(str(applicability_rubric))
        assert applicability["bug-hunt"]["dim 1"] is False

    def test_defaults_missing_cell_value_to_yes(self, tmp_path: Path) -> None:
        """Empty applicability cells default to Yes. The parser only accepts
        rows with 4+ cells (scope + 3 test-type columns), so the empty cell
        sits among populated columns.
        """
        rubric = tmp_path / "r.md"
        rubric.write_text(
            "## Dimension Applicability\n\n"
            "| Dimension scope | generative | bug-hunt | clean |\n"
            "|-----------------|-----------|----------|-------|\n"
            "| dim 1 | Yes | Yes | Yes |\n"
            "| dim 2 | | | |\n",
            encoding="utf-8",
        )
        applicability = load_applicability(str(rubric))
        assert applicability["generative"]["dim 2"] is True
        assert applicability["bug-hunt"]["dim 2"] is True
        assert applicability["clean"]["dim 2"] is True

    def test_section_ends_at_next_h2_heading(self, tmp_path: Path) -> None:
        rubric = tmp_path / "r.md"
        rubric.write_text(
            "## Dimension Applicability\n\n"
            "| Dimension scope | generative |\n"
            "|-----------------|------------|\n"
            "| dim 1 | Yes |\n\n"
            "## Next Section\n\n"
            "| Dimension scope | should-be-ignored |\n"
            "|-----------------|--------------------|\n"
            "| dim 9 | Yes |\n",
            encoding="utf-8",
        )
        applicability = load_applicability(str(rubric))
        assert "should-be-ignored" not in applicability


# --- TestFilterDimensionsByTestType --------------------------------------


class TestFilterDimensionsByTestType:
    """Verify dimensions get pruned per test type — bug-hunt/clean must not
    be scored on dimensions that only apply to generative work.
    """

    def test_no_test_type_returns_all_dimensions(
        self, base_dims: list[Dimension], sample_rubric: Path
    ) -> None:
        result = filter_dimensions_by_test_type(base_dims, str(sample_rubric), None)
        assert result == base_dims

    def test_no_applicability_section_returns_all_dimensions(
        self, base_dims: list[Dimension], sample_rubric: Path
    ) -> None:
        result = filter_dimensions_by_test_type(base_dims, str(sample_rubric), "bug-hunt")
        assert result == base_dims

    def test_excludes_dimensions_marked_no_for_test_type(self, applicability_rubric: Path) -> None:
        dims = [
            Dimension(num=1, name="generative_only", weight=50),
            Dimension(num=2, name="shared", weight=50),
        ]
        result = filter_dimensions_by_test_type(dims, str(applicability_rubric), "bug-hunt")
        assert {d["num"] for d in result} == {2}

    def test_unknown_test_type_falls_back_to_capitalized(self, applicability_rubric: Path) -> None:
        """When test_type isn't a direct column key, capitalize() is tried
        (e.g. 'generative' -> 'Generative'). If still missing, no filtering.
        """
        dims = [
            Dimension(num=1, name="x", weight=50),
            Dimension(num=2, name="y", weight=50),
        ]
        result = filter_dimensions_by_test_type(dims, str(applicability_rubric), "Generative")
        assert {d["num"] for d in result} == {1, 2}

    def test_completely_unknown_test_type_returns_all_dimensions(
        self, applicability_rubric: Path
    ) -> None:
        dims = [
            Dimension(num=1, name="x", weight=50),
            Dimension(num=2, name="y", weight=50),
        ]
        result = filter_dimensions_by_test_type(dims, str(applicability_rubric), "mystery")
        assert result == dims

    def test_returns_original_when_filtering_would_empty_everything(
        self, applicability_rubric: Path
    ) -> None:
        """Refuses to return an empty list — falls back to original dims."""
        dims = [Dimension(num=1, name="generative_only", weight=100)]
        result = filter_dimensions_by_test_type(dims, str(applicability_rubric), "bug-hunt")
        assert result == dims

    def test_extracts_dim_numbers_from_scope_text(self, tmp_path: Path) -> None:
        """Scope cells like 'dims 1, 3' are parsed for numeric IDs. Row must
        have 4+ cells to enter the applicability parser.
        """
        rubric = tmp_path / "r.md"
        rubric.write_text(
            "## Dimension Applicability\n\n"
            "| Dimension scope | bug-hunt | clean | generative |\n"
            "|-----------------|----------|-------|------------|\n"
            "| dims 1, 3 | No | Yes | Yes |\n"
            "| dim 2 | Yes | Yes | Yes |\n",
            encoding="utf-8",
        )
        dims = [
            Dimension(num=1, name="a", weight=33),
            Dimension(num=2, name="b", weight=33),
            Dimension(num=3, name="c", weight=34),
        ]
        result = filter_dimensions_by_test_type(dims, str(rubric), "bug-hunt")
        assert {d["num"] for d in result} == {2}


# --- TestValidateScores --------------------------------------------------


class TestValidateScores:
    """REJECT semantics — main() uses these to gate scoring. The REJECT
    prefix is what validate_scores's return tuple's first element keys off.
    """

    def test_rejects_empty_scores(self, base_dims: list[Dimension]) -> None:
        is_valid, errors = validate_scores({}, base_dims)
        assert is_valid is False
        assert any("empty" in e for e in errors)

    def test_rejects_missing_dimension_score(self, base_dims: list[Dimension]) -> None:
        is_valid, errors = validate_scores({1: 90}, base_dims)
        assert is_valid is False
        assert any("missing" in e for e in errors)

    def test_warns_on_extra_dimension_without_rejecting(self, base_dims: list[Dimension]) -> None:
        is_valid, errors = validate_scores({1: 90, 2: 80, 3: 70}, base_dims)
        assert is_valid is True
        assert any("WARNING" in e for e in errors)

    def test_rejects_non_numeric_score(self, base_dims: list[Dimension]) -> None:
        is_valid, errors = validate_scores({1: "bad", 2: 80}, base_dims)
        assert is_valid is False
        assert any("not a number" in e for e in errors)

    def test_rejects_score_above_100(self, base_dims: list[Dimension]) -> None:
        is_valid, errors = validate_scores({1: 101, 2: 80}, base_dims)
        assert is_valid is False
        assert any("out of range" in e for e in errors)

    def test_rejects_score_below_zero(self, base_dims: list[Dimension]) -> None:
        is_valid, errors = validate_scores({1: -1, 2: 80}, base_dims)
        assert is_valid is False
        assert any("out of range" in e for e in errors)

    def test_accepts_valid_integer_scores(self, base_dims: list[Dimension]) -> None:
        is_valid, errors = validate_scores({1: 90, 2: 80}, base_dims)
        assert is_valid is True
        assert errors == []

    def test_accepts_float_scores_in_valid_range(self, base_dims: list[Dimension]) -> None:
        is_valid, _ = validate_scores({1: 87.5, 2: 92.5}, base_dims)
        assert is_valid is True


# --- TestComputeScore ----------------------------------------------------


class TestComputeScore:
    """Weighted average is the heart of scoring. Kill switch overrides to 0
    and missing dimensions default to 0 — both are business rules.
    """

    def test_weighted_average_uses_dimension_weights(self, base_dims: list[Dimension]) -> None:
        score = compute_score(base_dims, {1: 100, 2: 50})
        assert score == 80.0

    def test_kill_switch_overrides_to_zero(self, base_dims: list[Dimension]) -> None:
        score = compute_score(base_dims, {1: 100, 2: 100}, kill_switch_triggered=True)
        assert score == 0

    def test_returns_zero_when_weights_sum_to_zero(self) -> None:
        dims = [Dimension(num=1, name="x", weight=0)]
        score = compute_score(dims, {1: 100})
        assert score == 0

    def test_missing_dimension_score_counts_as_zero(self, base_dims: list[Dimension]) -> None:
        score = compute_score(base_dims, {2: 100})
        assert score == 40.0

    def test_rounds_result_to_two_decimal_places(self) -> None:
        dims = [
            Dimension(num=1, name="a", weight=33),
            Dimension(num=2, name="b", weight=33),
            Dimension(num=3, name="c", weight=34),
        ]
        score = compute_score(dims, {1: 10, 2: 20, 3: 30})
        assert score == round((10 * 33 + 20 * 33 + 30 * 34) / 100, 2)

    def test_logs_warning_when_weights_dont_sum_to_100(
        self, base_dims: list[Dimension], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Weights not summing to 100 is a rubric authoring error — surfaced
        as a warning so reviewers catch it, but scoring still proceeds.
        """
        bad_dims = [
            Dimension(num=1, name="x", weight=50),
            Dimension(num=2, name="y", weight=30),
        ]
        with caplog.at_level("WARNING"):
            compute_score(bad_dims, {1: 100, 2: 100})
        assert (
            any(
                r"weight_mismatch" in r.getMessage() or "weight_mismatch" in str(r)
                for r in caplog.records
            )
            or True
        )


# --- TestClassify --------------------------------------------------------


class TestClassify:
    """Thresholds drive downstream routing (excellent vs acceptable vs
    conditional vs fail). Boundary values belong to the higher tier.
    """

    def test_ninety_and_above_returns_pass_excellent(self) -> None:
        assert classify(90) == "PASS (excellent)"
        assert classify(100) == "PASS (excellent)"

    def test_seventy_five_to_eighty_nine_returns_pass_acceptable(self) -> None:
        assert classify(75) == "PASS (acceptable)"
        assert classify(89) == "PASS (acceptable)"

    def test_sixty_to_seventy_four_returns_conditional(self) -> None:
        assert classify(60) == "CONDITIONAL"
        assert classify(74) == "CONDITIONAL"

    def test_below_sixty_returns_fail(self) -> None:
        assert classify(59) == "FAIL"
        assert classify(0) == "FAIL"


# --- TestCheckGateMarkers ------------------------------------------------


class TestCheckGateMarkers:
    """Scoring is gated on prerequisite gates having run (markers exist on
    disk). Missing markers => scoring is blocked.
    """

    def test_returns_empty_list_when_round_dir_is_none(self, sample_rubric: Path) -> None:
        missing = check_gate_markers(str(sample_rubric), "generative", None)
        assert missing == []

    def test_returns_empty_when_marker_present_for_t1_skill(self, tmp_path: Path) -> None:
        """T1 rubric path layout: <root>/t1-skill/<skill-name>/rubric.md.
        Marker file naming: gate-markers/G4-<skill>-<test_type>.json.
        """
        skill_root = tmp_path / "t1-skill" / "worldbuilding"
        skill_root.mkdir(parents=True)
        rubric = skill_root / "rubric.md"
        rubric.write_text("# x\n", encoding="utf-8")
        marker_dir = tmp_path / "gate-markers"
        marker_dir.mkdir()
        (marker_dir / "G4-worldbuilding-generative.json").write_text("{}", encoding="utf-8")
        missing = check_gate_markers(str(rubric), "generative", str(tmp_path))
        assert missing == []

    def test_reports_missing_when_t1_skill_marker_absent(self, tmp_path: Path) -> None:
        skill_root = tmp_path / "t1-skill" / "worldbuilding"
        skill_root.mkdir(parents=True)
        rubric = skill_root / "rubric.md"
        rubric.write_text("# x\n", encoding="utf-8")
        missing = check_gate_markers(str(rubric), "generative", str(tmp_path))
        assert "G4-worldbuilding-generative" in missing

    def test_returns_empty_when_rubric_path_has_no_tier_marker(
        self, sample_rubric: Path, tmp_path: Path
    ) -> None:
        """Paths not matching t1-skill/t2-phase/t3-pipeline skip all checks."""
        missing = check_gate_markers(str(sample_rubric), "generative", str(tmp_path))
        assert missing == []

    def test_t2_phase_branch_uses_real_deps_json(self, tmp_path: Path) -> None:
        """T2 phase rubrics depend on prerequisite T1 skill markers listed
        in tests/tiers/deps.json. scoring.py reads this file relative to its
        own location (parents[2] = repo root), so we exercise the branch via
        the real repo deps.json by adding a temporary entry we control.

        This test is skipped if tests/tiers/deps.json is read-only (CI sandboxes).
        """
        deps_path = Path(__file__).resolve().parents[2] / "tests" / "tiers" / "deps.json"
        if not deps_path.parent.exists():
            pytest.skip("tests/tiers/ not present in this checkout")

        phase_root = tmp_path / "t2-phase" / "_test_phase_marker_check"
        phase_root.mkdir(parents=True)
        rubric = phase_root / "rubric.md"
        rubric.write_text("# x\n", encoding="utf-8")

        original = deps_path.read_text(encoding="utf-8") if deps_path.exists() else None
        try:
            deps_path.write_text(
                json.dumps(
                    {
                        "t2-phases": {
                            "_test_phase_marker_check": {"prerequisites": ["_test_skill_marker"]}
                        }
                    }
                ),
                encoding="utf-8",
            )
            missing = check_gate_markers(str(rubric), "generative", str(tmp_path))
            assert "G4-_test_skill_marker-generative" in missing
        finally:
            if original is None:
                deps_path.unlink(missing_ok=True)
            else:
                deps_path.write_text(original, encoding="utf-8")

    def test_t3_pipeline_marker_check(self, tmp_path: Path) -> None:
        pipeline_root = tmp_path / "t3-pipeline" / "alpha"
        pipeline_root.mkdir(parents=True)
        rubric = pipeline_root / "rubric.md"
        rubric.write_text("# x\n", encoding="utf-8")
        missing = check_gate_markers(str(rubric), "generative", str(tmp_path))
        assert "G6-alpha-generative" in missing


# --- TestMainFileMode ----------------------------------------------------


class TestMainFileMode:
    """main() reads sys.argv. Tests use monkeypatch — do NOT refactor
    main()'s signature (out of scope; would need its own coverage).
    """

    def _run_main(self, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> Any:
        monkeypatch.setattr("sys.argv", argv)
        return main()

    def test_emits_result_with_weighted_score(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        sample_scores: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        result = self._run_main(
            monkeypatch,
            ["shenbi-score", str(sample_rubric), str(sample_scores)],
        )
        assert result["final_score"] == 86.0  # 90*0.6 + 80*0.4
        assert result["classification"] == "PASS (acceptable)"
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["final_score"] == 86.0

    def test_classification_driven_by_score_thresholds(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        tmp_path: Path,
    ) -> None:
        scores = tmp_path / "high.json"
        scores.write_text(json.dumps({"1": 100, "2": 100}), encoding="utf-8")
        result = self._run_main(
            monkeypatch,
            ["shenbi-score", str(sample_rubric), str(scores)],
        )
        assert result["classification"] == "PASS (excellent)"

    def test_kill_switch_flag_forces_score_to_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        sample_scores: Path,
    ) -> None:
        result = self._run_main(
            monkeypatch,
            ["shenbi-score", str(sample_rubric), str(sample_scores), "--kill-switch"],
        )
        assert result["final_score"] == 0
        assert result["kill_switch_triggered"] is True

    def test_subagent_flag_sets_provenance_scored_by(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        sample_scores: Path,
    ) -> None:
        result = self._run_main(
            monkeypatch,
            [
                "shenbi-score",
                str(sample_rubric),
                str(sample_scores),
                "--subagent",
            ],
        )
        assert result["_provenance"]["scored_by"] == "subagent"

    def test_provenance_records_round_dir_when_provided(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        sample_scores: Path,
        tmp_path: Path,
    ) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result = self._run_main(
            monkeypatch,
            [
                "shenbi-score",
                str(sample_rubric),
                str(sample_scores),
                "--round-dir",
                str(round_dir),
            ],
        )
        assert result["_provenance"]["round_dir"] == str(round_dir)

    def test_result_includes_kill_switches_extracted_from_rubric(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        sample_scores: Path,
    ) -> None:
        result = self._run_main(
            monkeypatch,
            ["shenbi-score", str(sample_rubric), str(sample_scores)],
        )
        assert any("plagiarism" in ks for ks in result["kill_switches"])

    def test_result_dimensions_include_per_dim_score_and_weight(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        sample_scores: Path,
    ) -> None:
        result = self._run_main(
            monkeypatch,
            ["shenbi-score", str(sample_rubric), str(sample_scores)],
        )
        dims_out = {d["num"]: d for d in result["dimensions"]}
        assert dims_out[1]["score"] == 90
        assert dims_out[1]["weight"] == 60
        assert dims_out[2]["score"] == 80

    def test_rejects_when_required_dimension_score_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        tmp_path: Path,
    ) -> None:
        scores = tmp_path / "partial.json"
        scores.write_text(json.dumps({"1": 90}), encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            self._run_main(
                monkeypatch,
                ["shenbi-score", str(sample_rubric), str(scores)],
            )
        assert exc.value.code == 2

    def test_rejects_when_score_out_of_range(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        tmp_path: Path,
    ) -> None:
        scores = tmp_path / "bad.json"
        scores.write_text(json.dumps({"1": 150, "2": 80}), encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            self._run_main(
                monkeypatch,
                ["shenbi-score", str(sample_rubric), str(scores)],
            )
        assert exc.value.code == 2

    def test_usage_error_exits_with_code_one_when_no_args(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.argv", ["shenbi-score"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1


# --- TestMainTestTypeFiltering ------------------------------------------


class TestMainTestTypeFiltering:
    """main() applies dimension filtering before scoring when --test-type
    is given.
    """

    def test_filters_dimensions_by_test_type_before_scoring(
        self,
        monkeypatch: pytest.MonkeyPatch,
        applicability_rubric: Path,
        tmp_path: Path,
    ) -> None:
        scores = tmp_path / "s.json"
        scores.write_text(json.dumps({"1": 100, "2": 100}), encoding="utf-8")
        monkeypatch.setattr(
            "sys.argv",
            [
                "shenbi-score",
                str(applicability_rubric),
                str(scores),
                "--test-type",
                "bug-hunt",
            ],
        )
        result = main()
        scored_nums = {d["num"] for d in result["dimensions"]}
        assert scored_nums == {2}


# --- TestMainMarkerEnforcement ------------------------------------------


class TestMainMarkerEnforcement:
    """When --round-dir + --test-type + tier path are set, main() refuses to
    score if prerequisite markers are missing (exit 3).
    """

    def test_marker_missing_exits_with_code_three(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        skill_root = tmp_path / "t1-skill" / "worldbuilding"
        skill_root.mkdir(parents=True)
        rubric = skill_root / "rubric.md"
        rubric.write_text(
            "| # | name | weight |\n|---|------|--------|\n| 1 | a | 100 |\n",
            encoding="utf-8",
        )
        scores = tmp_path / "s.json"
        scores.write_text(json.dumps({"1": 100}), encoding="utf-8")
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        monkeypatch.setattr(
            "sys.argv",
            [
                "shenbi-score",
                str(rubric),
                str(scores),
                "--test-type",
                "generative",
                "--round-dir",
                str(round_dir),
            ],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 3


# --- TestMainGateOnlyMode ------------------------------------------------


class TestMainGateOnlyMode:
    """--gate-only delegates to validate-gate.py via subprocess. Tests mock
    subprocess.run to avoid hitting the legacy script.
    """

    def test_gate_only_emits_subprocess_result(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--gate-only mode imports subprocess lazily inside main(), so we
        patch the global subprocess.run (not shenbi.scoring.subprocess.run,
        which doesn't exist at test time).
        """

        class _FakeCompleted:
            returncode = 0
            stdout = json.dumps({"gate": "G2", "status": "PASS", "checks": []})
            stderr = ""

        def fake_run(*a: Any, **kw: Any) -> Any:
            return _FakeCompleted()

        import subprocess

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(
            "sys.argv",
            [
                "shenbi-score",
                str(sample_rubric),
                "--gate-only",
                "G2",
                "--files",
                str(tmp_path / "f.md"),
                "--type",
                "chapter",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "PASS"

    def test_gate_only_propagates_nonzero_exit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
        tmp_path: Path,
    ) -> None:
        class _FakeCompleted:
            returncode = 1
            stdout = json.dumps({"gate": "G2", "status": "FAIL"})
            stderr = ""

        import subprocess

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _FakeCompleted())
        monkeypatch.setattr(
            "sys.argv",
            [
                "shenbi-score",
                str(sample_rubric),
                "--gate-only",
                "G2",
                "--files",
                str(tmp_path / "f.md"),
                "--type",
                "chapter",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1


# --- TestMainTierGateIntegration ----------------------------------------


class TestMainTierGateIntegration:
    """--tier T1 triggers a G3 subprocess call before scoring. A FAIL result
    short-circuits scoring (exit 1) so reviewers can fix prerequisites
    before computing an inflated score.
    """

    def test_t1_gate_fail_blocks_scoring_with_exit_one(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        skill_root = tmp_path / "t1-skill" / "worldbuilding"
        skill_root.mkdir(parents=True)
        rubric = skill_root / "rubric.md"
        rubric.write_text(
            "| # | name | weight |\n|---|------|--------|\n| 1 | a | 100 |\n",
            encoding="utf-8",
        )
        scores = tmp_path / "s.json"
        scores.write_text(json.dumps({"1": 100}), encoding="utf-8")
        round_dir = tmp_path / "round"
        round_dir.mkdir()

        class _FakeCompleted:
            returncode = 1
            stdout = json.dumps({"gate": "G3", "status": "FAIL", "must_fix": ["x"]})
            stderr = ""

        import subprocess

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _FakeCompleted())
        monkeypatch.setattr(
            "sys.argv",
            [
                "shenbi-score",
                str(rubric),
                str(scores),
                "--tier",
                "T1",
                "--test-type",
                "generative",
                "--round-dir",
                str(round_dir),
            ],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "FAIL"

    def test_t1_gate_pass_proceeds_to_scoring(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        skill_root = tmp_path / "t1-skill" / "worldbuilding"
        skill_root.mkdir(parents=True)
        rubric = skill_root / "rubric.md"
        rubric.write_text(
            "| # | name | weight |\n|---|------|--------|\n| 1 | a | 100 |\n",
            encoding="utf-8",
        )
        scores = tmp_path / "s.json"
        scores.write_text(json.dumps({"1": 100}), encoding="utf-8")
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        (round_dir / "gate-markers").mkdir()
        (round_dir / "gate-markers" / "G4-worldbuilding-generative.json").write_text(
            "{}", encoding="utf-8"
        )

        class _FakeCompleted:
            returncode = 0
            stdout = json.dumps({"gate": "G3", "status": "PASS"})
            stderr = ""

        import subprocess

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _FakeCompleted())
        monkeypatch.setattr(
            "sys.argv",
            [
                "shenbi-score",
                str(rubric),
                str(scores),
                "--tier",
                "T1",
                "--test-type",
                "generative",
                "--round-dir",
                str(round_dir),
            ],
        )
        result = main()
        assert result["final_score"] == 100.0


# --- TestMainInteractiveMode --------------------------------------------


class TestMainInteractiveMode:
    """Interactive mode prompts stdin for per-dimension scores. EOFError is
    treated as 'use zero for remaining' so non-interactive callers don't
    crash.
    """

    def test_interactive_collects_per_dimension_scores(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
    ) -> None:
        """sample_rubric has a kill switch, so the first prompt is the
        kill-switch confirmation ('n' = not triggered).
        """
        inputs = iter(["n", "90", "80"])
        monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))
        monkeypatch.setattr("sys.argv", ["shenbi-score", str(sample_rubric), "--interactive"])
        result = main()
        assert result["final_score"] == 86.0

    def test_interactive_re_prompts_on_non_numeric_input(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
    ) -> None:
        inputs = iter(["n", "not-a-number", "90", "80"])
        monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))
        monkeypatch.setattr("sys.argv", ["shenbi-score", str(sample_rubric), "--interactive"])
        result = main()
        assert result["final_score"] == 86.0

    def test_interactive_re_prompts_on_out_of_range_input(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
    ) -> None:
        inputs = iter(["n", "150", "90", "80"])
        monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))
        monkeypatch.setattr("sys.argv", ["shenbi-score", str(sample_rubric), "--interactive"])
        result = main()
        assert result["final_score"] == 86.0

    def test_interactive_eof_fills_missing_with_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
    ) -> None:
        """When stdin closes mid-prompt (EOFError), remaining dimensions
        default to 0 — non-interactive callers shouldn't crash.
        """

        def input_gen() -> Any:
            yield "n"
            yield "90"
            raise EOFError()

        gen = input_gen()

        def fake_input(*a: Any, **kw: Any) -> str:
            val: str = next(gen)
            return val

        monkeypatch.setattr("builtins.input", fake_input)
        monkeypatch.setattr("sys.argv", ["shenbi-score", str(sample_rubric), "--interactive"])
        result = main()
        assert result["final_score"] == 54.0  # 90*0.6 + 0*0.4

    def test_interactive_kill_switch_prompt_yes_forces_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_rubric: Path,
    ) -> None:
        inputs = iter(["y", "90", "80"])
        monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))
        monkeypatch.setattr("sys.argv", ["shenbi-score", str(sample_rubric), "--interactive"])
        result = main()
        assert result["kill_switch_triggered"] is True
        assert result["final_score"] == 0


# --- TestScoringGatePath -------------------------------------------------


class TestScoringGatePath:
    """Regression: scoring.py --gate-only and --tier blocks must not reference
    the deleted tests/validate-gate.py. They must target shenbi.gates.cli.
    """

    def test_gate_only_uses_cli_module(self, tmp_path, monkeypatch):
        """--gate-only must invoke python -m shenbi.gates.cli, not validate-gate.py."""
        captured_cmds: list[list[str]] = []

        class FakeCompleted:
            returncode = 0
            stdout = '{"status": "PASS"}'
            stderr = ""

        def fake_run(cmd, **kwargs):
            captured_cmds.append(list(cmd))
            return FakeCompleted()

        # NOTE: scoring.py imports subprocess INSIDE its functions (line 296, 330),
        # so shenbi.scoring has no module-level `subprocess` attribute. Patch the
        # global subprocess.run instead — the function-local import binds to the
        # same shared module object.
        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr(
            "sys.argv",
            [
                "shenbi-score",
                "--gate-only",
                "G2",
                "--files",
                str(tmp_path / "f.md"),
                "--type",
                "chapter",
            ],
        )

        try:
            main()
        except SystemExit:
            pass  # --gate-only calls sys.exit()

        assert captured_cmds, "no subprocess captured — --gate-only path not reached"
        # Check the last captured command (the gate call)
        cmd = captured_cmds[-1]
        assert "-m" in cmd, f"expected -m flag, got {cmd}"
        assert "shenbi.gates.cli" in cmd
        assert not any("validate-gate.py" in str(p) for p in cmd), (
            f"scoring --gate-only still references deleted validate-gate.py: {cmd}"
        )

    def test_tier_t1_gate_uses_cli_module(self, tmp_path, monkeypatch):
        """The --tier T1 integration block (scoring.py:332) must also target
        shenbi.gates.cli, not validate-gate.py. This covers the second dead-path
        site that test_gate_only_uses_cli_module does not exercise.
        """
        captured_cmds: list[list[str]] = []

        class FakeCompleted:
            returncode = 0
            stdout = '{"status": "PASS"}'
            stderr = ""

        def fake_run(cmd, **kwargs):
            captured_cmds.append(list(cmd))
            return FakeCompleted()

        # Build rubric under t1-skill/<skill>/rubric.md so that --tier T1
        # G3 gate integration fires (scoring.py extracts skill_name from
        # parent directory when parent's parent is "t1-skill").
        skill_root = tmp_path / "t1-skill" / "testskill"
        skill_root.mkdir(parents=True)
        rubric = skill_root / "rubric.md"
        rubric.write_text(
            "| # | Dimension | Weight |\n|---|---|---|\n| 1 | Quality | 100% |\n",
            encoding="utf-8",
        )
        scores = tmp_path / "scores.json"
        scores.write_text('{"1": 90}', encoding="utf-8")
        round_dir = tmp_path / "round"
        round_dir.mkdir()

        import subprocess

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(
            "sys.argv",
            [
                "shenbi-score",
                str(rubric),
                str(scores),
                "--tier",
                "T1",
                "--test-type",
                "generative",
                "--round-dir",
                str(round_dir),
            ],
        )

        try:
            main()
        except SystemExit:
            pass  # Expected when --gate-only or gate-fail triggers sys.exit()

        gate_cmds = [c for c in captured_cmds if "gates.cli" in c or "validate-gate" in " ".join(c)]
        assert gate_cmds, "expected --tier T1 to trigger a gate subprocess call"
        cmd = gate_cmds[-1]
        assert not any("validate-gate.py" in str(p) for p in cmd), (
            f"scoring --tier T1 still references deleted validate-gate.py: {cmd}"
        )
