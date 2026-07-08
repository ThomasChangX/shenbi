"""NovelConfig: matches the shape of the novel/config doc (g6 consumer).

D26 resolution: the producer writes ``target_word_count`` while the legacy g6.py
consumer reads ``target_words``. The model uses the producer-authoritative name
``target_word_count``; g6.py is adapted to read it in a later task (Task 21).
``extra: forbid`` so any undeclared key surfaces as structural drift.
"""

from __future__ import annotations

from pydantic import BaseModel


class NovelConfig(BaseModel):
    model_config = {"extra": "forbid"}
    title: str = ""
    genre: str = ""
    language: str = "zh"
    era: str = ""
    core_concept: str = ""
    target_word_count: int = 0
    total_chapters: int = 0
    ending_direction: str = ""
    golden_opening_chapters: str = ""
    status: str = ""
    themes: list[str] = []
    mode: str = ""
