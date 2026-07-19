"""Tests that revision_count is incremented on revision routing (spec §3.2)."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import _route_revision_after_resonance
from shenbi.pipeline.revision_router import RevisionRoute
from shenbi.pipeline.state import PipelineState


def test_revision_count_increments_on_non_noop_route(tmp_path: Path, monkeypatch):
    s = PipelineState.default(project_dir=str(tmp_path))
    # Force the router to return a revision route.
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.route_chapter_revision",
        lambda issues, blocking: RevisionRoute.SPOT_FIX,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.collect_audit_issues",
        lambda pd, ch: (["some issue"], False),
    )

    _route_revision_after_resonance(s, tmp_path, chapter=1)

    cs = s.chapter_loop.chapter_states["1"]
    assert cs.revision_count == 1, f"revision_count should be 1, got {cs.revision_count}"


def test_revision_count_unchanged_on_no_revision(tmp_path: Path, monkeypatch):
    s = PipelineState.default(project_dir=str(tmp_path))
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.route_chapter_revision",
        lambda issues, blocking: RevisionRoute.NO_REVISION,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.collect_audit_issues",
        lambda pd, ch: ([], False),
    )

    _route_revision_after_resonance(s, tmp_path, chapter=1)

    cs = s.chapter_loop.chapter_states["1"]
    assert cs.revision_count == 0, "NO_REVISION must not increment revision_count"


def test_revision_count_accumulates_across_routes(tmp_path: Path, monkeypatch):
    s = PipelineState.default(project_dir=str(tmp_path))
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.route_chapter_revision",
        lambda issues, blocking: RevisionRoute.SPOT_FIX,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.collect_audit_issues",
        lambda pd, ch: (["issue"], False),
    )
    _route_revision_after_resonance(s, tmp_path, chapter=2)
    _route_revision_after_resonance(s, tmp_path, chapter=2)

    assert s.chapter_loop.chapter_states["2"].revision_count == 2
