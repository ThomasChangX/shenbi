"""Tests for the pre-flight prompt token estimator (spec §3.4)."""

from __future__ import annotations

import logging

from shenbi.cost.estimate import (
    CONTEXT_WARN_FRACTION,
    MODEL_CONTEXT_LIMITS,
    estimate_prompt_tokens,
    warn_if_over_budget,
)


class TestEstimate:
    def test_english_approx_4_chars_per_token(self):
        # 400 chars of ASCII -> ~100 tokens
        toks = estimate_prompt_tokens("a" * 400)
        assert 80 <= toks <= 120

    def test_cjk_uses_smaller_ratio(self):
        # CJK chars are denser: ~1.5 chars/token
        cjk = "中" * 150  # ~100 tokens
        toks = estimate_prompt_tokens(cjk)
        assert 80 <= toks <= 120

    def test_mixed(self):
        text = "a" * 200 + "中" * 75
        toks = estimate_prompt_tokens(text)
        assert toks > 0


class TestContextLimits:
    def test_warn_fraction_is_0_8(self):
        assert CONTEXT_WARN_FRACTION == 0.8

    def test_default_model_has_limit(self):
        from shenbi.cost.pricing import DEFAULT_PRICING_MODEL

        assert DEFAULT_PRICING_MODEL in MODEL_CONTEXT_LIMITS


class TestWarnIfOverBudget:
    def test_small_prompt_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            warned = warn_if_over_budget("short", "deepseek-v4-pro", logger=logging.getLogger("t"))
        assert warned is False

    def test_huge_prompt_warns(self):
        limit = MODEL_CONTEXT_LIMITS["deepseek-v4-pro"]
        # Build a string whose estimate exceeds 80% of the limit.
        huge = "a" * (limit * 5)  # way over
        warned = warn_if_over_budget(huge, "deepseek-v4-pro", logger=logging.getLogger("t"))
        assert warned is True

    def test_unknown_model_uses_default_no_crash(self):
        # Must not raise on an unknown model.
        warned = warn_if_over_budget(
            "a" * 10000, "totally-unknown-model", logger=logging.getLogger("t")
        )
        assert warned in (True, False)
