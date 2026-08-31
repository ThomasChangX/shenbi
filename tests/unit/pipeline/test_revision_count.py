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


def test_revision_cap_escalates_once_beyond_two(tmp_path: Path, monkeypatch):
    """Spec #33 T1b: revision count > 2 escalates (exactly once, deduped)."""
    s = PipelineState.default(project_dir=str(tmp_path))
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.route_chapter_revision",
        lambda issues, blocking: RevisionRoute.SPOT_FIX,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.collect_audit_issues",
        lambda pd, ch: (["issue"], False),
    )
    escalations: list[int] = []
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.dispatch_escalation",
        lambda pd, ch, context="": escalations.append(ch) or True,
    )
    for _ in range(4):
        _route_revision_after_resonance(s, tmp_path, chapter=1)
    cs = s.chapter_loop.chapter_states["1"]
    assert cs.revision_count == 4
    assert escalations == [1]  # first exceedance only (3rd route), deduped after


def test_cap_and_retry_budget_orthogonal(tmp_path: Path, monkeypatch):
    """Spec #33 T1b reconciliation: retries(3) counts consecutive failures,
    cap(2) counts cumulative revisions — both fire independently.
    """
    from shenbi.pipeline.revision_router import MAX_AUTO_REVISIONS, revision_cap_exceeded

    assert MAX_AUTO_REVISIONS == 2
    # A chapter can exhaust the cap while retry budget is untouched (no
    # dispatch/gate failures) and vice versa.
    assert revision_cap_exceeded(3)  # cap fires without any retry failure
    # Retry budget logic lives in _handle_audit_blocking (3 attempts); its
    # counter is independent of cs.revision_count (incremented only on
    # revision routes). Drives: cap fires at revision 3 even when every
    # dispatch succeeded — pinned by the test above.
