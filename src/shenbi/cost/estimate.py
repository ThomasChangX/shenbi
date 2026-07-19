"""Pre-flight prompt token estimate + context-overflow warning (spec §3.4).

Rough heuristic only — ~4 chars/token for ASCII, ~1.5 chars/token for CJK.
Used to WARN before an assembled prompt risks exceeding the model context
window (expensive API failure). Not a hard gate.
"""

from __future__ import annotations

import logging
from typing import Any

# Warn when estimated prompt tokens exceed this fraction of the model limit.
CONTEXT_WARN_FRACTION = 0.8

# Conservative per-model context limits (prompt tokens). Unknown models fall
# back to the default entry.
MODEL_CONTEXT_LIMITS: dict[str, int] = {
    "deepseek-v4-pro": 128_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
}
_DEFAULT_CONTEXT_LIMIT = 128_000

# CJK Unified Ideographs range, used to pick the denser char/token ratio.
_CJK_START = 0x4E00
_CJK_END = 0x9FFF


def estimate_prompt_tokens(text: str) -> int:
    """Rough token estimate: 1 token ~= 4 chars (ASCII) / 1.5 chars (CJK)."""
    cjk = sum(1 for c in text if _CJK_START <= ord(c) <= _CJK_END)
    other = len(text) - cjk
    return int(cjk / 1.5 + other / 4)


def _limit_for(model: str) -> int:
    return MODEL_CONTEXT_LIMITS.get(model, _DEFAULT_CONTEXT_LIMIT)


def warn_if_over_budget(prompt: str, model: str, logger: Any = None) -> bool:
    """Log a warning if *prompt* exceeds 80% of *model*'s context limit.

    Returns True if a warning was emitted, False otherwise.
    """
    log = logger or logging.getLogger("shenbi.cost.estimate")
    limit = _limit_for(model)
    estimated = estimate_prompt_tokens(prompt)
    threshold = int(limit * CONTEXT_WARN_FRACTION)
    if estimated > threshold:
        log.warning(
            "prompt_approaching_context_limit",
            extra={
                "estimated_tokens": estimated,
                "context_limit": limit,
                "warn_fraction": CONTEXT_WARN_FRACTION,
                "model": model,
            },
        )
        return True
    return False
