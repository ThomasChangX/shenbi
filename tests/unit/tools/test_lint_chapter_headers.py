"""Structural tests for the chapter-header form assertion tool (spec #84 T0-14).

Inputs are constructed inline under tmp_path (G0.9: structural inputs may be
constructed; the shapes mirror on-disk vol2 defect forms — 3-H1 / no-number /
CJK-numeral / English residue).
"""

from __future__ import annotations

from pathlib import Path

from tools.lint_chapter_headers import main

# On-disk adjacency mirrored: ch39/40 carry the date H1 directly adjacent to
# the title H1 (no blank line between them) — keep fixtures faithful (M5).
GOOD = "<!--META-END-->\n\n# 第37章\n\n# 过期四十一天\n\n正文。"
CH39_FORM = "<!--META-END-->\n\n# 第39章\n\n# 正月廿六\n# 数目另议\n\n正文。"  # 3 H1
CH40_FORM = "<!--META-END-->\n\n# 正月廿八\n# 还不起\n\n正文。"  # no chapter number
CH41_FORM = "<!--META-END-->\n\n# 第四十一章\n\n# 勾名\n\n正文。"  # CJK numeral
EN_RESIDUE = "<!--META-END-->\n\n# Chapter 41:\n\n# 第41章\n\n# 勾名\n\n正文。"


def _write(project: Path, name: str, text: str) -> None:
    chapters = project / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    (chapters / name).write_text(text, encoding="utf-8")


def test_good_chapter_passes(tmp_path: Path, capsys) -> None:
    _write(tmp_path, "chapter-37.md", GOOD)
    assert main([str(tmp_path)]) == 0
    assert "OK" in capsys.readouterr().out


def test_three_h1_flagged(tmp_path: Path, capsys) -> None:
    _write(tmp_path, "chapter-39.md", CH39_FORM)
    assert main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "chapter-39.md" in out
    assert "恰一行" in out  # cites the single-title rule


def test_missing_number_flagged(tmp_path: Path, capsys) -> None:
    _write(tmp_path, "chapter-40.md", CH40_FORM)
    assert main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "chapter-40.md" in out
    assert "阿码章号行" in out  # cites the exactly-one-Arabic-number rule


def test_cjk_numeral_flagged(tmp_path: Path, capsys) -> None:
    _write(tmp_path, "chapter-41.md", CH41_FORM)
    assert main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "chapter-41.md" in out
    assert "中文数字" in out or "CJK" in out


def test_english_residue_flagged(tmp_path: Path, capsys) -> None:
    _write(tmp_path, "chapter-42.md", EN_RESIDUE)
    assert main([str(tmp_path)]) == 1
    assert "chapter-42.md" in capsys.readouterr().out


def test_backups_and_sidecars_excluded(tmp_path: Path, capsys) -> None:
    """-pre-rev backups and decisions sidecars never match chapter-<N>.md stems."""
    _write(tmp_path, "chapter-9.md", GOOD.replace("第37章", "第9章").replace("过期四十一天", "题"))
    _write(tmp_path, "chapter-9-pre-rev.md", "garbage with no header at all\n")
    (tmp_path / "chapters" / "chapter-9-decisions.json").write_text("{}", encoding="utf-8")
    assert main([str(tmp_path)]) == 0
    assert "OK" in capsys.readouterr().out


def test_missing_chapters_dir_fails_loud(tmp_path: Path, capsys) -> None:
    assert main([str(tmp_path)]) == 2
    assert "not found" in capsys.readouterr().out


def test_empty_chapters_dir_fails_loud(tmp_path: Path, capsys) -> None:
    """An empty chapters/ dir (no chapter-<N>.md) is exit 2, not a false OK."""
    (tmp_path / "chapters").mkdir()
    assert main([str(tmp_path)]) == 2
    assert "no chapter" in capsys.readouterr().out
