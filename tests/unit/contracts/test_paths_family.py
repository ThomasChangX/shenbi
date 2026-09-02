"""C13 (spec #39 T7): path resolution completeness — F207/F208/F209/F228."""

from __future__ import annotations

import pytest

from shenbi.contracts.paths import (
    PathContext,
    UnresolvedPathError,
    resolve_chapter_path,
    resolve_contract_path,
)


@pytest.mark.c13_regression
def test_family_placeholder_missing_ctx_value_raises() -> None:
    """F207: ctx present but family value None must not silently fall back to
    chapter semantics (volume-N resolving to the chapter number).
    """
    ctx = PathContext(chapter=60)  # arc/stratum/volume are None
    with pytest.raises(UnresolvedPathError):
        resolve_contract_path("audits/volume-N-payoff.md", 60, ctx)


@pytest.mark.c13_regression
def test_second_family_placeholder_resolved() -> None:
    """F208: every occurrence of the family placeholder resolves (old code
    replaced only the first via count=1).
    """
    ctx = PathContext(arc=5, chapter=7)
    assert (
        resolve_contract_path("truth/arcs/arc-N/notes-arc-N.md", 7, ctx)
        == "truth/arcs/arc-5/notes-arc-5.md"
    )


@pytest.mark.c13_regression
def test_family_and_anchor_coexist() -> None:
    """F228: family substitution no longer shadows AC-NNN anchor resolution."""
    ctx = PathContext(arc=5, anchor=3)
    assert (
        resolve_contract_path("truth/arcs/arc-N/AC-NNN.md", None, ctx)
        == "truth/arcs/arc-5/AC-003.md"
    )


@pytest.mark.c13_regression
def test_nnn_replacement_bounded_within_n_runs() -> None:
    """F209: NNN inside a longer N-run is left intact (old unbounded replace
    produced the corrupted '100N').
    """
    assert resolve_chapter_path("data/NNNN-summary.md", 100) == "data/NNNN-summary.md"
    assert resolve_chapter_path("snapshots/chapter-NNN/", 100) == "snapshots/chapter-100/"
