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
    assert isinstance(cl.ai_marker_hits, dict)
    assert all(v >= 1 for v in cl.ai_marker_hits.values())
    assert cl.paragraph_cv is not None and cl.paragraph_cv >= 0  # real CV, not dead
    assert cl.version == 1


def test_cache_version_mismatch_regenerates(tmp_path: Path) -> None:
    _project(tmp_path)
    generate_review_checklist(tmp_path, 2)
    cache = tmp_path / "context" / "review-checklist-2.json"
    data = json.loads(cache.read_text(encoding="utf-8"))
    del data["version"]  # simulate old-format cache (no version field)
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    # Make the cache mtime NEWER than the source so only the version gate
    # can force regeneration — the actual regression path.
    import os

    src = tmp_path / "chapters" / "chapter-2.md"
    older = src.stat().st_mtime - 100
    os.utime(src, (older, older))
    cl = generate_review_checklist(tmp_path, 2)
    assert cl.version == 1
    on_disk = json.loads(cache.read_text(encoding="utf-8"))
    assert on_disk.get("version") == 1  # cache rewritten, not loaded stale


def test_injection_json_carries_precompute(tmp_path: Path) -> None:
    _project(tmp_path)
    cl = generate_review_checklist(tmp_path, 2)
    prompt = inject_checklist_into_prompt("PROMPT", cl)
    assert "transition_count" in prompt
    assert "ai_marker_hits" in prompt
    assert "PROMPT" in prompt


def test_transition_budget_g4_boundary_alignment(tmp_path: Path) -> None:
    """Acceptance 3: budget equals G4's max(5, wc//1000) at 1000-boundaries."""
    chapters = tmp_path / "chapters"
    chapters.mkdir(exist_ok=True)
    from shenbi.gates.shared import word_count_md

    for n, chars in [(1, 999), (2, 1000), (3, 4999), (4, 6000), (5, 9000)]:
        (chapters / f"chapter-{n}.md").write_text("字" * chars, encoding="utf-8")
    for n in range(1, 6):
        cl = generate_review_checklist(tmp_path, n)
        wc = word_count_md(chapters / f"chapter-{n}.md")
        assert cl.transition_budget == max(5, wc // 1000)
        assert cl.transition_budget >= 5
