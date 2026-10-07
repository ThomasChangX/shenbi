r"""Dispatch-layer empty-content resend (phase3 esc#4, ch28 settle).

The provider occasionally returns a zero-byte content stream while billing
a full completion (the tokens ride a reasoning channel — same signature
hit review-group-character at a 67K prompt and self-healed on its next
attempt, while settle's zero-retry policy escalated the same $0.02
transient). The dispatch layer now resends ONCE, mirroring the §5.1
cap-raise topology; a genuinely empty response (zero completion tokens)
is a different failure and must NOT trigger the resend.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import shenbi.pipeline.dispatch_helper as dh


def _usage(completion: int) -> SimpleNamespace:
    return SimpleNamespace(
        completion_tokens=completion, prompt_tokens=10, total_tokens=completion + 10
    )


_GOOD_JSON = '{"files": [{"path": "world/power_system.md", "content": "ok"}], "decisions": null}'


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    import openai

    monkeypatch.setattr(openai, "OpenAI", MagicMock())


def _stream_mock(sequence: list[tuple[str, str, object, str]]) -> MagicMock:
    return MagicMock(side_effect=sequence)


class TestEmptyContentResend:
    def test_empty_with_billed_completion_resends_once_and_succeeds(self, tmp_path: Path) -> None:
        stream = _stream_mock(
            [
                ("", "stop", _usage(12821), "stop"),
                (_GOOD_JSON, "stop", _usage(100), "stop"),
            ]
        )
        monkey_patch = dh._call_llm_streaming_with_retry
        dh._call_llm_streaming_with_retry = stream
        try:
            result = dh._dispatch_via_api("shenbi-power-system", tmp_path, "Execute test.")
        finally:
            dh._call_llm_streaming_with_retry = monkey_patch
        assert stream.call_count == 2
        assert result.success

    def test_persistently_empty_falls_through(self, tmp_path: Path) -> None:
        stream = _stream_mock(
            [("", "stop", _usage(500), "stop"), ("", "stop", _usage(480), "stop")]
        )
        original = dh._call_llm_streaming_with_retry
        dh._call_llm_streaming_with_retry = stream
        try:
            result = dh._dispatch_via_api("shenbi-power-system", tmp_path, "Execute test.")
        finally:
            dh._call_llm_streaming_with_retry = original
        assert stream.call_count == 2  # first try + the single resend
        assert not result.success

    def test_zero_completion_empty_response_does_not_resend(self, tmp_path: Path) -> None:
        stream = _stream_mock([("", "stop", _usage(0), "stop")])
        original = dh._call_llm_streaming_with_retry
        dh._call_llm_streaming_with_retry = stream
        try:
            result = dh._dispatch_via_api("shenbi-power-system", tmp_path, "Execute test.")
        finally:
            dh._call_llm_streaming_with_retry = original
        assert stream.call_count == 1
        assert not result.success
