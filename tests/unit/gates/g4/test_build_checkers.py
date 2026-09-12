"""build_checkers() factory + declarative wiring facts (spec #60 T0a-2 / F1017)."""

from shenbi.gates.g4.generic import G4_CHECKER_KEYS, G4_DECISIONS_WIRED, build_checkers


def test_build_checkers_returns_thirty():
    checkers = build_checkers()
    assert len(checkers) == 30
    assert set(checkers) == set(G4_CHECKER_KEYS)


def test_decisions_wired_is_eight():
    assert (
        frozenset(
            {
                "shenbi-chapter-drafting",
                "shenbi-chapter-planning",
                "shenbi-context-composing",
                "shenbi-genre-config",
                "shenbi-chapter-revision",
                "shenbi-short-drafting",
                "shenbi-state-settling",
                "shenbi-market-radar",
            }
        )
        == G4_DECISIONS_WIRED
    )


def test_wired_subset_of_checkers():
    assert set(G4_CHECKER_KEYS) >= G4_DECISIONS_WIRED
