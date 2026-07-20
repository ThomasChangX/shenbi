"""Test state machine current_step healing and validation.

Task 17-13: State Machine -- Heal current_step Corruption.
"""

from unittest.mock import MagicMock

from shenbi.pipeline.chapter_loop import CHAPTER_STEPS
from shenbi.pipeline.state import (
    _heal_current_step,
    _validate_state_consistency,
)


class TestHealCurrentStep:
    def test_heals_empty_current_step_with_valid_index(self):
        state = MagicMock()
        state.chapter_loop.current_step = ""
        state.chapter_loop.step_index = 5  # Valid index

        _heal_current_step(state, CHAPTER_STEPS)
        assert state.chapter_loop.current_step != ""
        assert state.chapter_loop.current_step == CHAPTER_STEPS[5].skill

    def test_no_change_when_current_step_already_set(self):
        state = MagicMock()
        state.chapter_loop.current_step = "shenbi-chapter-drafting"
        state.chapter_loop.step_index = 4

        _heal_current_step(state, CHAPTER_STEPS)
        assert state.chapter_loop.current_step == "shenbi-chapter-drafting"

    def test_handles_step_index_beyond_list(self):
        state = MagicMock()
        state.chapter_loop.current_step = ""
        state.chapter_loop.step_index = 999  # Beyond list

        _heal_current_step(state, CHAPTER_STEPS)
        assert state.chapter_loop.current_step == "chapter_complete"

    def test_step_index_zero_with_empty_step(self):
        state = MagicMock()
        state.chapter_loop.current_step = ""
        state.chapter_loop.step_index = 0

        _heal_current_step(state, CHAPTER_STEPS)
        # At step 0, current_step should remain empty (not yet started)
        assert state.chapter_loop.current_step == ""

    def test_step_index_zero_not_healed(self):
        """step_index <= 0 means not yet started -- don't heal."""
        state = MagicMock()
        state.chapter_loop.current_step = ""
        state.chapter_loop.step_index = 0

        _heal_current_step(state, CHAPTER_STEPS)
        # step_index <= 0 -> return early, current_step stays ""
        assert state.chapter_loop.current_step == ""


class TestValidateStateConsistency:
    def test_detects_and_heals_corrupt_state(self):
        state = MagicMock()
        state.chapter_loop.current_step = ""
        state.chapter_loop.step_index = 9

        issues = _validate_state_consistency(state, CHAPTER_STEPS)
        # Should auto-heal
        assert state.chapter_loop.current_step != ""
        assert len(issues) > 0
        assert any("auto-healing" in i for i in issues)

    def test_passes_consistent_state(self):
        state = MagicMock()
        state.chapter_loop.current_step = "shenbi-state-settling"
        state.chapter_loop.step_index = 7

        # Should not raise, should not change
        issues = _validate_state_consistency(state, CHAPTER_STEPS)
        assert state.chapter_loop.current_step == "shenbi-state-settling"
        assert len(issues) == 0

    def test_clamps_step_index_beyond_list(self):
        state = MagicMock()
        state.chapter_loop.current_step = "some-skill"
        state.chapter_loop.step_index = 999

        issues = _validate_state_consistency(state, CHAPTER_STEPS)
        assert state.chapter_loop.step_index == len(CHAPTER_STEPS)
        assert state.chapter_loop.current_step == "chapter_complete"
        assert len(issues) > 0
        assert any("clamping" in i for i in issues)

    def test_no_issues_for_step_index_at_boundary(self):
        """step_index == len(CHAPTER_STEPS) is valid (chapter complete)."""
        state = MagicMock()
        state.chapter_loop.current_step = "chapter_complete"
        state.chapter_loop.step_index = len(CHAPTER_STEPS)

        issues = _validate_state_consistency(state, CHAPTER_STEPS)
        # step_index == len(CHAPTER_STEPS) is not > len, so no clamping
        # and current_step is set, so no healing
        assert len(issues) == 0
