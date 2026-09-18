"""Carrier guard for the xinghuo-ranqiong upstream-copy fixture tree (spec #66 F750).

Byte-fidelity vs git history (d120a444^) is a one-off acceptance command run
on a full clone (spec AC#4) — CI quality workflows use shallow clones
(fetch-depth=1), so this permanent guard checks tree completeness and
provenance carriers only, with no git dependency.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g0_purity import load_provenance

# tests/unit/gates/<file>.py → parents[3] = repo root（对齐 test_g0.py:317 先例）
FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "xinghuo-ranqiong"
EXPECTED_FILES = frozenset(
    {
        "novel.json",
        "world/story_bible.md",
        "world/rules.md",
        "truth/current_state.md",
        "truth/character_matrix.md",
        "truth/emotional_arcs.md",
        "truth/chapter_summaries.md",
        "characters/protagonist.md",
    }
)


@pytest.mark.unit
def test_xinghuo_fixture_tree_complete_with_carriers() -> None:
    files = {
        p.relative_to(FIXTURE_ROOT).as_posix()
        for p in FIXTURE_ROOT.rglob("*")
        if p.is_file() and p.suffix in (".md", ".json") and not p.name.endswith(".provenance.json")
    }
    assert files == EXPECTED_FILES
    for rel in sorted(EXPECTED_FILES):
        assert load_provenance(FIXTURE_ROOT / rel) == "upstream-copy", rel
