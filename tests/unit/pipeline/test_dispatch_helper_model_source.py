"""Spec #93 T3 — dispatch model constants single-sourced in cost.pricing."""

from __future__ import annotations

import shenbi.pipeline.dispatch_helper as dh
from shenbi.cost import pricing


def test_dispatch_helper_has_no_local_model_constants() -> None:
    assert not hasattr(dh, "_DEFAULT_MODEL")
    assert not hasattr(dh, "_ENV_LLM_MODEL")


def test_dispatch_uses_pricing_single_source() -> None:
    # vars() dict access: direct `dh.<name>` (and, under the pre-commit
    # hook's basedpyright config, getattr(dh, "<name>") too) trips
    # reportPrivateImportUsage on non-re-exported imports; the __dict__
    # identity check stays fully runtime-real.
    dh_names = vars(dh)
    assert dh_names["LLM_MODEL_ENV_VAR"] is pricing.LLM_MODEL_ENV_VAR
    assert dh_names["DEFAULT_PRICING_MODEL"] is pricing.DEFAULT_PRICING_MODEL
