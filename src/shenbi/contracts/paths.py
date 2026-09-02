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
# F209 (spec #39 T7): NNN replaces only whole N-runs — an unbounded
# str.replace would mis-replace NNN inside longer runs (NNNN → 100N).
_NNN_BOUNDED = re.compile(r"(?<!N)NNN(?!N)")

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

    C13 hardening (spec #39 T7, F207/F208/F228): with a ctx present, a family
    placeholder whose ctx value is None raises UnresolvedPathError instead of
    silently falling back to chapter semantics; ALL occurrences of a family
    placeholder are replaced (not just the first); family and anchor
    substitution are no longer mutually exclusive.
    """
    if ctx is not None:
        m = _FAMILY_N.search(path)
        if m:
            vals: dict[str, int | str] = {}
            for key in {g.group(1) for g in _FAMILY_N.finditer(path)}:
                val = getattr(ctx, key)
                if val is None:
                    # F207: missing family value is an explicit error — the
                    # chapter-semantics fallback silently mis-resolves e.g.
                    # "volume-N" to the chapter number.
                    raise UnresolvedPathError(path)
                vals[key] = val
            # F208: replace every occurrence of every family placeholder.
            # Callable replacement: a str sentinel containing backslash
            # sequences must not be expanded as an re template.
            path = _FAMILY_N.sub(lambda fm: f"{fm.group(1)}-{vals[fm.group(1)]}", path)
        if ctx.anchor is not None:
            anchor_m = _AC_ANCHOR.search(path)
            if anchor_m:
                pad = f"{ctx.anchor:03d}" if isinstance(ctx.anchor, int) else str(ctx.anchor)
                path = _AC_ANCHOR.sub(lambda _m: f"AC-{pad}", path)
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
    result = _NNN_BOUNDED.sub(f"{chapter:03d}", path)
    return _bounded_replace_n(result, chapter)


def resolve_volume_path(path: str, volume: int | None) -> str:
    if volume is None:
        if _BOUND_N.search(path):
            raise UnresolvedPathError(path)
        return path
    return _bounded_replace_n(path, volume)


class AmbiguousChapterError(ValueError):
    """Multiple distinct chapter references where one was required (F234, spec #38)."""


def extract_chapter(text: str, *, strict: bool = False) -> int | None:
    """First non-zero chapter reference; 'chapter 0' is a prologue marker,
    not a chapter number (F258).

    ``strict=True`` raises :class:`AmbiguousChapterError` when the text
    references more than one distinct non-zero chapter — first-match routing
    across an ambiguous prompt is how wrong-chapter dispatches happened
    (F234, spec #38).
    """
    seen: set[int] = set()
    first: int | None = None
    for m in re.finditer(r"\bchapter\s+(\d+)\b", text, re.IGNORECASE):
        n = int(m.group(1))
        if n > 0:
            seen.add(n)
            if first is None:
                first = n
    if strict and len(seen) > 1:
        raise AmbiguousChapterError(f"multiple chapters referenced: {sorted(seen)}")
    return first


def resolve_or_skip(path: str, chapter: int | None) -> str | None:
    """Genesis-mode helper: returns None if path has unresolvable placeholder."""
    try:
        return resolve_chapter_path(path, chapter)
    except UnresolvedPathError:
        return None
