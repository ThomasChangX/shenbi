"""Unit-test-scoped fixtures.

The existing autouse fixture (_isolate_structlog_config) lives in
tests/conftest.py (repo root). pytest merges conftest scopes, so both
coexist correctly. This file is specifically for unit-test-scoped fixtures.
"""

import pytest

from shenbi.dispatcher import executor


@pytest.fixture(autouse=True)
def reset_executor_caches():
    """Reset module-global caches before each test to prevent order-dependence."""
    executor._truth_files_cache = None
    executor._decisions_files_cache = None
    yield
    executor._truth_files_cache = None
    executor._decisions_files_cache = None
