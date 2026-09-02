"""Unified field-level filtering. Replaces 3 divergent matching semantics:
extract_h2_sections (exact), check_fields_exist (exact), lint normalize (lower).
Canonical rule: strip + fold ASCII whitespace AND U+3000 to single ASCII space;
remove zero-width chars (U+200B, U+FEFF, U+200C, U+200D);
apply NFKC normalization (handles fullwidth ASCII, etc.);
do NOT lowercase (preserves Chinese heading semantics).
"""

from __future__ import annotations
import json
import re
import unicodedata

import structlog

log = structlog.get_logger()


def _normalize_ws(s: str) -> str:
    """Normalize whitespace and CJK-specific characters.

    - Replace ideographic space (U+3000) with ASCII space
    - Remove zero-width characters (U+200B, U+FEFF, U+200C, U+200D)
    - Apply NFKC normalization (handles fullwidth ASCII, etc.)
    - Collapse multiple whitespace to single space
    - Strip leading/trailing whitespace
    """
    s = s.replace("\u3000", " ")
    s = "".join(c for c in s if c not in ("\u200b", "\ufeff", "\u200c", "\u200d"))
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", " ", s).strip()


def match_field(declared: str, heading: str) -> bool:
    return _normalize_ws(declared) == _normalize_ws(heading)


def extract_h2_sections(text: str) -> dict[str, str]:
    """Extract H2 section bodies. First occurrence wins on duplicate H2
    headings (F264); `## ` lines inside fenced code blocks are content,
    not headings (F271).
    """
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_body: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            heading = line[3:].strip()
            if current_heading is not None and current_heading not in sections:
                sections[current_heading] = "\n".join(current_body).strip()
            if heading in sections:
                # duplicate H2: first occurrence wins (F264); F233 residual
                # (spec #39 T9) — the skip is disclosed.
                log.warning("duplicate_h2_first_wins", heading=heading)
                current_heading = None
            else:
                current_heading = heading
            current_body = []
        elif current_heading is not None:
            current_body.append(line)
    if current_heading is not None and current_heading not in sections:
        sections[current_heading] = "\n".join(current_body).strip()
    return sections


def _filter_md(text: str, fields: list[str]) -> tuple[str, bool]:
    sections = extract_h2_sections(text)
    matched: dict[str, str] = {}
    for heading, body in sections.items():
        if any(match_field(f, heading) for f in fields):
            matched[heading] = body
    missing = [f for f in fields if not any(match_field(f, h) for h in sections)]
    if missing:
        # AGENTS.md field-level reads contract: ANY declared field missing ->
        # escape hatch returns the full file + WARN (spec #9 R3 / F218).
        log.warning(
            "field_filter_missing_fields",
            missing=missing,
            matched=list(matched.keys()),
            available=list(sections.keys()),
        )
        return text, False
    return "\n\n".join(f"## {h}\n{b}" for h, b in matched.items()), True


def _filter_json(text: str, fields: list[str], path: str) -> tuple[str, bool]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        log.warning("field_filter_json_invalid", path=path)
        return text, False
    if not isinstance(data, dict):
        log.warning("field_filter_json_not_object", path=path)
        return text, False
    projected = {k: v for k, v in data.items() if k in fields}
    missing = [f for f in fields if f not in data]
    if missing:
        # Same any-missing -> full-text + WARN contract as _filter_md (F218).
        log.warning(
            "field_filter_missing_fields",
            path=path,
            missing=missing,
            matched=list(projected.keys()),
            available=list(data.keys()),
        )
        return text, False
    return json.dumps(projected, ensure_ascii=False, indent=2), True


def filter_to_fields(text: str, fields: list[str], path: str) -> tuple[str, bool]:
    """Returns (filtered_text, matched_all). matched=False means the escape
    hatch fired (full file returned; WARN already logged inside).
    """
    if not fields:
        return text, True
    if path.endswith(".md"):
        return _filter_md(text, fields)
    if path.endswith(".json"):
        return _filter_json(text, fields, path)
    # T305 (spec #39 T12): unknown extensions pass through, now disclosed.
    log.warning("field_filter_unknown_extension_passthrough", path=path)
    return text, True
