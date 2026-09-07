"""compaction（判据 7 I6b + N4 + New-G）。COMPACTION 事件成为 trace 新首条，
payload={prev_compaction_seq, snapshot, truncated_at_seq}。旧事件被截断，
历史保存在 snapshot。verify_chain 校验 COMPACTION 的 prev_compaction_seq
链单调无缺口；首条可为 None（LEGACY_MIGRATION 合法锚）。
"""

from __future__ import annotations


from shenbi.trace.event import TraceEvent


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
