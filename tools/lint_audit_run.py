"""Audit-run lint: mechanical validation of audit process artifacts (spec #49 R1, C35).

Checks per run directory (docs/superpowers/audit-runs/<date>/):
- row_columns: ledger rows must have 11 body columns; extra columns are
  tolerated only when they are closure annotations (text starting with "→",
  e.g. "→ closed (C-35 spec #49) (merged-into-F1177, ...)").
- pipe_escape: unescaped pipes shifting columns (detected via severity cell
  falling outside the known vocabulary).
- id_unique / dup_row / title_placeholder: ledger hygiene.

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


def load_exemptions(run_dir: Path) -> dict[str, set[str]]:
    """Load audit-lint-exemptions.json → {check: {ids}}; run-level ids included."""
    path = run_dir / "audit-lint-exemptions.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, set[str]] = {}
    for entry in data.get("exemptions", []):
        result.setdefault(entry["check"], set()).add(entry["id"])
    return result


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
    """Lint one run dir: raw findings + exemption application + exemption validation."""
    raw = lint_run(run_dir)
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
