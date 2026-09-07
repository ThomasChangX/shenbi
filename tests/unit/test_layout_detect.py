# spec #48 C34 (F413/F407): layout detection single-source.
# detect_layout is a pure path-topology function; minimal JSON placeholders
# probe the detection logic only (G0.9 note, plan T1). Content-bearing layout
# fixtures elsewhere copy real tests/fixtures products.

from pathlib import Path

from shenbi.paths import Layout, detect_layout


def _mk(root: Path, layout: str) -> Path:
    proj = root / layout / "proj-x"
    proj.mkdir(parents=True)
    return proj


def test_detect_project_output(tmp_path):
    p = _mk(tmp_path, "rounds/r1")
    (p / "novel.json").write_text("{}", encoding="utf-8")
    assert detect_layout(p) is Layout.PROJECT_OUTPUT


def test_detect_novel_output(tmp_path):
    p = _mk(tmp_path, "novel-output")
    (p / "genre-config.json").write_text("{}", encoding="utf-8")
    assert detect_layout(p) is Layout.NOVEL_OUTPUT


def test_detect_skill_output(tmp_path):
    p = _mk(tmp_path, "skill-output")
    (p / "genre-config.json").write_text("{}", encoding="utf-8")
    assert detect_layout(p) is Layout.SKILL_OUTPUT


def test_detect_none(tmp_path):
    p = _mk(tmp_path, "misc")
    assert detect_layout(p) is Layout.NONE


def test_detect_upward_walk(tmp_path):
    p = _mk(tmp_path, "skill-output")
    (p / "genre-config.json").write_text("{}", encoding="utf-8")
    deep = p / "chapters" / "ch3"
    deep.mkdir(parents=True)
    assert detect_layout(deep) is Layout.SKILL_OUTPUT
