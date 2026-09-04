"""T1609 (C28 R3a): bounded-prefix title reads + meta-first no-op fix.

Both extractors anchored ``re.match`` at position 0 — real chapters front-load
a ``## PRE_WRITE_CHECK`` block (H1 at ~line 10), so BOTH returned "" and the
title dedup was a silent full-chain no-op. Fixed to MULTILINE search over a
4KB prefix.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from shenbi.pipeline.chapter_loop import _extract_chapter_title, _load_previous_titles

_FIX = Path(__file__).resolve().parents[2] / "fixtures"


def test_meta_first_fixture_title_extracted() -> None:
    """Real fixture (H1 at ~line 10 after PRE_WRITE_CHECK block)."""
    assert _extract_chapter_title(_FIX / "chapter-7-example.md") != ""


def test_previous_titles_include_meta_first_chapters(tmp_path: Path) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    shutil.copy(_FIX / "chapter-7-example.md", chapters / "chapter-1.md")
    shutil.copy(_FIX / "chapter-8-example.md", chapters / "chapter-2.md")
    titles = _load_previous_titles(tmp_path, 3)
    assert titles  # non-empty: meta-first chapters now contribute titles


def test_title_lookup_read_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.pipeline.helpers.c28_corpus import expand_chapter_corpus

    expand_chapter_corpus(_FIX / "multi-chapter-example", tmp_path, n=56)
    reads = {"n": 0}
    real_read = Path.read_text

    def counting_read(self: Path, *a: object, **k: object) -> str:
        if self.parent.name == "chapters" and self.suffix == ".md":
            reads["n"] += 1
        return real_read(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting_read)
    titles = _load_previous_titles(tmp_path, 56)
    assert len(titles) == 55
    assert reads["n"] == 0  # bounded prefix reads via open("rb"), not read_text


def test_title_lookup_reads_at_most_4kb_per_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R3-1 spec acceptance: title-lookup bytes <= 4096*N (was ~24KB*N).
    n=8 asserts the per-file <=4KB bound (N-scale covered by corpus test).
    """
    from tests.pipeline.helpers.c28_corpus import expand_chapter_corpus

    expand_chapter_corpus(_FIX / "multi-chapter-example", tmp_path, n=8)
    read_bytes = {"n": 0}
    real_open = Path.open

    def bounded_open(self: Path, *a: object, **k: object) -> object:
        fh = real_open(self, *a, **k)  # type: ignore[arg-type]
        if self.suffix == ".md" and self.parent.name == "chapters":
            orig_read = fh.read

            def counting_read(n: int = -1) -> bytes:
                data = orig_read(n)
                read_bytes["n"] += len(data)
                return data

            fh.read = counting_read  # type: ignore[method-assign]
        return fh

    monkeypatch.setattr(Path, "open", bounded_open)
    _load_previous_titles(tmp_path, 8)
    assert read_bytes["n"] <= 4096 * 7  # 7 previous chapters, <=4KB each
