"""Regression test for foreshadowing_plant isinstance defense.

Bug: basedpyright flagged `if not isinstance(hooks, list)` as unnecessary
because the surrounding annotation was `hooks: list[dict[str, Any]]`.
But `yaml.safe_load` returns Any at runtime — a hooks section containing
a dict or scalar (instead of a list of hook dicts) would slip past the
check and break the downstream `for h in hooks` loop.

Fix: load yaml into an explicitly-typed `loaded: Any`, then narrow with
isinstance. The check is now semantically meaningful.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.g4.foreshadowing_plant import g4_foreshadowing_plant

pytestmark = pytest.mark.unit


def test_hooks_section_with_dict_yaml_instead_of_list_does_not_crash(
    tmp_path: Path,
) -> None:
    """Regression: a `## hooks` body whose YAML parses to a dict (not a
    list) must be normalized to an empty list, not propagated downstream.
    """
    hooks_file = tmp_path / "hooks.md"
    hooks_file.write_text(
        "# Foreshadowing\n\n## hooks\n\nnot_a_list: this_is_a_dict\n",
        encoding="utf-8",
    )
    result_str = g4_foreshadowing_plant([str(hooks_file)])
    parsed = json.loads(result_str)
    # Strong assertions: gate must produce structured G4 output, not just
    # any JSON-parseable string.
    assert parsed["status"] in {"PASS", "FAIL"}, "gate must complete, not raise"
    assert parsed["gate"] == "G4-foreshadowing-plant"
    assert isinstance(parsed["checks"], list)


def test_hooks_section_with_scalar_yaml_instead_of_list_does_not_crash(
    tmp_path: Path,
) -> None:
    """Regression: a `## hooks` body containing a bare scalar (string,
    number) must also be normalized to empty list.
    """
    hooks_file = tmp_path / "hooks.md"
    hooks_file.write_text(
        "# Foreshadowing\n\n## hooks\n\njust_a_string\n",
        encoding="utf-8",
    )
    result_str = g4_foreshadowing_plant([str(hooks_file)])
    parsed = json.loads(result_str)
    assert parsed["status"] in {"PASS", "FAIL"}, "gate must complete, not raise"
    assert parsed["gate"] == "G4-foreshadowing-plant"
    assert isinstance(parsed["checks"], list)
