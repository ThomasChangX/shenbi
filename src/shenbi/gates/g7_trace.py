"""G7 tamper audit (read-only). Reads trace.jsonl raw bytes, recomputes the
hash chain to detect tampering; validates the COMPACTION chain (LEGACY anchor)
+ schema_version monotonicity. Never mutates files (criteria 7/11). ASCII
docstring: matches gates/*.py whose ruff ignore list omits RUF002.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shenbi.trace.compaction import verify_chain
from shenbi.trace.event import GENESIS_PREV, TraceEvent, canonical_payload, sign
from shenbi.trace.versioning import assert_monotonic


def _read_only_events(path: Path) -> list[TraceEvent]:
    out: list[TraceEvent] = []
    if not path.exists():
        return out
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            out.append(TraceEvent.model_validate_json(ln))
        except Exception:
            break  # torn line: stop here (read-only, no repair)
    return out


def audit_trace(round_dir: str | Path) -> tuple[list[str], list[dict[str, Any]]]:
    path = Path(round_dir) / "trace.jsonl"
    mf: list[str] = []
    checks: list[dict[str, Any]] = []
    if not path.exists():
        checks.append({"id": "G7T.absent", "s": "PASS", "note": "no trace.jsonl (pre-TierA round)"})
        return mf, checks
    events = _read_only_events(path)
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
        checks.append({"id": "G7T.chain", "s": "PASS", "events": len(events)})
    ver_issues = assert_monotonic(events)
    comp_issues = verify_chain(events)
    mf.extend(f"G7T.version: {i}" for i in ver_issues)
    mf.extend(f"G7T.compaction: {i}" for i in comp_issues)
    if not ver_issues and not comp_issues:
        checks.append({"id": "G7T.version_chain", "s": "PASS"})
    return mf, checks
