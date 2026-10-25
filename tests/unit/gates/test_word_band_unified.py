"""spec #72 T2: floor=min / ceiling=max / total_chars 口径 unification.

Four-way band consistency (2800/2799/4000/4001), floor fallback chain
(min → default → constant), SCENE-marker exclusion from all counting, and
the 3300 保量 math (ceil=3125 / 0.95x3200 >= 10M/3300 / _implied_total).
All inputs are constructed in tmp_path (G0.9 structural exemption, spec §4).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

from shenbi.gates.g2 import gate_G2
from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting
from shenbi.gates.g4.length_normalizing import g4_length_normalizing
from shenbi.gates.shared import (
    chapter_word_floor,
    is_scene_marker_line,
    strip_scene_markers,
    total_chars_md_text,
)
from shenbi.pipeline.volume_budget import _implied_total

CW = {"default": 3200, "min": 2800, "max": 4000}


def _project(tmp_path: Path, cw: dict[str, int] | None = CW) -> Path:
    if cw is not None:
        (tmp_path / "genre-config.json").write_text(
            json.dumps({"chapter_word": cw}), encoding="utf-8"
        )
    return tmp_path


def _h1(n: int) -> str:
    return f"# 第{n}章：题"


def _nonws(s: str) -> int:
    return len(re.sub(r"\s", "", s))


def _chapter(tmp_path: Path, n: int, body_chars: int, *, markers: int = 0) -> Path:
    """Chapter whose total_chars (post-strip) == body_chars exactly.

    Real anatomy (probe13 fixtures): PRE block on top, then the H1 (its
    boundary ends the PRE strip), prose, POST at tail. PRE/POST are stripped
    by strip_narrative_body; marker lines must be stripped by the #72 marker
    exclusion (T2); the H1's non-whitespace chars count, so the body is
    shortened accordingly (plan T2 constructor-calibration note).
    """
    d = tmp_path / "chapters"
    d.mkdir(exist_ok=True)
    h1 = _h1(n)
    parts = ["## PRE_WRITE_CHECK", "", "- x", "", h1, ""]
    for _ in range(markers):
        parts += ["<!--SCENE-->", ""]
    parts.append("灯" * (body_chars - _nonws(h1)))
    parts += ["", "## POST_WRITE_SELF_CHECK", "", "- y", ""]
    f = d / f"chapter-{n}.md"
    f.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return f


def _ln_chapter(tmp_path: Path, n: int, body_chars: int) -> Path:
    """Length-normalized chapter shape (## 归一化报告 present)."""
    d = tmp_path / "chapters"
    d.mkdir(exist_ok=True)
    h1 = _h1(n)
    f = d / f"chapter-{n}.md"
    f.write_text(
        "## PRE_WRITE_CHECK\n\n- x\n\n"
        + h1
        + "\n\n"
        + "灯" * (body_chars - _nonws(h1))
        + "\n\n## 归一化报告\n\n- mode: expand\n",
        encoding="utf-8",
    )
    return f


def _statuses(result: str) -> tuple[set[str], dict[str, str]]:
    """(pass_ids, fail_id→expected-string) from a gate JSON string."""
    data = json.loads(result)
    ok = {c["id"] for c in data.get("checks", []) if c.get("s") == "PASS"}
    bad: dict[str, str] = {}
    for m in data.get("must_fix", []):
        mid = m["id"] if isinstance(m, dict) else str(m)
        bad[mid.split(":")[0]] = str(m)
    return ok, bad


# ---- floor source: min with fallback chain ----


@pytest.mark.unit
def test_floor_reads_min(tmp_path: Path) -> None:
    assert (
        chapter_word_floor(_project(tmp_path, {"default": 3200, "min": 2800, "max": 4000})) == 2800
    )


@pytest.mark.unit
def test_floor_fallback_default(tmp_path: Path) -> None:
    assert chapter_word_floor(_project(tmp_path, {"default": 3200, "max": 4000})) == 3200


@pytest.mark.unit
def test_floor_fallback_constant(tmp_path: Path) -> None:
    from shenbi.gates.shared import CHAPTER_WORD_FLOOR

    assert chapter_word_floor(_project(tmp_path, None)) == CHAPTER_WORD_FLOOR


# ---- marker predicate + exclusion ----


@pytest.mark.unit
def test_marker_predicate_single_source() -> None:
    assert is_scene_marker_line("<!--SCENE-->")
    assert is_scene_marker_line("  <!--SCENE-->  ")
    assert not is_scene_marker_line("<!--SCENE--> extra")
    assert not is_scene_marker_line("<!--scene-->")


@pytest.mark.unit
def test_marker_lines_excluded_from_count() -> None:
    text = "灯" * 100 + "\n<!--SCENE-->\n" + "灯" * 100
    assert total_chars_md_text(text) == 200
    assert "<!--SCENE-->" not in strip_scene_markers(text)


# ---- G2 four-way band ----


@pytest.mark.unit
def test_g2_band_four_way(tmp_path: Path) -> None:
    proj = _project(tmp_path)
    for n, chars, g26_fail, g27_fail in (
        (1, 2799, True, False),
        (2, 2800, False, False),
        (3, 4000, False, False),
        (4, 4001, False, True),
    ):
        f = _chapter(tmp_path, n, chars)
        ok, bad = _statuses(gate_G2(str(f), file_type="chapter", project_dir=str(proj)))
        assert ("G2.6" in bad) is g26_fail, (n, chars, bad)
        assert ("G2.7" in bad) is g27_fail, (n, chars, bad)
        assert ("G2.6" in ok) is (not g26_fail)
        # must_fix 字符串形态（fail() helper）不携带 expected 数字——id 级断言即契约


@pytest.mark.unit
def test_marker_lines_excluded_g2(tmp_path: Path) -> None:
    # 2790 body + marker: old behavior counted the 12 marker chars (2802,
    # false pass); #72 exclusion → 2790 → FAIL. Proves G2.6 strips markers.
    proj = _project(tmp_path)
    f = _chapter(tmp_path, 9, 2790, markers=1)
    ok, bad = _statuses(gate_G2(str(f), file_type="chapter", project_dir=str(proj)))
    assert "G2.6" in bad
    assert "G2.6" not in ok


@pytest.mark.unit
def test_g4cd_same_counter_as_g2(tmp_path: Path) -> None:
    proj = _project(tmp_path)
    lo = _chapter(tmp_path, 11, 2799)
    hi = _chapter(tmp_path, 12, 2800)
    _, bad_lo = _statuses(g4_chapter_drafting([str(lo)], project_dir=str(proj)))
    ok_hi, _ = _statuses(g4_chapter_drafting([str(hi)], project_dir=str(proj)))
    assert "G4.word_count" in bad_lo
    assert "G4.word_count" in ok_hi


# ---- G4.ln band ----


@pytest.mark.unit
def test_g4ln_band(tmp_path: Path) -> None:
    proj = _project(tmp_path)
    for n, chars, below, above in (
        (21, 2799, True, False),
        (22, 2800, False, False),
        (23, 4000, False, False),
        (24, 4001, False, True),
    ):
        f = _ln_chapter(tmp_path, n, chars)
        result = g4_length_normalizing([str(f)], project_dir=str(proj))
        assert ("G4.ln.below_floor" in result) is below, (n, chars)
        assert ("G4.ln.above_ceiling" in result) is above, (n, chars)


# ---- 3300 保量 math ----


@pytest.mark.unit
def test_g03_ceil_3125(tmp_path: Path) -> None:
    proj = tmp_path
    (proj / "novel.json").write_text(
        json.dumps({"target_word_count": 10_000_000}), encoding="utf-8"
    )
    (proj / "genre-config.json").write_text(json.dumps({"chapter_word": CW}), encoding="utf-8")
    implied, default = _implied_total(proj)
    # G0.3 uses the same ceiling-division idiom (g0.py:386-393)
    assert default == 3200
    assert implied == -(-10_000_000 // 3200) == 3125


@pytest.mark.unit
def test_baoliang_inequality() -> None:
    assert 0.95 * 3200 == 3040
    assert 10_000_000 / 3300 <= 3040
    assert math.ceil(10_000_000 / 3300) == 3031  # target_total_chapters 自洽下界


@pytest.mark.unit
def test_loop_bounds_counter(tmp_path: Path) -> None:
    # _check_word_count_bounds: total_chars 口径 + 剥标记（WARN 观测面）
    from shenbi.pipeline.chapter_loop import _check_word_count_bounds

    proj = _project(tmp_path)
    text = "## PRE_WRITE_CHECK\n\n- x\n\n<!--SCENE-->\n\n" + "灯" * 2790 + "\n"
    issues = _check_word_count_bounds(text, project_dir=proj)
    assert any("below_floor" in i for i in issues)  # 2790 < 2800（标记不计入）
    ok_issues = _check_word_count_bounds("灯" * 3200, project_dir=proj)
    assert ok_issues == []
