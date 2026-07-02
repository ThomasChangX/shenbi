"""Centralized error handling and retry/escalation logic. Spec section 11.

Replaces the inline _handle_failure functions that were duplicated in
genesis.py and chapter_loop.py. Each decision function is a pure
predicate (returns True to retry, False to escalate) so callers retain full
control over state mutation and checkpoint raising.

Retry limits (spec section 11):

  * dispatch/gate failure  -- max 2 retries (3 total attempts), then escalate
  * audit BLOCKING         -- max 3 revision rounds, then escalate
  * scoring failure        -- exit 2 re-dispatch, exit 3 run G4 first
  * state-settling failure -- mark settling_failed, pause for human

The same-type interruption rule (same-type failure >= 3) is satisfied by the
per-skill escalation: when retry_counts[skill] reaches the configured
limit the orchestrator raises an escalation checkpoint, which pauses the
pipeline for root-cause analysis.
"""

from __future__ import annotations

from shenbi.logging import get_logger
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.state import (
    ChapterState,
    CheckpointType,
    PipelineState,
)

log = get_logger(__name__)

# Spec section 11 defaults. The actual enforcement reads
# state.config.max_revision_retries / max_audit_retries so that the
# limits remain configurable; these constants document the spec values.
MAX_DISPATCH_RETRIES = 2  # 2 retries == 3 total attempts
MAX_AUDIT_RETRIES = 3


def handle_dispatch_failure(
    state: PipelineState,
    skill: str,
    attempt: int,
) -> bool:
    """Decide whether to retry or escalate a dispatch/gate failure (spec S11).

    *attempt* is the 1-based current attempt number. Returns True when the
    caller should re-dispatch (attempt < max_revision_retries, i.e. at most
    2 retries / 3 total attempts with the default config), False when retries
    are exhausted and an escalation checkpoint is needed.
    """
    limit = state.config.max_revision_retries
    if attempt < limit:
        log.warning("dispatch_retry", skill=skill, attempt=attempt, limit=limit)
        return True
    log.error("dispatch_escalation", skill=skill, attempts=attempt, limit=limit)
    return False


def handle_audit_blocking(
    state: PipelineState,
    chapter: int,
    revision_count: int,
) -> bool:
    """Decide whether to retry the revision loop after audit BLOCKING (spec S11).

    Returns True while revision_count < max_audit_retries (the caller should
    re-revise and re-audit), False when the loop is exhausted and an
    escalation checkpoint is needed.
    """
    limit = state.config.max_audit_retries
    if revision_count < limit:
        log.warning(
            "audit_revision_retry",
            chapter=chapter,
            revision=revision_count,
            limit=limit,
        )
        return True
    log.error("audit_escalation", chapter=chapter, revisions=revision_count, limit=limit)
    return False


def handle_scoring_failure(state: PipelineState, exit_code: int) -> bool:
    """Decide the recovery action for a scoring failure (spec S11).

    Exit code 2: validation failure -- re-dispatch the skill and re-run G3.
    Exit code 3: marker file missing -- run G4 first, then re-score.
    Any other exit code: no automatic recovery path.

    Returns True when a retry path exists, False otherwise.
    """
    if exit_code == 2:
        log.warning("scoring_redispatch", exit_code=exit_code)
        return True
    if exit_code == 3:
        log.warning("scoring_run_g4_first", exit_code=exit_code)
        return True
    log.error("scoring_unrecoverable", exit_code=exit_code)
    return False


def handle_state_settle_failure(state: PipelineState, chapter: int) -> None:
    """Mark settling_failed on the chapter and pause for human review (spec S11).

    The chapter status is set to "settling_failed" and an escalation
    checkpoint is raised. The pipeline phase stays chapter-loop so the user
    can resolve the issue and resume without a full restart.
    """
    key = str(chapter)
    cs = state.chapter_loop.chapter_states.get(key)
    if cs is None:
        cs = ChapterState()
        state.chapter_loop.chapter_states[key] = cs
    cs.status = "settling_failed"
    set_checkpoint(
        state,
        CheckpointType.ESCALATION,
        chapter=chapter,
        context=(
            f"Chapter {chapter} state-settling failed. Manual review required before resuming."
        ),
    )
    log.error("state_settle_failed", chapter=chapter)
