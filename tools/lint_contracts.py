#!/usr/bin/env python3
"""Contract lints (spec §5.5 #1, #2).

1. load-all  — every in-pipeline skill's contract loads (schema + registry).
2. completeness — a REPORT skill consumed downstream (per DAG) declares a
   persisted writes path (kills the "report only" drift).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shenbi.contracts.graph import dag_key
from shenbi.contracts.legacy import ContractError, load_contract, load_registry
from shenbi.gates.shared import ALL_SKILLS
from shenbi.sync_contracts import build_dag, load_all_contracts

META_SKILLS = {"using-shenbi", "shenbi-writing-skills"}


def in_pipeline_skills() -> list[str]:
    """Return every skill that participates in a phase/DAG (excludes the 2 meta skills)."""
    return [s for s in ALL_SKILLS if s not in META_SKILLS]


def find_load_violations() -> list[str]:
    """Load every in-pipeline skill's contract; return a message per failure."""
    vios: list[str] = []
    for skill in in_pipeline_skills():
        try:
            load_contract(skill)
        except ContractError as e:
            vios.append(f"{skill}: {e}")
    return vios


def find_completeness_violations(
    contracts: dict[str, dict[str, Any]], dag: dict[str, Any], registry: dict[str, Any]
) -> list[dict[str, str]]:
    """Flag REPORT skills consumed downstream that lack a persisted write.

    Glob-aware: a concrete audit write (audits/chapter-N-anti-ai.md) satisfies
    a glob audit read (audits/chapter-N-*.md) via the shared dag_key.
    """
    write_keys: dict[str, set[str]] = {
        s: {dag_key(f, registry) for f in [*c.get("writes", []), *c.get("updates", [])]}
        for s, c in contracts.items()
    }
    vios: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for e in dag["edges"]:
        producer = e["producer"]
        c = contracts.get(producer, {})
        if c.get("kind") != "report":
            continue
        key = dag_key(e["file"], registry)
        if key not in write_keys.get(producer, set()):
            tag = (producer, key)
            if tag not in seen:
                seen.add(tag)
                vios.append(
                    {
                        "skill": producer,
                        "file": e["file"],
                        "reason": "report consumed downstream but no persisted write",
                    }
                )
    return vios


def main() -> int:
    """Run load-all + completeness checks; print violations, exit non-zero if any."""
    vios = find_load_violations()
    registry = load_registry()
    contracts = load_all_contracts()
    dag = build_dag(contracts, registry)
    vios.extend(str(v) for v in find_completeness_violations(contracts, dag, registry))
    for v in vios:
        print(v)
    return 1 if vios else 0


if __name__ == "__main__":
    sys.exit(main())
