"""Dispatch payload constructors for tests (spec #92 T6).

Replaces hand-written ``=== path ===`` blocks and dispatch/decisions dicts.
First consumers: the highest-frequency dict-construction files (see spec);
adopt gradually elsewhere — do NOT mass-migrate.
"""

from __future__ import annotations

from typing import Any


def file_block(path: str, body: str) -> str:
    """Render one ``=== <path> ===`` file block as skills emit them."""
    return f"=== {path} ===\n{body}"


def payload(skill: str, **fields: Any) -> dict[str, Any]:
    """Build a dispatch-shaped dict (``skill`` header + fields)."""
    p: dict[str, Any] = {"skill": skill}
    p.update(fields)
    return p


def decisions_payload(
    skill: str,
    chapter: int,
    produced_at: str = "2026-10-28T00:00:00Z",
    **fields: Any,
) -> dict[str, Any]:
    """Build a ``shenbi-decisions-v1`` document dict (the skeleton tests
    hand-write: $schema + skill + chapter + produced_at, then domain fields).
    """
    p: dict[str, Any] = {
        "$schema": "shenbi-decisions-v1",
        "skill": skill,
        "chapter": chapter,
        "produced_at": produced_at,
    }
    p.update(fields)
    return p
