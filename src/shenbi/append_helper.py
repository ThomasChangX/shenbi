"""append_jsonl: unified fsync + timestamp + directory-lock JSONL append (spec #37 F534).

safe_write is temp+replace (whole-file) and therefore incompatible with
append-only ledgers (write-audit.jsonl, audit trail, token ledger). This
helper gives those writers one consistent shape: an ISO timestamp field,
fsync per append, and the same directory-flock domain as safe_write so
appenders and replacers on one directory mutually exclude.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.safe_write import acquire_write_lock

log = get_logger(__name__)


def append_jsonl(
    path: Path,
    record: dict[str, Any],
    *,
    timestamp_field: str = "timestamp",
) -> None:
    """Append one JSON record with a timestamp, fsync, under the directory lock."""
    stamped = dict(record)
    stamped.setdefault(timestamp_field, datetime.now(UTC).isoformat(timespec="seconds"))
    line = json.dumps(stamped, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)  # write-path only (T407)
    lock_fd, lockfile = acquire_write_lock(path)
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())  # durability: survive crash after append
    finally:
        os.close(lock_fd)
        if lockfile is not None:
            try:
                lockfile.unlink()
            except FileNotFoundError:
                pass  # already released by a concurrent stale-takeover
