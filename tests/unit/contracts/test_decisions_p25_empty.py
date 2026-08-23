"""F404/F458: empty/whitespace rationale must fail P2.5 REQUIRED rules."""

import pytest
from pydantic import ValidationError

from shenbi.contracts.schemas.decisions import Adjustment, Selection


def test_selection_manual_override_empty_rationale_rejected() -> None:
    with pytest.raises(ValidationError, match="rationale REQUIRED"):
        Selection(
            target="chapter-3",
            selected=["a"],
            basis="manual_override",
            rationale="   ",
        )


def test_selection_high_severity_empty_string_rationale_rejected() -> None:
    with pytest.raises(ValidationError, match="rationale REQUIRED"):
        Selection(
            target="chapter-3",
            selected=["a"],
            basis="arc_relevance",
            severity="high",
            rationale="",
        )


def test_selection_routine_low_still_forbids_rationale() -> None:
    # unchanged semantics: routine+low forbids any rationale (even non-empty)
    with pytest.raises(ValidationError, match="FORBIDDEN"):
        Selection(
            target="chapter-3",
            selected=["a"],
            basis="arc_relevance",
            severity="low",
            rationale="why not",
        )


def test_selection_valid_rationale_still_accepted() -> None:
    s = Selection(
        target="chapter-3",
        selected=["a"],
        basis="manual_override",
        rationale="用户点名要求跳过该场景",
    )
    assert s.rationale


def test_adjustment_empty_rationale_rejected() -> None:
    with pytest.raises(ValidationError, match="rationale REQUIRED"):
        Adjustment(issue_id="i1", severity="low", handling="ignore", rationale="")


def test_adjustment_whitespace_rationale_rejected() -> None:
    with pytest.raises(ValidationError, match="rationale REQUIRED"):
        Adjustment(issue_id="i1", severity="low", handling="ignore", rationale=" \t ")


def test_adjustment_valid_rationale_accepted() -> None:
    a = Adjustment(issue_id="i1", severity="low", handling="ignore", rationale="因为 X")
    assert a.rationale
