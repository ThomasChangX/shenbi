"""Spec #89 T3 narrow helpers: byte-exact degradation strings + oracle triples."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.shared import (
    CHAPTER_NUM_RE,
    chapter_no,
    degrade,
    load_facts_oracle,
)


@pytest.mark.unit
def test_degrade_emission_strings_byte_exact() -> None:
    # 六条逐字快照（cd:668/:695/:740、cp:735、xc:964 五发射点 + cd:706 no_decl 变体）
    assert (
        degrade("no_facts", "props facts absent/empty", "hand-off scan skipped")
        == "no_facts — props facts absent/empty; hand-off scan skipped (degradation visible)"
    )
    assert (
        degrade("no_facts", "counters facts absent/empty", "reconciliation skipped")
        == "no_facts — counters facts absent/empty; reconciliation skipped (degradation visible)"
    )
    assert (
        degrade("no_facts", "props facts absent/empty", "F16 cp legality skipped")
        == "no_facts — props facts absent/empty; F16 cp legality skipped (degradation visible)"
    )
    assert (
        degrade("no_ledger", "particle_ledger.md absent", "balance anchor skipped")
        == "no_ledger — particle_ledger.md absent; balance anchor skipped (degradation visible)"
    )
    assert (
        degrade("no_facts", "identity facts absent/empty", "F15 narration scan skipped")
        == "no_facts — identity facts absent/empty; F15 narration scan skipped (degradation visible)"
    )
    assert (
        degrade(
            "no_decl",
            "memo declares no counters this chapter",
            "reconciliation not activated",
            visible=False,
            tail=" (legacy-memo compat, ch17-class false-red guard)",
        )
        == "no_decl — memo declares no counters this chapter; reconciliation not activated (legacy-memo compat, ch17-class false-red guard)"
    )


@pytest.mark.unit
def test_chapter_no_search_semantics() -> None:
    assert chapter_no("chapter-42.md") == 42
    assert chapter_no("rounds/r1/chapter-7-plan.md") == 7
    assert chapter_no(Path("rounds/r1/chapter-9.md")) == 9
    assert chapter_no("outline.md") is None
    m = CHAPTER_NUM_RE.search("chapter-3")
    assert m is not None
    assert m.group(1) == "3"


@pytest.mark.unit
def test_load_facts_oracle_empty_equals_absent(tmp_path: Path) -> None:
    from shenbi.facts.enums import FactsDim

    # 缺席 → None（三连语义：None 或空都折叠为 None，spec #89 T3）
    assert load_facts_oracle(tmp_path, FactsDim.PROPS) is None
