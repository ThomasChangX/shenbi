"""Thread-safe truth file I/O (spec §3.2).

The concurrency model for skill dispatch is in-process ``ThreadPoolExecutor``
(threads). The correct synchronization primitive is therefore ``threading.Lock``
— NOT ``fcntl.flock``, which targets inter-process locking and leaves
``.lock`` files on disk. This module provides a path-keyed lock registry so
that writes to different truth files do not block each other, while
concurrent writes to the SAME file serialize.

A read-merge-write (e.g. upsert-markdown-row) is NOT atomic across threads
even though the final ``safe_write`` is atomic (temp + ``os.replace``): two
threads can each read the prior content and the second writer's merge loses
the first writer's row (spec §2.2 lost-update race). The per-path lock
serializes the whole read-merge-write transaction.

Wraps :func:`shenbi.safe_write.safe_write` with update-mode awareness:
- ``replace``: atomic overwrite (current snapshot files)
- ``upsert_yaml``: read existing YAML records, dedup by key_field, merge,
  re-serialize, write (structured data like hooks)
- ``upsert_markdown_row``: read existing markdown table/bullet rows, dedup by
  key column, merge new row, write (trend files read by escalation_bridge)

Supports both str-based (table-row format) and dict-based (bullet-row format)
data for ``replace`` and ``upsert_markdown_row`` modes.

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

# Module-level registry of per-path locks. Access to the registry dict itself
# is guarded by _REGISTRY_LOCK to avoid a race where two threads lazily create
# a lock for the same path and each stores its own (losing one). No lock files
# are written to disk — this is purely in-process.
_REGISTRY_LOCK = threading.Lock()
_PATH_LOCKS: dict[str, threading.Lock] = {}


def _path_lock(path: Path) -> threading.Lock:
    """Return the singleton lock for *path*, creating it lazily.

    Different paths get different locks (no cross-file blocking); the same
    path always returns the same lock object (serializes same-file writers).
    """
    key = str(path)
    with _REGISTRY_LOCK:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[key] = lock
        return lock


def write_truth_file(
    project_dir: Path,
    filename: str,
    new_data: str | dict[str, Any] | list[dict[str, Any]],
    *,
    mode: str = "replace",
    key_field: str | None = None,
) -> None:
    """Write to a truth file thread-safely, respecting update_mode.

    Args:
        project_dir: Root directory of the novel project.
        filename: Relative filename within ``truth/`` (e.g. ``resonance_trend.md``).
        new_data: Content to write. ``str`` for table-row format,
            ``dict[str, Any]`` for bullet-row format (key/value pairs),
            ``list[dict]`` for YAML records.
        mode: ``"replace"`` for atomic overwrite, ``"upsert_yaml"`` for
            structured-record key dedup, ``"upsert_markdown_row"`` for
            table/bullet-row key-column dedup.
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

    lock = _path_lock(path)
    with lock:
        if mode == "replace":
            if isinstance(new_data, dict):
                body = f"# {filename.removesuffix('.md')}\n\n- {new_data}\n"
                safe_write(path, body.encode("utf-8"))
            else:
                content = new_data if isinstance(new_data, str) else str(new_data)
                safe_write(path, content)
            log.info("truth_file_written", path=str(path), mode=mode)
            return

        if mode == "upsert_markdown_row":
            if isinstance(new_data, dict):
                _upsert_markdown_bullet(path, filename, new_data, key_field)
            elif isinstance(new_data, str):
                existing = path.read_text(encoding="utf-8") if path.exists() else ""
                merged = _upsert_markdown_table_row(existing, new_data, key_field or "chapter")
                safe_write(path, merged)
                log.info("truth_file_markdown_row_upserted", file=filename)
            else:
                raise ValueError("upsert_markdown_row requires str or dict new_data")
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


def _read_truth_rows(path: Path) -> list[dict[str, str]]:
    """Parse existing markdown rows into list of {column: value} dicts.

    Reads lines starting with ``- `` (bullet rows) or ``| ... |`` (table
    rows) and splits on ``:`` (bullet) or ``|`` (table). Tolerates an empty
    or heading-only file by returning [].
    """
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("- "):
            body = s[2:]
            if ":" in body:
                k, _, v = body.partition(":")
                rows.append({k.strip(): v.strip()})
        elif s.startswith("|") and s.endswith("|") and set(s) != {"|"}:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and cells[0] and cells[0] != "chapter":
                # treat first cell as key column for table form
                rows.append({cells[0]: " ".join(cells[1:])})
    return rows


def _upsert_markdown_bullet(
    path: Path,
    filename: str,
    new_data: dict[str, Any],
    key_field: str | None,
) -> None:
    """Upsert a dict row into a bullet-format markdown truth file.

    Reads existing bullet/table rows, deduplicates by *key_field* value,
    appends the new row, and writes back. Serialized by the per-path lock
    so concurrent upserts to the same file cannot lose updates.
    """
    if key_field is None:
        raise ValueError("upsert_markdown_row requires key_field")
    rows = _read_truth_rows(path)
    # Dedup: drop any existing row whose key matches the new row's key_field value.
    key_val = str(new_data.get(key_field, ""))
    rows = [r for r in rows if next(iter(r.keys())) != key_val]
    # Render non-key fields as "k=v" pairs.
    rest_fields = " ".join(f"{k}={v}" for k, v in new_data.items() if k != key_field)
    rows.append({key_val: rest_fields} if rest_fields else {key_val: ""})
    body = f"# {filename.removesuffix('.md')}\n\n"
    body += "\n".join(f"- {next(iter(r.items()))[0]}: {next(iter(r.items()))[1]}" for r in rows)
    body += "\n"
    safe_write(path, body.encode("utf-8"))
    log.info(
        "truth_file_written",
        path=str(path),
        mode="upsert_markdown_row",
        rows=len(rows),
    )


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
