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


def test_directory_read_expands_to_sorted_md_children():
    """Fixcheck anchor false-unavailable: shenbi-review-resonance declares
    ``benchmarks/anchors/`` (directory form) as a read. The resolver
    returned the DIRECTORY itself, read_text raised IsADirectoryError, and
    the prompt carried a ``[binary or unreadable: ...]`` sentinel — the
    skill then honestly reported anchor_calibration: unavailable for two
    consecutive chapters while AC-001.md sat readable on disk. A directory
    read means "every markdown file inside", sorted.
    """
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        anchors = project_dir / "benchmarks" / "anchors"
        anchors.mkdir(parents=True)
        (anchors / "AC-002.md").write_text("anchor 2", encoding="utf-8")
        (anchors / "AC-001.md").write_text("anchor 1", encoding="utf-8")
        (anchors / "notes.txt").write_text("not markdown", encoding="utf-8")

        paths = _resolve_read_path(project_dir, "benchmarks/anchors/")

        assert [p.name for p in paths] == ["AC-001.md", "AC-002.md"], paths
        assert all(p.is_file() for p in paths)
