"""F415-0815 (C28 R3b): content_uniqueness fingerprint cache.

In-process (path, mtime_ns, size) memoization — production G4 runs are
subprocess-per-call (cold per spawn); the benefit lands on in-process
multi-file callers (g5.5 embedded gate_G4 loop, tests) and any future
in-process gate invocation.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4 import chapter_drafting as cd
from tests.pipeline.helpers.c28_corpus import expand_chapter_corpus

_FIX = Path(__file__).resolve().parents[2] / "fixtures"


def test_second_pass_reads_each_chapter_once(tmp_path: Path, monkeypatch: object) -> None:

    expand_chapter_corpus(_FIX / "multi-chapter-example", tmp_path, n=8)
    reads = {"n": 0}
    real = Path.read_text

    def counting(self: Path, *a: object, **k: object) -> str:
        reads["n"] += 1
        return real(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting)  # type: ignore[attr-defined]
    cd._FINGERPRINT_CACHE.clear()
    for i in range(1, 9):
        cd._fingerprint_of(tmp_path / "chapters" / f"chapter-{i}.md")
    first_pass = reads["n"]
    assert first_pass == 8
    for i in range(1, 9):
        cd._fingerprint_of(tmp_path / "chapters" / f"chapter-{i}.md")
    assert reads["n"] == first_pass  # zero new reads: all cache hits


def test_mtime_change_invalidates(tmp_path: Path) -> None:
    import os

    expand_chapter_corpus(_FIX / "multi-chapter-example", tmp_path, n=2)
    ch = tmp_path / "chapters" / "chapter-1.md"
    cd._FINGERPRINT_CACHE.clear()
    fp1 = cd._fingerprint_of(ch)
    st = ch.stat()
    os.utime(ch, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
    fp2 = cd._fingerprint_of(ch)
    assert fp1 is not fp2  # re-derived (content equal, fresh parse)


def test_read_failure_returns_empty_and_uncached(tmp_path: Path) -> None:
    cd._FINGERPRINT_CACHE.clear()  # isolate from alphabetically-earlier tests
    missing = tmp_path / "chapters" / "chapter-404.md"
    assert cd._fingerprint_of(missing) == frozenset()
    assert not cd._FINGERPRINT_CACHE  # failures are never cached
