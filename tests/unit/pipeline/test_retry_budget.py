"""Tests for the durable retry_budget_consumed counter (spec §3.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.exceptions import RetryExhaustedError
from shenbi.pipeline.chapter_loop import ChapterStep, _handle_failure, _reset_retries, _retry_key
from shenbi.pipeline.state import PipelineState


def _state() -> PipelineState:
    s = PipelineState.default(project_dir="/tmp/test")
    s.config.max_audit_retries = 2
    s.config.max_revision_retries = 2
    return s


def _step(skill: str = "shenbi-chapter-drafting") -> ChapterStep:
    return ChapterStep(step_num=1, skill=skill, name="x")


class TestDurableCounter:
    def test_reset_retries_clears_retry_counts_not_budget(self, tmp_path: Path):
        """_reset_retries clears retry_counts but MUST leave retry_budget_consumed."""
        s = _state()
        key = _retry_key(1, "shenbi-chapter-drafting")
        s.chapter_loop.retry_counts[key] = 3
        s.chapter_loop.retry_budget_consumed[key] = 3

        _reset_retries(s, _step(), chapter=1)

        assert key not in s.chapter_loop.retry_counts, "retry_counts should be cleared"
        assert s.chapter_loop.retry_budget_consumed.get(key) == 3, (
            "retry_budget_consumed must NOT be cleared on success (spec §3.1)"
        )

    def test_handle_failure_increments_durable_budget(self, tmp_path: Path, monkeypatch):
        """A G4/dispatch failure increments the durable budget (and retry_counts)."""
        s = _state()
        # keep handle_dispatch_failure returning True so _handle_failure retries
        monkeypatch.setattr(
            "shenbi.pipeline.error_handler.handle_dispatch_failure",
            lambda state, skill, count: True,
        )
        escalated = _handle_failure(s, _step(), chapter=1, failure="gate", project_dir=tmp_path)
        assert escalated is False  # retries, does not escalate yet
        key = _retry_key(1, "shenbi-chapter-drafting")
        assert s.chapter_loop.retry_budget_consumed.get(key, 0) >= 1


class TestBudgetEnforcement:
    def test_exceeding_max_audit_retries_raises(self, tmp_path: Path, monkeypatch):
        """When durable budget exceeds max_audit_retries, RetryExhaustedError is raised."""
        s = _state()
        s.config.max_audit_retries = 2
        key = _retry_key(1, "shenbi-chapter-drafting")
        # Pre-seed budget at the limit so the next failure trips it.
        s.chapter_loop.retry_budget_consumed[key] = 2
        monkeypatch.setattr(
            "shenbi.pipeline.error_handler.handle_dispatch_failure",
            lambda state, skill, count: True,
        )
        with pytest.raises(RetryExhaustedError):
            _handle_failure(s, _step(), chapter=1, failure="gate", project_dir=tmp_path)


class TestStateRoundTrip:
    def test_retry_budget_consumed_serializes(self):
        s = _state()
        s.chapter_loop.retry_budget_consumed = {"ch1-x": 2}
        data = s.to_dict()
        assert data["chapter_loop"]["retry_budget_consumed"] == {"ch1-x": 2}

    def test_retry_budget_consumed_loads_with_default(self):
        # Old state file without the key loads to {} (additive field).
        import json

        s = PipelineState.from_json(
            json.dumps({"version": 1, "project_dir": "/x", "phase": "genesis"})
        )
        assert s.chapter_loop.retry_budget_consumed == {}
