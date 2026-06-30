"""Tier A 事件溯源：append-only trace.jsonl（spec 支柱四 Tier A）。"""

from shenbi.trace.compaction import compact, verify_chain
from shenbi.trace.event import GENESIS_PREV, TraceEvent, canonical_payload, sign
from shenbi.trace.materialize import materialize_progress
from shenbi.trace.migrate import migrate_from_progress
from shenbi.trace.replay import replay
from shenbi.trace.versioning import (
    CURRENT_VERSION,
    assert_monotonic,
    migrate_to_current,
)
from shenbi.trace.writer import TraceWriter

__all__ = [
    "CURRENT_VERSION",
    "GENESIS_PREV",
    "TraceEvent",
    "TraceWriter",
    "assert_monotonic",
    "canonical_payload",
    "compact",
    "materialize_progress",
    "migrate_from_progress",
    "migrate_to_current",
    "replay",
    "sign",
    "verify_chain",
]
