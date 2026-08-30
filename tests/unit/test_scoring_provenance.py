"""spec #31 T3 (F113 residual): scored_by provenance 三值 (file/interactive/subagent)."""

from __future__ import annotations

import pytest

from shenbi.contracts.enums import ALL_ENUMS, ScoredBy


def test_scored_by_in_all_enums() -> None:
    assert ALL_ENUMS["ScoredBy"] == ScoredBy


@pytest.mark.unit
@pytest.mark.parametrize(
    ("argv_extra", "expected"),
    [
        (["--subagent"], "subagent"),
        (["--interactive"], "interactive"),
        ([], "file"),
    ],
)
def test_scored_by_three_values(
    monkeypatch: pytest.MonkeyPatch, argv_extra: list[str], expected: str
) -> None:
    from shenbi.scoring import _resolve_scored_by

    monkeypatch.setattr("sys.argv", ["scoring.py", "r.md", "s.json", *argv_extra])
    assert _resolve_scored_by() == expected
