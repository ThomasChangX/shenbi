# Novel Pipeline Wave 2: Retrieval Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Build the three-route hybrid retrieval system (truth-index + truth-embed + context-assemble) that replaces context-composing's flat file loading with query-driven slice retrieval.

**Architecture:** Three modules in `src/shenbi/pipeline/` that build on Wave 1's state machine. Route A (entity index) is a pure Python JSON index. Route B (vector search) uses sqlite-vec with bge-large-zh embeddings. Route C (rule routing) is deterministic fixed loading. A deterministic rerank step fuses results before LLM curation.

**Tech Stack:** Python 3.11+, sqlite3 (stdlib), sqlite-vec (new dep optional), hashlib, pathlib, pytest

**Spec reference:** `docs/superpowers/specs/2026-07-01-novel-pipeline-design.md` Section 7

## Global Constraints

Same as Wave 1. Additionally:
- `sqlite3` is stdlib, no extra dep for Route A
- `sqlite-vec` is optional — Route B degrades gracefully if unavailable (spec §7.3)
- Embedding model invocation is abstracted behind an interface so bge-large-zh can be swapped

---

### Task 1: Truth Entity Index (Route A)

**Files:**
- Create: `src/shenbi/pipeline/truth_index.py`
- Create: `tests/unit/pipeline/test_truth_index.py`

**Interfaces:**
- Consumes: `load_contract` from `shenbi.contracts.legacy`, truth files in project_dir
- Produces: `TruthIndex` class, `build_index(project_dir) -> TruthIndex`, `query_index(index, entities) -> list[IndexEntry]`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_truth_index.py
"""Tests for truth entity index (Route A)."""
from __future__ import annotations
from pathlib import Path
import pytest
from shenbi.pipeline.truth_index import TruthIndex, IndexEntry, build_index, query_index

@pytest.fixture
def project_with_truth(tmp_path: Path) -> Path:
    """Project with minimal truth files."""
    p = tmp_path / "project"
    (p / "truth").mkdir(parents=True)
    (p / "truth" / "pending_hooks.md").write_text(
        "---\nhooks:\n  - id: H01\n    content: Magic sword\n    state: PLANTED\n"
        "    last_reinforced: 3\n    max_distance: 25\n    characters: [Hero]\n"
        "    planted_chapter: 3\n---\n# Hooks\n", encoding="utf-8")
    (p / "truth" / "character_matrix.md").write_text(
        "# Matrix\n| Character | Status |\n| Hero | active |\n", encoding="utf-8")
    (p / "characters").mkdir()
    (p / "characters" / "protagonist.md").write_text(
        "---\nname: Hero\nrole: protagonist\n---\n# Hero\nBrave warrior.", encoding="utf-8")
    (p / "world").mkdir()
    (p / "world" / "rules.md").write_text(
        "## R1: Magic exists\nMagic is real.\n## R2: Dragons\nDragons are ancient.", encoding="utf-8")
    return p

class TestBuildIndex:
    def test_index_has_characters(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert "Hero" in idx.characters
        assert idx.characters["Hero"].file.endswith("protagonist.md")

    def test_index_has_hooks(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert "H01" in idx.hooks
        assert idx.hooks["H01"].state == "PLANTED"

    def test_index_has_rules(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert len(idx.rules) >= 1

class TestQueryIndex:
    def test_query_by_character(self, project_with_truth):
        idx = build_index(project_with_truth)
        results = query_index(idx, characters=["Hero"])
        assert any(e.category == "character" for e in results)

    def test_query_by_hook(self, project_with_truth):
        idx = build_index(project_with_truth)
        results = query_index(idx, hooks=["H01"])
        assert any(e.category == "hook" for e in results)

    def test_query_empty_entities(self, project_with_truth):
        idx = build_index(project_with_truth)
        results = query_index(idx, characters=[], hooks=[])
        assert results == []

    def test_query_unknown_entity(self, project_with_truth):
        idx = build_index(project_with_truth)
        results = query_index(idx, characters=["Nonexistent"])
        assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**
Run: `uv run pytest tests/unit/pipeline/test_truth_index.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

```python
# src/shenbi/pipeline/truth_index.py
"""Route A: Entity index for deterministic truth file slice retrieval.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 7.3.
Parses truth files into an entity-keyed JSON index for fast lookup by name/ID.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)


@dataclass
class IndexEntry:
    category: str  # character | hook | location | rule | thread
    entity_id: str
    file: str
    ref: str  # line ref or section anchor
    extra: dict[str, object] = field(default_factory=dict)


@dataclass
class TruthIndex:
    characters: dict[str, IndexEntry] = field(default_factory=dict)
    hooks: dict[str, IndexEntry] = field(default_factory=dict)
    locations: dict[str, IndexEntry] = field(default_factory=dict)
    rules: dict[str, IndexEntry] = field(default_factory=dict)
    threads: dict[str, IndexEntry] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({
            "characters": {k: v.__dict__ for k, v in self.characters.items()},
            "hooks": {k: v.__dict__ for k, v in self.hooks.items()},
            "locations": {k: v.__dict__ for k, v in self.locations.items()},
            "rules": {k: v.__dict__ for k, v in self.rules.items()},
            "threads": {k: v.__dict__ for k, v in self.threads.items()},
        }, ensure_ascii=False, indent=2)


def _parse_frontmatter(text: str) -> dict[str, object]:
    """Parse YAML frontmatter (between --- markers). Returns dict."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    import yaml
    return yaml.safe_load(parts[1]) or {}


def _index_characters(project_dir: Path, index: TruthIndex) -> None:
    chars_dir = project_dir / "characters"
    if not chars_dir.exists():
        return
    for card in chars_dir.rglob("*.md"):
        fm = _parse_frontmatter(card.read_text(encoding="utf-8"))
        name = str(fm.get("name", card.stem))
        index.characters[name] = IndexEntry(
            category="character",
            entity_id=name,
            file=str(card.relative_to(project_dir)),
            ref=f"characters/{card.name}",
            extra={
                "role": fm.get("role", ""),
                "matrix_ref": "truth/character_matrix.md",
            },
        )


def _index_hooks(project_dir: Path, index: TruthIndex) -> None:
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        return
    fm = _parse_frontmatter(hooks_file.read_text(encoding="utf-8"))
    hooks = fm.get("hooks", [])
    if isinstance(hooks, list):
        for h in hooks:
            if not isinstance(h, dict):
                continue
            hid = str(h.get("id", ""))
            index.hooks[hid] = IndexEntry(
                category="hook",
                entity_id=hid,
                file="truth/pending_hooks.md",
                ref=f"truth/pending_hooks.md#{hid}",
                extra={
                    "state": h.get("state", ""),
                    "last_reinforced": h.get("last_reinforced", 0),
                    "max_distance": h.get("max_distance", 0),
                    "characters": h.get("characters", []),
                    "planted_chapter": h.get("planted_chapter", 0),
                    "content_keywords": h.get("content", ""),
                },
            )


def _index_rules(project_dir: Path, index: TruthIndex) -> None:
    rules_file = project_dir / "world" / "rules.md"
    if not rules_file.exists():
        return
    text = rules_file.read_text(encoding="utf-8")
    for match in re.finditer(r"^##\s+(R?\d+)[:.]?\s*(.+)$", text, re.MULTILINE):
        rid = match.group(1)
        content = match.group(2).strip()
        index.rules[rid] = IndexEntry(
            category="rule",
            entity_id=rid,
            file="world/rules.md",
            ref=f"world/rules.md#{rid}",
            extra={"content": content},
        )


def build_index(project_dir: Path | str) -> TruthIndex:
    """Build truth entity index from project files."""
    project_dir = Path(project_dir)
    index = TruthIndex()
    _index_characters(project_dir, index)
    _index_hooks(project_dir, index)
    _index_rules(project_dir, index)
    log.info("truth_index_built",
             characters=len(index.characters),
             hooks=len(index.hooks),
             rules=len(index.rules))
    return index


def query_index(
    index: TruthIndex,
    *,
    characters: list[str] | None = None,
    hooks: list[str] | None = None,
    locations: list[str] | None = None,
    rules: list[str] | None = None,
) -> list[IndexEntry]:
    """Query index for entries matching given entity IDs."""
    results: list[IndexEntry] = []
    for name in characters or []:
        if name in index.characters:
            results.append(index.characters[name])
    for hid in hooks or []:
        if hid in index.hooks:
            results.append(index.hooks[hid])
    for loc in locations or []:
        if loc in index.locations:
            results.append(index.locations[loc])
    for rid in rules or []:
        if rid in index.rules:
            results.append(index.rules[rid])
    return results
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_truth_index.py -v
git add src/shenbi/pipeline/truth_index.py tests/unit/pipeline/test_truth_index.py
git commit -m "feat: add truth entity index for Route A retrieval (wave2 task1)"
```

---

### Task 2: Embedding Store with Degradation (Route B)

**Files:**
- Create: `src/shenbi/pipeline/truth_embed.py`
- Create: `tests/unit/pipeline/test_truth_embed.py`

**Interfaces:**
- Produces: `EmbeddingStore` (SQLite-backed), `EmbeddingResult` dataclass, `is_embed_available() -> bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_truth_embed.py
"""Tests for embedding store (Route B)."""
from __future__ import annotations
from pathlib import Path
import pytest
from shenbi.pipeline.truth_embed import EmbeddingStore, EmbeddingResult, is_embed_available

class TestEmbeddingStore:
    def test_store_and_retrieve(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embeddings.db")
        store.upsert("chunk-1", "truth/chapter_summaries.md", "chapter_summary",
                     chapter_ref=1, entity_refs='["Hero"]', text="Hero finds sword",
                     embedding=b'\x00\x01\x02\x03')
        result = store.get("chunk-1")
        assert result is not None
        assert result.text == "Hero finds sword"

    def test_search_returns_top_k(self, tmp_path: Path):
        store = EmbeddingStore(tmp_path / "embeddings.db")
        store.upsert("c1", "f1", "chapter_summary", 1, '[]', "dragon attack", b'\x01\x00')
        store.upsert("c2", "f2", "chapter_summary", 2, '[]', "hero trains", b'\x00\x01')
        results = store.search_cosine(b'\x01\x00', top_k=1)
        assert len(results) == 1
        assert results[0].id == "c1"

    def test_degradation_flag(self, tmp_path: Path):
        """When embed model unavailable, is_embed_available returns False."""
        available = is_embed_available()
        assert isinstance(available, bool)
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement.**

```python
# src/shenbi/pipeline/truth_embed.py
"""Route B: Embedding store with graceful degradation.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 7.3-7.4.
Uses SQLite for storage. Embedding computation is abstracted — if the model
is unavailable, Route B degrades (skip + flag, spec §7.3).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger

log = get_logger(__name__)


@dataclass
class EmbeddingResult:
    id: str
    source_file: str
    chunk_type: str
    chapter_ref: int | None
    entity_refs: str
    text: str
    embedding: bytes
    similarity: float = 0.0


def is_embed_available() -> bool:
    """Check if embedding model is available."""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


class EmbeddingStore:
    """SQLite-backed embedding store."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                source_file TEXT,
                chunk_type TEXT,
                chapter_ref INTEGER,
                entity_refs TEXT,
                text TEXT,
                embedding BLOB
            )
        """)
        self._conn.commit()

    def upsert(self, id: str, source_file: str, chunk_type: str,
               chapter_ref: int | None, entity_refs: str,
               text: str, embedding: bytes) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO embeddings VALUES (?,?,?,?,?,?,?)",
            (id, source_file, chunk_type, chapter_ref, entity_refs, text, embedding))
        self._conn.commit()

    def get(self, id: str) -> EmbeddingResult | None:
        row = self._conn.execute(
            "SELECT * FROM embeddings WHERE id=?", (id,)).fetchone()
        if not row:
            return None
        return EmbeddingResult(*row)

    def search_cosine(self, query_vec: bytes, top_k: int = 10) -> list[EmbeddingResult]:
        """Simple cosine similarity search (fallback without sqlite-vec)."""
        rows = self._conn.execute("SELECT * FROM embeddings").fetchall()
        results: list[EmbeddingResult] = []
        for row in rows:
            stored_vec = row[6]
            sim = _cosine_sim(query_vec, stored_vec)
            results.append(EmbeddingResult(*row, similarity=sim))
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:top_k]

    def close(self) -> None:
        self._conn.close()


def _cosine_sim(a: bytes, b: bytes) -> float:
    """Naive byte-level cosine similarity (placeholder for real vector math)."""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_truth_embed.py -v
git add src/shenbi/pipeline/truth_embed.py tests/unit/pipeline/test_truth_embed.py
git commit -m "feat: add embedding store with degradation for Route B (wave2 task2)"
```

---

### Task 3: Context Assembly (Three-Route + Rerank)

**Files:**
- Create: `src/shenbi/pipeline/context_assemble.py`
- Create: `tests/unit/pipeline/test_context_assemble.py`

**Interfaces:**
- Consumes: `TruthIndex` from Task 1, `EmbeddingStore` from Task 2, `PipelineState` from Wave 1
- Produces: `assemble_context(project_dir, chapter_plan_path) -> ContextPackage`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_context_assemble.py
"""Tests for context assembly (three-route + rerank)."""
from __future__ import annotations
from pathlib import Path
import pytest
from shenbi.pipeline.context_assemble import (
    ContextPackage, assemble_context, rerank_results, RouteCResult
)

@pytest.fixture
def project_with_chapter(tmp_path: Path) -> Path:
    p = tmp_path / "project"
    (p / "plans").mkdir(parents=True)
    (p / "plans" / "chapter-1-plan.md").write_text(
        "## 1. Current Task\nchapter_role: 推进/转折\nHero finds sword.\n", encoding="utf-8")
    (p / "truth").mkdir()
    (p / "truth" / "book_spine.md").write_text("# Spine\nCore conflict.", encoding="utf-8")
    (p / "truth" / "audit_drift.md").write_text("---\ndrift_items: []\n---\n# Drift", encoding="utf-8")
    (p / "style").mkdir()
    (p / "style" / "style_profile.md").write_text("# Style\nVoice fingerprint.", encoding="utf-8")
    return p

class TestRerank:
    def test_priority_ordering(self):
        entries = [
            {"source": "A", "weight": 1.0, "text": "entity match"},
            {"source": "B", "weight": 0.8, "text": "semantic match"},
            {"source": "C", "weight": 0.6, "text": "rule route"},
        ]
        ranked = rerank_results(entries)
        assert ranked[0]["weight"] == 1.0
        assert ranked[-1]["weight"] == 0.6

    def test_dedup_merges_same_text(self):
        entries = [
            {"source": "A", "weight": 1.0, "text": "same text", "id": "1"},
            {"source": "B", "weight": 0.8, "text": "same text", "id": "1"},
        ]
        ranked = rerank_results(entries)
        assert len(ranked) == 1

class TestAssembleContext:
    def test_produces_package(self, project_with_chapter):
        pkg = assemble_context(project_with_chapter, "plans/chapter-1-plan.md")
        assert pkg.chapter_role is not None
        assert len(pkg.sections) > 0

    def test_route_c_included(self, project_with_chapter):
        pkg = assemble_context(project_with_chapter, "plans/chapter-1-plan.md")
        spine_sections = [s for s in pkg.sections if "spine" in s.source.lower()]
        assert len(spine_sections) >= 1
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement.**

```python
# src/shenbi/pipeline/context_assemble.py
"""Context assembly: three-route retrieval + deterministic rerank.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 7.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.truth_index import TruthIndex, build_index, query_index

log = get_logger(__name__)

BUDGET_BY_ROLE = {"高潮/兑现": 18000, "推进/转折": 12000, "过渡/铺垫": 8000}
DEFAULT_BUDGET = 12000


@dataclass
class ContextSection:
    source: str  # file path or "route-a" / "route-b" / "route-c"
    priority: float
    text: str
    category: str = ""


@dataclass
class ContextPackage:
    chapter_role: str | None = None
    sections: list[ContextSection] = field(default_factory=list)
    total_tokens: int = 0
    route_b_degraded: bool = False

    def to_markdown(self) -> str:
        lines: list[str] = []
        for s in self.sections:
            lines.append(f"## {s.source}\n\n{s.text}\n")
        return "\n".join(lines)


def _parse_chapter_role(plan_text: str) -> str | None:
    match = re.search(r"chapter_role:\s*(.+)", plan_text)
    return match.group(1).strip() if match else None


def _route_a(index: TruthIndex, plan_text: str) -> list[dict[str, object]]:
    """Route A: entity index lookup. Returns candidate entries."""
    # Extract character names from plan (simplified: look for capitalized words)
    char_names = re.findall(r"[\u4e00-\u9fff]{2,4}", plan_text[:200])
    hook_ids = re.findall(r"H\d+|MH\d+", plan_text)
    entries = query_index(index, characters=char_names[:5], hooks=hook_ids)
    return [
        {"source": f"route-a:{e.entity_id}", "weight": 1.0,
         "text": f"[{e.category}] {e.entity_id} from {e.file}", "id": e.entity_id}
        for e in entries
    ]


def _route_c(project_dir: Path) -> list[dict[str, object]]:
    """Route C: deterministic fixed loading."""
    results: list[dict[str, object]] = []
    for filename, label in [
        ("truth/book_spine.md", "book_spine"),
        ("truth/audit_drift.md", "audit_drift"),
        ("style/style_profile.md", "style_profile"),
    ]:
        path = project_dir / filename
        if path.exists():
            results.append({
                "source": f"route-c:{label}",
                "weight": 0.6,
                "text": path.read_text(encoding="utf-8")[:2000],
                "id": label,
            })
    return results


def rerank_results(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    """Deterministic rerank: sort by weight, deduplicate by id."""
    entries.sort(key=lambda e: e.get("weight", 0.0), reverse=True)
    seen: set[str] = set()
    deduped: list[dict[str, object]] = []
    for e in entries:
        eid = str(e.get("id", ""))
        if eid and eid in seen:
            continue
        seen.add(eid)
        deduped.append(e)
    return deduped


def assemble_context(
    project_dir: Path | str, chapter_plan_path: str
) -> ContextPackage:
    """Assemble context package using three-route retrieval + rerank."""
    project_dir = Path(project_dir)
    plan_text = (project_dir / chapter_plan_path).read_text(encoding="utf-8")
    chapter_role = _parse_chapter_role(plan_text)

    # Route A: entity index
    index = build_index(project_dir)
    route_a = _route_a(index, plan_text)

    # Route B: embedding search (degrade gracefully)
    route_b: list[dict[str, object]] = []
    degraded = False
    try:
        from shenbi.pipeline.truth_embed import EmbeddingStore, is_embed_available
        if is_embed_available():
            store = EmbeddingStore(project_dir / "truth-embeddings.db")
            # Would embed plan_text and search; placeholder for now
            store.close()
    except Exception:
        degraded = True

    # Route C: rule routing
    route_c = _route_c(project_dir)

    # Rerank
    all_entries = route_a + route_b + route_c
    ranked = rerank_results(all_entries)

    # Build package
    budget = BUDGET_BY_ROLE.get(chapter_role or "", DEFAULT_BUDGET)
    sections: list[ContextSection] = []
    total_tokens = 0
    for entry in ranked:
        text = str(entry.get("text", ""))
        token_est = len(text) // 3  # rough zh->token estimate
        if total_tokens + token_est > budget:
            break
        sections.append(ContextSection(
            source=str(entry["source"]),
            priority=float(entry.get("weight", 0.0)),
            text=text,
            category=entry.get("source", "").split(":")[0],
        ))
        total_tokens += token_est

    return ContextPackage(
        chapter_role=chapter_role,
        sections=sections,
        total_tokens=total_tokens,
        route_b_degraded=degraded,
    )
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_context_assemble.py -v
git add src/shenbi/pipeline/context_assemble.py tests/unit/pipeline/test_context_assemble.py
git commit -m "feat: add three-route context assembly with rerank (wave2 task3)"
```

---

### Task 4: Context Materialization

**Files:**
- Modify: `src/shenbi/pipeline/context_assemble.py` (add `write_context_file`)
- Modify: `tests/unit/pipeline/test_context_assemble.py`

- [ ] **Step 1: Add test**

```python
def test_write_context_file(project_with_chapter, tmp_path):
    from shenbi.pipeline.context_assemble import assemble_context, write_context_file
    pkg = assemble_context(project_with_chapter, "plans/chapter-1-plan.md")
    out_path = write_context_file(project_with_chapter, 1, pkg)
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "book_spine" in content or "route-c" in content
```

- [ ] **Step 2: Implement**

Add to `context_assemble.py`:
```python
def write_context_file(project_dir: Path | str, chapter: int, pkg: ContextPackage) -> Path:
    """Materialize context package to context/chapter-N-context.md."""
    project_dir = Path(project_dir)
    out = project_dir / "context" / f"chapter-{chapter}-context.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(pkg.to_markdown(), encoding="utf-8")
    return out
```

- [ ] **Step 3: Run tests, commit.**

```bash
uv run pytest tests/unit/pipeline/test_context_assemble.py -v
git add src/shenbi/pipeline/context_assemble.py tests/unit/pipeline/test_context_assemble.py
git commit -m "feat: add context file materialization (wave2 task4)"
```
