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
