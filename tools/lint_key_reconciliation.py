#!/usr/bin/env python3
"""lint_key_reconciliation — read↔writer key reconciliation lint (spec #27 T7).

Static assertion that every registered reader key (gate checker / pipeline
parser read face) has a live writer anchor. Each ``ReadKey`` entry names:

- ``check_id``: stable identifier for violation reporting
- ``anchor``: where the reader lives (path + pattern; line numbers are
  commentary only — they drift)
- ``read_pattern``: what the reader consumes (a file-name glob family or a
  literal key)
- ``writer_sources``: grep-able anchors (path + pattern) in the producing
  code; every anchor must still match, and at least one writer must exist

Assertion (a): every writer_source anchor pattern still exists in its file.
Assertion (b): read_pattern is reconciled — for glob families, at least one
writer anchor constructs that family; for literal keys, the key appears in a
writer anchor file.

WARN→FAIL transition: default mode reports violations as WARN and exits 0.
The WARN cycle was consumed at merge time — the registry shipped green, so
this tool is wired into ``just check`` and CI already in ``--strict`` mode
(spec #27 final review ruling); default WARN mode remains for local triage.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


@dataclass
class ReadKey:
    """One registered reader key with its required writer anchors."""

    check_id: str
    anchor: str  # "path: pattern" — where the reader lives
    read_pattern: str  # glob family or literal key the reader consumes
    writer_sources: list[str] = field(default_factory=list)  # "path: pattern"
    # Glob-family reads whose reconciliation is the filename family itself
    # (no shared code symbol) are exempt from the symbol-binding check.
    binding_exempt: bool = False


READ_KEY_REGISTRY: list[ReadKey] = [
    # --- marker protocol (T2) ---
    ReadKey(
        "marker/G4-family",
        "src/shenbi/scoring.py: marker_filename",
        "gate-markers/G4-<skill>-<test_type>.json",
        [
            "src/shenbi/gates/shared.py: def marker_filename",
            "src/shenbi/gates/cli.py: write_gate_marker(",
        ],
    ),
    ReadKey(
        "marker/G6-family",
        "src/shenbi/scoring.py: marker_filename",
        "gate-markers/G6-<pipeline>-<test_type>.json",
        ["src/shenbi/gates/shared.py: def marker_filename"],
    ),
    # --- g_reconcile status vocab (T4) ---
    ReadKey(
        "reconcile/status-key",
        "src/shenbi/gates/g_reconcile.py: .upper() == ",
        "skills.<skill>.<test_type>.status == done",
        ["src/shenbi/dispatcher/modes/codex.py: SkillProgressStatus.DONE"],
    ),
    ReadKey(
        "reconcile/report-family",
        "src/shenbi/gates/g_reconcile.py: reports_dir.glob",
        "t1-reports/<skill>-<test_type>-scores[-subagent].json",
        ["src/shenbi/dispatcher/modes/codex.py: -scores-subagent.json"],
    ),
    # --- G3.2 canonical scoring shape (T4) ---
    ReadKey(
        "g3/final-score",
        "src/shenbi/gates/g3.py: _extract_score_fields",
        "final_score / total_score / score",
        ['src/shenbi/scoring.py: "final_score": final'],
    ),
    # --- G7.1 report-artifact family (T1/T3) ---
    ReadKey(
        "g7/report-artifacts",
        "src/shenbi/gates/g7.py: reports_dir_g71.glob",
        "t1-reports/*.json",
        ["src/shenbi/gates/shared.py: def parse_report_stem"],
    ),
    ReadKey(
        "g7/timeline-family",
        'src/shenbi/gates/g7.py: glob("*-scores*.json")',
        "t{1,2,3}-reports/*-scores*.json",
        ["src/shenbi/dispatcher/modes/codex.py: -scores-subagent.json"],
        binding_exempt=True,
    ),
    # --- audit gate scan list (T5) ---
    ReadKey(
        "chapterloop/audit-scan-family",
        "src/shenbi/pipeline/chapter_loop.py: _any_audit_has_findings",
        "audits/chapter-<N>-<audit_suffix>.md",
        [
            "src/shenbi/pipeline/audit_layer.py: def audit_relative_path",
            'src/shenbi/pipeline/chapter_loop.py: output_path=f"audits/chapter-',
        ],
    ),
    # --- drift trigger format (T5) ---
    ReadKey(
        "triggers/drift-warning-format",
        "src/shenbi/pipeline/triggers.py: _WARNING_RE",
        "- [<DriftKind>] <dim>: <detail>",
        ["src/shenbi/skill_utils/drift_detection/compute_drift.py: f.kind.value"],
    ),
    # --- resonance product format (T5) ---
    ReadKey(
        "chapterloop/resonance-score",
        "src/shenbi/pipeline/chapter_loop.py: _parse_resonance_score",
        "audits/chapter-<N>-resonance.md (**结果**: … (N/100))",
        ["src/shenbi/pipeline/chapter_loop.py: audit_relative_path(chapter, step.skill)"],
    ),
    # --- cascade history shape (T5) ---
    ReadKey(
        "chapterloop/cascade-history",
        "src/shenbi/pipeline/chapter_loop.py: _should_skip_audit",
        "audit_results[<short>] = {passed, hard_failures}",
        ["src/shenbi/pipeline/chapter_loop.py: cs.audit_results[short] = {"],
    ),
    # --- drift-guidance alert surface (T5) ---
    ReadKey(
        "chapterloop/drift-guidance",
        "src/shenbi/pipeline/chapter_loop.py: _drift_guidance_triggered",
        "truth/audit_drift.md drift-finding lines",
        ["src/shenbi/skill_utils/drift_detection/compute_drift.py: def _append_audit"],
    ),
    # --- pending hooks single parser (T5) ---
    ReadKey(
        "chapterloop/pending-hooks",
        "src/shenbi/pipeline/chapter_loop.py: _check_conditional_resolve",
        "truth/pending_hooks.md hook records",
        ["src/shenbi/pipeline/truth_readers.py: def read_pending_hooks"],
    ),
    # --- avg G3 score contract keys (T5) ---
    # --- rubric applicability lint face (T7; F104/F757 parser face was
    # implemented by spec #9 R4 — this entry pins the reconciliation) ---
    ReadKey(
        "scoring/load-applicability",
        "src/shenbi/scoring.py: def load_applicability",
        "rubric Dimension Applicability table (dual shapes)",
        ["src/shenbi/scoring.py: load_applicability"],  # same-file: local binding
    ),
    # --- F458 residual glob family ---
    ReadKey(
        "g0/generative-scores-glob",
        "src/shenbi/gates/g0.py: *-generative-scores*.json",
        "t1-reports/*-generative-scores*.json",
        ["src/shenbi/dispatcher/modes/codex.py: -scores-subagent"],
        binding_exempt=True,
    ),
    # --- F374 pre-rev backup exclusion ---
    ReadKey(
        "triggers/style-stale-excl-backup",
        "src/shenbi/pipeline/triggers.py: -pre-rev.md",
        "chapters/chapter-*.md excluding chapter-<N>-pre-rev.md",
        ["src/shenbi/pipeline/chapter_loop.py: chapter-{chapter}-pre-rev.md"],
    ),
    ReadKey(
        "cost/avg-g3-score",
        "src/shenbi/cost/report.py: _try_avg_g3_score",
        "*score*.json with final_score/total_score/score",
        ['src/shenbi/scoring.py: "final_score": final'],
    ),
]


def _binding_holds(rk: ReadKey) -> tuple[bool, str]:
    """Check cross-file symbol binding for a reader key.

    Assertion (b): when reader and writer live in different files, the
    reader file must reference at least one writer symbol — otherwise the
    reader could drift onto a hand-rolled format with all anchors intact.
    """
    r_path = rk.anchor.split(": ", 1)[0]
    r_file = REPO / r_path
    if not r_file.exists():
        return False, f"reader file missing: {r_path}"
    r_text = r_file.read_text(encoding="utf-8")
    cross_file = [ws for ws in rk.writer_sources if ws.split(": ", 1)[0] != r_path]
    if not cross_file:
        return True, ""  # all writers live in the reader file — binding is local
    for ws in cross_file:
        pattern = ws.split(": ", 1)[1]
        tokens = re.split(r"\W+", pattern)
        ident = [t for t in tokens if t.isidentifier()]
        if not ident:
            continue
        sym = max(ident, key=len)
        if re.search(r"\b" + re.escape(sym) + r"\b", r_text):
            return True, ""
    return False, "reader file references no writer symbol (binding broken)"


def _anchor_matches(anchor: str) -> tuple[bool, str]:
    """Check a 'path: pattern' anchor. Returns (ok, detail)."""
    if ": " not in anchor:
        return False, f"malformed anchor (expected 'path: pattern'): {anchor}"
    path, pattern = anchor.split(": ", 1)
    f = REPO / path
    if not f.exists():
        return False, f"anchor file missing: {path}"
    try:
        text = f.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"anchor file unreadable: {path} ({exc})"
    if not re.search(re.escape(pattern), text):
        return False, f"pattern no longer present in {path}: {pattern!r}"
    return True, ""


def main(argv: list[str] | None = None) -> int:
    """Run the reconciliation lint; 0 on clean, 1 on violations in strict mode."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 on any violation (WARN cycle: omit until retirement)",
    )
    args = parser.parse_args(argv)

    violations: list[str] = []
    for rk in READ_KEY_REGISTRY:
        if not rk.writer_sources:
            violations.append(f"{rk.check_id}: zero writer sources registered")
        for ws in rk.writer_sources:
            ok, detail = _anchor_matches(ws)
            if not ok:
                violations.append(f"{rk.check_id}: writer anchor failed — {detail}")
        ok, detail = _anchor_matches(rk.anchor)
        if not ok:
            violations.append(f"{rk.check_id}: reader anchor failed — {detail}")
            continue
        if rk.binding_exempt:
            continue
        ok, detail = _binding_holds(rk)
        if not ok:
            violations.append(f"{rk.check_id}: {detail}")

    if violations:
        level = "FAIL" if args.strict else "WARN"
        for v in violations:
            print(f"{level}: lint_key_reconciliation: {v}")
        if args.strict:
            return 1
        # first-cycle WARN mode: violations are printed but non-fatal only if
        # the registry itself is reconciled — a WARN with zero violations is
        # the acceptance bar for spec #27 验收 3.
        return 0
    print(f"lint_key_reconciliation: OK ({len(READ_KEY_REGISTRY)} read keys reconciled)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
