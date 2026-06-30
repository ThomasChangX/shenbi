from __future__ import annotations

from shenbi.trace.event import TraceEvent
from shenbi.trace.versioning import (
    CURRENT_VERSION,
    assert_monotonic,
    migrate_to_current,
)


def _ev(sv: int) -> TraceEvent:
    return TraceEvent.sign_and_new(
        prev_signature="0" * 64,
        seq=1,
        actor="d",
        actor_role="GATE",
        action="A",
        target="t",
        schema_version=sv,
    )


def test_monotonic_ok() -> None:
    # Non-decreasing sequence of KNOWN versions (sv > CURRENT_VERSION
    # is rejected by the unknown-version guard, so stay within v1).
    assert assert_monotonic([_ev(1), _ev(1)]) == []


def test_monotonic_rejects_decrease() -> None:
    issues = assert_monotonic([_ev(2), _ev(1)])
    assert any("decrease" in i for i in issues)


def test_unknown_higher_version_fails() -> None:
    issues = assert_monotonic([_ev(CURRENT_VERSION + 1)])
    assert any("unknown" in i.lower() for i in issues)


def test_migrate_old_to_current() -> None:
    old = _ev(1)
    new = migrate_to_current(old)
    assert new.schema_version == CURRENT_VERSION
    assert new.action == old.action
