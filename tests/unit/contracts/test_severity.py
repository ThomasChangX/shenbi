"""Spec #105 T1: severity single-source module (registry-aligned)."""

from typing import get_args


def test_routing_tier_literal_and_runtime_tuple():
    from shenbi.contracts.severity import ROUTING_TIERS, RoutingTier

    assert get_args(RoutingTier) == ("BLOCKING", "CRITICAL")
    assert ROUTING_TIERS == ("BLOCKING", "CRITICAL")


def test_aggregate_vocab_flattens_and_supersedes_severity():
    from shenbi.contracts.enums import Severity
    from shenbi.contracts.severity import AGGREGATE_VOCAB, AGGREGATE_VOCAB_SET, AggregateVocab

    assert get_args(AggregateVocab) == ("BLOCKING", "CRITICAL", "MINOR", "WARNING", "ERROR")
    assert AGGREGATE_VOCAB == ("BLOCKING", "CRITICAL", "MINOR", "WARNING", "ERROR")
    assert set(get_args(Severity)) <= set(AGGREGATE_VOCAB)  # 子集断言
    assert frozenset(AGGREGATE_VOCAB) == AGGREGATE_VOCAB_SET


def test_hard_tier_aliases_excluded_from_tier_values():
    from shenbi.contracts.severity import ROUTING_HARD_TIER_ALIASES, RoutingTier

    assert ROUTING_HARD_TIER_ALIASES == ("ERROR",)
    assert "ERROR" not in get_args(RoutingTier)  # registry 值集相等契约


def test_bracket_word_groups_pin_the_two_routing_shapes():
    from shenbi.contracts.severity import (
        ROUTING_BLOCKING_BRACKET_WORDS,
        ROUTING_CRITICAL_BRACKET_WORDS,
    )

    # router/parallel_dispatch CRITICAL 形必须只含 CRITICAL|ERROR（I-1：混入 BLOCKING=行为变更）
    assert ROUTING_BLOCKING_BRACKET_WORDS == ("BLOCKING",)
    assert ROUTING_CRITICAL_BRACKET_WORDS == ("CRITICAL", "ERROR")


def test_anchored_forms_match_in_vocab_words_only():
    from shenbi.contracts.severity import (
        AGGREGATE_VOCAB,
        BOLD_ANCHOR_RE,
        BRACKET_ANCHOR_RE,
    )

    assert BRACKET_ANCHOR_RE.search("- [MINOR] something")
    assert not BRACKET_ANCHOR_RE.search("- [MAJOR] something")  # 词表外不入传感域
    assert BOLD_ANCHOR_RE.search("**BLOCKING**")
    assert BOLD_ANCHOR_RE.search("**CRITICAL**")
    for w in AGGREGATE_VOCAB:
        assert BRACKET_ANCHOR_RE.search(f"- [{w}] x")


def test_section_header_re_includes_minor():
    from shenbi.contracts.severity import SECTION_HEADER_RE

    assert SECTION_HEADER_RE.match("## MINOR Findings (3)")
    assert SECTION_HEADER_RE.match("## ERROR Findings (1)")
    assert not SECTION_HEADER_RE.match("## Resonance 报告")


def test_cjk_and_key_name_sets():
    from shenbi.contracts.severity import CJK_SEVERITY_WORDS, KEY_NAME_TOKENS

    assert "严重" in CJK_SEVERITY_WORDS
    assert "严重度" not in CJK_SEVERITY_WORDS  # 裸 key 非 severity 值
    assert frozenset({"SEVERITY", "严重度"}) == KEY_NAME_TOKENS
