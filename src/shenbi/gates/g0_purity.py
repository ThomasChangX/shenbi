"""Scenario path purity checks for G0.

Extracted from g0.py to keep file length under 500 lines. These checks
verify that test scenarios reference only tests/fixtures/ paths, not
project-relative paths.
"""

import re
from pathlib import Path
from typing import Any


def check_scenario_file_purity(
    t1_skill_dir: Path,
) -> tuple[list[dict[str, Any]], str | None, list[str]]:
    """G0.9: scenario file paths must reference tests/fixtures/ or skills/.

    Returns (checks, fail_reason_or_None, must_fix).
    """
    impure_refs: dict[str, list[str]] = {}
    if t1_skill_dir.exists():
        for skill_dir in sorted(t1_skill_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                continue
            for test_type in ("generative", "bug-hunt", "clean"):
                scenario = skill_dir / test_type / "input" / "scenario.md"
                if not scenario.exists():
                    continue
                try:
                    sc_content = scenario.read_text(encoding="utf-8")
                except Exception:
                    continue
                refs = set(re.findall(r"`([a-zA-Z][\w\-/]*\.[a-zA-Z]+)`", sc_content))
                for ref in refs:
                    if ref.startswith("skills/"):
                        continue
                    if ref.startswith("tests/fixtures/"):
                        continue
                    impure_refs.setdefault(ref, []).append(f"{skill_dir.name}/{test_type}")

    if impure_refs:
        detail = "; ".join(
            f"'{r}' → must use tests/fixtures/ (found in: {', '.join(skills[:3])})"
            for r, skills in sorted(impure_refs.items())
        )
        return (
            [{"id": "G0.9", "s": "FAIL", "r": f"scenarios contain non-fixture paths: {detail}"}],
            "scenarios contain non-fixture paths",
            ["G0.9: replace project paths with tests/fixtures/ equivalents"],
        )
    return (
        [{"id": "G0.9", "s": "PASS", "note": "all scenario input paths reference tests/fixtures/"}],
        None,
        [],
    )


def check_scenario_dir_purity(t1_skill_dir: Path) -> list[dict[str, Any]]:
    """G0.9c: scenario directory paths must reference tests/fixtures/ or skills/."""
    impure_dirs: dict[str, list[str]] = {}
    if t1_skill_dir.exists():
        for skill_dir in sorted(t1_skill_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                continue
            for test_type in ("generative", "bug-hunt", "clean"):
                scenario = skill_dir / test_type / "input" / "scenario.md"
                if not scenario.exists():
                    continue
                try:
                    sc_content = scenario.read_text(encoding="utf-8")
                except Exception:
                    continue
                dirs = set(re.findall(r"`([a-zA-Z][\w\-/]+/)`?", sc_content))
                dirs = {d.rstrip("`") for d in dirs}
                for d in dirs:
                    if d.startswith("tests/fixtures/") or d.startswith("skills/"):
                        continue
                    impure_dirs.setdefault(d, []).append(f"{skill_dir.name}/{test_type}")

    if impure_dirs:
        count = sum(len(v) for v in impure_dirs.values())
        detail = "; ".join(
            f"'{d}' → (found in: {', '.join(skills[:3])})"
            for d, skills in sorted(impure_dirs.items())
        )
        return [
            {
                "id": "G0.9c",
                "s": "WARN",
                "r": f"{count} non-fixture directory references found: {detail}",
                "note": "not blocking; fix incrementally",
            }
        ]
    return [
        {
            "id": "G0.9c",
            "s": "PASS",
            "note": "all scenario directory paths reference tests/fixtures/",
        }
    ]


def check_skill_md_purity(
    skills_dir: Path,
) -> tuple[list[dict[str, Any]], str | None, list[str]]:
    """G0.9b: SKILL.md files must NOT contain tests/fixtures/ references."""
    skill_fixture_leaks: dict[str, list[str]] = {}
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            sk_content = skill_md.read_text(encoding="utf-8")
        except Exception:
            continue
        leaked = re.findall(r"tests/fixtures/[\w\-/]+", sk_content)
        if leaked:
            skill_fixture_leaks[skill_dir.name] = leaked

    if skill_fixture_leaks:
        detail = "; ".join(
            f"{skill}: {', '.join(paths)}" for skill, paths in sorted(skill_fixture_leaks.items())
        )
        return (
            [
                {
                    "id": "G0.9b",
                    "s": "FAIL",
                    "r": f"SKILL.md files contain tests/fixtures/ paths (use project paths, not test paths): {detail}",
                }
            ],
            "SKILL.md files contain tests/fixtures/ paths",
            [
                "G0.9b: replace tests/fixtures/ paths in SKILL.md with project paths; move fixture mapping to scenario.md"
            ],
        )
    return (
        [{"id": "G0.9b", "s": "PASS", "note": "no SKILL.md files leak test fixture paths"}],
        None,
        [],
    )
