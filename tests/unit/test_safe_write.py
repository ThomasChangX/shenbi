from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

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


@pytest.mark.skipif(sys.platform == "win32", reason="fcntl is POSIX-only")
def test_safe_write_removes_o_excl_lockfile_on_release(tmp_path: Path, monkeypatch) -> None:
    """Lockfile fallback (M5): the O_EXCL .lock must be unlinked on release.

    Regression: safe_write only closed the fd, leaving a permanent stale lock
    that forced every later writer through the 1s backoff + stale-takeover path.
    """
    import fcntl

    def boom(fd: int, op: int) -> None:
        raise OSError("flock unavailable (test)")

    monkeypatch.setattr(fcntl, "flock", boom)
    p = tmp_path / "out.json"
    safe_write(p, '{"k": 1}')
    assert json.loads(p.read_text(encoding="utf-8")) == {"k": 1}
    # The fallback lockfile must not be left behind after a successful write.
    assert not (tmp_path / "out.json.lock").exists(), "O_EXCL lockfile leaked on release"
    # A second write must not inherit a stale lock from the first.
    safe_write(p, '{"k": 2}')
    assert json.loads(p.read_text(encoding="utf-8")) == {"k": 2}
    assert not (tmp_path / "out.json.lock").exists()
