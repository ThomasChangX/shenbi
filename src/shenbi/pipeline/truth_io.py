"""Key-based upsert truth-file writer for pipeline integrity.

Wraps :func:`shenbi.safe_write.safe_write` with update-mode awareness:
- ``replace``: atomic overwrite (current snapshot files)
- ``upsert_yaml``: read existing YAML records, dedup by key_field, merge,
  re-serialize, write (structured data like hooks)
- ``upsert_markdown_row``: read existing markdown table rows, dedup by key
  column, merge new row, write (trend files read by escalation_bridge)

Idempotency is based on NATURAL KEYS (chapter number, hook id), NOT substring
matching. truth_index.py already abandoned substring matching as the broken
approach; LLM prose is never byte-identical across runs so substring matching
yields false negatives (whitespace diffs) and false positives (short substrings
dropped). The proven pattern is hook_planting.py:204-276 (read structured data,
dedup by stable key, merge, write back).

Thread safety: in-process threading.Lock keyed by path (not fcntl.flock).
"""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any

import yaml

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write

log = get_logger(__name__)

# Per-path locks for in-process concurrency. Keyed by resolved truth-file path.
_PATH_LOCKS: dict[str, threading.Lock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


def _get_path_lock(path: Path) -> threading.Lock:
    """Get or create the in-process lock for a given truth-file path."""
    key = str(path)
    with _PATH_LOCKS_GUARD:
        if key not in _PATH_LOCKS:
            _PATH_LOCKS[key] = threading.Lock()
        return _PATH_LOCKS[key]


def write_truth_file(
    project_dir: Path,
    filename: str,
    new_data: str | list[dict[str, Any]],  # str for markdown_table mode, list[dict] for yaml
    *,
    mode: str = "replace",  # replace | upsert_yaml | upsert_markdown_row
    key_field: str | None = None,
) -> None:
    """Write to a truth file, respecting update_mode.

    Args:
        project_dir: Root directory of the novel project.
        filename: Relative filename within ``truth/`` (e.g. ``resonance_trend.md``).
        new_data: Content to write. ``str`` for replace/upsert_markdown_row,
            ``list[dict]`` for upsert_yaml.
        mode: ``"replace"`` for atomic overwrite, ``"upsert_yaml"`` for
            structured-record key dedup, ``"upsert_markdown_row"`` for
            table-row key-column dedup.
        key_field: Natural key for dedup (e.g. ``"chapter"``, ``"id"``).
            Required for the upsert modes.

    Raises:
        ValueError: If mode is unrecognized or key_field missing for upsert.
    """
    if mode not in ("replace", "upsert_yaml", "upsert_markdown_row"):
        raise ValueError(
            f"Unknown mode '{mode}'; expected 'replace', 'upsert_yaml', or 'upsert_markdown_row'"
        )

    truth_dir = project_dir / "truth"
    truth_dir.mkdir(parents=True, exist_ok=True)
    path = truth_dir / filename

    lock = _get_path_lock(path)
    with lock:
        if mode == "replace":
            content = new_data if isinstance(new_data, str) else str(new_data)
            safe_write(path, content)
            log.debug("truth_file_replaced", file=filename)
            return

        if mode == "upsert_markdown_row":
            if not isinstance(new_data, str):
                raise ValueError("upsert_markdown_row requires str new_data")
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            merged = _upsert_markdown_table_row(existing, new_data, key_field or "chapter")
            safe_write(path, merged)
            log.info("truth_file_markdown_row_upserted", file=filename)
            return

        if mode == "upsert_yaml":
            if not isinstance(new_data, list):
                raise ValueError("upsert_yaml requires list[dict] new_data")
            if key_field is None:
                raise ValueError("upsert_yaml requires key_field")
            existing_records = _read_yaml_records(path)
            merged_records = _upsert_by_key(existing_records, new_data, key_field)
            yaml_content = _serialize_yaml_records(merged_records, filename)
            safe_write(path, yaml_content)
            log.info("truth_file_yaml_upserted", file=filename)


def _upsert_markdown_table_row(existing: str, new_row: str, key_name: str) -> str:
    """Dedup a markdown table row by key column value.

    Extracts the key from new_row's first ``|`` cell, removes any existing row
    with the same key, appends new_row. Preserves headers and non-table content
    (frontmatter, prose). This is key-based dedup, NOT substring matching.
    """
    # Extract key from new_row (first cell after |)
    new_key_match = re.match(r"\|\s*(\S+)", new_row)
    if not new_key_match:
        # Not a table row — just append to existing content
        return existing.rstrip() + "\n" + new_row
    new_key = new_key_match.group(1)

    lines = existing.split("\n")
    result_lines = []
    for line in lines:
        if line.startswith("|"):
            existing_key_match = re.match(r"\|\s*(\S+)", line)
            if existing_key_match and existing_key_match.group(1) == new_key:
                continue  # Skip the existing row with the same key — replaced below
        result_lines.append(line)
    result_lines.append(new_row)
    return "\n".join(result_lines)


def _read_yaml_records(path: Path) -> list[dict[str, Any]]:
    """Read the YAML-fronted records list (e.g. frontmatter ``hooks:`` array)."""
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1]) or {}
                for key in ("hooks", "records", "items"):
                    if isinstance(fm, dict):
                        records = fm.get(key)
                        if isinstance(records, list):
                            return records
        return []
    except (yaml.YAMLError, OSError, ValueError):
        log.warning("truth_yaml_read_failed", path=str(path))
        return []


def _upsert_by_key(
    existing: list[dict[str, Any]], new_records: list[dict[str, Any]], key_field: str
) -> list[dict[str, Any]]:
    """Merge records by key_field: new records replace existing ones with same key."""
    by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for rec in existing:
        if isinstance(rec, dict) and key_field in rec:  # pyright: ignore[reportUnnecessaryIsInstance]
            k = str(rec[key_field])
            if k not in by_key:
                order.append(k)
            by_key[k] = rec
        else:
            # Preserve records without the key field at the front
            order.insert(0, f"__nokey_{id(rec)}__")
            by_key[f"__nokey_{id(rec)}__"] = rec
    for rec in new_records:
        if isinstance(rec, dict) and key_field in rec:  # pyright: ignore[reportUnnecessaryIsInstance]
            k = str(rec[key_field])
            if k not in by_key:
                order.append(k)
            by_key[k] = rec
    return [by_key[k] for k in order if k in by_key]


def _serialize_yaml_records(records: list[dict[str, Any]], filename: str) -> str:
    """Serialize records back into the YAML-frontmatter + markdown-body format."""
    yaml_key = "hooks" if "hook" in filename else "records"
    fm = {yaml_key: records}
    front = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front}\n---\n\n"
