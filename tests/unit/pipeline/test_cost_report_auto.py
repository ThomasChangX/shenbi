"""Spec #36 T4: chapter-completion + closure nodes auto-render cost/report.md."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from shenbi.cost.ledger import TokenLedger
from shenbi.cost.report import write_report


def test_write_report_creates_file(tmp_path):
    TokenLedger(tmp_path).record("s", 1, {"prompt_tokens": 5, "total_tokens": 5})
    out = write_report(tmp_path)
    assert out is not None
    assert out == tmp_path / "cost" / "report.md"
    assert out.exists() and "Cost Report" in out.read_text(encoding="utf-8")


def test_write_report_fail_safe(tmp_path, monkeypatch):
    import shenbi.cost.report as rep

    def boom(p):
        raise RuntimeError("render exploded")

    monkeypatch.setattr(rep, "render_report", boom)
    assert write_report(tmp_path) is None  # WARN, never raises


def test_complete_chapter_renders_report(tmp_path, monkeypatch):
    from typing import cast

    from shenbi.pipeline import chapter_loop
    from shenbi.pipeline.state import PipelineState

    monkeypatch.setattr("shenbi.pipeline.product_contracts.check_product_contracts", lambda pd: [])
    state = SimpleNamespace(
        project_dir=str(tmp_path),
        chapter_loop=SimpleNamespace(
            chapter_states={},
            current_chapter=1,
            step_index=0,
            current_step="",
            per_chapter_review_enabled=False,
        ),
    )
    with (
        patch.object(chapter_loop, "_maybe_rebuild_truth_index", return_value=None),
        patch.object(chapter_loop, "_check_world_file_freshness", return_value=None),
        patch.object(chapter_loop, "_print_timing_summary", return_value=None),
        patch.object(chapter_loop, "print_token_summary", return_value=None),
    ):
        chapter_loop._complete_chapter(cast(PipelineState, state), 1)
    assert (tmp_path / "cost" / "report.md").exists()


def test_closure_completed_renders_report(tmp_path):
    from typing import cast

    from shenbi.pipeline import closure as clo
    from shenbi.pipeline.state import ClosureState, PipelineState

    state = SimpleNamespace(
        closure_step=len(clo.CLOSURE_STEPS),
        closure=None,
        closure_retry_counts={},
        project_dir=str(tmp_path),
    )
    assert clo.run_closure_step(cast(PipelineState, state), tmp_path) is True
    assert state.closure == ClosureState.COMPLETED
    assert (tmp_path / "cost" / "report.md").exists()
