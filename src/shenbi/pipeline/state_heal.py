"""Self-heal orphaned state counters on resume (spec §3.4).

After a crash, retry_budget_consumed / revision_count / last_snapshot may be
stale or empty. heal_state_counters cross-checks each against disk reality
and repairs conservatively (never undercount consumed retry budget). Every
heal action is logged and returned as a description string for auditability.
"""

from __future__ import annotations

import re
from datetime import datetime, UTC
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.state import PipelineState

log = get_logger(__name__)

_SNAPSHOT_CHAPTER_RE = re.compile(r"chapter-(\d+)-")


def _extract_chapter_from_snapshot_name(name: str) -> int:
    m = _SNAPSHOT_CHAPTER_RE.search(name)
    return int(m.group(1)) if m else 0


def _heal_retry_budget(state: PipelineState, project_dir: Path) -> list[str]:
    """Seed retry_budget_consumed (min 1) for retry_feedback keys missing it."""
    actions: list[str] = []
    budget = state.chapter_loop.retry_budget_consumed
    for step_key in state.chapter_loop.retry_feedback:
        if step_key not in budget:
            budget[step_key] = 1
            log.warning(
                "retry_budget_consumed_healed",
                step_key=step_key,
                seeded_value=1,
                note="durable budget missing for key with retry_feedback",
            )
            actions.append(f"retry_budget_consumed_healed:{step_key}")
    return actions


def _heal_revision_counts(state: PipelineState, project_dir: Path) -> list[str]:
    """Reconcile revision_count with the presence of a revision-decisions file.

    Note (spec §3.4): the revision-decisions file is overwritten per round, so
    disk presence is a floor (0 or 1), not an exact revision history. Logged so
    the undercount is visible.
    """
    actions: list[str] = []
    for key, cs in state.chapter_loop.chapter_states.items():
        try:
            chapter_num = int(key)
        except ValueError:
            continue
        rev_path = project_dir / "chapters" / f"chapter-{chapter_num}-revision-decisions.json"
        disk_count = 1 if rev_path.exists() else 0
        if cs.revision_count != disk_count:
            log.warning(
                "revision_count_healed",
                chapter=chapter_num,
                state_value=cs.revision_count,
                disk_value=disk_count,
                note="disk_count undercounts: revision-decisions file is overwritten per round",
            )
            actions.append(
                f"revision_count_healed:ch{chapter_num}:{cs.revision_count}->{disk_count}"
            )
            # Use max() so we don't lose the in-memory count if it's higher than the disk floor.
            cs.revision_count = max(cs.revision_count, disk_count)
    return actions


def _heal_last_snapshot(state: PipelineState, project_dir: Path) -> list[str]:
    """Point last_snapshot at the newest on-disk snapshot if it is empty."""
    if state.last_snapshot:
        return []
    snap_dir = project_dir / "snapshots"
    if not snap_dir.exists():
        return []
    snaps = sorted(snap_dir.glob("chapter-*.md"), key=lambda p: p.stat().st_mtime)
    if not snaps:
        return []
    latest = snaps[-1]
    state.last_snapshot = {
        "chapter": _extract_chapter_from_snapshot_name(latest.name),
        "path": str(latest.relative_to(project_dir)),
        "timestamp": datetime.fromtimestamp(latest.stat().st_mtime, tz=UTC).strftime(
            "%Y%m%dT%H%M%S"
        ),
    }
    log.info("last_snapshot_healed", path=str(latest))
    return [f"last_snapshot_healed:{state.last_snapshot['path']}"]


def heal_state_counters(state: PipelineState, project_dir: Path) -> list[str]:
    """Self-heal orphaned state counters by cross-checking against disk.

    Returns a list of heal-action description strings (empty == nothing healed).
    Safe to call on every resume; idempotent.
    """
    actions: list[str] = []
    actions += _heal_retry_budget(state, project_dir)
    actions += _heal_revision_counts(state, project_dir)
    actions += _heal_last_snapshot(state, project_dir)
    return actions
