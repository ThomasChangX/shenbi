"""Staging mechanism for checkpoint-gated skill outputs.

Spec: docs/superpowers/specs/archive/2026-07-01-novel-pipeline-design.md Section 2.7.

Checkpoint-gated skills (chapter-planning, state-settling) write to staging/
during dispatch. On review approve, the pipeline commits staging to final
paths. On review reject, staging is cleared and the skill re-dispatches.
"""

from __future__ import annotations

import json
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


def _load_staging_meta(project_dir: Path) -> dict[str, dict[str, str]]:
    """Read the staging-write metadata sidecar (SDD #21 R3).

    Returns ``{target_path: {"update_mode": ..., "key_field": ...}}`` for the
    targets that were staged through the keyed-upsert route. A missing or
    unreadable sidecar yields ``{}`` (legacy whole-file commit behaviour).
    """
    meta_path = project_dir / STAGING_DIR / ".staging-meta.json"
    if not meta_path.exists():
        return {}
    try:
        loaded = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.warning("staging_meta_unreadable", path=str(meta_path))
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _merge_staged_rows_keyed(staged_text: str, live_text: str, key_field: str) -> str:
    """Live-priority row merge of a staged snapshot into the live file.

    The staged file is a snapshot (live baseline at stage time + this
    chapter's increments). At commit time the LIVE file is the authority:
    rows whose key exists in live keep the live version (a row written to
    live after staging — e.g. the resonance step — must not be clobbered by
    the older staged copy); staged rows whose key is MISSING from live are
    appended. This is the commit-side half of the SDD #21 R3 fix: a plain
    whole-file replace here re-introduced last-writer-wins between the
    staging window and the commit.
    """
    from shenbi.pipeline.truth_io import (
        is_separator_row,
        has_markdown_row,
        split_table_cells,
        upsert_markdown_row,
    )

    merged = live_text
    for line in staged_text.split("\n"):
        cells = split_table_cells(line)
        if cells is None or is_separator_row(cells):
            continue
        if not has_markdown_row(merged, line, key_field):
            merged = upsert_markdown_row(merged, line, key_field)
    return merged


def commit_staging(project_dir: Path | str, target_paths: list[str]) -> list[Path]:
    """Commit staging files to their final paths.

    Default: copy each staging file to its target via :func:`safe_write`
    (atomic temp + fsync + os.replace).

    SDD #21 R3: targets recorded in the ``.staging-meta.json`` sidecar as
    keyed-upsert (``append_dedup``) are committed with a LIVE-PRIORITY row
    merge instead of a whole-file replace — the staged file is a stage-time
    snapshot, so replacing live with it could drop rows written to live
    after staging (see :func:`_merge_staged_rows_keyed`).

    Parent dirs are created as needed. Returns the list of committed target
    paths in the same order. Raises FileNotFoundError if a staging file does
    not exist.
    """
    project_dir = Path(project_dir)
    meta = _load_staging_meta(project_dir)
    committed: list[Path] = []
    for target_path in target_paths:
        source = staging_path(project_dir, target_path)
        if not source.exists():
            log.error("staging_file_missing", source=str(source), target=target_path)
            raise FileNotFoundError(f"Staging file not found: {source}")
        dest = project_dir / target_path
        entry = meta.get(target_path)
        try:
            if entry and entry.get("update_mode") == "append_dedup" and entry.get("key_field"):
                key_field = str(entry["key_field"])
                live_text = dest.read_text(encoding="utf-8") if dest.exists() else ""
                merged = _merge_staged_rows_keyed(
                    source.read_text(encoding="utf-8"), live_text, key_field
                )
                safe_write(dest, merged.encode("utf-8"))
                log.info(
                    "staging_committed_keyed_merge",
                    target=target_path,
                    key_field=key_field,
                )
            else:
                safe_write(dest, source.read_bytes())
        except OSError as _se:
            log.error("staging_write_failed", target=str(dest), error=str(_se))
            raise
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
