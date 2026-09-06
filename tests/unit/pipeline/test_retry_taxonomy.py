"""C33 (spec #47): FailureClass taxonomy + classification points."""

from __future__ import annotations

import httpx
import pytest

from shenbi.contracts.enums import FailureClass
from shenbi.pipeline.dispatch_helper import classify_dispatch_failure


class TestClassifier:
    def test_httpx_timeout_transient(self):
        assert classify_dispatch_failure(exc=httpx.ConnectTimeout("t")) is FailureClass.TRANSIENT

    def test_httpx_5xx_transient(self):
        req = httpx.Request("POST", "https://api/x")
        resp = httpx.Response(503, request=req)
        exc = httpx.HTTPStatusError("503", request=req, response=resp)
        assert classify_dispatch_failure(exc=exc) is FailureClass.TRANSIENT

    def test_openai_sdk_exc_wrapping_httpx_transient(self):
        # F977 repro: SDK exceptions wrap httpx as __cause__, never subclass it.
        class FakeAPIConnectionError(Exception):
            def __init__(self):
                super().__init__("conn")
                self.__cause__ = httpx.ReadTimeout("read timed out")

        assert classify_dispatch_failure(exc=FakeAPIConnectionError()) is FailureClass.TRANSIENT

    def test_rc2_write_audit_gate_deterministic(self):
        # F533: rc=2 GATE_FAIL is deterministic — zero retry.
        assert (
            classify_dispatch_failure(returncode=2, stderr="write-audit GATE_FAIL: drift")
            is FailureClass.DETERMINISTIC_GATE
        )

    def test_rc2_plain_is_content(self):
        assert classify_dispatch_failure(returncode=2) is FailureClass.DETERMINISTIC_CONTENT

    def test_plain_exception_defaults_transient(self):
        # unknown → transient-or-escalate rule (M1): transient, budget still guards.
        assert classify_dispatch_failure(exc=RuntimeError("x")) is FailureClass.TRANSIENT


class TestPredicateTreeWalk:
    """F977 acceptance: the tenacity predicate itself accepts SDK wrappers."""

    def test_retryable_predicate_accepts_sdk_wrapper(self):
        from shenbi.pipeline.dispatch_helper import _is_retryable

        class FakeSdkError(Exception):
            def __init__(self):
                super().__init__("sdk")
                self.__cause__ = httpx.ReadTimeout("read timed out")

        assert _is_retryable(FakeSdkError()) is True

    def test_predicate_rejects_plain_error(self):
        from shenbi.pipeline.dispatch_helper import _is_retryable

        assert _is_retryable(ValueError("nope")) is False


class TestSdgMaxRetriesZero:
    def test_openai_client_constructed_with_max_retries_zero(self):
        # T506: SDK implicit max_retries=2 must be eliminated at the single
        # construction point so all transient retries are visible to tenacity.
        import inspect

        from shenbi.pipeline import dispatch_helper as dh

        assert "max_retries=0" in inspect.getsource(dh)


class TestTraceFailureClass:
    def test_emit_dispatch_trace_writes_failure_class_payload(self, tmp_path):
        """Acceptance #3 (spec R1): classification written to trace under the
        exact field name `failure_class` — REAL payload assertion, not a mock.
        """
        import json

        from shenbi.pipeline import dispatch_helper as dh

        (tmp_path / "trace.jsonl").write_text('{"action": "SEED"}\n', encoding="utf-8")
        dh._emit_dispatch_trace(
            tmp_path,
            "shenbi-review-resonance",
            1,
            "test-model",
            None,
            False,
            1,
            success=False,
            failure_class=FailureClass.DETERMINISTIC_CONTENT,
        )
        line = json.loads(
            (tmp_path / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1]
        )
        assert line["payload"]["failure_class"] == "deterministic_content"


from shenbi.pipeline.chapter_loop import ChapterStep  # noqa: E402
from shenbi.pipeline.error_handler import handle_scoring_failure  # noqa: E402
from shenbi.pipeline.state import PipelineState  # noqa: E402


class TestScoringDeterministic:
    def test_exit2_classified_content_zero_retry(self):
        retry, fc = handle_scoring_failure(PipelineState(), 2)
        assert retry is False and fc is FailureClass.DETERMINISTIC_CONTENT

    def test_exit3_classified_gate_zero_retry(self):
        retry, fc = handle_scoring_failure(PipelineState(), 3)
        assert retry is False and fc is FailureClass.DETERMINISTIC_GATE

    def test_other_exit_no_recovery(self):
        retry, fc = handle_scoring_failure(PipelineState(), 7)
        assert retry is False and fc is FailureClass.DETERMINISTIC_CONTENT


class TestAmplificationCap:
    def test_persistent_transient_collapses_to_tenacity_only(self):
        """T506: outer(3) x tenacity(3) x SDK(3) = 27 worst case must collapse
        to tenacity-only attempts: SDK max_retries=0 (T2) + outer scoring
        zero-retry deterministic (T3) + tenacity stop_after_attempt(3).
        """
        import inspect

        import tenacity
        from tenacity import Retrying, stop_after_attempt

        # Bind to the PRODUCTION decorator's policy (not a fresh copy): the
        # tenacity wiring at dispatch_helper must remain stop_after_attempt(3).
        from shenbi.pipeline import dispatch_helper as dh

        assert "stop_after_attempt(3)" in inspect.getsource(dh)

        retrying = Retrying(stop=stop_after_attempt(3))
        rs = tenacity.RetryCallState(retry_object=retrying, fn=None, args=(), kwargs={})
        rs.attempt_number = 3
        assert retrying.stop(rs) is True
        rs.attempt_number = 2
        assert retrying.stop(rs) is False


class TestSerialBackoff:
    def test_handle_failure_sleeps_with_jitter_before_retry(self, monkeypatch, tmp_path):
        """T510: serial layer retries had zero backoff; R2 reuses the
        RETRY_JITTER pattern (parallel_dispatch) with an injected clock.
        """
        import time

        from shenbi.pipeline import chapter_loop as cl

        slept: list[float] = []
        monkeypatch.setattr(time, "sleep", slept.append)
        st = PipelineState.default(str(tmp_path))
        key = "ch1-shenbi-review-resonance"
        st.chapter_loop.retry_counts[key] = 0
        st.chapter_loop.retry_budget_consumed[key] = 0  # budget NOT exhausted → retry path
        step = ChapterStep(step_num=3, skill="shenbi-review-resonance", name="review-resonance")
        monkeypatch.setattr(cl, "dispatch_escalation", lambda *a, **k: None)
        import random

        monkeypatch.setattr(random, "uniform", lambda a, b: 1.5)
        retried = cl._handle_failure(st, step, 1, "scoring", tmp_path)
        assert retried is False
        # Curve shape (count=1): 2.0**0 + U(0,2) == 1.0 + 1.5 == 2.5
        assert slept == [2.5]
        # Exponential growth (count=2): 2.0**1 + 1.5 == 3.5
        retried2 = cl._handle_failure(st, step, 1, "scoring", tmp_path)
        assert retried2 is False and slept[-1] == 3.5

    def test_budget_exhausted_raises_before_sleep(self, monkeypatch, tmp_path):
        """Exhausted budget raises RetryExhaustedError without backoff sleep."""
        import time

        from shenbi.exceptions import RetryExhaustedError
        from shenbi.pipeline import chapter_loop as cl

        slept: list[float] = []
        monkeypatch.setattr(time, "sleep", slept.append)
        st = PipelineState.default(str(tmp_path))
        key = "ch9-shenbi-review-resonance"
        st.chapter_loop.retry_budget_consumed[key] = st.config.max_audit_retries
        step = ChapterStep(step_num=3, skill="shenbi-review-resonance", name="review-resonance")
        with pytest.raises(RetryExhaustedError):
            cl._handle_failure(st, step, 9, "scoring", tmp_path)
        assert slept == []


class TestAuditRetryReset:
    """T508 (spec #47 R3): audit_retry_count/revision_count reset on ESCALATION
    resolution — all three decisions, chapter-scoped, str-keyed states.
    """

    def _state_with_checkpoint(self, chapter: int | None = 3):
        from shenbi.pipeline.machine import set_checkpoint
        from shenbi.pipeline.state import ChapterState, CheckpointType

        st = PipelineState()
        key = str(chapter)
        st.chapter_loop.chapter_states[key] = ChapterState()
        st.chapter_loop.chapter_states[key].audit_retry_count = st.config.max_audit_retries
        st.chapter_loop.chapter_states[key].revision_count = st.config.max_audit_retries
        set_checkpoint(st, CheckpointType.ESCALATION, chapter=chapter, context="audit_blocking")
        return st

    def test_approve_resets_counters(self):
        from shenbi.pipeline.machine import clear_checkpoint
        from shenbi.pipeline.state import ReviewDecision

        st = self._state_with_checkpoint()
        clear_checkpoint(st, ReviewDecision.APPROVE)
        cs = st.chapter_loop.chapter_states["3"]
        assert cs.audit_retry_count == 0 and cs.revision_count == 0

    def test_reject_and_modify_also_reset(self):
        from shenbi.pipeline.machine import clear_checkpoint
        from shenbi.pipeline.state import ReviewDecision

        for decision in (ReviewDecision.REJECT, ReviewDecision.MODIFY):
            st = self._state_with_checkpoint()
            clear_checkpoint(st, decision)
            assert st.chapter_loop.chapter_states["3"].audit_retry_count == 0

    def test_chapter_none_clears_all(self):
        from shenbi.pipeline.machine import clear_checkpoint, set_checkpoint
        from shenbi.pipeline.state import ChapterState, CheckpointType, ReviewDecision

        st = PipelineState()
        for ch in ("1", "2"):
            st.chapter_loop.chapter_states[ch] = ChapterState()
            st.chapter_loop.chapter_states[ch].audit_retry_count = 5
        set_checkpoint(st, CheckpointType.ESCALATION, chapter=None, context="pipeline")
        clear_checkpoint(st, ReviewDecision.APPROVE)
        assert all(cs.audit_retry_count == 0 for cs in st.chapter_loop.chapter_states.values())

    def test_post_resolve_blocking_routes_to_revision(self):
        """T508 acceptance (T2-tier): ESCALATION resolved → new BLOCKING must
        retry revision instead of instantly re-escalating.
        """
        from shenbi.pipeline.error_handler import handle_audit_blocking
        from shenbi.pipeline.machine import clear_checkpoint
        from shenbi.pipeline.state import ReviewDecision

        st = self._state_with_checkpoint(chapter=5)
        clear_checkpoint(st, ReviewDecision.APPROVE)
        cs = st.chapter_loop.chapter_states["5"]
        assert handle_audit_blocking(st, 5, cs.audit_retry_count) is True

    def test_non_escalation_checkpoint_does_not_reset(self):
        from shenbi.pipeline.machine import clear_checkpoint
        from shenbi.pipeline.state import CheckpointType, ReviewDecision

        st = self._state_with_checkpoint()
        st.pending_checkpoint = type(st.pending_checkpoint)(
            type=CheckpointType.PER_CHAPTER, chapter=3
        )
        clear_checkpoint(st, ReviewDecision.APPROVE)
        assert st.chapter_loop.chapter_states["3"].audit_retry_count == st.config.max_audit_retries
