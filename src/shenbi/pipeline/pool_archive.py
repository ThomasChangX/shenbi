"""GO② rolling archival for the pending_hooks evidence pool.

The pool's detail sections accumulate per-reinforcement evidence history
without bound (phase3 ch118: 94KB live file, MH01 alone thousands of chars
of 证据/notes). ``archive_pool`` moves TERMINAL hooks (``lifecycle_state:
RESOLVED`` with ``resolve_chapter`` at/below the caller's window) verbatim
to ``truth/pending_hooks_archive.md`` and leaves a three-bullet tombstone
plus drops the overview row — deterministic code, not an LLM discipline (the
drift-guidance ``audit_drift_archive`` window is the design precedent).

Call sites: the volume-boundary chain (driver protocol / boundary steps) —
``just pool-archive <dir> <resolved-through>``. The keep-window choice
belongs to the caller; a volume's worth of recency (``boundary - 24``) is
the recommended default.

Usage::

    python -m shenbi.pipeline.pool_archive <project_dir> --resolved-through 94
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from shenbi.pipeline.truth_io import (
    _HOOK_HEADING_BLOCK_RE,  # pyright: ignore[reportPrivateUsage]
    canon_hook_id,
    path_lock,
)
from shenbi.safe_write import safe_write

_ARCHIVE_REL = "truth/pending_hooks_archive.md"
_POOL_REL = "truth/pending_hooks.md"
_TOMBSTONE_FIELDS = (
    "- lifecycle_state: {state}\n",
    "- resolve_chapter: {rc}\n",
    "- archived_to: " + _ARCHIVE_REL + "\n",
)
_ARCHIVE_FRONTMATTER = (
    "---\ntype: truth\ncategory: state\nstatus: active\n"
    'note: "由 shenbi.pipeline.pool_archive 滚动归档（GO②）；整段自 truth/pending_hooks.md '
    '原样移入，不重述、不改写。"\n---\n\n# 伏笔池 · 已归档详情\n\n'
)
_ARCHIVED_NOTE_RE = re.compile(r"^> 已归档.*$", re.MULTILINE)


def _section_fields(section: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in section.splitlines():
        m = re.match(
            r"^-\s+(lifecycle_state|resolve_chapter|archived_to)\s*[:：]\s*(.+)$", line.strip()
        )
        if m:
            fields.setdefault(m.group(1), m.group(2).strip())
    return fields


def archive_pool(project_dir: Path, resolved_through: int) -> list[str]:
    """Move terminal hook sections past the window into the archive file.

    Returns the archived hook ids (canonical, in file order). Idempotent:
    tombstoned hooks (``archived_to`` bullet present) and non-terminal hooks
    are skipped, so a repeated call with the same window is a no-op. Raises
    ValueError when the live pool lacks the expected 总览/详情 shape — the
    archival must never guess at an unexpected layout (degrade loudly).
    """
    pool_path = project_dir / _POOL_REL
    archive_path = project_dir / _ARCHIVE_REL
    live = pool_path.read_text(encoding="utf-8")

    if not re.search(r"^##\s*总览\s*$", live, re.MULTILINE) or not re.search(
        r"^##\s*详情\s*$", live, re.MULTILINE
    ):
        raise ValueError(
            "truth/pending_hooks.md 缺少 总览/详情 结构——拒绝在异常布局上归档（degrade loudly）。"
        )

    # Section spans in the details body (heading → next same-or-higher heading).
    sections: list[tuple[str, str, int, int]] = []  # (id, heading_line, start, end)
    starts = [hm for hm in _HOOK_HEADING_BLOCK_RE.finditer(live)]
    for i, hm in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(live)
        line_end = live.find("\n", hm.start())
        heading = live[hm.start() : line_end if line_end != -1 else end].rstrip()
        sections.append((canon_hook_id(hm.group(2)), heading, hm.start(), end))

    to_archive: list[tuple[str, str, str]] = []  # (id, heading, section_text)
    for hid, heading, start, end in sections:
        text = live[start:end]
        fields = _section_fields(text)
        if fields.get("lifecycle_state") != "RESOLVED":
            continue
        if "archived_to" in fields:
            continue
        rc = fields.get("resolve_chapter", "")
        if not rc.isdigit() or int(rc) > resolved_through:
            continue
        to_archive.append((hid, heading, text.rstrip() + "\n"))

    if not to_archive:
        return []

    archived_ids = [hid for hid, _, _ in to_archive]

    # 1) Live pool: tombstone each archived section, drop its overview row.
    out = live
    for hid, heading, text in to_archive:
        tombstone = (
            f"{heading}\n\n"
            f"- lifecycle_state: RESOLVED\n"
            f"- resolve_chapter: {_section_fields(text).get('resolve_chapter', '-')}\n"
            f"- archived_to: {_ARCHIVE_REL}\n"
        )
        out = out.replace(text, tombstone, 1)
    lines = out.split("\n")
    dropped = {
        _row_hook_id(line)
        for line in lines
        if line.strip().startswith("|") and _row_hook_id(line) in archived_ids
    }
    out = "\n".join(
        line
        for line in lines
        if _row_hook_id(line) not in archived_ids or not line.strip().startswith("|")
    )
    note = f"> 已归档 {len(dropped)} 钩的详情段（RESOLVED，见 {_ARCHIVE_REL}）；总览行已同步移除。"
    if _ARCHIVED_NOTE_RE.search(out):
        out = _ARCHIVED_NOTE_RE.sub(note, out, count=1)
    else:
        out = re.sub(r"^(##\s*总览\s*)$", r"\1\n\n" + note, out, count=1, flags=re.MULTILINE)

    with path_lock(pool_path):
        safe_write(pool_path, out.encode("utf-8"))

    # 2) Archive: append the verbatim sections (create with frontmatter).
    with path_lock(archive_path):
        existing = archive_path.read_text(encoding="utf-8") if archive_path.exists() else ""
        base = existing if existing.startswith("---\n") else _ARCHIVE_FRONTMATTER + existing
        if existing and not existing.endswith("\n"):
            base += "\n"
        safe_write(
            archive_path, (base + "\n" + "".join(text for _, _, text in to_archive)).encode("utf-8")
        )

    return archived_ids


def _row_hook_id(line: str) -> str | None:
    m = re.search(r"(?<![A-Za-z0-9-])(MH|CP)-?(\d{1,4})(?!\d)", line)
    return canon_hook_id(f"{m.group(1)}{m.group(2)}") if m else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "Pool archive").splitlines()[0])
    parser.add_argument("project_dir", type=str, help="novel project directory")
    parser.add_argument(
        "--resolved-through",
        type=int,
        required=True,
        help="archive hooks whose resolve_chapter is at/below this (keep-window applied by caller)",
    )
    args = parser.parse_args(argv)
    archived = archive_pool(Path(args.project_dir), args.resolved_through)
    sys.stdout.write(f"archived {len(archived)}: {', '.join(archived) or '-'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
