"""Test restructured CHAPTER_STEPS with conditional dispatch.

Task 5 of Plan 18: Restructure CHAPTER_STEPS and Add Conditional Dispatch.
"""

from unittest.mock import MagicMock, patch

from shenbi.pipeline.chapter_loop import (
    CHAPTER_STEPS,
    _should_run_step,
)


def test_chapter_steps_count():
    """CHAPTER_STEPS shrinks from 20 to ~16 core steps."""
    assert len(CHAPTER_STEPS) <= 18  # ~16 core + some conditional


def test_no_deprecated_skills_in_steps():
    """Ensure deprecated skills are not in CHAPTER_STEPS."""
    deprecated = [
        "shenbi-foreshadowing-plant",
        "shenbi-foreshadowing-track",
        "shenbi-foreshadowing-recall",
        "shenbi-context-composing",
    ]
    step_skills = [s.skill for s in CHAPTER_STEPS]
    for dep in deprecated:
        assert dep not in step_skills


def test_escalation_review_NOT_a_step():
    """escalation-review is NOT a CHAPTER_STEPS entry (reactive dispatch).

    There is therefore no _should_run_step branch for it.
    """
    step_skills = [s.skill for s in CHAPTER_STEPS]
    assert "shenbi-escalation-review" not in step_skills


def test_intent_management_boundary_only():
    """intent-management should only run at volume boundaries."""
    state = MagicMock()
    step = MagicMock()
    step.skill = "shenbi-intent-management"
    step.conditional = True

    with patch("shenbi.pipeline.chapter_loop._is_volume_boundary", return_value=False):
        assert not _should_run_step(state, step)

    with patch("shenbi.pipeline.chapter_loop._is_volume_boundary", return_value=True):
        assert _should_run_step(state, step)


def test_non_conditional_steps_always_run():
    """Steps without conditional flag should always return True."""
    state = MagicMock()
    step = MagicMock()
    step.skill = "shenbi-chapter-planning"
    step.conditional = False

    assert _should_run_step(state, step)


def test_conditional_snapshot_manage_runs():
    """shenbi-snapshot-manage (conditional) should run when conditional gate triggers."""
    state = MagicMock()
    step = MagicMock()
    step.skill = "shenbi-snapshot-manage"
    step.conditional = True

    # No specific gate for snapshot-manage in _should_run_step → defaults to True
    assert _should_run_step(state, step)


def test_drift_guidance_triggered_by_alerts():
    """shenbi-drift-guidance should run when 3+ consecutive drift alerts."""
    state = MagicMock()
    state.drift_alerts = ["alert1", "alert2", "alert3"]
    step = MagicMock()
    step.skill = "shenbi-drift-guidance"
    step.conditional = True

    assert _should_run_step(state, step)

    state.drift_alerts = ["alert1", "alert2"]
    assert not _should_run_step(state, step)


def test_chapter_revision_with_findings():
    """shenbi-chapter-revision should run when audit has BLOCKING or FAIL findings."""
    state = MagicMock()
    step = MagicMock()
    step.skill = "shenbi-chapter-revision"
    step.conditional = True

    with patch("shenbi.pipeline.chapter_loop._any_audit_has_findings", return_value=True):
        assert _should_run_step(state, step)

    with patch("shenbi.pipeline.chapter_loop._any_audit_has_findings", return_value=False):
        assert not _should_run_step(state, step)
