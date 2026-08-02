"""Tests for finish_reason detection in _call_llm_streaming (spec §2.9)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from shenbi.pipeline.dispatch_helper import _call_llm_streaming


def _make_chunk(
    content: str | None = None, finish_reason: str | None = None, usage: Any = None
) -> Any:
    """Build a fake OpenAI streaming chunk."""
    delta = SimpleNamespace(content=content)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], usage=usage)


def test_finish_reason_length_captured():
    """When the final chunk has finish_reason='length', it must be returned."""
    client = MagicMock()
    client.chat.completions.create.return_value = iter(
        [
            _make_chunk(content="Hello "),
            _make_chunk(content="world"),
            _make_chunk(content=None, finish_reason="length"),
        ]
    )
    result, stop_reason, usage, finish_reason = _call_llm_streaming(
        client, "test-model", [{"role": "user", "content": "hi"}]
    )
    assert finish_reason == "length"
    assert result == "Hello world"


def test_finish_reason_stop_captured():
    """Normal completion has finish_reason='stop'."""
    client = MagicMock()
    client.chat.completions.create.return_value = iter(
        [
            _make_chunk(content="Done"),
            _make_chunk(content=None, finish_reason="stop"),
        ]
    )
    result, stop_reason, usage, finish_reason = _call_llm_streaming(
        client, "test-model", [{"role": "user", "content": "hi"}]
    )
    assert finish_reason == "stop"


def test_finish_reason_content_filter_captured():
    """content_filter finish_reason must be surfaced (spec §5.1 C2)."""
    client = MagicMock()
    client.chat.completions.create.return_value = iter(
        [
            _make_chunk(content="some "),
            _make_chunk(content=None, finish_reason="content_filter"),
        ]
    )
    result, stop_reason, usage, finish_reason = _call_llm_streaming(
        client, "test-model", [{"role": "user", "content": "hi"}]
    )
    assert finish_reason == "content_filter"


def test_finish_reason_none_when_no_choices():
    """When chunks have no choices, finish_reason stays None."""
    client = MagicMock()
    client.chat.completions.create.return_value = iter(
        [
            SimpleNamespace(choices=[], usage=None),
        ]
    )
    result, stop_reason, usage, finish_reason = _call_llm_streaming(
        client, "test-model", [{"role": "user", "content": "hi"}]
    )
    assert finish_reason is None
