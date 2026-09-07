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


@pytest.mark.skipif(sys.platform == "win32", reason="fcntl is POSIX-only")
def test_lockfile_mutual_exclusion_via_acquire_lock(tmp_path: Path, monkeypatch) -> None:
    """A second _acquire_lock on a held lock must not succeed within the window."""
    import fcntl
    import threading

    from shenbi.safe_write import _acquire_lock

    def boom(fd: int, op: int) -> None:
        raise OSError("flock unavailable (test)")

    monkeypatch.setattr(fcntl, "flock", boom)  # force O_EXCL lockfile path
    target = tmp_path / "data.json"
    target.write_text("{}", encoding="utf-8")
    fd1, lock1 = _acquire_lock(target)
    assert fd1 >= 0
    assert lock1 is not None  # O_EXCL fallback produced a real lockfile

    results: dict[str, object] = {}

    def try_second() -> None:
        try:
            fd2, lock2 = _acquire_lock(target)
            results["second"] = (fd2, lock2)
            os.close(fd2)
            if lock2 is not None:
                lock2.unlink()
        except Exception as exc:
            results["error"] = exc

    t = threading.Thread(
        target=try_second, daemon=True
    )  # daemon: never hang the suite on a failure
    t.start()
    t.join(timeout=2.0)
    # Snapshot INSIDE the held-lock window; after release the waiter may
    # legitimately acquire, so asserting post-release would be a false red.
    acquired_during_window = "second" in results
    os.close(fd1)
    lock1.unlink()
    t.join(timeout=2.0)
    assert not acquired_during_window, f"mutual exclusion broken: {results.get('second')}"


@pytest.mark.skipif(sys.platform == "win32", reason="fcntl is POSIX-only")
def test_lockfile_fallback_sets_0o600(tmp_path: Path, monkeypatch) -> None:
    """The O_EXCL fallback lockfile produced by _acquire_lock has 0o600 perms."""
    import fcntl

    from shenbi.safe_write import _acquire_lock

    def boom(fd: int, op: int) -> None:
        raise OSError("flock unavailable (test)")

    monkeypatch.setattr(fcntl, "flock", boom)
    target = tmp_path / "data.json"
    target.write_text("{}", encoding="utf-8")
    fd, lockfile = _acquire_lock(target)
    assert lockfile is not None
    actual_mode = lockfile.stat().st_mode & 0o777
    assert actual_mode == 0o600, f"Expected 0o600, got {oct(actual_mode)}"
    os.close(fd)
    lockfile.unlink()


@pytest.mark.skipif(sys.platform == "win32", reason="fcntl is POSIX-only")
def test_safe_write_lockfile_fallback_cleanup_posix(tmp_path: Path, monkeypatch) -> None:
    """Force the flock fallback path on POSIX to verify lockfile cleanup.

    Regression: safe_write only closed the fd, leaving a permanent stale lock
    that forced every later writer through the 1s backoff + stale-takeover path.
    """
    import fcntl  # POSIX-only; see module skipif guard on these tests

    def boom(fd: int, op: int) -> None:
        raise OSError("flock unavailable (test)")

    monkeypatch.setattr(fcntl, "flock", boom)
    p = tmp_path / "out.json"
    safe_write(p, '{"k": 1}')
    assert not (tmp_path / "out.json.lock").exists(), "O_EXCL lockfile leaked on release"
    safe_write(p, '{"k": 2}')
    assert not (tmp_path / "out.json.lock").exists()


def test_stale_takeover_requires_stale_lock(tmp_path, monkeypatch):
    """A FRESH lockfile must not be unconditionally seized (spec #37 T603/F111)."""
    import fcntl  # POSIX-only; see module skipif guard on these tests

    monkeypatch.setattr(fcntl, "flock", lambda *a, **k: (_ for _ in ()).throw(OSError("forced")))
    from shenbi.safe_write import _acquire_lock

    target = tmp_path / "data.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    lockfile = tmp_path / "data.json.lock"
    lockfile.write_text("999999\n", encoding="utf-8")  # fresh lock, dead pid
    import os
    import time

    past = time.time() - 3600
    os.utime(lockfile, (past, past))  # stale by mtime
    fd, lf = _acquire_lock(target)  # stale by age -> takeover allowed
    assert lf == lockfile
    os.close(fd)


def test_stale_takeover_blocked_on_fresh_lock(tmp_path, monkeypatch):
    """A lockfile younger than the staleness TTL must NOT be taken over."""
    import fcntl  # POSIX-only; see module skipif guard on these tests

    monkeypatch.setattr(fcntl, "flock", lambda *a, **k: (_ for _ in ()).throw(OSError("forced")))
    import pytest

    import shenbi.safe_write as sw

    monkeypatch.setattr(sw, "LOCK_WAIT_TIMEOUT", 0.5)  # speed up the wait

    target = tmp_path / "data.json"
    lockfile = tmp_path / "data.json.lock"
    lockfile.write_text("999999\n", encoding="utf-8")  # just created -> fresh
    assert sw.STALE_LOCK_TTL > 0
    with pytest.raises(TimeoutError):
        sw._acquire_lock(target)


def test_stale_takeover_blocked_on_live_pid(tmp_path, monkeypatch):
    """A stale-mtime lock held by a LIVE pid must not be taken over."""
    import fcntl  # POSIX-only; see module skipif guard on these tests
    import os
    import subprocess
    import time

    monkeypatch.setattr(fcntl, "flock", lambda *a, **k: (_ for _ in ()).throw(OSError("forced")))
    import pytest

    import shenbi.safe_write as sw

    monkeypatch.setattr(sw, "LOCK_WAIT_TIMEOUT", 0.5)
    holder = subprocess.Popen(["sleep", "30"])
    try:
        target = tmp_path / "data.json"
        lockfile = tmp_path / "data.json.lock"
        lockfile.write_text(f"{holder.pid}\n", encoding="utf-8")
        past = time.time() - 3600
        os.utime(lockfile, (past, past))  # stale by mtime, but holder alive
        with pytest.raises(TimeoutError):
            sw._acquire_lock(target)
        assert lockfile.exists()  # not robbed
    finally:
        holder.kill()
        holder.wait()
