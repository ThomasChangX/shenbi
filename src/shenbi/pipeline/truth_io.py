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
dropped). The proven pattern (formerly hook_planting.py) is: read structured data,
dedup by stable key, merge, write back).

Thread safety: in-process threading.Lock keyed by path (not fcntl.flock).
"""

from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from collections.abc import Generator
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
#: Bounded registry (spec #37 T607): long-running processes touching many
#: paths would otherwise grow the registry without limit. Entries carry a
#: refcount maintained under the registry guard — eviction only ever drops
#: refcount==0 entries (the locked()-snapshot race the spec rejected).
_PATH_LOCKS_MAX = 256
_PATH_LOCKS: dict[str, tuple[threading.Lock, int]] = {}


@contextmanager
def _path_lock(path: Path) -> Generator[None, None, None]:
    """Serialize same-path writers in-process AND cross-process (spec #37 T709).

    Layering: registry threading.Lock (in-process identity + refcount) then
    flock on ``<path>.lockfile`` (cross-process). Writers that honor this
    lockfile — including subprocess helpers that take it explicitly — are
    in the same mutual-exclusion domain (spec #37 T709). Subprocess writers
    that go through safe_write/locked_transact only (directory flock) are
    serialized with each other but NOT with per-path RMW sections; the
    docstring of each such site declares its lock domain. On
    flock-unavailable platforms this degrades to in-process-only.
    """
    import os
    import sys

    key = str(path)
    with _REGISTRY_LOCK:
        entry = _PATH_LOCKS.get(key)
        if entry is None:
            if len(_PATH_LOCKS) >= _PATH_LOCKS_MAX:
                for stale_key, (stale_lock, stale_rc) in list(_PATH_LOCKS.items()):
                    if stale_key != key and stale_rc == 0 and not stale_lock.locked():
                        del _PATH_LOCKS[stale_key]
                        if len(_PATH_LOCKS) < _PATH_LOCKS_MAX:
                            break
            entry = (threading.Lock(), 0)
            _PATH_LOCKS[key] = entry
        thread_lock, refcount = entry
        _PATH_LOCKS[key] = (thread_lock, refcount + 1)  # refcount acquired under guard
    lockfile = path.parent / (path.name + ".lockfile")
    fd: int | None = None
    try:
        with thread_lock:
            if sys.platform != "win32":
                try:
                    import fcntl

                    lockfile.parent.mkdir(parents=True, exist_ok=True)
                    fd = os.open(str(lockfile), os.O_CREAT | os.O_RDONLY)
                    fcntl.flock(fd, fcntl.LOCK_EX)  # blocking; held by close
                except (ImportError, OSError):
                    if fd is not None:
                        os.close(fd)
                    fd = None  # degrade to in-process only
            yield
    finally:
        if fd is not None:
            os.close(fd)
        with _REGISTRY_LOCK:
            entry = _PATH_LOCKS.get(key)
            if entry is not None:
                thread_lock2, rc = entry
                _PATH_LOCKS[key] = (thread_lock2, max(0, rc - 1))


@contextmanager
def truth_file_flock(path: Path) -> Generator[None, None, None]:
    """Cross-process-only flock on ``<path>.lockfile`` (no in-process registry).

    For short-lived subprocess helpers (e.g. compute_drift CLI) writing
    truth/** files: taking the SAME lockfile as _path_lock puts them in the
    same mutual-exclusion domain as in-process RMW sections (spec #37 T709).
    """
    import os
    import sys

    if sys.platform == "win32":  # pragma: no cover — POSIX-authoritative
        yield
        return
    try:
        import fcntl

        lockfile = path.parent / (path.name + ".lockfile")
        lockfile.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lockfile), os.O_CREAT | os.O_RDONLY)
    except (ImportError, OSError):
        yield  # degrade to no cross-process exclusion (POSIX-authoritative)
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


#: Public alias: sibling modules (dispatch_helper staging route, checkpoint
#: commit merge) reuse the SAME per-path lock registry — a second registry
#: would not mutually exclude with write_truth_file's locking (SDD #21 R3).
path_lock = _path_lock


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
        TruthFileParseError: In ``upsert_yaml`` mode, if the existing file's
            YAML frontmatter is corrupt/unreadable (fail-loud, T706) — the
            file is left untouched for repair instead of being collapsed.
    """
    if mode not in ("replace", "upsert_yaml", "upsert_markdown_row", "insert_markdown_row"):
        raise ValueError(
            f"Unknown mode '{mode}'; expected 'replace', 'upsert_yaml', 'upsert_markdown_row', "
            "or 'insert_markdown_row'"
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
                existing = ensure_table_header(
                    filename, path.read_text(encoding="utf-8") if path.exists() else ""
                )
                merged = upsert_markdown_row(existing, new_data, key_field or "chapter")
                safe_write(path, merged)
                log.info("truth_file_markdown_row_upserted", file=filename)
            else:
                raise ValueError("upsert_markdown_row requires str or dict new_data")
            return

        if mode == "insert_markdown_row":
            # T701 (SDD #21 R1): insert-only semantics — if the key already
            # exists, skip (a richer row from another writer stays untouched);
            # otherwise append. The existence check runs INSIDE the per-path
            # lock so concurrent writer threads cannot interleave check and
            # write (check-then-act race). Unlike upsert_markdown_row this
            # never replaces an existing row: the framework placeholder row
            # must not clobber a skill's rich row (dimension scores, role,
            # confidence) written moments earlier in the same chapter.
            if not isinstance(new_data, str):
                raise ValueError("insert_markdown_row requires str new_data")
            existing = ensure_table_header(
                filename, path.read_text(encoding="utf-8") if path.exists() else ""
            )
            if has_markdown_row(existing, new_data, key_field or "chapter"):
                log.info(
                    "truth_file_markdown_row_insert_skipped", file=filename, key_field=key_field
                )
                return
            merged = upsert_markdown_row(existing, new_data, key_field or "chapter")
            safe_write(path, merged)
            log.info("truth_file_markdown_row_inserted", file=filename)
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


#: Contract headers bootstrapped when a cumulative table file is CREATED by
#: the keyed upsert path. Probe2: the first resonance_trend row landed on an
#: empty base, producing a headerless file the longitudinal reader rejects
#: ("contract header row missing") — both writers (skill increment and the
#: framework's post-review persistence) route through the upsert, so the
#: create-path is the single bootstrap point.
_TABLE_HEADER_BOOTSTRAP: dict[str, str] = {
    "resonance_trend.md": (
        "| chapter | 类型 | 子项1 | 子项2 | 子项3 | 子项4 | overall | 档位 | human_overridden |"
    ),
}


def ensure_table_header(filename: str, content: str) -> str:
    """Prepend the file's contract header when *content* starts with a bare
    data row (file creation) and a header is registered for *filename*.
    """
    header = _TABLE_HEADER_BOOTSTRAP.get(filename)
    if not header:
        return content
    if not content.strip():
        return header + "\n|---|---|---|---|---|---|---|---|---|"
    first = next((line for line in content.split("\n") if line.strip()), "")
    if first.lstrip().startswith("|") and "chapter" not in first and "---" not in first:
        return header + "\n|---|---|---|---|---|---|---|---|---|\n" + content
    return content


_BULLET_ROW_RE = re.compile(r"^\s*-\s*(?P<key>.+?)\s*:(?P<rest>.*)$")

#: Hook-detail headings (``### MH-001 · …``) mark sections whose only
#: legitimate mutations are named-field bullet updates (probe3 P0: the only
#: merge primitive for headed sections was whole-section replacement, which
#: made the LLM responsible for verbatim base reproduction — 189 dropped
#: lines on attempt1, then a 49152-token whole-file retry on attempt2).
_HOOK_HEADING_RE = re.compile(r"^(#{2,6})\s+((?:MH|H|CP)-\d{3})\b")


def is_hook_heading(text: str) -> bool:
    """True when *text* is a hook-keyed heading (``### MH-001 · …``).

    Public seam over :data:`_HOOK_HEADING_RE` for cross-module consumers
    (dispatch_helper's increment splitter must keep hook sections
    independently routed — escalation #16).
    """
    return _HOOK_HEADING_RE.match(text.strip()) is not None


_COLON_BULLET_RE = re.compile(r"^-\s*([^:：\s][^:：]*)\s*[:：]")


def _hook_section_bullet_merge(existing: str, unit: str) -> str | None:
    """Patch a hook section's named fields in place; None when inapplicable.

    Applicable when the unit's first non-empty line is a hook heading and
    every other non-empty line is a ``- name: value`` colon bullet — a pure
    field update. Each bullet replaces the section's first same-name bullet
    in place; names absent from the live section insert after its last
    bullet. Stable lines are never re-emitted, so they cannot be dropped or
    rewritten by construction. Section location: exact heading line first,
    else same heading level + hook id (a paraphrased title after the id
    still targets the live block instead of appending a duplicate section).
    Accumulating fields (证据/notes) must restate their full history in the
    increment — the writer's contract duty, not the merge's.
    """
    unit_lines = unit.split("\n")
    h_idx = next((i for i, l in enumerate(unit_lines) if l.strip()), None)
    if h_idx is None:
        return None
    heading = unit_lines[h_idx].strip()
    hm = _HOOK_HEADING_RE.match(heading)
    if not hm:
        return None
    level = len(hm.group(1))
    hook_id = hm.group(2)
    fields: list[tuple[str, str]] = []
    for line in unit_lines[h_idx + 1 :]:
        s = line.strip()
        if not s:
            continue
        fm = _COLON_BULLET_RE.match(s)
        if not fm:
            return None  # free-form content = section rewrite — legacy replace
        fields.append((fm.group(1).strip(), line.rstrip()))
    if not fields:
        return None

    lines = existing.split("\n")
    target: int | None = None
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("#"):
            continue
        if s == heading:
            target = i
            break
        tm = _HOOK_HEADING_RE.match(s)
        if tm and len(tm.group(1)) == level and tm.group(2) == hook_id:
            target = i
            break
    if target is None:
        return None  # unknown hook — caller appends the whole unit

    end = len(lines)
    for j in range(target + 1, len(lines)):
        s = lines[j].lstrip()
        if s.startswith("#"):
            lvl = len(s) - len(s.lstrip("#"))
            if lvl <= level:
                end = j
                break

    used = [False] * len(fields)
    for fi, (name, newline) in enumerate(fields):
        for j in range(target + 1, end):
            s = lines[j].strip()
            if not s.startswith("-"):
                continue
            fm = _COLON_BULLET_RE.match(s)
            if fm and fm.group(1).strip() == name:
                lines[j] = newline
                used[fi] = True
                break
    bullet_positions = [j for j in range(target + 1, end) if lines[j].strip().startswith("-")]
    insert_at = bullet_positions[-1] + 1 if bullet_positions else target + 1
    for fi, (name, newline) in enumerate(fields):
        if not used[fi]:
            lines.insert(insert_at, newline)
            insert_at += 1
    out = "\n".join(lines)
    if not out.endswith("\n"):
        out += "\n"
    return out


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


def patch_markdown_table_cell(
    path: Path, key: str, key_field: str, cell_index: int, value: str
) -> bool:
    """Patch a single cell of an existing markdown table row (spec #33 T1b).

    Column location is positional (``cell_index``), not header-based: header
    placement is uncontrolled for append_dedup writers (spec #33 v8 ruling).
    ``key_field`` is logging-only observability (position, not header, rules).
    Rows shorter than ``cell_index + 1`` are padded with ``-`` placeholders.
    Key matching is exact whole-cell (consistent with upsert_markdown_row).
    Returns False when the file or the keyed row does not exist; header and
    separator rows are never patched; negative cell_index is rejected.
    Thread-safe via the per-path lock registry (same rationale as
    ``insert_markdown_row``). Preserves the file's CRLF/LF convention.
    """
    lock = _path_lock(path)
    with lock:
        if not path.exists():
            return False
        # Bytes + decode: read_text() would translate CRLF to LF (universal
        # newlines), silently rewriting the whole file's line endings.
        raw = path.read_bytes().decode("utf-8")
        had_crlf = "\r\n" in raw
        lines = raw.splitlines()
        for idx, line in enumerate(lines):
            cells = split_table_cells(line)
            if cells is None:
                continue
            if _is_separator_row(cells):
                continue
            # Header row: the immediately following line is a separator.
            if idx + 1 < len(lines):
                nxt = split_table_cells(lines[idx + 1])
                if nxt is not None and _is_separator_row(nxt):
                    continue
            # Exact whole-cell key match (consistent with upsert_markdown_row);
            # _norm_cell would collide "5-2" with "52".
            if cells[0] != key:
                continue
            while len(cells) <= cell_index:
                cells.append("-")
            if cell_index < 0:
                log.warning("truth_cell_patch_bad_index", cell_index=cell_index)
                return False
            cells[cell_index] = value
            lines[idx] = "| " + " | ".join(c.strip() for c in cells) + " |"
            sep = "\r\n" if had_crlf else "\n"
            safe_write(path, (sep.join(lines) + sep).encode("utf-8"))
            log.info(
                "truth_cell_patched",
                path=str(path),
                key=key,
                key_field=key_field,
                cell_index=cell_index,
            )
            return True
        return False


def split_table_cells(line: str) -> list[str] | None:
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


def _norm_key(cell: str) -> str:
    """Key-cell IDENTITY for row dedup: whitespace-insensitive only.

    Fixcheck ch3: two settle attempts emitted the same chapter key with
    different spacing (``第 3 章`` vs ``第3章``); exact-string comparison
    treated them as distinct keys and both rows landed in the same table.
    Header-COLUMN matching keeps the broader :func:`_norm_cell` form
    (case/dash-insensitive); row-key identity stays conservative here.
    """
    return re.sub(r"\s+", "", cell)


def _is_separator_row(cells: list[str]) -> bool:
    """True for a markdown table separator row (``| --- | :---: |``)."""
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def _key_columns(existing: str, key_spec: str) -> list[int]:
    """Locate the key column indices for a single OR composite key spec.

    Single-name specs keep the historical single-column semantics (T713:
    header-cell match positions the key column; first column otherwise; only
    the first table line is a header candidate, and only when followed by a
    separator row — a data row that merely *contains* the key word must not
    redirect the key column).

    Probe2 settle capacity fix: the character_matrix 交互表 keys rows on the
    (角色A, 角色B) TUPLE — a single-column key on 角色A would collapse every
    row sharing the same first character. A comma-separated *key_spec*
    (``"角色A,角色B"``) selects all named columns; the row key is the cell
    tuple. Rule: only the FIRST table line is a header candidate (same
    convention as the historical single-name lookup); when EVERY named column matches the
    header, those positions are the key; otherwise the spec degrades to the
    first column — so mixed-table increments (e.g. the 信息边界表 keyed on
    角色对) keep single-column semantics.
    """
    names = [n for n in (part.strip() for part in key_spec.split(",")) if n]
    lines = existing.split("\n")
    for idx, line in enumerate(lines):
        cells = split_table_cells(line)
        if cells is None:
            continue
        next_cells = next(
            (split_table_cells(l) for l in lines[idx + 1 :] if split_table_cells(l) is not None),
            None,
        )
        if next_cells is not None and not _is_separator_row(next_cells):
            return [0]  # first table line is a data row, not a header
        positions: list[int] = []
        for name in names:
            for i, cell in enumerate(cells):
                if cell and _norm_cell(cell) == _norm_cell(name):
                    positions.append(i)
                    break
            else:
                return [0]  # a named column is absent — degrade to first column
        return positions if positions else [0]
    return [0]


def _structural_table_lines(lines: list[str]) -> list[bool]:
    """Flag structural table lines: separator rows and header rows.

    A header row is a pipe row whose NEXT pipe row is a separator (markdown
    table convention). Headers and separators define table structure — they
    must never be removed or matched as data by the upsert (probe escalation
    #6: an increment re-emitting a ``| Hook ID | ... |`` header deleted the
    live 8-column registry header, leaving the table unparseable).
    """
    flags = [False] * len(lines)
    pipe_indices = [i for i, line in enumerate(lines) if split_table_cells(line) is not None]
    for pos, i in enumerate(pipe_indices):
        cells = split_table_cells(lines[i])
        if cells is not None and _is_separator_row(cells):
            flags[i] = True
            continue
        nxt = pipe_indices[pos + 1] if pos + 1 < len(pipe_indices) else None
        if nxt is not None:
            next_cells = split_table_cells(lines[nxt])
            if next_cells is not None and _is_separator_row(next_cells):
                flags[i] = True
    return flags


def _key_table_tail(lines: list[str], key_name: str) -> int | None:
    """Line index just past the last row of the table whose header carries
    *key_name* — the in-table insertion point for a new-key row.

    None when no table's header matches (callers fall back to EOF append).
    """
    structural = _structural_table_lines(lines)
    for i, line in enumerate(lines):
        if not structural[i] or _is_separator_row(split_table_cells(line) or []):
            continue
        cells = split_table_cells(line) or []
        if any(c and _norm_cell(c) == _norm_cell(key_name) for c in cells):
            tail = i
            for j in range(i + 1, len(lines)):
                if split_table_cells(lines[j]) is not None:
                    tail = j
                else:
                    break
            return tail + 1
    return None


def _replace_section(existing: str, section: str) -> str | None:
    """Replace the same-heading section in *existing* with *section*.

    The section span runs from the identical heading line to the next
    heading of the same or higher level (or EOF). Returns None when no
    matching heading exists (caller falls back to append).
    """
    lines = existing.split("\n")
    heading = next((l for l in section.split("\n") if l.strip()), "")
    if not heading:
        return None
    level = len(heading) - len(heading.lstrip("#"))
    for i, line in enumerate(lines):
        if line.strip() != heading:
            continue
        end = len(lines)
        for j in range(i + 1, len(lines)):
            stripped = lines[j].lstrip()
            if stripped.startswith("#"):
                lvl = len(stripped) - len(stripped.lstrip("#"))
                if lvl <= level:
                    end = j
                    break
        # keep surrounding blank-line rhythm: replace the span, ensure a
        # single blank separator before the next heading
        new_lines = lines[:i] + section.split("\n") + lines[end:]
        out = "\n".join(new_lines)
        return re.sub(r"\n{3,}", "\n\n", out)
    return None


def upsert_markdown_row(existing: str, new_row: str, key_name: str) -> str:
    """Dedup a markdown table row by whole-cell key-column value (T702/T713).

    The key is the FULL text of the key cell (first cell by default, or the
    column whose header matches *key_name*), never a whitespace token. Rows
    whose key cell equals the new row's key are replaced by the new row
    IN PLACE — the pre-probe-#6 primitive removed the matched row and
    appended the replacement at EOF, so every update relocated its row out
    of the table and dangled it after trailing prose. Everything else
    (frontmatter, headers, separator rows, prose, rows with a different key)
    is preserved verbatim; header-shaped increment rows are skipped (a
    re-emitted ``| Hook ID | ... |`` header used to delete the live header).
    A non-table *new_row* — or one with no usable natural key — is appended
    without dedup so no data is silently dropped (data-preserving fallback,
    symmetric with T703).
    """
    new_cells = split_table_cells(new_row)
    if new_cells is None:
        # Not a table row — no key to dedup on. HEADED sections use REPLACE
        # semantics (probe, twice bitten: the first block-dedup version
        # skipped re-emitted same-heading sections whole, so approved
        # section updates could never reach live through the commit merge —
        # an empty shell that landed first blocked every later filled
        # version). Heading-less prose keeps the append/skip fallback.
        first_line = next((l for l in new_row.split("\n") if l.strip()), "")
        if not first_line:
            return existing
        if first_line.lstrip().startswith("#"):
            merged = _hook_section_bullet_merge(existing, new_row)
            if merged is not None:
                log.info("truth_hook_section_fields_patched", key_name=key_name)
                return merged
            replaced_section = _replace_section(existing, new_row)
            if replaced_section is not None:
                return replaced_section
            return existing.rstrip() + "\n" + new_row
        if any(l.strip() == first_line for l in existing.split("\n")):
            log.warning("truth_block_upsert_duplicate_skipped", key_name=key_name)
            return existing
        log.warning("truth_table_upsert_non_table_row", key_name=key_name)
        return existing.rstrip() + "\n" + new_row
    key_cols = _key_columns(existing, key_name)
    key_col = key_cols[0]
    if any(c >= len(new_cells) for c in key_cols):
        # New row lacks a key column — no natural key; append without dedup.
        log.warning("truth_table_upsert_row_missing_key_column", key_name=key_name, column=key_col)
        return existing.rstrip() + "\n" + new_row
    new_key_cells = [new_cells[c] for c in key_cols]
    if not any(cell.strip() for cell in new_key_cells):
        # Empty key cell(s) = no natural key; append without dedup rather
        # than letting all empty-key rows annihilate each other.
        log.warning("truth_table_upsert_empty_key", key_name=key_name)
        return existing.rstrip() + "\n" + new_row
    header_cells = (
        [key_name.split(",", maxsplit=1)[0].strip()]
        if len(key_cols) == 1
        else [n.strip() for n in key_name.split(",")]
    )
    if len(header_cells) == len(new_key_cells) and all(
        _norm_cell(nc) == _norm_cell(hc)
        for nc, hc in zip(new_key_cells, header_cells, strict=False)
    ):
        # The increment re-emitted this table's HEADER row. Headers are
        # structural: upserting one would delete the live header (key match)
        # and append a ragged copy at the tail (probe escalation #6).
        log.warning("truth_table_upsert_header_row_skipped", key_name=key_name)
        return existing

    lines = existing.split("\n")
    structural = _structural_table_lines(lines)
    result_lines: list[str] = []
    replaced = False
    matched = False
    for i, line in enumerate(lines):
        if not structural[i] and line.lstrip().startswith("|"):
            cells = split_table_cells(line)
            if (
                cells is not None
                and all(c < len(cells) for c in key_cols)
                and _norm_key("×".join(cells[c] for c in key_cols))
                == _norm_key("×".join(new_key_cells))
            ):
                matched = True
                # Shape guard (probe escalation #14): replace only when the
                # new row matches the old width or strictly ENRICHES it
                # (same cells + appended ones). A different-shape rewrite
                # (8-col registry row replaced by a 10-col status row)
                # corrupts the table — keep the old row; the update also
                # lives in the increment's detail sections.
                same_shape = len(cells) == len(new_cells)
                enrichment = len(new_cells) > len(cells) and new_cells[: len(cells)] == cells
                if not replaced and (same_shape or enrichment):
                    result_lines.append(new_row)  # replace at the row's position
                    replaced = True
                elif not replaced:
                    log.warning(
                        "truth_table_upsert_row_shape_mismatch_skipped",
                        key_name=key_name,
                        old_cols=len(cells),
                        new_cols=len(new_cells),
                    )
                    result_lines.append(line)
                # duplicate rows with the same key are dropped
                continue
        result_lines.append(line)
    if not matched:
        insert_at = _key_table_tail(lines, key_name)
        if insert_at is not None:
            result_lines.insert(insert_at, new_row)
        else:
            result_lines.append(new_row)  # no keyed table — EOF fallback
    return "\n".join(result_lines)


def has_markdown_row(existing: str, new_row: str, key_name: str) -> bool:
    """True if a table row with the new row's key already exists (SDD #21 R1).

    Uses the same whole-cell key-column semantics as
    :func:`upsert_markdown_row`. Rows that are not tables, lack the key
    column, or have an empty key count as "not present" (insert proceeds —
    symmetric with the data-preserving fallback in upsert).
    """
    new_cells = split_table_cells(new_row)
    if new_cells is None:
        return False
    key_cols = _key_columns(existing, key_name)
    if any(c >= len(new_cells) for c in key_cols):
        return False
    new_key = "×".join(new_cells[c] for c in key_cols)
    if not new_key.strip("× "):
        return False
    for line in existing.split("\n"):
        cells = split_table_cells(line)
        if cells is None or _is_separator_row(cells):
            continue
        if all(c < len(cells) for c in key_cols) and _norm_key(
            "×".join(cells[c] for c in key_cols)
        ) == _norm_key(new_key):
            return True
    return False


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
        # Frontmatter gate: the FIRST LINE must be exactly ``---``. A bare
        # ``startswith("---")`` prefix test also matched ``----`` thematic
        # breaks, misparsing frontmatter-less bodies as frontmatter and
        # raising TruthFileParseError on them (final review T4 M2).
        first_line = text.split("\n", 1)[0].rstrip("\r \t")
        if first_line != "---":
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


#: Public alias for the separator-row predicate (used by the checkpoint-side
#: keyed merge; single source, no duplicate regex).
is_separator_row = _is_separator_row
