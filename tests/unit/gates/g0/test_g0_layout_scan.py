# spec #48 C34 (F413/F407): G0.3/G0.cc layout scans via detect single-source.
# G0.3's project-root set expands to all detected layouts (skill-output +
# novel-output); G0.cc keeps novel-output-only semantics. Fixtures assembled
# from real tests/fixtures products (G0.9).

import json
import shutil
from pathlib import Path

import pytest

from shenbi.gates import g0
from shenbi.paths import Layout, detect_layout

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


def _novel_project(base: Path) -> Path:
    proj = base / "novel-output" / "proj-x"
    proj.mkdir(parents=True)
    shutil.copy(FIXTURES / "genre-config-example.json", proj / "genre-config.json")
    return proj


def test_layout_project_roots_filters_by_layout(tmp_path):
    _novel_project(tmp_path)
    so = tmp_path / "skill-output" / "proj-y"
    so.mkdir(parents=True)
    shutil.copy(FIXTURES / "genre-config-example.json", so / "genre-config.json")
    both = g0._layout_project_roots(tmp_path, frozenset({Layout.NOVEL_OUTPUT, Layout.SKILL_OUTPUT}))
    novel_only = g0._layout_project_roots(tmp_path, frozenset({Layout.NOVEL_OUTPUT}))
    assert sorted(p.name for p in both) == ["proj-x", "proj-y"]
    assert [p.name for p in novel_only] == ["proj-x"]


def test_layout_project_roots_sorted_and_container_excluded(tmp_path):
    _novel_project(tmp_path)
    roots = g0._layout_project_roots(
        tmp_path, frozenset({Layout.NOVEL_OUTPUT, Layout.SKILL_OUTPUT})
    )
    assert roots == sorted(roots)
    assert tmp_path / "novel-output" not in roots  # container dir never returned
    empty = tmp_path / "novel-output" / "empty-proj"
    empty.mkdir()
    assert empty not in roots  # key-file existence filter (no genre-config)


@pytest.mark.parametrize("gc_default", [2500])
def test_g0_3_reads_novel_output_project(tmp_path, monkeypatch, gc_default):
    # RED today: G0.3 scans skill-output only → silent no-op on novel-output.
    proj = _novel_project(tmp_path)
    gc = json.loads(proj.joinpath("genre-config.json").read_text(encoding="utf-8"))
    gc.setdefault("chapter_word", {})["default"] = gc_default
    proj.joinpath("genre-config.json").write_text(json.dumps(gc), encoding="utf-8")
    seed = tmp_path / "seed.md"
    seed.write_text("# 大纲\n\n目标字数：10000\n", encoding="utf-8")
    monkeypatch.setattr(g0, "PROJECT", tmp_path)
    result = json.loads(g0.gate_G0(str(seed)))
    g03 = [c for c in result["checks"] if c["id"] == "G0.3"]
    assert g03 and g03[0].get("chapter_word_default") == gc_default


def test_detect_upward_walk_to_project(tmp_path):
    proj = _novel_project(tmp_path)
    deep = proj / "chapters" / "ch3"
    deep.mkdir(parents=True)
    assert detect_layout(deep) is Layout.NOVEL_OUTPUT
