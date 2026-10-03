"""Audit-routed settle re-dispatch must survive the queue round-trip.

probe4 ch1: chapter-revision (audit-routed) queued a shenbi-state-settling
re-dispatch with checkpoint_type="per_chapter" (underscore), but
CheckpointType.PER_CHAPTER.value is "per-chapter" (hyphen) —
_execute_pending_re_dispatches found no DERIVED_TRUTH_MAP entry for the
misspelled key, logged re_dispatch_unknown_type, and DROPPED the entry
silently. The post-revision settle never ran: live truth kept pre-revision
facts (criterion E broken at its execution half).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from shenbi.pipeline.cli import DERIVED_TRUTH_MAP, _execute_pending_re_dispatches
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.state import CheckpointType, PipelineState


def _entry() -> dict[str, Any]:
    """The entry exactly as chapter_loop's audit-routed queue site builds it."""
    from shenbi.pipeline.chapter_loop import (
        _audit_routed_settle_redispatch_entry,
    )

    return dict(_audit_routed_settle_redispatch_entry(1))


def test_audit_routed_entry_checkpoint_type_hits_derived_truth_map() -> None:
    entry = _entry()
    assert entry["checkpoint_type"] in DERIVED_TRUTH_MAP, (
        f"checkpoint_type {entry['checkpoint_type']!r} has no DERIVED_TRUTH_MAP "
        f"entry — _execute_pending_re_dispatches would drop it as unknown_type "
        f"(probe4 ch1: post-revision settle silently lost)"
    )
    skills = [s for s, _ in DERIVED_TRUTH_MAP[entry["checkpoint_type"]]]
    assert entry["skill"] in skills


def test_queued_settle_redispatch_executes_not_dropped(tmp_path: Path) -> None:
    state = PipelineState.default(str(tmp_path))
    state.pending_re_dispatches = [_entry()]

    with patch(
        "shenbi.pipeline.dispatch_helper.dispatch_skill",
        return_value=DispatchResult(True, 0, "", ""),
    ) as mock_disp:
        executed = _execute_pending_re_dispatches(state, tmp_path)

    assert executed, "entry must execute, not fall through as unknown_type"
    assert mock_disp.called
    assert state.pending_re_dispatches == []


def test_checkpoint_type_value_is_hyphenated() -> None:
    """Pin the vocabulary: the enum value uses hyphens, so any queue site
    must derive from the enum, not hand-type the snake_case form.
    """
    assert CheckpointType.PER_CHAPTER.value == "per-chapter"


def test_settle_redispatch_suffix_mandates_line_ref_relocation() -> None:
    """Batch #15 #41 (probe20 adjudication #004D): the revision shifts
    chapter lines ~10-20 — the re-settle prompt must mandate re-anchoring
    evidence line refs against the POST-revision text.
    """
    suffixes = dict(DERIVED_TRUTH_MAP[CheckpointType.PER_CHAPTER.value])
    assert "line reference" in suffixes["shenbi-state-settling"]
    assert "POST-revision" in suffixes["shenbi-state-settling"]
