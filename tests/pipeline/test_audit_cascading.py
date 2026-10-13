"""Tests for audit cascading (N=3 chapter zero-HARD-failure streak heuristic)
and Task 6 wiring helpers.
"""


def test_three_chapter_zero_hard_streak_skips_cascaded_audit():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    # Previous N=3 chapters: 'dialogue' audit passed with zero HARD failures each time.
    # audit_history is most-recent-last; only the trailing N=3 entries are considered.
    audit_history = [
        {"skill": "dialogue", "chapter": 1, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": 2, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": 3, "passed": True, "hard_failures": 0},
    ]
    assert _should_skip_audit("dialogue", audit_history) is True


def test_hard_failure_in_streak_prevents_skip():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    # One of the previous 3 chapters had a HARD failure in 'dialogue' → do NOT skip.
    audit_history = [
        {"skill": "dialogue", "chapter": 1, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": 2, "passed": False, "hard_failures": 1},  # HARD failure
        {"skill": "dialogue", "chapter": 3, "passed": True, "hard_failures": 0},
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
    assert len(history) == 3  # 1 from ch1 + 2 from ch2

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
        {"skill": "dialogue", "chapter": 1, "passed": True, "hard_failures": 0},
        {"skill": "continuity", "chapter": 1, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": 2, "passed": True, "hard_failures": 0},
        {"skill": "continuity", "chapter": 2, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": 3, "passed": True, "hard_failures": 0},
        {"skill": "continuity", "chapter": 3, "passed": True, "hard_failures": 0},
    ]

    # dialogue is cascadable and has a 3-chapter clean streak → skip
    assert _should_skip_audit("dialogue", audit_history) is True
    # continuity is a core audit → never cascade-skipped
    assert _should_skip_audit("continuity", audit_history) is False
    # resonance is always-run → never skipped
    assert _should_skip_audit("resonance", audit_history) is False


def test_unknown_skill_never_skipped():
    """F748 (spec #52): an audit in NO list (core/always-run/cascadable) is
    never cascade-skipped — unknown skills are outside the heuristic's scope.
    """
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    passing_history = [
        {"skill": "mystery-audit", "chapter": i, "passed": True, "hard_failures": 0}
        for i in range(1, 4)
    ]
    assert _should_skip_audit("mystery-audit", passing_history) is False


# ---------------------------------------------------------------------------
# Probe session 2026-09-29 (Stage 2 friction): the cascade froze PERMANENTLY
# after its first trigger — skipped audits append no new history, so the
# trailing-3-passes streak never refreshes and the audit goes blind from ch4
# to the end of the book (134-chapter scale: no audit evidence for G7). A
# re-verification gap forces one real run every CASCADE_REVERIFY_GAP skipped
# chapters, refreshing the streak.


def test_streak_skip_still_applies_within_reverify_gap():
    from shenbi.pipeline.chapter_loop import _should_skip_audit

    history = [
        {"skill": "dialogue", "chapter": 1, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": 2, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": 3, "passed": True, "hard_failures": 0},
    ]
    # current ch4: first skip — within the gap
    assert _should_skip_audit("dialogue", history, current_chapter=4) is True


def test_stale_streak_forces_rerun_after_reverify_gap():
    from shenbi.pipeline.chapter_loop import CASCADE_REVERIFY_GAP, _should_skip_audit

    history = [
        {"skill": "dialogue", "chapter": 1, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": 2, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": 3, "passed": True, "hard_failures": 0},
    ]
    # The streak's newest record is ch3; after CASCADE_REVERIFY_GAP skipped
    # chapters the audit must RUN again to refresh the evidence.
    stale_ch = 3 + CASCADE_REVERIFY_GAP + 1
    assert _should_skip_audit("dialogue", history, current_chapter=stale_ch) is False


def test_fresh_streak_from_recent_chapter_still_skips():
    from shenbi.pipeline.chapter_loop import CASCADE_REVERIFY_GAP, _should_skip_audit

    base = 10
    history = [
        {"skill": "dialogue", "chapter": base - 2, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": base - 1, "passed": True, "hard_failures": 0},
        {"skill": "dialogue", "chapter": base, "passed": True, "hard_failures": 0},
    ]
    assert _should_skip_audit("dialogue", history, current_chapter=base + 2) is True
    assert (
        _should_skip_audit("dialogue", history, current_chapter=base + CASCADE_REVERIFY_GAP) is True
    )
