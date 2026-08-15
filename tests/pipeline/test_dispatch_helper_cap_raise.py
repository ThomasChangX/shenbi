"""Tests for finish_reason-driven cap-raise and content_filter hard-fail (spec §5.1)."""

from __future__ import annotations

from unittest.mock import MagicMock

from shenbi.pipeline.dispatch_helper import DispatchResult, _dispatch_via_api


def test_length_truncation_triggers_cap_raise_resend(tmp_path, monkeypatch):
    """finish_reason='length' → raise max_tokens and resend once (not same-params)."""
    max_tokens_used: list[int] = []

    call_count = [0]

    def mock_streaming_with_retry(client, model, messages, **kwargs):
        call_count[0] += 1
        max_tokens_used.append(kwargs.get("max_tokens", 16384))
        if call_count[0] == 1:
            # First call: truncated
            return ("truncated output...", None, MagicMock(), "length")
        # Second call (cap-raised): complete
        return ("complete output", None, MagicMock(), "stop")

    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._call_llm_streaming_with_retry",
        mock_streaming_with_retry,
    )
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    # Mock _build_skill_prompt to avoid file I/O
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._build_skill_prompt",
        lambda *a, **kw: ("sys", "user", []),
    )
    # Mock _write_parsed_outputs to avoid file writes
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._write_parsed_outputs",
        lambda *a, **kw: True,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._parse_structured_output",
        lambda text: MagicMock(files=[]),
    )

    _dispatch_via_api("shenbi-chapter-drafting", tmp_path, "test prompt")

    assert call_count[0] == 2  # exactly 2 calls: original + 1 cap-raise resend
    assert max_tokens_used[1] > max_tokens_used[0]  # cap was raised


def test_content_filter_is_hard_fail(tmp_path, monkeypatch):
    """finish_reason='content_filter' → immediate DispatchResult(False), no resend."""
    call_count = [0]

    def mock_streaming_with_retry(client, model, messages, **kwargs):
        call_count[0] += 1
        return ("filtered...", None, MagicMock(), "content_filter")

    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._call_llm_streaming_with_retry",
        mock_streaming_with_retry,
    )
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._build_skill_prompt",
        lambda *a, **kw: ("sys", "user", []),
    )

    result: DispatchResult = _dispatch_via_api("shenbi-chapter-drafting", tmp_path, "test prompt")

    assert call_count[0] == 1  # no resend
    assert result.success is False
    assert "content_filter" in result.stderr


def test_cap_raise_capped_at_model_ceiling(tmp_path, monkeypatch):
    """When cap is already at ceiling (raised_cap <= original_cap), fail-fast with NO resend."""
    call_count = [0]

    def mock_streaming_with_retry(client, model, messages, **kwargs):
        call_count[0] += 1
        return ("truncated...", None, MagicMock(), "length")

    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._call_llm_streaming_with_retry",
        mock_streaming_with_retry,
    )
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._build_skill_prompt",
        lambda *a, **kw: ("sys", "user", []),
    )
    # Simulate post-T3 state: drafting max_tokens = 32768
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._get_skill_max_tokens",
        lambda skill: 32768,
    )
    # Set ceiling = drafting's configured max_tokens so raised_cap (min(cap*2, ceiling*0.9))
    # = min(65536, 29491) = 29491 < 32768 = original_cap → fail-fast, NO resend.
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._MODEL_OUTPUT_CEILING",
        32768,  # == drafting's max_tokens after T3
    )

    result: DispatchResult = _dispatch_via_api("shenbi-chapter-drafting", tmp_path, "test prompt")

    assert call_count[0] == 1  # fail-fast BEFORE any resend (raised_cap <= original_cap)
    assert result.success is False
    assert "ceiling" in result.stderr.lower()


def test_cap_raise_persistent_length_fail_fast(tmp_path, monkeypatch):
    """After cap-raise resend, if STILL length → fail-fast (spec §5.1: max 1 resend)."""
    call_count = [0]

    def mock_streaming_with_retry(client, model, messages, **kwargs):
        call_count[0] += 1
        # Always returns length — even after cap-raise
        return ("still truncated...", None, MagicMock(), "length")

    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._call_llm_streaming_with_retry",
        mock_streaming_with_retry,
    )
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._build_skill_prompt",
        lambda *a, **kw: ("sys", "user", []),
    )
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._write_parsed_outputs",
        lambda *a, **kw: True,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._parse_structured_output",
        lambda text: MagicMock(files=[]),
    )
    # Ceiling high enough that cap-raise DOES fire (65536 > drafting's 32768)
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._MODEL_OUTPUT_CEILING",
        65536,
    )

    result: DispatchResult = _dispatch_via_api("shenbi-chapter-drafting", tmp_path, "test prompt")

    assert call_count[0] == 2  # original + exactly 1 cap-raise resend (then fail-fast)
    assert result.success is False
    assert "still exceeds" in result.stderr.lower() or "persistent" in result.stderr.lower()
