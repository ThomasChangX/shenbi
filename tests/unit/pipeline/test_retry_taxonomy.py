"""C33 (spec #47): FailureClass taxonomy + classification points."""

from __future__ import annotations

import httpx

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
