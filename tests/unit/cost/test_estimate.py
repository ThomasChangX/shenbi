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
            warned = warn_if_over_budget(
                "short", "deepseek-v4-flash", logger=logging.getLogger("t")
            )
        assert warned is False

    def test_huge_prompt_warns(self):
        limit = MODEL_CONTEXT_LIMITS["deepseek-v4-flash"]
        # Build a string whose estimate exceeds 80% of the limit.
        huge = "a" * (limit * 5)  # way over
        warned = warn_if_over_budget(huge, "deepseek-v4-flash", logger=logging.getLogger("t"))
        assert warned is True

    def test_unknown_model_uses_default_no_crash(self):
        # Must not raise on an unknown model.
        warned = warn_if_over_budget(
            "a" * 10000, "totally-unknown-model", logger=logging.getLogger("t")
        )
        assert warned in (True, False)


class TestF523Spec36:
    """C10 spec #36 T6'a: CJK ext-A/fullwidth ranges + conservative fallback."""

    def test_ext_a_and_fullwidth_count_as_cjk(self):
        ext_a = "".join(chr(c) for c in range(0x3400, 0x3400 + 30))
        fullwidth = "ＡＢＣ１２３！"  # fullwidth forms FF00-FFEF
        new = estimate_prompt_tokens(ext_a + fullwidth)
        old_style = int(0 / 1.5 + len(ext_a + fullwidth) / 4)  # BMP-only behavior
        assert new > old_style

    def test_compat_ideographs_count_as_cjk(self):
        compat = "".join(chr(c) for c in range(0xF900, 0xF900 + 10))
        assert estimate_prompt_tokens(compat) == int(10 / 1.5)

    def test_unknown_model_conservative_limit(self):
        from shenbi.cost import estimate

        assert estimate._limit_for("totally-unknown-model") == 131_072

    def test_unknown_model_warns_once(self, caplog):
        from shenbi.cost import estimate

        estimate.reset_unknown_model_warning()
        logger = logging.getLogger("shenbi.cost.estimate")
        with caplog.at_level(logging.WARNING, logger="shenbi.cost.estimate"):
            estimate.warn_if_over_budget("x" * 600_000, "totally-unknown-model", logger=logger)
            estimate.warn_if_over_budget("x" * 600_000, "totally-unknown-model", logger=logger)
        once = [
            r
            for r in caplog.records
            if r.name == "shenbi.cost.estimate" and "conservative" in str(getattr(r, "msg", ""))
        ]
        assert len(once) == 1
        estimate.reset_unknown_model_warning()
