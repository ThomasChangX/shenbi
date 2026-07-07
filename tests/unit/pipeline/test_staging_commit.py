"""Tests for staging two-phase commit in auto mode."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import ChapterStep, _advance
from shenbi.pipeline.state import (
    CheckpointType,
    PipelineState,
)


class TestStagingAutoCommit:
    """When checkpoint is auto-skipped, staging files should be committed."""

    def test_chapter_memo_auto_commit(self, tmp_path: Path):
        """Auto mode commits staging when chapter_memo checkpoint skipped."""
        (tmp_path / "staging" / "plans").mkdir(parents=True)
        plan_file = tmp_path / "staging" / "plans" / "chapter-1-plan.md"
        plan_file.write_text("# Chapter 1 plan", encoding="utf-8")

        state = PipelineState(project_dir=str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1
        state.config.chapter_memo_review_required = False

        step = ChapterStep(
            step_num=2,
            skill="shenbi-chapter-planning",
            name="chapter-planning",
            checkpoint=CheckpointType.CHAPTER_MEMO,
            uses_staging=True,
            output_path="plans/chapter-N-plan.md",
        )

        result = _advance(state, 1, step, 1, project_dir=tmp_path)

        # After auto-commit, file should be at final path
        final = tmp_path / "plans" / "chapter-1-plan.md"
        assert final.exists(), "staging file should be committed to final path"
        assert "Chapter 1 plan" in final.read_text(encoding="utf-8")

    def test_staging_missing_file_logs_warning(self, tmp_path: Path):
        """When staging file doesn't exist, commit is skipped with warning."""
        state = PipelineState(project_dir=str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1
        state.config.chapter_memo_review_required = False

        step = ChapterStep(
            step_num=2,
            skill="shenbi-chapter-planning",
            name="chapter-planning",
            checkpoint=CheckpointType.CHAPTER_MEMO,
            uses_staging=True,
            output_path="plans/chapter-N-plan.md",
        )

        # No staging file exists — should not raise
        result = _advance(state, 1, step, 1, project_dir=tmp_path)
        # Should advance without error (commit skipped gracefully)
        assert state.chapter_loop.step_index == 2


class TestDispatchUsesStaging:
    """dispatch_skill should pass uses_staging through to _build_skill_prompt."""

    def test_build_skill_prompt_prefixes_staging(self, tmp_path: Path):
        """When uses_staging=True, output paths are prefixed with staging/."""
        from shenbi.pipeline.dispatch_helper import _build_skill_prompt

        # Create minimal contract fixture
        (tmp_path / "skills" / "shenbi-chapter-planning").mkdir(parents=True)
        (tmp_path / "skills" / "shenbi-chapter-planning" / "SKILL.md").write_text(
            "---\nname: shenbi-chapter-planning\ncontract:\n  reads: []\n  writes:\n    - plans/chapter-N-plan.md\n  updates: []\n---\n# Test",
            encoding="utf-8",
        )

        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            _, _, output_paths = _build_skill_prompt(
                "shenbi-chapter-planning", tmp_path, "test prompt", chapter=5, uses_staging=True
            )
        finally:
            os.chdir(old_cwd)

        assert len(output_paths) > 0
        for p in output_paths:
            assert p.startswith("staging/"), f"Expected staging/ prefix, got {p}"
