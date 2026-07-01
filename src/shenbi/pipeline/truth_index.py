"""Route A: deterministic truth entity index (spec section 7.1).

Scans a novel project's truth files and extracts named entities into a
queryable index. This replaces the broken approach of matching arbitrary CJK
substrings with a regex: instead, entities are matched by their known
canonical names harvested from structured truth files.

Sources:
    - characters/*.md     -> frontmatter ``name`` key (fallback: file stem)
    - truth/pending_hooks.md -> ``hooks`` list in frontmatter
    - world/rules.md      -> ``## <id>: <text>`` headings
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from shenbi.logging import get_logger
from shenbi.text import find_terms

log = get_logger(__name__)

# Hook ids embedded in prose, e.g. "resolve H01" or "payoff MH02".
_HOOK_ID_RE = re.compile(r"[HM]\d+")
# Rule headings like "## R1: ..." or "## 2. ...".
_RULE_RE = re.compile(r"^##\s+(R?\d+)[:.]?\s*(.+)$", re.MULTILINE)


@dataclass
class IndexEntry:
    """A single indexed entity.

    Attributes:
        category: One of "character", "hook", "rule".
        entity_id: Canonical name/id used as the lookup key.
        file: Source file path relative to the project dir.
        ref: Human-readable reference into the source (may include an anchor).
        extra: Category-specific payload (hook state, rule text, ...).
    """

    category: str
    entity_id: str
    file: str
    ref: str
    extra: dict[str, object] = field(default_factory=dict)


def _entry_to_dict(entry: IndexEntry) -> dict[str, object]:
    """Flatten an entry to a JSON-serializable dict."""
    return {
        "category": entry.category,
        "entity_id": entry.entity_id,
        "file": entry.file,
        "ref": entry.ref,
        "extra": entry.extra,
    }


@dataclass
class TruthIndex:
    """Queryable index of truth-file entities for Route A retrieval."""

    characters: dict[str, IndexEntry] = field(default_factory=dict)
    hooks: dict[str, IndexEntry] = field(default_factory=dict)
    rules: dict[str, IndexEntry] = field(default_factory=dict)

    @property
    def all_known_names(self) -> set[str]:
        """Union of every entity id across all categories."""
        return set(self.characters) | set(self.hooks) | set(self.rules)

    def to_json(self) -> str:
        """Serialize the index to a JSON string for persistence by the orchestrator."""
        return json.dumps(
            {
                "characters": {k: _entry_to_dict(v) for k, v in self.characters.items()},
                "hooks": {k: _entry_to_dict(v) for k, v in self.hooks.items()},
                "rules": {k: _entry_to_dict(v) for k, v in self.rules.items()},
            },
            ensure_ascii=False,
            indent=2,
        )


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse a YAML frontmatter block delimited by leading ``---`` lines.

    Returns an empty dict when the text has no frontmatter or it is not a
    mapping. ``Any`` values are intentional: YAML yields heterogeneous data
    whose exact shapes are validated per-category by the callers.
    """
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data = yaml.safe_load(parts[1])
    return data if isinstance(data, dict) else {}


def _index_characters(project_dir: Path, idx: TruthIndex) -> None:
    """Index every character card under characters/ (recursive)."""
    chars_dir = project_dir / "characters"
    if not chars_dir.exists():
        return
    for card in chars_dir.rglob("*.md"):
        fm = _parse_frontmatter(card.read_text(encoding="utf-8"))
        name = str(fm.get("name", card.stem))
        idx.characters[name] = IndexEntry(
            category="character",
            entity_id=name,
            file=str(card.relative_to(project_dir)),
            ref=f"characters/{card.name}",
        )


def _index_hooks(project_dir: Path, idx: TruthIndex) -> None:
    """Index hook records from the frontmatter of truth/pending_hooks.md."""
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        return
    fm = _parse_frontmatter(hooks_file.read_text(encoding="utf-8"))
    raw_hooks = fm.get("hooks")
    if not isinstance(raw_hooks, list):
        return
    for hook in raw_hooks:
        if isinstance(hook, dict):
            hook_id = str(hook.get("id", ""))
            idx.hooks[hook_id] = IndexEntry(
                category="hook",
                entity_id=hook_id,
                file="truth/pending_hooks.md",
                ref=f"truth/pending_hooks.md#{hook_id}",
                extra={
                    "state": hook.get("state", ""),
                    "last_reinforced": hook.get("last_reinforced", 0),
                    "max_distance": hook.get("max_distance", 0),
                    "content_keywords": hook.get("content", ""),
                },
            )


def _index_rules(project_dir: Path, idx: TruthIndex) -> None:
    """Index world rules declared as ``## <id>: <text>`` headings."""
    rules_file = project_dir / "world" / "rules.md"
    if not rules_file.exists():
        return
    for match in _RULE_RE.finditer(rules_file.read_text(encoding="utf-8")):
        rule_id = match.group(1)
        idx.rules[rule_id] = IndexEntry(
            category="rule",
            entity_id=rule_id,
            file="world/rules.md",
            ref=f"world/rules.md#{rule_id}",
            extra={"content": match.group(2).strip()},
        )


def build_index(project_dir: Path | str) -> TruthIndex:
    """Scan truth files under ``project_dir`` and build the entity index.

    Missing source directories are treated as empty rather than errors, so an
    early-stage project with only a characters/ dir still yields a valid index.
    """
    project_dir = Path(project_dir)
    idx = TruthIndex()
    _index_characters(project_dir, idx)
    _index_hooks(project_dir, idx)
    _index_rules(project_dir, idx)
    log.info(
        "truth_index_built",
        characters=len(idx.characters),
        hooks=len(idx.hooks),
        rules=len(idx.rules),
    )
    return idx


def query_index(
    index: TruthIndex,
    *,
    characters: list[str] | None = None,
    hooks: list[str] | None = None,
    rules: list[str] | None = None,
) -> list[IndexEntry]:
    """Return entries for the requested ids that exist in the index.

    Unknown ids are silently dropped (empty list if none match). This is the
    P1 direct-involvement path of Route A (weight 1.0): callers pass the ids a
    chapter plan references and receive the backing truth entries.
    """
    results: list[IndexEntry] = []
    for name in characters or []:
        if name in index.characters:
            results.append(index.characters[name])
    for hook_id in hooks or []:
        if hook_id in index.hooks:
            results.append(index.hooks[hook_id])
    for rule_id in rules or []:
        if rule_id in index.rules:
            results.append(index.rules[rule_id])
    return results


def extract_entities_from_plan(index: TruthIndex, plan_text: str) -> dict[str, list[str]]:
    """Match known index names against a chapter plan's text.

    This is the replacement for the broken regex approach: rather than
    matching arbitrary CJK substrings, we check which canonical entity names
    from the index actually appear in the plan. Character and rule names use
    the repo's canonical substring matcher (``shenbi.text.find_terms``); hook
    ids are extracted from prose by pattern (e.g. "H01") then filtered to known
    hooks. Returns matched ids grouped by category.
    """
    char_hits = {hit.term for hit in find_terms(plan_text, index.characters)}
    rule_hits = {hit.term for hit in find_terms(plan_text, index.rules)}
    hook_hits = [hid for hid in _HOOK_ID_RE.findall(plan_text) if hid in index.hooks]
    return {
        "characters": list(char_hits),
        "hooks": hook_hits,
        "rules": list(rule_hits),
    }
