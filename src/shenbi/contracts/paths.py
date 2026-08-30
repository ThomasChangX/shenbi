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
from dataclasses import dataclass


class UnresolvedPathError(ValueError):
    """Path contains a chapter/volume placeholder but no context was provided."""


_BOUND_N = re.compile(r"(?<=[-/])N(?=[-./]|$)")
_NNN = "NNN"

PATH_CONTEXT_PREFIX = "[path-context]"

# Family-prefixed N: arc-N / stratum-N / volume-N / chapter-N / escalation-N
_FAMILY_N = re.compile(r"(?<=[-/])(arc|stratum|volume|chapter|escalation)-N(?=[-./]|$)")
_AC_ANCHOR = re.compile(r"(?<=[-/])AC-NNN(?=[-./]|$)")
_CTX_KEYS = ("chapter", "arc", "stratum", "volume", "anchor", "escalation")


@dataclass(frozen=True)
class PathContext:
    """Per-family placeholder values carried alongside (or inside, via the
    ``[path-context]`` prompt line) a dispatch.

    ``int | str`` sentinel fields allow book-level markers (e.g.
    ``escalation="genesis"`` resolves ``escalation-N-report.md`` to the genesis
    artifact name; ``anchor=1`` resolves ``AC-NNN.md`` to ``AC-001.md``).
    """

    chapter: int | None = None
    arc: int | None = None
    stratum: int | None = None
    volume: int | None = None
    anchor: int | str | None = None
    escalation: int | str | None = None


def format_path_context(ctx: PathContext) -> str:
    """Render the cross-route carrier line (empty when ctx carries no values)."""
    parts = [f"{k}={getattr(ctx, k)}" for k in _CTX_KEYS if getattr(ctx, k) is not None]
    return f"{PATH_CONTEXT_PREFIX} " + " ".join(parts) if parts else ""


_UNSAFE_VALUE_RE = re.compile(r"[/\\]|\.\.")


def parse_path_context(prompt: str) -> PathContext | None:
    r"""Parse the first ``[path-context]`` line of a prompt; None when absent.

    Str-valued sentinel values containing ``/``, ``\\`` or ``..`` are dropped:
    they are substituted into output paths, and a prompt-injected carrier line
    (parse takes the FIRST such line) must not gain path traversal.
    """
    for line in prompt.splitlines():
        s = line.strip()
        if not s.startswith(PATH_CONTEXT_PREFIX):
            continue
        kv: dict[str, int | str] = {}
        for tok in s[len(PATH_CONTEXT_PREFIX) :].split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                if k in _CTX_KEYS:
                    if v.isdecimal():
                        kv[k] = int(v)  # isdecimal: "²" is isdigit-only
                    elif not _UNSAFE_VALUE_RE.search(v):
                        kv[k] = v
        if kv:
            return PathContext(**kv)  # type: ignore[arg-type]
    return None


def build_trigger_context(chapter: int, boundaries: set[int]) -> PathContext:
    """Trigger-fan-out context (memory-distill SKILL: arc N = chapter // 12;
    stratum N = chapter // 36; volume N = count(boundaries <= chapter) — NOT
    len(boundaries), which only agrees at the final volume's end chapter).
    """
    return PathContext(
        chapter=chapter,
        arc=chapter // 12,
        stratum=chapter // 36,
        volume=sum(1 for b in boundaries if b <= chapter),
    )


def resolve_contract_path(path: str, chapter: int | None, ctx: PathContext | None = None) -> str:
    """Resolve N/NNN with per-family semantics when *ctx* is present.

    Family-prefixed N resolves from ctx's family value; AC-NNN from ctx.anchor
    (int -> %03d, str -> literal); everything else falls back to chapter
    semantics (legacy resolve_chapter_path behavior unchanged).
    """
    if ctx is not None:
        m = _FAMILY_N.search(path)
        if m:
            key = m.group(1)
            val = getattr(ctx, key)
            if val is not None:
                # Callable replacement: a str sentinel containing backslash
                # sequences must not be expanded as a re template.
                path = _FAMILY_N.sub(lambda _m: f"{key}-{val}", path, count=1)
                # Co-occurring bare N/NNN still need chapter semantics — delegate
                # (raises UnresolvedPathError when chapter is None, matching the
                # legacy resolve_or_skip filter instead of passing placeholders
                # through).
                return resolve_chapter_path(path, chapter)
        if ctx.anchor is not None and _AC_ANCHOR.search(path):
            pad = f"{ctx.anchor:03d}" if isinstance(ctx.anchor, int) else str(ctx.anchor)
            return resolve_chapter_path(path.replace("AC-NNN", f"AC-{pad}"), chapter)
    return resolve_chapter_path(path, chapter)


def resolve_or_skip_ctx(
    path: str, chapter: int | None, ctx: PathContext | None = None
) -> str | None:
    """resolve_contract_path with the resolve_or_skip genesis-mode filter."""
    try:
        return resolve_contract_path(path, chapter, ctx)
    except UnresolvedPathError:
        return None


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
    """First non-zero chapter reference; 'chapter 0' is a prologue marker,
    not a chapter number (F258).
    """
    for m in re.finditer(r"\bchapter\s+(\d+)\b", text, re.IGNORECASE):
        if int(m.group(1)) > 0:
            return int(m.group(1))
    return None


def resolve_or_skip(path: str, chapter: int | None) -> str | None:
    """Genesis-mode helper: returns None if path has unresolvable placeholder."""
    try:
        return resolve_chapter_path(path, chapter)
    except UnresolvedPathError:
        return None
