#!/usr/bin/env python3
"""Spec #105 T1: freeze audit-corpus sensor outputs (pre/post swap differential, #99 precedent)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from shenbi.contracts.severity import (
    NEGATION_PAYLOAD_TAIL,
    QUOTED_VALUE_TAIL,
    SEV_ENUM_TAIL,
)
from shenbi.pipeline import audit_aggregate, audit_layer, chapter_loop, revision_router


def _consolidator_blocking_equiv(content: str) -> bool:
    """M-7 consolidator key: equivalent of the pre-swap blocking_re.

    Three forms + three tails, built from the migrated single-source tails;
    must match per file after the swap too.
    """
    pat = re.compile(
        rf"(?-i:\*\*BLOCKING\*\*)"
        rf"|(?:severity|严重度)\*{{0,2}}\W{{0,6}}BLOCKING\b"
        rf"{SEV_ENUM_TAIL}{QUOTED_VALUE_TAIL}"
        rf"|^\s*-\s*\[BLOCKING\]{NEGATION_PAYLOAD_TAIL}",
        re.IGNORECASE | re.M,
    )
    return bool(pat.search(content))


def sensor_outputs(content: str) -> dict[str, object]:
    """Five sensors over one audit file's content (call sites kept stable)."""
    units, _ctx = audit_aggregate.extract_finding_units("x.md", content)
    return {
        "router_blocking": bool(revision_router._SEVERITY_BLOCKING_RE.search(content)),
        "router_critical": bool(revision_router._SEVERITY_CRITICAL_RE.search(content)),
        "loop_marker": bool(chapter_loop._BLOCKING_MARKER_RE.search(content)),
        "error_label": bool(audit_layer._ERROR_LABEL_RE.search(content)),
        "consolidator_blocking": _consolidator_blocking_equiv(content),
        "aggregate_units": [[u.severity, u.text, list(u.reporters)] for u in units],
    }


#: CLI arity that means "write JSON to stdout" (corpus path only).
_STDOUT_ARITY = 2


def main() -> int:
    """Dump per-file sensor outputs for the corpus as sorted JSON."""
    corpus = Path(sys.argv[1])
    use_stdout = len(sys.argv) == _STDOUT_ARITY
    result = {
        p.name: sensor_outputs(p.read_text(encoding="utf-8"))
        for p in sorted(corpus.glob("*.md"))
        if p.name != "PROVENANCE.md"
    }
    text = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True)
    if use_stdout:
        sys.stdout.write(text)
    else:
        Path(sys.argv[2]).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
