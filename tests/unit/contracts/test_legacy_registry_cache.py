"""T1613/F215 (C28 R2a): load_registry (path, mtime_ns, size) process cache.

Same mtime_ns+size -> exactly one YAML parse; any file change (mtime_ns
covers same-second edits) invalidates. The cached pydantic model is shared —
read-only by convention (callers audited 2026-09-04: zero mutation sites).
"""

from __future__ import annotations

import os
from typing import Any

import pytest
import yaml

from shenbi.contracts import legacy


def _counting_safe_load(calls: dict[str, int]) -> Any:
    real_safe_load = yaml.safe_load

    def counting(*a: Any, **k: Any) -> Any:
        calls["n"] += 1
        return real_safe_load(*a, **k)

    return counting


def test_load_registry_caches_until_mtime_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}
    monkeypatch.setattr(yaml, "safe_load", _counting_safe_load(calls))
    # cache reset for test isolation (os.utime below only touches mtime of the
    # real registry file — content unchanged, safe under the ns-keyed cache)
    monkeypatch.setattr(legacy, "_registry_cache", {})

    legacy.load_registry()
    legacy.load_registry()
    legacy.load_registry()
    assert calls["n"] == 1

    st = legacy.REGISTRY_PATH.stat()
    os.utime(legacy.REGISTRY_PATH, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
    legacy.load_registry()
    assert calls["n"] == 2


def test_registry_cache_hit_path_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unchanged file -> single parse across repeated loads (hit path)."""
    calls = {"n": 0}
    monkeypatch.setattr(yaml, "safe_load", _counting_safe_load(calls))
    monkeypatch.setattr(legacy, "_registry_cache", {})
    legacy.load_registry()
    legacy.load_registry()
    assert calls["n"] == 1
