"""Single loader for skill I/O contracts (spec §5.1, fixes audit D2).

The frontmatter ``contract:`` block is the ONE editable location for a skill's
I/O. Every consumer (dispatcher, phase_runner, gates, generator) imports
``load_contract`` — the loader-uniqueness lint forbids a second reader of the
frontmatter ``contract:`` key.

Validation layers (spec §4.2, all "impossible to land"):
  * schema  — kind in OutputKind; reads/writes/updates are list[str]
  * registry — every path resolves to a concept, glob, or parametric pattern
A per-skill load does NOT check cross-skill completeness (that needs the DAG);
the contract-completeness lint (Part IV) does.
"""

from __future__ import annotations

import fnmatch
from enum import StrEnum
from pathlib import Path
from typing import Any, TypedDict

import yaml

from shenbi.exceptions import FrameworkError
from shenbi.gates.shared import PROJECT, SKILLS

REGISTRY_PATH = PROJECT / "docs" / "framework" / "truth-files.yaml"


class ContractError(FrameworkError):
    """A skill contract is missing, malformed, or fails registry resolution."""


class OutputKind(StrEnum):
    ARTIFACT = "artifact"  # writes a durable project file -> G2 chapter/truth validation
    REPORT = "report"  # emits a persisted report (path declared in writes) -> G2 report-type
    EPHEMERAL = "ephemeral"  # transient guidance, no persisted artifact -> output gates skip


class Contract(TypedDict):
    kind: OutputKind
    reads: list[str]
    writes: list[str]
    updates: list[str]


def _skill_path(skill: str) -> Path:
    return SKILLS / skill / "SKILL.md"


def load_registry() -> dict[str, Any]:
    """Load and return the canonical file registry as a dict."""
    if not REGISTRY_PATH.exists():
        raise ContractError("registry missing", registry=str(REGISTRY_PATH))
    try:
        data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ContractError("registry malformed YAML", registry=str(REGISTRY_PATH)) from e
    if not isinstance(data, dict):
        raise ContractError("registry malformed", registry=str(REGISTRY_PATH))
    return data


def resolves(path: str, registry: dict[str, Any]) -> bool:
    """True if path is a concept, a declared glob, or a registered parametric."""
    concepts = {c["name"] for c in registry.get("concepts", [])}
    if path in concepts:
        return True
    globs = [g["pattern"] for g in registry.get("globs", [])]
    if any(fnmatch.fnmatch(path, g) for g in globs):
        return True
    # parametric: a contract may declare a parametric pattern (e.g. chapters/chapter-N.md);
    # it resolves if the registry has that parametric (lookup, not inference).
    parametrics = {p["parametric"] for p in registry.get("patterns", [])}
    return path in parametrics


def _read_frontmatter_contract(skill: str, skill_md: Path) -> dict[str, Any]:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ContractError("frontmatter missing", skill=skill)
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ContractError("frontmatter unterminated", skill=skill)
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        raise ContractError("frontmatter malformed YAML", skill=skill) from e
    if not isinstance(data, dict):
        raise ContractError("frontmatter not a mapping", skill=skill)
    contract = data.get("contract")
    if not isinstance(contract, dict):
        raise ContractError("contract block missing", skill=skill)
    return contract


def _validate(raw: dict[str, Any], skill: str, registry: dict[str, Any]) -> Contract:
    if "kind" not in raw:
        raise ContractError("contract.kind missing", skill=skill)
    try:
        kind = OutputKind(raw["kind"])
    except ValueError:
        raise ContractError(
            "contract.kind invalid",
            skill=skill,
            kind=raw["kind"],
            allowed=[k.value for k in OutputKind],
        ) from None

    validated: dict[str, list[str]] = {}
    for field in ("reads", "writes", "updates"):
        val = raw.get(field)
        if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
            raise ContractError(f"contract.{field} must be a list[str]", skill=skill, field=field)
        for p in val:
            if not resolves(p, registry):
                raise ContractError(
                    "contract path does not resolve in registry", skill=skill, field=field, path=p
                )
        validated[field] = val
    return {
        "kind": kind,
        "reads": validated["reads"],
        "writes": validated["writes"],
        "updates": validated["updates"],
    }


def load_contract(skill: str) -> Contract:
    """Load and fully validate a skill's frontmatter contract."""
    path = _skill_path(skill)
    if not path.exists():
        raise ContractError("skill SKILL.md not found", skill=skill)
    registry = load_registry()
    raw = _read_frontmatter_contract(skill, path)
    return _validate(raw, skill, registry)
