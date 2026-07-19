"""Tests for the revision router (Wave 3 Task 5).

Spec §6.3 — revision routing reuses the existing ``route_revision`` from
``shenbi.skill_utils.revision_routing.route`` and adds:
  * Specialist skill delegation (style-polishing, anti-detect, length-normalizing)
  * Resonance threshold check against ``config.resonance_global_floor``
  * Full §6.3 decision tree (pass / revision / escalation)
  * Escalation dispatch (``shenbi-escalation-review``)
  * Audit issue collection from chapter audit reports
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.revision_router import (
    CHAPTER_REVISION_SKILL,
    ESCALATION_SKILL,
    SPECIALIST_SKILLS,
    RevisionDecision,
    RevisionRoute,
    check_resonance,
    collect_audit_issues,
    decide_revision,
    dispatch_escalation,
    route_chapter_revision,
)


# ---------------------------------------------------------------------------
# Specialist skill mapping (brief verbatim)
# ---------------------------------------------------------------------------
class TestSpecialistSkills:
    def test_polishing_mapped(self):
        assert SPECIALIST_SKILLS["craft_expression"] == "shenbi-style-polishing"

    def test_anti_detect_mapped(self):
        assert SPECIALIST_SKILLS["ai_tell"] == "shenbi-anti-detect"

    def test_length_mapped(self):
        assert SPECIALIST_SKILLS["word_count"] == "shenbi-length-normalizing"

    def test_all_three_specialists(self):
        assert len(SPECIALIST_SKILLS) == 3

    def test_all_values_are_shenbi(self):
        for v in SPECIALIST_SKILLS.values():
            assert v.startswith("shenbi-")

    def test_escalation_skill_constant(self):
        assert ESCALATION_SKILL == "shenbi-escalation-review"

    def test_chapter_revision_skill_constant(self):
        assert CHAPTER_REVISION_SKILL == "shenbi-chapter-revision"


# ---------------------------------------------------------------------------
# route_chapter_revision (brief verbatim + additional)
# ---------------------------------------------------------------------------
class TestRouteChapterRevision:
    def test_craft_only_routes_to_spot_fix(self):
        route = route_chapter_revision(
            issues=[{"category": "craft", "severity": "CRITICAL"}], blocking=False
        )
        assert route == RevisionRoute.SPOT_FIX

    def test_blocking_routes_to_regenerate(self):
        route = route_chapter_revision(
            issues=[{"category": "unmet_goal", "severity": "BLOCKING"}], blocking=True
        )
        assert route == RevisionRoute.REGENERATE

    def test_empty_issues_no_revision(self):
        assert route_chapter_revision(issues=[], blocking=False) == RevisionRoute.NO_REVISION

    def test_constrained_regenerate_when_both_present(self):
        route = route_chapter_revision(
            issues=[
                {"category": "unmet_goal", "severity": "BLOCKING"},
                {"category": "craft", "severity": "CRITICAL"},
            ],
            blocking=True,
        )
        assert route == RevisionRoute.CONSTRAINED_REGENERATE

    def test_minor_craft_still_spot_fix(self):
        route = route_chapter_revision(
            issues=[{"category": "craft", "severity": "MINOR"}], blocking=False
        )
        assert route == RevisionRoute.SPOT_FIX


# ---------------------------------------------------------------------------
# check_resonance (spec §6.3 global floor)
# ---------------------------------------------------------------------------
class TestCheckResonance:
    def test_above_floor_passes(self):
        assert check_resonance(75, floor=65) is True

    def test_at_floor_passes(self):
        assert check_resonance(65, floor=65) is True

    def test_below_floor_fails(self):
        assert check_resonance(49, floor=65) is False

    def test_none_resonance_passes(self):
        """Missing resonance data does not block (defensive)."""
        assert check_resonance(None, floor=65) is True

    def test_default_floor_is_50(self):
        assert check_resonance(50) is True
        assert check_resonance(49) is False


# ---------------------------------------------------------------------------
# decide_revision (full spec §6.3 decision tree)
# ---------------------------------------------------------------------------
class TestDecideRevision:
    def test_blocking_routes_to_revision(self):
        decision = decide_revision(
            issues=[{"category": "unmet_goal", "severity": "BLOCKING"}],
            blocking=True,
            resonance_score=90,
            resonance_floor=65,
        )
        assert decision == RevisionDecision.REVISION

    def test_no_blocking_high_resonance_passes(self):
        decision = decide_revision(
            issues=[], blocking=False, resonance_score=80, resonance_floor=65
        )
        assert decision == RevisionDecision.PASS

    def test_no_blocking_resonance_at_floor_passes(self):
        decision = decide_revision(
            issues=[], blocking=False, resonance_score=64, resonance_floor=65
        )
        assert decision == RevisionDecision.REVISION

    def test_no_blocking_low_resonance_revisions(self):
        decision = decide_revision(
            issues=[], blocking=False, resonance_score=40, resonance_floor=65
        )
        assert decision == RevisionDecision.REVISION

    def test_blocking_overrides_high_resonance(self):
        """Even with high resonance, BLOCKING always requires revision."""
        decision = decide_revision(
            issues=[{"category": "unmet_goal", "severity": "BLOCKING"}],
            blocking=True,
            resonance_score=95,
            resonance_floor=65,
        )
        assert decision == RevisionDecision.REVISION

    def test_none_resonance_no_blocking_passes(self):
        decision = decide_revision(
            issues=[], blocking=False, resonance_score=None, resonance_floor=65
        )
        assert decision == RevisionDecision.PASS

    def test_craft_critical_no_blocking_low_resonance_revisions(self):
        decision = decide_revision(
            issues=[{"category": "craft", "severity": "CRITICAL"}],
            blocking=False,
            resonance_score=30,
            resonance_floor=65,
        )
        assert decision == RevisionDecision.REVISION


# ---------------------------------------------------------------------------
# dispatch_escalation (spec §6.3 escalation-review dispatch)
# ---------------------------------------------------------------------------
PATCH_DISPATCH_ESC = "shenbi.pipeline.revision_router.dispatch_skill"


class TestDispatchEscalation:
    @patch(PATCH_DISPATCH_ESC)
    def test_successful_dispatch(self, mock_disp, tmp_path: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        result = dispatch_escalation(tmp_path, chapter=5)
        assert result is True
        skill = mock_disp.call_args[0][0]
        assert skill == ESCALATION_SKILL

    @patch(PATCH_DISPATCH_ESC)
    def test_dispatch_failure_returns_false(self, mock_disp, tmp_path: Path):
        mock_disp.return_value = DispatchResult(False, 1, "", "error")
        result = dispatch_escalation(tmp_path, chapter=3)
        assert result is False

    @patch(PATCH_DISPATCH_ESC)
    def test_prompt_contains_chapter(self, mock_disp, tmp_path: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        dispatch_escalation(tmp_path, chapter=7)
        prompt = mock_disp.call_args[0][2]
        assert "7" in prompt

    @patch(PATCH_DISPATCH_ESC)
    def test_context_appended_to_prompt(self, mock_disp, tmp_path: Path):
        mock_disp.return_value = DispatchResult(True, 0, "ok", "")
        dispatch_escalation(tmp_path, chapter=2, context="3 audit retries exhausted")
        prompt = mock_disp.call_args[0][2]
        assert "3 audit retries exhausted" in prompt


# ---------------------------------------------------------------------------
# collect_audit_issues (scan audit reports for blocking/critical)
# ---------------------------------------------------------------------------
class TestCollectAuditIssues:
    def test_no_audit_dir_returns_empty(self, tmp_path: Path):
        issues, blocking = collect_audit_issues(tmp_path, chapter=1)
        assert issues == []
        assert blocking is False

    def test_empty_audit_dir_returns_empty(self, tmp_project: Path):
        (tmp_project / "audits").mkdir()
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert issues == []
        assert blocking is False

    def test_blocking_report_sets_flag(self, tmp_project: Path):
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-anti-ai.md").write_text(
            "# Anti-AI\n\n**BLOCKING**: AI tells detected.\n"
        )
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert blocking is True
        assert len(issues) == 1
        assert issues[0]["severity"] == "BLOCKING"

    def test_critical_report_no_blocking(self, tmp_project: Path):
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-pacing.md").write_text(
            "# Pacing\n\n**CRITICAL**: pacing too slow.\n"
        )
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert blocking is False
        assert len(issues) == 1
        assert issues[0]["severity"] == "CRITICAL"

    def test_clean_report_no_issues(self, tmp_project: Path):
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-continuity.md").write_text("# Continuity\n\nAll clear.")
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert issues == []
        assert blocking is False

    def test_multiple_reports_collected(self, tmp_project: Path):
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-anti-ai.md").write_text("**BLOCKING**")
        (audit_dir / "chapter-1-pacing.md").write_text("**CRITICAL**")
        (audit_dir / "chapter-1-continuity.md").write_text("clean")
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert blocking is True
        assert len(issues) == 2

    def test_only_current_chapter_collected(self, tmp_project: Path):
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-anti-ai.md").write_text("**BLOCKING**")
        (audit_dir / "chapter-2-anti-ai.md").write_text("**BLOCKING**")
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert len(issues) == 1

    def test_no_blocking_in_prose_not_detected(self, tmp_project: Path):
        """'No BLOCKING issues detected' must not register as blocking (W3T5 review).

        Regression: the old bare ``"BLOCKING" in content`` substring match
        falsely flagged prose mentions. The matcher now requires a severity
        marker (bolded or severity-keyed).
        """
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-continuity.md").write_text(
            "# Continuity\n\nNo BLOCKING issues detected.\n"
        )
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert issues == []
        assert blocking is False

    def test_no_critical_in_prose_not_detected(self, tmp_project: Path):
        """'No CRITICAL issues' must not register as a critical issue."""
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-pacing.md").write_text("# Pacing\n\nNo CRITICAL issues found.\n")
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert issues == []
        assert blocking is False

    def test_severity_keyed_blocking_detected(self, tmp_project: Path):
        """'severity: BLOCKING' (not bolded) is still a valid severity marker."""
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-character.md").write_text("# Character\n\n- severity: BLOCKING\n")
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert blocking is True
        assert len(issues) == 1
        assert issues[0]["severity"] == "BLOCKING"

    # --- CJK production format (all 20 audit skills emit **严重度**: <LEVEL>) ---
    def test_cjk_bolded_severity_blocking_detected(self, tmp_project: Path):
        """The actual production format '**严重度**: BLOCKING' is recognised.

        This is the format every audit skill's SKILL.md specifies (e.g.
        shenbi-review-pacing, shenbi-review-character). Regression for the
        wave3 task5 re-review: the English-only matcher missed these.
        """
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-pacing.md").write_text(
            "# Pacing\n\n| 问题 | **严重度**: BLOCKING |\n"
        )
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert blocking is True
        assert len(issues) == 1
        assert issues[0]["severity"] == "BLOCKING"

    def test_cjk_plain_severity_blocking_detected(self, tmp_project: Path):
        """Unbolded CJK form '严重度: BLOCKING' is also recognised."""
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-continuity.md").write_text("# Continuity\n\n- 严重度: BLOCKING\n")
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert blocking is True
        assert len(issues) == 1
        assert issues[0]["severity"] == "BLOCKING"

    def test_cjk_severity_critical_detected(self, tmp_project: Path):
        """CJK critical form '**严重度**: CRITICAL' registers as CRITICAL (no blocking)."""
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-texture.md").write_text(
            "# Texture\n\n- **严重度**: CRITICAL (意象不足)\n"
        )
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert blocking is False
        assert len(issues) == 1
        assert issues[0]["severity"] == "CRITICAL"

    def test_cjk_severity_not_blocking_in_prose(self, tmp_project: Path):
        """Bare '严重度' in prose without a BLOCKING value must not flag blocking.

        Guards against re-introducing the false-positive the severity-keyed
        matcher was designed to avoid, now applied to the CJK key.
        """
        audit_dir = tmp_project / "audits"
        audit_dir.mkdir()
        (audit_dir / "chapter-1-dialogue.md").write_text(
            "# Dialogue\n\n所有检查项的严重度均为 MINOR 或更低。\n"
        )
        issues, blocking = collect_audit_issues(tmp_project, chapter=1)
        assert issues == []
        assert blocking is False
