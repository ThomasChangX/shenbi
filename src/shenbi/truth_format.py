"""Single source for truth-file format parsing (spec #85).

Domain split (spec section 2.1): the volume family stays in
``pipeline._shared``; this module owns the truth-file format families
(hook id / thread id / table row / separator row / frontmatter / section
boundary). Zero shenbi dependencies - the only acyclic landing point under
the gates<->pipeline two-way import; both sides may import it top-level.

Forward export: ``iter_sections`` first consumer is #95 T3 settle
windowing (spec section 2.1 r2.1 note).
"""

from __future__ import annotations

import re
from collections.abc import Iterator

_FAMILY_ORDER: tuple[str, ...] = ("MH", "CP", "H", "P")

#: The ONLY family literals in this module — every exported hook regex is
#: derived from this table (single-source invariant, guarded by test).
_FAMILY_SOURCE: dict[str, str] = {
    "MH": r"MH-?\d{1,4}",
    "CP": r"CP-?\d{1,4}",
    "H": r"H-?\d{1,4}",
    "P": r"P\d*-\d{1,4}",
}

_ALL_FAMILIES_SRC = "|".join(_FAMILY_SOURCE[f] for f in _FAMILY_ORDER)

#: Canonical hook id acceptance (spec §1.3), DERIVED from the family table.
#: Lookaround boundaries are the root fix for M1/M2: unbounded ``[HM]\d+``
#: could match from the second character of ``MH01``. Family order puts the
#: long forms first; ``P\d*-`` (compound plant ids like ``P0-4``) last.
#: Bare ``P14`` (no hyphen) has no production evidence and is excluded.
HOOK_ID_RE = re.compile(rf"(?<![A-Za-z0-9-])(?:{_ALL_FAMILIES_SRC})(?![0-9A-Za-z])")

#: Thread/clue ids as written in thread_map: ``A1`` / ``AB12`` / ``D12``.
#: NOTE: carries one capture group (group(1)=id) so ``.pattern`` interpolation
#: into composites inherits that layout (same as truth_io _THREAD_ID_CELL_RE).
THREAD_ID_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Za-z]+\d{1,3})(?![0-9A-Za-z])")

#: Hook-id heading (``### MH01（名）`` / ``### P0-4 TRIGGER 证据``).
#: Two-group contract: group(1)=heading level, group(2)=id — aligned with
#: the LedgerSpec group(2) contract (ledger_archive.py docstring). Block
#: scanners derive with ``re.compile(HOOK_HEADING_RE.pattern, re.MULTILINE)``.
HOOK_HEADING_RE = re.compile(rf"^(#{{2,6}})\s+((?:{_ALL_FAMILIES_SRC}))")


def canon_hook_id(raw: str) -> str:
    """Canonical hook id: ``MH-001`` ≡ ``MH01`` ≡ ``mh1``.

    Family letters uppercased, hyphen dropped, leading zeros stripped, so
    live-form (genesis template), gate-example, and legacy heading keys all
    address the same hook. Non-family ids (``CH1-L1`` local hooks) pass
    through uppercased. Compound ``P0-4`` ids fail the fullmatch and pass
    through uppercased (``P0-4`` is already upper-case so this is the M4
    integral-string identity premise).
    """
    m = re.fullmatch(r"([A-Za-z]+)-?0*(\d+)", raw.strip())
    if not m:
        return raw.strip().upper()
    return f"{m.group(1).upper()}{m.group(2)}"


def split_table_cells(line: str) -> list[str] | None:
    """Split a markdown table row into stripped cells, or None if not a row.

    A table row starts and ends with ``|``. Cell boundaries are the pipes
    themselves, so a key is the FULL cell text — never the first whitespace
    token (T702 fix semantics, migrated verbatim from truth_io).
    """
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")) or len(s) < 2:
        return None
    return [c.strip() for c in s[1:-1].split("|")]


def is_separator_row(cells: list[str]) -> bool:
    """True for a markdown table separator row (``| --- | :---: |``)."""
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split leading frontmatter; return ``(fm_text, body)``.

    ``fm_text`` keeps the ``---`` fences verbatim (byte-exact round trip for
    splice-style consumers); yaml parsing stays with each consumer. Returns
    ``("", text)`` when there is no frontmatter. Carries the truth_io
    ``----`` thematic-break first-line repair: only an exact ``---`` first
    line opens a block. No error modes.
    """
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r \t") != "---":
        return ("", text)
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r \t") == "---":
            fm = "\n".join(lines[: i + 1]) + "\n"
            body = "\n".join(lines[i + 1 :])
            return (fm, body)
    return ("", text)


def iter_sections(text: str, level: int = 2) -> Iterator[tuple[str, str]]:
    """Yield ``(title, body)`` for ATX sections at exactly ``level``.

    ``level`` interpolates into the compiled pattern (``#{level}``) — it is
    a construction parameter, not a quantifier bound: level=2 yields only
    H2 sections, level=3 only H3 (no H2 ancestors). Blueprint:
    ledger_archive's section-tail slicing.
    """
    heading = re.compile(rf"^#{{{level}}}\s+\S", re.M)
    matches = list(heading.finditer(text))
    for idx, m in enumerate(matches):
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end]
        first_line = block.split("\n", 1)
        title = first_line[0].lstrip("#").strip()
        body = first_line[1] if len(first_line) > 1 else ""
        yield (title, body)


def _family_of(token: str) -> str:
    if token.startswith("MH"):
        return "MH"
    if token.startswith("CP"):
        return "CP"
    if token.startswith("P"):
        return "P"
    return "H"


def find_hook_ids(text: str, families: tuple[str, ...] | None = None) -> list[str]:
    """Scan ``text`` for hook ids; return **canon-normalized** ids in order.

    ``families`` filters by family letters (e.g. ``("MH",)`` keeps the
    MH-only judgment domain of chapter_planning's registry check); None
    accepts all families. Normalized output guarantees both sides of the
    chapter_planning registry/refs reconciliation compare equal strings.
    """
    if families is None:
        return [canon_hook_id(m.group(0)) for m in HOOK_ID_RE.finditer(text)]
    wanted = set(families)
    return [
        canon_hook_id(m.group(0))
        for m in HOOK_ID_RE.finditer(text)
        if _family_of(m.group(0)) in wanted
    ]


def hook_family_source(families: tuple[str, ...]) -> str:
    r"""Regex **source string** for the given hook-id families.

    Returns a single embeddable unit: top-level alternation is wrapped in
    ``(?:...)``, long forms first (``MH|CP|H`` before ``P\\d*-``), hyphen
    slots kept per family. Carries NO boundary assertions — composites
    embed it inside their own anchors/terminators (chapter_planning B-layer
    composite points and the C-layer guarded row-key faces; see spec #85
    §2.3.1 for the site table).
    """
    if not families:
        raise ValueError("families must be non-empty")
    unknown = set(families) - set(_FAMILY_ORDER)
    if unknown:
        raise ValueError(f"unknown hook families: {sorted(unknown)}")
    parts = [_FAMILY_SOURCE[f] for f in _FAMILY_ORDER if f in families]
    if len(parts) == 1:
        return rf"(?:{parts[0]})"
    joined = "|".join(parts)
    return rf"(?:{joined})"
