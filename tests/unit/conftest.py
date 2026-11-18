"""Unit-test-scoped fixtures.

The existing autouse fixture (_isolate_structlog_config) lives in
tests/conftest.py (repo root). pytest merges conftest scopes, so both
coexist correctly. This file is specifically for unit-test-scoped fixtures.

The former autouse reset_executor_caches fixture was retired with the
executor module-global caches it reset (spec #93 T4): the derived sets are
now derived per call behind the loader's stat-key cache.
"""
