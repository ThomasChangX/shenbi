"""Tests for review checklist deterministic precompute (spec #33 T3)."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.gates.shared import word_count_md
from shenbi.pipeline.review_checklist import (
    generate_review_checklist,
    inject_checklist_into_prompt,
)


def _project(tmp_path: Path) -> Path:
    chapters = tmp_path / "chapters"
    chapters.mkdir(exist_ok=True)
    text = Path("tests/fixtures/chapter-2-draft.md")
    if not text.exists():
        text = next(Path("tests/fixtures").glob("chapter-*-draft.md"))
    (chapters / "chapter-2.md").write_text(text.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_transition_budget_uses_word_count_md_denominator(tmp_path: Path) -> None:
    _project(tmp_path)
    cl = generate_review_checklist(tmp_path, 2)
    expected = max(5, word_count_md(tmp_path / "chapters" / "chapter-2.md") // 1000)
    assert cl.transition_budget == expected


def test_precompute_fields_present(tmp_path: Path) -> None:
    _project(tmp_path)
    cl = generate_review_checklist(tmp_path, 2)
    assert cl.transition_count >= 0
    assert cl.ai_marker_hits >= 0
    assert cl.paragraph_cv is None or cl.paragraph_cv >= 0
    assert cl.version == 1


def test_cache_version_mismatch_regenerates(tmp_path: Path) -> None:
    _project(tmp_path)
    generate_review_checklist(tmp_path, 2)
    cache = tmp_path / "context" / "review-checklist-2.json"
    data = json.loads(cache.read_text(encoding="utf-8"))
    del data["version"]  # simulate old-format cache (no version field)
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    cl = generate_review_checklist(tmp_path, 2)
    assert cl.version == 1  # regenerated, not loaded stale


def test_injection_json_carries_precompute(tmp_path: Path) -> None:
    _project(tmp_path)
    cl = generate_review_checklist(tmp_path, 2)
    prompt = inject_checklist_into_prompt("PROMPT", cl)
    assert "transition_count" in prompt
    assert "ai_marker_hits" in prompt
    assert "PROMPT" in prompt
