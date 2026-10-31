"""Spec #69 T5 (F368 residual): chapter-close sweep of retry_feedback keys.

The per-step canary pop (G4-pass sites, chapter_loop.py:3276/:3477) retires
feedback for steps that pass re-validation; the chapter-close sweep is the
catch-all so a finished chapter's corrective feedback can never leak into
later dispatch cycles. Precedent for the harness:
tests/unit/pipeline/test_cost_report_auto.py:36-52.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

from shenbi.pipeline import chapter_loop
from shenbi.pipeline.state import PipelineState


def _state(tmp_path, retry_feedback: dict[str, str]):
    return SimpleNamespace(
        project_dir=str(tmp_path),
        chapter_loop=SimpleNamespace(
            chapter_states={},
            current_chapter=1,
            step_index=0,
            current_step="",
            per_chapter_review_enabled=False,
            retry_feedback=retry_feedback,
            streak_monitor_rewinds={},  # spec #83 T4 字段入 mock
        ),
    )


def _run(tmp_path, state, chapter: int) -> None:
    import shenbi.pipeline.product_contracts as pc

    orig = pc.check_product_contracts
    pc.check_product_contracts = lambda pd: []
    try:
        with (
            patch.object(chapter_loop, "_check_world_file_freshness", return_value=None),
            patch.object(chapter_loop, "_print_timing_summary", return_value=None),
            patch.object(chapter_loop, "print_token_summary", return_value=None),
        ):
            chapter_loop._complete_chapter(cast(PipelineState, state), chapter)
    finally:
        pc.check_product_contracts = orig


def test_chapter_close_clears_all_chapter_keys(tmp_path):
    """失败→遗留(含 legacy 键形)→ 章节关闭 → 该章全部键消失."""
    state = _state(
        tmp_path,
        {
            "ch1-shenbi-review-resonance": "fb",
            "ch1-shenbi-chapter-drafting": "fb2",  # legacy 键形(:1197 同构)
            "ch10-shenbi-review-resonance": "keep",
        },
    )
    _run(tmp_path, state, 1)
    assert "ch1-shenbi-review-resonance" not in state.chapter_loop.retry_feedback
    assert "ch1-shenbi-chapter-drafting" not in state.chapter_loop.retry_feedback


def test_chapter_close_does_not_touch_other_chapters(tmp_path):
    """Dash 终结使 ch1- 前缀不误伤 ch10-*(spec §2 T5.1 安全性)."""
    state = _state(tmp_path, {"ch10-shenbi-review-resonance": "keep", "ch2-x": "keep2"})
    _run(tmp_path, state, 1)
    assert state.chapter_loop.retry_feedback == {
        "ch10-shenbi-review-resonance": "keep",
        "ch2-x": "keep2",
    }
