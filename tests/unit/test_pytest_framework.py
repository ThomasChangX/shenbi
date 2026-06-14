"""Verify pytest framework infrastructure works."""

from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st


def test_tmp_project_dir_fixture_creates_dir(tmp_project_dir: Path) -> None:
    """tmp_project_dir should create and return an existing directory."""
    assert tmp_project_dir.exists()
    assert tmp_project_dir.is_dir()


def test_sample_worldbuilding_fixture_writes_files(sample_worldbuilding_output: Path) -> None:
    """sample_worldbuilding_output should produce novel.json and world/story_bible.md."""
    assert (sample_worldbuilding_output / "novel.json").exists()
    assert (sample_worldbuilding_output / "world" / "story_bible.md").exists()


@pytest.mark.unit
def test_unit_marker_works() -> None:
    """@pytest.mark.unit should not raise."""
    assert True


@pytest.mark.integration
def test_integration_marker_works() -> None:
    """@pytest.mark.integration should not raise."""
    assert True


@pytest.mark.property
@given(st.integers())
def test_property_marker_works(n: int) -> None:
    """Property-based test infrastructure (Hypothesis)."""
    assert isinstance(n, int)


@pytest.mark.benchmark
def test_benchmark_marker_works(benchmark: Any) -> None:
    """Benchmark infrastructure."""
    benchmark(lambda: 1 + 1)
