# tests/pipeline/test_dispatch_helper_glob.py
import tempfile
from pathlib import Path

from shenbi.pipeline.dispatch_helper import _resolve_read_path


def test_glob_wildcard_expands():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        char_dir = project_dir / "characters" / "major"
        char_dir.mkdir(parents=True)
        (char_dir / "protagonist.md").write_text("protagonist", encoding="utf-8")
        (char_dir / "antagonist.md").write_text("antagonist", encoding="utf-8")

        paths = _resolve_read_path(project_dir, "characters/major/*.md")
        assert len(paths) == 2, f"Expected 2 files, got {len(paths)}: {paths}"
        names = {p.name for p in paths}
        assert names == {"protagonist.md", "antagonist.md"}


def test_glob_non_wildcard_returns_single():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        f = project_dir / "test.md"
        f.write_text("test", encoding="utf-8")

        paths = _resolve_read_path(project_dir, "test.md")
        assert len(paths) == 1
        assert paths[0].name == "test.md"


def test_glob_missing_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        paths = _resolve_read_path(project_dir, "nonexistent/*.md")
        assert paths == []
