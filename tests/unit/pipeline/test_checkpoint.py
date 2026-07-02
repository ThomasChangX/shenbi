"""Tests for checkpoint staging mechanism.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 2.7.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.checkpoint import (
    clear_staging,
    commit_staging,
    staging_path,
)


class TestStagingPath:
    def test_staging_path_maps_target(self, tmp_project: Path):
        target = "plans/chapter-5-plan.md"
        sp = staging_path(tmp_project, target)
        assert "staging" in str(sp)
        assert sp.name == "chapter-5-plan.md"
        assert sp.parent == tmp_project / "staging" / "plans"

    def test_staging_path_accepts_str_project_dir(self, tmp_project: Path):
        sp = staging_path(str(tmp_project), "truth/world.md")
        assert sp == tmp_project / "staging" / "truth" / "world.md"


class TestCommitStaging:
    def test_commit_staging_copies_files(self, tmp_project: Path):
        sp = staging_path(tmp_project, "plans/chapter-1-plan.md")
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text("# Chapter 1 Plan", encoding="utf-8")

        committed = commit_staging(tmp_project, ["plans/chapter-1-plan.md"])

        assert len(committed) == 1
        target = tmp_project / "plans" / "chapter-1-plan.md"
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "# Chapter 1 Plan"

    def test_commit_multiple_files(self, tmp_project: Path):
        for name in ("truth/world.md", "truth/characters.md"):
            sp = staging_path(tmp_project, name)
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(f"# {name}", encoding="utf-8")

        committed = commit_staging(tmp_project, ["truth/world.md", "truth/characters.md"])

        assert len(committed) == 2
        assert (tmp_project / "truth" / "world.md").read_text(
            encoding="utf-8"
        ) == "# truth/world.md"
        assert (tmp_project / "truth" / "characters.md").read_text(
            encoding="utf-8"
        ) == "# truth/characters.md"

    def test_commit_overwrites_existing_target(self, tmp_project: Path):
        sp = staging_path(tmp_project, "plans/chapter-1-plan.md")
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text("# New Plan", encoding="utf-8")

        target = tmp_project / "plans" / "chapter-1-plan.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Old Plan", encoding="utf-8")

        commit_staging(tmp_project, ["plans/chapter-1-plan.md"])

        assert target.read_text(encoding="utf-8") == "# New Plan"

    def test_commit_nonexistent_staging_raises(self, tmp_project: Path):
        with pytest.raises(FileNotFoundError):
            commit_staging(tmp_project, ["nonexistent.md"])


class TestClearStaging:
    def test_clear_staging_removes_all(self, tmp_project: Path):
        staging_dir = tmp_project / "staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        (staging_dir / "test.md").write_text("test", encoding="utf-8")

        clear_staging(tmp_project)

        assert not staging_dir.exists() or not any(staging_dir.iterdir())

    def test_clear_staging_idempotent_when_absent(self, tmp_project: Path):
        # No staging directory exists yet — clear must not raise.
        clear_staging(tmp_project)
        assert not (tmp_project / "staging").exists()
