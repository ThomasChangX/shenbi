"""CLI entry point for the novel pipeline.

Spec: docs/superpowers/specs/archive/2026-07-01-novel-pipeline-design.md Section 2.2.

Commands:
    init <seed-file> [--project-dir <dir>]
    next <project-dir>
    status <project-dir>
    review <project-dir> approve|reject|modify [--feedback <file>]
    resume <project-dir>
    chapters <project-dir>

All machine-readable output goes to stdout via :func:`emit_json`; human
diagnostics go to stderr via structlog (see ``cli_utils`` module docstring).
Every file write is routed through :func:`safe_write` (atomic, fsync, locked)
to satisfy the src/shenbi purity lint. Result-envelope status values use the
typed :class:`CommandStatus` vocabulary (spec D3) rather than bare literals.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.cli_utils import echo, emit_json
from shenbi.logging import configure_logging, get_logger
from shenbi.pipeline.filelock_utils import ReadLock, WriteLock
from shenbi.pipeline.chapter_loop import chapter_sort_key
from shenbi.pipeline.dispatch_helper import run_gate_g4
from shenbi.pipeline.machine import (
    clear_checkpoint,
    is_at_checkpoint,
    load_state,
    save_state,
    set_checkpoint,
)
from shenbi.pipeline.seed_parser import parse_seed
from shenbi.pipeline.state import (
    CheckpointType,
    CheckpointData,
    ClosureState,
    GenesisState,
    PipelineState,
    PipelinePhase,
    ReviewDecision,
)
from shenbi.safe_write import safe_write
from shenbi.status import CommandStatus, GateStatus


# Orchestration loop: phase dispatch, trigger checks, closure transition
#: Truth files that are derived from other truth files and need re-sync
#: when the source file is modified by a reviewer (spec \u00a79.2).
#: Maps checkpoint type to list of (skill, prompt_suffix) tuples.
DERIVED_TRUTH_MAP: dict[str, list[tuple[str, str]]] = {
    CheckpointType.CHAPTER_MEMO.value: [
        ("shenbi-pacing-design", "Re-sync pacing design after chapter-plan modify"),
    ],
    CheckpointType.STATE_SETTLE.value: [
        ("shenbi-relationship-map", "Re-sync relationship map after truth modify"),
        ("shenbi-foreshadowing-resolve", "Re-solve foreshadowing after truth modify"),
    ],
    # PER_CHAPTER reject-redo queues a revision re-dispatch (spec #6 F340):
    # rolling the whole chapter back would re-fire prev-chapter volume-boundary
    # fan-out and strand chapter_states; a targeted revision with feedback is
    # the "redo the chapter review" semantics. Also applies to MODIFY (a human
    # edit to the review artifact should propagate the same way).
    CheckpointType.PER_CHAPTER.value: [
        ("shenbi-chapter-revision", "Revise rejected chapter with feedback"),
        # Fixcheck P2 (2026-09-29): without a settle re-run after the
        # revision, truth files keep the PRE-revision draft's settlement
        # forever (ch1/ch2 truth rode placeholders while revised chapters
        # advanced). Order matters: revision lands first, settle then reads
        # the revised chapters/chapter-N.md.
        # batch #15 #41 (probe20 adjudication #004D): the revision shifts
        # chapter lines ~10-20 — the re-settle MUST re-anchor every
        # 证据/evidence line reference to the POST-revision chapter text,
        # not reuse the pre-revision citations riding in staging.
        (
            "shenbi-state-settling",
            "Re-settle truth files after the revised chapter — every evidence/证据 "
            "line reference (chapter-N.md Lnn) must be re-located against the "
            "POST-revision chapter text; never reuse pre-revision line numbers",
        ),
    ],
}


#: #53 (probe21 adjudication #009): a REJECT/MODIFY of an OLDER chapter's
#: chapter-scoped checkpoint must never rewind the chapter-loop step cursor —
#: the stale ch1 STATE_SETTLE reject set ``step_index=7`` while the loop sat
#: at ch2, sending the un-drafted chapter into settle→audit→revision (ghost
#: chain, fabricated truth). The redo belongs to the checkpoint's OWN chapter
#: and rides the re-dispatch queue — the same vehicle the audit-routed
#: re-settlement uses — re-raising the checkpoint for that chapter.
_REDO_RE_DISPATCH: dict[str, tuple[str, str]] = {
    CheckpointType.STATE_SETTLE.value: (
        "shenbi-state-settling",
        "Re-settle truth files for this chapter incorporating the review "
        "feedback; re-locate every evidence/证据 line reference against the "
        "current chapter text",
    ),
    CheckpointType.CHAPTER_MEMO.value: (
        "shenbi-chapter-planning",
        "Re-plan this chapter incorporating the review feedback",
    ),
}


def _chapter_mismatch(state: PipelineState, cp: CheckpointData) -> bool:
    """True when a chapter-scoped checkpoint is reviewed after the loop's
    cursor has moved past its chapter (probe21: ch1 settle reviewed at ch2).
    """
    return (
        state.phase == PipelinePhase.CHAPTER_LOOP
        and cp.chapter is not None
        and cp.chapter != state.chapter_loop.current_chapter
    )


def _defer_redo_to_re_dispatch_queue(
    state: PipelineState, cp: CheckpointData, feedback: str | None = None
) -> None:
    """Queue the checkpoint's OWN-chapter redo instead of rewinding the
    step cursor (#53). The entry is chapter-tagged, so the executor's
    dispatch prompt and the re-raised checkpoint both target the
    checkpoint's chapter, never the chapter the loop currently sits on.
    """
    skill, _suffix = _REDO_RE_DISPATCH[cp.type.value]
    already = any(
        d.get("skill") == skill and d.get("chapter") == cp.chapter
        for d in state.pending_re_dispatches
    )
    if not already:
        state.pending_re_dispatches.append(
            {
                "skill": skill,
                "checkpoint_type": cp.type.value,
                "chapter": cp.chapter,
                "feedback": feedback,
            }
        )
    log.warning(
        "chapter_redo_deferred_to_re_dispatch",
        checkpoint=cp.type.value,
        checkpoint_chapter=cp.chapter,
        current_chapter=state.chapter_loop.current_chapter,
        skill=skill,
    )


def _queue_re_dispatches(
    state: PipelineState, cp: CheckpointData, feedback: str | None = None
) -> None:
    """Queue re-dispatches for derived truth files after a modify decision.

    After ``modify``, skills that produce derived truth from the modified files
    must be re-dispatched so derived files reflect the human edit.
    """
    entries = DERIVED_TRUTH_MAP.get(cp.type.value, [])
    for skill, _ in entries:
        # Avoid duplicate entries for the same skill.
        already = any(
            d.get("skill") == skill and d.get("chapter") == cp.chapter
            for d in state.pending_re_dispatches
        )
        if not already:
            state.pending_re_dispatches.append(
                {
                    "skill": skill,
                    "checkpoint_type": cp.type.value,
                    "chapter": cp.chapter,
                    "feedback": feedback,
                }
            )
            log.info("re_dispatch_queued", skill=skill, checkpoint=cp.type.value)


#: Re-dispatch retry cap (probe session 2026-09-29): a failed entry used to
#: stay in pending_re_dispatches forever and re-fired on EVERY resume — one
#: length-truncated chapter-revision burned 73 LLM calls / 2.3M tokens
#: (24.7% of probe cost). After this many attempts the entry is dropped with
#: an error log (the checkpoint trail keeps the feedback for human action).
RE_DISPATCH_RETRY_CAP = 3


#: #51 (probe21 adjudication #009): re-dispatch targets whose input is the
#: chapter DRAFT — they fabricate derived truth when the draft is absent, so
#: the executor prechecks existence and refuses to dispatch.
_DRAFT_CONSUMING_RE_DISPATCH_SKILLS = frozenset(
    {"shenbi-state-settling", "shenbi-foreshadowing-lifecycle", "shenbi-chapter-revision"}
)


def _re_dispatch_g4_must_fix(
    project_dir: Path, skill: str, chapter: int | None
) -> list[str] | None:
    """#51: structural-gate re-run for a successful re-dispatch.

    Returns the must_fix list on G4 failure, ``None`` when the output passed
    (or the skill has no chapter-loop structural profile / no files to check —
    the in-loop G4 owns those paths). The re-dispatch path used to re-raise
    review checkpoints over UNVALIDATED staging; the ghost chain's fabricated
    ch2 truth never met a structural gate.
    """
    from shenbi.pipeline.chapter_loop import (
        _resolve_g4_files,  # pyright: ignore[reportPrivateUsage]
        CHAPTER_STEPS,
    )

    step = next((s for s in CHAPTER_STEPS if s.skill == skill), None)
    if step is None:
        return None
    g4_files = _resolve_g4_files(project_dir, step, chapter or 0)
    if not g4_files:
        return None
    g4 = run_gate_g4(skill, g4_files, project_dir, chapter=chapter, phase="chapter_loop")
    if str(g4.get("status")) == GateStatus.PASS:
        return None
    return list(g4.get("must_fix", []))


def _execute_pending_re_dispatches(state: PipelineState, project_dir: Path) -> bool:
    """Execute all pending re-dispatches from state.

    Returns True if any re-dispatch was executed (caller may want to re-persist).
    Failed entries accumulate an ``attempts`` count and are DROPPED (error
    log) after :data:`RE_DISPATCH_RETRY_CAP` tries — an infinite silent
    retry loop is how a single truncated revision became a 73-call money
    pit (probe session, Stage 2 friction).
    """
    if not state.pending_re_dispatches:
        return False

    from shenbi.pipeline.dispatch_helper import dispatch_skill

    remaining: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for entry in state.pending_re_dispatches:
        skill = entry.get("skill", "")
        ch = entry.get("chapter")
        # Skip entries for checkpoint types no longer in DERIVED_TRUTH_MAP
        # (stale state from a previous pipeline version).
        prompt_suffix_lookup = DERIVED_TRUTH_MAP.get(entry.get("checkpoint_type", ""), [])
        redo_entry = _REDO_RE_DISPATCH.get(entry.get("checkpoint_type", ""))
        if not prompt_suffix_lookup and redo_entry is None:
            log.warning(
                "re_dispatch_unknown_type",
                checkpoint_type=entry.get("checkpoint_type", ""),
                skill=skill,
            )
            continue
        prompt_suffix = ""
        for s, p in prompt_suffix_lookup:
            if s == skill:
                prompt_suffix = p
                break
        if not prompt_suffix and redo_entry is not None and redo_entry[0] == skill:
            # #53 mismatch-deferred redo entries carry their own instruction
            # (their skill is not a DERIVED_TRUTH_MAP propagation member).
            prompt_suffix = redo_entry[1]
        prompt = prompt_suffix
        if ch:
            prompt = f"[Chapter {ch}] {prompt_suffix}"
        fb = entry.get("feedback")
        if fb:  # conditional: MODIFY-queued entries have no feedback (never render None)
            prompt += f"\n\nHuman review feedback (incorporate these changes): {fb}"

        # Staging-gated skills (state-settling writes truth through
        # staging/) must re-dispatch through their gated write path too —
        # a live-direct write would bypass the STATE_SETTLE review.
        from shenbi.pipeline.chapter_loop import CHAPTER_STEPS  # pyright: ignore[reportPrivateUsage]

        uses_staging = any(s.skill == skill and s.uses_staging for s in CHAPTER_STEPS)

        # #51 ghost-chain guard: never dispatch a draft-consuming writer for
        # a chapter whose chapters/chapter-N.md does not exist — the dispatch
        # would fabricate derived truth from nothing (probe21: a settle
        # re-run on the un-drafted ch2 poisoned every later truth file).
        if skill in _DRAFT_CONSUMING_RE_DISPATCH_SKILLS and ch is not None:
            draft = project_dir / "chapters" / f"chapter-{ch}.md"
            if not draft.exists():
                log.error("re_dispatch_draft_missing", skill=skill, chapter=ch, expected=str(draft))
                entry["blocked_reason"] = (
                    f"{skill}@ch{ch}: chapters/chapter-{ch}.md 不存在——"
                    "禁止对未起草章节重派（幽灵链防护 #51），需人工回卷游标后重试"
                )
                dropped.append(entry)
                continue

        result = dispatch_skill(skill, project_dir, prompt, uses_staging=uses_staging)
        if result.success:
            g4_must_fix = _re_dispatch_g4_must_fix(project_dir, skill, ch)
            if g4_must_fix is not None:
                # #51: failed structural gate consumes an attempt with the
                # must-fix wired forward — never re-raise a review checkpoint
                # over unvalidated staging.
                entry["attempts"] = int(entry.get("attempts", 0)) + 1
                g4_note = f"上次重派输出未过 G4 结构门：{g4_must_fix}"
                prev_fb = entry.get("feedback")
                entry["feedback"] = f"{prev_fb}\n\n{g4_note}" if prev_fb else g4_note
                log.error(
                    "re_dispatch_g4_failed",
                    skill=skill,
                    chapter=ch,
                    attempts=entry["attempts"],
                    must_fix=str(g4_must_fix)[:300],
                )
                if entry["attempts"] >= RE_DISPATCH_RETRY_CAP:
                    dropped.append(entry)
                    continue
                remaining.append(entry)
                continue
            log.info("re_dispatch_ok", skill=skill)
            if skill == "shenbi-state-settling" and ch is not None:
                # The re-settled increments ride staging — re-raise the
                # settle checkpoint so the human reviews them (approve
                # commits; the orchestrate loop returns on the checkpoint).
                set_checkpoint(
                    state,
                    CheckpointType.STATE_SETTLE,
                    chapter=ch,
                    context=(
                        f"Re-settlement after chapter {ch} revision — review "
                        "the staged truth increments before the chapter closes"
                    ),
                )
            elif skill == "shenbi-chapter-planning" and ch is not None:
                # #53 mismatch-deferred memo redo: the re-planned memo rides
                # staging — without re-raising CHAPTER_MEMO it would be
                # orphaned with no commit gate.
                set_checkpoint(
                    state,
                    CheckpointType.CHAPTER_MEMO,
                    chapter=ch,
                    context=(
                        f"Re-planned chapter {ch} after a review redo — review "
                        "the staged chapter plan before the chapter resumes"
                    ),
                )
        else:
            entry["attempts"] = int(entry.get("attempts", 0)) + 1
            # #45 (probe20): attempt-N stderr rides into the entry's feedback
            # so attempt N+1's prompt carries corrective signal — the queue
            # path used to retry byte-identically (15270/15270 tokens, 3
            # deterministic rejections). #30 wired the chapter_loop dispatch
            # sites only; this is the family fix.
            stderr_note = f"上次派发失败（输出未落盘）：{result.stderr[:2000]}"
            prev_fb = entry.get("feedback")
            entry["feedback"] = f"{prev_fb}\n\n{stderr_note}" if prev_fb else stderr_note
            if entry["attempts"] >= RE_DISPATCH_RETRY_CAP:
                log.error(
                    "re_dispatch_retry_cap_exceeded",
                    skill=skill,
                    chapter=ch,
                    attempts=entry["attempts"],
                    last_error=result.stderr[:200],
                )
                dropped.append(entry)  # checkpoint trail keeps the feedback
                continue
            log.warning("re_dispatch_failed", skill=skill, stderr=result.stderr[:200])
            remaining.append(entry)

    state.pending_re_dispatches = remaining
    if remaining or dropped:
        # #46 (probe20): a queue that cannot drain BLOCKS chapter advancement
        # by raising a human checkpoint — the orchestrate loop used to roll
        # into the next chapter while failures rode along (ch2 planned on
        # empty templates). Failures dominate a concurrent settle re-raise:
        # the settle checkpoint re-fires once the queue drains clean.
        stuck = [
            f"{e.get('skill')}@ch{e.get('chapter')}(attempts={e.get('attempts')})"
            for e in [*remaining, *dropped]
        ]
        reasons = [
            str(e.get("blocked_reason")) for e in [*remaining, *dropped] if e.get("blocked_reason")
        ]
        context = (
            "重派队列未能排空——仍失败或已达重试上限："
            + "、".join(stuck)
            + "。最近失败原因已并入各条目反馈；approve 后将带反馈重试，"
            "持续失败需人工裁决。"
        )
        if reasons:
            context += " 阻断原因：" + "；".join(reasons)
        set_checkpoint(
            state,
            CheckpointType.ESCALATION,
            chapter=dropped[0].get("chapter") if dropped else remaining[0].get("chapter"),
            context=context,
        )
    return True


def _read_total_chapters(project_dir: Path) -> int:
    """Delegate to _shared.read_total_chapters (single source, spec #6 R2/R3)."""
    from shenbi.pipeline._shared import read_total_chapters

    return read_total_chapters(project_dir)


def _update_total_chapters(project_dir: Path) -> int:
    """Delegate to _shared.update_total_chapters (single source, spec #6 R2)."""
    from shenbi.pipeline._shared import update_total_chapters

    return update_total_chapters(project_dir)


def _orchestrate_to_checkpoint(state: PipelineState, project_dir: Path) -> None:
    """Run pipeline steps until a checkpoint is reached or the pipeline completes.

    Assumes the caller already holds the WriteLock and will persist *state*.
    Dispatches to genesis / chapter-loop / closure step runners, and handles
    trigger execution + closure transition at the start of each new chapter.
    """
    # F304 (spec #6): RetryExhaustedError converts to an ESCALATION checkpoint
    # instead of escaping — the caller's save_state then persists the budget
    # trail (a top-level escape would skip save_state and the exhaustion
    # storm repeats one full cycle after crash-resume).
    from shenbi.exceptions import RetryExhaustedError
    from shenbi.pipeline.chapter_loop import DriftEscalationError

    try:
        from shenbi.pipeline.chapter_loop import (
            _cleanup_residual_staging,  # pyright: ignore[reportPrivateUsage]
            _has_pending_staging_step,  # pyright: ignore[reportPrivateUsage]
            run_chapter_step,
        )
        from shenbi.pipeline.closure import run_closure_step
        from shenbi.pipeline.genesis import run_genesis_step
        from shenbi.pipeline.transitions import (
            transition_chapter_to_closure,
            transition_closure_to_completed,
        )
        from shenbi.pipeline.triggers import check_triggers, run_triggered_skills

        # Clean residual staging at pipeline resume to prevent stale file accumulation.
        _cleanup_residual_staging(project_dir, has_pending_staging=_has_pending_staging_step(state))

        while True:
            # Execute any pending re-dispatches queued by modify decisions (G4).
            if _execute_pending_re_dispatches(state, project_dir):
                save_state(project_dir, state)
                if is_at_checkpoint(state):
                    return  # settle re-raise or #46 queue-drain escalation

            phase = state.phase

            if phase in (PipelinePhase.COMPLETED, PipelinePhase.FAILED):
                return

            if phase == PipelinePhase.GENESIS:
                if run_genesis_step(state, project_dir):
                    return
                # Save state after each genesis step so progress survives
                # process interruption (timeout, crash, etc.).
                save_state(project_dir, state)

            elif phase == PipelinePhase.CHAPTER_LOOP:
                cl = state.chapter_loop
                if cl.step_index == 0 and cl.current_chapter > 1:
                    total = _read_total_chapters(project_dir)
                    if total <= 0:
                        # Mid-book heal (spec #6 R2): in-flight projects past
                        # genesis never re-run the step-6 hook — recompute before
                        # the guard or the self-lock persists (56-chapter case).
                        from shenbi.pipeline._shared import update_total_chapters

                        total = update_total_chapters(project_dir)
                    if total > 0:
                        prev_ch = cl.current_chapter - 1
                        result = check_triggers(state, prev_ch, total)
                        if result.book_closure:
                            result.book_closure = False
                            if result.any_triggered():
                                ok = run_triggered_skills(state, project_dir, prev_ch, result)
                                if not ok:
                                    log.warning(
                                        "triggered_skill_failed_before_closure",
                                        chapter=prev_ch,
                                    )
                                    set_checkpoint(
                                        state,
                                        CheckpointType.ESCALATION,
                                        chapter=prev_ch,
                                        context=(
                                            f"Triggered skill failed for chapter "
                                            f"{prev_ch} before book closure"
                                        ),
                                    )
                                    save_state(project_dir, state)
                                    return
                                if is_at_checkpoint(state):
                                    cl.step_index = 1  # C1: prevent re-fire
                                    save_state(project_dir, state)
                                    return
                            transition_chapter_to_closure(state)
                            continue
                        if result.any_triggered():
                            ok = run_triggered_skills(state, project_dir, prev_ch, result)
                            if not ok:
                                log.warning(
                                    "triggered_skill_failed",
                                    chapter=prev_ch,
                                )
                                set_checkpoint(
                                    state,
                                    CheckpointType.ESCALATION,
                                    chapter=prev_ch,
                                    context=(f"Triggered skill failed for chapter {prev_ch}"),
                                )
                                save_state(project_dir, state)
                                return
                            if is_at_checkpoint(state):
                                cl.step_index = 1  # C1: prevent re-fire
                                save_state(project_dir, state)
                                return

                if run_chapter_step(state, project_dir):
                    return
                # Save state after each chapter step so progress survives
                # process interruption (timeout, crash, etc.).
                save_state(project_dir, state)

            elif phase == PipelinePhase.CLOSURE:
                # Closure runner returns True on any successful step (not just
                # checkpoints), unlike genesis/chapter_loop which return False
                # when a step merely advances. So we must inspect state to decide
                # whether to stop.
                if run_closure_step(state, project_dir):
                    if is_at_checkpoint(state):
                        return  # book-closure checkpoint raised
                    if state.closure == ClosureState.COMPLETED:
                        transition_closure_to_completed(state)
                        return  # step 10 done, pipeline complete
                    # Step advanced without checkpoint: save state and continue.
                    save_state(project_dir, state)
                else:
                    # Closure step failed. The closure runner has no internal
                    # retry logic, so raise an escalation checkpoint for human
                    # intervention rather than spinning on the same failing step.
                    # Dispatch escalation-review first, then set checkpoint.
                    from shenbi.pipeline.revision_router import dispatch_escalation

                    dispatch_escalation(
                        project_dir,
                        None,  # closure has no chapter context
                        context=f"Closure step {state.closure_step + 1} failed",
                    )
                    set_checkpoint(
                        state,
                        CheckpointType.ESCALATION,
                        context=f"Closure step {state.closure_step + 1} failed",
                    )
                    return

            else:
                return

    except RetryExhaustedError as exc:
        log.error("retry_budget_exhausted_escalation", error=str(exc))
        # Carry the chapter so a later REJECT can reset this step's budget
        # (chapter-less ESCALATION would make _reset_retry_budget a no-op —
        # the exact re-exhaustion trap it exists to prevent).
        esc_chapter = (
            state.chapter_loop.current_chapter
            if state.phase == PipelinePhase.CHAPTER_LOOP
            else None
        )
        set_checkpoint(
            state,
            CheckpointType.ESCALATION,
            chapter=esc_chapter,
            context=f"Retry budget exhausted: {exc}",
        )
    except DriftEscalationError as exc:
        # R4 (F620): ESCALATE must persist as a resumable ESCALATION checkpoint
        # (mirrors RetryExhaustedError) — otherwise every resume re-raises at
        # the same step in a crash loop instead of pausing for human review.
        log.error("drift_escalate_checkpoint", error=str(exc))
        esc_chapter = (
            state.chapter_loop.current_chapter
            if state.phase == PipelinePhase.CHAPTER_LOOP
            else None
        )
        set_checkpoint(
            state,
            CheckpointType.ESCALATION,
            chapter=esc_chapter,
            context=f"Linguistic drift ESCALATE: {exc}",
        )


def _emit_orchestration_result(state: PipelineState) -> None:
    """Emit the final JSON status after the orchestration loop exits."""
    if is_at_checkpoint(state):
        emit_json(
            {
                "status": CommandStatus.BLOCKED,
                "checkpoint": state.pending_checkpoint.type.value,
                "artifact": state.pending_checkpoint.artifact,
            }
        )
    else:
        emit_json({"status": CommandStatus.OK, "phase": state.phase.value})


def _checkpoint_staging_targets(project_dir: Path, cp: CheckpointData) -> list[str]:
    """Staging targets a checkpoint OWNS — the single map both approve
    (commit) and reject (scoped discard, #39) act on, so the two decisions
    can never diverge on what belongs to this checkpoint.
    """
    from shenbi.pipeline.chapter_loop import staged_decisions_targets

    if cp.type == CheckpointType.CHAPTER_MEMO:
        chapter = cp.chapter or 1
        targets = [f"plans/chapter-{chapter}-plan.md"]
        # audit-T5 C1: contract-declared sidecar joins the same batch.
        targets += staged_decisions_targets(project_dir, "shenbi-chapter-planning", chapter)
    elif cp.type in (CheckpointType.STATE_SETTLE, CheckpointType.PER_CHAPTER):
        # I3: glob all staged truth files rather than hardcoding one.
        from shenbi.pipeline.checkpoint import STAGING_DIR

        staging_truth = project_dir / STAGING_DIR / "truth"
        if staging_truth.is_dir():
            targets = [f"truth/{p.name}" for p in sorted(staging_truth.glob("*.md"))]
        else:
            targets = []
        targets += staged_decisions_targets(project_dir, "shenbi-state-settling", cp.chapter)
    else:
        return []
    return targets


def _reject_staging_scoped(project_dir: Path, cp: CheckpointData) -> None:
    """#39: discard the checkpoint's OWN staged products on reject.

    Other checkpoints' staging (e.g. settle increments during an
    escalation reject) survives — see :func:`_checkpoint_staging_targets`.
    """
    from shenbi.pipeline.checkpoint import discard_staging_targets

    targets = _checkpoint_staging_targets(project_dir, cp)
    if not targets:
        log.info("reject_staging_scope_none", checkpoint=cp.type.value)
        return
    discard_staging_targets(project_dir, targets, reason=f"reject:{cp.type.value}")


def _commit_staging_for_checkpoint(project_dir: Path, cp: CheckpointData) -> None:
    """Commit staging files for checkpoint-gated skills (spec section 2.7).

    CHAPTER_MEMO and STATE_SETTLE checkpoints own their staging files
    directly; PER_CHAPTER must also commit any truth staging still pending —
    a state-settling redo after a rejected STATE_SETTLE checkpoint does not
    re-raise the settle checkpoint, so its staged truth rides until the
    per-chapter review. Unconditionally clearing without committing (probe
    session 2026-09-28) destroyed chapter 1's increments on its per-chapter
    approve. Each target is committed individually so a missing file for one
    type does not block the other. The staging directory is cleared
    afterwards.
    """
    from shenbi.pipeline.checkpoint import commit_staging
    from shenbi.pipeline.chapter_loop import staged_decisions_targets

    if cp.type == CheckpointType.CHAPTER_MEMO:
        chapter = cp.chapter or 1
        targets = [f"plans/chapter-{chapter}-plan.md"]
        # audit-T5 C1: contract-declared sidecar joins the same commit batch,
        # otherwise clear_staging below silently destroys it.
        targets += staged_decisions_targets(project_dir, "shenbi-chapter-planning", chapter)
        # spec #72: dual-memo bundle — follower memo + sidecar join the batch.
        from shenbi.pipeline.chapter_loop import bundle_chapters

        for n in bundle_chapters(project_dir, chapter)[1:]:
            targets.append(f"plans/chapter-{n}-plan.md")
            targets += staged_decisions_targets(project_dir, "shenbi-chapter-planning", n)
    elif cp.type in (CheckpointType.STATE_SETTLE, CheckpointType.PER_CHAPTER):
        # I3: glob all staged truth files rather than hardcoding one.
        from shenbi.pipeline.checkpoint import STAGING_DIR

        staging_truth = project_dir / STAGING_DIR / "truth"
        if staging_truth.is_dir():
            targets = [f"truth/{p.name}" for p in sorted(staging_truth.glob("*.md"))]
            if cp.type == CheckpointType.PER_CHAPTER and not targets:
                # #39 observability: a per-chapter approve normally commits
                # staged truth; finding none after a settle ran is the smoke
                # of a silent-loss wipe.
                log.warning("per_chapter_no_staged_truth", chapter=cp.chapter)
        else:
            targets = []
            if cp.type == CheckpointType.PER_CHAPTER:
                log.warning("per_chapter_no_staged_truth", chapter=cp.chapter)
        targets += staged_decisions_targets(project_dir, "shenbi-state-settling", cp.chapter)
    else:
        return

    for target in targets:
        try:
            commit_staging(project_dir, [target])
        except FileNotFoundError:
            # Expected: file may have been cleared since the checkpoint was
            # raised — but stay observable (C30 audit-T1 M3): a checkpointed
            # survivor wiped elsewhere surfaces here as a silent loss.
            log.warning("staging_commit_target_missing", target=target, checkpoint=cp.type.value)

    # Clear staging dir regardless (remove any remaining staged files).
    from shenbi.pipeline.checkpoint import clear_staging

    clear_staging(project_dir)


log = get_logger(__name__)


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new novel project from a seed file.

    Parses the seed, writes ``novel.json`` / ``genre-config.json`` /
    ``genesis-context/*.md``, and bootstraps ``pipeline-state.json`` with the
    genesis phase already in-progress.  If the project directory already
    contains an incomplete pipeline state the command succeeds with status
    ``exists`` so the caller can simply ``resume`` rather than picking a new
    directory name.
    """
    # T2: structural validation BEFORE any lock/scaffold — an AI-tool-edited
    # outline that dropped/renamed sections fails fast with the full problem
    # list instead of silently degrading genesis context.
    from shenbi.pipeline.seed_parser import validate_seed

    seed_errors = validate_seed(args.seed_file)
    if seed_errors:
        emit_json(
            {
                "status": CommandStatus.ERROR,
                "message": "seed 结构校验未过（AI 改写 outline 后请先 just seed-validate）",
                "errors": seed_errors,
            }
        )
        return 1

    project_dir = (
        Path(args.project_dir)
        if args.project_dir
        else Path.cwd() / f"novel-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    )
    state_file = project_dir / "pipeline-state.json"

    # spec #37 F327/T606: check + seed writes + save inside ONE WriteLock
    # critical section — the old check(ReadLock)->write(unlocked)->save(WL)
    # split let two concurrent inits both pass the existence check.
    try:
        with WriteLock(project_dir):
            return _cmd_init_locked(args, project_dir, state_file)
    except TimeoutError:
        emit_json(
            {
                "status": CommandStatus.BLOCKED,
                "message": "pipeline is busy — another process holds the write lock, retry shortly",
            }
        )
        return 1


def _cmd_init_locked(
    args: argparse.Namespace,
    project_dir: Path,
    state_file: Path,
) -> int:
    if state_file.exists():
        try:
            existing = load_state(project_dir)
        except Exception:
            emit_json(
                {
                    "status": CommandStatus.ERROR,
                    "message": "pipeline-state.json exists but is unreadable",
                }
            )
            return 1
        if existing.phase in (PipelinePhase.COMPLETED, PipelinePhase.FAILED):
            emit_json(
                {
                    "status": CommandStatus.ERROR,
                    "message": f"project already in terminal phase: {existing.phase.value}",
                }
            )
            return 1
        emit_json(
            {
                "status": CommandStatus.EXISTS,
                "project_dir": str(project_dir),
                "phase": existing.phase.value,
                "message": "project already initialized — use 'pipeline resume' to continue",
            }
        )
        return 0

    project_dir.mkdir(parents=True, exist_ok=True)

    # Scaffold the core truth dirs upfront: `_verify_truth_integrity`
    # requires them to exist on EVERY resume — including the first one,
    # before any genesis step has lazily created them via its writers.
    # Without this, init→resume deadlocks on the F325 fail-fast wiring.
    for core_dir in ("truth", "characters", "outline", "world"):
        (project_dir / core_dir).mkdir(exist_ok=True)

    # Spec #80 T2: seed empty facts files (props/counters/identity) so the
    # invariant gates have their WARN-visible bootstrap surface from init
    # (write-if-absent, idempotent — same discipline as seed_style_directives).
    from shenbi.facts.store import seed_empty as seed_facts_empty

    seed_facts_empty(project_dir)

    # Session31 Q1: seed the universal style TARGET so the channel is never a
    # blank-page problem (write-if-absent; never clobbers a user edit).
    from shenbi.pipeline.style_seed import seed_style_directives

    seed_style_directives(project_dir)

    seed_data = parse_seed(args.seed_file)

    # T3: CLI override wins over the seed-declared 目标章节数.
    if getattr(args, "target_chapters", None):
        seed_data.novel_json["target_total_chapters"] = int(args.target_chapters)

    # Write novel.json (seed metadata; total_chapters set later by volume-outlining).
    novel_json_path = project_dir / "novel.json"
    safe_write(
        novel_json_path,
        json.dumps(seed_data.novel_json, indent=2, ensure_ascii=False),
    )

    # Write genre-config.json when the seed supplied narrative parameters.
    if seed_data.genre_config:
        genre_config = {"version": "1.0", **seed_data.genre_config}
        safe_write(
            project_dir / "genre-config.json",
            json.dumps(genre_config, indent=2, ensure_ascii=False),
        )

    # Persist each genesis-context section as its own prompt fragment. Since
    # spec #69 these are consumed: the five genesis skills declare the
    # fragment paths in their contract reads (worldbuilding /
    # character-design / story-architecture / faction-builder /
    # volume-outlining) — see the genesis-context globs entry in
    # truth-files.yaml.
    ctx_dir = project_dir / "genesis-context"
    for key, value in seed_data.genesis_context.items():
        if value:
            safe_write(ctx_dir / f"{key}.md", value)

    # Genesis starts in-progress per spec section 3.1.
    state = PipelineState.default(project_dir=str(project_dir))
    state.genesis.state = GenesisState.IN_PROGRESS

    # --auto flag: reduce checkpoints for automated / Codex-driven runs so
    # fewer human (or simulated-human) approvals are needed per chapter.
    if args.auto:
        state.config.per_chapter_review_enabled = False
        state.config.chapter_memo_review_required = False
        state.config.state_settle_review_required = False
        # _complete_chapter() reads the chapter-loop copy; keep both in sync.
        state.chapter_loop.per_chapter_review_enabled = False
        log.info("auto_mode_enabled", project_dir=str(project_dir))

    save_state(project_dir, state)  # caller (_cmd_init_locked) holds WriteLock

    log.info("project_initialized", project_dir=str(project_dir))
    emit_json(
        {
            "status": CommandStatus.OK,
            "project_dir": str(project_dir),
            "novel_json": str(novel_json_path),
            "total_chapters": seed_data.novel_json.get("total_chapters", "unknown"),
        }
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Query current pipeline state and emit it as a JSON snapshot."""
    project_dir = Path(args.project_dir)

    try:
        with ReadLock(project_dir):
            state = load_state(project_dir)
    except FileNotFoundError:
        emit_json(
            {
                "status": CommandStatus.ERROR,
                "message": f"pipeline-state.json not found in {project_dir}",
            }
        )
        return 1

    cp = state.pending_checkpoint
    emit_json(
        {
            "phase": state.phase.value,
            "current_chapter": state.chapter_loop.current_chapter,
            "current_step": state.chapter_loop.current_step,
            "pending_checkpoint": cp.type.value if cp.type != CheckpointType.NONE else None,
            "checkpoint_chapter": cp.chapter,
            "checkpoint_artifact": cp.artifact,
        }
    )
    return 0


def _reset_retry_budget(state: PipelineState, cp: CheckpointData) -> None:
    """REJECT-redo: reset the producing step's retry counters (spec #6 F340) —
    otherwise an ESCALATION redo re-exhausts immediately (clear_checkpoint
    clears retry_counts on ESCALATION resolution but NOT retry_budget_consumed).
    """
    ch = cp.chapter
    # chapter-less ESCALATION ("ch") clears ALL chapter-scoped budgets
    prefix = f"ch{ch}-" if ch is not None else "ch"
    state.chapter_loop.retry_counts = {
        k: v for k, v in state.chapter_loop.retry_counts.items() if not k.startswith(prefix)
    }
    state.chapter_loop.retry_budget_consumed = {
        k: v
        for k, v in state.chapter_loop.retry_budget_consumed.items()
        if not k.startswith(prefix)
    }
    state.genesis.retry_counts.clear()
    state.closure_retry_counts.clear()
    # C33 R3 (T508, spec #47): idempotent mirror of clear_checkpoint's new
    # per-chapter audit counter reset (clear_checkpoint is authoritative).
    for k in (
        [str(cp.chapter)] if cp.chapter is not None else list(state.chapter_loop.chapter_states)
    ):
        cs = state.chapter_loop.chapter_states.get(k)
        if cs is not None:
            cs.audit_retry_count = 0
            cs.revision_count = 0


def _rollback_genesis_step(state: PipelineState) -> None:
    """GENESIS_COMPLETE redo: cursor back one step AND un-mark that step's skill.

    A stale skills_done entry makes the re-dispatch's G3.4 scorer evidence
    collide with its own generator route (fixcheck escalation 2026-09-29:
    step-17 re-run recorded scorer == generator, deterministic 3/3 fail).
    """
    from shenbi.pipeline.genesis import GENESIS_STEPS

    idx = state.genesis.current_step - 1
    if 0 <= idx < len(GENESIS_STEPS):
        skill = GENESIS_STEPS[idx].skill
        if skill in state.genesis.skills_done:
            state.genesis.skills_done.remove(skill)
    state.genesis.current_step = max(0, state.genesis.current_step - 1)


def _rollback_genesis_to_steps(
    state: PipelineState, step_nums: list[int], feedback: str | None = None
) -> None:
    """Scoped genesis rollback (probe8): rewind the cursor to the earliest
    listed step, drop ONLY those skills from ``skills_done`` — un-listed
    done steps are skipped on resume, not regenerated — and route the
    reviewer feedback into each redo target's corrective-feedback slot so
    the re-dispatch is not blind.

    #48 (probe21): the slot also carries a machine-extracted STRUCTURE
    BINDING of the redo target's current on-disk baseline — a feedback-bound
    regen shuffled every unbound layer (anchors, rule numbering) and needed
    four review rounds to converge. The snapshot is stored on
    ``frozen_bindings`` for the genesis-complete drift report (#49).
    """
    from shenbi.pipeline.genesis import (
        BINDING_FREEZE_HEADER,
        GENESIS_STEPS,
        extract_structure_bindings,
    )

    nums = set(step_nums)
    target_idx = min(nums) - 1
    project_dir = Path(state.project_dir) if state.project_dir else None
    for step in GENESIS_STEPS[target_idx:]:
        if step.step_num in nums:
            if step.skill in state.genesis.skills_done:
                state.genesis.skills_done.remove(step.skill)
            if step.skill in state.genesis.frozen_bindings:
                # Drift guard (probe22 adjudication #002): the on-disk baseline
                # of a CONTESTED redo step is the drifted output — re-extracting
                # would crown it the new freeze. First freeze wins; the
                # corrective block re-injects the ORIGINAL snapshot.
                log.info("genesis_binding_freeze_retained", skill=step.skill)
                binding_block = (
                    f"{BINDING_FREEZE_HEADER}\n{state.genesis.frozen_bindings[step.skill]}"
                )
                state.genesis.retry_feedback[step.skill] = (
                    f"{feedback}\n\n{binding_block}" if feedback else binding_block
                )
                continue
            binding = extract_structure_bindings(project_dir, step.skill) if project_dir else ""
            if binding:
                state.genesis.frozen_bindings[step.skill] = binding
                binding_block = f"{BINDING_FREEZE_HEADER}\n{binding}"
                state.genesis.retry_feedback[step.skill] = (
                    f"{feedback}\n\n{binding_block}" if feedback else binding_block
                )
            elif feedback:
                state.genesis.retry_feedback[step.skill] = feedback
        # Unlisted frozen skills are UNCONTESTED: the reviewer's redo list
        # ruling leaves their current output standing, so keeping the freeze
        # would re-report the (now accepted) drift at the next
        # genesis-complete raise.
        elif step.skill in state.genesis.frozen_bindings:
            state.genesis.frozen_bindings.pop(step.skill, None)
            log.info("genesis_binding_freeze_consumed_uncontested", skill=step.skill)
    state.genesis.current_step = target_idx


def _apply_reject_redo(
    state: PipelineState,
    cp: CheckpointData,
    feedback: str | None = None,
    redo_steps: list[int] | None = None,
) -> None:
    """REJECT = redo the step that raised the checkpoint (spec #6 F340).

    Full CheckpointType coverage; BOOK_CLOSURE keeps its existing transition.
    """
    from shenbi.pipeline.chapter_loop import CHAPTER_STEPS

    if cp.type == CheckpointType.CHAPTER_MEMO:
        if _chapter_mismatch(state, cp):
            _defer_redo_to_re_dispatch_queue(state, cp, feedback)
        else:
            state.chapter_loop.step_index = 1
    elif cp.type == CheckpointType.STATE_SETTLE:
        if _chapter_mismatch(state, cp):
            _defer_redo_to_re_dispatch_queue(state, cp, feedback)
        else:
            # spec #72: settling moved to table index 8 after the scene-split
            # insertion — resolve dynamically so future inserts can't rot it.
            state.chapter_loop.step_index = next(
                i for i, s in enumerate(CHAPTER_STEPS) if s.skill == "shenbi-state-settling"
            )
    elif cp.type == CheckpointType.GENESIS_COMPLETE:
        if redo_steps:
            _rollback_genesis_to_steps(state, redo_steps, feedback)
        else:
            _rollback_genesis_step(state)
        state.genesis.retry_counts.clear()
    elif cp.type == CheckpointType.VOLUME_BOUNDARY:
        if _chapter_mismatch(state, cp):
            # The step-0 rewind is positional: on resume the trigger fan-out
            # re-runs at the CURRENT chapter top — at a mismatch that would
            # fan out the wrong chapter (#53 family). Freeze the cursor; the
            # boundary decision must be re-made by human rewind, not by a
            # cursor the checkpoint does not own.
            log.warning(
                "volume_boundary_redo_deferred",
                checkpoint_chapter=cp.chapter,
                current_chapter=state.chapter_loop.current_chapter,
            )
        else:
            state.chapter_loop.step_index = 0  # next() re-runs the trigger fan-out
    elif cp.type == CheckpointType.PER_CHAPTER:
        # Redo the chapter REVISION (not the whole chapter — see the
        # DERIVED_TRUTH_MAP note) with the reject feedback attached.
        _queue_re_dispatches(state, cp, feedback=feedback)
    elif cp.type == CheckpointType.ESCALATION:
        _reset_retry_budget(state, cp)  # failing step re-runs with a fresh budget
    # BOOK_CLOSURE: handled by the existing transition below.


def cmd_review(args: argparse.Namespace) -> int:
    """Submit a review decision for the pending checkpoint.

    Clears the checkpoint, records the decision in ``checkpoint_history``, and
    optionally attaches reviewer feedback. Errors when no checkpoint is pending.
    """
    project_dir = Path(args.project_dir)

    try:
        with WriteLock(project_dir):
            state = load_state(project_dir)

            if not is_at_checkpoint(state):
                emit_json(
                    {"status": CommandStatus.ERROR, "message": "no pending checkpoint to review"}
                )
                return 1

            decision = ReviewDecision(args.decision)
            cp = state.pending_checkpoint

            # Validate inputs BEFORE any staging side effects (F390).
            feedback = None
            if args.feedback:
                feedback_path = Path(args.feedback)
                if not feedback_path.is_file():
                    log.error("feedback_file_not_found", path=str(feedback_path))
                    emit_json(
                        {
                            "status": CommandStatus.ERROR,
                            "message": f"feedback file not found: {args.feedback}",
                        }
                    )
                    return 1
                feedback = feedback_path.read_text(encoding="utf-8")

            # probe8 deadlock: scoped genesis-complete rejects need an explicit
            # redo-step list (adjudications already enumerate it). Validated
            # BEFORE any staging side effects, same F390 discipline.
            redo_steps: list[int] = []
            if getattr(args, "redo_steps", None):
                if decision != ReviewDecision.REJECT or cp.type != CheckpointType.GENESIS_COMPLETE:
                    emit_json(
                        {
                            "status": CommandStatus.ERROR,
                            "message": "--redo-steps is only valid for a genesis-complete reject",
                        }
                    )
                    return 1
                from shenbi.pipeline.genesis import GENESIS_STEPS

                try:
                    redo_steps = sorted(
                        {int(tok) for tok in args.redo_steps.split(",") if tok.strip()}
                    )
                except ValueError:
                    redo_steps = []
                if not redo_steps or any(n < 1 or n > len(GENESIS_STEPS) for n in redo_steps):
                    emit_json(
                        {
                            "status": CommandStatus.ERROR,
                            "message": (
                                f"--redo-steps must be comma-separated ints in "
                                f"1..{len(GENESIS_STEPS)}"
                            ),
                        }
                    )
                    return 1

            # Staging handling (spec section 2.7): approve commits staging
            # files to their final paths; reject clears staging. C30 F323:
            # MODIFY = human edits are the baseline — the old staged LLM
            # output is explicitly discarded (same audited predicate as
            # reject), NOT committed and then overwritten by re-dispatch.
            if decision == ReviewDecision.APPROVE:
                _commit_staging_for_checkpoint(project_dir, cp)
            elif decision == ReviewDecision.MODIFY:
                # Contract (C30 audit-T1 I2): human edits must land on the
                # COMMITTED artifact path or travel via modify_feedback —
                # edits made only to the staged copy are discarded with it.
                from shenbi.pipeline.checkpoint import discard_staging

                discard_staging(project_dir, reason="modify_baseline_human_edit")
            elif decision == ReviewDecision.REJECT:
                # #39 (probe20): a reject discards ONLY the products its own
                # checkpoint type owns (the same target set approve commits,
                # mirrored in _reject_staging_scoped). Checkpoint types that
                # own no staging (escalation, genesis-*, volume-boundary,
                # book-closure) clear NOTHING — the old unconditional
                # clear_staging destroyed the reviewed settle increments on
                # an escalation reject and every later writer merged against
                # shell bases.
                _reject_staging_scoped(project_dir, cp)

            if decision == ReviewDecision.REJECT:
                _apply_reject_redo(
                    state, cp, feedback=feedback, redo_steps=redo_steps
                )  # acts on the cp snapshot
            clear_checkpoint(state, decision)

            # Genesis-phase escalation: route feedback into the step's
            # corrective-feedback slot. Genesis re-dispatch reads
            # genesis.retry_feedback (genesis.py), NOT chapter_loop's
            # modify_feedback — without this, reviewer feedback on a genesis
            # escalation is a dead wire (canary escalation, 2026-09-28).
            if (
                feedback
                and cp.type == CheckpointType.ESCALATION
                and state.phase == PipelinePhase.GENESIS
            ):
                from shenbi.pipeline.genesis import GENESIS_STEPS

                idx = state.genesis.current_step
                if 0 <= idx < len(GENESIS_STEPS):
                    state.genesis.retry_feedback[GENESIS_STEPS[idx].skill] = feedback

            # GAP-a (fixcheck ch1, 17:17 evidence): the routing above is
            # genesis-gated, so a chapter-phase ESCALATION reject's feedback
            # never reached any re-dispatch prompt (a 1385-char repair
            # instruction was silently dropped while the 17:22-17:33 retries
            # ran blind). Route it into the failing step's corrective slot —
            # step_index still points at the un-completed step, and the redo
            # dispatch injects the slot via _append_feedback_injections.
            if (
                feedback
                and cp.type == CheckpointType.ESCALATION
                and state.phase == PipelinePhase.CHAPTER_LOOP
                and cp.chapter is not None
            ):
                from shenbi.pipeline.chapter_loop import CHAPTER_STEPS

                # Phase3 dead-route fix (adjudication 191 observation): a
                # TRIGGERED-skill failure raises ESCALATION while the loop
                # sits at next-chapter step_index=0 — CHAPTER_STEPS[0] is the
                # deterministic pipeline-volume-align, which never consumes
                # retry_feedback. When last_trigger_failure matches this
                # checkpoint's chapter, the feedback belongs to THAT skill;
                # run_triggered_skills injects it into the re-dispatch.
                trig = state.last_trigger_failure or {}
                if trig.get("chapter") == cp.chapter and trig.get("skill"):
                    state.chapter_loop.retry_feedback[f"ch{cp.chapter}-{trig['skill']}"] = feedback
                else:
                    idx = state.chapter_loop.step_index
                    if 0 <= idx < len(CHAPTER_STEPS):
                        skill = CHAPTER_STEPS[idx].skill
                        state.chapter_loop.retry_feedback[f"ch{cp.chapter}-{skill}"] = feedback

            # G4: On modify, queue re-dispatches for derived truth files
            # (spec section 9.2: truth-sync propagation after human edit).
            if decision == ReviewDecision.MODIFY:
                # Roll back step cursor so resume re-dispatches the skill.
                # #53: at a chapter mismatch the rewind is DEFERRED to the
                # re-dispatch queue (same guard as _apply_reject_redo) — the
                # cursor belongs to the chapter the loop sits on.
                if cp.type == CheckpointType.CHAPTER_MEMO:
                    if _chapter_mismatch(state, cp):
                        _defer_redo_to_re_dispatch_queue(state, cp, feedback)
                    else:
                        state.chapter_loop.step_index = 1  # CHAPTER_STEPS[1] = chapter-planning
                elif cp.type == CheckpointType.STATE_SETTLE:
                    if _chapter_mismatch(state, cp):
                        _defer_redo_to_re_dispatch_queue(state, cp, feedback)
                    else:
                        from shenbi.pipeline.chapter_loop import (
                            CHAPTER_STEPS,
                        )

                        state.chapter_loop.step_index = next(
                            i
                            for i, s in enumerate(CHAPTER_STEPS)
                            if s.skill == "shenbi-state-settling"
                        )  # spec #72: dynamic (settling at index 8 after insertion)
                elif cp.type == CheckpointType.GENESIS_COMPLETE:
                    _rollback_genesis_step(state)

                # Store feedback for the next dispatch
                if feedback:
                    state.chapter_loop.modify_feedback = feedback

                _queue_re_dispatches(state, cp)

            # I4: Rejecting a book-closure checkpoint transitions back to
            # chapter loop so the human can revise and re-close.
            if decision == ReviewDecision.REJECT and cp.type == CheckpointType.BOOK_CLOSURE:
                from shenbi.pipeline.transitions import (
                    transition_closure_to_chapter_loop,
                )

                transition_closure_to_chapter_loop(state)

            if feedback:
                state.checkpoint_history[-1]["feedback"] = feedback

            save_state(project_dir, state)
    except FileNotFoundError:
        emit_json({"status": CommandStatus.ERROR, "message": "project not found"})
        return 1

    log.info(
        "checkpoint_reviewed",
        decision=decision.value,
        checkpoint=state.checkpoint_history[-1]["type"],
    )
    emit_json(
        {
            "status": CommandStatus.OK,
            "decision": decision.value,
            "checkpoint_type": state.checkpoint_history[-1]["type"],
        }
    )
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    """Execute toward the next checkpoint (loop-until-checkpoint).

    Loads state under an exclusive WriteLock, runs the orchestration loop
    (genesis / chapter-loop / closure) until a checkpoint is reached or the
    pipeline completes, then persists state and emits the result. When a
    checkpoint is already pending, returns ``blocked`` without running.
    """
    project_dir = Path(args.project_dir)

    try:
        with WriteLock(project_dir):
            state = load_state(project_dir)
            if is_at_checkpoint(state):
                emit_json(
                    {
                        "status": CommandStatus.BLOCKED,
                        "message": "pending checkpoint requires review",
                        "checkpoint": state.pending_checkpoint.type.value,
                    }
                )
                return 1

            _orchestrate_to_checkpoint(state, project_dir)
            save_state(project_dir, state)
    except FileNotFoundError:
        emit_json({"status": CommandStatus.ERROR, "message": "project not found"})
        return 1

    _emit_orchestration_result(state)
    return 0


def _verify_truth_integrity(state: PipelineState, project_dir: Path) -> list[str]:
    """Lightweight truth-integrity check on resume (spec \u00a73.4).

    Checks that essential truth files and directories still exist for the
    current pipeline phase. Returns a list of missing critical paths. If
    a truth file is missing, the pipeline can fail fast here rather than
    on the first resumed step's G1 gate.
    """
    missing: list[str] = []

    # Core directories that must exist after genesis.
    core_dirs = ["truth", "characters", "outline", "world"]
    for d in core_dirs:
        p = project_dir / d
        if not p.is_dir():
            missing.append(str(p.relative_to(project_dir)))

    # If genesis completed, verify key genesis outputs.
    if state.phase in (PipelinePhase.CHAPTER_LOOP, PipelinePhase.CLOSURE, PipelinePhase.COMPLETED):
        genesis_outputs = [
            "world/story_bible.md",
            "genre-config.json",
            "characters/protagonist.md",
            "outline/story_frame.md",
            "outline/volume_map.md",
            "outline/rhythm_principles.md",
            "outline/thread_map.md",
            "truth/pending_hooks.md",
            "world/power_system.md",
            "world/locations.md",
            "characters/relationships.md",
            "truth/book_spine.md",
            "truth/author_intent.md",
            "style/style_profile.md",
            "world/factions.md",  # genesis step-5 output (F354)
            "foundation/review_report.md",  # genesis step-17 output (F354)
        ]
        for rel_path in genesis_outputs:
            if not (project_dir / rel_path).exists():
                missing.append(rel_path)

    # If chapter loop is active, verify the previous chapter's plan exists.
    # The CURRENT chapter's plan is created during its own step 2, so its
    # absence is normal — checking it flagged every chapter (F398).
    if state.phase == PipelinePhase.CHAPTER_LOOP:
        ch = state.chapter_loop.current_chapter
        if ch > 1:
            prev_plan = project_dir / "plans" / f"chapter-{ch - 1}-plan.md"
            if not prev_plan.exists():
                missing.append(f"plans/chapter-{ch - 1}-plan.md")

    if missing:
        log.warning("truth_integrity_check_failed", missing=missing)
    else:
        log.info("truth_integrity_check_passed")

    return missing


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume after a checkpoint review.

    Handles phase transitions triggered by the last checkpoint decision:
    approve genesis-complete enters the chapter loop, approve book-closure
    completes the pipeline. Then delegates to the orchestration loop.
    """
    project_dir = Path(args.project_dir)

    try:
        with WriteLock(project_dir):
            state = load_state(project_dir)

            # Self-heal orphaned counters from disk (spec §3.4):
            # retry_budget_consumed, revision_count.
            from shenbi.pipeline.state_heal import heal_state_counters

            heal_state_counters(state, project_dir)

            # Persist healed values immediately so crash-resume sees them.
            save_state(project_dir, state)

            # Heal emergency shutdown state (spec §3.4): if the pipeline was
            # interrupted by a crash/SIGTERM, the current_step will be marked
            # "EMERGENCY_SHUTDOWN_AT_{skill}". Restore the correct step name
            # from CHAPTER_STEPS so the loop can resume cleanly.
            cl = state.chapter_loop
            if cl.current_step and cl.current_step.startswith("EMERGENCY_SHUTDOWN"):
                from shenbi.pipeline.chapter_loop import CHAPTER_STEPS

                log.warning(
                    "resuming_from_emergency_shutdown",
                    chapter=cl.current_chapter,
                    step=cl.current_step,
                )
                if cl.step_index < len(CHAPTER_STEPS):
                    cl.current_step = CHAPTER_STEPS[cl.step_index].skill
                else:
                    cl.current_step = ""
                save_state(project_dir, state)

            # Truth-integrity check (spec §3.4): verify truth files exist
            # before resuming, so missing files surface immediately rather than
            # on the first step dispatch. C37 F325 wiring: the returned
            # missing-list was previously ignored — fail fast on it.
            _integrity_missing = _verify_truth_integrity(state, project_dir)
            if _integrity_missing:
                log.error("resume_truth_integrity_failed", missing=_integrity_missing)
                emit_json(
                    {
                        "status": CommandStatus.ERROR,
                        "message": "truth integrity check failed on resume",
                        "missing": _integrity_missing,
                    }
                )
                return 1

            # Detect stale/missing progress.json (no rebuild — spec #37 F630 ruling b).
            from shenbi.pipeline.chapter_loop import _auto_rebuild_progress_if_stale  # pyright: ignore[reportPrivateUsage]

            _auto_rebuild_progress_if_stale(project_dir)

            # C30 R2 (F371): clamp a runaway cursor to the committed-product
            # anchor BEFORE any transition logic keys off it, and migrate
            # old-generation steps_done names (F797).
            from shenbi.pipeline.chapter_loop import (
                _clamp_resume_cursor,  # pyright: ignore[reportPrivateUsage]
                migrate_steps_done,
            )

            cl_state = state.chapter_loop
            before = (cl_state.current_chapter, cl_state.step_index, cl_state.current_step)
            _clamp_resume_cursor(cl_state, project_dir)
            state_dirty = (
                cl_state.current_chapter,
                cl_state.step_index,
                cl_state.current_step,
            ) != before
            for ch_key, cs in list(cl_state.chapter_states.items()):
                migrated, changed = migrate_steps_done(cs.steps_done)
                if changed:
                    log.warning("steps_done_migrated", chapter=ch_key)
                    cs.steps_done = migrated
                    state_dirty = True

            if state.checkpoint_history:
                # C30 F371: consume the transition event instead of guessing
                # from history[-1] — the newest UNCONSUMED approve entry is
                # the one this resume acts on; older ones are already handled.
                # Entries written by pre-C30 versions carry no "consumed"
                # field and are treated as already handled (default True):
                # a one-way, WARN-noted discard — replaying them would
                # double-dispatch snapshot-manage.
                legacy_approves = [
                    e
                    for e in state.checkpoint_history
                    if e.get("decision") == "approve" and "consumed" not in e
                ]
                if legacy_approves:
                    log.warning(
                        "legacy_checkpoint_events_discarded",
                        count=len(legacy_approves),
                    )
                pending_event = next(
                    (
                        e
                        for e in reversed(state.checkpoint_history)
                        if e.get("decision") == "approve" and not e.get("consumed", True)
                    ),
                    None,
                )
                last = pending_event
                if last is not None:
                    last["consumed"] = True
                    state_dirty = True
                if last is not None and last.get("decision") == "approve":
                    cp_type = last.get("type")
                    if cp_type == CheckpointType.GENESIS_COMPLETE.value:
                        from shenbi.pipeline.transitions import (
                            transition_genesis_to_chapter_loop,
                        )

                        transition_genesis_to_chapter_loop(state)
                    elif cp_type == CheckpointType.VOLUME_BOUNDARY.value:
                        # C1: dispatch the deferred volume-boundary snapshot
                        # that was held pending checkpoint clearance (spec
                        # section 6.4: [CHECKPOINT] -> snapshot-manage).
                        from shenbi.pipeline.dispatch_helper import dispatch_skill

                        # Update total_chapters from the revised volume map
                        # (volume-boundary expansion may change the chapter count).
                        _update_total_chapters(project_dir)

                        snap_ch = last.get("chapter")
                        snap_result = dispatch_skill(
                            "shenbi-snapshot-manage",
                            project_dir,
                            f"Volume-boundary snapshot after chapter {snap_ch}.",
                        )
                        if not snap_result.success:
                            log.error(
                                "volume_boundary_snapshot_failed",
                                chapter=snap_ch,
                                rc=snap_result.returncode,
                            )
                            # Keep the event unconsumed so the next resume
                            # retries the snapshot (final-review I2: consuming
                            # here would permanently drop a failed dispatch).
                            last["consumed"] = False
                            state_dirty = False
                        # If this boundary was also the book-closure point,
                        # transition to closure (the step_index guard prevents
                        # the trigger block from re-firing on re-entry).
                        total = _read_total_chapters(project_dir)
                        if total > 0 and snap_ch and snap_ch >= total:
                            from shenbi.pipeline.transitions import (
                                transition_chapter_to_closure,
                            )

                            transition_chapter_to_closure(state)
                    # Book-closure approval does NOT complete the pipeline here.
                    # The closure runner paused before step 10 (snapshot-manage);
                    # the checkpoint was already cleared by ``review``, so falling
                    # through to _orchestrate_to_checkpoint runs step 10. The
                    # runner then sets closure=COMPLETED and the orchestrator
                    # calls transition_closure_to_completed (spec section 8).

            # Persist clamp/migration/consumption BEFORE the BLOCKED early
            # return, or every resume re-replays them (audit-T2 I3).
            if state_dirty:
                save_state(project_dir, state)

            if is_at_checkpoint(state):
                emit_json(
                    {
                        "status": CommandStatus.BLOCKED,
                        "message": "pending checkpoint requires review",
                        "checkpoint": state.pending_checkpoint.type.value,
                    }
                )
                return 1

            _orchestrate_to_checkpoint(state, project_dir)
            save_state(project_dir, state)
    except FileNotFoundError:
        emit_json({"status": CommandStatus.ERROR, "message": "project not found"})
        return 1

    _emit_orchestration_result(state)
    return 0


def cmd_chapters(args: argparse.Namespace) -> int:
    """Show per-chapter progress overview."""
    project_dir = Path(args.project_dir)

    try:
        with ReadLock(project_dir):
            state = load_state(project_dir)
    except FileNotFoundError:
        emit_json({"status": CommandStatus.ERROR, "message": "project not found"})
        return 1

    chapters = [
        {
            "chapter": int(ch_num_str),
            "status": ch_state.status,
            "resonance_score": ch_state.resonance_score,
            "revision_count": ch_state.revision_count,
        }
        for ch_num_str, ch_state in sorted(
            state.chapter_loop.chapter_states.items(), key=lambda kv: chapter_sort_key(kv[0])
        )
    ]

    emit_json(
        {
            "current_chapter": state.chapter_loop.current_chapter,
            "chapters": chapters,
        }
    )
    return 0


def cmd_backfill_context(args: argparse.Namespace) -> int:
    """Re-run deterministic context assembly for a chapter range.

    These are deterministic Python functions and can be re-executed safely to
    close coverage gaps for already-generated chapters. Uses the real
    assemble_context(project_dir, plan_path) / write_context_file signatures
    (spec §3.1 backfill; curated layer removed by spec #67).
    """
    project_path = Path(args.project_dir)

    chapters = args.chapters
    if "-" in chapters:
        start, end = chapters.split("-")
        chapter_range = range(int(start), int(end) + 1)
    else:
        ch = int(chapters)
        chapter_range = range(ch, ch + 1)

    from shenbi.pipeline.filelock_utils import WriteLock

    # spec #37 T605: backfill previously ran entirely outside L1 — concurrent
    # pipeline commands could interleave with per-file context rewrites.
    with WriteLock(project_path):
        return _backfill_range(project_path, chapter_range)


def _backfill_range(project_path: Path, chapter_range: range) -> int:
    from shenbi.pipeline.context_assemble import assemble_context, write_context_file

    for ch in chapter_range:
        try:
            plan_path = f"plans/chapter-{ch}-plan.md"
            pkg = assemble_context(project_path, plan_path)
            write_context_file(project_path, ch, pkg)  # safe_write inside
            echo(f"  Backfilled context for chapter {ch}")
        except Exception as e:
            echo(f"  FAILED chapter {ch}: {e}", err=True)

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; parses ``argv`` (defaults to ``sys.argv[1:]``)."""
    configure_logging()
    parser = argparse.ArgumentParser(prog="pipeline", description="Novel pipeline orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize novel project from seed file")
    p_init.add_argument("seed_file", type=str, help="Path to seed file")
    p_init.add_argument("--project-dir", type=str, default=None)
    p_init.add_argument(
        "--target-chapters",
        type=int,
        default=None,
        help="Authoritative total chapter count (overrides seed-declared 目标章节数; volume-outlining derives volume structure from it instead of target_word_count)",
    )
    p_init.add_argument(
        "--auto",
        action="store_true",
        help="Reduce checkpoints for automated/Codex-driven runs (disables per-chapter review, chapter-memo review, and state-settle review)",
    )
    p_init.set_defaults(func=cmd_init)

    p_next = sub.add_parser("next", help="Execute to next checkpoint")
    p_next.add_argument("project_dir", type=str)
    p_next.set_defaults(func=cmd_next)

    p_status = sub.add_parser("status", help="Query pipeline state")
    p_status.add_argument("project_dir", type=str)
    p_status.set_defaults(func=cmd_status)

    p_review = sub.add_parser("review", help="Submit checkpoint review")
    p_review.add_argument("project_dir", type=str)
    p_review.add_argument("decision", choices=["approve", "reject", "modify"])
    p_review.add_argument("--feedback", type=str, default=None)
    p_review.add_argument(
        "--redo-steps",
        type=str,
        default=None,
        help=(
            "genesis-complete reject only: comma list of genesis step numbers "
            "to re-dispatch (scoped redo, probe8). Steps not listed stay done "
            "and are skipped on resume."
        ),
    )
    p_review.set_defaults(func=cmd_review)

    p_resume = sub.add_parser("resume", help="Resume after checkpoint review")
    p_resume.add_argument("project_dir", type=str)
    p_resume.set_defaults(func=cmd_resume)

    p_chapters = sub.add_parser("chapters", help="Show chapter progress")
    p_chapters.add_argument("project_dir", type=str)
    p_chapters.set_defaults(func=cmd_chapters)

    p_backfill = sub.add_parser(
        "backfill-context", help="Re-run context assembly for a chapter range"
    )
    p_backfill.add_argument(
        "--chapters", type=str, required=True, help="Chapter range, e.g. '13-54'"
    )
    p_backfill.add_argument("--project-dir", type=str, default=".", help="Project directory")
    p_backfill.set_defaults(func=cmd_backfill_context)

    args = parser.parse_args(argv)
    # argparse stores set_defaults(func=...) as Any; annotate so the dispatched
    # cmd_* return type (int) flows into main's declared return type for mypy.
    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
