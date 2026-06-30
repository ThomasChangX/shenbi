"""safe_write: sole atomic-write entry for framework state (spec pillar 4 Tier A).

temp + fsync(file) + os.replace(atomic) + fsync(dir) + fcntl.flock;
on flock-unavailable, falls back to a lockfile (M5). Optionally appends a
trace event via TraceWriter. ASCII docstring: matches src/shenbi/*.py whose
ruff ignore list omits RUF002 (ambiguous-unicode-in-docstring).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    except OSError as e:  # 某些 FS 不支持目录 fsync
        log.debug("dir_fsync_unsupported", path=str(path), error=str(e))
    finally:
        os.close(fd)


def _acquire_lock(path: Path) -> tuple[int, Path | None]:
    """Acquire exclusive lock on parent dir; return (fd, lockfile_to_unlink).

    The fd must stay open across os.replace+fsync for the lock to be held.
    Returns (fd, None) for flock locking (lock releases on close) or
    (fd, lockfile_path) for the M5 O_EXCL fallback — the caller MUST unlink
    lockfile_path on release, since an O_EXCL lock is existence-based and
    closing the fd alone does not free it.
    """
    # fcntl is POSIX-only. Guarding with sys.platform lets mypy narrow the
    # platform context: on win32 the flock branch is unreachable (no
    # attr-defined error); on POSIX flock/LOCK_EX always resolve (no
    # unused-ignore). This avoids a type: ignore that would be needed on one
    # platform but flagged as unused on the other.
    if sys.platform != "win32":
        try:
            import fcntl

            fd = os.open(str(path.parent), os.O_RDONLY)
            fcntl.flock(fd, fcntl.LOCK_EX)
            return fd, None  # caller closes to release
        except (ImportError, OSError):
            pass  # flock unavailable → fall through to O_EXCL lockfile fallback
    # M5 fallback: O_EXCL lockfile (used on Windows or when flock fails).
    lockfile = path.parent / (path.name + ".lock")
    # Franklin Important: M5 fallback with O_EXCL for real mutual exclusion
    # (touch() grants zero exclusion — two writers both proceed).
    try:
        return os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY), lockfile
    except FileExistsError:
        # Another writer holds the lock — retry with backoff
        import time

        for _attempt in range(10):
            time.sleep(0.1)
            try:
                return (
                    os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY),
                    lockfile,
                )
            except FileExistsError:  # retry with backoff
                continue
        # Stale lock takeover (Helmholtz P3 fix): unlink + recreate with O_EXCL.
        # After 1s of backoff the lock is likely stale (crash left it behind).
        try:
            os.unlink(str(lockfile))
        except FileNotFoundError:
            pass  # already gone — safe to proceed with O_EXCL recreate
        return os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY), lockfile


def safe_write(
    path: Path,
    data: bytes | str,
    *,
    round_dir: Path | None = None,
    trace_action: str | None = None,
    trace_target: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd, lockfile = _acquire_lock(path)  # held open across write (I3)
    payload = data if isinstance(data, bytes) else data.encode("utf-8")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    finally:
        os.close(lock_fd)  # release flock (or close lockfile fd) AFTER os.replace+fsync
        if lockfile is not None:
            # M5 O_EXCL lockfile: release by unlinking — existence-based lock,
            # so closing the fd alone leaves a permanent stale lock + race.
            try:
                os.unlink(lockfile)
            except FileNotFoundError:
                pass  # already gone — concurrent stale-takeover cleaned it up
    if round_dir is not None and trace_action is not None:
        from shenbi.trace.writer import TraceWriter  # 局部 import 避免循环

        # Franklin Important: trace append can crash if trace.jsonl has a torn tail.
        # The write already succeeded — don't let a trace error undo the caller's success signal.
        try:
            TraceWriter(round_dir).append(
                actor="safe_write",
                actor_role="GATE",
                action=trace_action,
                target=trace_target or path.name,
                payload={"path": str(path)},
            )
        except Exception:
            log.warning("safe_write_trace_append_failed", path=str(path), exc_info=True)
