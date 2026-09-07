"""Generate tests/fixtures/provenance-baseline.json (spec #54 C16 T0).

The gate checkers never write files (purity rule); this standalone tools/
generator owns baseline authorship. Baseline is used ONLY for delta
reporting — WARN/FAIL judgement is live-scan + wave mode.

Usage: uv run python tools/gen_provenance_baseline.py
"""

import json
import sys
from datetime import date
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from shenbi.gates.g0_purity import (  # noqa: E402
    check_fixture_provenance,
    check_scenario_reference_closure,
    check_variant_bypass,
)

T1 = PROJECT / "tests" / "tiers" / "t1-skill"
FIXTURES = PROJECT / "tests" / "fixtures"
OUT = FIXTURES / "provenance-baseline.json"


def _violations(checks: list[dict[str, object]]) -> list[str]:
    """Full structured violation list from a check result (uncapped)."""
    if not checks:
        return []
    return list(checks[0].get("violations", []))  # pyright: ignore[reportUnknownArgumentType]


def main() -> int:
    """Scan the real library and write the provenance baseline snapshot."""
    violations: dict[str, list[str]] = {
        "G0.17": _violations(check_scenario_reference_closure(T1, PROJECT)),
        "G0.18": _violations(check_fixture_provenance(T1, FIXTURES)),
        "G0.19": _violations(check_variant_bypass(T1, FIXTURES)),
    }
    out: dict[str, object] = {
        "generated_at": date.today().isoformat(),
        "counts": {k: len(v) for k, v in violations.items()},
        "violations": violations,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
