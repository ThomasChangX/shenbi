"""Deterministic hook planting — replaces LLM-based foreshadowing-plant.

Parses chapter plan section 7 for hook plant operations, generates hook YAML
metadata from templates, and appends to ``truth/pending_hooks.md`` — all
without an LLM call. Replaces 1 LLM call per chapter. Speed: ~5min → ~50ms.

Spec: docs/superpowers/specs/2026-07-07-pipeline-performance-redesign.md Phase 2.2
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def plant_hooks_from_plan(project_dir: Path | str, chapter: int) -> int:
    """Parse chapter plan section 7, extract plant operations, generate
    hook YAML, and append to ``truth/pending_hooks.md``.

    Args:
        project_dir: Project root directory.
        chapter: Chapter number (1-indexed).

    Returns:
        Number of hooks planted.
    """
    project_dir = Path(project_dir)
    plan_path = project_dir / "plans" / f"chapter-{chapter}-plan.md"

    if not plan_path.exists():
        log.info("hook_plant_no_plan", chapter=chapter, path=str(plan_path))
        return 0

    plan = plan_path.read_text(encoding="utf-8")
    section7 = _extract_section_7(plan)

    if not section7:
        log.info("hook_plant_no_section_7", chapter=chapter)
        return 0

    entries = _parse_hook_entries(section7)
    if not entries:
        log.info("hook_plant_no_plant_entries", chapter=chapter)
        return 0

    planted = _append_to_pending_hooks(project_dir, entries, chapter)
    log.info("hooks_planted_deterministically", chapter=chapter, count=planted)
    return planted


# ---------------------------------------------------------------------------
# Section 7 extraction
# ---------------------------------------------------------------------------


def _extract_section_7(plan_text: str) -> str:
    """Extract section 7 content from a chapter plan markdown string.

    Looks for ``## 7.`` header and captures everything until ``## 8.``
    or end-of-file. Returns empty string when section 7 is absent.
    """
    # Find the start of section 7.
    start_m = re.search(r"^## 7\.", plan_text, re.MULTILINE)
    if not start_m:
        return ""

    start = start_m.start()

    # Find the start of section 8 (if any) after section 7.
    end_m = re.search(r"^## 8\.", plan_text[start + 1 :], re.MULTILINE)
    if end_m:
        end = start + 1 + end_m.start()
        return plan_text[start:end]

    # No section 8 — capture to end of file.
    return plan_text[start:]


# ---------------------------------------------------------------------------
# Hook entry parsing
# ---------------------------------------------------------------------------


def _parse_hook_entries(section7: str) -> list[dict[str, Any]]:
    """Parse hook operation entries from section 7 markdown.

    Supports two table formats:

    1. **Spec format** (5+ columns):
       ``| hook_id | description | operation | type | category |``

    2. **Legacy plan format** (4 columns):
       ``| ID | 操作 | 推进方式 | 沉默章数 |``
       where "操作" of ``open`` is treated as ``plant``.

    Non-plant entries (advance, defer, resolve, etc.) are silently skipped.
    Header rows and separator rows are ignored.

    Returns:
        List of parsed hook entry dicts with keys: hook_id, description,
        operation, type, category. Only ``plant`` operations are returned.
    """
    entries: list[dict[str, Any]] = []
    if not section7.strip():
        return entries

    lines = section7.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if "|" not in stripped:
            continue

        cells = [c.strip() for c in stripped.split("|") if c.strip()]
        if not cells:
            continue

        # Skip table header rows and separator rows.
        first_cell_lower = cells[0].lower()
        if first_cell_lower in ("id", "hook id", "hook-id", "hook_id"):
            continue
        if all(c.replace("-", "").replace(":", "").replace(" ", "") == "" for c in cells):
            continue

        # Need at least: hook_id + description + operation
        if len(cells) < 3:
            continue

        # Skip rows that don't look like hook entries (first cell should
        # contain "hook" or start with "MH-" or "H-").
        if "hook" not in first_cell_lower and not re.match(r"^(MH|H)-", cells[0]):
            continue

        raw_op = cells[2].lower() if len(cells) > 2 else ""

        # Only process "plant" operations.
        # "open" is the legacy plan equivalent of "plant".
        if raw_op not in ("plant", "open"):
            continue

        entry: dict[str, Any] = {
            "hook_id": cells[0],
            "description": cells[1] if len(cells) > 1 else "",
            "operation": "plant",  # normalize
            "type": cells[3] if len(cells) > 3 and cells[3] else None,
            "category": cells[4] if len(cells) > 4 and cells[4] else None,
        }
        entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
# Pending hooks persistence
# ---------------------------------------------------------------------------


def _generate_hook_yaml(entry: dict[str, Any], chapter: int) -> dict[str, Any]:
    """Generate complete hook YAML metadata from a plan entry + template defaults.

    Args:
        entry: Parsed entry from ``_parse_hook_entries`` with keys:
            hook_id, description, type, category.
        chapter: Current chapter number.

    Returns:
        A dict suitable for serialization into the pending_hooks YAML frontmatter.
    """
    hook_type = entry.get("type") or "GENUINE"
    dimension = entry.get("category") or "CHARACTER"

    return {
        "id": entry["hook_id"],
        "content": entry.get("description", ""),
        "state": "PLANTED",
        "operation": "plant",
        "type": hook_type,
        "dimension": dimension,
        "subtlety": 0.6,
        "plant_chapter": chapter,
        "cultivation_interval": 5,
        "last_reinforced": chapter,
        "max_distance": 20,
        "escalation_curve": "RISING",
        "depends_on": [],
        "core_hook": False,
        "promoted": False,
    }


def _append_to_pending_hooks(
    project_dir: Path,
    entries: list[dict[str, Any]],
    chapter: int,
) -> int:
    """Append hook YAML entries to ``truth/pending_hooks.md``.

    Reads existing hooks from YAML frontmatter, deduplicates by hook ID,
    appends new entries, and writes back atomically via ``safe_write``.

    Args:
        project_dir: Project root directory.
        entries: Parsed hook entries to plant.
        chapter: Current chapter number.

    Returns:
        Number of new hooks actually planted (deduplicated count).
    """
    hooks_file = project_dir / "truth" / "pending_hooks.md"

    # Read existing hooks.
    existing_hooks: list[dict[str, Any]] = []
    existing_ids: set[str] = set()

    if hooks_file.exists():
        text = hooks_file.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                    hooks = fm.get("hooks", [])
                    if isinstance(hooks, list):
                        existing_hooks = hooks
                        existing_ids = {
                            h["id"]
                            for h in existing_hooks
                            if isinstance(h, dict) and "id" in h  # pyright: ignore[reportUnnecessaryIsInstance]
                        }
                except Exception:
                    log.warning("hook_plant_yaml_parse_error", path=str(hooks_file))

    # Collect new hooks (skip duplicates).
    new_hooks: list[dict[str, Any]] = []
    for entry in entries:
        hook_id = entry["hook_id"]
        if hook_id in existing_ids:
            log.info("hook_plant_duplicate_skipped", hook_id=hook_id, chapter=chapter)
            continue
        hook = _generate_hook_yaml(entry, chapter)
        new_hooks.append(hook)
        existing_ids.add(hook_id)

    if not new_hooks:
        return 0

    # Build new YAML frontmatter.
    all_hooks = existing_hooks + new_hooks
    frontmatter: dict[str, Any] = {"hooks": all_hooks}
    new_content = (
        "---\n"
        + yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False)
        + "---\n"
    )

    safe_write(hooks_file, new_content)
    log.info(
        "hook_plant_appended_to_pending_hooks",
        chapter=chapter,
        new_count=len(new_hooks),
        total_count=len(all_hooks),
    )
    return len(new_hooks)


__all__ = [
    "_append_to_pending_hooks",
    "_extract_section_7",
    "_generate_hook_yaml",
    "_parse_hook_entries",
    "plant_hooks_from_plan",
]
