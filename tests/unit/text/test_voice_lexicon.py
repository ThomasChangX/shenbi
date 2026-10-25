"""Spec #76 T1: voice lexicon + genre_params domains."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.text.voice_lexicon import (
    ACCOUNTING_VERBS,
    catchphrases_from_card,
    distinct_voice_signals,
)

FIX = Path(__file__).resolve().parents[3] / "tests/fixtures"


@pytest.mark.unit
def test_no_single_char_verbs_in_lexicon() -> None:
    """裸单字排除（「记」在旧九章 8-26 次/章——plan R1 实测）。"""
    assert all(len(v) >= 2 for v in ACCOUNTING_VERBS)


@pytest.mark.unit
def test_catchphrases_extracted_with_annotation_stripping() -> None:
    card = (
        "---\nname: 林烽\nvoice_profile:\n  catchphrases:\n"
        "    - 这笔我先记下。\n    - 折旧完了，人就自由了。（初期）\n---\n\n正文卡。\n"
    )
    assert catchphrases_from_card(card) == ["这笔我先记下", "折旧完了，人就自由了"]


@pytest.mark.unit
def test_distinct_signals_counting() -> None:
    body = "他心里想：这笔我先记下。利息又涨了。这买卖不亏吧？\n他又数了一遍。"
    # catchphrase 命中(1) + 动词族命中(1, 利息) + 自嘲反问(1) = 3；重复 catchphrase 去重
    assert distinct_voice_signals(body, ["这笔我先记下"]) == 3


@pytest.mark.unit
def test_distinct_signals_empty_body() -> None:
    assert distinct_voice_signals("他推门。", ["这笔我先记下"]) == 0


@pytest.mark.unit
def test_genre_params_domains() -> None:
    import json

    from shenbi.contracts.skills.genre_config import GenreConfig

    base = json.loads((Path("novel-xinghuo-vol1/genre-config.json")).read_text(encoding="utf-8"))
    mp = base["market_params"]
    # 现值合法
    GenreConfig.model_validate(base)
    # quote_type_quota 可选键合法加入
    ok = dict(base, market_params=dict(mp, quote_type_quota={"burning_per_volume": 2}))
    GenreConfig.model_validate(ok)
    # 越域三例
    for key, sub, val in (
        ("voice_density_min", "min_per_chapter", 9),
        ("meme_quota", "per_volume", 0),
        ("quote_type_quota", "burning_per_volume", 11),
    ):
        bad = dict(base, market_params=dict(mp, **{key: {sub: val}}))
        with pytest.raises(ValueError, match=key):
            GenreConfig.model_validate(bad)
