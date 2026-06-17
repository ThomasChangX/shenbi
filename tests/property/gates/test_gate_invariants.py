"""Hypothesis property tests for gate invariants.

These tests verify properties that must hold for ALL inputs, not just
specific examples. They catch edge cases human-authored tests miss.

Note on fixture interaction: hypothesis's @given decorator and pytest
fixtures can conflict when both are positional args. Tests that need a
tmp_path use the st.register_type_strategy pattern or build the path
inline via tempfile, avoiding the fixture-collision issue.
"""

from __future__ import annotations

import json
import string
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.gates.shared import (
    count_transition_words,
    jload,
    normalize_file_paths,
    word_count_md,
)


@pytest.mark.unit
@pytest.mark.property
@given(st.text(alphabet=string.ascii_letters + " \n。！？，、", min_size=0, max_size=2000))
@settings(max_examples=200, deadline=None)
def test_word_count_md_always_non_negative(content: str) -> None:
    """word_count_md returns >= 0 for any input (Chinese chars counted)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        assert word_count_md(path) >= 0
    finally:
        Path(path).unlink(missing_ok=True)


@pytest.mark.unit
@pytest.mark.property
@given(st.lists(st.text(min_size=0, max_size=100), max_size=20))
@settings(max_examples=100, deadline=None)
def test_normalize_file_paths_returns_list(input_list: list[str]) -> None:
    """normalize_file_paths always returns a list."""
    result = normalize_file_paths(input_list)
    assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.property
@given(st.text())
@settings(max_examples=100, deadline=None)
def test_count_transition_words_returns_non_negative(content: str) -> None:
    """count_transition_words returns >= 0 for any text."""
    assert count_transition_words(content) >= 0


@pytest.mark.unit
@pytest.mark.property
@given(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=string.ascii_letters),
        values=st.integers(),
        max_size=5,
    )
)
@settings(max_examples=50, deadline=None)
def test_jload_round_trips_dict(data: dict[str, int]) -> None:
    """Jload reads back exactly what was written for dict data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(json.dumps(data))
        path = f.name
    try:
        assert jload(path) == data
    finally:
        Path(path).unlink(missing_ok=True)


@pytest.mark.unit
@pytest.mark.property
def test_gate_g0_returns_valid_json_for_empty_seed() -> None:
    """GATE G0 always returns parseable JSON even with no input."""
    from shenbi.gates.g0 import gate_G0

    result = gate_G0(seed_file=None)
    parsed = json.loads(result)
    assert "gate" in parsed
    assert "status" in parsed
