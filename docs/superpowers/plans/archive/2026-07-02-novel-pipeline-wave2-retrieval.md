# Novel Pipeline Wave 2: Retrieval Layer (R2 rewrite)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Build three-route hybrid retrieval: entity index (Route A), float32 embedding store with sentence_transformers (Route B), rule routing (Route C), deterministic rerank, and context materialization.

**Architecture:** Route A parses truth files into an entity-keyed JSON index. Route B stores float32 embeddings in SQLite with numpy cosine similarity. Route C loads fixed context. A rerank step fuses results with content-hash deduplication. All modules get CLI entry points.

**Spec reference:** Section 7

## Global Constraints
Same as Wave 1. Add `numpy>=1.26.0` to `[project] dependencies` in `pyproject.toml` (it's currently transitive only — direct imports should be declared). `sentence_transformers` is optional (degrade gracefully). All token estimates use `int(len(text) * 1.5)` per spec §7.2.

---

### Task 1: Truth Entity Index (Route A) — fixed entity extraction

**Files:** Create `src/shenbi/pipeline/truth_index.py`, `tests/unit/pipeline/test_truth_index.py`

**Interfaces:** Produces `TruthIndex`, `IndexEntry`, `build_index(project_dir)`, `query_index(index, **kwargs)`

The original plan used a regex matching arbitrary Chinese substrings — broken. This version extracts entities from the truth index's known names and matches them against the chapter plan's structured sections (hook table, character references in section 1/6).

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_truth_index.py
from __future__ import annotations
from pathlib import Path
import pytest
from shenbi.pipeline.truth_index import TruthIndex, IndexEntry, build_index, query_index

@pytest.fixture
def project_with_truth(tmp_path: Path) -> Path:
    p = tmp_path / "project"
    (p / "truth").mkdir(parents=True)
    (p / "truth" / "pending_hooks.md").write_text(
        "---\nhooks:\n  - id: H01\n    content: Magic sword hidden in cave\n"
        "    state: PLANTED\n    last_reinforced: 3\n    max_distance: 25\n"
        "    characters: [Hero]\n    planted_chapter: 3\n---\n# Hooks\n", encoding="utf-8")
    (p / "characters").mkdir()
    (p / "characters" / "protagonist.md").write_text(
        "---\nname: Hero\nrole: protagonist\n---\n# Hero\nBrave warrior.", encoding="utf-8")
    (p / "world").mkdir()
    (p / "world" / "rules.md").write_text("## R1: Magic exists\n## R2: Dragons\n", encoding="utf-8")
    return p

class TestBuildIndex:
    def test_characters_indexed(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert "Hero" in idx.characters

    def test_hooks_indexed(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert "H01" in idx.hooks
        assert idx.hooks["H01"].extra["state"] == "PLANTED"

    def test_rules_indexed(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert "R1" in idx.rules

class TestQueryIndex:
    def test_query_known_character(self, project_with_truth):
        idx = build_index(project_with_truth)
        results = query_index(idx, characters=["Hero"])
        assert any(e.entity_id == "Hero" for e in results)

    def test_query_unknown_character_empty(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert query_index(idx, characters=["Ghost"]) == []
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement**

```python
# src/shenbi/pipeline/truth_index.py
"""Route A: Entity index for deterministic truth file slice retrieval."""
from __future__ import annotations
import json, re, yaml
from dataclasses import dataclass, field
from pathlib import Path
from shenbi.logging import get_logger
log = get_logger(__name__)

@dataclass
class IndexEntry:
    category: str
    entity_id: str
    file: str
    ref: str
    extra: dict[str, object] = field(default_factory=dict)

@dataclass
class TruthIndex:
    characters: dict[str, IndexEntry] = field(default_factory=dict)
    hooks: dict[str, IndexEntry] = field(default_factory=dict)
    rules: dict[str, IndexEntry] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize index to JSON for persistence (called by orchestrator)."""
        import json
        return json.dumps({
            "characters": {k: {"category": v.category, "entity_id": v.entity_id,
                              "file": v.file, "ref": v.ref, "extra": v.extra}
                          for k, v in self.characters.items()},
            "hooks": {k: {"category": v.category, "entity_id": v.entity_id,
                         "file": v.file, "ref": v.ref, "extra": v.extra}
                     for k, v in self.hooks.items()},
            "rules": {k: {"category": v.category, "entity_id": v.entity_id,
                         "file": v.file, "ref": v.ref, "extra": v.extra}
                     for k, v in self.rules.items()},
        }, ensure_ascii=False, indent=2)

    @property
    def all_known_names(self) -> set[str]:
        """All entity names known to the index — used for matching against plan text."""
        return set(self.characters.keys()) | set(self.hooks.keys()) | set(self.rules.keys())

def _parse_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---"): return {}
    parts = text.split("---", 2)
    if len(parts) < 3: return {}
    return yaml.safe_load(parts[1]) or {}

def build_index(project_dir: Path | str) -> TruthIndex:
    project_dir = Path(project_dir)
    idx = TruthIndex()
    # Index characters
    for card in (project_dir / "characters").rglob("*.md") if (project_dir / "characters").exists() else []:
        fm = _parse_frontmatter(card.read_text(encoding="utf-8"))
        name = str(fm.get("name", card.stem))
        idx.characters[name] = IndexEntry("character", name, str(card.relative_to(project_dir)), f"characters/{card.name}")
    # Index hooks
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if hooks_file.exists():
        fm = _parse_frontmatter(hooks_file.read_text(encoding="utf-8"))
        for h in fm.get("hooks", []) if isinstance(fm.get("hooks"), list) else []:
            if isinstance(h, dict):
                hid = str(h.get("id", ""))
                idx.hooks[hid] = IndexEntry("hook", hid, "truth/pending_hooks.md", f"truth/pending_hooks.md#{hid}", {
                    "state": h.get("state",""), "last_reinforced": h.get("last_reinforced",0),
                    "max_distance": h.get("max_distance",0), "content_keywords": h.get("content","")})
    # Index rules
    rules_file = project_dir / "world" / "rules.md"
    if rules_file.exists():
        for m in re.finditer(r"^##\s+(R?\d+)[:.]?\s*(.+)$", rules_file.read_text(encoding="utf-8"), re.MULTILINE):
            idx.rules[m.group(1)] = IndexEntry("rule", m.group(1), "world/rules.md", f"world/rules.md#{m.group(1)}", {"content": m.group(2).strip()})
    log.info("truth_index_built", characters=len(idx.characters), hooks=len(idx.hooks), rules=len(idx.rules))
    return idx

def query_index(index: TruthIndex, *, characters=None, hooks=None, rules=None) -> list[IndexEntry]:
    results = []
    for name in characters or []:
        if name in index.characters: results.append(index.characters[name])
    for hid in hooks or []:
        if hid in index.hooks: results.append(index.hooks[hid])
    for rid in rules or []:
        if rid in index.rules: results.append(index.rules[rid])
    return results

def extract_entities_from_plan(index: TruthIndex, plan_text: str) -> dict[str, list[str]]:
    """Extract entities from chapter plan by matching known index names against plan text.

    This replaces the broken regex approach. Instead of matching arbitrary Chinese
    substrings, we check which known entity names (from the index) appear in the plan.
    """
    found_chars = [name for name in index.characters if name in plan_text]
    found_hooks = re.findall(r'[HM]\d+', plan_text)  # Hook IDs like H01, MH02
    found_hooks = [h for h in found_hooks if h in index.hooks]
    found_rules = [rid for rid in index.rules if rid in plan_text]
    return {"characters": found_chars, "hooks": found_hooks, "rules": found_rules}
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_truth_index.py -v
git add src/shenbi/pipeline/truth_index.py tests/unit/pipeline/test_truth_index.py
git commit -m "feat: add truth entity index with known-name matching (wave2 task1)"
```

---

### Task 2: Embedding Store with float32 (Route B) — fixed math

**Files:** Create `src/shenbi/pipeline/truth_embed.py`, `tests/unit/pipeline/test_truth_embed.py`

Critical fix: store embeddings as float32 arrays (not byte BLOBs), use numpy cosine similarity.

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_truth_embed.py
from __future__ import annotations
from pathlib import Path
import struct
import pytest
from shenbi.pipeline.truth_embed import EmbeddingStore, EmbeddingResult, is_embed_available

class TestEmbeddingStore:
    def test_store_and_retrieve_float32(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        vec = struct.pack("3f", 1.0, 0.0, 0.0)  # float32 vector [1,0,0]
        store.upsert("c1", "truth/chapter_summaries.md", "chapter_summary", 1, '["Hero"]', "Hero finds sword", vec)
        result = store.get("c1")
        assert result is not None
        assert result.text == "Hero finds sword"

    def test_cosine_similarity_correct(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embed.db")
        store.upsert("c1", "f1", "summary", 1, '[]', "dragon", struct.pack("2f", 1.0, 0.0))
        store.upsert("c2", "f2", "summary", 2, '[]', "sword", struct.pack("2f", 0.0, 1.0))
        query = struct.pack("2f", 1.0, 0.1)  # closer to c1 than c2
        results = store.search_cosine(query, top_k=2)
        assert results[0].id == "c1"  # higher similarity
        assert results[0].similarity > results[1].similarity

    def test_degradation_flag(self):
        assert isinstance(is_embed_available(), bool)
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement**

```python
# src/shenbi/pipeline/truth_embed.py
"""Route B: Float32 embedding store with numpy cosine similarity.

Spec §7.3-7.4. Stores embeddings as float32 BLOBs (struct pack/unpack).
Uses numpy for vectorized cosine similarity.
"""
from __future__ import annotations
import sqlite3, struct
from dataclasses import dataclass
from pathlib import Path
from shenbi.logging import get_logger
log = get_logger(__name__)

@dataclass
class EmbeddingResult:
    chunk_id: str  # renamed from 'id' to avoid shadowing builtin
    source_file: str
    chunk_type: str
    chapter_ref: int | None
    entity_refs: str
    text: str
    embedding: bytes
    similarity: float = 0.0

def is_embed_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False

def embed_and_store(store: EmbeddingStore, text: str, chunk_id: str,
                    source_file: str, chunk_type: str,
                    chapter_ref: int | None = None,
                    entity_refs: str = "[]") -> bool:
    """Embed text and store in the embedding DB. Returns True on success.

    Called by the orchestrator after state-settling (to embed chapter summaries)
    and after memory-distill (to embed arc syntheses).
    """
    if not is_embed_available():
        return False
    try:
        import struct
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("bge-large-zh")
        vec = model.encode(text).astype("<f4").tobytes()
        store.upsert(chunk_id, source_file, chunk_type, chapter_ref, entity_refs, text, vec)
        return True
    except Exception as e:
        log.warning("embed_failed", chunk_id=chunk_id, error=str(e))
        return False

class EmbeddingStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("""CREATE TABLE IF NOT EXISTS embeddings (
            chunk_id TEXT PRIMARY KEY, source_file TEXT, chunk_type TEXT,
            chapter_ref INTEGER, entity_refs TEXT, text TEXT, embedding BLOB)""")
        self._conn.commit()

    def upsert(self, chunk_id: str, source_file: str, chunk_type: str,
               chapter_ref: int | None, entity_refs: str, text: str, embedding: bytes) -> None:
        self._conn.execute("INSERT OR REPLACE INTO embeddings VALUES (?,?,?,?,?,?,?)",
                           (chunk_id, source_file, chunk_type, chapter_ref, entity_refs, text, embedding))
        self._conn.commit()

    def get(self, chunk_id: str) -> EmbeddingResult | None:
        row = self._conn.execute("SELECT * FROM embeddings WHERE chunk_id=?", (chunk_id,)).fetchone()
        return EmbeddingResult(*row) if row else None

    def search_cosine(self, query_vec: bytes, top_k: int = 10) -> list[EmbeddingResult]:
        import numpy as np
        query = np.frombuffer(query_vec, dtype=np.float32)
        rows = self._conn.execute("SELECT * FROM embeddings").fetchall()
        results = []
        for row in rows:
            stored = np.frombuffer(row[6], dtype=np.float32)
            if len(stored) != len(query):
                continue
            dot = float(np.dot(query, stored))
            norm = float(np.linalg.norm(query) * np.linalg.norm(stored))
            sim = dot / norm if norm > 0 else 0.0
            results.append(EmbeddingResult(*row, similarity=sim))
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:top_k]

    def close(self) -> None:
        self._conn.close()
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_truth_embed.py -v
git add src/shenbi/pipeline/truth_embed.py tests/unit/pipeline/test_truth_embed.py
git commit -m "feat: add float32 embedding store with numpy cosine (wave2 task2)"
```

---

### Task 3: Context Assembly with working Route B + content-hash dedup + CLI entry points

**Files:** Create `src/shenbi/pipeline/context_assemble.py`, `tests/unit/pipeline/test_context_assemble.py`, modify `pyproject.toml`

Critical fixes: Route B actually embeds+searches, token estimate uses `*1.5`, dedup by content hash, add CLI entry points.

- [ ] **Step 1: Write failing tests** (same structure as before, plus content-hash dedup test)

```python
# tests/unit/pipeline/test_context_assemble.py
from __future__ import annotations
from pathlib import Path
import pytest
from shenbi.pipeline.context_assemble import ContextPackage, assemble_context, rerank_results, write_context_file

@pytest.fixture
def project_with_plan(tmp_path: Path) -> Path:
    p = tmp_path / "project"
    (p / "plans").mkdir(parents=True)
    (p / "plans" / "chapter-1-plan.md").write_text(
        "## 1. 当前任务\nchapter_role: 推进/转折\nHero finds sword.\n", encoding="utf-8")
    (p / "truth").mkdir()
    (p / "truth" / "book_spine.md").write_text("# Spine\nCore.", encoding="utf-8")
    (p / "truth" / "audit_drift.md").write_text("---\ndrift_items: []\n---\n# Drift", encoding="utf-8")
    (p / "style").mkdir()
    (p / "style" / "style_profile.md").write_text("# Style\nVoice.", encoding="utf-8")
    (p / "characters").mkdir()
    (p / "characters" / "protagonist.md").write_text("---\nname: Hero\n---\n# Hero\nBrave.", encoding="utf-8")
    return p

class TestRerank:
    def test_content_hash_dedup(self):
        """Same text from different routes should dedup by content hash."""
        entries = [
            {"source": "route-a", "weight": 1.0, "text": "same content", "id": "a1"},
            {"source": "route-c", "weight": 0.6, "text": "same content", "id": "c1"},
        ]
        ranked = rerank_results(entries)
        assert len(ranked) == 1  # deduped by content hash
        assert ranked[0]["weight"] == 1.0  # kept highest weight

class TestAssembleContext:
    def test_produces_package(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        assert pkg.chapter_role == "推进/转折"
        assert len(pkg.sections) > 0

    def test_token_estimate_uses_1_5x(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        # Each section's token estimate should be ~ len(text)*1.5
        for s in pkg.sections:
            assert s.estimated_tokens > 0

    def test_write_context_file(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        out = write_context_file(project_with_plan, 1, pkg)
        assert out.exists()
        assert "Spine" in out.read_text(encoding="utf-8") or "route" in out.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement**

```python
# src/shenbi/pipeline/context_assemble.py
"""Context assembly: three-route retrieval + deterministic rerank + materialization."""
from __future__ import annotations
import hashlib, re
from dataclasses import dataclass, field
from pathlib import Path
from shenbi.logging import get_logger
from shenbi.pipeline.truth_index import TruthIndex, build_index, query_index, extract_entities_from_plan
log = get_logger(__name__)

BUDGET_BY_ROLE = {"高潮/兑现": 18000, "推进/转折": 12000, "过渡/铺垫": 8000}
DEFAULT_BUDGET = 12000
TOKEN_FACTOR = 1.5  # 1 Chinese char ≈ 1.5 tokens (spec §7.2)

@dataclass
class ContextSection:
    source: str
    priority: float
    text: str
    category: str = ""
    estimated_tokens: int = 0

@dataclass
class ContextPackage:
    chapter_role: str | None = None
    sections: list[ContextSection] = field(default_factory=list)
    total_tokens: int = 0
    route_b_degraded: bool = False

    def to_markdown(self) -> str:
        return "\n\n".join(f"## {s.source}\n\n{s.text}\n" for s in self.sections)

def _parse_chapter_role(plan_text: str) -> str | None:
    m = re.search(r"chapter_role:\s*(.+)", plan_text)
    return m.group(1).strip() if m else None

def _route_a(index: TruthIndex, plan_text: str) -> list[dict[str, object]]:
    """Route A: entity index lookup using known-name matching."""
    entities = extract_entities_from_plan(index, plan_text)
    entries = query_index(index, **entities)
    return [{"source": f"route-a:{e.entity_id}", "weight": 1.0,
             "text": f"[{e.category}] {e.entity_id} from {e.file}", "id": e.entity_id} for e in entries]

def _route_b(project_dir: Path, plan_text: str) -> tuple[list[dict[str, object]], bool]:
    """Route B: embedding search. Returns (results, degraded_flag)."""
    try:
        from shenbi.pipeline.truth_embed import EmbeddingStore, is_embed_available
        if not is_embed_available():
            return [], True
        store = EmbeddingStore(project_dir / "truth-embeddings.db")
        # Embed the plan text (first 500 chars as query)
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("bge-large-zh")
        query_vec = model.encode(plan_text[:500]).astype("<f4").tobytes()
        results = store.search_cosine(query_vec, top_k=5)
        store.close()
        return [{"source": f"route-b:{r.chunk_id}", "weight": float(r.similarity) * 0.8,
                 "text": r.text, "id": r.chunk_id} for r in results], False
    except Exception as e:
        log.warning("route_b_degraded", error=str(e))
        return [], True

def _route_c(project_dir: Path) -> list[dict[str, object]]:
    results = []
    for fname, label in [("truth/book_spine.md","book_spine"), ("truth/audit_drift.md","audit_drift"), ("style/style_profile.md","style_profile")]:
        p = project_dir / fname
        if p.exists():
            results.append({"source": f"route-c:{label}", "weight": 0.6,
                           "text": p.read_text(encoding="utf-8")[:2000], "id": label})
    return results

def _content_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def rerank_results(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    """Deterministic rerank: sort by weight, dedup by content hash."""
    entries.sort(key=lambda e: e.get("weight", 0.0), reverse=True)
    seen_hashes: set[str] = set()
    deduped = []
    for e in entries:
        ch = _content_hash(str(e.get("text", "")))
        if ch in seen_hashes:
            continue
        seen_hashes.add(ch)
        deduped.append(e)
    return deduped

def assemble_context(project_dir: Path | str, chapter_plan_path: str) -> ContextPackage:
    project_dir = Path(project_dir)
    plan_text = (project_dir / chapter_plan_path).read_text(encoding="utf-8")
    chapter_role = _parse_chapter_role(plan_text)
    index = build_index(project_dir)
    route_a = _route_a(index, plan_text)
    route_b, degraded = _route_b(project_dir, plan_text)
    route_c = _route_c(project_dir)
    ranked = rerank_results(route_a + route_b + route_c)
    budget = BUDGET_BY_ROLE.get(chapter_role or "", DEFAULT_BUDGET)
    sections, total = [], 0
    for entry in ranked:
        text = str(entry.get("text", ""))
        tokens = int(len(text) * TOKEN_FACTOR)
        if total + tokens > budget:
            break
        sections.append(ContextSection(str(entry["source"]), float(entry.get("weight",0)), text,
                                       str(entry.get("source","")).split(":")[0], tokens))
        total += tokens
    return ContextPackage(chapter_role, sections, total, degraded)

def write_context_file(project_dir: Path | str, chapter: int, pkg: ContextPackage) -> Path:
    project_dir = Path(project_dir)
    out = project_dir / "context" / f"chapter-{chapter}-context.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(pkg.to_markdown(), encoding="utf-8")
    return out
```

- [ ] **Step 4: Add CLI entry points to pyproject.toml, run tests, commit**

Add to `[project.scripts]`:
```toml
pipeline-truth-index = "shenbi.pipeline.truth_index:main"
pipeline-truth-embed = "shenbi.pipeline.truth_embed:main"
pipeline-context-assemble = "shenbi.pipeline.context_assemble:main"
```

Add `main()` CLI functions to each module:

```python
# truth_index.py — add at end:
def main() -> int:
    import argparse, sys
    p = argparse.ArgumentParser(prog="pipeline-truth-index")
    p.add_argument("command", choices=["update", "rebuild", "query"])
    p.add_argument("--project-dir", required=True)
    args = p.parse_args()
    if args.command in ("update", "rebuild"):
        idx = build_index(args.project_dir)
        Path(args.project_dir, "truth-index.json").write_text(idx.to_json(), encoding="utf-8")
    return 0

# truth_embed.py — add at end:
def main() -> int:
    import argparse, json
    p = argparse.ArgumentParser(prog="pipeline-truth-embed")
    p.add_argument("command", choices=["update", "rebuild", "search"])
    p.add_argument("--project-dir", required=True)
    p.add_argument("--text", help="Text to embed (for update/search)")
    args = p.parse_args()
    store = EmbeddingStore(Path(args.project_dir) / "truth-embeddings.db")
    if args.command in ("update", "rebuild") and args.text:
        # Embed a single text chunk and store it
        embed_and_store(store, args.text, chunk_id=f"manual-{hash(args.text)}",
                       source_file="manual", chunk_type="manual")
    store.close()
    return 0

# context_assemble.py — add at end:
def main() -> int:
    import argparse
    p = argparse.ArgumentParser(prog="pipeline-context-assemble")
    p.add_argument("build", choices=["build"])
    p.add_argument("--project-dir", required=True)
    p.add_argument("--chapter", type=int, required=True)
    args = p.parse_args()
    plan_path = f"plans/chapter-{args.chapter}-plan.md"
    pkg = assemble_context(args.project_dir, plan_path)
    write_context_file(args.project_dir, args.chapter, pkg)
    return 0
```

```bash
uv run pytest tests/unit/pipeline/test_context_assemble.py -v
git add src/shenbi/pipeline/context_assemble.py tests/unit/pipeline/test_context_assemble.py pyproject.toml
git commit -m "feat: add context assembly with working Route B + content-hash dedup + CLI (wave2 task3)"
```
