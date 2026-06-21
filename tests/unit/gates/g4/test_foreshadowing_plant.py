"""Bespoke error-path tests for g4_foreshadowing_plant.

Distinct from test_foreshadowing_plant_regression.py (which covers the
isinstance defense for non-list YAML bodies). These tests cover hook
metadata completeness, depends_on, ops ceiling, and SMOKESCREEN validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from shenbi.gates.g4.foreshadowing_plant import g4_foreshadowing_plant


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


def _hooks_file(tmp_path: Path, hooks: list[dict[str, Any]] | None) -> Path:
    """Write a hooks.md whose '## hooks' body is the YAML dump of `hooks`.

    Passing None writes a file with no ## hooks section (forces no_hooks).
    """
    f = tmp_path / "hooks.md"
    if hooks is None:
        f.write_text("# Foreshadowing\n\n(no hooks section)\n", encoding="utf-8")
        return f
    body = yaml.safe_dump(hooks, allow_unicode=True)
    f.write_text(f"# Foreshadowing\n\n## hooks\n\n{body}\n", encoding="utf-8")
    return f


@pytest.mark.unit
def test_fails_when_hook_missing_required_field(tmp_path: Path) -> None:
    """A hook missing 'subtlety' -> FAIL with G4.fp.<id>.missing_subtlety."""
    hook = {
        "id": "h1",
        "type": "PLANT",
        "dimension": "x",
        "max_distance": 5,
        "escalation_curve": "linear",
        "depends_on": [],
    }
    # subtlety, cultivation_interval deliberately omitted
    f = _hooks_file(tmp_path, [hook])

    result = _result(g4_foreshadowing_plant([str(f)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.fp.h1.missing_subtlety" for mf in result["must_fix"])
    assert any(mf == "G4.fp.h1.missing_cultivation_interval" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_hook_depends_on_is_null(tmp_path: Path) -> None:
    """depends_on: null -> FAIL with G4.fp.<id>.depends_on_null."""
    hook = {
        "id": "h1",
        "type": "PLANT",
        "dimension": "x",
        "subtlety": 3,
        "cultivation_interval": 2,
        "max_distance": 5,
        "escalation_curve": "linear",
        "depends_on": None,
    }
    f = _hooks_file(tmp_path, [hook])

    result = _result(g4_foreshadowing_plant([str(f)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.fp.h1.depends_on_null" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_ops_count_exceeds_eight(tmp_path: Path) -> None:
    """More than 8 plant/reinforce/trigger/resolve ops -> FAIL with G4.fp.ops:{n}>8."""
    hooks = [
        {
            "id": f"h{i}",
            "type": "PLANT",
            "dimension": "x",
            "subtlety": 3,
            "cultivation_interval": 2,
            "max_distance": 5,
            "escalation_curve": "linear",
            "depends_on": [],
            "operation": "plant",
        }
        for i in range(9)
    ]
    f = _hooks_file(tmp_path, hooks)

    result = _result(g4_foreshadowing_plant([str(f)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.fp.ops:9>8" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_smokescreen_hook_lacks_exit_note(tmp_path: Path) -> None:
    """SMOKESCREEN hook with short/condition-free notes -> G4.fp.<id>.smokescreen_no_exit."""
    hook = {
        "id": "h1",
        "type": "SMOKESCREEN",
        "dimension": "x",
        "subtlety": 3,
        "cultivation_interval": 2,
        "max_distance": 5,
        "escalation_curve": "linear",
        "depends_on": [],
        "notes": "短得不够，而且没有条件词。",
    }  # < 50 chars, no conditional kw
    f = _hooks_file(tmp_path, [hook])

    result = _result(g4_foreshadowing_plant([str(f)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.fp.h1.smokescreen_no_exit" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_no_hooks_section_present(tmp_path: Path) -> None:
    """File without a '## hooks' section -> FAIL with G4.fp.no_hooks:<fp>."""
    f = _hooks_file(tmp_path, None)

    result = _result(g4_foreshadowing_plant([str(f)]))
    assert result["status"] == "FAIL"
    assert any("G4.fp.no_hooks" in mf for mf in result["must_fix"])
    assert any(str(f) in mf for mf in result["must_fix"])
