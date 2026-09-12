"""Bespoke error-path tests for g4_foreshadowing_lifecycle (spec #59 T3).

Ported from the retired plant/track checker tests: hook metadata completeness,
depends_on, ops ceiling, SMOKESCREEN validation (plant heritage) and
pending_hooks change/chapter-ref checks (track heritage).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from shenbi.gates.g4.foreshadowing_lifecycle import g4_foreshadowing_lifecycle


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


def _hooks_file(tmp_path: Path, hooks: list[dict[str, Any]] | None) -> Path:
    """Write a hooks.md whose '## hooks' body is the YAML dump of `hooks`."""
    f = tmp_path / "hooks.md"
    if hooks is None:
        f.write_text("# Foreshadowing\n\n(no hooks section)\n", encoding="utf-8")
        return f
    body = yaml.safe_dump(hooks, allow_unicode=True)
    f.write_text(f"# Foreshadowing\n\n## hooks\n\n{body}\n", encoding="utf-8")
    return f


def _setup(tmp_path: Path, pending: str | None = None) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"
    sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True)
    marker = sub_dir / "out.md"
    if pending is None:
        marker.write_text("x", encoding="utf-8")
    else:
        marker.write_text(pending, encoding="utf-8")
    truth = project_dir / "truth"
    truth.mkdir(parents=True)
    (truth / "pending_hooks.md").write_text(
        pending if pending is not None else "# Hooks\n操作: PLANTED\n第1章\n",
        encoding="utf-8",
    )
    return project_dir, marker


# — plant heritage —


@pytest.mark.unit
def test_fails_when_hook_missing_required_field(tmp_path: Path) -> None:
    hook = {
        "id": "h1",
        "type": "PLANT",
        "dimension": "x",
        "max_distance": 5,
        "escalation_curve": "linear",
        "depends_on": [],
    }
    f = _hooks_file(tmp_path, [hook])
    project_dir, marker = _setup(tmp_path)

    result = _result(g4_foreshadowing_lifecycle([str(f)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.fl.h1.missing_subtlety" for mf in result["must_fix"])
    assert any(mf == "G4.fl.h1.missing_cultivation_interval" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_hook_depends_on_is_null(tmp_path: Path) -> None:
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
    project_dir, _ = _setup(tmp_path)

    result = _result(g4_foreshadowing_lifecycle([str(f)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.fl.h1.depends_on_null" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_ops_count_exceeds_ceiling(tmp_path: Path) -> None:
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
        for i in range(25)
    ]
    f = _hooks_file(tmp_path, hooks)
    project_dir, _ = _setup(tmp_path)

    result = _result(g4_foreshadowing_lifecycle([str(f)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.fl.ops:25>24" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_smokescreen_hook_lacks_exit_note(tmp_path: Path) -> None:
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
    }
    f = _hooks_file(tmp_path, [hook])
    project_dir, _ = _setup(tmp_path)

    result = _result(g4_foreshadowing_lifecycle([str(f)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.fl.h1.smokescreen_no_exit" for mf in result["must_fix"])


@pytest.mark.unit
def test_hooks_payload_with_non_dict_entry_fails(tmp_path: Path) -> None:
    """F409 heritage: a string element in the hooks list must not crash."""
    f = _hooks_file(tmp_path, ["just-a-string"])  # type: ignore[list-item]
    project_dir, _ = _setup(tmp_path)

    result = _result(g4_foreshadowing_lifecycle([str(f)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any("G4.fl.hook_not_dict" in mf for mf in result["must_fix"])


# — track heritage —


@pytest.mark.unit
def test_fails_when_pending_hooks_missing(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True)
    marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    (project_dir / "truth").mkdir()

    result = _result(g4_foreshadowing_lifecycle([str(marker)], rd=str(project_dir)))
    assert any("G4.fl.not_found_pending_hooks" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_no_state_changes(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path, pending="# Hooks\njust text\n")

    result = _result(g4_foreshadowing_lifecycle([str(marker)], rd=str(project_dir)))
    assert any("G4.fl.no_changes" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_no_chapter_refs(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path, pending="# Hooks\n操作: PLANTED\n")

    result = _result(g4_foreshadowing_lifecycle([str(marker)], rd=str(project_dir)))
    assert any("G4.fl.chapter_refs" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_changes_and_refs(tmp_path: Path) -> None:
    project_dir, marker = _setup(tmp_path, pending="# Hooks\n操作: PLANTED\n第1章 第2章\n")

    result = _result(g4_foreshadowing_lifecycle([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"


# — lifecycle-specific (recall vocabulary, r5 ruling) —


@pytest.mark.unit
def test_recall_phase_vocabulary_accepted(tmp_path: Path) -> None:
    """DORMANT/ACTIVE/ABANDONED transitions in free-form reports pass the state check."""
    project_dir, marker = _setup(tmp_path)
    report = tmp_path / "audit.md"
    report.write_text(
        "| H01 | DORMANT | ACTIVE | trigger_condition matched current chapter context |\n",
        encoding="utf-8",
    )

    result = _result(g4_foreshadowing_lifecycle([str(report)], rd=str(project_dir)))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_free_form_output_without_states_fails(tmp_path: Path) -> None:
    project_dir, _ = _setup(tmp_path)
    report = tmp_path / "audit.md"
    report.write_text("no state words here\n", encoding="utf-8")

    result = _result(g4_foreshadowing_lifecycle([str(report)], rd=str(project_dir)))
    assert any("G4.fl.no_hook_states" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_no_files_skips_per_file_checks(tmp_path: Path) -> None:
    project_dir, _ = _setup(tmp_path)
    result = _result(g4_foreshadowing_lifecycle([], rd=str(project_dir)))
    assert result["status"] == "PASS"  # project face still green; per-file SKIP recorded


@pytest.mark.unit
def test_empty_hooks_payload_fails_like_no_hooks(tmp_path: Path) -> None:
    """Ported regression: `## hooks: []` must FAIL (old plant no_hooks parity),
    not silently skip per-file checks.
    """
    f = tmp_path / "hooks.md"
    f.write_text("# Foreshadowing\n\n## hooks\n\n[]\n", encoding="utf-8")
    project_dir, _ = _setup(tmp_path)

    result = _result(g4_foreshadowing_lifecycle([str(f)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any("G4.fl.no_hook_states" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_scalar_yaml_hooks_body_fails_free_form(tmp_path: Path) -> None:
    """Ported regression: a scalar (non-list) `## hooks` body falls to the
    free-form state check and FAILs on state-less content.
    """
    f = tmp_path / "hooks.md"
    f.write_text("# Foreshadowing\n\n## hooks\n\njust a scalar\n", encoding="utf-8")
    project_dir, _ = _setup(tmp_path)

    result = _result(g4_foreshadowing_lifecycle([str(f)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any("G4.fl.no_hook_states" in mf for mf in result["must_fix"])
