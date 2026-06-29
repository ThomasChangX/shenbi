"""compaction（判据 7 I6b + N4 + New-G）。COMPACTION 事件成为 trace 新首条，
payload={prev_compaction_seq, snapshot, truncated_at_seq}。旧事件被截断，
历史保存在 snapshot。verify_chain 校验 COMPACTION 的 prev_compaction_seq
链单调无缺口；首条可为 None（LEGACY_MIGRATION 合法锚）。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from shenbi.trace.event import GENESIS_PREV, TraceEvent
from shenbi.trace.replay import replay


def compact(round_dir: Path, snapshot: dict[str, object]) -> TraceEvent:
    """Compact the current trace: rewrite to a fresh file with one COMPACTION event.

    N2 fix: crash-safe via temp+fsync+os.replace+dir-fsync (mirrors safe_write),
    so a mid-compaction crash cannot leave an empty trace.jsonl. The COMPACTION
    head is built directly via TraceEvent.sign_and_new (no stale TraceWriter).
    """
    path = Path(round_dir) / "trace.jsonl"
    prev_events = replay(round_dir)
    prev_compaction_seq: int | None = None
    truncated_at = 0
    for e in prev_events:
        if e.action == "COMPACTION":
            prev_compaction_seq = e.seq
        truncated_at = max(truncated_at, e.seq)

    # Build the new COMPACTION head as the sole event (seq=1, prev=GENESIS).
    head_event = TraceEvent.sign_and_new(
        prev_signature=GENESIS_PREV,
        seq=1,
        actor="system",
        actor_role="GATE",
        action="COMPACTION",
        target="trace.jsonl",
        schema_version=1,
        payload={
            "prev_compaction_seq": prev_compaction_seq,
            "snapshot": snapshot,
            "truncated_at_seq": truncated_at,
        },
    )
    # Write to temp, fsync, atomically replace, dir-fsync.
    content = head_event.model_dump_json() + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="trace.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        dirfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return head_event


def verify_chain(events: list[TraceEvent]) -> list[str]:
    """校验 COMPACTION 链：prev_compaction_seq 无缺口；首条 None 合法。"""
    issues: list[str] = []
    last_prev: int | None = None
    for e in events:
        if e.action != "COMPACTION":
            continue
        pcs = e.payload.get("prev_compaction_seq")
        if last_prev is None:
            if pcs is not None and not isinstance(pcs, int):
                issues.append(f"COMPACTION seq={e.seq} prev_compaction_seq 非法类型")
        elif not isinstance(pcs, int):
            issues.append(f"COMPACTION seq={e.seq} 缺 prev_compaction_seq（应为 {last_prev}）")
        elif pcs != last_prev:
            issues.append(f"COMPACTION chain gap: prev={pcs} 期望={last_prev} (monotonic 断裂)")
        last_prev = e.seq
    return issues
