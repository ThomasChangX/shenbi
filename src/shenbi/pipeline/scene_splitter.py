"""Spec #72 deterministic scene splitter: single-source marker machinery.

The bundle contract: one drafting dispatch = 2 consecutive chapters (~6400
chars) written to ``staging/chapter-{N}-bundle.md`` with ``===CH:n===``
chapter-boundary lines and durable ``<!--SCENE-->`` scene-boundary lines.
This module is the SINGLE SOURCE for every marker consumer — the
``pipeline-scene-split`` step (split + promote), G4.cd scene checks, the
G4.cp packability precheck, revision marker-diff revalidation, and
release_split v2's scene-atomic packing. Marker predicates live in
``shenbi.gates.shared`` (layering: pipeline imports gates, never the
reverse); they are re-exported here for consumer convenience.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from shenbi.gates.shared import (
    SCENE_MARKER,
    is_scene_marker_line,
    strip_scene_markers,
    total_chars_md_text,
)

#: Re-exports (single source = gates.shared; listed so type checkers keep them).
__all__ = [
    "CH_MARKER_RE",
    "SCENE_INDEPENDENT_BAND",
    "SCENE_MARKER",
    "SCENE_PAIRED_BAND",
    "BundleChapters",
    "SceneSpan",
    "SceneSplitError",
    "SplitChapter",
    "chapter_total_chars",
    "count_scene_markers",
    "is_scene_marker_line",
    "pack_scenes",
    "parse_scene_declarations",
    "split_bundle",
    "strip_scene_markers",
    "validate_split",
]

#: Chapter-boundary marker — staging bundle only, stripped on promotion.
CH_MARKER_RE = re.compile(r"^===CH:(\d+)===$")

#: Scene-size domains (spec #72 施工面 2 two-type rule):
#: 独立型 [1800, 2000] packs alone as one 更; 配对型 [900, 1400] packs in
#: adjacent pairs. The open interval [1400, 1800) is the planning-fragile
#: gray zone — banned, splitter-enforced.
SCENE_INDEPENDENT_BAND = (1800, 2000)
SCENE_PAIRED_BAND = (900, 1400)

#: Memo scene-budget declaration line (planning SKILL contract):
#: ``- 场景1: 1900字｜独立型｜收束钩：<hook text>``
_SCENE_DECL_RE = re.compile(
    r"^-\s*场景(\d+):\s*(\d+)字｜(独立型|配对型)｜收束钩：(.+?)\s*$",
    re.MULTILINE,
)


class SceneSplitError(RuntimeError):
    """Structural bundle failure (missing/malformed markers) — exit 1 class."""


@dataclass(frozen=True)
class SceneSpan:
    """One marker-delimited scene of a split chapter."""

    index: int  # 0-based within the chapter
    size: int  # non-whitespace chars of the scene text
    last_line: str  # final non-empty line — the declared hook lands here


@dataclass(frozen=True)
class SplitChapter:
    """One chapter extracted from a staging bundle."""

    number: int
    title: str  # second H1's text (v1 release_split title convention)
    body: str  # chapter text: CH marker stripped, SCENE markers KEPT
    scenes: tuple[SceneSpan, ...]


@dataclass(frozen=True)
class BundleChapters:
    """1-2 chapters from one bundle (singleton at volume ends)."""

    chapters: tuple[SplitChapter, ...]


def count_scene_markers(text: str) -> int:
    """Standalone SCENE marker lines in ``text``."""
    return sum(1 for ln in text.split("\n") if is_scene_marker_line(ln))


def chapter_total_chars(text: str) -> int:
    """Chapter word-band count: total_chars 口径, markers/meta stripped.

    Same expression as the G4.cd final check (single counting surface via
    ``gates.shared.total_chars_md_text`` — SCENE marker lines excluded there).
    """
    return total_chars_md_text(text)


def parse_scene_declarations(memo_text: str) -> list[tuple[int, int, str, str]]:
    """Declared scene budgets from a planning memo.

    Returns ``[(场景序号, 字数, 型别, 钩原文), ...]``; empty list when the
    memo carries no scene-budget block (pre-#72 memos).
    """
    return [
        (int(m.group(1)), int(m.group(2)), m.group(3), m.group(4))
        for m in _SCENE_DECL_RE.finditer(memo_text)
    ]


def _h1s(lines: list[str]) -> list[str]:
    return [ln for ln in lines if ln.startswith("# ")]


def _split_chapter_section(number: int, section_lines: list[str]) -> SplitChapter:
    """One CH section → SplitChapter (scenes segmented at marker lines)."""
    h1_lines = _h1s(section_lines)
    if len(h1_lines) < 2:
        raise SceneSplitError(f"===CH:{number}=== 段无第二个 H1（章题提取失败）")
    title = h1_lines[1].lstrip("#").strip()

    marker_idx = [i for i, ln in enumerate(section_lines) if is_scene_marker_line(ln)]
    # Scene k spans (marker_k, next marker | first trailing meta H2 | EOF).
    trailing_meta = next(
        (
            i
            for i, ln in enumerate(section_lines)
            if ln.startswith("## ") and i > (marker_idx[-1] if marker_idx else -1)
        ),
        len(section_lines),
    )
    scenes: list[SceneSpan] = []
    for k, start in enumerate(marker_idx):
        end = marker_idx[k + 1] if k + 1 < len(marker_idx) else trailing_meta
        seg = [ln for ln in section_lines[start + 1 : end] if ln.strip()]
        if not seg:
            raise SceneSplitError(f"===CH:{number}=== 场景{k + 1} 为空段（连续标记或标记贴尾部）")
        nonws = sum(len(re.sub(r"\s", "", ln)) for ln in seg)
        scenes.append(SceneSpan(index=k, size=nonws, last_line=seg[-1].strip()))

    body = "\n".join(section_lines)
    return SplitChapter(number=number, title=title, body=body, scenes=tuple(scenes))


def split_bundle(bundle_text: str) -> BundleChapters:
    """Split a staging bundle at ``===CH:n===`` lines.

    Raises :class:`SceneSplitError` on missing/malformed/duplicate markers.
    """
    lines = bundle_text.split("\n")
    sections: dict[int, list[str]] = {}
    order: list[int] = []
    current: int | None = None
    for ln in lines:
        m = CH_MARKER_RE.match(ln.strip())
        if m:
            current = int(m.group(1))
            if current in sections:
                raise SceneSplitError(f"CH 标记重复: ===CH:{current}===")
            sections[current] = []
            order.append(current)
            continue
        if current is not None:
            sections[current].append(ln)
    if not order:
        raise SceneSplitError("bundle 无任何 ===CH:n=== 标记")
    if order != sorted(order):
        raise SceneSplitError(f"CH 标记章号非升序: {order}")
    if order != list(range(order[0], order[0] + len(order))):
        raise SceneSplitError(f"CH 标记章号不连续: {order}")
    chapters = tuple(_split_chapter_section(n, sections[n]) for n in order)
    if len(chapters) > 2:
        raise SceneSplitError(f"bundle 章数 {len(chapters)} > 2（场景簇契约）")
    return BundleChapters(chapters=chapters)


def _scene_domain_violations(ch: SplitChapter) -> list[str]:
    issues: list[str] = []
    for s in ch.scenes:
        in_ind = SCENE_INDEPENDENT_BAND[0] <= s.size <= SCENE_INDEPENDENT_BAND[1]
        in_pair = SCENE_PAIRED_BAND[0] <= s.size <= SCENE_PAIRED_BAND[1]
        if not (in_ind or in_pair):
            issues.append(
                f"scene_domain:ch{ch.number}:场景{s.index + 1}={s.size} 落灰域/域外"
                f"（合法域 [1800,2000]∪[900,1400]）"
            )
    return issues


def _composition_violations(ch: SplitChapter, band: tuple[int, int]) -> list[str]:
    """Chapter-level composition rule (spec #72).

    2-scene chapter: both independent-type, sum in [3600, 4000].
    3-scene chapter: three paired-type OR one independent + two paired,
    sum inside the band.
    """
    issues: list[str] = []
    total = sum(s.size for s in ch.scenes)
    if not (band[0] <= total <= band[1]):
        issues.append(f"chapter_band:ch{ch.number}:章和 {total} 不在带 [{band[0]},{band[1]}]")
    n = len(ch.scenes)
    if n == 2 and not all(
        SCENE_INDEPENDENT_BAND[0] <= s.size <= SCENE_INDEPENDENT_BAND[1] for s in ch.scenes
    ):
        issues.append(f"composition:ch{ch.number}:2 场景章须两独立型（和 [3600,4000]）")
    if n == 3:
        indep = sum(
            1 for s in ch.scenes if SCENE_INDEPENDENT_BAND[0] <= s.size <= SCENE_INDEPENDENT_BAND[1]
        )
        if not (indep == 0 or indep == 1):
            issues.append(
                f"composition:ch{ch.number}:3 场景章须三配对型或一独两配（独立型 {indep} 个）"
            )
    return issues


def validate_split(ch: SplitChapter, band: tuple[int, int]) -> list[str]:
    """All deterministic chapter-level violations (empty list = clean).

    ``band`` = (min, max) from ``chapter_word`` (total_chars 口径).
    """
    issues: list[str] = []
    total = total_chars_md_text(ch.body)
    if not (band[0] <= total <= band[1]):
        issues.append(f"word_band:ch{ch.number}:total_chars {total} 不在带 [{band[0]},{band[1]}]")
    if len(ch.scenes) < 2:
        issues.append(f"scene_count:ch{ch.number}:场景数 {len(ch.scenes)} < 2")
    issues.extend(_scene_domain_violations(ch))
    issues.extend(_composition_violations(ch, band))
    return issues


def pack_scenes(sizes: list[int], update_band: tuple[int, int]) -> list[list[int]] | None:
    """Greedy scene-run packing for 番茄 更 (spec 施工面 6).

    Groups consecutive scenes so each group's sum lands in ``update_band``.
    Deterministic — the SAME function backs the G4.cp precheck and
    release_split v2, so precheck-pass guarantees v2-pass on the same input.
    Returns the grouping, or ``None`` when the sequence is unpackageable.
    """
    lo, hi = update_band
    groups: list[list[int]] = []
    current: list[int] = []
    for size in sizes:
        if size > hi:
            return None  # single scene can never fit
        if current and sum(current) + size > hi:
            if sum(current) < lo:
                return None  # closing under-weight with no room to extend
            groups.append(current)
            current = []
        current.append(size)
    if current:
        if sum(current) < lo:
            return None
        groups.append(current)
    return groups
