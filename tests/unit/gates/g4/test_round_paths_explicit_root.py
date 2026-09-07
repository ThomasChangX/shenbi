# spec #48 C34 (RoundPaths.read explicit fallback): rd-miss fallback to
# project_dir must be observable (structlog debug event) and strict mode must
# raise instead of falling back. Checkers construct explicit double roots.

import json
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from shenbi.paths import RoundPaths


def _rp(tmp_path: Path) -> tuple[RoundPaths, Path, Path]:
    rd = tmp_path / "rd"
    pd = tmp_path / "pd"
    rd.mkdir()
    pd.mkdir()
    (pd / "target.md").write_text("x", encoding="utf-8")
    rp = RoundPaths(round_dir=rd, project_dir=pd, repo_root=tmp_path)
    return rp, rd, pd


def test_read_fallback_logs_event(tmp_path):
    rp, rd, pd = _rp(tmp_path)
    (rd / "hit.md").write_text("y", encoding="utf-8")
    with capture_logs() as logs:
        assert rp.read("hit.md") == (rd / "hit.md").resolve()
    assert not [e for e in logs if e.get("event") == "round_paths_read_fallback"]
    with capture_logs() as logs:
        assert rp.read("target.md") == (pd / "target.md").resolve()
    assert [e for e in logs if e.get("event") == "round_paths_read_fallback"]


def test_read_strict_raises_on_rd_miss(tmp_path):
    rp, rd, pd = _rp(tmp_path)
    with pytest.raises(FileNotFoundError):
        rp.read("target.md", strict=True)


def test_read_rd_hit_strict_ok(tmp_path):
    rp, rd, pd = _rp(tmp_path)
    (rd / "hit.md").write_text("y", encoding="utf-8")
    assert rp.read("hit.md", strict=True) == (rd / "hit.md").resolve()


def test_checkers_read_fallback_walks(tmp_path):
    # Real checker code path: target md only in project_dir — checker must
    # resolve it via the (now logged) explicit fallback.
    from shenbi.gates.g4 import pacing_design

    rd = tmp_path / "rd"
    pd = tmp_path / "pd"
    (pd / "config").mkdir(parents=True)
    (pd / "config" / "genre-config.json").write_text(json.dumps({"pacing": {}}), encoding="utf-8")
    fps = ["pacing-plan.md"]
    (pd / "pacing-plan.md").write_text("# 计划\n", encoding="utf-8")
    with capture_logs() as logs:
        result = pacing_design.g4_pacing_design(fps, str(rd), str(pd), str(tmp_path))
    assert isinstance(result, str)
    assert [e for e in logs if e.get("event") == "round_paths_read_fallback"]
