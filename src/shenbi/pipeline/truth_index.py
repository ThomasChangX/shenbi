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

# Hook ids embedded in prose. Supports BOTH the legacy canonical form
# (``H01``, ``MH02``) AND the production form used by shenbi-foreshadowing-*
# (``P0-4``, ``P0-9``). Spec §3.2b.
_HOOK_ID_RE = re.compile(r"(?:[HM]\d+|P\d*-\d+)")
# Rule headings — Chinese ordinals: ``## 规则一：能量守恒`` (production).
_RULE_HEADING_RE = re.compile(
    r"^##\s+规则\s*[：:.]?\s*([一二三四五六七八九十百\d]+)[:：]?\s*(.+)$",
    re.MULTILINE,
)
# Rule headings — legacy numeric IDs: ``## R1: ...`` / ``## 2. ...``.
_RULE_NUMERIC_RE = re.compile(r"^##\s+(R?\d+)[:.]?\s*(.+)$", re.MULTILINE)


def _parse_rules(rules_text: str) -> list[tuple[str, str]]:
    """Parse worldbuilding rule headings. Supports both formats:

    * Chinese ordinals: ``## 规则一: 能量守恒`` (production)
    * Numeric IDs:      ``## 1:`` / ``## R1:`` (legacy + tests)

    Returns a list of ``(rule_id, content)`` tuples. A line matching both
    patterns is yielded once (Chinese-ordinal takes precedence).
    """
    rules: list[tuple[str, str]] = []
    seen_spans: set[tuple[int, int]] = set()
    for rx in (_RULE_HEADING_RE, _RULE_NUMERIC_RE):
        for m in rx.finditer(rules_text):
            if (m.start(), m.end()) in seen_spans:
                continue
            seen_spans.add((m.start(), m.end()))
            rules.append((m.group(1), m.group(2).strip()))
    return rules


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


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file into (frontmatter_dict, body_text).

    Returns ``({}, text)`` when there is no frontmatter. Mirrors
    :func:`_parse_frontmatter` but also returns the body for body-source
    extraction (spec §3.2b).
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    data = yaml.safe_load(parts[1])
    fm = data if isinstance(data, dict) else {}
    return fm, parts[2]


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
    r"""Index hook records from truth/pending_hooks.md (dual-source).

    Source 1 — YAML frontmatter ``hooks`` list: authoritative, written by
    :mod:`shenbi.pipeline.hook_planting`. Carries the rich payload (state,
    last_reinforced, max_distance, content).

    Source 2 — markdown body: hook IDs (``P0-N`` / ``H\\d+`` / ``M\\d+``)
    appearing anywhere in the body. Catches entries written by the LLM
    track / state-settling path when the frontmatter list is absent or out
    of sync (the production state). Body entries get a minimal payload.
    """
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        return
    text = hooks_file.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)

    # Source 1: frontmatter `hooks` list (existing behaviour).
    raw_hooks = fm.get("hooks")
    if isinstance(raw_hooks, list):
        for hook in raw_hooks:
            if isinstance(hook, dict):
                hook_id = str(hook.get("id", ""))
                if not hook_id:
                    continue
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
                        "source": "frontmatter",
                    },
                )

    # Source 2: body hook IDs — only add IDs not already captured above.
    for hid_match in _HOOK_ID_RE.finditer(body):
        hook_id = hid_match.group(0)
        if hook_id in idx.hooks:
            continue
        idx.hooks[hook_id] = IndexEntry(
            category="hook",
            entity_id=hook_id,
            file="truth/pending_hooks.md",
            ref=f"truth/pending_hooks.md#{hook_id}",
            extra={"source": "body"},
        )


def _index_rules(project_dir: Path, idx: TruthIndex) -> None:
    """Index world rules declared as ``## <id>: <text>`` headings.

    Supports Chinese ordinals (``## 规则一:``) and numeric IDs (``## R1:``).
    """
    rules_file = project_dir / "world" / "rules.md"
    if not rules_file.exists():
        return
    text = rules_file.read_text(encoding="utf-8")
    for rule_id, content in _parse_rules(text):
        idx.rules[rule_id] = IndexEntry(
            category="rule",
            entity_id=rule_id,
            file="world/rules.md",
            ref=f"world/rules.md#{rule_id}",
            extra={"content": content},
        )


def build_index(project_dir: Path | str) -> TruthIndex:
    """Scan truth files under ``project_dir`` and build the entity index.

    Missing source directories are treated as empty rather than errors, so an
    early-stage project with only a characters/ dir still yields a valid index.

    After building, emits ``truth_index_empty_*`` warnings when a source file
    has content but its index bucket is empty — the silent-success-failure
    signal (spec §3.3).
    """
    project_dir = Path(project_dir)
    idx = TruthIndex()
    _index_characters(project_dir, idx)
    _index_hooks(project_dir, idx)
    _index_rules(project_dir, idx)

    # Silent-success-failure detection (spec §3.3).
    _warn_if_empty(project_dir / "truth" / "pending_hooks.md", idx.hooks, "hooks")
    _warn_if_empty(project_dir / "world" / "rules.md", idx.rules, "rules")

    log.info(
        "truth_index_built",
        characters=len(idx.characters),
        hooks=len(idx.hooks),
        rules=len(idx.rules),
    )
    return idx


def _warn_if_empty(source_file: Path, bucket: dict[str, Any], kind: str) -> None:
    """Log a warning if *source_file* has >100 bytes but *bucket* is empty."""
    if bucket:
        return
    if not source_file.exists():
        return
    try:
        size = source_file.stat().st_size
    except OSError:
        return
    if size > 100:
        log.warning(
            f"truth_index_empty_{kind}",
            file=str(source_file),
            size=size,
            msg=f"{source_file.name} exists with content but index extracted "
            f"zero {kind} — parser format mismatch likely",
        )


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
    hook_hits = {hid for hid in _HOOK_ID_RE.findall(plan_text) if hid in index.hooks}
    return {
        "characters": list(char_hits),
        "hooks": list(hook_hits),
        "rules": list(rule_hits),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``pipeline-truth-index``.

    Commands:
        rebuild --project-dir <dir>   Rebuild index, write truth-index.json
        query --project-dir <dir>     Build index, emit entity summary as JSON
    """
    import argparse

    from shenbi.cli_utils import emit_json
    from shenbi.logging import configure_logging
    from shenbi.safe_write import safe_write
    from shenbi.status import CommandStatus

    configure_logging()
    parser = argparse.ArgumentParser(prog="pipeline-truth-index")
    parser.add_argument("command", choices=["rebuild", "query"])
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args(argv)

    idx = build_index(args.project_dir)

    if args.command == "rebuild":
        out = Path(args.project_dir) / "truth-index.json"
        safe_write(out, idx.to_json())

    emit_json(
        {
            "status": CommandStatus.OK,
            "command": args.command,
            "characters": len(idx.characters),
            "hooks": len(idx.hooks),
            "rules": len(idx.rules),
        }
    )
    return 0
