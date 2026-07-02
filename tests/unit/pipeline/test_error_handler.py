"""Tests for centralized error handling and retry logic (Wave 3 Task 8).

Covers spec section 11:
  - dispatch/gate failure: retry <= MAX_DISPATCH_RETRIES, then escalate
  - audit BLOCKING: revision loop <= MAX_AUDIT_RETRIES, then escalate
  - scoring failure: exit code 2 -> re-dispatch, exit code 3 -> run G4 first
  - state-settling failure: mark settling_failed + escalation checkpoint
  - configurable limits via state.config.max_revision_retries / max_audit_retries
"""

from __future__ import annotations

from shenbi.pipeline.error_handler import (
    MAX_AUDIT_RETRIES,
    MAX_DISPATCH_RETRIES,
    handle_audit_blocking,
    handle_dispatch_failure,
    handle_scoring_failure,
    handle_state_settle_failure,
)
from shenbi.pipeline.state import (
    CheckpointType,
    PipelinePhase,
    PipelineState,
)


# ---------------------------------------------------------------------------
# Brief verbatim tests
# ---------------------------------------------------------------------------
class TestBriefVerbatim:
    def test_first_failure_allows_retry(self):
        state = PipelineState.default("/x")
        assert handle_dispatch_failure(state, "shenbi-worldbuilding", 1) is True  # retry

    def test_third_failure_escalates(self):
        state = PipelineState.default("/x")
        assert handle_dispatch_failure(state, "shenbi-worldbuilding", 3) is False  # escalate


# ---------------------------------------------------------------------------
# handle_dispatch_failure
# ---------------------------------------------------------------------------
class TestHandleDispatchFailure:
    def test_first_attempt_retries(self):
        state = PipelineState.default("/x")
        assert handle_dispatch_failure(state, "skill-a", 1) is True

    def test_second_attempt_retries(self):
        state = PipelineState.default("/x")
        assert handle_dispatch_failure(state, "skill-a", 2) is True

    def test_third_attempt_escalates(self):
        state = PipelineState.default("/x")
        assert handle_dispatch_failure(state, "skill-a", 3) is False

    def test_fourth_attempt_escalates(self):
        """Beyond the limit stays escalate (defensive)."""
        state = PipelineState.default("/x")
        assert handle_dispatch_failure(state, "skill-a", 4) is False

    def test_respects_configured_max_revision_retries(self):
        """When config lowers the limit, escalation triggers sooner."""
        state = PipelineState.default("/x")
        state.config.max_revision_retries = 2
        assert handle_dispatch_failure(state, "skill-a", 1) is True
        assert handle_dispatch_failure(state, "skill-a", 2) is False


# ---------------------------------------------------------------------------
# handle_audit_blocking
# ---------------------------------------------------------------------------
class TestHandleAuditBlocking:
    def test_zero_revisions_allows_retry(self):
        state = PipelineState.default("/x")
        assert handle_audit_blocking(state, 1, 0) is True

    def test_one_revision_allows_retry(self):
        state = PipelineState.default("/x")
        assert handle_audit_blocking(state, 1, 1) is True

    def test_two_revisions_allows_retry(self):
        state = PipelineState.default("/x")
        assert handle_audit_blocking(state, 1, 2) is True

    def test_three_revisions_escalates(self):
        state = PipelineState.default("/x")
        assert handle_audit_blocking(state, 1, 3) is False

    def test_respects_configured_max_audit_retries(self):
        state = PipelineState.default("/x")
        state.config.max_audit_retries = 2
        assert handle_audit_blocking(state, 1, 1) is True
        assert handle_audit_blocking(state, 1, 2) is False


# ---------------------------------------------------------------------------
# handle_scoring_failure
# ---------------------------------------------------------------------------
class TestHandleScoringFailure:
    def test_exit_code_2_allows_retry(self):
        state = PipelineState.default("/x")
        assert handle_scoring_failure(state, 2) is True

    def test_exit_code_3_allows_retry(self):
        state = PipelineState.default("/x")
        assert handle_scoring_failure(state, 3) is True

    def test_exit_code_1_no_retry(self):
        state = PipelineState.default("/x")
        assert handle_scoring_failure(state, 1) is False

    def test_exit_code_0_no_retry(self):
        state = PipelineState.default("/x")
        assert handle_scoring_failure(state, 0) is False

    def test_negative_exit_code_no_retry(self):
        state = PipelineState.default("/x")
        assert handle_scoring_failure(state, -1) is False


# ---------------------------------------------------------------------------
# handle_state_settle_failure
# ---------------------------------------------------------------------------
class TestHandleStateSettleFailure:
    def test_marks_chapter_status_settling_failed(self):
        state = PipelineState.default("/x")
        handle_state_settle_failure(state, 5)
        cs = state.chapter_loop.chapter_states["5"]
        assert cs.status == "settling_failed"

    def test_raises_escalation_checkpoint(self):
        state = PipelineState.default("/x")
        handle_state_settle_failure(state, 5)
        assert state.pending_checkpoint.type == CheckpointType.ESCALATION
        assert state.pending_checkpoint.chapter == 5

    def test_phase_stays_chapter_loop(self):
        """Spec: state stays chapter-loop:in-progress so user can resolve+resume."""
        state = PipelineState.default("/x")
        state.phase = PipelinePhase.CHAPTER_LOOP
        handle_state_settle_failure(state, 5)
        assert state.phase == PipelinePhase.CHAPTER_LOOP

    def test_creates_chapter_state_if_missing(self):
        state = PipelineState.default("/x")
        assert "3" not in state.chapter_loop.chapter_states
        handle_state_settle_failure(state, 3)
        assert "3" in state.chapter_loop.chapter_states
        assert state.chapter_loop.chapter_states["3"].status == "settling_failed"

    def test_overwrites_existing_chapter_status(self):
        state = PipelineState.default("/x")
        from shenbi.pipeline.state import ChapterState

        state.chapter_loop.chapter_states["7"] = ChapterState(status="complete")
        handle_state_settle_failure(state, 7)
        assert state.chapter_loop.chapter_states["7"].status == "settling_failed"


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------
class TestConstants:
    def test_max_dispatch_retries_is_two(self):
        """2 retries == 3 total attempts (spec section 11)."""
        assert MAX_DISPATCH_RETRIES == 2

    def test_max_audit_retries_is_three(self):
        assert MAX_AUDIT_RETRIES == 3
