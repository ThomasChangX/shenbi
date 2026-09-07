"""Shared helpers for pipeline-layer tests (spec #52 C14: single fixture assembly)."""

from __future__ import annotations

import shutil
from pathlib import Path

_FIX = Path(__file__).resolve().parents[1] / "fixtures"


def assemble_shared_context_project(tmp_path: Path) -> Path:
    """Real-output fixture project (G0.9) for SharedAuditContext tests.

    Single source for the fixture assembly previously duplicated between
    test_audit_context_cache.py and test_dispatch_helper_keys.py (final-review
    I-1): copies of real products only, never hand-written.
    """
    for sub in ("chapters", "truth", "world", "style", "context"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    for src in sorted((_FIX / "multi-chapter-example").glob("chapter-*.md")):
        shutil.copy(src, tmp_path / "chapters" / src.name)
    shutil.copy(
        _FIX / "snapshots" / "chapter-025" / "truth" / "character_matrix.md",
        tmp_path / "truth" / "character_matrix.md",
    )
    shutil.copy(
        _FIX / "snapshots" / "chapter-025" / "truth" / "pending_hooks.md",
        tmp_path / "truth" / "pending_hooks.md",
    )
    shutil.copy(_FIX / "world-rules-example.md", tmp_path / "world" / "rules.md")
    shutil.copy(_FIX / "style-profile-example.md", tmp_path / "style" / "style_profile.md")
    return tmp_path
