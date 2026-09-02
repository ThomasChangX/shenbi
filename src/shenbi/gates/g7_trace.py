"""G7 tamper audit (read-only). Reads trace.jsonl raw bytes, recomputes the
hash chain to detect tampering; validates the COMPACTION chain (LEGACY anchor)
+ schema_version monotonicity. Never mutates files (criteria 7/11). ASCII
docstring: matches gates/*.py whose ruff ignore list omits RUF002.
"""

from __future__ import annotations
from shenbi.status import GateStatus

from pathlib import Path
from typing import Any

from shenbi.trace.compaction import verify_chain
from shenbi.trace.event import GENESIS_PREV, TraceEvent, canonical_payload, sign
from shenbi.trace.versioning import assert_monotonic


def _read_only_events(path: Path) -> tuple[list[TraceEvent], int | None, int]:
    """Parse trace.jsonl read-only. Returns (events, torn_line, total_lines).

    A line that fails TraceEvent validation is a tamper candidate (F535):
    instead of silently truncating the event list (prefix-PASS bypass), the
    torn line number is reported and parsing continues with the remaining
    lines. torn_line is the FIRST torn line (1-based); None when intact.
    """
    out: list[TraceEvent] = []
    torn_line: int | None = None
    total = 0
    if not path.exists():
        return out, torn_line, total
    for i, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not ln.strip():
            continue
        total += 1
        try:
            out.append(TraceEvent.model_validate_json(ln))
        except Exception:
            if torn_line is None:
                torn_line = i
    return out, torn_line, total


def audit_trace(round_dir: str | Path) -> tuple[list[str], list[dict[str, Any]]]:
    path = Path(round_dir) / "trace.jsonl"
    mf: list[str] = []
    checks: list[dict[str, Any]] = []
    if not path.exists():
        checks.append(
            {"id": "G7T.absent", "s": GateStatus.PASS, "note": "no trace.jsonl (pre-TierA round)"}
        )
        return mf, checks
    events, torn_line, total_lines = _read_only_events(path)
    if torn_line is not None:
        # F535/F410: torn line = tamper candidate, disclosed with line counts
        # so mid-file injection and tail truncation are both observable.
        mf.append(f"G7T.tamper: torn line at {torn_line} (内容被改/链断裂)")
        checks.append(
            {
                "id": "G7T.torn",
                "s": GateStatus.FAIL,
                "torn_line": torn_line,
                "total_lines": total_lines,
            }
        )
    prev = GENESIS_PREV
    tampered = False
    for e in events:
        expected = sign(prev, canonical_payload(e), e.schema_version)
        if expected != e.signature:
            mf.append(f"G7T.tamper: seq={e.seq} signature mismatch (内容被改/链断裂)")
            tampered = True
            break
        prev = e.signature
    if not tampered:
        checks.append({"id": "G7T.chain", "s": GateStatus.PASS, "events": len(events)})
    ver_issues = assert_monotonic(events)
    comp_issues = verify_chain(events)
    mf.extend(f"G7T.version: {i}" for i in ver_issues)
    mf.extend(f"G7T.compaction: {i}" for i in comp_issues)
    if not ver_issues and not comp_issues:
        checks.append({"id": "G7T.version_chain", "s": GateStatus.PASS})
    return mf, checks
