"""T1603/F328 (C28 R2b): shared model singleton + TTL negative cache.

Construction points today (both sequential): context_assemble._route_b and
truth_embed.embed_and_store (genesis re-instantiates per entry). The lock is
defensive — no concurrent construction path exists, but the singleton must
still be correct by construction.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import Any, cast

import pytest

import shenbi.pipeline.truth_embed as te


@pytest.fixture
def te_reset_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(te, "_model_state", {"model": None, "neg_until": 0.0})


def _patch_st(monkeypatch: pytest.MonkeyPatch, ctor: Any) -> None:
    import importlib

    monkeypatch.setattr(te, "is_embed_available", lambda: True)
    fake_mod = SimpleNamespace(SentenceTransformer=ctor)
    monkeypatch.setattr(importlib, "import_module", lambda name: fake_mod)


def _make_fake_st() -> Any:
    """Fresh counting class per test (a class-level counter would leak across
    tests under pytest's alphabetical execution order).
    """

    class FakeST:
        instances = 0

        def __init__(self, name: str) -> None:
            FakeST.instances += 1

    return FakeST


def test_singleton_constructs_once(te_reset_cache: None, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _make_fake_st()
    _patch_st(monkeypatch, fake)
    assert te.get_shared_model() is not None
    assert te.get_shared_model() is not None
    assert fake.instances == 1


def test_concurrent_init_constructs_once(
    te_reset_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _make_fake_st()
    _patch_st(monkeypatch, fake)
    threads = [threading.Thread(target=te.get_shared_model) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert fake.instances == 1  # defensive: no concurrent path today


def test_negative_cache_suppresses_retry(
    te_reset_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    constructed = {"n": 0}

    class _Boom:
        def __init__(self, name: str) -> None:
            constructed["n"] += 1
            raise RuntimeError("HF 401")

    _patch_st(monkeypatch, _Boom)
    assert te.get_shared_model() is None  # failure cached (constructed 1)
    assert te.get_shared_model() is None  # within TTL: suppressed
    assert te.get_shared_model() is None
    assert constructed["n"] == 1  # no retry within TTL
    monkeypatch.setitem(te._model_state, "neg_until", 0.0)  # expire
    assert te.get_shared_model() is None  # retries once, fails again
    assert constructed["n"] == 2


def test_embed_and_store_uses_singleton(
    te_reset_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """embed_and_store must not re-instantiate the model (F328: genesis
    re-loaded bge-large-zh per hook/rule entry).
    """
    calls = {"encode": 0}

    class _FakeModel:
        def encode(self, text: str) -> Any:
            calls["encode"] += 1
            import numpy as np

            return np.zeros(4)

    class _FakeStore:
        def upsert(self, *a: Any, **k: Any) -> None:
            pass

    fake = _make_fake_st()
    _patch_st(monkeypatch, fake)
    model = te.get_shared_model()
    assert isinstance(model, fake)
    # swap the singleton for an encode-capable fake, then call twice:
    # construction count must stay at 1
    monkeypatch.setitem(te._model_state, "model", _FakeModel())
    ok1 = te.embed_and_store(cast(Any, _FakeStore()), "text", "c1", "f.md", "hook")
    ok2 = te.embed_and_store(cast(Any, _FakeStore()), "text2", "c2", "f.md", "rule")
    assert ok1 and ok2
    assert calls["encode"] == 2
    assert fake.instances == 1  # no re-construction in embed_and_store
