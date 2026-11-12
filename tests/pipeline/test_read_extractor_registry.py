"""Spec #87 T2: extractor registry — table-driven WARN policies + leaf single-source."""

import inspect

import pytest

from shenbi.contracts.loader import READ_EXTRACTORS
from shenbi.contracts.read_extractor_names import READ_EXTRACTOR_NAMES
from shenbi.pipeline import read_extractors as re_mod
from shenbi.pipeline.read_extractors import REGISTRY


@pytest.mark.unit
def test_registry_keys_equal_leaf_roster() -> None:
    assert set(REGISTRY) == READ_EXTRACTOR_NAMES == READ_EXTRACTORS


@pytest.mark.unit
def test_registry_size_matches_leaf() -> None:
    # not a hardcoded 11 — the 12th extractor must be a 2-edit change
    assert len(REGISTRY) == len(READ_EXTRACTOR_NAMES)


@pytest.mark.unit
def test_per_extractor_chapter_none_policies() -> None:
    assert REGISTRY["volume_chapter"].chapter_none == "guard_warn"
    assert REGISTRY["hooks_audit_scoped"].chapter_none == "silent"
    assert REGISTRY["matrix_scoped"].chapter_none == "loud"
    assert REGISTRY["recent_increments"].empty_warn_predicate is re_mod.has_chapter_units


@pytest.mark.unit
def test_no_bare_extractor_equality_in_dispatch_helper() -> None:
    """Anti-recurrence guard: a new extractor must never re-add a bare if-arm."""
    from shenbi.pipeline import dispatch_helper as dh

    assert "extractor ==" not in inspect.getsource(dh)
