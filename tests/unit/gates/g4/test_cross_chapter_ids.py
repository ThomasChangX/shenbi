"""spec #88 T1c: machine ids for pure-Chinese XC findings (tuple form)."""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4.cross_chapter import (
    CrossChapterContext,
    check_cross_chapter,
)

FIX = Path(__file__).resolve().parents[4] / "tests/fixtures/cross-chapter-regression"
CH20_WOUND = (
    Path(__file__).resolve().parents[4]
    / "tests/fixtures/invariant-mutants/ch20-name-swap-prop-break.md"
)


def _issues(ch_cur: str, ch_prev: str | None):
    prev = FIX / "chapters" / ch_prev if ch_prev else None
    return check_cross_chapter(FIX / "chapters" / ch_cur, prev, None, CrossChapterContext())


def test_pov_break_carries_machine_id():
    issues = _issues("chapter-2.md", "chapter-1.md")
    assert any(cid == "pov_break" and "POV 人称断裂" in det for cid, det in issues)


def test_title_violation_carries_machine_id():
    issues = _issues("chapter-4.md", "chapter-3.md")
    assert any(cid == "title_violation" and "称谓违例" in det for cid, det in issues)


def test_narration_name_nested_promotion_no_inner_prefix():
    """Nested promotion: inner XC.narration_name prefix stripped, id promoted, detail clean."""
    identity = {"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]}
    ctx = CrossChapterContext(identity_fact=identity)
    issues = check_cross_chapter(CH20_WOUND, None, None, ctx)
    narration = [(cid, det) for cid, det in issues if cid == "narration_name"]
    assert narration, "ch20 wound fixture must trip narration_name"
    for _cid, det in narration:
        assert not det.startswith("XC.narration_name")


def test_all_issue_elements_are_tuples():
    """All issue elements are (id, detail) tuples; ids belong to the spec 1.1 roster."""
    known_ids = {
        "pronoun_mismatch",
        "title_violation",
        "org_drift",
        "residence_drift",
        "reserved_name_hijack",
        "prop_chain_origin",
        "prop_undeclared",
        "pov_break",
        "timeline_rollback",
        "balance_jump",
        "narration_name",
    }
    for issues in (
        _issues("chapter-2.md", "chapter-1.md"),
        _issues("chapter-4.md", "chapter-3.md"),
    ):
        for cid, _det in issues:
            assert cid in known_ids
