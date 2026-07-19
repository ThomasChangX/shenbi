from __future__ import annotations

import json
import os
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


def test_safe_write_no_lockfile_leak(tmp_path: Path) -> None:
    """safe_write must never leave a .lock file behind on any platform.

    On POSIX: flock is used (no lockfile created). On Windows: the O_EXCL
    lockfile fallback is always used and must be cleaned up on release.
    """
    p = tmp_path / "out.json"
    safe_write(p, '{"k": 1}')
    assert json.loads(p.read_text(encoding="utf-8")) == {"k": 1}
    assert not (tmp_path / "out.json.lock").exists(), "lockfile leaked"
    safe_write(p, '{"k": 2}')
    assert not (tmp_path / "out.json.lock").exists()


def test_lockfile_has_correct_permissions():
    """Lockfile created by safe_write has 0o644 permissions."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.json"
        # Use _acquire_lock directly to test the lockfile path
        lockfile = Path(tmp) / "test.json.lock"
        # Create lockfile like _acquire_lock does
        fd = os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)

        # Set permissions
        os.chmod(lockfile, 0o644)

        actual_mode = lockfile.stat().st_mode & 0o777
        assert actual_mode == 0o644, f"Expected 0o644, got {oct(actual_mode)}"

        # Clean up
        os.unlink(lockfile)


def test_lockfile_permissions_are_set_via_os_chmod():
    """Verify os.chmod sets correct permissions on lockfile creation."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        lockfile = Path(tmp) / "test.lock"
        # Create lockfile like _acquire_lock does
        fd = os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)

        # Set permissions
        os.chmod(lockfile, 0o644)

        actual_mode = lockfile.stat().st_mode & 0o777
        assert actual_mode == 0o644, f"Expected 0o644, got {oct(actual_mode)}"

        # Clean up
        os.unlink(lockfile)


@pytest.mark.skipif(sys.platform == "win32", reason="fcntl is POSIX-only")
def test_safe_write_lockfile_fallback_cleanup_posix(tmp_path: Path, monkeypatch) -> None:
    """Force the flock fallback path on POSIX to verify lockfile cleanup.

    Regression: safe_write only closed the fd, leaving a permanent stale lock
    that forced every later writer through the 1s backoff + stale-takeover path.
    """
    import fcntl

    def boom(fd: int, op: int) -> None:
        raise OSError("flock unavailable (test)")

    monkeypatch.setattr(fcntl, "flock", boom)
    p = tmp_path / "out.json"
    safe_write(p, '{"k": 1}')
    assert not (tmp_path / "out.json.lock").exists(), "O_EXCL lockfile leaked on release"
    safe_write(p, '{"k": 2}')
    assert not (tmp_path / "out.json.lock").exists()
