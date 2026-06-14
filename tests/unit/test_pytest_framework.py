"""Verify pytest framework infrastructure works."""

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st


def test_conftest_fixtures_loadable(tmp_project_dir: object, configure_logging: object) -> None:
    """All global fixtures defined in conftest.py should load."""
    assert tmp_project_dir is not None


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
