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
from typing import TYPE_CHECKING, Any

from shenbi.logging import get_logger

log = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable


def _fsync_dir(path: Path) -> None:
    """Best-effort directory fsync after atomic replace (POSIX-only).

    Windows can't open directories as fds (PermissionError); on some network
    filesystems os.fsync(dir) is unsupported. os.replace is already atomic
    via NTFS rename, so skipping is safe for durability.
    """
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return  # Windows / network FS: can't open dirs for fsync
    try:
        os.fsync(fd)
    except OSError as e:  # 某些 FS 不支持目录 fsync
        log.debug("dir_fsync_unsupported", path=str(path), error=str(e))
    finally:
        os.close(fd)


#: Staleness proof thresholds for the O_EXCL fallback (spec #37 T603/F111).
STALE_LOCK_TTL = 60.0  # seconds without mtime heartbeat -> lock assumed crashed
LOCK_WAIT_TIMEOUT = 10.0  # total backoff budget before failing the acquire
_LOCK_POLL_INTERVAL = 0.1


def _write_lock_holder(lockfile: Path, fd: int) -> None:
    """Record holder pid for liveness proof (best-effort; POSIX path only)."""
    try:
        os.write(fd, f"{os.getpid()}\n".encode())
        os.fsync(fd)
    except OSError:
        # holder pid is advisory for staleness proofs — failure to record it
        # must not fail the lock acquisition itself.
        pass


def _lock_is_stale(lockfile: Path) -> bool:
    """True only with a staleness PROOF: mtime older than TTL and holder dead."""
    import time

    try:
        age = time.time() - lockfile.stat().st_mtime
    except OSError:
        return True  # vanished -> nothing to take over (retry O_EXCL)
    if age < STALE_LOCK_TTL:
        return False
    # Age alone is not proof on POSIX — a live holder that merely went quiet
    # must not be robbed. Check the recorded pid when present.
    if sys.platform != "win32":
        try:
            pid_txt = lockfile.read_text(encoding="utf-8").strip()
            pid = int(pid_txt) if pid_txt.isdigit() else 0
        except (OSError, ValueError):
            pid = 0
        if pid and pid != os.getpid() and _pid_alive(pid):
            return False  # holder alive -> keep waiting
    return True


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user


def _unlink_if_same(lockfile: Path, inode: int) -> bool:
    """Unlink ONLY if the lockfile is still the one we judged stale.

    Two waiters can both judge stale; if B already took over (unlinked +
    recreated), A's blind unlink would delete B's FRESH lock and break
    mutual exclusion. Comparing inodes across the judgment->unlink gap
    closes that takeover race (spec #37 T603 residual).
    """
    try:
        if lockfile.stat().st_ino != inode:
            return False  # replaced by another taker — do not touch
        os.unlink(str(lockfile))
        return True
    except FileNotFoundError:
        return True  # already gone — O_EXCL retry is safe
    except OSError:
        return False


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
        fd = os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.chmod(lockfile, 0o600)
        _write_lock_holder(lockfile, fd)
        return fd, lockfile
    except FileExistsError:
        # Another writer holds the lock — retry with backoff, and only take
        # over a lock PROVEN stale (spec #37 T603/F111: the old code unlinked
        # unconditionally after 1s, breaking mutual exclusion for any writer
        # slower than the backoff window).
        import time

        deadline = time.monotonic() + LOCK_WAIT_TIMEOUT
        while time.monotonic() < deadline:
            time.sleep(_LOCK_POLL_INTERVAL)
            try:
                fd = os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.chmod(lockfile, 0o600)
                _write_lock_holder(lockfile, fd)
                return fd, lockfile
            except FileExistsError:
                try:
                    inode = lockfile.stat().st_ino
                except OSError:
                    continue  # vanished — retry O_EXCL
                if _lock_is_stale(lockfile) and _unlink_if_same(lockfile, inode):
                    continue  # proven-stale takeover (same inode we judged)
                continue
        if sys.platform == "win32":  # pragma: no cover — POSIX-authoritative
            log.warning("lock_takeover_timeout_fallback", lockfile=str(lockfile))
            try:
                os.unlink(str(lockfile))
            except FileNotFoundError:
                pass
            fd = os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.chmod(lockfile, 0o600)
            return fd, lockfile
        raise TimeoutError(
            f"lock wait timed out after {LOCK_WAIT_TIMEOUT}s on {lockfile}"
        ) from None


#: Public alias: cross-instance writers (TokenLedger.append) need the same
#: directory-lock domain as safe_write without rewriting the payload path.
acquire_write_lock = _acquire_lock


def locked_transact(
    path: Path,
    mutator: Callable[[Any], Any],
    *,
    round_dir: Path | None = None,
    trace_action: str | None = None,
) -> object:
    """Lock a whole read-modify-write cycle on *path* (spec #37 F206/F347).

    Holds the directory lock across read -> mutator -> atomic write so
    concurrent transactors cannot interleave. Plain safe_write only locks
    the write, leaving the read outside the critical section (TOCTOU).

    JSON files: the mutator receives the parsed dict (or {} for a missing
    file); in-place mutation is applied, a non-None return value wins.
    Any other file: the mutator receives the raw str and returns a str.
    """
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd, lockfile = _acquire_lock(path)
    try:
        raw = path.read_text(encoding="utf-8") if path.exists() else None
        if path.suffix == ".json":
            data = json.loads(raw) if raw else {}
            result = mutator(data)
            payload = json.dumps(
                result if result is not None else data, indent=2, ensure_ascii=False
            )
        else:
            result = mutator(raw)
            payload = str(result if result is not None else (raw or ""))
        _write_payload(path, payload)
    finally:
        os.close(lock_fd)
        if lockfile is not None:
            try:
                os.unlink(lockfile)
            except FileNotFoundError:
                pass
    # Trace seam AFTER lock release (same placement as safe_write): emitting
    # it under the directory flock would take dir-flock -> trace-per-path,
    # inverting the L2 fixed order (per-path -> dir flock).
    if round_dir is not None and trace_action is not None:
        from shenbi.trace.writer import TraceWriter

        try:
            TraceWriter(round_dir).append(
                actor="safe_write",
                actor_role="GATE",
                action=trace_action,
                target=path.name,
                payload={"path": str(path)},
            )
        except Exception:
            log.warning("safe_write_trace_append_failed", path=str(path), exc_info=True)
    return result


def _write_payload(
    path: Path,
    payload: str,
    *,
    round_dir: Path | None = None,
    trace_action: str | None = None,
    trace_target: str | None = None,
) -> None:
    """Temp + fsync + atomic replace + dir fsync + best-effort trace seam.

    Locking is the caller's responsibility (flock conflicts across fds even
    within one process, so a nested safe_write would self-deadlock).
    """
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload.encode("utf-8"))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
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
    try:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data if isinstance(data, bytes) else data.encode("utf-8"))
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
