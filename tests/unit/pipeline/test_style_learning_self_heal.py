"""Tests for style-learning self-heal and failure visibility in triggers.py."""

import tempfile
from pathlib import Path

from shenbi.pipeline.triggers import _style_profile_is_stale


def _write_profile(style_dir: Path, confidence: str, sample_count: int) -> Path:
    """Write a style_profile.md with the given bootstrap/mature markers."""
    style_dir.mkdir(parents=True, exist_ok=True)
    profile = style_dir / "style_profile.md"
    profile.write_text(
        f"---\ngeneration_mode: extracted\n"
        f"confidence: {confidence}\nsample_chapter_count: {sample_count}\n---\n\nbody\n"
    )
    return profile


def test_stale_when_bootstrap_and_three_or_more_chapters_done():
    """Self-heal triggers when profile is bootstrap and >=3 chapters exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "chapters").mkdir()
        for n in (1, 2, 3):
            (project_dir / "chapters" / f"chapter-{n}.md").write_text("prose")
        _write_profile(project_dir / "style", confidence="low", sample_count=0)

        assert _style_profile_is_stale(project_dir) is True


def test_not_stale_when_profile_mature():
    """Self-heal does NOT trigger when profile is already mature."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "chapters").mkdir()
        for n in range(1, 11):
            (project_dir / "chapters" / f"chapter-{n}.md").write_text("prose")
        _write_profile(project_dir / "style", confidence="medium", sample_count=6)

        assert _style_profile_is_stale(project_dir) is False


def test_not_stale_when_fewer_than_three_chapters():
    """Self-heal does NOT trigger when fewer than 3 chapters exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "chapters").mkdir()
        (project_dir / "chapters" / "chapter-1.md").write_text("prose")
        _write_profile(project_dir / "style", confidence="low", sample_count=0)

        assert _style_profile_is_stale(project_dir) is False


def test_stale_when_profile_missing_entirely():
    """Self-heal triggers when no style_profile.md exists and >=3 chapters done."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "chapters").mkdir()
        for n in (1, 2, 3):
            (project_dir / "chapters" / f"chapter-{n}.md").write_text("prose")
        # No style dir / profile at all

        assert _style_profile_is_stale(project_dir) is True
