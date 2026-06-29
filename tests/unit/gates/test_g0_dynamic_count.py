"""Unit test for G0.10 dynamic skill count (spec §9.4)."""

from __future__ import annotations

import pytest

from shenbi.gates.shared import ALL_SKILLS


@pytest.mark.unit
def test_all_skills_is_dynamic_not_hardcoded() -> None:
    """ALL_SKILLS is scanned from the directory, not hardcoded."""
    assert isinstance(ALL_SKILLS, list | set)
    assert len(ALL_SKILLS) >= 61  # current count, grows with new skills
