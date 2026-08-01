"""Audit shared symbols (Cluster 2 cyclic-import refactor leaf module).

Leaf module: imports only shenbi.contracts.* + stdlib, does NOT import
dispatcher/audit.write_audit/audit.record. The original dispatcher/audit cycle
(executor <-> write_audit via _declared_patterns, plus record -> write_audit
TYPE_CHECKING) had its back-edges broken by sinking the shared symbols here.

Migrated from: dispatcher/executor.py (derive_output_files) +
audit/write_audit.py (AuditResult). Behavior unchanged (spec §3.3).

Dependency direction note: executor.py (dispatcher pkg) will top-level import
derive_output_files from this module, creating a dispatcher -> audit package
dependency. This is intentional — _shared is a leaf (no back-import into
dispatcher/audit.write_audit/audit.record); the audit prefix is organizational
(package-private _shared), not semantic. derive_output_files is a thin
contracts-resolving wrapper (load_contract + resolve_or_skip).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shenbi.contracts import ContractError, load_contract
from shenbi.contracts.paths import resolve_or_skip

__all__ = ["AuditResult", "derive_output_files"]


@dataclass(frozen=True)
class AuditResult:
    skill: str
    violations: tuple[str, ...]
    drift: tuple[str, ...]
    checked_files: tuple[str, ...]


def derive_output_files(
    skill: str, chapter: int | None = None, round_dir: Path | None = None
) -> list[str]:
    """Return the skill's contract writes+updates, resolving chapter placeholders.
    When *chapter* is provided, N/NNN placeholders are resolved.
    Paths with unresolvable placeholders (genesis mode) are skipped via
    resolve_or_skip -> None -> filtered. When *round_dir* is provided,
    relative paths are made absolute.
    """
    try:
        c = load_contract(skill)
        paths = [
            rp
            for p in [*c["writes"], *c["updates"]]
            if (rp := resolve_or_skip(p, chapter)) is not None
        ]
        if round_dir is not None:
            paths = [str((round_dir / p).resolve()) for p in paths]
        return paths
    except ContractError:
        return []
