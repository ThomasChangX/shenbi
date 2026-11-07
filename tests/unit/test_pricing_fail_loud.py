"""Tests for pricing.py fail-loud on unknown model (spec §5.2 I3)."""

from __future__ import annotations

import pytest

from shenbi.cost.pricing import estimate_cost


def test_known_model_succeeds():
    """The default model must still work."""
    cost = estimate_cost({"prompt_tokens": 1000, "completion_tokens": 500})
    assert cost > 0


def test_unknown_model_raises():
    """Unknown models must raise ValueError, not silently fall back (spec I3).

    Fixture renamed off "deepseek-v4-pro" (spec #98 r2.2): that id is now a
    real priced tier, so it must NOT be used as the unknown-model stand-in.
    """
    with pytest.raises(ValueError, match="unknown model"):
        estimate_cost(
            {"prompt_tokens": 1000, "completion_tokens": 500},
            model="no-such-model-x",
        )
