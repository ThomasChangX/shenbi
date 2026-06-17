"""Bespoke error-path tests for g4_character_design.

character_design inspects each fp; files with "protagonist" in their path
and a .md suffix trigger the frontmatter checks. project_dir (used for the
characters/major/ scan) is fps[0].parent.parent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.character_design import g4_character_design


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


def _project(tmp_path: Path) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"
    chars = project_dir / "characters" / "protagonist"
    chars.mkdir(parents=True)
    # fps[0].parent.parent must == project_dir; protagonist file sits two deep.
    protag = chars / "protagonist-01.md"
    return project_dir, protag


def _protagonist_md(overrides: dict[str, object] | None = None) -> str:
    """Full valid protagonist frontmatter; callers strip fields via overrides."""
    fm: dict[str, object] = {
        "name": "主角",
        "role": "protagonist",
        "personality_tags": ["勇敢"],
        "core_value": "正义",
        "goal_surface": "变强",
        "goal_deep": "复仇",
        "fear": "失败",
        "arc_type": "成长",
        "arc_starting": "弱小",
        "arc_turning": "觉醒",
        "arc_ending": "强大",
        "voice_profile": {
            "speech_patterns": ["直接", "简短"],
            "catchphrases": ["绝不会"],
            "avoid_patterns": ["啰嗦"],
        },
    }
    if overrides:
        fm.update(overrides)
    # Emit YAML-ish frontmatter (delimited by ---) that yload can parse.
    import yaml

    return "---\n" + yaml.safe_dump(fm, allow_unicode=True) + "---\n\n# 主角\n"


@pytest.mark.unit
def test_fails_when_protagonist_missing_required_field(tmp_path: Path) -> None:
    """protagonist.md missing a required field (core_value) -> FAIL with G4.protag.missing_core_value."""
    project_dir, protag = _project(tmp_path)
    # Remove core_value by overriding to empty string (triggers the falsy guard).
    body = _protagonist_md({"core_value": ""})
    protag.write_text(body, encoding="utf-8")

    result = _result(g4_character_design([str(protag)]))
    assert result["status"] == "FAIL"
    assert any("G4.protag.missing_core_value" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_protagonist_frontmatter_is_invalid_yaml(tmp_path: Path) -> None:
    """protagonist.md with unparseable frontmatter -> FAIL with G4.protag.yaml_error."""
    project_dir, protag = _project(tmp_path)
    protag.write_text(
        "---\nname: 主角\n  bad: : : indent\n---\n\n# 主角\n",
        encoding="utf-8",
    )

    result = _result(g4_character_design([str(protag)]))
    assert result["status"] == "FAIL"
    assert any("G4.protag.yaml_error" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_voice_profile_array_below_minimum(tmp_path: Path) -> None:
    """voice_profile.speech_patterns with 1 entry (< 2) -> FAIL with G4.voice.speech_patterns."""
    project_dir, protag = _project(tmp_path)
    body = _protagonist_md(
        {
            "voice_profile": {
                "speech_patterns": ["only one"],
                "catchphrases": ["x"],
                "avoid_patterns": ["y"],
            }
        }
    )
    protag.write_text(body, encoding="utf-8")

    result = _result(g4_character_design([str(protag)]))
    assert result["status"] == "FAIL"
    assert any("G4.voice.speech_patterns:need_2_got_1" in mf for mf in result["must_fix"])


def _protag_at_depth_two(tmp_path: Path) -> Path:
    """Protagonist file at <project>/<sub>/protagonist-01.md so that
    fps[0].parent.parent == project_dir (needed for the major_chars scan).
    """
    sub = tmp_path / "project" / "out"
    sub.mkdir(parents=True)
    return sub / "protagonist-01.md"


@pytest.mark.unit
def test_fails_when_major_chars_dir_has_fewer_than_two(tmp_path: Path) -> None:
    """characters/major/ with < 2 files -> FAIL with G4.cd.major_chars:need_2_got_1."""
    protag = _protag_at_depth_two(tmp_path)
    protag.write_text(_protagonist_md(), encoding="utf-8")
    project_dir = protag.parent.parent
    major = project_dir / "characters" / "major"
    major.mkdir(parents=True)
    (major / "only.md").write_text("# x\n", encoding="utf-8")

    result = _result(g4_character_design([str(protag)]))
    assert result["status"] == "FAIL"
    assert any("G4.cd.major_chars:need_2_got_1" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_major_chars_dir_missing(tmp_path: Path) -> None:
    """No characters/major/ dir -> FAIL with G4.cd.major_dir.not_found."""
    protag = _protag_at_depth_two(tmp_path)
    protag.write_text(_protagonist_md(), encoding="utf-8")

    result = _result(g4_character_design([str(protag)]))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.cd.major_dir.not_found" for mf in result["must_fix"])
