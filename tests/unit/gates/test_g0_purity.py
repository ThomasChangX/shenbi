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


# ---------------------------------------------------------------------------
# Error-path tests (PR-52 Step 12)
#
# Verified against src/shenbi/gates/g0_purity.py: this module exposes only
# three functions — check_scenario_file_purity, check_scenario_dir_purity,
# check_skill_md_purity. It does NOT parse SKILL.md frontmatter or scan for
# meta-narrative (those concepts live elsewhere), so the "stray meta-narrative"
# and "broken frontmatter" categories are pinned to the module's actual
# behavior (frontmatter-agnostic, meta-narrative-agnostic).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scenario_file_placeholder_non_fixture_path_fails(tmp_path: Path) -> None:
    """A scenario referencing a placeholder file path that is not under
    tests/fixtures/ or skills/ -> check_scenario_file_purity FAILs.
    """
    t1 = _build_t1_skill_dir(
        tmp_path,
        "shenbi-worldbuilding",
        "# Scenario\n\nReads placeholder output `output/seed.md`.\n",
    )
    checks, fail_reason, must_fix = check_scenario_file_purity(t1)
    assert fail_reason is not None
    assert any(c["s"] == "FAIL" for c in checks)
    assert must_fix  # non-empty


@pytest.mark.unit
def test_scenario_dir_non_fixture_directory_warns(tmp_path: Path) -> None:
    """A scenario referencing a directory path not under tests/fixtures/ or
    skills/ -> check_scenario_dir_purity emits a WARN (not blocking).
    """
    t1 = _build_t1_skill_dir(
        tmp_path,
        "shenbi-worldbuilding",
        "# Scenario\n\nRead all from `output/chapters/`.\n",
    )
    result = check_scenario_dir_purity(t1)
    assert isinstance(result, list)
    assert any(c["s"] == "WARN" for c in result)


@pytest.mark.unit
def test_missing_scenario_file_returns_pass(tmp_path: Path) -> None:
    """When the t1 skill dir exists but has no scenario.md, there is nothing
    impure to flag -> file purity returns PASS (no scenario to scan).
    """
    t1_root = tmp_path / "t1-skills"
    skill_dir = t1_root / "shenbi-worldbuilding"
    skill_dir.mkdir(parents=True)
    # generative/input/ exists but no scenario.md
    (skill_dir / "generative" / "input").mkdir(parents=True)
    checks, fail_reason, must_fix = check_scenario_file_purity(t1_root)
    assert fail_reason is None
    assert must_fix == []
    assert all(c["s"] == "PASS" for c in checks)


@pytest.mark.unit
def test_skill_md_meta_narrative_not_flagged_pins_behavior(tmp_path: Path) -> None:
    """SKILL.md stray meta-narrative is NOT flagged by check_skill_md_purity.

    Pins current behavior: this module only scans for tests/fixtures/ path
    leaks, not for META_NARRATIVE phrases (which live in shared.py but are
    not referenced here). A SKILL.md full of meta-narrative but free of
    fixture leaks returns PASS.
    """
    skills = tmp_path / "skills"
    skill_dir = skills / "shenbi-narrative-skill"
    skill_dir.mkdir(parents=True)
    body = (
        "---\nname: shenbi-narrative-skill\ndescription: x\n---\n\n"
        "# Skill\n\n由此可见，引人深思，让人感悟。综上所述，不禁感慨。\n"
    )
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    checks, fail_reason, must_fix = check_skill_md_purity(skills)
    assert fail_reason is None  # pins current behavior: meta-narrative ignored
    assert must_fix == []


@pytest.mark.unit
def test_skill_md_broken_frontmatter_not_flagged_pins_behavior(tmp_path: Path) -> None:
    """SKILL.md with broken/malformed frontmatter is NOT flagged here.

    Pins current behavior: check_skill_md_purity reads SKILL.md as plain
    text and only greps for tests/fixtures/ paths; it does not parse YAML
    frontmatter, so broken frontmatter is silently tolerated.
    """
    skills = tmp_path / "skills"
    skill_dir = skills / "shenbi-broken-fm-skill"
    skill_dir.mkdir(parents=True)
    body = "---\nname: shenbi-broken-fm-skill\n  bad: : : indent\n  - broken yaml\n---\n\n# Body\n"
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    checks, fail_reason, must_fix = check_skill_md_purity(skills)
    assert fail_reason is None  # pins current behavior: frontmatter not parsed
    assert must_fix == []
