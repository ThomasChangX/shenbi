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
    "deepseek-v4-flash": 1_048_576,
}
# CJK ranges (F523, spec #36 T6'a): Basic + Ext-A + compatibility ideographs
# + fullwidth forms. The old BMP-only range priced Ext-A/fullwidth text at the
# ASCII 4-chars/token ratio, systematically underestimating Chinese prompts.
_CJK_RANGES = (
    (0x3400, 0x4DBF),  # CJK Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
    (0xFF00, 0xFFEF),  # Fullwidth Forms
)

# F523: unknown models must NOT fall back optimistically to the flagship
# 1M limit — that silently disabled the overflow warning for misconfigured
# model names. Conservative 128K default instead.
_DEFAULT_CONTEXT_LIMIT = 131_072

_unknown_model_warned = {"armed": True}


def reset_unknown_model_warning() -> None:
    """Test hook: re-arm the one-shot unknown-model fallback warning."""
    _unknown_model_warned["armed"] = True


def _is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return any(start <= cp <= end for start, end in _CJK_RANGES)


def estimate_prompt_tokens(text: str) -> int:
    """Rough token estimate: 1 token ~= 4 chars (ASCII) / 1.5 chars (CJK)."""
    cjk = sum(1 for c in text if _is_cjk(c))
    other = len(text) - cjk
    return int(cjk / 1.5 + other / 4)


def _limit_for(model: str) -> int:
    limit = MODEL_CONTEXT_LIMITS.get(model)
    if limit is None:
        if _unknown_model_warned["armed"]:
            _unknown_model_warned["armed"] = False
            logging.getLogger("shenbi.cost.estimate").warning(
                "context_limit_unknown_model_conservative_fallback",
                extra={"model": model, "fallback_limit": _DEFAULT_CONTEXT_LIMIT},
            )
        return _DEFAULT_CONTEXT_LIMIT
    return limit


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
