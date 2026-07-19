"""Comprehensive cross-wave integration tests (Wave 5 Task 4).

Covers edge cases and cross-wave interactions not exercised by the focused
W5T1 (genesis -> chapter-loop) and W5T2 (full chapter loop) suites:

  * staging commit-on-approve through the CLI review surface
  * revision routing from audit-circle results (BLOCKING vs CRITICAL vs clean)
  * the deterministic trigger system (arc-cycle at ch%12, book closure)
  * centralized error handling / retry + escalation predicates (spec S11)
  * the full 10-step closure flow pausing at the book-closure checkpoint

Only the external subprocess boundaries (skill dispatch, G3/G4 gate CLIs) are
mocked; the orchestrator logic under test is the real code.

NOTE on location: placed in ``tests/unit/pipeline/`` rather than the brief's
``tests/integration/pipeline/`` to honour the project-wide convention recorded
in the SDD progress ledger ("Tests in tests/unit/pipeline/") and to share the
pipeline conftest. (Same rationale as W5T1's test_genesis_to_loop.py and
W5T2's test_chapter_loop_full.py.)

Brief divergences (adapted to the real implementation):
  * TestClosureFlow: the closure runner pauses at the book-closure checkpoint
    AFTER step 9, so only 9 skills dispatch before the pause (step 10,
    snapshot-manage, runs after the checkpoint is cleared). The brief asserted
    a count of 10; the correct count is 9.
  * TestClosureFlow also mocks ``run_gate_g3`` (closure steps 4 and 8 have
    ``requires_g3=True``); without it the real G3 subprocess would run.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from shenbi.pipeline.cli import main
from shenbi.pipeline.crash_recovery import reset_emergency_state
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.error_handler import (
    handle_dispatch_failure,
    handle_scoring_failure,
)
from shenbi.pipeline.machine import load_state, save_state
from shenbi.pipeline.revision_router import RevisionRoute, route_chapter_revision
from shenbi.pipeline.state import (
    ClosureState,
    GenesisState,
    PipelinePhase,
    PipelineState,
)
from shenbi.pipeline.triggers import check_triggers

# Every dispatched step passes G4; closure steps 4/8 additionally pass G3.
_GATE_PASS = {"status": "PASS"}


@pytest.fixture(autouse=True)
def _reset_crash_state():
    """Prevent cross-test contamination of module-level emergency globals under xdist."""
    reset_emergency_state()


# ---------------------------------------------------------------------------
# Staging -> checkpoint -> review commit (cross-wave: checkpoint.py + cli.py)
# ---------------------------------------------------------------------------


class TestStagingIntegration:
    """Verify staging files are committed to final paths on checkpoint approve."""

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_staging_committed_on_approve(self, mock_g4, mock_disp, tmp_path: Path) -> None:
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = _GATE_PASS

        project = tmp_path / "novel"
        project.mkdir()
        state = PipelineState.default(str(project))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.genesis.state = GenesisState.COMPLETED
        state.chapter_loop.current_chapter = 1
        save_state(project, state)

        # Simulate the dispatched chapter-planning skill writing to staging/.
        staging_dir = project / "staging" / "plans"
        staging_dir.mkdir(parents=True)
        (staging_dir / "chapter-1-plan.md").write_text("# Plan", encoding="utf-8")

        # Run next -> chapter 1 advances past steps 1-2 to the chapter-memo
        # checkpoint (chapter-planning is a staging-gated step).
        assert main(["next", str(project)]) == 0
        state = load_state(project)
        assert state.pending_checkpoint.type.value == "chapter-memo"

        # Approve the checkpoint -> staging is committed to its final path.
        assert main(["review", str(project), "approve"]) == 0
        assert (project / "plans" / "chapter-1-plan.md").exists()


# ---------------------------------------------------------------------------
# Revision routing (cross-wave: audit_circle -> revision_router)
# ---------------------------------------------------------------------------


class TestRevisionRouting:
    """Revision router routes audit issues to the correct revision mode."""

    def test_revision_routes_craft_to_spot_fix(self) -> None:
        """A craft-only CRITICAL issue routes to SPOT_FIX (surface polishing)."""
        route = route_chapter_revision(
            issues=[{"category": "craft", "severity": "CRITICAL"}], blocking=False
        )
        assert route == RevisionRoute.SPOT_FIX

    def test_revision_routes_blocking_to_regenerate(self) -> None:
        """A BLOCKING unmet-goal issue routes to REGENERATE."""
        route = route_chapter_revision(
            issues=[{"category": "unmet_goal", "severity": "BLOCKING"}], blocking=True
        )
        assert route == RevisionRoute.REGENERATE


class TestRevisionRoutingFromAuditResults:
    """Audit BLOCKING/CRITICAL results feed into the revision router."""

    def test_blocking_audit_routes_to_regenerate(self, tmp_path: Path) -> None:
        """A BLOCKING audit report routes the chapter to REGENERATE."""
        audits_dir = tmp_path / "novel" / "audits"
        audits_dir.mkdir(parents=True)
        (audits_dir / "chapter-5-continuity.md").write_text(
            "## Audit Report\n\nSeverity: BLOCKING\nIssue: Timeline contradiction",
            encoding="utf-8",
        )

        issues: list[dict[str, str]] = []
        blocking = False
        for audit_file in audits_dir.glob("chapter-5-*.md"):
            text = audit_file.read_text(encoding="utf-8")
            if "BLOCKING" in text:
                blocking = True
                issues.append({"category": "unmet_goal", "severity": "BLOCKING"})
            elif "CRITICAL" in text:
                issues.append({"category": "craft", "severity": "CRITICAL"})

        route = route_chapter_revision(issues=issues, blocking=blocking)
        assert route == RevisionRoute.REGENERATE
        assert blocking is True

    def test_craft_only_routes_to_spot_fix(self, tmp_path: Path) -> None:
        """An audit with only CRITICAL (no BLOCKING) routes to SPOT_FIX."""
        audits_dir = tmp_path / "novel" / "audits"
        audits_dir.mkdir(parents=True)
        (audits_dir / "chapter-5-pacing.md").write_text(
            "## Audit Report\n\nSeverity: CRITICAL\nIssue: Pacing too slow",
            encoding="utf-8",
        )

        issues: list[dict[str, str]] = []
        blocking = False
        for audit_file in audits_dir.glob("chapter-5-*.md"):
            text = audit_file.read_text(encoding="utf-8")
            if "BLOCKING" in text:
                blocking = True
                issues.append({"category": "unmet_goal", "severity": "BLOCKING"})
            elif "CRITICAL" in text:
                issues.append({"category": "craft", "severity": "CRITICAL"})

        route = route_chapter_revision(issues=issues, blocking=blocking)
        assert route == RevisionRoute.SPOT_FIX
        assert blocking is False

    def test_clean_chapter_no_revision(self) -> None:
        """No audit issues -> revision routing returns NO_REVISION."""
        route = route_chapter_revision(issues=[], blocking=False)
        assert route == RevisionRoute.NO_REVISION


# ---------------------------------------------------------------------------
# Trigger system (cross-wave: chapter_loop -> triggers)
# ---------------------------------------------------------------------------


class TestTriggerSystem:
    """The deterministic trigger calendar fires on the expected chapters."""

    def test_l2_trigger_at_ch12(self) -> None:
        """ch%12 fires the arc-cycle: memory-distill L2 + score-arc."""
        result = check_triggers(PipelineState.default("/x"), 12, 67)
        assert result.l2_distill and result.score_arc

    def test_closure_trigger_at_last_chapter(self) -> None:
        """Ch == total_chapters fires the book-closure trigger."""
        result = check_triggers(PipelineState.default("/x"), 67, 67)
        assert result.book_closure


# ---------------------------------------------------------------------------
# Error handling (cross-wave: orchestrators -> error_handler)
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Retry vs escalation predicates from the centralized error handler (S11)."""

    def test_dispatch_failure_increments_retry(self) -> None:
        """handle_dispatch_failure retries below the limit, escalates at it."""
        state = PipelineState.default("/x")
        assert handle_dispatch_failure(state, "test-skill", 1) is True  # retry
        assert handle_dispatch_failure(state, "test-skill", 2) is True  # retry
        assert handle_dispatch_failure(state, "test-skill", 3) is False  # escalate

    def test_scoring_failure_exit_code_routing(self) -> None:
        """handle_scoring_failure has recovery paths for exit 2 and 3 only."""
        state = PipelineState.default("/x")
        assert handle_scoring_failure(state, 2) is True  # validation fail -> retry
        assert handle_scoring_failure(state, 3) is True  # marker missing -> retry
        assert handle_scoring_failure(state, 1) is False  # other error -> give up


# ---------------------------------------------------------------------------
# Closure flow (cross-wave: closure runner -> checkpoint -> transitions)
# ---------------------------------------------------------------------------


class TestClosureFlow:
    """The 10-step closure sequence pauses at the book-closure checkpoint."""

    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    @patch("shenbi.pipeline.closure.run_gate_g3")
    def test_closure_runs_all_steps(self, mock_g3, mock_g4, mock_disp, tmp_path: Path) -> None:
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = _GATE_PASS
        mock_g3.return_value = _GATE_PASS

        project = tmp_path / "novel"
        project.mkdir()
        state = PipelineState.default(str(project))
        state.phase = PipelinePhase.CLOSURE
        state.closure = ClosureState.IN_PROGRESS
        save_state(project, state)

        # Run next -> steps 1-9 run, then the book-closure checkpoint is raised
        # before step 10 (snapshot-manage), which is gated on approval.
        assert main(["next", str(project)]) == 0

        state = load_state(project)
        assert state.pending_checkpoint.type.value == "book-closure"
        # 9 closure steps dispatch before the pause (step 10 is post-checkpoint).
        assert mock_disp.call_count == 9
        assert state.closure_step == 9
