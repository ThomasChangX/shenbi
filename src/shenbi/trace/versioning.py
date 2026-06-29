"""事件版本化（判据 7 I6c + N5）。schema_version 单调非递减；未知更高版本→fail；
旧→新迁移函数注册在 MIGRATIONS。当前只有 v1，迁移逻辑为恒等（结构扩展点）。
"""

from __future__ import annotations

from collections.abc import Callable

from shenbi.trace.event import TraceEvent

CURRENT_VERSION = 1


def _identity(e: TraceEvent) -> TraceEvent:
    return e


MIGRATIONS: dict[int, Callable[[TraceEvent], TraceEvent]] = {}


def assert_monotonic(events: list[TraceEvent]) -> list[str]:
    issues: list[str] = []
    highest = 0
    for e in events:
        if e.schema_version > CURRENT_VERSION:
            issues.append(f"unknown schema_version {e.schema_version} > CURRENT {CURRENT_VERSION}")
        if e.schema_version < highest:
            issues.append(f"schema_version decrease: {e.schema_version} < {highest}")
        highest = max(highest, e.schema_version)
    return issues


def migrate_to_current(event: TraceEvent) -> TraceEvent:
    e = event
    while e.schema_version < CURRENT_VERSION:
        up = MIGRATIONS.get(e.schema_version, _identity)
        e = up(e)
    return e
