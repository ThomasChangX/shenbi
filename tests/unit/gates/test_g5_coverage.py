"""Branch-coverage tests for G5.3 cross-skill conflict detection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from shenbi.gates.g5 import gate_G5


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


@pytest.mark.unit
def test_g53_detects_numeric_and_terminology_conflicts(tmp_path: Path) -> None:
    """Same concept with differing numbers across world files + mixed term pair -> G5.3 conflicts.

    Covers g5.py:137-152 (numeric registry + conflict) and 170-174 (terminology).
    """
    project_dir = tmp_path / "project"
    world = project_dir / "world"
    world.mkdir(parents=True)
    # Same concept (队伍人数) with two different values across two files.
    (world / "a.md").write_text("# A\n\n队伍人数：3人。\n", encoding="utf-8")
    (world / "b.md").write_text("# B\n\n队伍人数：5人。\n", encoding="utf-8")
    chars = project_dir / "characters"
    chars.mkdir(parents=True)
    # Mixed term pair 灵能/灵力 with combined count > 3.
    (chars / "hero.md").write_text("灵能灵能灵能灵力。角色描述。\n", encoding="utf-8")
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    result = _result_dict(gate_G5("genesis", str(round_dir), str(project_dir)))
    conflicts = [mf for mf in result.get("must_fix", []) if "G5.3" in str(mf)]
    assert conflicts
    flat = " ".join(str(c) for c in conflicts)
    assert "numeric" in flat or "term_mix" in flat
