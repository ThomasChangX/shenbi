# tests/unit/test_round_paths.py

import dataclasses

import pytest

from shenbi.paths import RoundPaths


def test_read_prefers_round_dir(tmp_path):
    rd = tmp_path / "round"
    rd.mkdir()
    pd = tmp_path / "project"
    pd.mkdir()
    (rd / "truth").mkdir()
    (pd / "truth").mkdir()
    (rd / "truth" / "current_state.md").write_text("ROUND")
    (pd / "truth" / "current_state.md").write_text("PROJECT")
    rp = RoundPaths(round_dir=rd, project_dir=pd, repo_root=tmp_path)
    assert rp.read("truth/current_state.md").read_text() == "ROUND"


def test_read_falls_back_to_project_dir(tmp_path):
    pd = tmp_path / "project"
    (pd / "truth").mkdir(parents=True)
    (pd / "truth" / "current_state.md").write_text("PROJECT")
    rp = RoundPaths(round_dir=tmp_path / "round", project_dir=pd, repo_root=tmp_path)
    assert rp.read("truth/current_state.md").read_text() == "PROJECT"


def test_write_always_round_dir(tmp_path):
    rd = tmp_path / "round"
    rp = RoundPaths(round_dir=rd, project_dir=tmp_path / "project", repo_root=tmp_path)
    p = rp.write("chapters/chapter-5.md")
    assert str(rd) in str(p)


def test_backup_same_root_as_write(tmp_path):
    rd = tmp_path / "round"
    rp = RoundPaths(round_dir=rd, project_dir=tmp_path / "project", repo_root=tmp_path)
    w = rp.write("truth/current_state.md")
    b = rp.backup("truth/current_state.md")
    assert b == w.with_name(w.name + ".bak")


def test_chapter_substitution(tmp_path):
    rp = RoundPaths(
        round_dir=tmp_path / "round", project_dir=tmp_path / "project", repo_root=tmp_path
    )
    assert "chapter-5" in str(rp.read("chapters/chapter-N.md", chapter=5))


def test_frozen(tmp_path):
    rp = RoundPaths(tmp_path, tmp_path, tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        rp.round_dir = tmp_path  # type: ignore
