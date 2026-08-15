"""Volume-map domain shared symbols (Cluster 1 cyclic-import refactor leaf module).

Leaf module: depends only on stdlib (re/pathlib/json/dataclasses) plus safe_write
and the base logger, imports
no pipeline cycle member (triggers/context_assemble/plan_skeleton/dispatch_helper).
The original 4-node cycle (triggers -> dispatch_helper -> plan_skeleton ->
context_assemble -> triggers) had its back-edge (context_assemble -> triggers)
broken by sinking the shared volume-map symbols here.

Migrated from: triggers.py (read_volume_boundaries/VOLUME_MAP_PATH/_END_RE/
_RANGE_RE) + context_assemble.py (_BRIDGE_ACTIVATION_WINDOW/
_resolve_volume_at_runtime). Behavior unchanged (spec §3.2).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "VOLUME_MAP_PATH",
    "_BRIDGE_ACTIVATION_WINDOW",
    "_END_RE",
    "_RANGE_RE",
    "BridgeRow",
    "_read_cn_volume_boundaries",
    "_resolve_volume_at_runtime",
    "bridges_for_chapter",
    "read_bridges",
    "read_chapter_node",
    "read_total_chapters",
    "read_volume_boundaries",
    "update_total_chapters",
]

#: Bridge activation window: chapters before activation to start surfacing bridges.
_BRIDGE_ACTIVATION_WINDOW = 3

#: Path to the volume map (relative to project_dir).
VOLUME_MAP_PATH = "outline/volume_map.md"

# "Chapter N-M" / "Chapters N-M" / "N-M" patterns in volume sections.
_END_RE = re.compile(
    r"(?:chapter\s*)?(?:end|chapter_end|end_chapter)\s*[:\uff1a]\s*(\d+)",
    re.IGNORECASE,
)
_RANGE_RE = re.compile(
    r"(?:chapters?|ch)\s*(\d+)\s*[-\u2013\u2014~\u301c]\s*(\d+)",
    re.IGNORECASE,
)

# Chinese volume format (production): volume header `## 第N卷：{卷名}` with the
# volume-level range line `**章节范围**: 第A章 - 第M章（共K章）`. KR-level lines
# are list-dash-prefixed (`- **章节范围**`) and excluded by the line-start anchor;
# the `| 段 | 章节范围 |` tension-table column never matches the bolded pattern.
_CN_VOL_HEAD_RE = re.compile(
    r"^##\s*第[0-9一二三四五六七八九十百]+卷\s*[：:]",
    re.MULTILINE,
)
_CN_VOL_RANGE_LINE_RE = re.compile(
    r"^\*\*章节范围\*\*.*?第\s*(\d+)\s*章\s*[-\u2013\u2014~\u301c]\s*第\s*(\d+)\s*章",
    re.MULTILINE,
)


def _read_cn_volume_boundaries(text: str) -> set[int]:
    """Volume-scoped Chinese parse: per ``## 第N卷:`` section, only the first
    line-start ``**章节范围**`` range line counts (its end chapter M).

    Volume header requires the colon; sections are cut at the next ``##``-level
    header so trailing summary sections cannot donate a stray range line to
    the last volume.
    """
    boundaries: set[int] = set()
    for m in _CN_VOL_HEAD_RE.finditer(text):
        section = text[m.end() :]
        nxt = re.search(r"^##\s", section, re.MULTILINE)
        if nxt:
            section = section[: nxt.start()]
        rm = _CN_VOL_RANGE_LINE_RE.search(section)
        if rm:
            boundaries.add(int(rm.group(2)))
    return boundaries


def read_volume_boundaries(project_dir: Path | str) -> set[int]:
    """Parse ``outline/volume_map.md`` and return last-chapter numbers per volume.

    Supports two markdown formats:

    1. Section with ``Chapter End: N`` (or ``End: N``).
    2. ``Chapters N-M`` range notation.
    3. Chinese volume-scoped fallback (``## 第N卷:`` + volume-level
       ``**章节范围**: 第N章 - 第M章``) when the English formats yield nothing.

    Returns an empty set if the file does not exist or cannot be parsed.
    """
    if not project_dir:
        raise ValueError("read_volume_boundaries: project_dir is required")
    project_dir = Path(project_dir)
    vm_file = project_dir / VOLUME_MAP_PATH
    if not vm_file.exists():
        return set()

    text = vm_file.read_text(encoding="utf-8")
    boundaries: set[int] = set()

    # Try "Chapter End: N" patterns first.
    for m in _END_RE.finditer(text):
        boundaries.add(int(m.group(1)))

    # Fall back to "Chapters N-M" ranges.
    if not boundaries:
        for m in _RANGE_RE.finditer(text):
            boundaries.add(int(m.group(2)))

    # Chinese volume-scoped fallback (production format, spec #6 R1).
    if not boundaries:
        boundaries = _read_cn_volume_boundaries(text)

    return boundaries


def read_total_chapters(project_dir: Path) -> int:
    """Read novel.json.total_chapters (0 when absent/malformed/not yet set)."""
    novel_path = project_dir / "novel.json"
    if not novel_path.exists():
        return 0
    try:
        data = json.loads(novel_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return 0
    total = data.get("total_chapters", 0)
    return int(total) if isinstance(total, (int, float)) else 0


def update_total_chapters(project_dir: Path) -> int:
    """Recompute novel.json.total_chapters := max(read_volume_boundaries()).

    Single write-point semantics for the genesis step-6 hook, mid-book heal,
    and volume-boundary resume (spec #6 R2). Returns the new total, or 0 when
    no boundaries parse or novel.json is absent/malformed.
    """
    boundaries = read_volume_boundaries(project_dir)
    if not boundaries:
        return 0
    new_total = max(boundaries)
    novel_path = project_dir / "novel.json"
    if not novel_path.exists():
        return 0
    try:
        data = json.loads(novel_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("total_chapters") != new_total:
        data["total_chapters"] = new_total
        from shenbi.logging import get_logger
        from shenbi.safe_write import safe_write

        get_logger(__name__).info("total_chapters_updated", total_chapters=new_total)
        safe_write(novel_path, json.dumps(data, ensure_ascii=False, indent=2))
    return new_total


def _resolve_volume_at_runtime(project_dir: Path, chapter: int) -> tuple[str, int, int] | None:
    """Resolve (volume_name, ch_start, ch_end) for a chapter at runtime.

    Parses volume_map.md via read_volume_boundaries() which
    returns a set of last-chapter numbers per volume. We build the
    (start, end) ranges from that set. The volume name is the real
    ``## 第N卷:`` header when present (spec #6 R6), falling back to
    ``Volume {i}``.
    """
    boundary_chapters = read_volume_boundaries(project_dir)
    if not boundary_chapters:
        return None

    vm_text = (project_dir / VOLUME_MAP_PATH).read_text(encoding="utf-8")
    boundaries_sorted = sorted(boundary_chapters)
    prev_end = 0
    for i, end in enumerate(boundaries_sorted, 1):
        ch_start = prev_end + 1
        if ch_start <= chapter <= end:
            name = _volume_display_name(vm_text, i) or f"Volume {i}"
            return (name, ch_start, end)
        prev_end = end
    return None


# ---------------------------------------------------------------------------
# Chapter-node / bridge / volume-name extraction (spec #6 R6).
# ---------------------------------------------------------------------------

_CN_NODE_ROW_RE_TMPL = r"^[ \t]*\|\s*第\s*{ch}\s*章\s*\|([^|]+)\|([^|]+)\|"
# The English head is kept for section splitting only: legacy 4-column
# `| V1-B1 | content | Ch N |` rows do NOT match _BRIDGE_ROW_RE (6-column,
# numeric first cell) — English row support is deferred to specs #16/#25.
_BRIDGE_HEADS = ("### 跨卷桥接", "## Cross-Volume Bridges")
_BRIDGE_ROW_RE = re.compile(
    r"^[ \t]*\|\s*\d+\s*\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]*)\|",
    re.MULTILINE,  # sections start with "\n\n| # |..." — ^ must anchor per line
)
_THIS_BOOK_VOL_RE = re.compile(r"^第\d+卷$")
# Compact ranges `第26-28章` (no second 第) and full form `第A章 - 第B章` both
# occur in production — the second 第 must be optional.
_ACT_RANGE_RE = re.compile(r"第\s*(\d+)\s*(?:[-\u2013\u2014~\u301c]\s*(?:第\s*)?(\d+)\s*)?章")


def read_chapter_node(volume_map_text: str, chapter: int) -> dict[str, str] | None:
    """Extract {role, content} from the ``| 第N章 | role | content |`` node row.

    Rows are indented (nested under ``- **章节节点**:``) — leading whitespace
    tolerated. The bare ``| N |`` alternative is deliberately NOT offered: it
    matches bridge-table ``| 1 |`` rows (the R6 garbage bug). Legacy English
    maps are deferred to the dead-code/legacy batch (specs #16/#25).
    """
    m = re.search(_CN_NODE_ROW_RE_TMPL.format(ch=chapter), volume_map_text, re.MULTILINE)
    if m:
        return {"role": m.group(1).strip(), "content": m.group(2).strip()}
    return None


@dataclass(frozen=True)
class BridgeRow:
    content: str
    kind: str
    target_volume: str
    activation: int | None
    status: str


def read_bridges(volume_map_text: str) -> list[BridgeRow]:
    """Aggregate bridge rows across ALL bridge sections (5 in production — one
    per volume; the old split()[1] consumers only ever saw volume 1).

    Rows whose 带入卷 is not ``第N卷`` (sequel markers like ``《…》续作``) are
    skipped; non-numeric activation values skip with a WARN.
    """
    from shenbi.logging import get_logger

    rows: list[BridgeRow] = []
    for head in _BRIDGE_HEADS:
        for section in volume_map_text.split(head)[1:]:
            for m in _BRIDGE_ROW_RE.finditer(section):
                content, kind, target, act_raw, status = (g.strip() for g in m.groups())
                if not _THIS_BOOK_VOL_RE.match(target):
                    continue  # sequel / non-volume row (spec #6 R6)
                am = _ACT_RANGE_RE.search(act_raw)
                if not am:
                    get_logger(__name__).warning(
                        "bridge_activation_non_numeric", target=target, raw=act_raw
                    )
                    continue
                ends = [int(am.group(1))] + ([int(am.group(2))] if am.group(2) else [])
                rows.append(BridgeRow(content, kind, target, min(ends), status))
    return rows


def bridges_for_chapter(
    bridges: list[BridgeRow], chapter: int, window: int = _BRIDGE_ACTIVATION_WINDOW
) -> list[str]:
    return [
        f"{b.target_volume} 桥接: {b.content} (activates Ch {b.activation})"
        for b in bridges
        if b.activation is not None and chapter >= b.activation - window
    ]


def _volume_display_name(text: str, index: int) -> str | None:
    heads = list(_CN_VOL_HEAD_RE.finditer(text))
    if 0 < index <= len(heads):
        line_end = text.find("\n", heads[index - 1].start())
        raw = text[heads[index - 1].start() : line_end].lstrip("#").strip()
        # The `（第A-B章）` suffix is a production coincidence, not the volume
        # name — strip it.
        return re.sub(r"[（(][^）)]*[）)]\s*$", "", raw).strip()
    return None
