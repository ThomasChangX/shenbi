"""F432: G7.1b reverse coverage anchors to the t1-skill scaffold set (69)."""

import json
from pathlib import Path

from shenbi.gates.g7 import gate_G7
from shenbi.gates.shared import ALL_SKILLS, T1_SCAFFOLD_SKILLS


def test_scaffold_set_excludes_unscaffolded() -> None:
    unscaffolded = set(ALL_SKILLS) - set(T1_SCAFFOLD_SKILLS)
    assert unscaffolded, "expected group-/lifecycle skills to lack T1 scaffolds"
    assert all(
        s.startswith("shenbi-review-group")
        or "lifecycle" in s
        or s in ("using-shenbi",)
        or "snapshot" in s
        or "canon" in s
        for s in unscaffolded
    )


def test_full_scaffold_coverage_no_missing(tmp_path: Path) -> None:
    """A summary covering the whole scaffold set (names taken from the real
    tests/tiers/t1-skill roster, not hand-typed) must not FAIL G7.1b.
    """
    rd = tmp_path / "round"
    rd.mkdir()
    summary = {"t1_scores": dict.fromkeys(T1_SCAFFOLD_SKILLS, 90)}
    (rd / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    result = json.loads(gate_G7(str(rd)))
    assert not any("missing_coverage" in str(m) for m in result.get("must_fix", []))


def test_missing_scaffold_skill_still_fails(tmp_path: Path) -> None:
    """Reverse coverage must still FAIL when a scaffolded skill is missing."""
    rd = tmp_path / "round"
    rd.mkdir()
    partial = list(T1_SCAFFOLD_SKILLS)[:-1]
    summary = {"t1_scores": dict.fromkeys(partial, 90)}
    (rd / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    result = json.loads(gate_G7(str(rd)))
    assert any("missing_coverage" in str(m) for m in result.get("must_fix", []))
