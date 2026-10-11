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
- ``hooks_inventory_scoped`` (pending_hooks): the volume-boundary resolve
  variant — grounding comes from the file itself (总览 rows whose 当前生命周
  期 is TRIGGERED or PARTIAL), not from chapter plan/audit naming. Same head
  shape (frontmatter + 总览 full + ``## 详情``) so the inventory keeps the
  whole lifecycle table while only candidate detail sections ride along.
- ``hooks_overview`` (pending_hooks): frontmatter + 总览 table only, details
  omitted with a sentinel — for consumers that need the lifecycle table and
  nothing else (planning / composing / boundary consolidation / distill /
  payoff).
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


def _boundary_candidate_ids(content: str) -> set[str]:
    """Hook ids whose 总览 lifecycle cell reads TRIGGERED **or PARTIAL** (the
    volume-boundary resolve candidates — PARTIAL hooks carry an open payoff
    disposition: phase3 ch94, CP-005/CP-007 could only be adjudicated via a
    driver modify because the extractor never surfaced them). Empty on any
    missing/misordered section shape — the caller treats that as fallback.
    """
    m_ov = re.search(r"^##\s*总览\s*$", content, re.MULTILINE)
    m_det = re.search(r"^##\s*详情\s*$", content, re.MULTILINE)
    if m_ov is None or m_det is None or m_ov.start() >= m_det.start():
        return set()
    from shenbi.pipeline.truth_io import canon_hook_id

    ids: set[str] = set()
    for line in content[m_ov.end() : m_det.start()].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        idm = _GROUNDING_ID_RE.search(cells[0])
        if idm is not None and cells[1] in ("TRIGGERED", "PARTIAL"):
            ids.add(canon_hook_id(f"{idm.group(1)}{idm.group(2)}"))
    return ids


def extract_hooks_overview(content: str) -> str:
    """Slice pending_hooks to frontmatter + 总览 table + a disclosed omission.

    For consumers that only need the lifecycle table — chapter planning,
    context composing, and the boundary chain (arc-payoff / memory-distill /
    volume-consolidation read states and resolve/carried tallies, all of
    which live in overview columns). The detail evidence history is the
    pool's bulk (MH01 alone carries thousands of chars of 证据 at ch118) and
    is not these consumers' concern. Returns ``""`` on an unexpected shape —
    the dispatch loop then serves the full file with a WARN (extractor
    failure must degrade loudly, never silently).

    A compact tombstone index rides along: archived hooks (GO② pool_archive)
    have no overview row and no live section — without the index, planning
    could not see that the id ever existed and might re-plant a semantic
    duplicate (session31 self-review defect).
    """
    m_ov = re.search(r"^##\s*总览\s*$", content, re.MULTILINE)
    m_det = re.search(r"^##\s*详情\s*$", content, re.MULTILINE)
    if m_ov is None or m_det is None or m_ov.start() >= m_det.start():
        return ""
    n_sections = len(_DETAIL_HEADING_RE.findall(content[m_det.end() :]))
    sentinel = (
        f"> [extractor:hooks_overview] 详情 {n_sections} 段已整体省略——"
        f"总览表每行即该钩生命周期的权威摘要（当前生命周期/种植章/兑现章），"
        f"证据史与字段明细见 truth/pending_hooks.md 本体。\n"
    )
    body = content[m_det.end() :]
    tombstones: list[str] = []
    starts = [hm for hm in _DETAIL_HEADING_RE.finditer(body)]
    for i, hm in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(body)
        section = body[hm.start() : end]
        if "archived_to" in section:
            state = re.search(r"- lifecycle_state:\s*(\S+)", section)
            rc = re.search(r"- resolve_chapter:\s*(\d+)", section)
            tombstones.append(
                f"- {hm.group(1)}: {state.group(1) if state else 'RESOLVED'}"
                f"@{rc.group(1) if rc else '?'} → truth/pending_hooks_archive.md"
            )
    index = ""
    if tombstones:
        index = (
            "\n### 已归档钩索引（extractor 附——这些 id 已终态归档，"
            "不得重复种植同语义钩）\n\n" + "\n".join(tombstones) + "\n"
        )
    return content[: m_det.end()] + "\n" + sentinel + index


def extract_hooks_inventory_scoped(content: str) -> str:
    """Slice pending_hooks for the volume-boundary resolve inventory.

    Same output shape as :func:`extract_hooks_audit_scoped` (frontmatter +
    总览 full + ``## 详情`` + kept sections + omission sentinel) but the
    grounding set is intrinsic: the hooks the 总览 itself marks TRIGGERED or
    PARTIAL — the resolve candidates. Returns ``""`` when there are no
    candidates or the shape is unexpected — the dispatch loop then serves
    the full file with a WARN (extractor failure must degrade loudly, never
    silently).
    """
    from shenbi.pipeline.truth_io import canon_hook_id

    m = re.search(r"^##\s*详情\s*$", content, re.MULTILINE)
    if m is None:
        return ""
    triggered = _boundary_candidate_ids(content)
    if not triggered:
        return ""

    head = content[: m.end()]
    body = content[m.end() :]

    starts = [hm for hm in _DETAIL_HEADING_RE.finditer(body)]
    if not starts:
        return ""

    kept: list[str] = []
    omitted: list[str] = []
    plant_by_id: dict[str, str] = {}
    lr_by_id: dict[str, str] = {}
    section_ids: list[tuple[str, str]] = []
    for i, hm in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(body)
        section = body[hm.start() : end]
        sec_id = canon_hook_id(hm.group(1))
        section_ids.append((hm.group(1), sec_id))
        pm = re.search(r"- plant_chapter:\s*(\d+)", section)
        if pm is not None:
            plant_by_id[sec_id] = pm.group(1)
        lrm = re.search(r"- last_reinforced:\s*第?\s*(\d+)\s*章", section)
        lr_by_id[sec_id] = lrm.group(1) if lrm is not None else "未强化"
        if sec_id in triggered:
            kept.append(section)
        else:
            omitted.append(hm.group(1))
    if not kept:
        return ""
    # T0 follow-up (adjudication 233 watch 1): plant chapters from the
    # overview's 种植章 column for hooks whose detail omits the field.
    m_ov = re.search(r"^##\s*总览\s*$", content, re.MULTILINE)
    if m_ov is not None and m_ov.start() < m.start():
        for line in content[m_ov.end() : m.start()].splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3:
                continue
            idm = _GROUNDING_ID_RE.search(cells[0])
            if idm is not None:
                plant_by_id.setdefault(canon_hook_id(f"{idm.group(1)}{idm.group(2)}"), cells[2])
    anchor_lines = [
        f"- {display}: plant {plant_by_id.get(sec_id, '?')} | last_reinforced {lr_by_id.get(sec_id, '未强化')}"
        for display, sec_id in section_ids
    ]
    digest = (
        "\n### 生命周期锚点（extractor 附；CP 口径：time_since_plant = 边界章 − last_reinforced）\n\n"
        + "\n".join(anchor_lines)
        + "\n\n"
    )

    omitted_list = "、".join(omitted[:_MAX_SENTINEL_UNITS])
    if len(omitted) > _MAX_SENTINEL_UNITS:
        omitted_list += f" 等 {len(omitted)} 段"
    sentinel = (
        f"> [extractor:hooks_inventory_scoped] 详情已按 TRIGGERED/PARTIAL 清点裁剪："
        f"保留 {len(kept)} 段，省略 {len(omitted)} 段（{omitted_list}）——"
        f"未清点钩子的完整生命周期见上方总览表。\n"
    )
    return head + "\n" + sentinel + digest + "".join(kept).rstrip() + "\n"


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


#: Thread-ledger detail-section heading inside ``## 线索详情``
#: (``### A1: 灵印·私修引灵与《灵律》残句``).
_THREAD_DETAIL_HEADING_RE = re.compile(r"^###\s+([ABC]\d{1,3})(?![0-9A-Za-z])", re.MULTILINE)

#: A 章节线索推进表 interval row: ``| 1-8（一卷 KR1） | A1 | … |``.
_THREAD_INTERVAL_ROW_RE = re.compile(r"^\|\s*(\d+)\s*-\s*(\d+)\s*[（(]")


def extract_threads_overview(content: str, chapter: int | None = None) -> str:
    """Slice outline/thread_map.md to what one chapter's consumers need.

    B 批 (千万字读面): the thread ledger grows without bound — every volume
    adds interval rows and every weave grows the 交叉点/高潮窗口 history.
    The slice serves:

    - frontmatter + preamble + the FULL 线索总览表 (every live thread's
      compact authoritative row — archival keeps it bounded);
    - ACTIVE detail sections only (``- **状态**:`` ≠ RESOLVED, no
      ``archived_to`` tombstone) with a disclosed omission sentinel;
    - a tombstone index of archived threads (same anti-re-plant contract
      as the pool's 已归档钩索引);
    - the 章节线索推进表 windowed to the current chapter's interval ± 1
      (chapter=None keeps it whole — the genesis weaver);
    - NOT the 约束检查表/空白检测/跨卷衔接/线索编织汇总 validator snapshots.

    Returns ``""`` on an unexpected shape, or when *chapter* lies outside
    every planned interval (re-budget seam — the consumer needs the whole
    file) — the dispatch loop then serves full text + WARN (extractor
    failure must degrade loudly, never silently).
    """
    m_ov = re.search(r"^##\s*线索总览表\s*$", content, re.MULTILINE)
    m_det = re.search(r"^##\s*线索详情\s*$", content, re.MULTILINE)
    if m_ov is None or m_det is None or m_ov.start() >= m_det.start():
        return ""
    m_plan = re.search(r"^##\s*章节线索推进表\s*$", content, re.MULTILINE)

    head = content[: m_det.end()]
    details_end = (
        m_plan.start() if (m_plan is not None and m_plan.start() > m_det.end()) else len(content)
    )
    body = content[m_det.end() : details_end]

    starts = [hm for hm in _THREAD_DETAIL_HEADING_RE.finditer(body)]
    kept: list[str] = []
    omitted: list[str] = []
    tombstones: list[str] = []
    for i, hm in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(body)
        section = body[hm.start() : end]
        if "archived_to" in section:
            sm = re.search(r"-\s+\*{0,2}状态\*{0,2}\s*[:：]\s*(\S+)", section)
            tombstones.append(
                f"- {hm.group(1)}: {sm.group(1) if sm else 'RESOLVED'} → outline/thread_map_archive.md"
            )
            continue
        sm = re.search(r"-\s+\*{0,2}状态\*{0,2}\s*[:：]\s*(\S+)", section)
        if sm is not None and sm.group(1) == "RESOLVED":
            omitted.append(hm.group(1))
        else:
            kept.append(section)

    n_total = len(starts)
    sentinel = (
        f"> [extractor:threads_overview] 线索详情 {n_total} 段：保留活跃 {len(kept)} 段，"
        f"省略 {len(omitted)} 段（终态/已归档）——各线当前状态见上方线索总览表，"
        f"完整交叉点与高潮窗口史见 outline/thread_map.md 本体。\n"
    )
    index = ""
    if tombstones:
        index = (
            "\n### 已归档线索索引（extractor 附——这些 ID 已终态归档，"
            "不得重复开辟同语义线）\n\n" + "\n".join(tombstones) + "\n"
        )
    out = head + "\n" + sentinel + index + "".join(kept).rstrip() + "\n"

    if m_plan is not None:
        plan_line_end = content.find("\n", m_plan.start())
        rest = content[plan_line_end + 1 :]
        m_trail = re.search(r"^##\s+\S", rest, re.MULTILINE)
        plan_body = rest[: m_trail.start()] if m_trail is not None else rest
        trailing_head = rest[m_trail.start() :] if m_trail is not None else ""
        plan_windowed = _window_interval_rows(plan_body, chapter)
        if plan_windowed is None:
            return ""
        out += "\n" + content[m_plan.start() : plan_line_end] + "\n" + plan_windowed
        if trailing_head:
            out += (
                "\n> [extractor:threads_overview] 约束检查表/空白检测/跨卷衔接/"
                "线索编织汇总 为编织器校验快照，已省略——见 outline/thread_map.md 本体。\n"
            )
    return out


def _window_interval_rows(plan_body: str, chapter: int | None) -> str | None:
    """Keep the interval row containing *chapter* ± 1 neighbor; None = degrade.

    Non-interval lines (the table header/separator, the blockquote note)
    always ride along. ``chapter=None`` keeps every interval row (genesis).
    A chapter inside NO interval is a re-budget seam — None makes the
    caller fall back to the whole file (loud, never a silent mis-slice).
    """
    lines = plan_body.split("\n")
    interval_idx = [i for i, l in enumerate(lines) if _THREAD_INTERVAL_ROW_RE.match(l.strip())]
    keep: set[int] = set()
    if chapter is None:
        return plan_body  # genesis weaver — every planned interval rides along
    anchor: int | None = None
    for pos, i in enumerate(interval_idx):
        m = _THREAD_INTERVAL_ROW_RE.match(lines[i].strip())
        if m is not None and int(m.group(1)) <= chapter <= int(m.group(2)):
            anchor = pos
            break
    if anchor is None:
        return None
    for pos in (anchor - 1, anchor, anchor + 1):
        if 0 <= pos < len(interval_idx):
            keep.add(interval_idx[pos])
    out_lines: list[str] = []
    omitted = len(interval_idx) - len(keep)
    for i, line in enumerate(lines):
        if i in interval_idx and i not in keep:
            if omitted and out_lines and out_lines[-1] != "":
                out_lines.append(
                    f"> …已按当前章窗口裁剪：保留 {len(keep)}/{len(interval_idx)} 个区间行，"
                    f"省略 {omitted} 行——完整推进表见 outline/thread_map.md 本体。"
                )
                omitted = 0  # one sentinel, placed at the first cut
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


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
