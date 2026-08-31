"""Tests for truth_io.patch_markdown_table_cell (spec #33 T1b-1)."""

from __future__ import annotations

import threading
from pathlib import Path

from shenbi.pipeline.truth_io import patch_markdown_table_cell


def _mk(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


HDR = """| chapter | role | d1 | d2 | d3 | d4 | overall | confidence | human |
|---|---|---|---|---|---|---|---|---|
| 5 | 高潮 | 70 | 65 | 80 | 75 | 72 | high |  |
"""


def test_patch_confidence_cell_on_skill_row(tmp_path: Path) -> None:
    f = tmp_path / "truth" / "resonance_trend.md"
    _mk(f, HDR)
    ok = patch_markdown_table_cell(f, "5", "chapter", 7, "mid")
    assert ok
    line = next(ln for ln in f.read_text(encoding="utf-8").splitlines() if ln.startswith("| 5 "))
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    assert cells[7] == "mid"
    assert cells[0] == "5" and cells[6] == "72"  # other cells untouched


def test_patch_positional_on_headerless_framework_file(tmp_path: Path) -> None:
    f = tmp_path / "truth" / "resonance_trend.md"
    _mk(f, "| 3 | - | - | - | - | - | 61 | - |  |\n")
    assert patch_markdown_table_cell(f, "3", "chapter", 7, "mid")
    assert "| 3 | - | - | - | - | - | 61 | mid |  |" in f.read_text(encoding="utf-8")


def test_short_row_padded(tmp_path: Path) -> None:
    f = tmp_path / "truth" / "t.md"
    _mk(f, "| 7 | x |\n")
    assert patch_markdown_table_cell(f, "7", "chapter", 7, "low")
    line = next(ln for ln in f.read_text(encoding="utf-8").splitlines() if ln.startswith("| 7"))
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    assert len(cells) >= 8 and cells[7] == "low" and cells[1] == "x"


def test_header_and_separator_untouched(tmp_path: Path) -> None:
    f = tmp_path / "truth" / "t.md"
    _mk(f, HDR)
    assert not patch_markdown_table_cell(f, "chapter", "chapter", 7, "mid")
    text = f.read_text(encoding="utf-8")
    assert "| chapter | role |" in text  # header not patched


def test_missing_row_and_file(tmp_path: Path) -> None:
    f = tmp_path / "truth" / "t.md"
    _mk(f, HDR)
    assert not patch_markdown_table_cell(f, "99", "chapter", 7, "mid")
    assert not patch_markdown_table_cell(tmp_path / "truth" / "nope.md", "5", "chapter", 7, "mid")


def test_concurrent_patches_no_lost_update(tmp_path: Path) -> None:
    f = tmp_path / "truth" / "t.md"
    _mk(f, "".join(f"| {n} | - | - | - | - | - | {n} | - |  |\n" for n in range(20)))
    errs: list[Exception] = []

    def worker(n: int) -> None:
        try:
            assert patch_markdown_table_cell(f, str(n), "chapter", 7, f"v{n}")
        except Exception as exc:
            errs.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errs
    text = f.read_text(encoding="utf-8")
    for n in range(20):
        assert f"| {n} | - | - | - | - | - | {n} | v{n} |  |" in text
