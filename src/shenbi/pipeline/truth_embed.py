"""Route B: float32 embedding store with numpy cosine similarity.

Spec §7.3-7.4. Stores text chunks and their float32 embeddings in a SQLite
database; retrieval uses vectorized numpy cosine similarity. The embedding
*model* (``sentence_transformers`` with ``bge-large-zh``) is optional: when it
is unavailable, :func:`is_embed_available` returns ``False`` and
:func:`embed_and_store` returns ``False`` so the orchestrator can mark
``route_b_degraded: true`` in pipeline-state.json (§7.3 degradation path).

``sentence_transformers`` is loaded dynamically via :mod:`importlib` so that the
optional dependency is never imported at module level — this keeps both the
framework import-safe and the type checkers (mypy/basedpyright) clean.

Chunk types (§7.4): ``chapter_summary``, ``arc_synthesis``,
``character_arc``, ``hook``, ``rule``, ``volume_summary``. These are stored as
opaque strings; this module does not validate chunk_type values, leaving that
to the orchestrator.
"""

from __future__ import annotations

import importlib
import importlib.util
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger

log = get_logger(__name__)

# Chunk types recognised by §7.4. Exposed for callers that want to enumerate
# valid values, but upsert/search do NOT enforce membership.
CHUNK_TYPES: frozenset[str] = frozenset(
    {"chapter_summary", "arc_synthesis", "character_arc", "hook", "rule", "volume_summary"}
)


@dataclass
class EmbeddingResult:
    """A single stored embedding chunk, optionally scored by similarity.

    Attributes:
        chunk_id: Primary key (caller-assigned, e.g. ``summary-ch001``).
        source_file: Truth file the chunk was extracted from.
        chunk_type: One of §7.4's chunk types (stored verbatim, not enforced).
        chapter_ref: Chapter number the chunk is anchored to, or ``None``.
        entity_refs: JSON list of referenced entity ids (e.g. ``'["Hero"]'``).
        text: The chunk's prose content.
        embedding: Raw float32 bytes (struct-packed, native endian).
        similarity: Cosine similarity to the query vector (0.0 on direct get).
    """

    chunk_id: str
    source_file: str
    chunk_type: str
    chapter_ref: int | None
    entity_refs: str
    text: str
    embedding: bytes
    similarity: float = 0.0


def _row_to_result(row: Any, similarity: float = 0.0) -> EmbeddingResult:
    """Build an EmbeddingResult from a 7-column sqlite row tuple.

    Columns (in SELECT order): chunk_id, source_file, chunk_type, chapter_ref,
    entity_refs, text, embedding. Using explicit indices rather than ``*row``
    keeps the type checkers happy (sqlite rows are ``tuple[Any, ...]``).
    """
    return EmbeddingResult(
        chunk_id=row[0],
        source_file=row[1],
        chunk_type=row[2],
        chapter_ref=row[3],
        entity_refs=row[4],
        text=row[5],
        embedding=row[6],
        similarity=similarity,
    )


def is_embed_available() -> bool:
    """Return ``True`` iff the embedding model dependency is installed.

    Uses ``importlib.util.find_spec`` so the optional dependency is never
    imported at module level. This is the §7.3 gate: callers check it before
    attempting to embed, and set ``route_b_degraded: true`` when it returns
    ``False``.
    """
    return importlib.util.find_spec("sentence_transformers") is not None


def embed_and_store(
    store: EmbeddingStore,
    text: str,
    chunk_id: str,
    source_file: str,
    chunk_type: str,
    chapter_ref: int | None = None,
    entity_refs: str = "[]",
) -> bool:
    """Embed ``text`` with ``bge-large-zh`` and store it in ``store``.

    Returns ``True`` on success, ``False`` if the model is unavailable or
    encoding fails (§7.3 degradation: the orchestrator then marks
    ``route_b_degraded`` and Routes A+C continue). Called by the orchestrator
    after state-settling (to embed chapter summaries) and after memory-distill
    (to embed arc syntheses).
    """
    if not is_embed_available():
        log.info("route_b_unavailable", chunk_id=chunk_id)
        return False
    try:
        st = importlib.import_module("sentence_transformers")
        model = st.SentenceTransformer("bge-large-zh")
        vec = model.encode(text).astype("<f4").tobytes()
    except Exception as e:
        log.warning("embed_failed", chunk_id=chunk_id, error=str(e))
        return False
    store.upsert(chunk_id, source_file, chunk_type, chapter_ref, entity_refs, text, vec)
    return True


class EmbeddingStore:
    """SQLite-backed store of float32 embedding chunks.

    Each row is one chunk (§7.4): an id, provenance metadata, the text, and
    the embedding as a raw float32 BLOB. Retrieval decodes BLOBs back to numpy
    arrays and ranks by cosine similarity to the query vector.
    """

    def __init__(self, db_path: Path | str) -> None:
        """Open (creating parent dirs and the table if needed) the SQLite DB."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS embeddings ("
            "chunk_id TEXT PRIMARY KEY, source_file TEXT, chunk_type TEXT, "
            "chapter_ref INTEGER, entity_refs TEXT, text TEXT, embedding BLOB)"
        )
        self._conn.commit()

    def upsert(
        self,
        chunk_id: str,
        source_file: str,
        chunk_type: str,
        chapter_ref: int | None,
        entity_refs: str,
        text: str,
        embedding: bytes,
    ) -> None:
        """Insert or replace the chunk identified by ``chunk_id``."""
        self._conn.execute(
            "INSERT OR REPLACE INTO embeddings "
            "(chunk_id, source_file, chunk_type, chapter_ref, entity_refs, text, embedding) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chunk_id, source_file, chunk_type, chapter_ref, entity_refs, text, embedding),
        )
        self._conn.commit()

    def get(self, chunk_id: str) -> EmbeddingResult | None:
        """Return the chunk by id, or ``None`` if it is not stored."""
        row = self._conn.execute(
            "SELECT chunk_id, source_file, chunk_type, chapter_ref, "
            "entity_refs, text, embedding FROM embeddings WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        return _row_to_result(row) if row else None

    def search_cosine(self, query_vec: bytes, top_k: int = 10) -> list[EmbeddingResult]:
        """Rank stored chunks by cosine similarity to ``query_vec``.

        ``query_vec`` is raw float32 bytes. Chunks whose embedding dimension
        differs from the query's are skipped (they are incomparable). Returns
        at most ``top_k`` results sorted by descending similarity.
        """
        import numpy as np

        query = np.frombuffer(query_vec, dtype=np.float32)  # type: ignore[var-annotated, unused-ignore]
        query_norm = float(np.linalg.norm(query))
        rows = self._conn.execute(
            "SELECT chunk_id, source_file, chunk_type, chapter_ref, "
            "entity_refs, text, embedding FROM embeddings"
        ).fetchall()
        results: list[EmbeddingResult] = []
        for row in rows:
            stored = np.frombuffer(row[6], dtype=np.float32)  # type: ignore[var-annotated, unused-ignore]
            if len(stored) != len(query):
                continue
            stored_norm = float(np.linalg.norm(stored))
            norm = query_norm * stored_norm
            sim = float(np.dot(query, stored)) / norm if norm > 0 else 0.0
            results.append(_row_to_result(row, similarity=sim))
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:top_k]

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()


__all__ = [
    "CHUNK_TYPES",
    "EmbeddingResult",
    "EmbeddingStore",
    "embed_and_store",
    "is_embed_available",
]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``pipeline-truth-embed``.

    Commands:
        rebuild --project-dir <dir>   Open/create the embedding DB (seed)
        update --project-dir <dir> --text <text>
            Embed a single text chunk and store it
    """
    import argparse
    import hashlib

    from shenbi.cli_utils import emit_json
    from shenbi.logging import configure_logging
    from shenbi.status import CommandStatus

    configure_logging()
    parser = argparse.ArgumentParser(prog="pipeline-truth-embed")
    parser.add_argument("command", choices=["rebuild", "update"])
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--text", default=None, help="Text to embed (for update)")
    args = parser.parse_args(argv)

    store = EmbeddingStore(Path(args.project_dir) / "truth-embeddings.db")

    if args.command == "update" and args.text:
        chunk_id = "manual-" + hashlib.md5(args.text.encode("utf-8")).hexdigest()[:12]
        ok = embed_and_store(store, args.text, chunk_id, "manual", "manual")
        store.close()
        emit_json({"status": CommandStatus.OK if ok else "degraded", "chunk_id": chunk_id})
        return 0

    store.close()
    emit_json({"status": CommandStatus.OK, "command": args.command})
    return 0
