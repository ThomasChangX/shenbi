"""Thinking-mode knob wiring (session30 调试②: empty-content dispatches).

deepseek's chat-completions API runs thinking mode by default (effort
high); the reasoning channel draws on the same completion budget — when it
consumes all of max_tokens the content channel returns empty (90+ runs
pinned at exactly the cap with output_length=0). The knob maps
executor_config.toml's optional per-skill ``thinking`` key onto the
official API switch:
- ``disabled`` -> extra_body {"thinking": {"type": "disabled"}}
- ``low``      -> reasoning_effort="low" (light thinking)
- absent/other -> no kwargs (provider default, unchanged behavior)
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_get_skill_thinking_reads_override(monkeypatch: pytest.MonkeyPatch) -> None:
    from shenbi.pipeline import dispatch_helper as dh

    monkeypatch.setattr(
        dh,
        "_executor_config_cache",
        [
            {
                "default": {},
                "overrides": {
                    "shenbi-review-resonance": {"thinking": "disabled"},
                    "shenbi-chapter-drafting": {"thinking": "low"},
                    "shenbi-state-settling": {"temperature": 0.7},
                },
            }
        ],
    )
    assert dh._get_skill_thinking("shenbi-review-resonance") == "disabled"
    assert dh._get_skill_thinking("shenbi-chapter-drafting") == "low"
    # absent key -> None (provider default); unknown value -> None, never a
    # half-guessed API param
    assert dh._get_skill_thinking("shenbi-state-settling") is None
    monkeypatch.setattr(
        dh,
        "_executor_config_cache",
        [{"default": {}, "overrides": {"x": {"thinking": "medium"}}}],
    )
    assert dh._get_skill_thinking("x") is None


def test_thinking_kwargs_map_to_official_api_shapes() -> None:
    from shenbi.pipeline.dispatch_helper import _thinking_kwargs

    assert _thinking_kwargs("disabled") == {"extra_body": {"thinking": {"type": "disabled"}}}
    assert _thinking_kwargs("low") == {"reasoning_effort": "low"}
    assert _thinking_kwargs(None) == {}
