"""Centralized CJK text operations (spec pillar 3)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class TermHit:
    """A single term match found in text."""

    term: str
    start: int
    end: int


def find_terms(text: str, terms: Iterable[str]) -> list[TermHit]:
    r"""Find terms as exact substrings. Replaces broken \w-anchored regex.

    Semantics: exact substring match. For pure CJK text every char position
    is a valid boundary. False-positive handling deferred to integration.
    """
    hits: list[TermHit] = []
    for term in terms:
        if not term:
            continue
        start = 0
        while True:
            idx = text.find(term, start)
            if idx == -1:
                break
            hits.append(TermHit(term=term, start=idx, end=idx + len(term)))
            start = idx + 1
    hits.sort(key=lambda h: h.start)
    return hits
