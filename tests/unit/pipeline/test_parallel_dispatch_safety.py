"""Tests for WRITE_SAFETY classification in parallel dispatch (spec §3.1, §3.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.parallel_dispatch import (
    ReviewTask,
    dispatch_reviews_parallel,
)
from shenbi.pipeline.write_safety import WriteSafety, classify_skill_write_safety


class TestClassification:
    @pytest.mark.parametrize(
        "skill",
        [
            "shenbi-review-anti-ai",
            "shenbi-review-resonance",
            "shenbi-review-arc-payoff",
        ],
    )
    def test_review_skills_are_read_only(self, skill: str):
        assert classify_skill_write_safety(skill) == WriteSafety.READ_ONLY_AUDIT

    @pytest.mark.parametrize(
        "skill",
        [
            "shenbi-state-settling",
            "shenbi-foreshadowing-track",
        ],
    )
    def test_shared_writers_must_serialize(self, skill: str):
        assert classify_skill_write_safety(skill) == WriteSafety.WRITE_SHARED

    def test_unknown_skill_defaults_to_write_shared(self):
        # Conservative: unknown skills must NOT be parallelized.
        assert classify_skill_write_safety("shenbi-something-new") == WriteSafety.WRITE_SHARED


class TestParallelDispatchBoundary:
    def test_read_only_reviews_dispatch_in_parallel(self, tmp_path: Path):
        """Read-only review tasks dispatch without error (boundary allows them)."""
        tasks = [
            ReviewTask(
                skill="shenbi-review-anti-ai",
                project_dir=tmp_path,
                prompt="x",
                output_path="audits/c-1-anti-ai.md",
            )
        ]
        # assert_parallelizable must not raise for review skills.
        from shenbi.pipeline.parallel_dispatch import assert_parallelizable

        assert_parallelizable(tasks)  # no exception

    def test_write_shared_skill_rejected_from_parallel_path(self, tmp_path: Path):
        """A write-shared skill on the parallel path raises immediately."""
        tasks = [
            ReviewTask(
                skill="shenbi-state-settling",  # WRITE_SHARED
                project_dir=tmp_path,
                prompt="x",
                output_path="truth/current_state.md",
            )
        ]
        with pytest.raises(ValueError, match="WRITE_SHARED"):
            dispatch_reviews_parallel(tasks)
