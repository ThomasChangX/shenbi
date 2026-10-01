"""intent-management grounding reads (probe6 finding, 2026-10-01).

Genesis step 14 dispatched intent-management in auto mode with only
placeholder reads (``truth/author_intent.md`` + ``truth/audit_drift.md``) —
zero grounding about the actual novel. The model confabulated a COMPLETE
DIFFERENT STORY (deep-space exploration, keyed off the project directory
name ``novel-xinghuo-probe6`` and the title 《星火》) into the truth file
that chapter-planning's priority chain then had to override every chapter.
Historical probes (2-4) showed only thematic drift; probe6 escalated to a
full foreign story. Root cause: no grounding reads (adjudication 002/005
upstream referrals).
"""

from __future__ import annotations

from shenbi.contracts.loader import load_contract


def test_intent_management_reads_story_grounding() -> None:
    contract = load_contract("shenbi-intent-management")
    for grounding in ("novel.json", "outline/story_frame.md"):
        assert grounding in contract["reads"], (
            f"{grounding} must be a grounding read — without it the auto-mode "
            "genesis dispatch confabulates intent from the project name"
        )


def test_intent_management_body_pins_derivation() -> None:
    skill = (
        __import__("pathlib").Path(__file__).parents[3]
        / "skills"
        / "shenbi-intent-management"
        / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "story_frame" in skill
    assert "不得编造" in skill or "禁止编造" in skill or "无从编造" in skill or "不得虚构" in skill
