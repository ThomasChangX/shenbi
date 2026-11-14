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


def test_roster_single_source() -> None:
    """Spec #90 T1: shared.py holds the authoritative literal; generic re-imports."""
    import ast
    from pathlib import Path

    repo = Path(__file__).resolve().parents[4]
    shared_src = (repo / "src/shenbi/gates/shared.py").read_text(encoding="utf-8")
    tree = ast.parse(shared_src)
    plain = {
        t.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for t in node.targets
        if isinstance(t, ast.Name)
    }
    ann = {
        node.target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, (ast.Call, ast.Set))
    }
    assert "G4_CHECKER_KEYS" in (plain | ann), "shared.py must define the literal"
    assert "G4_CHECKER_SKILLS" in plain, "shared.py must keep alias line"

    from shenbi.gates.g4 import generic
    from shenbi.gates.shared import G4_CHECKER_KEYS

    assert generic.G4_CHECKER_KEYS is G4_CHECKER_KEYS, "generic must re-import, not copy"
    assert len(G4_CHECKER_KEYS) == 30


def test_short_map_derived_in_g4_branch() -> None:
    """Spec #90 T1: SHORT_MAP is derived inside the G4 lazy branch, not a top-level dict."""
    import ast
    from pathlib import Path

    repo = Path(__file__).resolve().parents[4]
    src = (repo / "src/shenbi/gates/cli.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    top_assigns = [
        t.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for t in node.targets
        if isinstance(t, ast.Name)
    ]
    assert "SHORT_MAP" not in top_assigns, "no top-level SHORT_MAP dict (spec #90 T1)"
    assert "short_map = {k.removeprefix(" in src, "derived form must exist in G4 branch"
