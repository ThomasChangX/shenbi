"""Word-floor unification on genre-config chapter_word (probe3 P1).

probe3: genre-config declared 1400/1700/4500 with a note claiming G4/G2 read
it; chapter_drafting G4/G2.7/G6 did (escalation #9), but length_normalizing
hardcoded 3000/10000 and the chapter_loop WARN hardcoded 4000/15000 — three
different regimes over the same chapter. All sites must read the SAME
config, falling back to their legacy constants when it is absent.
"""

from __future__ import annotations

import json

import pytest

from shenbi.gates.g4.length_normalizing import g4_length_normalizing
from shenbi.pipeline.chapter_loop import _check_word_count_bounds


def _write_config(tmp_path, default=1700, mn=1400, mx=4500):
    (tmp_path / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": default, "min": mn, "max": mx}}),
        encoding="utf-8",
    )


def _report(n_chars: int) -> str:
    # The counting 口径 strips the 归一化报告 meta section (boundary: next
    # heading or EOF) — the normalized chapter body must sit OUTSIDE it.
    return "字" * n_chars + "\n\n## 归一化报告\n\n扩写完成。\n"


@pytest.mark.unit
def test_length_normalizing_floor_follows_genre_config(tmp_path):
    _write_config(tmp_path)
    report = tmp_path / "report.md"
    report.write_text(_report(2000), encoding="utf-8")

    result = g4_length_normalizing(["report.md"], rd=str(tmp_path), project_dir=str(tmp_path))
    assert '"status": "PASS"' in result, result


@pytest.mark.unit
def test_length_normalizing_ceiling_follows_genre_config(tmp_path):
    _write_config(tmp_path)
    report = tmp_path / "report.md"
    report.write_text(_report(4600), encoding="utf-8")

    result = g4_length_normalizing(["report.md"], rd=str(tmp_path), project_dir=str(tmp_path))
    assert "above_ceiling" in result and "4500" in result, result


@pytest.mark.unit
def test_length_normalizing_legacy_fallback_without_config(tmp_path):
    report = tmp_path / "report.md"
    report.write_text(_report(2000), encoding="utf-8")

    result = g4_length_normalizing(["report.md"], rd=str(tmp_path), project_dir=str(tmp_path))
    assert "below_floor" in result and "3000" in result, result


@pytest.mark.unit
def test_chapter_loop_bounds_follow_genre_config(tmp_path):
    _write_config(tmp_path)
    body = "字" * 2000

    assert _check_word_count_bounds(body, project_dir=tmp_path) == []
    assert any(
        "above_ceiling" in i for i in _check_word_count_bounds("字" * 4600, project_dir=tmp_path)
    )
    assert any(
        "below_floor" in i for i in _check_word_count_bounds("字" * 1300, project_dir=tmp_path)
    )


@pytest.mark.unit
def test_chapter_loop_bounds_legacy_fallback_without_config(tmp_path):
    assert _check_word_count_bounds("字" * 3500, project_dir=tmp_path) != []
    assert any("4000" in i for i in _check_word_count_bounds("字" * 3500, project_dir=tmp_path))
    assert _check_word_count_bounds("字" * 14000, project_dir=tmp_path) == []
