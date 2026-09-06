"""R3 (spec #45): output-path boundary for the codex write face.

Traversal (`../`), symlink escape out of project_dir, and state-file
deny-list (phase-state/, gate-markers, scores family) must all FAIL without
touching disk; normal relative paths stay green. T1202 carrier last-wins
covered in test_t1202_carrier.py.
"""

from pathlib import Path

import pytest

from shenbi.exceptions import DispatchWriteFailureError
from shenbi.pipeline.dispatch_helper import _write_parsed_outputs


def _resp(path: str) -> str:
    return f"### FILE: {path}\ncontent\n"


def test_traversal_rejected_and_not_written(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(Exception) as ei:
        _write_parsed_outputs(_resp("../escape.md"), ["../escape.md"], project)
    assert getattr(ei.value, "signature", "") == "path_escape"
    assert not (tmp_path / "escape.md").exists()


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    link = project / "link.md"
    link.symlink_to(outside)
    with pytest.raises(DispatchWriteFailureError):
        _write_parsed_outputs(_resp("link.md"), ["link.md"], project)
    assert outside.read_text(encoding="utf-8") == "secret"  # untouched


def test_state_file_denied(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    for rel in ("phase-state/x.json", "gate-markers/g4.md", "round/scores.json"):
        with pytest.raises(DispatchWriteFailureError) as ei:
            _write_parsed_outputs(_resp(rel), [rel], project)
        assert getattr(ei.value, "signature", "") == "state_file_write_denied"


def test_normal_relative_path_still_writes(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    written = _write_parsed_outputs(
        _resp("outline/chapter-1.md"), ["outline/chapter-1.md"], project
    )
    assert written == ["outline/chapter-1.md"]
    assert "content" in (project / "outline" / "chapter-1.md").read_text(encoding="utf-8")


def test_scores_family_variants_denied(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    for rel in ("final-scores.json", "round/g4-scores.json"):
        with pytest.raises(DispatchWriteFailureError) as ei:
            _write_parsed_outputs(_resp(rel), [rel], project)
        assert getattr(ei.value, "signature", "") == "state_file_write_denied"
