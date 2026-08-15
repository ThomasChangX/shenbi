"""R3: parameterized G4 directory validation (F371) — snapshot-family dirs
require a manifest-named entry; characters/ does not.

G0.9 boundary ruling (spec #6 R3 / plan I10): directory-content files are
real production snapshot copies (crash_recovery format); manifest.json is a
gate-internal test input, not a skill-output scenario claim — the real
snapshot-manage-format fixture belongs to spec #26's wiring acceptance.
"""

import json
import shutil
from pathlib import Path
from typing import Any

from shenbi.gates.g4.generic import g4_generic_generative

_SNAP_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "snapshot-dir"


def _result(raw: str) -> dict[str, Any]:
    return json.loads(raw)


def test_dir_with_files_and_manifest_passes(tmp_path):
    d = tmp_path / "snapshots" / "chapter-100"
    d.mkdir(parents=True)
    srcs = sorted(_SNAP_FIXTURE.glob("*.md"))[:2]
    for s in srcs:
        shutil.copy(s, d / s.name)
    (d / "manifest.json").write_text('{"files": []}', encoding="utf-8")
    r = _result(g4_generic_generative([str(d)]))
    assert r["status"] == "PASS"


def test_snapshot_dir_without_manifest_fails(tmp_path):
    d = tmp_path / "snapshots" / "chapter-100"
    d.mkdir(parents=True)
    shutil.copy(sorted(_SNAP_FIXTURE.glob("*.md"))[0], d / "snap.md")
    r = _result(g4_generic_generative([str(d)]))
    assert r["status"] == "FAIL"
    assert any("manifest_missing" in m for m in r["must_fix"])  # fail() key (gates/shared.py)


def test_characters_dir_no_manifest_required(tmp_path):
    """Acceptance: characters/ (non-snapshot) passes without a manifest."""
    d = tmp_path / "characters"
    d.mkdir()
    (d / "c-1.md").write_text("# 主角\n" + "设定 " * 30, encoding="utf-8")
    r = _result(g4_generic_generative([str(d)]))
    assert r["status"] == "PASS"


def test_empty_dir_fails(tmp_path):
    d = tmp_path / "final-snapshot"
    d.mkdir()
    r = _result(g4_generic_generative([str(d)]))
    assert r["status"] == "FAIL"
    assert any("dir_empty" in m for m in r["must_fix"])


def test_closure_snapshot_dir_resolution(tmp_path):
    """Closure step 10 G4 path = snapshots/chapter-{total:03d}/."""
    from shenbi.pipeline.closure import _closure_snapshot_dir

    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "novel.json").write_text(json.dumps({"total_chapters": 100}), encoding="utf-8")
    assert _closure_snapshot_dir(proj) == "snapshots/chapter-100/"
    # total unknown -> "" (G4 skips), never a fabricated chapter-000 dir
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "novel.json").write_text(json.dumps({}), encoding="utf-8")
    assert _closure_snapshot_dir(empty) == ""
