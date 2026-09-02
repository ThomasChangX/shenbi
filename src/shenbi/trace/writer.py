"""TraceWriter：append-only JSONL。seq 从现有 trace 接续；每条事件签名链前一条。
首次创建对父目录 fsync（判据 7 I6a）；每条 append 后对文件 fsync（durability）。

Concurrency: append() is serialized by trace.jsonl.lockfile flock (spec #37
F531/F536) and re-derives seq/prev_signature from the file inside the lock —
the __init__ cache alone would go stale under concurrent writers. compaction
(whole-file replace) takes the same lock.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)

from shenbi.contracts.enums import ActorRole
from shenbi.trace.event import GENESIS_PREV, TraceEvent

_TRACE_NAME = "trace.jsonl"


def _fsync_dir(path: Path) -> None:
    """Best-effort directory fsync (POSIX-only; no-op on Windows).

    Windows can't open directories as fds (PermissionError), and some network
    filesystems reject dir fsync. os.replace is already atomic via NTFS rename,
    so skipping is safe for durability on those platforms.
    """
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return  # Windows / network FS: can't open dirs for fsync
    try:
        os.fsync(fd)
    except OSError:
        pass  # FS doesn't support directory fsync
    finally:
        os.close(fd)


class TraceWriter:
    def __init__(self, round_dir: Path) -> None:
        self._path = Path(round_dir) / _TRACE_NAME
        self._seq = self._count_existing()
        self._prev = self._last_sig_existing()

    def _count_existing(self) -> int:
        return self._scan_existing()[0]

    def _last_sig_existing(self) -> str:
        return self._scan_existing()[1]

    def _scan_existing(self) -> tuple[int, str]:
        """One pass over the file -> (line_count, last_signature)."""
        if not self._path.exists():
            return 0, GENESIS_PREV
        count = 0
        last_sig = GENESIS_PREV
        for ln in self._path.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                last_sig = str(json.loads(ln).get("signature", GENESIS_PREV))
            except (json.JSONDecodeError, ValueError, AttributeError):
                # F608 (spec #38): torn-tail (partial last line from a crash
                # mid-write) — stop the scan at the last intact event; the
                # torn line does not count toward seq.
                log.warning("trace_torn_tail_skipped", seq=count)
                break
            count += 1
        return count, last_sig

    def next_seq(self) -> int:
        return self._seq + 1

    def last_signature(self) -> str:
        return self._prev

    def append(
        self,
        *,
        actor: str,
        actor_role: ActorRole,
        action: str,
        target: str,
        skill: str | None = None,
        gate: str | None = None,
        payload: dict[str, object] | None = None,
        schema_version: int = 1,
    ) -> TraceEvent:
        from shenbi.trace.locks import trace_lock

        with trace_lock(self._path.parent):
            # Re-derive from the file INSIDE the lock in one pass: the
            # __init__ cache is stale the moment another writer appended
            # (spec #37 F531); a single read avoids the 2x O(n) rescan.
            self._seq, self._prev = self._scan_existing()
            created = not self._path.exists()
            if created:
                self._path.parent.mkdir(parents=True, exist_ok=True)
            event = TraceEvent.sign_and_new(
                prev_signature=self._prev,
                seq=self.next_seq(),
                actor=actor,
                actor_role=actor_role,
                action=action,
                target=target,
                skill=skill,
                gate=gate,
                payload=payload or {},
                schema_version=schema_version,
            )
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(event.model_dump_json() + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            if created:
                _fsync_dir(self._path.parent)  # 判据 7 I6a
            self._seq = event.seq
            self._prev = event.signature
            return event
