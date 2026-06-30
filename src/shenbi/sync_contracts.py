"""Derive generated artifacts from contracts (spec §5.4, fixes D4/D1).

Reads every skill's contract via contract.load_contract (no third parser) and
derives:
  * deps.json expected_outputs  (parametric -> glob; in place)
  * docs/framework/dependency-dag.json   (producer/consumer graph — NEW)
  * docs/framework/truth-files.index.json (per-file usage)
  * the auto-rendered body 数据契约 view (OD-1)
"""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any

from shenbi.contracts import ContractError, load_contract, load_registry
from shenbi.safe_write import safe_write
from shenbi.gates.shared import ALL_SKILLS, PROJECT, SKILLS
from shenbi.logging import get_logger

log = get_logger(__name__)

DEPS_PATH = PROJECT / "tests" / "tiers" / "deps.json"
DAG_PATH = PROJECT / "docs" / "framework" / "dependency-dag.json"
INDEX_PATH = PROJECT / "docs" / "framework" / "truth-files.index.json"
BODY_BANNER = "<!-- AUTO-GENERATED from frontmatter — do not edit -->"
BODY_END = "<!-- END AUTO-GENERATED -->"


def normalize_to_glob(path: str, registry: dict[str, Any]) -> str:
    """Parametric -> its declared glob; a path matching a declared glob resolves
    to that glob; other globs/concrete pass through.

    The globs fallback handles per-dimension audit literals like
    ``audits/chapter-N-anti-ai.md``: the registry has ONE parametric for all
    dims (``audits/chapter-N-<dim>.md``), so a concrete-dim literal can't be
    exact-matched against it. Without this fallback, ``expected_outputs``
    would carry literal ``N``/``NNN`` and G5.4 / ``cmd_pre_score`` would never
    match real numbered files (e.g. ``audits/chapter-005-anti-ai.md``).
    Patterns are tried first so a specific parametric glob wins over a broad
    declared glob.
    """
    for p in registry.get("patterns", []):
        if p["parametric"] == path:
            return str(p["glob"])
    for g in registry.get("globs", []):
        if fnmatch.fnmatch(path, g["pattern"]):
            return str(g["pattern"])
    return path


def load_all_contracts() -> dict[str, dict[str, Any]]:
    """Load every skill's contract; skills without one (meta/pre-migration) are skipped."""
    out: dict[str, dict[str, Any]] = {}
    for skill in ALL_SKILLS:
        try:
            c = load_contract(skill)
        except ContractError:
            continue
        out[skill] = {
            "kind": c["kind"],
            "reads": list(c["reads"]),
            "writes": list(c["writes"]),
            "updates": list(c["updates"]),
        }
    return out


def dag_key(path: str, registry: dict[str, Any]) -> str:
    """Canonical matching key for a path in the DAG.

    A concrete write (audits/chapter-N-anti-ai.md) and a glob read
    (audits/chapter-N-*.md) must join under one edge, so the completeness check
    can see that a report is consumed downstream. Map any path to a declared
    glob it matches; else its parametric glob; else itself.

    Trade-off: matching is glob-aware, so unrelated files that share a broad
    declared glob (e.g. every ``truth/*.md`` file) collapse to one key and
    over-connect in the DAG. Benign for the completeness check — it only
    scrutinizes REPORT producers, which carry specific audit writes — but it
    adds noise for future impact analysis.
    """
    for g in registry.get("globs", []):
        if fnmatch.fnmatch(path, g["pattern"]):
            return str(g["pattern"])
    return normalize_to_glob(path, registry)


def build_dag(contracts: dict[str, dict[str, Any]], registry: dict[str, Any]) -> dict[str, Any]:
    """Skill B reads file X that skill A writes/updates => A -> B.

    Matching is glob-aware (via dag_key) so a concrete producer write and a glob
    consumer read connect even when their literal strings differ.
    """
    producers: dict[str, list[str]] = {}
    for skill, c in contracts.items():
        for f in [*c["writes"], *c["updates"]]:
            key = dag_key(f, registry)
            bucket = producers.setdefault(key, [])
            # A skill that both writes and updates files sharing a glob key
            # (e.g. any truth/*.md) must appear once per key, not once per
            # file, or every downstream edge is duplicated.
            if skill not in bucket:
                bucket.append(skill)
    edges: list[dict[str, str]] = []
    for consumer, c in contracts.items():
        for f in c["reads"]:
            for producer in producers.get(dag_key(f, registry), []):
                if producer != consumer:
                    edges.append({"producer": producer, "consumer": consumer, "file": f})
    return {"edges": edges}


def derive_expected_outputs(
    phase: dict[str, Any], contracts: dict[str, dict[str, Any]], registry: dict[str, Any]
) -> list[str]:
    """Derive a phase's expected_outputs from member writes/updates.

    Parametric patterns normalize to their declared glob; declared globs and
    concrete paths pass through. The curated ``expected_outputs`` is NOT read
    here — it is the drift surface being regenerated, so comparing against it
    would make the generator fail on its own first run.
    """
    members: list[str] = phase.get("prerequisites", [])
    produced: list[str] = []
    for skill in members:
        c = contracts.get(skill, {})
        for f in [*c.get("writes", []), *c.get("updates", [])]:
            produced.append(normalize_to_glob(f, registry))
    return sorted(set(produced))


def verify_bijection(
    generated: list[str],
    phase: dict[str, Any],
    contracts: dict[str, dict[str, Any]],
    registry: dict[str, Any],
) -> None:
    """Consistency guard (spec §5.4): ``generated`` must equal the normalized
    writes+updates of the phase's members.

    In ``main()`` this runs right after ``derive_expected_outputs``, so it
    confirms the two stay coupled — guarding a future refactor that decouples
    ``expected_outputs`` from member writes, or nondeterminism. It is NOT a
    meaningful check for logic bugs shared with ``derive_expected_outputs``
    (both iterate members identically, so they would drop the same write);
    the real D4 drift guard is the idempotency CI check. Called directly with
    an arbitrary ``generated`` it does verify the bijection. Raises on mismatch.
    """
    members: list[str] = phase.get("prerequisites", [])
    member_outputs = {
        normalize_to_glob(f, registry)
        for s in members
        for f in [*contracts.get(s, {}).get("writes", []), *contracts.get(s, {}).get("updates", [])]
    }
    gen_set = set(generated)
    missing = sorted(member_outputs - gen_set)
    spurious = sorted(gen_set - member_outputs)
    assert not missing and not spurious, f"bijection broken: missing={missing} spurious={spurious}"


def render_body_view(skill: str, contract: dict[str, Any]) -> str:
    """The auto-generated 数据契约 block, wrapped in start/end sentinels so
    re-rendering is an unambiguous regex replace (idempotent).
    """
    lines = [BODY_BANNER, "", "## 数据契约", ""]
    lines.append(f"- **Reads:** {', '.join(contract['reads']) or 'none'}")
    lines.append(f"- **Writes:** {', '.join(contract['writes']) or 'none'}")
    lines.append(f"- **Updates:** {', '.join(contract['updates']) or 'none'}")
    lines.append("")
    lines.append(BODY_END)
    return "\n".join(lines) + "\n"


def render_body_into(skill_md: Path, contract: dict[str, Any]) -> None:
    """Inject/replace the auto-generated body block in a SKILL.md (OD-1).

    Idempotent: the block is delimited by BODY_BANNER ... BODY_END, so an
    existing block is replaced wholesale and a missing one is prepended after
    the frontmatter.
    """
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^(---\n.*?\n---\n)(.*)$", text, flags=re.DOTALL)
    if not m:
        return  # not a skill file with frontmatter
    frontmatter, body = m.group(1), m.group(2)
    block = render_body_view(skill_md.parent.name, contract)
    pattern = re.compile(re.escape(BODY_BANNER) + r".*?" + re.escape(BODY_END) + r"\n?", re.DOTALL)
    if pattern.search(body):
        body = pattern.sub(block, body, count=1)
    else:
        body = block + "\n" + body.lstrip("\n")
    safe_write(skill_md, frontmatter + body)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    """Regenerate all contract-derived artifacts; bail pre-migration (no contracts)."""
    registry = load_registry()
    contracts = load_all_contracts()
    if not contracts:
        # Pre-migration (Parts III–IV): no skill has a frontmatter contract yet.
        # Bail BEFORE writing anything — otherwise every phase's expected_outputs
        # would be overwritten with []. Run `just generate` only after Task 13.
        log.error("no_contracts_loaded", hint="run after the Task 13 migration")
        return 1

    # DAG + index
    _write_json(DAG_PATH, build_dag(contracts, registry))
    usage: dict[str, dict[str, list[str]]] = {}
    for skill, c in contracts.items():
        for role, files in (
            ("reads", c["reads"]),
            ("writes", c["writes"]),
            ("updates", c["updates"]),
        ):
            for f in files:
                usage.setdefault(f, {"reads": [], "writes": [], "updates": []})[role].append(skill)
    _write_json(INDEX_PATH, usage)

    # Auto-rendered body 数据契约 view into each migrated skill (OD-1).
    for skill, c in contracts.items():
        render_body_into(SKILLS / skill / "SKILL.md", c)

    # deps.json expected_outputs in place (organizational fields preserved).
    # The curated expected_outputs is OVERWRITTEN — it is the D4 drift surface
    # being regenerated, so we never compare against it (that would fail the
    # generator on its own first run). Correctness is the bijection self-check.
    deps = json.loads(DEPS_PATH.read_text(encoding="utf-8"))
    for phase_name, phase in deps.get("t2-phases", {}).items():
        generated = derive_expected_outputs(phase, contracts, registry)
        verify_bijection(generated, phase, contracts, registry)
        phase["expected_outputs"] = generated
        log.info("phase_synced", phase=phase_name, outputs=generated)
    _write_json(DEPS_PATH, deps)
    log.info("sync_complete", skills=len(contracts))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
