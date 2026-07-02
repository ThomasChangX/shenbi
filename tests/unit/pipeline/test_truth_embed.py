"""Tests for Route B float32 embedding store (wave2 task2).

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md §7.3-7.4.
Route B stores text chunks as float32 embeddings and retrieves by numpy
cosine similarity. The embedding *model* (sentence_transformers) is optional:
when absent, Route B degrades gracefully (§7.3).
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from shenbi.pipeline.truth_embed import (
    EmbeddingStore,
    embed_and_store,
    is_embed_available,
)


def _vec(*values: float) -> bytes:
    """Pack floats into a native float32 byte vector."""
    return struct.pack(f"{len(values)}f", *values)


class TestEmbeddingStore:
    def test_store_and_retrieve_float32(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        vec = _vec(1.0, 0.0, 0.0)
        store.upsert(
            "c1",
            "truth/chapter_summaries.md",
            "chapter_summary",
            1,
            '["Hero"]',
            "Hero finds sword",
            vec,
        )
        result = store.get("c1")
        assert result is not None
        assert result.text == "Hero finds sword"
        assert result.chunk_type == "chapter_summary"
        assert result.chapter_ref == 1
        assert result.entity_refs == '["Hero"]'
        store.close()

    def test_upsert_replaces_existing_chunk(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        store.upsert("c1", "f1", "summary", 1, "[]", "old text", _vec(1.0, 0.0))
        store.upsert("c1", "f1", "summary", 1, "[]", "new text", _vec(0.0, 1.0))
        result = store.get("c1")
        assert result is not None
        assert result.text == "new text"
        store.close()

    def test_get_missing_chunk_returns_none(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        assert store.get("nonexistent") is None
        store.close()


class TestCosineSimilarity:
    def test_cosine_similarity_correct(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        store.upsert("c1", "f1", "summary", 1, "[]", "dragon", _vec(1.0, 0.0))
        store.upsert("c2", "f2", "summary", 2, "[]", "sword", _vec(0.0, 1.0))
        query = _vec(1.0, 0.1)  # closer to c1 than c2
        results = store.search_cosine(query, top_k=2)
        assert results[0].chunk_id == "c1"  # higher similarity
        assert results[0].similarity > results[1].similarity
        store.close()

    def test_identical_vectors_have_similarity_one(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        store.upsert("c1", "f1", "summary", 1, "[]", "a", _vec(1.0, 0.0))
        results = store.search_cosine(_vec(1.0, 0.0), top_k=1)
        assert len(results) == 1
        assert abs(results[0].similarity - 1.0) < 1e-6
        store.close()

    def test_search_empty_store_returns_empty(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        results = store.search_cosine(_vec(1.0, 0.0), top_k=5)
        assert results == []
        store.close()

    def test_search_respects_top_k(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        for i in range(5):
            store.upsert(f"c{i}", "f", "summary", i, "[]", f"t{i}", _vec(float(i), 0.0))
        results = store.search_cosine(_vec(4.0, 0.0), top_k=3)
        assert len(results) == 3
        store.close()

    def test_dimension_mismatch_skipped(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        store.upsert("c1", "f1", "summary", 1, "[]", "a", _vec(1.0, 0.0))
        store.upsert("c2", "f2", "summary", 2, "[]", "b", _vec(1.0, 0.0, 0.0))
        # query is 2-dim: c2 (3-dim) must be skipped, only c1 returned
        results = store.search_cosine(_vec(1.0, 0.0), top_k=10)
        assert len(results) == 1
        assert results[0].chunk_id == "c1"
        store.close()


class TestDegradationPath:
    """§7.3: when the embedding model is unavailable, Route B degrades.

    is_embed_available() must always return a bool; embed_and_store must
    return False without raising so the orchestrator can set
    route_b_degraded: true.
    """

    def test_is_embed_available_returns_bool(self):
        assert isinstance(is_embed_available(), bool)

    def test_embed_and_store_returns_false_when_unavailable(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        if is_embed_available():
            pytest.skip("sentence_transformers installed; degradation path not testable")
        ok = embed_and_store(store, "some text", "c1", "f.md", "summary")
        assert ok is False
        # Nothing should have been stored.
        assert store.get("c1") is None
        store.close()
