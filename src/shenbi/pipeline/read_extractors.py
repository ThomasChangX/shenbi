"""Plan A read-slicing extractors (adjudication 096 / 191-PENDING 方案A).

The cumulative truth tables (pending_hooks, chapter_summaries, the five
chapter-keyed state tables) grow without bound — ~1.7KB per chapter each.
Whole-file reads fed them into every dispatch prompt (linear-to-quadratic
input growth; ch58 lifecycle hit the 58982 completion ceiling restating a
pool it saw as a 32K head-clipped 残篇). These extractors slice reads to
what the dispatched skill actually needs for ONE chapter:

- ``hooks_audit_scoped`` (pending_hooks): the 总览 table FULL (every hook's
  lifecycle row is compact and authoritative) + ONLY the ``### <id>`` detail
  sections this chapter's grounding files name (the plan's hook 账 table
  union the chapter's foreshadowing audit). Fallback contract: return ``""`` on
  anything unexpected and the dispatch loop serves full text + WARN — never
  a silent drop (spec #65 §4.3 discipline).
- ``recent_increments`` (chapter-keyed cumulative tables/ledgers): preamble
  (frontmatter/title/table header) + the last N chapter units, disclosed by
  an omission sentinel.
- :func:`chapter_scoped_head_tail`: the budget-truncation backstop for
  chapter-keyed files — keep the head block and tail units, cut the middle
  (the old head-only clip orphaned table rows mid-file).

Extractor outputs ALWAYS carry an explicit omission sentinel (F361
cap-proof discipline: the disclosure is part of the served text).
"""

from __future__ import annotations

import re
from pathlib import Path

#: Hook ids as they appear in plan/audit grounding text (``MH02`` /
#: ``CP-001`` / legacy ``MH-002``) — normalized through canon_hook_id.
_GROUNDING_ID_RE = re.compile(r"(?<![A-Za-z0-9-])(MH|CP)-?(\d{1,4})(?!\d)")

#: Detail-section heading inside pending_hooks' ``## 详情`` (``### MH01（名）``).
_DETAIL_HEADING_RE = re.compile(r"^###\s+((?:MH|CP)-?\d{1,4})\b", re.MULTILINE)

#: A chapter-keyed section unit: ``### 第 47 章`` / ``## 第N章状态增量``.
_SECTION_UNIT_RE = re.compile(r"^#{2,4}\s*第\s*(\d+)\s*章", re.MULTILINE)

#: A chapter-keyed table row: ``| 第 47 章 | … ``.
_ROW_UNIT_RE = re.compile(r"^\|\s*第\s*(\d+)\s*章\s*\|", re.MULTILINE)

_GROUP_HEADING_RE = re.compile(r"^##\s+\S", re.MULTILINE)

#: Omitted-range sentinel cap: beyond this many units the sentinel names the
#: span, not every unit (the sentinel itself must stay cheap).
_MAX_SENTINEL_UNITS = 40


def _staging_first(project_dir: Path, rel: str) -> Path:
    """F-3 parity: same-chapter writer products exist only under staging/
    until commit — grounding lookups check the staged twin first.
    """
    staged = project_dir / "staging" / rel
    if staged.is_file():
        return staged
    return project_dir / rel


def _grounding_hook_ids(project_dir: Path, chapter: int) -> set[str]:
    from shenbi.pipeline.truth_io import canon_hook_id

    ids: set[str] = set()
    for rel in (f"plans/chapter-{chapter}-plan.md", f"audits/chapter-{chapter}-foreshadowing.md"):
        path = _staging_first(project_dir, rel)
        if not path.is_file():
            continue
        for m in _GROUNDING_ID_RE.finditer(path.read_text(encoding="utf-8")):
            ids.add(canon_hook_id(f"{m.group(1)}{m.group(2)}"))
    return ids


def has_chapter_units(content: str) -> bool:
    """True when *content* carries any chapter-keyed unit (row or section)."""
    return bool(_ROW_UNIT_RE.search(content) or _SECTION_UNIT_RE.search(content))


def extract_hooks_audit_scoped(project_dir: Path, chapter: int | None, content: str) -> str:
    """Slice pending_hooks to 总览 full + this chapter's named detail sections.

    Returns ``""`` when the slice cannot be made responsibly (chapter=None
    genesis dispatch, no grounding ids, or an unexpected file shape) — the
    dispatch loop then serves the full file with a WARN (extractor failure
    must degrade loudly, never silently).
    """
    if chapter is None:
        return ""
    named = _grounding_hook_ids(project_dir, chapter)
    if not named:
        return ""
    m = re.search(r"^##\s*详情\s*$", content, re.MULTILINE)
    if m is None:
        return ""
    from shenbi.pipeline.truth_io import canon_hook_id

    head = content[: m.end()]
    body = content[m.end() :]

    starts = [hm for hm in _DETAIL_HEADING_RE.finditer(body)]
    if not starts:
        return ""

    kept: list[str] = []
    omitted: list[str] = []
    for i, hm in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(body)
        section = body[hm.start() : end]
        hook_id = canon_hook_id(hm.group(1))
        if hook_id in named:
            kept.append(section)
        else:
            omitted.append(hm.group(1))
    if not kept:
        return ""

    omitted_list = "、".join(omitted[:_MAX_SENTINEL_UNITS])
    if len(omitted) > _MAX_SENTINEL_UNITS:
        omitted_list += f" 等 {len(omitted)} 段"
    sentinel = (
        f"> [extractor:hooks_audit_scoped] 详情已按本章 plan/audit 点名裁剪："
        f"保留 {len(kept)} 段，省略 {len(omitted)} 段（{omitted_list}）——"
        f"未点名钩子的完整生命周期见上方总览表。\n"
    )
    return head + "\n" + sentinel + "".join(kept).rstrip() + "\n"


def _slice_table_units(content: str, keep: int) -> str | None:
    """Last-*keep* chapter rows + preamble. None when not chapter-keyed."""
    rows = list(_ROW_UNIT_RE.finditer(content))
    if len(rows) <= keep:
        return None
    first_kept = rows[-keep]
    # Head block = everything before the FIRST unit (frontmatter/title/
    # table header) — NOT before the first kept unit, or the omitted rows
    # would ride along in the preamble.
    preamble = content[: rows[0].start()].rstrip("\n")
    chapters = [int(r.group(1)) for r in rows]
    omitted = [c for c in chapters[:-keep]]
    span = f"第{min(omitted)}–{max(omitted)}章" if omitted else ""
    sentinel = (
        f"> [extractor:recent_increments] 已裁剪：保留最近 {keep} 章"
        f"（第{chapters[-keep]}–{chapters[-1]}章），省略 {len(omitted)} 章（{span}）"
        f"——全史见 truth 文件本体。\n"
    )
    return preamble + "\n\n" + sentinel + content[first_kept.start() :]


def _slice_section_units(content: str, keep: int) -> str | None:
    """Last-*keep* ``第N章`` sections, each re-attached to its nearest ``##``
    group heading when that heading was cut. None when not section-keyed.
    """
    units = list(_SECTION_UNIT_RE.finditer(content))
    if len(units) <= keep:
        return None
    first_kept = units[-keep]
    # Head block stops at the FIRST unit — omitted sections must not ride
    # along in the preamble (only non-unit scaffolding belongs to it).
    preamble = content[: units[0].start()].rstrip("\n")

    kept_body = content[first_kept.start() :]
    group = None
    gm = None
    for gm_ in _GROUP_HEADING_RE.finditer(content[: first_kept.start()]):
        gm = gm_
    if gm is not None:
        line_end = content.find("\n", gm.start())
        group = content[gm.start() : line_end if line_end != -1 else gm.end()].rstrip()
    # Re-attach the kept block's nearest group heading unless the preamble
    # already carries it (the group of the FIRST kept unit was the last one
    # seen before the cut point).
    if group and group not in preamble:
        kept_body = group + "\n\n" + kept_body

    chapters = [int(u.group(1)) for u in units]
    omitted = chapters[:-keep]
    span = f"第{min(omitted)}–{max(omitted)}章" if omitted else ""
    sentinel = (
        f"> [extractor:recent_increments] 已裁剪：保留最近 {keep} 章分节"
        f"（第{chapters[-keep]}–{chapters[-1]}章），省略 {len(omitted)} 章（{span}）"
        f"——全史见 truth 文件本体。\n"
    )
    return preamble + "\n\n" + sentinel + kept_body


def extract_recent_increments(content: str, *, keep: int = 3) -> str:
    """Slice a chapter-keyed cumulative file to head + last *keep* units.

    Accepts both shapes in the wild: ``| 第 N 章 |`` table rows
    (chapter_summaries / the five state tables) and ``### 第 N 章``
    sections (audit_drift). Returns ``""`` on an unexpected shape (full-text
    fallback at the caller).
    """
    sliced = _slice_table_units(content, keep)
    if sliced is None:
        sliced = _slice_section_units(content, keep)
    if sliced is None:
        return ""
    return sliced


def chapter_scoped_head_tail(text: str, budget: int) -> str | None:
    """Budget-truncation backstop for chapter-keyed files: keep the head
    block plus as many TAIL units as *budget* allows (at least one), cut the
    middle, disclose with a ``[TRUNCATED …]`` sentinel.

    Returns ``None`` when *text* carries no chapter units — the caller then
    applies the plain head clip (unchanged behavior for non-chapter files).
    """
    if len(text) <= budget:
        return None
    row_matches = list(_ROW_UNIT_RE.finditer(text))
    section_matches = list(_SECTION_UNIT_RE.finditer(text))
    matches = row_matches if len(row_matches) >= len(section_matches) else section_matches
    if not matches:
        return None

    preamble = text[: matches[0].start()].rstrip("\n")
    sentinel_overhead = 120
    room = budget - len(preamble) - sentinel_overhead
    if room <= 0:
        return None
    # Greedy tail packing: newest unit first, stop before overflowing.
    kept_from = len(matches) - 1
    used = 0
    while kept_from > 0:
        unit_len = matches[kept_from].start() - matches[kept_from - 1].start()
        if used + unit_len > room:
            break
        used += unit_len
        kept_from -= 1
    kept = text[matches[kept_from].start() :]
    if len(preamble) + len(kept) >= len(text):
        return None
    total = len(matches)
    kept_n = total - kept_from
    sentinel = (
        f"\n\n[TRUNCATED head+tail {len(preamble) + len(kept)}/{len(text)} chars: "
        f"kept head block + last {kept_n}/{total} chapter units, middle cut]\n"
    )
    return preamble + sentinel + kept
