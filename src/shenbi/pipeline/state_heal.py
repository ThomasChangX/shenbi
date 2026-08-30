"""Self-heal orphaned state counters on resume (spec §3.4).

After a crash, retry_budget_consumed / revision_count may be
stale or empty. heal_state_counters cross-checks each against disk reality
and repairs conservatively (never undercount consumed retry budget). Every
heal action is logged and returned as a description string for auditability.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.state import PipelineState

log = get_logger(__name__)


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


def heal_state_counters(state: PipelineState, project_dir: Path) -> list[str]:
    """Self-heal orphaned state counters by cross-checking against disk.

    Returns a list of heal-action description strings (empty == nothing healed).
    Safe to call on every resume; idempotent.
    """
    actions: list[str] = []
    actions += _heal_retry_budget(state, project_dir)
    actions += _heal_revision_counts(state, project_dir)
    return actions
