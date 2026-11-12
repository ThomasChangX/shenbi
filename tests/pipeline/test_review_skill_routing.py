"""Spec #87 T4: substring elimination — dual path, behavior-preserving.

Path A: ChapterStep boolean attributes replace substring tests inside
chapter_loop. Path B: a precise frozenset roster replaces
``"review" in skill.lower()`` in dispatch_helper's review-checklist
injection — escalation/foundation-review KEEP their injection (r3.1
adjudication: today's substring match reaches them via dispatch_escalation
with chapter non-None; dropping them would be live behavior tightening).
"""

from pathlib import Path

import pytest

from shenbi.pipeline.chapter_loop import CHAPTER_STEPS
from shenbi.pipeline.review_checklist import REVIEW_SKILLS, is_review_skill


@pytest.mark.unit
def test_review_resonance_substring_negative() -> None:
    """A skill merely CONTAINING 'review-resonance' must not be treated as
    the resonance step (substring today over-triggers; red->green).
    """
    fake = type(CHAPTER_STEPS[0])(99, "shenbi-xreview-resonance-y", "fake", emits_resonance=False)
    assert not fake.emits_resonance
    # and the roster must not admit it (path B independence)
    assert not is_review_skill("shenbi-xreview-resonance-y")


@pytest.mark.unit
def test_preview_named_skill_not_review() -> None:
    assert not is_review_skill("shenbi-preview-x")  # "review" substring trap
    assert not is_review_skill("shenbi-review")  # bare prefix is not a skill


@pytest.mark.unit
def test_escalation_review_keeps_injection() -> None:
    """r3.1: escalation/foundation review keep the checklist injection."""
    assert is_review_skill("shenbi-escalation-review")
    assert is_review_skill("shenbi-foundation-review")
    assert is_review_skill("shenbi-review-resonance")


@pytest.mark.unit
def test_roster_scan_reconciles_with_skills_dir() -> None:
    """skills/ scan (prefix plus two explicit names, never a bare substring)
    must be a subset of the roster; a new review skill left unregistered
    turns this red.
    """
    root = Path(__file__).resolve().parents[2] / "skills"
    on_disk = {
        d.name
        for d in root.iterdir()
        if d.name.startswith("shenbi-review-")
        or d.name in {"shenbi-escalation-review", "shenbi-foundation-review"}
    }
    assert on_disk <= REVIEW_SKILLS, sorted(on_disk - REVIEW_SKILLS)


@pytest.mark.unit
def test_chapter_steps_flags_set() -> None:
    """Path A: the three steps carry their new attributes."""
    settling = next(s for s in CHAPTER_STEPS if s.skill == "shenbi-state-settling")
    resonance = next(s for s in CHAPTER_STEPS if s.skill == "shenbi-review-resonance")
    revision = next(s for s in CHAPTER_STEPS if s.skill == "shenbi-chapter-revision")
    assert settling.settles_state and settling.emits_resonance is False
    assert resonance.emits_resonance and resonance.settles_state is False
    assert revision.is_revision
