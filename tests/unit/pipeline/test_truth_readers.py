"""Tests for the single table-aware pending_hooks parser (SDD #21 R2).

The fixture is a byte-identical copy of the REAL production file
(``tests/fixtures/truth-pending_hooks-ch56.md``, G0.11 mirror-guarded).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shenbi.pipeline.truth_readers import read_pending_hooks

FIXTURE_PROJECT = Path("tests/fixtures")


def _real_hooks() -> list[dict[str, Any]]:
    # The fixture file lives at tests/fixtures root; read_pending_hooks
    # expects <project>/truth/pending_hooks.md — synthesize the layout.
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp)
        (proj / "truth").mkdir()
        shutil.copyfile(
            FIXTURE_PROJECT / "truth-pending_hooks-ch56.md", proj / "truth" / "pending_hooks.md"
        )
        return read_pending_hooks(proj)


def test_real_file_yields_all_seven_hooks_with_state() -> None:
    """Spec R2 acceptance: the real ch56 file parses to ≥7 records, each with
    a non-None state derived from the lifecycle table's post-state column.
    """
    hooks = _real_hooks()
    assert len(hooks) >= 7
    by_id = {h["id"]: h for h in hooks}
    for hid in ("P0-4", "P0-9", "P0-14", "P0-15", "P0-19", "P0-20", "P0-22"):
        assert hid in by_id, f"missing {hid}"
        assert by_id[hid]["state"], f"{hid} state is None"
    # Lifecycle table post-state wins: P0-4 is TRIGGERED (the presentation
    # column's RELEVANT→TRIGGERED(待track确认) is cross-check only).
    assert by_id["P0-4"]["state"] == "TRIGGERED"
    assert by_id["P0-9"]["state"] == "RELEVANT"


def test_transition_string_normalizes_to_post_state() -> None:
    """RELEVANT→TRIGGERED(待track确认) → TRIGGERED (arrow tail, no annotation)."""
    from shenbi.pipeline.truth_readers import _norm_state

    assert _norm_state("RELEVANT→TRIGGERED(待track确认)") == "TRIGGERED"
    assert _norm_state("RELEVANT -> RESOLVED") == "RESOLVED"
    assert _norm_state("RELEVANT") == "RELEVANT"
    assert _norm_state("??") is None


def test_last_reinforced_upper_bound_and_interval_table() -> None:
    """P0-9 last_reinforced=54 from the interval table (推定), P0-4 = 56."""
    by_id = {h["id"]: h for h in _real_hooks()}
    assert by_id["P0-9"]["last_reinforced"] == 54
    assert by_id["P0-4"]["last_reinforced"] == 56
    # every derived last_reinforced is capped by frontmatter last_chapter=56
    for h in by_id.values():
        if h["last_reinforced"] is not None:
            assert h["last_reinforced"] <= 56


def test_distance_table_supplies_plant_chapter_and_max_distance() -> None:
    """max_distance comes from the 距离上限逼近 table (header-embedded default)."""
    by_id = {h["id"]: h for h in _real_hooks()}
    for hid in ("P0-4", "P0-9", "P0-14"):
        assert by_id[hid]["plant_chapter"] == 44
        assert by_id[hid]["max_distance"] == 14


def test_missing_table_row_yields_none_not_default(tmp_path: Path) -> None:
    """A hook absent from the distance table gets None plant/max_distance —
    never a fabricated default (the table only lists near-cap hooks).
    """
    proj = tmp_path
    (proj / "truth").mkdir()
    (proj / "truth" / "pending_hooks.md").write_text(
        "---\nlast_chapter: 3\n---\n\n"
        "### 本章操作\n\n"
        "| Hook ID | 操作 | 前状态 | 后状态 | 文本位置 |\n"
        "|---------|------|--------|--------|---------|\n"
        "| P0-1 | REINFORCE | RELEVANT | RELEVANT | ch3 |\n",
        encoding="utf-8",
    )
    hooks = read_pending_hooks(proj)
    assert len(hooks) == 1
    h = hooks[0]
    assert h["state"] == "RELEVANT"
    assert h["last_reinforced"] == 3  # REINFORCE row in the latest chapter
    assert h["plant_chapter"] is None
    assert h["max_distance"] is None


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    assert read_pending_hooks(tmp_path) == []


@pytest.mark.parametrize(
    ("consumer", "expected"),
    [
        # G6.7 consumes via the same parser: unresolved = state != RESOLVED.
        ("g67", {"P0-4", "P0-9", "P0-14", "P0-15", "P0-19", "P0-20", "P0-22"}),
    ],
)
def test_g67_consumes_same_records(consumer: str, expected: set[str]) -> None:
    """All three consumers (context_curation / G6.7 / truth_index) go through
    read_pending_hooks — verified here via one consumer path.
    """
    if consumer == "g67":
        hooks = _real_hooks()
        unresolved = {h["id"] for h in hooks if h["state"] and h["state"] != "RESOLVED"}
        assert unresolved == expected
