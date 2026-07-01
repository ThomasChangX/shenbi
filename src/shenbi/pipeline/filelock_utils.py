"""Read/write lock separation for multi-user pipeline concurrency.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 2.4.

- WriteLock: exclusive (fcntl LOCK_EX), used by next/review/resume/rollback/init
- ReadLock: shared (fcntl LOCK_SH), used by status/chapters

Both operate on the SAME lockfile (pipeline-state.json.lockfile) so that
LOCK_EX and LOCK_SH provide correct reader-writer mutual exclusion on POSIX.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shenbi.logging import get_logger

log = get_logger(__name__)

LOCKFILE_NAME = "pipeline-state.json.lockfile"
DEFAULT_WRITE_TIMEOUT = 300.0
DEFAULT_READ_TIMEOUT = 30.0
_POLL_INTERVAL = 0.05  # seconds between non-blocking flock retries

if TYPE_CHECKING:
    from collections.abc import Callable


def _flock_acquire(fd: int, shared: bool, timeout: float, lockfile: Path) -> None:
    """Acquire a POSIX advisory lock via non-blocking flock with retry.

    Polls every ``_POLL_INTERVAL`` until the lock is granted or ``timeout``
    elapses, then raises :class:`TimeoutError`.
    """
    import fcntl

    operation = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, operation | fcntl.LOCK_NB)
            return
        except (BlockingIOError, OSError):
            if time.monotonic() > deadline:
                raise TimeoutError(f"Lock timed out after {timeout}s on {lockfile}") from None
            time.sleep(_POLL_INTERVAL)


def _flock_release(fd: int) -> None:
    """Release a POSIX advisory lock."""
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_UN)


def _windows_acquire(lockfile: Path, timeout: float) -> tuple[Any, Callable[[], None]]:
    """Acquire a Windows-exclusive lock via the filelock package.

    Returns (lock_obj, release_fn). On POSIX this is never called.
    """
    # importlib avoids a static ``import filelock`` that would fail mypy
    # in the pre-commit venv (which lacks the filelock dependency).
    import importlib

    filelock_cls = importlib.import_module("filelock").FileLock
    lock = filelock_cls(str(lockfile), timeout=timeout)
    lock.acquire()
    return lock, lock.release


class WriteLock:
    """Exclusive write lock (fcntl LOCK_EX).

    Blocks all readers and other writers until released. Default 300s timeout
    because next-chapter generation can run for minutes.
    """

    def __init__(self, project_dir: Path | str, timeout: float = DEFAULT_WRITE_TIMEOUT) -> None:
        """Store lockfile path, timeout, and initial fd/fallback state."""
        self._lockfile = Path(project_dir) / LOCKFILE_NAME
        self._lockfile.parent.mkdir(parents=True, exist_ok=True)
        self._timeout = timeout
        self._fd: int | None = None
        self._release_fn: Callable[[], None] | None = None

    def __enter__(self) -> WriteLock:
        """Acquire the exclusive lock (blocks competing readers and writers)."""
        if sys.platform != "win32":
            self._fd = os.open(str(self._lockfile), os.O_CREAT | os.O_RDONLY)
            try:
                _flock_acquire(
                    self._fd, shared=False, timeout=self._timeout, lockfile=self._lockfile
                )
            except BaseException:
                os.close(self._fd)
                self._fd = None
                raise
        else:  # pragma: no cover
            _, self._release_fn = _windows_acquire(self._lockfile, self._timeout)
        log.debug("write_lock_acquired", lockfile=str(self._lockfile))
        return self

    def __exit__(self, *args: object) -> None:
        """Release the exclusive lock and close the underlying file descriptor."""
        if self._fd is not None:
            _flock_release(self._fd)
            os.close(self._fd)
            self._fd = None
        if self._release_fn is not None:  # pragma: no cover
            self._release_fn()
            self._release_fn = None
        log.debug("write_lock_released", lockfile=str(self._lockfile))


class ReadLock:
    """Shared read lock (fcntl LOCK_SH).

    Multiple readers can hold the lock simultaneously; a WriteLock (LOCK_EX)
    blocks until all readers release. Default 30s timeout.
    """

    def __init__(self, project_dir: Path | str, timeout: float = DEFAULT_READ_TIMEOUT) -> None:
        """Store lockfile path, timeout, and initial fd/fallback state."""
        self._lockfile = Path(project_dir) / LOCKFILE_NAME
        self._lockfile.parent.mkdir(parents=True, exist_ok=True)
        self._timeout = timeout
        self._fd: int | None = None
        self._release_fn: Callable[[], None] | None = None

    def __enter__(self) -> ReadLock:
        """Acquire the shared lock (allows concurrent readers, blocks writers)."""
        if sys.platform != "win32":
            self._fd = os.open(str(self._lockfile), os.O_CREAT | os.O_RDONLY)
            try:
                _flock_acquire(
                    self._fd, shared=True, timeout=self._timeout, lockfile=self._lockfile
                )
            except BaseException:
                os.close(self._fd)
                self._fd = None
                raise
        else:  # pragma: no cover
            _, self._release_fn = _windows_acquire(self._lockfile, self._timeout)
        log.debug("read_lock_acquired", lockfile=str(self._lockfile))
        return self

    def __exit__(self, *args: object) -> None:
        """Release the shared lock and close the underlying file descriptor."""
        if self._fd is not None:
            _flock_release(self._fd)
            os.close(self._fd)
            self._fd = None
        if self._release_fn is not None:  # pragma: no cover
            self._release_fn()
            self._release_fn = None
        log.debug("read_lock_released", lockfile=str(self._lockfile))
