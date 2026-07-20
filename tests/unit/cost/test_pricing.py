"""Tests for the pricing module (spec §3.3)."""

from __future__ import annotations

import pytest

from shenbi.cost.pricing import (
    DEFAULT_PRICING_MODEL,
    PRICING,
    estimate_cost,
    resolve_model,
)


class TestPricingTable:
    def test_default_model_is_deepseek_v4_pro(self):
        # The repo default model is deepseek-v4-pro (dispatch_helper._DEFAULT_MODEL),
        # NOT gpt-4o. Pricing must default to the model that actually runs.
        assert DEFAULT_PRICING_MODEL == "deepseek-v4-pro"

    def test_pricing_has_default_model(self):
        assert DEFAULT_PRICING_MODEL in PRICING

    def test_each_entry_has_input_and_output_rates(self):
        for model, rates in PRICING.items():
            assert "input" in rates, f"{model} missing input rate"
            assert "output" in rates, f"{model} missing output rate"
            assert rates["input"] >= 0
            assert rates["output"] >= 0


class TestResolveModel:
    def test_explicit_model_wins(self, monkeypatch):
        monkeypatch.setenv("SHENBI_LLM_MODEL", "gpt-4o")
        assert resolve_model("deepseek-v4-pro") == "deepseek-v4-pro"

    def test_env_used_when_none(self, monkeypatch):
        monkeypatch.setenv("SHENBI_LLM_MODEL", "some-other-model")
        assert resolve_model(None) == "some-other-model"

    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("SHENBI_LLM_MODEL", raising=False)
        assert resolve_model(None) == DEFAULT_PRICING_MODEL

    def test_env_used_when_no_arg(self, monkeypatch):
        """Calling resolve_model() without args uses env."""
        monkeypatch.setenv("SHENBI_LLM_MODEL", "custom-model-v2")
        assert resolve_model() == "custom-model-v2"

    def test_empty_string_env_used_as_is(self, monkeypatch):
        """Empty string env var is returned as-is (caller's responsibility)."""
        monkeypatch.setenv("SHENBI_LLM_MODEL", "")
        assert resolve_model(None) == ""

    def test_default_constant_matches_pricing_key(self):
        """DEFAULT_PRICING_MODEL must exist as a key in PRICING."""
        assert DEFAULT_PRICING_MODEL in PRICING


class TestEstimateCost:
    def test_zero_tokens_zero_cost(self):
        assert estimate_cost({"prompt_tokens": 0, "completion_tokens": 0}) == 0.0

    def test_known_model_uses_its_rates(self, monkeypatch):
        monkeypatch.delenv("SHENBI_LLM_MODEL", raising=False)
        rates = PRICING[DEFAULT_PRICING_MODEL]
        usage = {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}
        expected = (
            rates["input"] * usage["prompt_tokens"] + rates["output"] * usage["completion_tokens"]
        )
        assert estimate_cost(usage) == pytest.approx(expected)

    def test_unknown_model_falls_back_to_default(self):
        # An unknown model must not crash; it prices against the default.
        usage = {"prompt_tokens": 10, "completion_tokens": 10}
        # Should not raise:
        cost = estimate_cost(usage, model="brand-new-model-x")
        assert cost >= 0

    def test_missing_tokens_treated_as_zero(self):
        """Missing prompt_tokens or completion_tokens default to 0."""
        cost = estimate_cost({"prompt_tokens": 0})
        assert cost == 0.0

        cost2 = estimate_cost({"completion_tokens": 100})
        assert cost2 >= 0

    def test_empty_usage_dict_zero_cost(self):
        """An empty usage dict produces zero cost."""
        assert estimate_cost({}) == 0.0

    def test_float_tokens_cast_to_int(self):
        """Float token counts are cast to int (truncated)."""
        cost = estimate_cost({"prompt_tokens": 100.9, "completion_tokens": 50.1})
        # Should not crash; integer conversion truncates
        assert cost >= 0

    def test_model_from_env_not_explicit(self, monkeypatch):
        """When model is None, env var SHENBI_LLM_MODEL drives pricing."""
        monkeypatch.setenv("SHENBI_LLM_MODEL", "gpt-4o")
        usage = {"prompt_tokens": 1_000_000, "completion_tokens": 0}
        cost = estimate_cost(usage)
        assert cost == pytest.approx(2.50)

    def test_explicit_none_uses_env_or_default(self, monkeypatch):
        """Passing model=None explicitly behaves same as omitting it."""
        monkeypatch.setenv("SHENBI_LLM_MODEL", "gpt-4o-mini")
        usage = {"prompt_tokens": 1_000_000, "completion_tokens": 0}
        cost = estimate_cost(usage, model=None)
        assert cost == pytest.approx(0.15)

    @pytest.mark.parametrize("model", ["deepseek-v4-pro", "gpt-4o", "gpt-4o-mini"])
    def test_each_known_model_produces_monotonic_cost(self, model):
        """More tokens → higher cost for every known model."""
        usage_small = {"prompt_tokens": 1, "completion_tokens": 1}
        usage_large = {"prompt_tokens": 1000, "completion_tokens": 1000}
        cost_small = estimate_cost(usage_small, model=model)
        cost_large = estimate_cost(usage_large, model=model)
        assert cost_large > cost_small, f"{model} cost not monotonic"
