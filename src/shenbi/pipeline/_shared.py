"""Volume-map domain shared symbols (Cluster 1 cyclic-import refactor leaf module).

Leaf module: depends only on stdlib (re/pathlib/json) plus safe_write and the
base logger, imports
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
from pathlib import Path

__all__ = [
    "VOLUME_MAP_PATH",
    "_BRIDGE_ACTIVATION_WINDOW",
    "_END_RE",
    "_RANGE_RE",
    "_read_cn_volume_boundaries",
    "_resolve_volume_at_runtime",
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
    (start, end) ranges from that set.
    """
    boundary_chapters = read_volume_boundaries(project_dir)
    if not boundary_chapters:
        return None

    boundaries_sorted = sorted(boundary_chapters)
    prev_end = 0
    for i, end in enumerate(boundaries_sorted, 1):
        ch_start = prev_end + 1
        if ch_start <= chapter <= end:
            return (f"Volume {i}", ch_start, end)
        prev_end = end
    return None
