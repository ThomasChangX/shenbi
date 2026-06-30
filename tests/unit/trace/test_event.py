from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shenbi.trace.event import (
    GENESIS_PREV,
    TraceEvent,
    canonical_payload,
    sign,
)


def _base_kwargs(**over: object) -> dict[str, object]:
    # ts MUST be pinned: TraceEvent.ts has default_factory=datetime.now,
    # so two sign_and_new() calls without ts get different microsecond
    # timestamps, making canonical_payload/sign non-deterministic.
    kw: dict[str, object] = {
        "ts": datetime(2026, 1, 1, tzinfo=UTC),
        "seq": 1,
        "actor": "dispatcher",
        "actor_role": "GATE",
        "action": "MARK_DONE",
        "target": "progress.json",
        "schema_version": 1,
        "payload": {"skill": "x", "score": 94.0},
    }
    kw.update(over)
    return kw


def test_event_frozen() -> None:
    e = TraceEvent.sign_and_new(prev_signature=GENESIS_PREV, **_base_kwargs())
    with pytest.raises(ValidationError):
        e.actor = "other"  # type: ignore[misc]


def test_signature_deterministic() -> None:
    e1 = TraceEvent.sign_and_new(prev_signature=GENESIS_PREV, **_base_kwargs())
    e2 = TraceEvent.sign_and_new(prev_signature=GENESIS_PREV, **_base_kwargs())
    assert e1.signature == e2.signature
    assert len(e1.signature) == 64  # sha256 hex


def test_signature_chains_prev() -> None:
    e1 = TraceEvent.sign_and_new(prev_signature=GENESIS_PREV, **_base_kwargs(seq=1))
    e2 = TraceEvent.sign_and_new(prev_signature=e1.signature, **_base_kwargs(seq=2))
    e2b = TraceEvent.sign_and_new(prev_signature=GENESIS_PREV, **_base_kwargs(seq=2))
    # 不同 prev 必出不同签名（篡改检测基础）
    assert e2.signature != e2b.signature


def test_canonical_payload_is_order_independent() -> None:
    a = canonical_payload(
        TraceEvent.sign_and_new(GENESIS_PREV, **_base_kwargs(payload={"a": 1, "b": 2}))
    )
    b = canonical_payload(
        TraceEvent.sign_and_new(GENESIS_PREV, **_base_kwargs(payload={"b": 2, "a": 1}))
    )
    assert a == b


def test_sign_helper_matches_method() -> None:
    e = TraceEvent.sign_and_new(GENESIS_PREV, **_base_kwargs())
    assert e.signature == sign(GENESIS_PREV, canonical_payload(e), 1)
