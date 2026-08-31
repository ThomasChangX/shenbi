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

from shenbi.cli_utils import emit_json
from shenbi.logging import configure_logging, get_logger
from shenbi.pipeline.filelock_utils import ReadLock, WriteLock
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
from shenbi.status import CommandStatus


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
    ],
}


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


def _execute_pending_re_dispatches(state: PipelineState, project_dir: Path) -> bool:
    """Execute all pending re-dispatches from state.

    Returns True if any re-dispatch was executed (caller may want to re-persist).
    """
    if not state.pending_re_dispatches:
        return False

    from shenbi.pipeline.dispatch_helper import dispatch_skill

    remaining: list[dict[str, Any]] = []
    for entry in state.pending_re_dispatches:
        skill = entry.get("skill", "")
        ch = entry.get("chapter")
        # Skip entries for checkpoint types no longer in DERIVED_TRUTH_MAP
        # (stale state from a previous pipeline version).
        prompt_suffix_lookup = DERIVED_TRUTH_MAP.get(entry.get("checkpoint_type", ""), [])
        if not prompt_suffix_lookup:
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
        prompt = prompt_suffix
        if ch:
            prompt = f"[Chapter {ch}] {prompt_suffix}"
        fb = entry.get("feedback")
        if fb:  # conditional: MODIFY-queued entries have no feedback (never render None)
            prompt += f"\n\nHuman review feedback (incorporate these changes): {fb}"

        result = dispatch_skill(skill, project_dir, prompt)
        if result.success:
            log.info("re_dispatch_ok", skill=skill)
        else:
            log.warning("re_dispatch_failed", skill=skill, stderr=result.stderr[:200])
            remaining.append(entry)

    state.pending_re_dispatches = remaining
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


def _commit_staging_for_checkpoint(project_dir: Path, cp: CheckpointData) -> None:
    """Commit staging files for checkpoint-gated skills (spec section 2.7).

    Only CHAPTER_MEMO and STATE_SETTLE checkpoints have staging files.
    Each target is committed individually so a missing file for one type
    does not block the other. The staging directory is cleared afterwards.
    """
    from shenbi.pipeline.checkpoint import commit_staging
    from shenbi.pipeline.chapter_loop import staged_decisions_targets

    if cp.type == CheckpointType.CHAPTER_MEMO:
        chapter = cp.chapter or 1
        targets = [f"plans/chapter-{chapter}-plan.md"]
        # audit-T5 C1: contract-declared sidecar joins the same commit batch,
        # otherwise clear_staging below silently destroys it.
        targets += staged_decisions_targets(project_dir, "shenbi-chapter-planning", chapter)
    elif cp.type == CheckpointType.STATE_SETTLE:
        # I3: glob all staged truth files rather than hardcoding one.
        from shenbi.pipeline.checkpoint import STAGING_DIR

        staging_truth = project_dir / STAGING_DIR / "truth"
        if staging_truth.is_dir():
            targets = [f"truth/{p.name}" for p in sorted(staging_truth.glob("*.md"))]
        else:
            targets = []
        targets += staged_decisions_targets(project_dir, "shenbi-state-settling", cp.chapter)
    else:
        return

    for target in targets:
        try:
            commit_staging(project_dir, [target])
        except FileNotFoundError:
            # Expected: file may have been cleared since the checkpoint was raised.
            pass

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

    seed_data = parse_seed(args.seed_file)

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

    # Persist each genesis-context section as its own prompt fragment.
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


def _apply_reject_redo(
    state: PipelineState, cp: CheckpointData, feedback: str | None = None
) -> None:
    """REJECT = redo the step that raised the checkpoint (spec #6 F340).

    Full CheckpointType coverage; BOOK_CLOSURE keeps its existing transition.
    """
    if cp.type == CheckpointType.CHAPTER_MEMO:
        state.chapter_loop.step_index = 1
    elif cp.type == CheckpointType.STATE_SETTLE:
        state.chapter_loop.step_index = 7
    elif cp.type == CheckpointType.GENESIS_COMPLETE:
        state.genesis.current_step = max(0, state.genesis.current_step - 1)
        state.genesis.retry_counts.clear()
    elif cp.type == CheckpointType.VOLUME_BOUNDARY:
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

            # Staging handling (spec section 2.7): approve/modify commits
            # staging files to their final paths; reject clears staging.
            if decision in (ReviewDecision.APPROVE, ReviewDecision.MODIFY):
                _commit_staging_for_checkpoint(project_dir, cp)
            elif decision == ReviewDecision.REJECT:
                from shenbi.pipeline.checkpoint import clear_staging

                clear_staging(project_dir)

            if decision == ReviewDecision.REJECT:
                _apply_reject_redo(state, cp, feedback=feedback)  # acts on the cp snapshot
            clear_checkpoint(state, decision)

            # G4: On modify, queue re-dispatches for derived truth files
            # (spec section 9.2: truth-sync propagation after human edit).
            if decision == ReviewDecision.MODIFY:
                # Roll back step cursor so resume re-dispatches the skill
                if cp.type == CheckpointType.CHAPTER_MEMO:
                    state.chapter_loop.step_index = 1  # CHAPTER_STEPS[1] = chapter-planning
                elif cp.type == CheckpointType.STATE_SETTLE:
                    state.chapter_loop.step_index = 7  # CHAPTER_STEPS[7] = state-settling
                elif cp.type == CheckpointType.GENESIS_COMPLETE:
                    state.genesis.current_step = max(0, state.genesis.current_step - 1)

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
            # on the first step dispatch.
            _verify_truth_integrity(state, project_dir)

            # Auto-rebuild progress.json from trace if stale or missing (Task 12).
            from shenbi.pipeline.chapter_loop import _auto_rebuild_progress_if_stale  # pyright: ignore[reportPrivateUsage]

            _auto_rebuild_progress_if_stale(project_dir)

            if state.checkpoint_history:
                last = state.checkpoint_history[-1]
                if last.get("decision") == "approve":
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
        for ch_num_str, ch_state in sorted(state.chapter_loop.chapter_states.items())
    ]

    emit_json(
        {
            "current_chapter": state.chapter_loop.current_chapter,
            "chapters": chapters,
        }
    )
    return 0


def cmd_backfill_context(args: argparse.Namespace) -> int:
    """Re-run deterministic context assembly + curation for a chapter range.

    These are deterministic Python functions and can be re-executed safely to
    close coverage gaps for already-generated chapters. Uses the real
    assemble_context(project_dir, plan_path) / write_context_file / curate_context
    signatures (spec §3.1 backfill).
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
    from shenbi.pipeline.context_curation import curate_context
    from shenbi.safe_write import safe_write

    for ch in chapter_range:
        try:
            plan_path = f"plans/chapter-{ch}-plan.md"
            pkg = assemble_context(project_path, plan_path)
            write_context_file(project_path, ch, pkg)  # safe_write inside
            curated = curate_context(project_path, ch)
            curated_path = project_path / "context" / f"chapter-{ch}-curated.md"
            curated_path.parent.mkdir(parents=True, exist_ok=True)
            safe_write(curated_path, curated)
            print(f"  Backfilled context for chapter {ch}")
        except Exception as e:
            print(f"  FAILED chapter {ch}: {e}", file=sys.stderr)

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
