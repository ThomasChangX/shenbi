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
def test_review_resonance_substring_negative(tmp_path, monkeypatch) -> None:
    """A skill merely CONTAINING 'review-resonance' must not trigger the
    resonance post-processing (audit-T4: drive the PUBLIC entry with an
    injected step — a constructed-flag assertion would be vacuous).
    """
    from types import SimpleNamespace
    from unittest.mock import patch

    from shenbi.pipeline import chapter_loop as cl
    from shenbi.pipeline.state import PipelinePhase, PipelineState

    fake = type(CHAPTER_STEPS[0])(
        99, "shenbi-xreview-resonance-y", "fake", uses_staging=True
    )  # emits_resonance defaults False — the substring form would over-fire
    real_steps = list(CHAPTER_STEPS)
    monkeypatch.setattr(cl, "CHAPTER_STEPS", real_steps + [fake])

    state = PipelineState.default(str(tmp_path))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 1
    state.chapter_loop.step_index = len(real_steps)  # the injected step

    tail_calls: list[str] = []
    with (
        patch.object(
            cl,
            "dispatch_skill",
            side_effect=lambda *a, **kw: SimpleNamespace(
                success=True, result={}, stdout="", stderr="", returncode=0
            ),
        ),
        patch.object(
            cl, "run_gate_g4", lambda *a, **kw: {"status": "PASS", "checks": [], "must_fix": []}
        ),
        patch.object(
            cl,
            "_parse_and_persist_resonance",
            side_effect=lambda *a, **kw: tail_calls.append("persist"),
        ),
        patch.object(
            cl,
            "_route_revision_after_resonance",
            side_effect=lambda *a, **kw: tail_calls.append("route"),
        ),
    ):
        reached = cl.run_chapter_step(state, tmp_path)

    assert isinstance(reached, bool)
    assert tail_calls == [], "substring-named skill must NOT fire resonance tails"
    # roster independence (path B)
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
