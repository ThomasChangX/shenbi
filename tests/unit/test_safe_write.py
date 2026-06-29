from __future__ import annotations

import json
from pathlib import Path

from shenbi.safe_write import safe_write


def test_safe_write_persists_content(tmp_path: Path) -> None:
    p = tmp_path / "out.json"
    safe_write(p, '{"x":1}')
    assert json.loads(p.read_text(encoding="utf-8")) == {"x": 1}


def test_safe_write_atomic_no_residue(tmp_path: Path) -> None:
    p = tmp_path / "out.json"
    safe_write(p, "first")
    safe_write(p, "second")
    assert p.read_text(encoding="utf-8") == "second"
    assert [f.name for f in tmp_path.iterdir() if ".tmp" in f.name] == []


def test_safe_write_accepts_bytes(tmp_path: Path) -> None:
    p = tmp_path / "bin.dat"
    safe_write(p, b"\x00\x01")
    assert p.read_bytes() == b"\x00\x01"


def test_safe_write_traces_when_round_given(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    safe_write(
        rd / "progress.json",
        "{}",
        round_dir=rd,
        trace_action="MATERIALIZE",
        trace_target="progress.json",
    )
    assert (rd / "trace.jsonl").exists()
    rec = json.loads((rd / "trace.jsonl").read_text(encoding="utf-8").strip())
    assert rec["action"] == "MATERIALIZE"
