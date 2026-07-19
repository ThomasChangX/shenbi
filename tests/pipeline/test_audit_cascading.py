"""Tests for audit cascading (N=3 chapter zero-HARD-failure streak heuristic)
and 3-tier instruction hierarchy injection.
"""

from shenbi.pipeline.dispatch_helper import _inject_instruction_hierarchy


def test_instruction_hierarchy_has_three_tiers():
    prompt = "Review the chapter for issues."
    result = _inject_instruction_hierarchy(prompt)
    assert "HARD_CONSTRAINTS" in result
    assert "GUIDELINES" in result
    assert "REFERENCE" in result


def test_three_chapter_zero_hard_streak_skips_cascaded_audit():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    # Previous N=3 chapters: 'dialogue' audit passed with zero HARD failures each time.
    # audit_history is most-recent-last; only the trailing N=3 entries are considered.
    audit_history = [
        {"dialogue": {"passed": True, "hard_failures": 0}},
        {"dialogue": {"passed": True, "hard_failures": 0}},
        {"dialogue": {"passed": True, "hard_failures": 0}},
    ]
    assert _should_skip_audit("dialogue", audit_history) is True


def test_hard_failure_in_streak_prevents_skip():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    # One of the previous 3 chapters had a HARD failure in 'dialogue' → do NOT skip.
    audit_history = [
        {"dialogue": {"passed": True, "hard_failures": 0}},
        {"dialogue": {"passed": False, "hard_failures": 1}},  # HARD failure
        {"dialogue": {"passed": True, "hard_failures": 0}},
    ]
    assert _should_skip_audit("dialogue", audit_history) is False


def test_insufficient_history_prevents_skip():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    # Fewer than N=3 chapters of history → cannot establish a streak → do NOT skip.
    audit_history = [
        {"dialogue": {"passed": True, "hard_failures": 0}},
        {"dialogue": {"passed": True, "hard_failures": 0}},
    ]
    assert _should_skip_audit("dialogue", audit_history) is False


def test_always_run_audits_are_never_skipped():
    from shenbi.pipeline.chapter_loop import ALWAYS_RUN, _should_skip_audit

    audit_history = [
        {"resonance": {"passed": True, "hard_failures": 0}},
        {"resonance": {"passed": True, "hard_failures": 0}},
        {"resonance": {"passed": True, "hard_failures": 0}},
    ]
    # resonance and memo-compliance ALWAYS run regardless of the cascade.
    for skill in ALWAYS_RUN:
        assert _should_skip_audit(skill, audit_history) is False, (
            f"{skill} must always run, but _should_skip_audit returned True"
        )


def test_non_cascadable_skill_is_not_skipped():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    # A core audit (e.g. 'continuity') is never cascade-skipped.
    audit_history = [
        {"continuity": {"passed": True, "hard_failures": 0}},
        {"continuity": {"passed": True, "hard_failures": 0}},
        {"continuity": {"passed": True, "hard_failures": 0}},
    ]
    assert _should_skip_audit("continuity", audit_history) is False
