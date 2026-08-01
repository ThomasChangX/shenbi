"""Volume-map domain shared symbols (Cluster 1 cyclic-import refactor leaf module).

Leaf module: depends only on stdlib (re/pathlib), imports no pipeline cycle
member (triggers/context_assemble/plan_skeleton/dispatch_helper). The original
4-node cycle (triggers -> dispatch_helper -> plan_skeleton -> context_assemble
-> triggers) had its back-edge (context_assemble -> triggers) broken by sinking
the shared volume-map symbols here.

Migrated from: triggers.py (read_volume_boundaries/VOLUME_MAP_PATH/_END_RE/
_RANGE_RE) + context_assemble.py (_BRIDGE_ACTIVATION_WINDOW/
_resolve_volume_at_runtime). Behavior unchanged (spec §3.2).
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = [
    "VOLUME_MAP_PATH",
    "_BRIDGE_ACTIVATION_WINDOW",
    "_END_RE",
    "_RANGE_RE",
    "_resolve_volume_at_runtime",
    "read_volume_boundaries",
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


def read_volume_boundaries(project_dir: Path | str) -> set[int]:
    """Parse ``outline/volume_map.md`` and return last-chapter numbers per volume.

    Supports two markdown formats:

    1. Section with ``Chapter End: N`` (or ``End: N``).
    2. ``Chapters N-M`` range notation.

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

    return boundaries


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
