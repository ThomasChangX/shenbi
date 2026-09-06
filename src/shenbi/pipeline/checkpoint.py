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
    if committed:
        _unmark_checkpointed(project_dir, target_paths)
    log.info("staging_commit_batch", count=len(committed))
    return committed


def mark_staging_checkpointed(project_dir: Path | str, targets: list[str]) -> None:
    """Mark staged targets as having entered a checkpoint (C30 R1, F318).

    The marker lives in the existing ``.staging-meta.json`` sidecar so the
    staged/committed boundary is derivable by a NEW process after a crash —
    the emergency cleanup predicate must not rely on in-process memory.
    """
    project_dir = Path(project_dir)
    meta = _load_staging_meta(project_dir)
    changed = False
    for target in targets:
        entry = meta.get(target)
        if entry is None:
            entry = {}
            meta[target] = entry
        if entry.get("checkpointed") != "true":
            entry["checkpointed"] = "true"
            changed = True
    if changed:
        meta_path = project_dir / STAGING_DIR / ".staging-meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        safe_write(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
        log.info("staging_marked_checkpointed", count=len(targets))


def staging_checkpointed_targets(project_dir: Path | str) -> set[str]:
    """Return the set of staged targets marked as checkpoint-entered."""
    meta = _load_staging_meta(Path(project_dir))
    return {t for t, entry in meta.items() if entry.get("checkpointed") == "true"}


def _unmark_checkpointed(project_dir: Path, targets: list[str]) -> None:
    """Drop the checkpoint marker for committed targets (meta rewrite, best-effort)."""
    meta = _load_staging_meta(project_dir)
    changed = False
    for target in targets:
        entry = meta.get(target)
        if entry is not None and entry.pop("checkpointed", None) is not None:
            changed = True
            if not entry:
                meta.pop(target, None)
    if changed:
        meta_path = project_dir / STAGING_DIR / ".staging-meta.json"
        if meta:
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            safe_write(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
        elif meta_path.exists():
            meta_path.unlink()
            _prune_empty_dirs(project_dir, meta_path.parent)
    log.debug("staging_unmarked_checkpointed", count=len(targets))


def _prune_empty_dirs(project_dir: Path, leaf: Path) -> None:
    """Remove now-empty staging subdirectories up to (not including) staging root."""
    staging_root = project_dir / STAGING_DIR
    node = leaf
    while node != staging_root and staging_root in node.parents:
        try:
            node.rmdir()
        except OSError:
            break
        node = node.parent


def discard_staging(project_dir: Path | str, reason: str) -> None:
    """Explicitly discard all staged products with an audit log (C30 R1, F323).

    Used on the MODIFY baseline decision: human edits become the baseline and
    the old staged LLM output is discarded through the same audited predicate
    as reject — not a third silent cleanup path.
    """
    project_dir = Path(project_dir)
    meta = _load_staging_meta(project_dir)
    log.info("staging_discarded", reason=reason, targets=sorted(meta.keys()))
    clear_staging(project_dir)


def clear_staging(project_dir: Path | str, *, preserve_checkpointed: bool = False) -> None:
    """Remove staging files (used on review reject / modify discard).

    Uses shutil.rmtree because deletion cannot be routed through safe_write
    (which only creates/replaces files). The file is on the purity-lint
    transitional allowlist for this reason.

    C30 R1 (F318): with ``preserve_checkpointed=True`` (emergency/atexit
    path), targets marked via :func:`mark_staging_checkpointed` SURVIVE —
    they are pending an explicit review decision, destroying them would
    silently void an approve. Explicit decision paths (reject, modify
    baseline) call without the flag and clear everything.
    """
    project_dir = Path(project_dir)
    staging_dir = project_dir / STAGING_DIR
    if not staging_dir.exists():
        log.debug("staging_clear_noop", reason="staging dir does not exist")
        return
    if not preserve_checkpointed:
        shutil.rmtree(staging_dir)
        log.info("staging_cleared", staging_dir=str(staging_dir))
        return
    keep = staging_checkpointed_targets(project_dir)
    if not keep:
        shutil.rmtree(staging_dir)
        log.info("staging_cleared_preserving_checkpointed", preserved=0)
        return
    removed = 0
    for path in sorted(staging_dir.rglob("*"), reverse=True):
        if path.is_dir():
            continue
        rel = path.relative_to(staging_dir).as_posix()
        if rel in keep or rel == ".staging-meta.json":
            continue
        path.unlink()
        removed += 1
    # Prune directories that only held removed files (bottom-up).
    for node in sorted(
        (p for p in staging_dir.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True
    ):
        try:
            next(node.iterdir())
        except StopIteration:
            node.rmdir()
    log.info("staging_cleared_preserving_checkpointed", preserved=len(keep), removed=removed)
