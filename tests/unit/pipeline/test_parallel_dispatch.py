"""Tests for parallel review dispatch with rate limiting and retry."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.parallel_dispatch import (
    MAX_CONCURRENT_REVIEWS,
    ReviewTask,
    consolidate_review_results,
)


class TestReviewTask:
    def test_review_task_creation(self):
        task = ReviewTask(
            skill="shenbi-review-anti-ai",
            project_dir=Path("/tmp"),
            prompt="Execute review",
            output_path="audits/chapter-5-anti-ai.md",
        )
        assert task.skill == "shenbi-review-anti-ai"
        assert task.output_path == "audits/chapter-5-anti-ai.md"


class TestRateLimiting:
    def test_max_concurrency_is_reasonable(self):
        """MAX_CONCURRENT_REVIEWS should be between 2 and 7."""
        assert 2 <= MAX_CONCURRENT_REVIEWS <= 7


class TestConsolidation:
    def test_consolidate_empty_results(self):
        result = consolidate_review_results([], chapter=5)
        assert "BLOCKING Issues" in result
        assert "0" in result  # zero issues

    def test_consolidate_with_blocking(self, tmp_path: Path):
        from shenbi.pipeline.dispatch_helper import DispatchResult

        reviews = [
            DispatchResult(True, 0, "BLOCKING: character OOC at L23\nCRITICAL: pacing flat", ""),
            DispatchResult(True, 0, "All clear. PASS.", ""),
            DispatchResult(False, -1, "", "API timeout"),
        ]
        result = consolidate_review_results(reviews, chapter=5)
        assert "BLOCKING" in result
        assert "OOC" in result
