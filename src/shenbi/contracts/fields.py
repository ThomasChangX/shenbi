"""Unified field-level filtering. Replaces 3 divergent matching semantics:
extract_h2_sections (exact), check_fields_exist (exact), lint normalize (lower).
Canonical rule: strip + fold ASCII whitespace AND U+3000 to single ASCII space;
do NOT lowercase (preserves Chinese heading semantics);
do NOT fold zero-width chars (U+200B carries semantic meaning).
"""

from __future__ import annotations
import json
import re
import structlog

log = structlog.get_logger()

# Fold ASCII whitespace + U+3000 (fullwidth space). Explicitly excludes U+200B/200C/200D.
_WS_FOLD = re.compile(r"[\s\u3000]+")


def _normalize_ws(s: str) -> str:
    return _WS_FOLD.sub(" ", s).strip()


def match_field(declared: str, heading: str) -> bool:
    return _normalize_ws(declared) == _normalize_ws(heading)


def extract_h2_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_body).strip()
            current_heading = line[3:].strip()
            current_body = []
        elif current_heading is not None:
            current_body.append(line)
    if current_heading is not None:
        sections[current_heading] = "\n".join(current_body).strip()
    return sections


def _filter_md(text: str, fields: list[str]) -> tuple[str, bool]:
    sections = extract_h2_sections(text)
    matched: dict[str, str] = {}
    for heading, body in sections.items():
        if any(match_field(f, heading) for f in fields):
            matched[heading] = body
    if not matched:
        log.warning("field_filter_no_match", fields=fields, available=list(sections.keys()))
        return text, False
    return "\n\n".join(f"## {h}\n{b}" for h, b in matched.items()), True


def _filter_json(text: str, fields: list[str]) -> tuple[str, bool]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        log.warning("field_filter_json_invalid", path="json")
        return text, False
    if not isinstance(data, dict):
        return text, False
    projected = {k: v for k, v in data.items() if k in fields}
    if not projected:
        log.warning("field_filter_no_match", fields=fields, available=list(data.keys()))
        return text, False
    return json.dumps(projected, ensure_ascii=False, indent=2), True


def filter_to_fields(text: str, fields: list[str], path: str) -> tuple[str, bool]:
    """Returns (filtered_text, matched_any). Caller decides WARN vs FAIL on matched=False."""
    if not fields:
        return text, True
    if path.endswith(".md"):
        return _filter_md(text, fields)
    if path.endswith(".json"):
        return _filter_json(text, fields)
    return text, True
