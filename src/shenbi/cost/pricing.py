"""USD pricing per 1M tokens, keyed to the model that actually ran (spec §3.3).

The dispatch path resolves the model as
``os.environ.get("SHENBI_LLM_MODEL", "deepseek-v4-pro")`` — see
``shenbi.pipeline.dispatch_helper`` constants ``_ENV_LLM_MODEL`` /
``_DEFAULT_MODEL``. Pricing MUST use that same default so cost reflects what
ran; do NOT hardcode gpt-4o here.
"""

from __future__ import annotations

import os
from typing import Any

# The model the dispatch path defaults to (mirrors dispatch_helper._DEFAULT_MODEL).
DEFAULT_PRICING_MODEL = "deepseek-v4-pro"

#: USD per 1,000,000 tokens. Update rates when confirmed for the deployment.
#: Unknown models fall back to the default entry (never crash on cost).
PRICING: dict[str, dict[str, float]] = {
    "deepseek-v4-pro": {"input": 1.10 / 1_000_000, "output": 4.40 / 1_000_000},
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
}

# Env var name — must match shenbi.pipeline.dispatch_helper._ENV_LLM_MODEL.
_ENV_LLM_MODEL = "SHENBI_LLM_MODEL"


def resolve_model(model: str | None = None) -> str:
    """Resolve the model to price: explicit arg > env var > default.

    Mirrors the dispatch path's resolution so pricing matches the run.
    """
    if model is not None:
        return model
    return os.environ.get(_ENV_LLM_MODEL, DEFAULT_PRICING_MODEL)


def estimate_cost(usage: dict[str, Any], model: str | None = None) -> float:
    """Estimate USD cost for a usage dict.

    Args:
        usage: dict with 'prompt_tokens' and 'completion_tokens' (int).
        model: explicit model name; None resolves from env/default.

    Unknown models fall back to the DEFAULT_PRICING_MODEL entry.
    """
    resolved = resolve_model(model)
    rates = PRICING.get(resolved, PRICING[DEFAULT_PRICING_MODEL])
    input_cost = int(usage.get("prompt_tokens", 0)) * rates["input"]
    output_cost = int(usage.get("completion_tokens", 0)) * rates["output"]
    return input_cost + output_cost
