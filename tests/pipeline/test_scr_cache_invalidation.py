"""C30 R4 SCR cache invalidation + step-output downgrade.

Spec #44 (F310/F1112): the per-chapter SCR cache must invalidate on
(size, mtime_ns) of the chapter file — a revision must never be served the
pre-revision cache; and a step whose declared output is missing must not be
recorded as done.
"""

import os
import shutil
from pathlib import Path

from shenbi.pipeline.scr_extractor import extract_scr

CHAPTER_FIXTURE = Path("tests/fixtures/chapter-2-draft.md")


def _stage_chapter(tmp_path: Path, chapter: int = 2) -> Path:
    (tmp_path / "chapters").mkdir(parents=True, exist_ok=True)
    dest = tmp_path / "chapters" / f"chapter-{chapter}.md"
    shutil.copy(CHAPTER_FIXTURE, dest)
    return dest


def test_scr_cache_invalidated_on_revision(tmp_path: Path) -> None:
    dest = _stage_chapter(tmp_path)
    first = extract_scr(tmp_path, 2)
    dest.write_text(dest.read_text(encoding="utf-8") + "\n新增段落", encoding="utf-8")
    second = extract_scr(tmp_path, 2)
    assert second.extracted_at != first.extracted_at  # re-extracted, not cached


def test_scr_cache_hit_when_unchanged(tmp_path: Path) -> None:
    _stage_chapter(tmp_path)
    first = extract_scr(tmp_path, 2)
    second = extract_scr(tmp_path, 2)
    assert second.extracted_at == first.extracted_at  # cached copy served


def test_cache_key_uses_size_and_mtime(tmp_path: Path) -> None:
    """Same size, different mtime_ns must invalidate (mtime granularity guard)."""
    dest = _stage_chapter(tmp_path)
    first = extract_scr(tmp_path, 2)
    os.utime(dest, ns=(dest.stat().st_atime_ns, dest.stat().st_mtime_ns + 1_000))
    second = extract_scr(tmp_path, 2)
    assert second.extracted_at != first.extracted_at


def test_cache_key_recorded_in_json(tmp_path: Path) -> None:
    _stage_chapter(tmp_path)
    extract_scr(tmp_path, 2)
    import json

    payload = json.loads((tmp_path / "context" / "chapter-2-scr.json").read_text(encoding="utf-8"))
    assert "_cache_key" in payload
    assert {"size", "mtime_ns"} <= set(payload["_cache_key"])
