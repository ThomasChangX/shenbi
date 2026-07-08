"""Shared review context cache — generates a JSON checklist once per chapter.

Injects the checklist into all review skill prompts so each review doesn't
independently compute the same context (genre config, fatigue words, voice
constraints, hook deliverables, etc.). Reduces review input from ~330K chars
    (11 x 30K) to ~4K chars (1 x generation + 11 x cache read).

Cache invalidation: compares mtime of source files (genre-config.json, chapter
file, truth/ files) against cache mtime. Graceful degradation: if any source
is missing, omit that section (don't crash).

Spec: docs/superpowers/specs/2026-07-07-pipeline-performance-redesign.md Phase 2.3
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.pipeline.context_curation import ENDING_PATTERNS
from shenbi.safe_write import safe_write

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ReviewChecklist:
    """Shared review context for a single chapter.

    All fields are serializable to JSON so the checklist can be cached to
    ``context/review-checklist-{chapter}.json`` and injected into prompts.
    """

    chapter: int
    transition_budget: int = 0
    ai_blacklist: list[str] = field(default_factory=list)
    fatigue_warnings: dict[str, Any] = field(default_factory=dict)
    voice_constraints: dict[str, Any] = field(default_factory=dict)
    pov_mode: str = ""
    hook_deliverables: list[dict[str, Any]] = field(default_factory=list)
    ending_constraints: list[str] = field(default_factory=list)
    world_rules_brief: str = ""
    sensitivity_flags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_review_checklist(
    project_dir: Path | str,
    chapter: int,
) -> ReviewChecklist:
    """Generate (or load cached) a review checklist for the given chapter.

    Uses mtime-based cache invalidation: compares the newest mtime of source
    files (genre-config.json, chapter file, truth/ files) against the cache
    file's mtime. If the cache is stale or missing, regenerates the checklist.

    Args:
        project_dir: Project root directory.
        chapter: Chapter number (1-indexed).

    Returns:
        A ``ReviewChecklist`` for the chapter.
    """
    project_dir = Path(project_dir)
    cache_dir = project_dir / "context"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"review-checklist-{chapter}.json"

    # Check if cache is fresh.
    if cache_path.exists():
        try:
            source_mtime = _get_max_source_mtime(project_dir, chapter)
            cache_mtime = cache_path.stat().st_mtime
            if source_mtime <= cache_mtime:
                # Cache is fresh — load and return.
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                return ReviewChecklist(**data)
            log.info(
                "review_checklist_cache_stale",
                chapter=chapter,
                source_mtime=source_mtime,
                cache_mtime=cache_mtime,
            )
        except Exception as exc:
            log.warning("review_checklist_cache_read_error", chapter=chapter, error=str(exc))

    # Generate fresh checklist.
    log.info("review_checklist_generating", chapter=chapter)
    checklist = _build_checklist(project_dir, chapter)

    # Cache to disk.
    data = {
        "chapter": checklist.chapter,
        "transition_budget": checklist.transition_budget,
        "ai_blacklist": checklist.ai_blacklist,
        "fatigue_warnings": checklist.fatigue_warnings,
        "voice_constraints": checklist.voice_constraints,
        "pov_mode": checklist.pov_mode,
        "hook_deliverables": checklist.hook_deliverables,
        "ending_constraints": checklist.ending_constraints,
        "world_rules_brief": checklist.world_rules_brief,
        "sensitivity_flags": checklist.sensitivity_flags,
    }
    safe_write(cache_path, json.dumps(data, ensure_ascii=False, indent=2))
    log.info("review_checklist_cached", chapter=chapter, path=str(cache_path))
    return checklist


def inject_checklist_into_prompt(prompt: str, checklist: ReviewChecklist) -> str:
    """Inject a JSON checklist block into a review skill prompt.

    The checklist is inserted as a ``审查参考数据`` block after the task
    description but before the input files section. If the prompt doesn't have
    an ``## Input Files`` marker, the checklist is appended at the end.

    Args:
        prompt: The original review skill user prompt.
        checklist: The ``ReviewChecklist`` to inject.

    Returns:
        The prompt with the checklist JSON block injected.
    """
    # Serialize checklist to compact JSON.
    checklist_json = json.dumps(
        {
            "chapter": checklist.chapter,
            "transition_budget": checklist.transition_budget,
            "ai_blacklist": checklist.ai_blacklist,
            "fatigue_warnings": checklist.fatigue_warnings,
            "voice_constraints": checklist.voice_constraints,
            "pov_mode": checklist.pov_mode,
            "hook_deliverables": checklist.hook_deliverables,
            "ending_constraints": checklist.ending_constraints,
            "world_rules_brief": checklist.world_rules_brief,
            "sensitivity_flags": checklist.sensitivity_flags,
        },
        ensure_ascii=False,
    )

    checklist_block = f"\n## 审查参考数据\n```json\n{checklist_json}\n```\n"

    # Insert before "## Input Files" if that marker exists.
    input_pos = prompt.find("## Input Files")
    if input_pos >= 0:
        return prompt[:input_pos] + checklist_block + "\n" + prompt[input_pos:]

    # Fallback: append at end.
    return prompt + checklist_block


# ---------------------------------------------------------------------------
# Checklist builder
# ---------------------------------------------------------------------------


def _build_checklist(project_dir: Path, chapter: int) -> ReviewChecklist:
    """Build a fresh ``ReviewChecklist`` from project source files.

    Each extractor handles missing files gracefully — no crashes.
    """
    genre_config = _load_genre_config(project_dir)

    return ReviewChecklist(
        chapter=chapter,
        transition_budget=max(5, _estimate_chapter_char_count(project_dir, chapter) // 1000),
        ai_blacklist=_extract_ai_blacklist(genre_config),
        fatigue_warnings=_extract_fatigue_warnings(genre_config),
        voice_constraints=_extract_voice_constraints(project_dir, chapter),
        pov_mode=genre_config.get("povMode", ""),
        hook_deliverables=_extract_hook_deliverables(project_dir, chapter),
        ending_constraints=_get_recent_ending_types(project_dir, chapter),
        world_rules_brief=_summarize_world_rules(project_dir),
        sensitivity_flags=genre_config.get("sensitivityFlags", []),
    )


# ---------------------------------------------------------------------------
# Source mtime computation (cache invalidation)
# ---------------------------------------------------------------------------


def _get_max_source_mtime(project_dir: Path, chapter: int) -> float:
    """Return the newest mtime among all source files that affect the checklist.

    Returns 0.0 if no source files exist (will always regenerate).
    """
    mtimes: list[float] = []

    # genre-config.json
    gc_path = project_dir / "genre-config.json"
    if gc_path.exists():
        mtimes.append(gc_path.stat().st_mtime)

    # Chapter file
    ch_path = project_dir / "chapters" / f"chapter-{chapter}.md"
    if ch_path.exists():
        mtimes.append(ch_path.stat().st_mtime)

    # truth/ directory files
    truth_dir = project_dir / "truth"
    if truth_dir.is_dir():
        for f in truth_dir.iterdir():
            if f.is_file():
                try:
                    mtimes.append(f.stat().st_mtime)
                except OSError:
                    # File may have been deleted between is_file() and stat();
                    # skip it gracefully.
                    pass

    return max(mtimes) if mtimes else 0.0


# ---------------------------------------------------------------------------
# Genre config loader
# ---------------------------------------------------------------------------


def _load_genre_config(project_dir: Path) -> dict[str, Any]:
    """Load genre-config.json, or return empty dict if missing."""
    gc_path = project_dir / "genre-config.json"
    if not gc_path.exists():
        log.info("genre_config_missing", path=str(gc_path))
        return {}
    try:
        result: Any = json.loads(gc_path.read_text(encoding="utf-8"))
        return result  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("genre_config_parse_error", path=str(gc_path), error=str(exc))
        return {}


# ---------------------------------------------------------------------------
# Helper extractors
# ---------------------------------------------------------------------------


def _extract_ai_blacklist(genre_config: dict[str, Any]) -> list[str]:
    """Extract flattened AI fatigue word blacklist from genre config.

    Collects all words from ``fatigueWords.禁用`` and ``fatigueWords.慎用``.
    Returns empty list when genre config is missing or has no fatigue words.
    """
    fw = genre_config.get("fatigueWords", {})
    if not isinstance(fw, dict):
        return []
    blacklist: list[str] = []
    blacklist.extend(fw.get("禁用", []))
    blacklist.extend(fw.get("慎用", []))
    return list(dict.fromkeys(blacklist))  # deduplicate, preserve order


def _extract_fatigue_warnings(genre_config: dict[str, Any]) -> dict[str, Any]:
    """Extract the full fatigue words structure from genre config.

    Returns the complete ``fatigueWords`` dict (with 禁用, 慎用, 替换建议)
    so reviewers can use the replacement suggestions. Returns empty dict
    when missing.
    """
    fw = genre_config.get("fatigueWords", {})
    return fw if isinstance(fw, dict) else {}


def _extract_voice_constraints(project_dir: Path, chapter: int) -> dict[str, str]:
    """Extract voice fingerprints for characters appearing in this chapter.

    Deterministic name-matching — simpler and more reliable than embedding search.
    """
    chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not chapter_path.exists():
        return {}

    chapter_text = chapter_path.read_text(encoding="utf-8")
    characters_dir = project_dir / "characters"
    if not characters_dir.exists():
        return {}

    voice_map: dict[str, str] = {}
    for profile_path in characters_dir.glob("**/*.md"):
        try:
            profile_text = profile_path.read_text(encoding="utf-8")
        except OSError:
            continue

        # Extract display name from frontmatter
        name_match = re.search(r"name\s*[:：]\s*(.+)", profile_text)
        display_name = name_match.group(1).strip() if name_match else profile_path.stem

        # Check if character appears in chapter
        if display_name not in chapter_text:
            continue

        # Extract voice fingerprint
        voice_match = re.search(r"voice_fingerprint\s*[:：]\s*(.+)", profile_text)
        if voice_match:
            voice_map[display_name] = voice_match.group(1).strip()

    return voice_map


def _extract_hook_deliverables(
    project_dir: Path,
    chapter: int,
) -> list[dict[str, Any]]:
    """Extract active hook deliverables from ``truth/pending_hooks.md``.

    Returns hooks that are in PLANTED state and may need advancement this
    chapter. Gracefully returns empty list when no hooks file exists.
    """
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        return []

    try:
        text = hooks_file.read_text(encoding="utf-8")
    except OSError:
        return []

    hooks: list[dict[str, Any]] = []
    if text.startswith("---"):
        import yaml

        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm: Any = yaml.safe_load(parts[1]) or {}
                raw_hooks: Any = fm.get("hooks", [])
                if isinstance(raw_hooks, list):
                    hooks = raw_hooks
            except Exception:
                log.warning("hook_deliverables_yaml_parse_error", path=str(hooks_file))
                return []

    # Filter to active hooks that need attention.
    active: list[dict[str, Any]] = []
    for h in hooks:
        state = h.get("state", "")
        last_reinforced = h.get("last_reinforced", h.get("plant_chapter", 0))
        silence = chapter - last_reinforced if last_reinforced else 999

        # Include PLANTED hooks that are approaching silence threshold, or
        # hooks that are explicitly marked for advancement.
        if state in ("PLANTED", "ACTIVE", "PENDING"):
            max_dist = h.get("max_distance", 20)
            urgency = "normal"
            if max_dist > 0 and silence > max_dist * 0.7:
                urgency = "URGENT"
            elif silence > 3:
                urgency = "attention"

            active.append(
                {
                    "id": h.get("id", "?"),
                    "content": h.get("content", h.get("description", "")),
                    "state": state,
                    "silence": silence,
                    "urgency": urgency,
                }
            )

    return active


def _get_recent_ending_types(project_dir: Path, chapter: int) -> list[str]:
    """Get ending types from the last 3 chapters' final paragraphs.

    Classifies endings using regex patterns (same as context_curation.py).
    Returns list of ending type strings (e.g., ['cliffhanger', 'hook',
    'resolution']). Gracefully handles missing chapters.
    """
    # Ending classification patterns (imported from context_curation.py).

    if chapter < 4:
        return []  # Not enough chapters for diversity check (need 3 prior chapters).

    ending_types: list[str] = []
    for offset in range(3, 0, -1):
        ch = chapter - offset
        ch_path = project_dir / "chapters" / f"chapter-{ch}.md"
        if not ch_path.exists():
            ending_types.append("missing")
            continue

        try:
            text = ch_path.read_text(encoding="utf-8")
        except OSError:
            ending_types.append("missing")
            continue

        # Get last non-empty paragraph.
        paragraphs = [
            p.strip()
            for p in text.split("\n\n")
            if p.strip() and not p.strip().startswith("<!--") and not p.strip().startswith("## ")
        ]
        last_p = paragraphs[-1] if paragraphs else ""

        etype = "other"
        for name, pattern in ENDING_PATTERNS.items():
            if re.search(pattern, last_p):
                etype = name
                break
        ending_types.append(etype)

    return ending_types


def _summarize_world_rules(project_dir: Path) -> str:
    """Return condensed world rules for review context."""
    rules_path = project_dir / "world" / "rules.md"
    if not rules_path.exists():
        return ""

    try:
        text = rules_path.read_text(encoding="utf-8")
    except OSError:
        return ""

    # Keep rules brief — reviews need constraints, not full lore
    return text[:2000] if len(text) > 2000 else text


def _estimate_chapter_char_count(project_dir: Path, chapter: int) -> int:
    """Estimate character count of the chapter file (Chinese-aware approximate).

    For Chinese text, each character is roughly one word. We count non-whitespace
    characters in the chapter file. Returns 0 when the file is missing.
    """
    ch_path = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not ch_path.exists():
        return 0

    try:
        text = ch_path.read_text(encoding="utf-8")
    except OSError:
        return 0

    # Strip YAML frontmatter.
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]

    # Count non-whitespace, non-punctuation Chinese-adjacent characters.
    # For simplicity, count all non-whitespace characters as approximate
    # word count (Chinese "字" ≈ characters).
    return len(re.sub(r"\s+", "", text))


__all__ = [
    "ReviewChecklist",
    "_build_checklist",
    "_estimate_chapter_char_count",
    "_extract_ai_blacklist",
    "_extract_fatigue_warnings",
    "_extract_hook_deliverables",
    "_extract_voice_constraints",
    "_get_max_source_mtime",
    "_get_recent_ending_types",
    "_load_genre_config",
    "_summarize_world_rules",
    "generate_review_checklist",
    "inject_checklist_into_prompt",
]
