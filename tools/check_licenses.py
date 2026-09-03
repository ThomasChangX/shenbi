#!/usr/bin/env python3
"""Supply-chain license & vulnerability-exemption enforcement (spec #41 C27 R2/R3).

Parses CycloneDX SBOMs (JSON) for copyleft licenses (GPL/LGPL/AGPL/SSPL family)
and enforces that every hit is registered in ``tools/supply_chain_exceptions.json``
with a ledger reference. Also parses CI workflows for ``--ignore-vuln <ID>``
arguments and enforces that every ignored vulnerability is registered.

Exit codes: 0 = all registered; 1 = unregistered copyleft or ignore-vuln found.
Tools follow the repo lint convention (print to stdout, rc semantics), see
tools/lint_contracts.py; the no-print rule applies to src/shenbi only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

COPYLEFT_PATTERN = re.compile(r"GPL|SSPL", re.IGNORECASE)
IGNORE_VULN_PATTERN = re.compile(r"--ignore-vuln[ =]+([A-Z0-9-]+)")


def load_exceptions(path: Path) -> dict[str, dict[str, dict[str, str]]]:
    """Load and shape-validate the exceptions registry."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("licenses"), dict) or not isinstance(data.get("ignore_vulns"), dict):
        raise SystemExit(f"malformed exceptions file {path}: licenses/ignore_vulns must be objects")
    return data


def component_licenses(component: dict[str, Any]) -> list[str]:
    """Extract SPDX id/name/expression strings from a CycloneDX component entry."""
    out: list[str] = []
    for entry in component.get("licenses") or []:
        lic = entry.get("license") or {}
        ident = lic.get("id") or lic.get("name") or entry.get("expression")
        if ident:
            out.append(ident)
    return out


def check_sbom(sbom_path: Path, exceptions: dict[str, dict[str, str]]) -> list[str]:
    """Return violation strings for unregistered/mismatched copyleft in one SBOM."""
    violations: list[str] = []
    if not sbom_path.exists():
        return [f"{sbom_path}: SBOM file not found"]
    data = json.loads(sbom_path.read_text(encoding="utf-8"))
    for comp in data.get("components", []):
        name = comp.get("name", "<unknown>")
        licenses = component_licenses(comp)
        if not licenses:
            print(f"WARN: {sbom_path.name}: {name}: no license metadata", file=sys.stderr)
            continue
        for lic in licenses:
            if not COPYLEFT_PATTERN.search(lic):
                continue
            entry = exceptions.get(name.lower())
            # exact match after stripping the "License :: OSI Approved ::" classifier
            # prefix (avoids GPL/LGPL substring-family confusion, audit-T3 M1)
            norm = lic.lower().removeprefix("license :: osi approved :: ")
            if entry and norm == entry["license"].lower():
                print(f"OK: {sbom_path.name}: {name}: {lic} (registered, ledger {entry['ledger']})")
            elif entry:
                violations.append(
                    f"{sbom_path.name}: {name}: {lic} does not match registered "
                    f"exception {entry['license']!r} (ledger {entry['ledger']})"
                )
            else:
                violations.append(
                    f"{sbom_path.name}: {name}: {lic} is copyleft and NOT registered "
                    f"in the exceptions table"
                )
    return violations


def check_workflows(
    workflow_paths: list[Path], ignore_vulns: dict[str, dict[str, str]]
) -> list[str]:
    """Return violation strings for --ignore-vuln IDs missing from the registry."""
    violations: list[str] = []
    for wf in workflow_paths:
        if not wf.exists():
            print(f"WARN: workflow not found, skipped: {wf}", file=sys.stderr)
            continue
        for vuln_id in sorted(set(IGNORE_VULN_PATTERN.findall(wf.read_text(encoding="utf-8")))):
            if vuln_id not in ignore_vulns:
                violations.append(
                    f"{wf.name}: --ignore-vuln {vuln_id} is NOT registered in "
                    f"the exemptions file (rule: unreachable CVEs must be upgraded "
                    f"or registered, never silently ignored)"
                )
            else:
                print(f"OK: {wf.name}: --ignore-vuln {vuln_id} (registered)")
    return violations


def main(argv: list[str] | None = None) -> int:
    """CLI entry: parse args, run both checks, print verdict, return exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sboms", nargs="+", type=Path, help="CycloneDX JSON SBOM files")
    parser.add_argument(
        "--exceptions",
        type=Path,
        default=Path(__file__).parent / "supply_chain_exceptions.json",
    )
    parser.add_argument(
        "--workflows",
        type=Path,
        nargs="*",
        default=[Path(__file__).resolve().parents[1] / ".github/workflows/security.yml"],
        help="workflows to scan for --ignore-vuln registrations",
    )
    args = parser.parse_args(argv)

    data = load_exceptions(args.exceptions)
    violations: list[str] = []
    for sbom in args.sboms:
        violations.extend(check_sbom(sbom, data["licenses"]))
    violations.extend(check_workflows(args.workflows, data["ignore_vulns"]))

    if violations:
        print("\nUNREGISTERED copyleft / ignore-vuln entries found:")
        for v in violations:
            print(f"  - {v}")
        print(
            "\nTo register: add an entry to tools/supply_chain_exceptions.json with "
            "ledger ID and reason (docs/framework/licenses.md)."
        )
        return 1
    print(f"OK: {len(args.sboms)} SBOM(s) clean, ignore-vuln registry consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
