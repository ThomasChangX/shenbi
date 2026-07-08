"""Tests for G1 BACKUP_SKILLS derivation (Task 14a).

The backup-target set is now derived from contracts — any skill whose
``updates:`` intersects a truth-kind concept — rather than a hardcoded
frozenset of 9 that silently missed ~4 truth-updaters (G2.11 truth-diff
no-op'd for them).
"""

from __future__ import annotations

from shenbi.gates.g1 import BACKUP_SKILLS, derive_backup_skills


def test_derive_includes_truth_updaters() -> None:
    # phase-0: 13 skills update truth files
    skills = derive_backup_skills()  # loads contracts + registry internally
    # spot-check a few that were missing from the old hardcoded list
    assert "shenbi-state-settling" in skills
    assert "shenbi-review-resonance" in skills  # was missing → G2.11 no-op
    assert "shenbi-memory-distill" in skills  # was missing


def test_module_constant_equals_derived() -> None:
    """BACKUP_SKILLS (computed at import) must match derive_backup_skills()."""
    assert derive_backup_skills() == BACKUP_SKILLS


def test_derive_excludes_world_only_updaters() -> None:
    """Skills that only update world/ (kind=world) are NOT truth backups.

    faction-builder updates world/factions.md — its .bak was never read by
    G2.11 (truth-only), so it must drop out of the derived set.
    """
    skills = derive_backup_skills()
    assert "shenbi-faction-builder" not in skills
    assert "shenbi-location-builder" not in skills
