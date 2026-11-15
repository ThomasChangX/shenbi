#!/usr/bin/env python3
"""Spec #105 T1: freeze audit-corpus sensor outputs (pre/post swap differential, #99 precedent)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from shenbi.contracts.severity import SECTION_HEADER_RE
from shenbi.pipeline import audit_aggregate, audit_layer, chapter_loop, revision_router
from shenbi.pipeline.parallel_dispatch import build_consolidator_sensors

#: audit-S8 I-3: the consolidator key is produced by the PRODUCTION builder
#: (parallel_dispatch.build_consolidator_sensors) — a change to the production
#: sensing now breaks the frozen baseline instead of silently diverging from a
#: hand-copied regex.
_CONSOLIDATOR_BLOCKING_RE, _CONSOLIDATOR_CRITICAL_RE = build_consolidator_sensors()


def sensor_outputs(content: str) -> dict[str, object]:
    """Five sensors over one audit file's content (call sites kept stable)."""
    units, _ctx = audit_aggregate.extract_finding_units("x.md", content)
    return {
        "router_blocking": bool(revision_router._SEVERITY_BLOCKING_RE.search(content)),
        "router_critical": bool(revision_router._SEVERITY_CRITICAL_RE.search(content)),
        "loop_marker": bool(chapter_loop._BLOCKING_MARKER_RE.search(content)),
        "error_label": bool(audit_layer._ERROR_LABEL_RE.search(content)),
        "consolidator_blocking": bool(_CONSOLIDATOR_BLOCKING_RE.search(content)),
        "consolidator_critical": bool(_CONSOLIDATOR_CRITICAL_RE.search(content)),
        "aggregate_units": [[u.severity, u.text, list(u.reporters)] for u in units],
    }


#: CLI arity that means "write JSON to stdout" (corpus path only).
_STDOUT_ARITY = 2


def production_patterns() -> dict[str, str]:
    """Compiled pattern strings of every production sensor (audit-S8 I-3).

    Pattern-level freeze: the corpus has no zero-declaration/legend samples
    (known gap), so data-level equality alone cannot catch every builder
    change — the exact pattern text is pinned alongside the data baseline.
    """
    return {
        "router_blocking": revision_router._SEVERITY_BLOCKING_RE.pattern,
        "router_critical": revision_router._SEVERITY_CRITICAL_RE.pattern,
        "loop_marker": chapter_loop._BLOCKING_MARKER_RE.pattern,
        "error_label": audit_layer._ERROR_LABEL_RE.pattern,
        "consolidator_blocking": _CONSOLIDATOR_BLOCKING_RE.pattern,
        "consolidator_critical": _CONSOLIDATOR_CRITICAL_RE.pattern,
        "aggregate_bracket": audit_aggregate._BRACKET_RE.pattern,
        "aggregate_bold": audit_aggregate._BOLD_RE.pattern,
        "aggregate_cell": audit_aggregate._CELL_RE.pattern,
        "aggregate_key": audit_aggregate._KEY_RE.pattern,
        "section_header": SECTION_HEADER_RE.pattern,
    }


def main() -> int:
    """Dump per-file sensor outputs for the corpus as sorted JSON."""
    corpus = Path(sys.argv[1])
    use_stdout = len(sys.argv) == _STDOUT_ARITY
    result = {
        p.name: sensor_outputs(p.read_text(encoding="utf-8"))
        for p in sorted(corpus.glob("*.md"))
        if p.name != "PROVENANCE.md"
    }
    # audit-S8 M-4: identical trailing newline on both paths (byte purity).
    text = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if use_stdout:
        sys.stdout.write(text)
    else:
        out = Path(sys.argv[2])
        out.write_text(text, encoding="utf-8")
        patterns = json.dumps(production_patterns(), ensure_ascii=False, indent=1, sort_keys=True)
        out.with_suffix(".patterns.json").write_text(patterns + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
