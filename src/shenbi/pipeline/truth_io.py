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

from shenbi.exceptions import TruthFileParseError
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
                # T712: render readable "- k: v" bullets, not a Python repr —
                # the repr was unreadable prose and unparseable on re-read.
                bullets = "\n".join(f"- {k}: {v}" for k, v in new_data.items())
                body = f"# {filename.removesuffix('.md')}\n\n{bullets}\n"
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


_BULLET_ROW_RE = re.compile(r"^\s*-\s*(?P<key>.+?)\s*:(?P<rest>.*)$")


def _render_bullet_row(new_data: dict[str, Any], key_field: str) -> str:
    """Render a dict row as the ``- {key}: {k=v ...}`` bullet format."""
    key_val = str(new_data.get(key_field, ""))
    rest_fields = " ".join(f"{k}={v}" for k, v in new_data.items() if k != key_field)
    return f"- {key_val}: {rest_fields}" if rest_fields else f"- {key_val}:"


def _upsert_markdown_bullet(
    path: Path,
    filename: str,
    new_data: dict[str, Any],
    key_field: str | None,
) -> None:
    """Upsert a dict row into a bullet-format markdown truth file (T701 fix).

    SURGICAL line edit: the existing bullet line whose key equals the new
    row's ``key_field`` value is replaced in place (later duplicates of the
    same key are dropped); if no such line exists the new bullet is appended
    at the end of the file. Every other line — frontmatter, H1/H2 headings,
    prose, bullets for other keys — is preserved verbatim. The old
    implementation re-serialized the whole file as a bare bullet list,
    collapsing the file structure.
    """
    if key_field is None:
        raise ValueError("upsert_markdown_row requires key_field")
    key_val = str(new_data.get(key_field, ""))
    new_line = _render_bullet_row(new_data, key_field)

    if not path.exists():
        body = f"# {filename.removesuffix('.md')}\n\n{new_line}\n"
        safe_write(path, body.encode("utf-8"))
        log.info("truth_file_written", path=str(path), mode="upsert_markdown_row", rows=1)
        return

    if not key_val:
        # No natural key — preserve (append) and log rather than dedup-match
        # every other keyless row (symmetric with the T703 policy).
        log.warning("truth_bullet_upsert_empty_key", key_field=key_field)
        text = path.read_text(encoding="utf-8")
        merged = text.rstrip("\n") + "\n" + new_line + "\n"
        safe_write(path, merged.encode("utf-8"))
        return

    lines = path.read_text(encoding="utf-8").split("\n")
    replaced = False
    duplicates = 0
    kept: list[str] = []
    for line in lines:
        m = _BULLET_ROW_RE.match(line)
        if m and m.group("key").strip() == key_val:
            if not replaced:
                kept.append(new_line)  # first match: update in place
                replaced = True
            else:
                duplicates += 1  # historical duplicate rows are collapsed
        else:
            kept.append(line)
    if not replaced:
        # Append after the last non-empty line, keeping trailing blank lines.
        while kept and kept[-1] == "":
            kept.pop()
        kept.append(new_line)
        kept.append("")
    body = "\n".join(kept)
    if not body.endswith("\n"):
        body += "\n"
    safe_write(path, body.encode("utf-8"))
    if duplicates:
        log.warning("truth_bullet_upsert_duplicate_rows_dropped", key=key_val, count=duplicates)
    log.info(
        "truth_file_written",
        path=str(path),
        mode="upsert_markdown_row",
        replaced=replaced,
    )


def _split_table_cells(line: str) -> list[str] | None:
    """Split a markdown table row into stripped cells, or None if not a row.

    A table row starts and ends with ``|``. Cell boundaries are the pipes
    themselves, so a key is the FULL cell text — never the first whitespace
    token. This is the T702 fix: keys like ``第 1 章`` or ``Ch 1`` (containing
    spaces/CJK) must compare as whole cells, otherwise rows whose first
    *token* collides (``第`` == ``第``) wrongly dedup each other and whole
    families of rows get deleted.
    """
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")) or len(s) < 2:
        return None
    return [c.strip() for c in s[1:-1].split("|")]


def _norm_cell(cell: str) -> str:
    """Normalize a header cell for key-column matching (T713).

    ``Hook ID``, ``hook_id`` and ``hook-id`` all normalize to ``hookid`` so
    the contract ``key_field`` declaration can locate its column by header
    name.
    """
    return re.sub(r"[\s_-]+", "", cell.lower())


def _is_separator_row(cells: list[str]) -> bool:
    """True for a markdown table separator row (``| --- | :---: |``)."""
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def _key_column(existing: str, key_name: str) -> int:
    """Locate the key column index: header cell matching *key_name*, else 0.

    Only the FIRST table row counts as a header candidate, and only when it
    is followed by a separator row (markdown table convention). This stops a
    data row that merely *contains* the key word from redirecting the key
    column. If no header matches, the first column is the key (T713:
    ``key_field`` used to be decorative for str rows — now it positions the
    column).
    """
    lines = existing.split("\n")
    for idx, line in enumerate(lines):
        cells = _split_table_cells(line)
        if cells is None:
            continue
        next_cells = next(
            (_split_table_cells(l) for l in lines[idx + 1 :] if _split_table_cells(l) is not None),
            None,
        )
        if next_cells is not None and not _is_separator_row(next_cells):
            return 0  # first table line is a data row, not a header
        for i, cell in enumerate(cells):
            if cell and _norm_cell(cell) == _norm_cell(key_name):
                return i
        break  # only the first table line is a header candidate
    return 0


def _upsert_markdown_table_row(existing: str, new_row: str, key_name: str) -> str:
    """Dedup a markdown table row by whole-cell key-column value (T702/T713).

    The key is the FULL text of the key cell (first cell by default, or the
    column whose header matches *key_name*), never a whitespace token. Rows
    whose key cell equals the new row's key are replaced by the new row;
    everything else (frontmatter, headers, separator rows, prose, rows with
    a different key) is preserved verbatim. A non-table *new_row* — or one
    with no usable natural key — is appended without dedup so no data is
    silently dropped (data-preserving fallback, symmetric with T703).
    """
    new_cells = _split_table_cells(new_row)
    if new_cells is None:
        # Not a table row — no key to dedup on; append (data-preserving).
        log.warning("truth_table_upsert_non_table_row", key_name=key_name)
        return existing.rstrip() + "\n" + new_row
    key_col = _key_column(existing, key_name)
    if key_col >= len(new_cells):
        # New row lacks the key column — no natural key; append without dedup.
        log.warning("truth_table_upsert_row_missing_key_column", key_name=key_name, column=key_col)
        return existing.rstrip() + "\n" + new_row
    new_key = new_cells[key_col]
    if not new_key:
        # Empty key cell = no natural key; append without dedup rather than
        # letting all empty-key rows annihilate each other.
        log.warning("truth_table_upsert_empty_key", key_name=key_name)
        return existing.rstrip() + "\n" + new_row

    result_lines: list[str] = []
    for line in existing.split("\n"):
        if line.lstrip().startswith("|"):
            cells = _split_table_cells(line)
            if cells is None or _is_separator_row(cells):
                result_lines.append(line)  # separator rows are never data
                continue
            if key_col < len(cells) and cells[key_col] == new_key:
                continue  # replaced by the new row appended below
        result_lines.append(line)
    result_lines.append(new_row)
    return "\n".join(result_lines)


def _read_yaml_records(path: Path) -> list[dict[str, Any]]:
    """Read the YAML-fronted records list (e.g. frontmatter ``hooks:`` array).

    Fails LOUD on unreadable or malformed files (T706): the previous ``[]``
    fallback made the subsequent upsert treat the existing records as gone
    and collapse the whole file on rewrite. A missing file or a frontmatter
    block that simply carries no records key legitimately yields ``[]``.
    """
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return []
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise TruthFileParseError(
                "truth file frontmatter is unterminated (no closing ---)",
                path=str(path),
            )
        fm = yaml.safe_load(parts[1]) or {}
        if not isinstance(fm, dict):
            raise TruthFileParseError(
                "truth file frontmatter is not a YAML mapping",
                path=str(path),
                frontmatter_type=type(fm).__name__,
            )
        for key in ("hooks", "records", "items"):
            records = fm.get(key)
            if isinstance(records, list):
                return records
        return []
    except (yaml.YAMLError, OSError, ValueError) as exc:
        raise TruthFileParseError(
            "truth file could not be parsed during upsert read",
            path=str(path),
        ) from exc


def _upsert_by_key(
    existing: list[dict[str, Any]], new_records: list[dict[str, Any]], key_field: str
) -> list[dict[str, Any]]:
    """Merge records by key_field: new records replace existing ones with same key.

    Records WITHOUT the key field are preserved on BOTH sides (T703 fix: the
    new-record loop used to silently drop them, so an LLM record missing its
    id simply vanished while existing keyless records were kept — asymmetric).
    Keyless new records are kept and logged so the caller can notice; nothing
    is discarded.
    """

    def _add(rec: dict[str, Any]) -> None:
        if key_field in rec:
            k = str(rec[key_field])
            if k not in by_key:
                order.append(k)
            by_key[k] = rec
        else:
            marker = f"__nokey_{id(rec)}__"
            if marker not in by_key:
                order.append(marker)
            by_key[marker] = rec

    by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for rec in existing:
        _add(rec)
    for rec in new_records:
        if key_field not in rec:
            log.warning("truth_yaml_upsert_record_missing_key", key_field=key_field)
        _add(rec)
    return [by_key[k] for k in order if k in by_key]


def _serialize_yaml_records(records: list[dict[str, Any]], filename: str) -> str:
    """Serialize records back into the YAML-frontmatter + markdown-body format."""
    yaml_key = "hooks" if "hook" in filename else "records"
    fm = {yaml_key: records}
    front = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front}\n---\n\n"
