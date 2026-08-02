"""USD pricing per 1M tokens, keyed to the model that actually ran (spec §3.3).

The dispatch path resolves the model as
``os.environ.get("SHENBI_LLM_MODEL", "deepseek-v4-flash")`` — see
``shenbi.pipeline.dispatch_helper`` constants ``_ENV_LLM_MODEL`` /
``_DEFAULT_MODEL``. Pricing MUST use that same default so cost reflects what
ran; do NOT hardcode other models here.
"""

from __future__ import annotations

import os
from typing import Any

# The model the dispatch path defaults to (mirrors dispatch_helper._DEFAULT_MODEL).
DEFAULT_PRICING_MODEL = "deepseek-v4-flash"

#: USD per 1,000,000 tokens (DeepSeek V4 Flash official rates, cache-miss).
#: Update rates when confirmed for the deployment.
#: Unknown models fall back to the default entry (never crash on cost).
PRICING: dict[str, dict[str, float]] = {
    "deepseek-v4-flash": {"input": 0.14 / 1_000_000, "output": 0.28 / 1_000_000},
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
