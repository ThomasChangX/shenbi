"""GO② rolling archival, ledger-generic (B 批参数化).

Two evidence ledgers accumulate detail history without bound and share one
archival shape — the pending_hooks pool (``- lifecycle_state:`` plain
bullets, resolve via ``resolve_chapter``) and the thread ledger
(``outline/thread_map.md``: ``- **状态**:`` bold bullets, resolve via the
end of ``- **跨度**: 第X章 - 第Y章``). :func:`archive_ledger` moves
TERMINAL entries (state RESOLVED with a resolve chapter at/below the
caller's window) verbatim into the ledger's archive file, leaving a
three-bullet tombstone and dropping the overview row — deterministic code,
not an LLM discipline (the drift-guidance ``audit_drift_archive`` window is
the design precedent).

``archive_pool`` keeps its historical signature (thin wrapper over
``POOL_SPEC``); :func:`archive_all` services both ledgers in one call for
the volume-boundary chain::

    python -m shenbi.pipeline.ledger_archive <dir> --resolved-through 94
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from shenbi.pipeline.truth_io import parse_thread_span, path_lock
from shenbi.safe_write import safe_write


@dataclass(frozen=True)
class LedgerSpec:
    """One evidence ledger's archival shape.

    ``section_heading_re`` must expose the entry id in group(2) (same group
    layout as truth_io's hook heading regexes); ``canon`` canonicalizes ids
    (hooks strip zero-padding, threads are already canonical).
    """

    live_rel: str
    archive_rel: str
    archive_title: str
    overview_heading: str  # ``## <overview_heading>`` bounds the row table
    details_heading: str  # ``## <details_heading>`` bounds the sections
    section_heading_re: re.Pattern[str]
    row_id_re: re.Pattern[str]  # id search inside a table row's FIRST cell
    state_field: str  # bullet name carrying the lifecycle state
    span_field: str  # bullet name carrying the resolve chapter(s)
    canon: Callable[[str], str]
    state_bullet: Callable[[str], str]
    span_bullet: Callable[[str, str], str]  # (raw span value, parsed end)


def _plain_state(state: str) -> str:
    return f"- lifecycle_state: {state}"


def _plain_span(_raw: str, end: str) -> str:
    return f"- resolve_chapter: {end}"


def _bold_state(state: str) -> str:
    return f"- **状态**: {state}"


def _bold_span(raw: str, _end: str) -> str:
    return f"- **跨度**: {raw}"


def _pool_canon(raw: str) -> str:
    from shenbi.pipeline.truth_io import canon_hook_id

    return canon_hook_id(raw)


#: The pending_hooks pool (GO② original shape).
POOL_SPEC = LedgerSpec(
    live_rel="truth/pending_hooks.md",
    archive_rel="truth/pending_hooks_archive.md",
    archive_title="伏笔池",
    overview_heading="总览",
    details_heading="详情",
    section_heading_re=re.compile(r"^(#{2,6})\s+((?:MH|CP)-?\d{1,4})\b", re.MULTILINE),
    row_id_re=re.compile(r"(?<![A-Za-z0-9-])(MH|CP)-?(\d{1,4})(?!\d)"),
    state_field="lifecycle_state",
    span_field="resolve_chapter",
    canon=_pool_canon,
    state_bullet=_plain_state,
    span_bullet=_plain_span,
)

#: The thread ledger (B 批): ``### A1: 名称`` sections under ``## 线索详情``,
#: overview rows under ``## 线索总览表``, terminal state via ``- **状态**:
#: RESOLVED``, resolve chapter = the END of the ``- **跨度**:`` bullet.
THREAD_SPEC = LedgerSpec(
    live_rel="outline/thread_map.md",
    archive_rel="outline/thread_map_archive.md",
    archive_title="线索地图",
    overview_heading="线索总览表",
    details_heading="线索详情",
    section_heading_re=re.compile(r"^(#{2,6})\s+([ABC]\d{1,3})(?![0-9])", re.MULTILINE),
    row_id_re=re.compile(r"(?<![A-Za-z0-9-])([ABC]\d{1,3})(?![0-9A-Za-z])"),
    state_field="状态",
    span_field="跨度",
    canon=lambda raw: raw.strip(),
    state_bullet=_bold_state,
    span_bullet=_bold_span,
)


def _section_fields(spec: LedgerSpec, section: str) -> dict[str, str]:
    """Latest colon-bullet fields of a section, emphasis markers stripped."""
    fields: dict[str, str] = {}
    pat = re.compile(
        r"^-\s+\*{0,2}("
        + re.escape(spec.state_field)
        + r"|"
        + re.escape(spec.span_field)
        + r"|archived_to)\*{0,2}\s*[:：]\s*(.+)$"
    )
    for line in section.splitlines():
        m = pat.match(line.strip())
        if m:
            fields.setdefault(m.group(1), m.group(2).strip())
    return fields


def _resolve_end(spec: LedgerSpec, fields: dict[str, str]) -> str:
    """The entry's resolve chapter as digits ("" when absent/unparseable)."""
    raw = fields.get(spec.span_field, "")
    if not raw:
        return ""
    if spec is THREAD_SPEC:
        return parse_thread_span(raw)[1]
    return raw.strip()


def archive_ledger(project_dir: Path, resolved_through: int, spec: LedgerSpec) -> list[str]:
    """Move terminal sections past the window into the ledger's archive file.

    Returns the archived entry ids (canonical, in file order). Idempotent:
    tombstoned sections (``archived_to`` bullet present) and non-terminal
    entries are skipped, so a repeated call with the same window is a no-op.
    Raises ValueError when the live ledger lacks the expected overview/
    details shape — the archival must never guess at an unexpected layout
    (degrade loudly).
    """
    live_path = project_dir / spec.live_rel
    archive_path = project_dir / spec.archive_rel
    live = live_path.read_text(encoding="utf-8")

    if not re.search(rf"^##\s*{spec.overview_heading}\s*$", live, re.MULTILINE) or (
        not re.search(rf"^##\s*{spec.details_heading}\s*$", live, re.MULTILINE)
    ):
        raise ValueError(
            f"{spec.live_rel} 缺少 {spec.overview_heading}/{spec.details_heading} 结构——"
            "拒绝在异常布局上归档（degrade loudly）。"
        )

    # Section spans in the details body (heading → next same-or-higher heading).
    sections: list[tuple[str, str, int, int]] = []  # (id, heading_line, start, end)
    starts = [hm for hm in spec.section_heading_re.finditer(live)]
    for i, hm in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(live)
        line_end = live.find("\n", hm.start())
        heading = live[hm.start() : line_end if line_end != -1 else end].rstrip()
        sections.append((spec.canon(hm.group(2)), heading, hm.start(), end))

    to_archive: list[tuple[str, str, str, str]] = []  # (id, heading, section_text, end)
    for hid, heading, start, end in sections:
        text = live[start:end]
        fields = _section_fields(spec, text)
        if fields.get(spec.state_field) != "RESOLVED":
            continue
        if "archived_to" in fields:
            continue
        rend = _resolve_end(spec, fields)
        if not rend.isdigit() or int(rend) > resolved_through:
            continue
        to_archive.append((hid, heading, text.rstrip() + "\n", rend))

    if not to_archive:
        return []

    archived_ids = [hid for hid, _, _, _ in to_archive]

    # 1) Live ledger: tombstone each archived section, drop its overview row.
    out = live
    for hid, heading, text, rend in to_archive:
        fields = _section_fields(spec, text)
        tombstone = (
            f"{heading}\n\n"
            f"{spec.state_bullet('RESOLVED')}\n"
            f"{spec.span_bullet(fields.get(spec.span_field, '-'), rend)}\n"
            f"- archived_to: {spec.archive_rel}\n"
        )
        out = out.replace(text, tombstone, 1)
    lines = out.split("\n")
    out = "\n".join(
        line
        for line in lines
        if not (line.strip().startswith("|") and _row_entry_id(spec, line) in archived_ids)
    )
    note = (
        f"> 已归档 {len(archived_ids)} 条终态条目（RESOLVED，见 {spec.archive_rel}）；"
        f"{spec.overview_heading}行已同步移除。"
    )
    note_re = re.compile(r"^> 已归档.*$", re.MULTILINE)
    if note_re.search(out):
        out = note_re.sub(note, out, count=1)
    else:
        out = re.sub(
            rf"^(##\s*{spec.overview_heading}\s*)$",
            r"\1\n\n" + note,
            out,
            count=1,
            flags=re.MULTILINE,
        )

    with path_lock(live_path):
        safe_write(live_path, out.encode("utf-8"))

    # 2) Archive: append the verbatim sections (create with frontmatter).
    frontmatter = (
        "---\ntype: truth\ncategory: state\nstatus: active\n"
        f'note: "由 shenbi.pipeline.ledger_archive 滚动归档（GO②/B 批）；整段自 {spec.live_rel} '
        '原样移入，不重述、不改写。"\n---\n\n' + f"# {spec.archive_title} · 已归档详情\n\n"
    )
    with path_lock(archive_path):
        existing = archive_path.read_text(encoding="utf-8") if archive_path.exists() else ""
        base = existing if existing.startswith("---\n") else frontmatter + existing
        if existing and not existing.endswith("\n"):
            base += "\n"
        safe_write(
            archive_path,
            (base + "\n" + "".join(text for _, _, text, _ in to_archive)).encode("utf-8"),
        )

    return archived_ids


def _row_entry_id(spec: LedgerSpec, line: str) -> str | None:
    """Entry id from a table row's FIRST cell (None when the cell has none)."""
    stripped = line.strip().strip("|")
    first = stripped.split("|", 1)[0] if "|" in stripped else stripped
    m = spec.row_id_re.search(first)
    return spec.canon(m.group(0)) if m else None


def archive_pool(project_dir: Path, resolved_through: int) -> list[str]:
    """Back-compat entry point: archive the pending_hooks pool only."""
    return archive_ledger(project_dir, resolved_through, POOL_SPEC)


def archive_all(project_dir: Path, resolved_through: int) -> dict[str, list[str]]:
    """Both ledgers in one call — the volume-boundary chain's single command."""
    results: dict[str, list[str]] = {}
    for spec in (POOL_SPEC, THREAD_SPEC):
        live = project_dir / spec.live_rel
        if not live.is_file():
            results[spec.live_rel] = []
            continue
        try:
            results[spec.live_rel] = archive_ledger(project_dir, resolved_through, spec)
        except ValueError as exc:
            # One ledger's abnormal layout must not abort the other's
            # archival — report the failure loudly and continue.
            from shenbi.logging import get_logger

            get_logger(__name__).error("ledger_archive_abnormal_layout", error=str(exc))
            sys.stderr.write(f"FAIL: {exc}\n")
            results[spec.live_rel] = []
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "Ledger archive").splitlines()[0])
    parser.add_argument("project_dir", type=str, help="novel project directory")
    parser.add_argument(
        "--resolved-through",
        type=int,
        required=True,
        help="archive entries whose resolve chapter is at/below this (keep-window applied by caller)",
    )
    parser.add_argument(
        "--ledger",
        choices=("all", "pool", "thread"),
        default="all",
        help="which ledger to archive (default: both)",
    )
    args = parser.parse_args(argv)
    project = Path(args.project_dir)
    specs: tuple[LedgerSpec, ...]
    if args.ledger == "pool":
        specs = (POOL_SPEC,)
    elif args.ledger == "thread":
        specs = (THREAD_SPEC,)
    else:
        specs = (POOL_SPEC, THREAD_SPEC)
    status = 0
    for spec in specs:
        live = project / spec.live_rel
        if not live.is_file():
            sys.stdout.write(f"{spec.live_rel}: not found, skipped\n")
            continue
        try:
            archived = archive_ledger(project, args.resolved_through, spec)
        except ValueError as exc:
            sys.stdout.write(f"FAIL {spec.live_rel}: {exc}\n")
            status = 1
            continue
        sys.stdout.write(
            f"{spec.live_rel}: archived {len(archived)}: {', '.join(archived) or '-'}\n"
        )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
