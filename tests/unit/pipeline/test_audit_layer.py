"""Tests for the audit sub-orchestrator: genre circle + boundary circle.

Wave 3 Task 4 — spec section 6.2 three-circle audit layer. This module covers
the genre circle (gate-driven activation from genre-config.json) and the
boundary circle (deterministic chapter-number triggers). The core circle
runs as regular chapter_loop steps 10-16 before run_audit_layer is called.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from shenbi.pipeline.audit_layer import (
    AUDIT_DIR,
    BOUNDARY_TRIGGERS,
    GENRE_ACTIVATION_MATRIX,
    AuditResult,
    audit_relative_path,
    get_active_boundary_audits,
    get_active_genre_audits,
    run_audit_layer,
)
from shenbi.pipeline.dispatch_helper import DispatchResult

PATCH_DISPATCH = "shenbi.pipeline.audit_layer.dispatch_skill"
PATCH_G4 = "shenbi.pipeline.audit_layer.run_gate_g4"


# ---------------------------------------------------------------------------
# Genre-circle activation matrix (spec section 6.2)
# ---------------------------------------------------------------------------
class TestActivationMatrix:
    def test_era_maps_to_review_era(self):
        assert GENRE_ACTIVATION_MATRIX["era"] == "shenbi-review-era"

    def test_sensitivity_maps(self):
        assert GENRE_ACTIVATION_MATRIX["sensitivity"] == "shenbi-review-sensitivity"

    def test_all_9_genre_skills_mapped(self):
        assert len(GENRE_ACTIVATION_MATRIX) == 9

    def test_all_values_are_shenbi_review(self):
        for v in GENRE_ACTIVATION_MATRIX.values():
            assert v.startswith("shenbi-review-")

    def test_world_rules_key(self):
        assert GENRE_ACTIVATION_MATRIX["world_rules"] == "shenbi-review-world-rules"

    def test_highpoint_focus_key(self):
        assert GENRE_ACTIVATION_MATRIX["highpoint_focus"] == "shenbi-review-highpoint"


# ---------------------------------------------------------------------------
# Boundary-circle triggers (spec section 6.2)
# ---------------------------------------------------------------------------
class TestBoundaryTriggers:
    def test_long_span_24(self):
        assert BOUNDARY_TRIGGERS["shenbi-review-long-span"](24) is True

    def test_long_span_48(self):
        assert BOUNDARY_TRIGGERS["shenbi-review-long-span"](48) is True

    def test_long_span_23(self):
        assert BOUNDARY_TRIGGERS["shenbi-review-long-span"](23) is False

    def test_chapter_pattern_6(self):
        assert BOUNDARY_TRIGGERS["shenbi-chapter-pattern"](6) is True

    def test_chapter_pattern_12(self):
        assert BOUNDARY_TRIGGERS["shenbi-chapter-pattern"](12) is True

    def test_chapter_pattern_5(self):
        assert BOUNDARY_TRIGGERS["shenbi-chapter-pattern"](5) is False

    def test_arc_payoff_disabled_by_default(self):
        assert BOUNDARY_TRIGGERS["shenbi-review-arc-payoff"](100) is False

    def test_spinoff_disabled_by_default(self):
        assert BOUNDARY_TRIGGERS["shenbi-review-spinoff"](100) is False

    def test_all_4_boundary_skills(self):
        assert len(BOUNDARY_TRIGGERS) == 4


# ---------------------------------------------------------------------------
# Genre-circle activation logic
# ---------------------------------------------------------------------------
class TestGetActiveGenreAudits:
    def test_empty_config_returns_empty(self):
        assert get_active_genre_audits({}) == []

    def test_no_audit_dimensions_key(self):
        assert get_active_genre_audits({"other": 1}) == []

    def test_all_active(self):
        gc = {"audit_dimensions": dict.fromkeys(GENRE_ACTIVATION_MATRIX, True)}
        result = get_active_genre_audits(gc)
        assert len(result) == 9
        assert "shenbi-review-era" in result
        assert "shenbi-review-sensitivity" in result

    def test_subset_active(self):
        gc = {"audit_dimensions": {"era": True, "sensitivity": True, "dialogue_focus": False}}
        result = get_active_genre_audits(gc)
        assert result == ["shenbi-review-era", "shenbi-review-sensitivity"]

    def test_false_values_excluded(self):
        gc = {"audit_dimensions": {"texture_focus": False}}
        assert get_active_genre_audits(gc) == []

    def test_non_dict_audit_dimensions(self):
        assert get_active_genre_audits({"audit_dimensions": "not-a-dict"}) == []


# ---------------------------------------------------------------------------
# Boundary-circle activation logic
# ---------------------------------------------------------------------------
class TestGetActiveBoundaryAudits:
    def test_chapter_1_nothing(self):
        assert get_active_boundary_audits(1) == []

    def test_chapter_5_nothing(self):
        assert get_active_boundary_audits(5) == []

    def test_chapter_6_pattern(self):
        result = get_active_boundary_audits(6)
        assert "shenbi-chapter-pattern" in result
        assert "shenbi-review-long-span" not in result

    def test_chapter_23_nothing(self):
        assert get_active_boundary_audits(23) == []

    def test_chapter_24_both(self):
        result = get_active_boundary_audits(24)
        assert "shenbi-review-long-span" in result
        assert "shenbi-chapter-pattern" in result

    def test_chapter_48_both(self):
        result = get_active_boundary_audits(48)
        assert "shenbi-review-long-span" in result
        assert "shenbi-chapter-pattern" in result


# ---------------------------------------------------------------------------
# Audit file path helper
# ---------------------------------------------------------------------------
class TestAuditRelativePath:
    def test_review_skill_strips_prefix(self):
        assert audit_relative_path(5, "shenbi-review-era") == "audits/chapter-5-era.md"

    def test_chapter_pattern_skill(self):
        assert (
            audit_relative_path(6, "shenbi-chapter-pattern")
            == "audits/chapter-6-chapter-pattern.md"
        )

    def test_review_long_span(self):
        assert (
            audit_relative_path(24, "shenbi-review-long-span") == "audits/chapter-24-long-span.md"
        )


# ---------------------------------------------------------------------------
# run_audit_layer end-to-end (dispatch + G4 + severity scan)
# ---------------------------------------------------------------------------
class TestRunAuditLayerNoActive:
    def test_no_active_audits_clean(self, tmp_project: Path):
        result = run_audit_layer(tmp_project, 1, {})
        assert result.blocking_found is False
        assert result.critical_found is False
        assert result.audit_reports == []
        assert result.issues == []


class TestRunAuditLayer:
    @patch(PATCH_G4)
    @patch(PATCH_DISPATCH)
    def test_genre_audit_pass(self, mock_disp, mock_g4, tmp_project: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        mock_g4.return_value = {"status": "PASS"}
        gc = {"audit_dimensions": {"era": True}}
        result = run_audit_layer(tmp_project, 1, gc)
        assert result.blocking_found is False
        assert len(result.audit_reports) == 1
        assert "chapter-1-era" in result.audit_reports[0]
        assert result.issues == []

    @patch(PATCH_G4)
    @patch(PATCH_DISPATCH)
    def test_blocking_in_content_sets_flag(self, mock_disp, mock_g4, tmp_project: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        mock_g4.return_value = {"status": "PASS"}
        audit_dir = tmp_project / AUDIT_DIR
        audit_dir.mkdir()
        (audit_dir / "chapter-1-era.md").write_text(
            "# Era Review\n\n**BLOCKING**: anachronism detected.\n"
        )
        gc = {"audit_dimensions": {"era": True}}
        result = run_audit_layer(tmp_project, 1, gc)
        assert result.blocking_found is True
        assert len(result.issues) == 1
        assert result.issues[0]["severity"] == "BLOCKING"
        assert result.issues[0]["skill"] == "shenbi-review-era"

    @patch(PATCH_G4)
    @patch(PATCH_DISPATCH)
    def test_critical_in_content_sets_flag(self, mock_disp, mock_g4, tmp_project: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        mock_g4.return_value = {"status": "PASS"}
        audit_dir = tmp_project / AUDIT_DIR
        audit_dir.mkdir()
        (audit_dir / "chapter-6-chapter-pattern.md").write_text(
            "# Pattern Review\n\n**CRITICAL**: repetitive chapter type.\n"
        )
        result = run_audit_layer(tmp_project, 6, {})
        assert result.critical_found is True
        assert result.blocking_found is False
        assert len(result.issues) == 1
        assert result.issues[0]["severity"] == "CRITICAL"

    @patch(PATCH_G4)
    @patch(PATCH_DISPATCH)
    def test_dispatch_failure_records_blocking(self, mock_disp, mock_g4, tmp_project: Path):
        mock_disp.return_value = DispatchResult(False, 1, "", "dispatch error")
        gc = {"audit_dimensions": {"era": True}}
        result = run_audit_layer(tmp_project, 1, gc)
        assert result.blocking_found is True
        assert len(result.issues) == 1
        assert result.issues[0]["source"] == "dispatch"
        mock_g4.assert_not_called()

    @patch(PATCH_G4)
    @patch(PATCH_DISPATCH)
    def test_g4_failure_records_blocking(self, mock_disp, mock_g4, tmp_project: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        mock_g4.return_value = {"status": "FAIL", "error": "structure"}
        gc = {"audit_dimensions": {"era": True}}
        result = run_audit_layer(tmp_project, 1, gc)
        assert result.blocking_found is True
        assert len(result.issues) == 1
        assert result.issues[0]["source"] == "g4"

    @patch(PATCH_G4)
    @patch(PATCH_DISPATCH)
    def test_genre_and_boundary_combined(self, mock_disp, mock_g4, tmp_project: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        mock_g4.return_value = {"status": "PASS"}
        gc = {"audit_dimensions": {"era": True}}
        result = run_audit_layer(tmp_project, 24, gc)
        assert mock_disp.call_count == 3  # era + long-span + chapter-pattern
        assert len(result.audit_reports) == 3

    @patch(PATCH_G4)
    @patch(PATCH_DISPATCH)
    def test_boundary_only_no_genre_config(self, mock_disp, mock_g4, tmp_project: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        mock_g4.return_value = {"status": "PASS"}
        result = run_audit_layer(tmp_project, 12, {})
        assert mock_disp.call_count == 1  # chapter-pattern only
        assert "chapter-12-chapter-pattern" in result.audit_reports[0]

    @patch(PATCH_G4)
    @patch(PATCH_DISPATCH)
    def test_passes_correct_prompt(self, mock_disp, mock_g4, tmp_project: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        mock_g4.return_value = {"status": "PASS"}
        gc = {"audit_dimensions": {"era": True}}
        run_audit_layer(tmp_project, 7, gc)
        prompt = mock_disp.call_args[0][2]
        assert "shenbi-review-era" in prompt
        assert "7" in prompt

    @patch(PATCH_G4)
    @patch(PATCH_DISPATCH)
    def test_missing_audit_file_no_crash(self, mock_disp, mock_g4, tmp_project: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        mock_g4.return_value = {"status": "PASS"}
        gc = {"audit_dimensions": {"era": True}}
        # No audit file created — should not crash, no severity flags.
        result = run_audit_layer(tmp_project, 1, gc)
        assert result.blocking_found is False
        assert result.critical_found is False


class TestAuditResultDefaults:
    def test_defaults(self):
        r = AuditResult()
        assert r.blocking_found is False
        assert r.critical_found is False
        assert r.audit_reports == []
        assert r.issues == []
