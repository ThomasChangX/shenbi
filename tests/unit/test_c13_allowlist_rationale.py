"""C13 allowlist rationale survival guard (spec #97 T1).

Ruff >=0.17 exempts structured except-handlers from BLE001, which turns the
inline ``# noqa: BLE001`` directives at those sites into unused-noqa (RUF100)
— an autofix then strips the directive together with its rationale comment
(the 7725f002 bot-run autopsy). The directives are retired by design; this
test pins the invariant that the C13 rationale itself never leaves the site.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Minimum number of src/ files carrying an inline C13 rationale (spec #97
#: T1: six migrated plain-comment sites plus archive.py provenance fallback,
#: which keeps its noqa — its bare ``return None`` handler still fires
#: BLE001 at ruff 0.17).
MIN_SITES = 6


def test_c13_allowlist_rationale_stays_at_sites() -> None:
    """C13 rationale comments remain at >= MIN_SITES sites under src/."""
    hits = [
        path
        for path in (REPO_ROOT / "src").rglob("*.py")
        if "C13 allowlist" in path.read_text(encoding="utf-8")
    ]
    assert len(hits) >= MIN_SITES, (
        f"C13 rationale dropped to {len(hits)} sites (< {MIN_SITES}) — "
        "rationale must never leave the site (spec #97 T1)"
    )
