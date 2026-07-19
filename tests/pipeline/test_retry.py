"""Test tenacity retry with exponential backoff on LLM calls."""

from unittest.mock import MagicMock

import httpx
import pytest
from tenacity import RetryError

from shenbi.pipeline.dispatch_helper import _call_llm_with_retry


class TestLLMRetry:
    def test_retries_on_429(self):
        """Should retry on HTTP 429 (rate limit)."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            httpx.HTTPStatusError(
                "rate limit", request=MagicMock(), response=MagicMock(status_code=429)
            ),
            httpx.HTTPStatusError(
                "rate limit", request=MagicMock(), response=MagicMock(status_code=429)
            ),
            MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))]),
        ]

        result = _call_llm_with_retry(
            mock_client, "test-model", [{"role": "user", "content": "hi"}]
        )
        assert result is not None
        assert mock_client.chat.completions.create.call_count == 3

    def test_retries_on_5xx(self):
        """Should retry on HTTP 500/502/503."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            httpx.HTTPStatusError(
                "server error", request=MagicMock(), response=MagicMock(status_code=500)
            ),
            MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))]),
        ]

        result = _call_llm_with_retry(
            mock_client, "test-model", [{"role": "user", "content": "hi"}]
        )
        assert mock_client.chat.completions.create.call_count == 2

    def test_gives_up_after_3_failures(self):
        """Should raise after 3 consecutive failures."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock(status_code=429)
        )

        with pytest.raises((RetryError, httpx.HTTPStatusError)):
            _call_llm_with_retry(mock_client, "test-model", [{"role": "user", "content": "hi"}])

    def test_no_retry_on_4xx_non_429(self):
        """Should NOT retry on 400/401/403 (client errors)."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = httpx.HTTPStatusError(
            "bad request", request=MagicMock(), response=MagicMock(status_code=400)
        )

        with pytest.raises(httpx.HTTPStatusError):
            _call_llm_with_retry(mock_client, "test-model", [{"role": "user", "content": "hi"}])
        assert mock_client.chat.completions.create.call_count == 1

    def test_retries_on_timeout(self):
        """Should retry on timeout."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            httpx.TimeoutException("timeout"),
            MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))]),
        ]

        result = _call_llm_with_retry(
            mock_client, "test-model", [{"role": "user", "content": "hi"}]
        )
        assert mock_client.chat.completions.create.call_count == 2
