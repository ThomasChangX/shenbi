"""vol1 probe escalation #024/#026: word-count retries must EXPAND, not re-roll.

The corrective feedback carried only the error text — the previous draft
never entered the retry prompt, so every retry was a blind full rewrite.
With the model's self-count biased 15-25% high (drafting 铁律 7's own
documentation), blind re-rolls either landed short again (ch5 oscillated
6177→8269→7337 raw and degraded on the second escalation) or overshot the
floor by double digits once the feedback said "expand" (ch1/2/4 landed
+9~19% gate-metric over the 7145 default — the anti-undershoot ratchet).
Attaching the persisted draft with an expand-don't-rewrite directive makes
the retry converge monotonically on the exact measured gap.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import _append_feedback_injections
from shenbi.pipeline.state import PipelineState


def _state_with_feedback(feedback: str, chapter: int = 5) -> PipelineState:
    state = PipelineState.default("proj")
    state.chapter_loop.retry_feedback[f"ch{chapter}-shenbi-chapter-drafting"] = feedback
    return state


def test_wordcount_retry_attaches_draft_with_expand_directive(tmp_path: Path) -> None:
    draft = tmp_path / "chapters" / "chapter-5.md"
    draft.parent.mkdir(parents=True)
    draft.write_text("前稿正文第一段。\n", encoding="utf-8")

    state = _state_with_feedback("G4.word_count:chapters/chapter-5.md:5133<7145")
    out = _append_feedback_injections("base prompt", state, 5, "shenbi-chapter-drafting", tmp_path)

    assert "前稿正文第一段。" in out, "persisted draft rides into the retry prompt"
    assert "扩写" in out and "禁止整章重写" in out, (
        "the directive must demand expansion of the prior text, not a fresh roll"
    )
    assert "5133" in out, "the measured gate count anchors the expansion amount"


def test_non_wordcount_retry_does_not_attach_draft(tmp_path: Path) -> None:
    draft = tmp_path / "chapters" / "chapter-5.md"
    draft.parent.mkdir(parents=True)
    draft.write_text("前稿正文。\n", encoding="utf-8")

    state = _state_with_feedback("G4.fatigue:chapters/chapter-5.md:9>8")
    out = _append_feedback_injections("base prompt", state, 5, "shenbi-chapter-drafting", tmp_path)

    assert "前稿正文。" not in out, (
        "non-length failures keep the rewrite freedom — only word_count needs the base text"
    )
    assert "CORRECTIVE FEEDBACK" in out, "plain corrective feedback still injected"


def test_wordcount_retry_without_persisted_draft_degrades_cleanly(tmp_path: Path) -> None:
    """Empty-content failures leave no file — the injection must not crash."""
    state = _state_with_feedback("G4.word_count:chapters/chapter-9.md:0<7145", chapter=9)
    out = _append_feedback_injections("base prompt", state, 9, "shenbi-chapter-drafting", tmp_path)

    assert "CORRECTIVE FEEDBACK" in out
    assert "PREVIOUS DRAFT" not in out


# ---------------------------------------------------------------------------
# regen v3 F3 (2026-10-27): #72 scene-cluster bundle face — scene-split length
# failures must attach the STAGING BUNDLE, not silently skip the draft base
# ---------------------------------------------------------------------------
def test_scene_split_word_band_attaches_staging_bundle(tmp_path: Path) -> None:
    """scene-split word failures (word_band/chapter_band/scene_domain ids) are
    the bundle face of the same length family — the #72 staging bundle is the
    persisted prior draft (no live chapter file exists pre-split). Without the
    base text every bundle retry re-rolls BOTH chapters, including the ones
    that already passed (regen v3 ch1: drafting escalated 4x re-rolling a
    passing ch1 to fix a short ch2).
    """
    bundle = tmp_path / "staging" / "chapter-1-bundle.md"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("===CH:1===\n前稿章一正文。\n===CH:2===\n前稿章二正文。\n", encoding="utf-8")

    state = _state_with_feedback(
        "pipeline-scene-split: word_band:ch2:total_chars 2637 不在带 [2800,4000]", chapter=1
    )
    out = _append_feedback_injections("base prompt", state, 1, "shenbi-chapter-drafting", tmp_path)

    assert "前稿章一正文。" in out and "前稿章二正文。" in out, (
        "staging bundle rides into the retry prompt as the expand base"
    )
    assert "扩写" in out and "禁止整章重写" in out
    assert "2637" in out, "measured gap anchors the expansion"


def test_scene_split_scene_domain_failure_also_attaches_bundle(tmp_path: Path) -> None:
    """scene_domain/composition failures are the same length family:
    expanding the existing scene into the two-type domain converges without
    structural rewrite.
    """
    bundle = tmp_path / "staging" / "chapter-1-bundle.md"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("===CH:1===\n好章。\n===CH:2===\n短章。\n", encoding="utf-8")

    state = _state_with_feedback(
        "pipeline-scene-split: scene_domain:ch2:场景1=1546 落灰域", chapter=1
    )
    out = _append_feedback_injections("base prompt", state, 1, "shenbi-chapter-drafting", tmp_path)
    assert "好章。" in out, "scene_domain failures attach the bundle base too"
