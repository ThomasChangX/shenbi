# src/shenbi/contracts/paths.py
"""Single source of truth for chapter/volume placeholder resolution.

Replaces 4 divergent implementations (executor._resolve_chapter_path,
dispatch_helper._resolve_path, chapter_loop._substitute_chapter,
closure._substitute_volume). The unbounded str.replace("N") in the old
executor/closure versions corrupted any path containing uppercase N
(e.g. import/canon/01_SECTION.md -> 01_SECTIO5.md). The bounded regex here
only replaces N at separator boundaries.
"""

from __future__ import annotations
import re


class UnresolvedPathError(ValueError):
    """Path contains a chapter/volume placeholder but no context was provided."""


_BOUND_N = re.compile(r"(?<=[-/])N(?=[-./]|$)")
_NNN = "NNN"


def _bounded_replace_n(path: str, value: int) -> str:
    return _BOUND_N.sub(str(value), path)


def resolve_chapter_path(path: str, chapter: int | None) -> str:
    if chapter is None:
        if _NNN in path or _BOUND_N.search(path):
            raise UnresolvedPathError(path)
        return path
    result = path.replace(_NNN, f"{chapter:03d}")
    return _bounded_replace_n(result, chapter)


def resolve_volume_path(path: str, volume: int | None) -> str:
    if volume is None:
        if _BOUND_N.search(path):
            raise UnresolvedPathError(path)
        return path
    return _bounded_replace_n(path, volume)


def extract_chapter(text: str) -> int | None:
    m = re.search(r"\bchapter\s+(\d+)\b", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def resolve_or_skip(path: str, chapter: int | None) -> str | None:
    """Genesis-mode helper: returns None if path has unresolvable placeholder."""
    try:
        return resolve_chapter_path(path, chapter)
    except UnresolvedPathError:
        return None
