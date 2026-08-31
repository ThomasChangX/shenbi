"""Per-path cross-process lock for trace.jsonl (spec #37 F531/F536/F619).

TraceWriter.append (seq/signature chain derivation + JSONL append) and
compaction (whole-file replace) must be mutually exclusive across threads
AND processes. A dedicated lockfile flock provides that; the writer's
directory-flock (safe_write) cannot be reused here because flock conflicts
across fds even within one process — nesting it would self-deadlock.

Lockfile debris (``trace.jsonl.lockfile``) is gitignored and lazily reused
(pipeline-state.json.lockfile precedent).
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from collections.abc import Generator
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)

_LOCK_SUFFIX = ".lockfile"
_DEFAULT_TIMEOUT = 30.0


@contextmanager
def trace_lock(
    round_dir: Path, *, timeout: float = _DEFAULT_TIMEOUT
) -> Generator[None, None, None]:
    """Hold an exclusive flock on ``<round_dir>/trace.jsonl.lockfile``."""
    lockfile = Path(round_dir) / ("trace.jsonl" + _LOCK_SUFFIX)
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":  # pragma: no cover — POSIX-authoritative per spec
        yield
        return
    import fcntl
    import time

    fd = os.open(str(lockfile), os.O_CREAT | os.O_RDONLY)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError):
                if time.monotonic() > deadline:
                    raise TimeoutError(
                        f"trace lock timed out after {timeout}s on {lockfile}"
                    ) from None
                time.sleep(0.05)
        yield
    finally:
        os.close(fd)  # releases the flock
