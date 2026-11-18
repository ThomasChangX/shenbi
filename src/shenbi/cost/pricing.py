"""USD pricing per 1M tokens, keyed to the model that actually ran (spec §3.3).

This module is the single source for the dispatch-path model constants
(``LLM_MODEL_ENV_VAR`` / ``DEFAULT_PRICING_MODEL``) — the dispatch path
imports them from here (spec #93 T3). Pricing uses that same default so
cost reflects what ran; do NOT hardcode other models here.
"""

from __future__ import annotations

import os
from typing import Any

# The dispatch-path default model — single source (spec #93 T3).
DEFAULT_PRICING_MODEL = "deepseek-v4-flash"

#: USD per 1,000,000 tokens (official rates, cache-miss; spec #98 T1).
#: deepseek-v4-pro / deepseek-flash rates verbatim from the T0 probe report
#: (docs/research/2026-11-07-spec98-t0-tier-probe.md §4-§5: platform page
#: 2026-11-07). deepseek-v4-flash is a retired alias served by V4.1-Flash at
#: Flash prices — its entry stays correct for existing ledgers.
#: Unknown models raise ValueError in estimate_cost (spec §5.2 I3).
#: The ledger wraps this in _safe_estimate_cost to avoid crashing dispatch.
PRICING: dict[str, dict[str, float]] = {
    "deepseek-v4-flash": {"input": 0.14 / 1_000_000, "output": 0.28 / 1_000_000},
    "deepseek-v4-pro": {"input": 0.435 / 1_000_000, "output": 0.87 / 1_000_000},
    "deepseek-flash": {"input": 0.14 / 1_000_000, "output": 0.28 / 1_000_000},
}

# Env var name — single source (spec #93 T3).
LLM_MODEL_ENV_VAR: str = "SHENBI_LLM_MODEL"


def resolve_model(model: str | None = None) -> str:
    """Resolve the model to price: explicit arg > env var > default.

    Mirrors the dispatch path's resolution so pricing matches the run.
    """
    if model is not None:
        return model
    return os.environ.get(LLM_MODEL_ENV_VAR, DEFAULT_PRICING_MODEL)


def estimate_cost(usage: dict[str, Any], model: str | None = None) -> float:
    """Estimate USD cost for a usage dict.

    Args:
        usage: dict with 'prompt_tokens' and 'completion_tokens' (int).
        model: explicit model name; None resolves from env/default.

    Raises:
        ValueError: if the resolved model has no PRICING entry (spec §5.2 I3).
    """
    resolved = resolve_model(model)
    if resolved not in PRICING:
        raise ValueError(
            f"unknown model '{resolved}': no PRICING entry. "
            f"Add it to PRICING or use a known model. "
            f"Known: {list(PRICING.keys())}"
        )
    rates = PRICING[resolved]
    input_cost = int(usage.get("prompt_tokens", 0)) * rates["input"]
    output_cost = int(usage.get("completion_tokens", 0)) * rates["output"]
    return input_cost + output_cost
