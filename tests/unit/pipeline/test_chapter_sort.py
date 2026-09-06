"""C29 R3 numeric chapter sort (F326) — chapter_sort_key + call sites."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.chapter_loop import chapter_sort_key

pytestmark = pytest.mark.unit


def test_sort_key_numeric_order():
    names = [f"tests/fixtures/chapter-{n}-draft.md" for n in (2, 3, 4, 5, 6, 7, 8, 9, 10)]
    ordered = sorted(names, key=chapter_sort_key)
    nums = [int(p.split("chapter-")[1].split("-")[0]) for p in ordered]
    assert nums == sorted(nums) == [2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_sort_key_accepts_path():
    paths = [Path("chapters/chapter-10.md"), Path("chapters/chapter-2.md")]
    ordered = sorted(paths, key=chapter_sort_key)
    assert [p.name for p in ordered] == ["chapter-2.md", "chapter-10.md"]


def test_sort_key_plain_number_strings():
    keys = sorted(["10", "2", "11", "1"], key=chapter_sort_key)
    assert keys == ["1", "2", "10", "11"]


def test_sort_key_non_numeric_stable_last():
    mixed = ["chapter-2.md", "notes.md", "chapter-10.md"]
    ordered = sorted(mixed, key=chapter_sort_key)
    assert ordered[0] == "chapter-2.md"
    assert ordered[1] == "chapter-10.md"
    assert ordered[2] == "notes.md"


def test_audit_history_numeric_order():
    """F326: _get_audit_history returns chapters in numeric order (10 after 9)."""
    from shenbi.pipeline.chapter_loop import _get_audit_history
    from shenbi.pipeline.state import ChapterState, PipelineState

    state = PipelineState()
    # Insert keys in an order that exposes lexicographic mis-sorting
    for ch in (2, 9, 10, 3):
        state.chapter_loop.chapter_states[str(ch)] = ChapterState(
            audit_results={
                "shenbi-review-continuity": {"passed": True, "hard_failures": 0, "issues": []}
            }
        )

    history = _get_audit_history(state, current_chapter=99)
    chapters = [row["chapter"] for row in history]
    assert chapters == [2, 3, 9, 10]


def test_cmd_chapters_rows_numeric_order(tmp_path: Path, capsys):
    """F326: cmd_chapters emits chapters in numeric order (real state file)."""
    import argparse
    import json

    from shenbi.pipeline import cli as pipeline_cli
    from shenbi.pipeline.machine import save_state
    from shenbi.pipeline.state import ChapterState, PipelineState

    state = PipelineState(project_dir=str(tmp_path))
    for ch in (10, 2, 9):
        state.chapter_loop.chapter_states[str(ch)] = ChapterState()
    save_state(tmp_path, state)

    rc = pipeline_cli.cmd_chapters(argparse.Namespace(project_dir=str(tmp_path)))
    assert rc == 0
    raw = capsys.readouterr().out
    out = json.loads(raw[raw.index("{") :])
    chapters = [row["chapter"] for row in out["chapters"]]
    assert chapters == [2, 9, 10]
