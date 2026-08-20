"""Tests for WRITE_SAFETY classification in parallel dispatch (spec §3.1, §3.4)."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shenbi.contracts import ContractError
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.parallel_dispatch import (
    MAX_RETRIES,
    ReviewTask,
    dispatch_reviews_parallel,
)
from shenbi.pipeline.write_safety import WriteSafety, classify_skill_write_safety


class TestClassification:
    @pytest.mark.parametrize(
        "skill",
        [
            # F532（C32 R4）：READ_ONLY 的判定依据是契约 writes/updates 只含
            # 技能自己的 audits/ 报告（无共享 truth 写入），不是名字前缀。
            # 旧断言把 review-resonance / review-arc-payoff 一并判 READ_ONLY，
            # 锁死了生产 bug（见 test_shared_truth_review_skills_must_serialize）。
            "shenbi-review-anti-ai",
            "shenbi-review-group-craft",
            "shenbi-review-sensitivity",
        ],
    )
    def test_review_skills_are_read_only(self, skill: str):
        assert classify_skill_write_safety(skill) == WriteSafety.READ_ONLY_AUDIT

    @pytest.mark.parametrize(
        "skill",
        [
            # F532：契约 updates 声明写共享 truth 文件（truth/audit_drift.md、
            # truth/resonance_trend.md、truth/arc_payoff_trend.md）→ 必须串行，
            # 无论技能名是否带 review- 前缀。
            "shenbi-review-resonance",
            "shenbi-review-arc-payoff",
            "shenbi-state-settling",
            "shenbi-foreshadowing-track",
        ],
    )
    def test_shared_truth_review_skills_must_serialize(self, skill: str):
        assert classify_skill_write_safety(skill) == WriteSafety.WRITE_SHARED

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

    def test_review_name_without_contract_is_write_shared(self, monkeypatch: pytest.MonkeyPatch):
        """F532: contract unloadable -> WRITE_SHARED; the review- prefix no longer passes."""

        def _raise(_skill: str) -> None:
            raise ContractError("skill SKILL.md not found")

        monkeypatch.setattr("shenbi.pipeline.write_safety.load_contract", _raise)
        assert (
            classify_skill_write_safety("shenbi-review-missing-contract")
            == WriteSafety.WRITE_SHARED
        )

    def test_contract_without_persisted_writes_is_read_only(self, monkeypatch: pytest.MonkeyPatch):
        """Contract with empty writes/updates -> no persisted writes -> READ_ONLY_AUDIT."""

        def _empty(_skill: str) -> dict[str, list[str]]:
            return {"writes": [], "updates": [], "reads": []}

        monkeypatch.setattr("shenbi.pipeline.write_safety.load_contract", _empty)
        assert classify_skill_write_safety("shenbi-review-ephemeral") == WriteSafety.READ_ONLY_AUDIT


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


class TestAuditWavePartition:
    """F532 (C32 R4): WRITE_SHARED audit skills go to the serial wave.

    review-resonance contract updates truth/audit_drift.md and
    truth/resonance_trend.md -> classified WRITE_SHARED -> chapter_loop's
    audit wave must partition it out to serial dispatch (leaving it in would
    make assert_parallelizable reject the entire wave).
    """

    def test_shared_truth_review_dispatched_serially_not_in_wave(self, tmp_path: Path):
        from shenbi.pipeline.chapter_loop import _FIRST_AUDIT_IDX, run_chapter_step
        from shenbi.pipeline.state import PipelineState

        wave_skills: list[list[str]] = []

        def _fake_parallel(tasks: list[ReviewTask]) -> list[object]:
            wave_skills.append([t.skill for t in tasks])
            return [DispatchResult(True, 0, "{}", "") for _ in tasks]

        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = _FIRST_AUDIT_IDX

        with (
            # Serial members now dispatch through parallel_dispatch.dispatch_skill
            # (inside _dispatch_with_retry, C32 R4 follow-up) — same seam as
            # concurrent-wave members.
            patch(
                "shenbi.pipeline.parallel_dispatch.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            ) as serial_disp,
            patch(
                "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel",
                side_effect=_fake_parallel,
            ),
            patch(
                "shenbi.pipeline.parallel_dispatch.consolidate_review_results",
                return_value=(
                    "# Chapter 1 — Consolidated Review Results\n\n"
                    "- **BLOCKING Issues**: 0\n- **CRITICAL Issues**: 0\n\n"
                    "No BLOCKING or CRITICAL issues found across all reviews.\n"
                ),
            ),
            patch(
                "shenbi.pipeline.chapter_loop.run_gate_g4",
                return_value={"status": "PASS"},
            ),
        ):
            run_chapter_step(state, tmp_path)

        # resonance never rides the concurrent wave...
        assert wave_skills, "parallel wave must have run"
        assert all("shenbi-review-resonance" not in w for w in wave_skills)
        # ...it is dispatched serially instead (keyword form — _dispatch_with_retry
        # calls dispatch_skill(skill=..., project_dir=..., prompt=..., ...)).
        serial_calls = [c.kwargs["skill"] for c in serial_disp.call_args_list]
        assert "shenbi-review-resonance" in serial_calls
        # ...and every task left on the wave is genuinely read-only.
        from shenbi.pipeline.parallel_dispatch import assert_parallelizable

        assert_parallelizable(
            [
                ReviewTask(skill=s, project_dir=tmp_path, prompt="x", output_path="x")
                for w in wave_skills
                for s in w
            ]
        )


@contextmanager
def _serial_dispatch_as(mock: MagicMock) -> Generator[None, None, None]:
    """Patch BOTH dispatch seams with the same mock (no real dispatch).

    The serial WRITE_SHARED path must dispatch through
    ``parallel_dispatch.dispatch_skill`` (inside ``_dispatch_with_retry``);
    ``chapter_loop.dispatch_skill`` is the seam used before the C32 R4
    follow-up and by the non-audit steps. Patching both with one shared mock
    makes these tests fail closed — the exception propagates and the test
    fails — if the serial path ever bypasses the retry wrapper again.
    """
    with (
        patch("shenbi.pipeline.chapter_loop.dispatch_skill", new=mock),
        patch("shenbi.pipeline.parallel_dispatch.dispatch_skill", new=mock),
        patch("shenbi.pipeline.parallel_dispatch.time.sleep"),  # no real backoff
    ):
        yield


class TestSerialDispatchFailureParity:
    """C32 R4 follow-up: serial WRITE_SHARED members get the same failure
    semantics as concurrent-wave members (``_dispatch_with_retry``):

    1. dispatch exceptions are caught and wrapped into a failed
       DispatchResult (batch survives, failure joins consolidation) instead
       of crashing ``run_chapter_step`` / the CLI driver;
    2. failures retry with backoff — MAX_RETRIES + 1 attempts total.
    """

    def _resonance_task(self, tmp_path: Path) -> ReviewTask:
        return ReviewTask(
            skill="shenbi-review-resonance",
            project_dir=tmp_path,
            prompt="Execute review",
            output_path="audits/chapter-1-resonance.md",
        )

    def test_serial_exception_wrapped_as_failed_result(self, tmp_path: Path):
        """A raised exception becomes ok=False, not a crashed batch."""
        from shenbi.pipeline.chapter_loop import _dispatch_serial_reviews

        serial_dispatch = MagicMock(side_effect=OSError("OpenAI() construction failed"))
        with _serial_dispatch_as(serial_dispatch):
            results = _dispatch_serial_reviews([self._resonance_task(tmp_path)], tmp_path)

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.returncode == -1
        assert "OpenAI() construction failed" in result.stderr

    def test_serial_persistent_failure_retries_max_attempts(self, tmp_path: Path):
        """Persistent failure exhausts MAX_RETRIES + 1 attempts before failed."""
        from shenbi.pipeline.chapter_loop import _dispatch_serial_reviews

        serial_dispatch = MagicMock(side_effect=OSError("api down"))
        with _serial_dispatch_as(serial_dispatch):
            results = _dispatch_serial_reviews([self._resonance_task(tmp_path)], tmp_path)

        assert serial_dispatch.call_count == MAX_RETRIES + 1  # 3 attempts
        assert results[0].success is False
        assert "retries exhausted" in results[0].stderr

    def test_serial_transient_failure_retried_then_succeeds(self, tmp_path: Path):
        """A transient exception is retried; the retry's success wins."""
        from shenbi.pipeline.chapter_loop import _dispatch_serial_reviews

        serial_dispatch = MagicMock(
            side_effect=[OSError("transient API hiccup"), DispatchResult(True, 0, "{}", "")]
        )
        with _serial_dispatch_as(serial_dispatch):
            results = _dispatch_serial_reviews([self._resonance_task(tmp_path)], tmp_path)

        assert serial_dispatch.call_count == 2
        assert results[0].success is True

    def test_serial_exception_does_not_crash_wave_and_joins_consolidation(self, tmp_path: Path):
        """End-to-end: the audit wave survives a raising serial member and its
        failure is consolidated (counted as failed) instead of crashing.
        """
        from shenbi.pipeline.chapter_loop import (
            _FIRST_AUDIT_IDX,
            _LAST_AUDIT_IDX,
            run_chapter_step,
        )
        from shenbi.pipeline.state import PipelineState

        captured: list[DispatchResult] = []

        def _capture(results: list[DispatchResult], chapter: int) -> str:
            captured.extend(results)
            return (
                "# Chapter 1 — Consolidated Review Results\n\n"
                "No BLOCKING or CRITICAL issues found across all reviews.\n"
            )

        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = _FIRST_AUDIT_IDX

        serial_dispatch = MagicMock(side_effect=OSError("OpenAI() construction failed"))
        with (
            _serial_dispatch_as(serial_dispatch),
            patch(
                "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel",
                side_effect=lambda tasks: [DispatchResult(True, 0, "{}", "") for _ in tasks],
            ),
            patch(
                "shenbi.pipeline.parallel_dispatch.consolidate_review_results",
                side_effect=_capture,
            ),
            patch(
                "shenbi.pipeline.chapter_loop.run_gate_g4",
                return_value={"status": "PASS"},
            ),
        ):
            run_chapter_step(state, tmp_path)  # must NOT raise

        failed = [r for r in captured if not r.success]
        assert len(failed) == 1  # resonance's failure joined the consolidation
        assert "OpenAI() construction failed" in failed[0].stderr
        # The chapter still advances past the whole audit wave.
        assert state.chapter_loop.step_index == _LAST_AUDIT_IDX + 1
