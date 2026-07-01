"""Staging mechanism for checkpoint-gated skill outputs.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 2.7.

Checkpoint-gated skills (chapter-planning, state-settling) write to staging/
during dispatch. On review approve, the pipeline commits staging to final
paths. On review reject, staging is cleared and the skill re-dispatches.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write

log = get_logger(__name__)

STAGING_DIR = "staging"


def staging_path(project_dir: Path | str, target_path: str) -> Path:
    """Map a target path to its staging location.

    Example: "plans/chapter-5-plan.md" -> project_dir/staging/plans/chapter-5-plan.md
    """
    project_dir = Path(project_dir)
    return project_dir / STAGING_DIR / target_path


def commit_staging(project_dir: Path | str, target_paths: list[str]) -> list[Path]:
    """Commit staging files to their final paths.

    Copies each staging file to its target location via :func:`safe_write`
    (atomic temp + fsync + os.replace). Parent dirs are created as needed.
    Returns the list of committed target paths in the same order.
    Raises FileNotFoundError if a staging file does not exist.
    """
    project_dir = Path(project_dir)
    committed: list[Path] = []
    for target_path in target_paths:
        source = staging_path(project_dir, target_path)
        if not source.exists():
            raise FileNotFoundError(f"Staging file not found: {source}")
        dest = project_dir / target_path
        safe_write(dest, source.read_bytes())
        committed.append(dest)
        log.info("staging_committed", target=target_path, dest=str(dest))
    log.info("staging_commit_batch", count=len(committed))
    return committed


def clear_staging(project_dir: Path | str) -> None:
    """Remove all staging files (used on review reject).

    Uses shutil.rmtree because deletion cannot be routed through safe_write
    (which only creates/replaces files). The file is on the purity-lint
    transitional allowlist for this reason.
    """
    project_dir = Path(project_dir)
    staging_dir = project_dir / STAGING_DIR
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
        log.info("staging_cleared", staging_dir=str(staging_dir))
    else:
        log.debug("staging_clear_noop", reason="staging dir does not exist")
