"""Tests for audit cascading (N=3 chapter zero-HARD-failure streak heuristic),
3-tier instruction hierarchy injection, and Task 6 wiring helpers.
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


# ---------------------------------------------------------------------------
# Task 6 wiring tests: helpers _audit_short_name and _get_audit_history
# ---------------------------------------------------------------------------


def test_audit_short_name_strips_prefix():
    """_audit_short_name maps full skill names to short dimension names."""
    from shenbi.pipeline.chapter_loop import _audit_short_name

    assert _audit_short_name("shenbi-review-anti-ai") == "anti-ai"
    assert _audit_short_name("shenbi-review-continuity") == "continuity"
    assert _audit_short_name("shenbi-review-dialogue") == "dialogue"
    assert _audit_short_name("shenbi-review-resonance") == "resonance"
    assert _audit_short_name("shenbi-review-memo-compliance") == "memo-compliance"


def test_get_audit_history_extracts_previous_chapters():
    """_get_audit_history returns results from chapters < current_chapter."""
    from shenbi.pipeline.chapter_loop import _get_audit_history
    from shenbi.pipeline.state import ChapterState, PipelineState

    state = PipelineState(project_dir="/tmp/test")
    # Populate chapter 1 audit results
    cs1 = ChapterState()
    cs1.audit_results["dialogue"] = {
        "passed": True,
        "hard_failures": 0,
        "issues": [],
    }
    state.chapter_loop.chapter_states["1"] = cs1

    # Populate chapter 2 audit results
    cs2 = ChapterState()
    cs2.audit_results["dialogue"] = {
        "passed": True,
        "hard_failures": 0,
        "issues": [],
    }
    cs2.audit_results["continuity"] = {
        "passed": False,
        "hard_failures": 1,
        "issues": ["plot hole"],
    }
    state.chapter_loop.chapter_states["2"] = cs2

    history = _get_audit_history(state, current_chapter=3)
    assert len(history) == 3  # 2 from ch1 + 1 from ch2? Wait, 1 from ch1 + 2 from ch2 = 3

    # Verify chapter 2's entries are included
    dialogue_entries = [h for h in history if h["skill"] == "dialogue"]
    assert len(dialogue_entries) == 2

    # Verify chapter 3+ entries are excluded
    cs3 = ChapterState()
    cs3.audit_results["dialogue"] = {"passed": True, "hard_failures": 0, "issues": []}
    state.chapter_loop.chapter_states["3"] = cs3
    history = _get_audit_history(state, current_chapter=3)
    assert len(history) == 3  # chapter 3 excluded


def test_cascade_wiring_skips_dialogue_keeps_continuity():
    """Task 6 Step 3: given a 3-chapter zero-HARD-failure streak for dialogue,
    _should_skip_audit returns True for dialogue but False for continuity/core.
    """
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    audit_history = [
        {
            "dialogue": {"passed": True, "hard_failures": 0},
            "continuity": {"passed": True, "hard_failures": 0},
        },
        {
            "dialogue": {"passed": True, "hard_failures": 0},
            "continuity": {"passed": True, "hard_failures": 0},
        },
        {
            "dialogue": {"passed": True, "hard_failures": 0},
            "continuity": {"passed": True, "hard_failures": 0},
        },
    ]

    # dialogue is cascadable and has a 3-chapter clean streak → skip
    assert _should_skip_audit("dialogue", audit_history) is True
    # continuity is a core audit → never cascade-skipped
    assert _should_skip_audit("continuity", audit_history) is False
    # resonance is always-run → never skipped
    assert _should_skip_audit("resonance", audit_history) is False
