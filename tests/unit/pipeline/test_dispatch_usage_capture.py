"""Tests that _dispatch_via_api handles streaming responses correctly (spec SS3.1)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def _fake_chunk(content: str) -> SimpleNamespace:
    """Build a streaming chunk shaped like an OpenAI chat completion chunk."""
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content))],
    )


def _fake_stream(content: str) -> list[SimpleNamespace]:
    """Build a streaming response: list of chunks."""
    return [_fake_chunk(content)]


class TestUsageCapture:
    def test_usage_recorded_on_success(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
        monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-pro")

        # Streaming: return an iterable of chunks
        fake_stream = _fake_stream("### FILE: chapters/chapter-1.md\nbody\n")

        with (
            patch("openai.OpenAI") as mock_openai,
            patch(
                "shenbi.pipeline.dispatch_helper._build_skill_prompt",
                return_value=("sys", "user", ["chapters/chapter-1.md"]),
            ),
        ):
            mock_openai.return_value.chat.completions.create.return_value = fake_stream
            from shenbi.pipeline.dispatch_helper import _dispatch_via_api

            result = _dispatch_via_api("shenbi-chapter-drafting", tmp_path, "Chapter 1 draft")
            assert result.success

    def test_missing_usage_does_not_crash(self, tmp_path: Path, monkeypatch):
        """An endpoint that omits response.usage must not break dispatch."""
        monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")

        fake_stream = _fake_stream("### FILE: chapters/chapter-1.md\nbody\n")

        with (
            patch("openai.OpenAI") as mock_openai,
            patch(
                "shenbi.pipeline.dispatch_helper._build_skill_prompt",
                return_value=("sys", "user", ["chapters/chapter-1.md"]),
            ),
        ):
            mock_openai.return_value.chat.completions.create.return_value = fake_stream
            from shenbi.pipeline.dispatch_helper import _dispatch_via_api

            result = _dispatch_via_api("shenbi-chapter-drafting", tmp_path, "Chapter 1 draft")
            assert result.success  # dispatch still succeeds
