"""TraceWriter：append-only JSONL。seq 从现有 trace 接续；每条事件签名链前一条。
首次创建对父目录 fsync（判据 7 I6a）；每条 append 后对文件 fsync（durability）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from shenbi.contracts.enums import ActorRole
from shenbi.trace.event import GENESIS_PREV, TraceEvent

_TRACE_NAME = "trace.jsonl"


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class TraceWriter:
    def __init__(self, round_dir: Path) -> None:
        self._path = Path(round_dir) / _TRACE_NAME
        self._seq = self._count_existing()
        self._prev = self._last_sig_existing()

    def _count_existing(self) -> int:
        if not self._path.exists():
            return 0
        return sum(1 for _ in self._path.read_text(encoding="utf-8").splitlines() if _.strip())

    def _last_sig_existing(self) -> str:
        if not self._path.exists():
            return GENESIS_PREV
        lines = [ln for ln in self._path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            return GENESIS_PREV
        return str(json.loads(lines[-1]).get("signature", GENESIS_PREV))

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
