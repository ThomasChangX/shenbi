"""Unit tests for g0_purity: G0.9/G0.9c/G0.9b scenario path purity.

Function contracts (verified against src/shenbi/gates/g0_purity.py):

- check_scenario_file_purity(t1_skill_dir: Path)
    -> tuple[list[dict], str | None, list[str]]
    Iterates t1_skill_dir/<skill_name>/<test_type>/input/scenario.md
    looking for backtick-quoted file refs NOT starting with
    `skills/` or `tests/fixtures/`.

- check_scenario_dir_purity(t1_skill_dir: Path)
    -> list[dict]  # note: NOT a tuple
    Same iteration as above; checks backtick-quoted directory refs.

- check_skill_md_purity(skills_dir: Path)
    -> tuple[list[dict], str | None, list[str]]
    Iterates skills_dir/<skill_name>/SKILL.md looking for leaked
    `tests/fixtures/...` paths (those should be in scenario.md, not SKILL.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g0_purity import (
    check_scenario_dir_purity,
    check_scenario_file_purity,
    check_skill_md_purity,
)


def _build_t1_skill_dir(tmp_path: Path, skill_name: str, scenario_body: str) -> Path:
    """Build a t1-style skill dir tree with one scenario.md under generative/input/."""
    t1_root = tmp_path / "t1-skills"
    scenario = t1_root / skill_name / "generative" / "input" / "scenario.md"
    scenario.parent.mkdir(parents=True)
    scenario.write_text(scenario_body, encoding="utf-8")
    return t1_root


@pytest.mark.unit
def test_check_scenario_file_purity_passes_when_all_refs_use_tests_fixtures(
    tmp_path: Path,
) -> None:
    """Scenario referencing tests/fixtures/ paths -> PASS."""
    t1 = _build_t1_skill_dir(
        tmp_path,
        "shenbi-worldbuilding",
        "# Scenario\n\nReads: `tests/fixtures/seed.md`.\n",
    )
    checks, fail_reason, must_fix = check_scenario_file_purity(t1)
    assert fail_reason is None
    assert must_fix == []
    assert all(c["s"] == "PASS" for c in checks)


@pytest.mark.unit
def test_check_scenario_file_purity_fails_on_project_relative_refs(
    tmp_path: Path,
) -> None:
    """Scenario referencing project/seed.md (not tests/fixtures/) -> FAIL."""
    t1 = _build_t1_skill_dir(
        tmp_path,
        "shenbi-worldbuilding",
        "# Scenario\n\nReads: `project/seed.md`.\n",
    )
    checks, fail_reason, must_fix = check_scenario_file_purity(t1)
    assert fail_reason is not None
    assert any(c["s"] == "FAIL" for c in checks)
    assert must_fix  # non-empty must_fix list


@pytest.mark.unit
def test_check_scenario_dir_purity_passes_when_no_dirs_referenced(
    tmp_path: Path,
) -> None:
    """Scenario with no directory refs -> returns list with single PASS check."""
    t1 = _build_t1_skill_dir(
        tmp_path,
        "shenbi-worldbuilding",
        "# Scenario\n\nNo directory refs here.\n",
    )
    result = check_scenario_dir_purity(t1)  # returns list, not tuple
    assert isinstance(result, list)
    assert any(c["s"] == "PASS" for c in result)


@pytest.mark.unit
def test_check_skill_md_purity_passes_when_no_fixture_leak(
    tmp_path: Path,
) -> None:
    """SKILL.md without tests/fixtures/ paths -> PASS."""
    skills = tmp_path / "skills"
    skill_dir = skills / "shenbi-test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: shenbi-test-skill\ndescription: trigger only\n---\n\n# Test\n",
        encoding="utf-8",
    )
    checks, fail_reason, must_fix = check_skill_md_purity(skills)
    assert fail_reason is None
    assert must_fix == []


@pytest.mark.unit
def test_check_skill_md_purity_fails_when_skill_md_leaks_fixture_path(
    tmp_path: Path,
) -> None:
    """SKILL.md mentioning tests/fixtures/foo.md -> FAIL."""
    skills = tmp_path / "skills"
    skill_dir = skills / "shenbi-leaky-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: shenbi-leaky-skill\ndescription: x\n---\n\n"
        "# Leaky\n\nReads tests/fixtures/seed.md for examples.\n",
        encoding="utf-8",
    )
    checks, fail_reason, must_fix = check_skill_md_purity(skills)
    assert fail_reason is not None
    assert any(c["s"] == "FAIL" for c in checks)
