"""Audit-run lint: mechanical validation of audit process artifacts (spec #49 R1, C35).

Checks per run directory (docs/superpowers/audit-runs/<date>/):
- row_columns: ledger rows must have 11 body columns; extra columns are
  tolerated only when they are closure annotations (text starting with "→",
  e.g. "→ closed (C-35 spec #49) (merged-into-F1177, ...)").
- pipe_escape: unescaped pipes shifting columns (detected via severity cell
  falling outside the known vocabulary).
- id_unique / dup_row / title_placeholder: ledger hygiene.
- counts_reconcile: ledger prefix counts (F/T/D/G) vs final-report stat
  claims (code-block `F=… T=… D=… G=… total=…` lines); zones *.files union
  vs the report's 表A/tracked claim (F973 shape).
- report_internal: report total claims vs computed ledger row count (F969
  shape: 781 vs 786); `(sum=N)` component sums; severity distribution
  claims vs normalized ledger severity counts.

Exemptions: <run-dir>/audit-lint-exemptions.json
    {"exemptions": [{"check": str, "id": str, "reason": str, "date": "YYYY-MM-DD"}]}
Ids: finding ID ("F1177"), row anchor ("row:<ID>"), or run-level ("run:<check>").
An exemption entry that matches no real hit is itself a FAIL (anti-rot).

CLI: no args = lint all docs/superpowers/audit-runs/*/ (frozen runs rely on
their exemption files); a single <run-dir> argument lints just that run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_RUNS_DIR = REPO_ROOT / "docs" / "superpowers" / "audit-runs"

SEVERITY_VOCAB = {"P0", "P1", "P2", "M", "severity-dispute"}
EXPECTED_BODY_COLUMNS = 11
_SEVERITY_COL = 3  # 0-based index of the severity column
EXEMPTION_FIELDS = {"check", "id", "reason", "date"}


@dataclass(frozen=True)
class Finding:
    """One lint hit: check name, anchor id (finding ID / row:N / run:check), message."""

    check: str
    id: str
    message: str


def _split_row(line: str) -> list[str]:
    # protect escaped pipes before splitting
    protected = line.replace("\\|", "\x00")
    return [c.strip().replace("\x00", "|") for c in protected.strip().strip("|").split("|")]


def _parse_rows(run_dir: Path) -> list[tuple[int, str, list[str]]]:
    ledger = run_dir / "findings-ledger.md"
    if not ledger.exists():
        return []
    rows: list[tuple[int, str, list[str]]] = []
    for lineno, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _split_row(stripped)
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue  # header separator
        if cells and cells[0] == "ID":
            continue  # header
        rows.append((lineno, stripped, cells))
    return rows


def _normalize_severity(cell: str) -> str:
    """Strip a trailing parenthetical suffix (half/full-width) from a severity cell."""
    return re.sub(r"[\uff08(][^\uff09())]*[\uff09)]\s*$", "", cell)


def _row_format_findings(rows: list[tuple[int, str, list[str]]]) -> list[Finding]:
    findings: list[Finding] = []
    seen_ids: dict[str, int] = {}
    seen_rows: dict[str, int] = {}
    for lineno, raw, cells in rows:
        fid = cells[0] if cells else f"row:{lineno}"
        if len(cells) < EXPECTED_BODY_COLUMNS:
            msg = f"line {lineno}: {len(cells)} columns (< {EXPECTED_BODY_COLUMNS})"
            findings.append(Finding("row_columns", fid, msg))
        else:
            extras = "".join(cells[EXPECTED_BODY_COLUMNS:])
            if extras and not extras.lstrip().startswith("→"):
                msg = f"line {lineno}: extra column(s) not closure annotation: {extras!r}"
                findings.append(Finding("row_columns", fid, msg))
        severity = _normalize_severity(cells[3]) if len(cells) > _SEVERITY_COL else ""
        if severity and severity not in SEVERITY_VOCAB:
            msg = f"line {lineno}: severity cell {cells[3]!r} outside vocab"
            findings.append(Finding("pipe_escape", fid, msg))
        if len(cells) > 1 and cells[1] == fid:
            findings.append(Finding("title_placeholder", fid, f"line {lineno}: title equals ID"))
        if fid in seen_ids:
            msg = f"line {lineno}: duplicate ID (first at line {seen_ids[fid]})"
            findings.append(Finding("id_unique", fid, msg))
        else:
            seen_ids[fid] = lineno
        if raw in seen_rows:
            msg = f"line {lineno}: exact duplicate of line {seen_rows[raw]}"
            findings.append(Finding("dup_row", fid, msg))
        else:
            seen_rows[raw] = lineno
    return findings


def lint_run(run_dir: Path) -> list[Finding]:
    """Row-format lint of <run-dir>/findings-ledger.md (no exemptions applied)."""
    return _row_format_findings(_parse_rows(run_dir))


def _report_text(run_dir: Path) -> str:
    report = run_dir / "final-report.md"
    if not report.exists():
        return ""
    return report.read_text(encoding="utf-8")


def _zones_union(run_dir: Path) -> int:
    zones_dir = run_dir / "zones"
    union: set[str] = set()
    if not zones_dir.is_dir():
        return 0
    for files_list in sorted(zones_dir.glob("*.files")):
        union.update(
            ln.strip() for ln in files_list.read_text(encoding="utf-8").splitlines() if ln.strip()
        )
    return len(union)


def reconcile(run_dir: Path) -> list[Finding]:
    """Ledger prefix counts + zones union vs final-report claims (spec #49 R1)."""
    findings: list[Finding] = []
    rows = _parse_rows(run_dir)
    report = _report_text(run_dir)

    prefix_counts: dict[str, int] = {}
    for _lineno, _raw, cells in rows:
        if cells and cells[0]:
            key = cells[0][0].upper()
            prefix_counts[key] = prefix_counts.get(key, 0) + 1

    claimed: dict[str, int] = {k: int(v) for k, v in re.findall(r"\b([FTDG])=(\d+)\b", report)}
    for prefix, count in claimed.items():
        actual = prefix_counts.get(prefix, 0)
        if actual != count:
            msg = f"report {prefix}={count} vs ledger {actual}"
            findings.append(Finding("counts_reconcile", f"prefix:{prefix}", msg))
    total_match = re.search(r"\btotal=(\d+)\b", report)
    if total_match and int(total_match.group(1)) != len(rows):
        claimed_total = int(total_match.group(1))
        msg = f"report total={claimed_total} vs ledger rows {len(rows)}"
        findings.append(Finding("counts_reconcile", "total_claim", msg))

    table_a = re.search("表\\s*A\\*{0,2}[\\uff09):\\uff1a]\\s*(?:\\|\\s*)?(\\d+)", report)
    if table_a:
        zones_union = _zones_union(run_dir)
        claimed_files = int(table_a.group(1))
        if zones_union != claimed_files:
            findings.append(
                Finding(
                    "counts_reconcile",
                    "zones_union",
                    f"zones union {zones_union} vs report 表A {claimed_files}",
                )
            )
    return findings


def report_internal(run_dir: Path) -> list[Finding]:
    """Final-report internal consistency vs computed ledger values (spec #49 R1)."""
    findings: list[Finding] = []
    rows = _parse_rows(run_dir)
    report = _report_text(run_dir)

    total_claims = [int(m) for m in re.findall(r"总 findings[:\uff1a]?\s*\*{0,2}(\d+)", report)]
    for claim in total_claims:
        if claim != len(rows):
            msg = f"report 总 findings={claim} vs ledger rows {len(rows)}"
            findings.append(Finding("report_internal", "total_claim", msg))

    sum_match = re.search(r"\(sum=(\d+)\)", report)
    if sum_match:
        severity_claims = {k: int(v) for k, v in re.findall(r"\b(P0|P1|P2|M)=(\d+)\b", report)}
        components_sum = sum(severity_claims.values())
        if severity_claims and components_sum != int(sum_match.group(1)):
            msg = f"(sum={sum_match.group(1)}) vs components {components_sum}"
            findings.append(Finding("report_internal", "sum_claim", msg))
        actual: dict[str, int] = {}
        for _lineno, _raw, cells in rows:
            if len(cells) > _SEVERITY_COL:
                sev = _normalize_severity(cells[_SEVERITY_COL])
                if sev in severity_claims:
                    actual[sev] = actual.get(sev, 0) + 1
        for sev, claim in severity_claims.items():
            if actual.get(sev, 0) != claim:
                msg = f"report {sev}={claim} vs ledger {actual.get(sev, 0)}"
                findings.append(
                    Finding(
                        "report_internal",
                        f"severity:{sev}",
                        f"report {sev}={claim} vs ledger {actual.get(sev, 0)}",
                    )
                )
    return findings


def load_exemptions(run_dir: Path) -> dict[str, set[str]]:
    """Load audit-lint-exemptions.json → {check: {ids}}; run-level ids included.

    Schema-invalid files yield {} here — validate_exemptions reports the
    violation (a corrupt file must FAIL, never crash the lint).
    """
    path = run_dir / "audit-lint-exemptions.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("exemptions", [])
        result: dict[str, set[str]] = {}
        for entry in entries:
            result.setdefault(entry["check"], set()).add(entry["id"])
        return result
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return {}


def apply_exemptions(findings: list[Finding], exemptions: dict[str, set[str]]) -> list[Finding]:
    """Return findings not muted by exemptions (finding id or run:<check>)."""
    kept: list[Finding] = []
    for f in findings:
        ids = exemptions.get(f.check, set())
        if f.id in ids or f"run:{f.check}" in ids:
            continue
        kept.append(f)
    return kept


def validate_exemptions(run_dir: Path, raw_findings: list[Finding]) -> list[Finding]:
    """Schema + anti-rot validation of audit-lint-exemptions.json."""
    problems: list[Finding] = []
    path = run_dir / "audit-lint-exemptions.json"
    if not path.exists():
        return problems
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [Finding("exemption_schema", "run:exemptions", f"invalid json: {exc}")]
    hit_keys = {(f.check, f.id) for f in raw_findings}
    hit_checks = {f.check for f in raw_findings}
    for i, entry in enumerate(data.get("exemptions", [])):
        if not isinstance(entry, dict) or set(entry) != EXEMPTION_FIELDS:
            got = sorted(entry) if isinstance(entry, dict) else type(entry)
            expected = sorted(EXEMPTION_FIELDS)
            problems.append(
                Finding("exemption_schema", f"entry:{i}", f"fields {got} != {expected}")
            )
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"]):
            problems.append(
                Finding("exemption_schema", f"entry:{i}", f"bad date {entry['date']!r}")
            )
            continue
        check, eid = entry["check"], entry["id"]
        if eid.startswith("run:"):
            if eid != f"run:{check}" or check not in hit_checks:
                problems.append(
                    Finding("stale_exemption", f"entry:{i}", f"run-level {eid} matches no hit")
                )
        elif (check, eid) not in hit_keys:
            problems.append(
                Finding("stale_exemption", f"entry:{i}", f"{check}:{eid} matches no hit")
            )
    return problems


def lint_run_full(run_dir: Path) -> list[Finding]:
    """Lint one run dir: raw findings + reconciliation + exemption handling."""
    raw = lint_run(run_dir) + reconcile(run_dir) + report_internal(run_dir)
    if not (run_dir / "audit-lint-exemptions.json").exists():
        return raw  # strict: no exemption file
    exemptions = load_exemptions(run_dir)
    return apply_exemptions(raw, exemptions) + validate_exemptions(run_dir, raw)


def main(argv: list[str] | None = None) -> int:
    """CLI entry: lint one run dir or all audit runs; exit 1 on any FAIL."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_dir", nargs="?", type=Path, help="single run dir (default: all audit runs)"
    )
    parser.add_argument(
        "--verify-carryover",
        action="store_true",
        help="also verify carryover.md coverage (spec #49 R2)",
    )
    args = parser.parse_args(argv)

    if args.run_dir is not None and not args.run_dir.is_dir():
        print(f"FAIL {args.run_dir}: run directory does not exist")
        return 1
    run_dirs = (
        [args.run_dir]
        if args.run_dir
        else sorted(p for p in AUDIT_RUNS_DIR.iterdir() if p.is_dir())
    )
    failed = False
    for run_dir in run_dirs:
        findings = lint_run_full(run_dir)
        if args.verify_carryover:
            findings += verify_carryover(run_dir)
        if findings:
            failed = True
            for f in findings:
                print(f"FAIL {run_dir.name}: {f.check} {f.id} — {f.message}")
        else:
            print(f"PASS {run_dir.name}")
    return 1 if failed else 0


def verify_carryover(run_dir: Path) -> list[Finding]:
    """Spec #49 R2 — implemented alongside generate_carryover (Task 3).

    Placeholder before Task 3: carryover.md may exist but no next-run ledger
    comparison is wired yet.
    """
    return []


if __name__ == "__main__":
    sys.exit(main())
