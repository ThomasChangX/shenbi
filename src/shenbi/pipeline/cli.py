"""CLI entry point for the novel pipeline.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 2.2.

Commands:
    init <seed-file> [--project-dir <dir>]
    next <project-dir>
    status <project-dir>
    review <project-dir> approve|reject|modify [--feedback <file>]
    resume <project-dir>
    chapters <project-dir>
    rollback <project-dir> --chapter <N>

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
}


def _queue_re_dispatches(state: PipelineState, cp: CheckpointData) -> None:
    """Queue re-dispatches for derived truth files after a modify decision.

    After ``modify``, skills that produce derived truth from the modified files
    must be re-dispatched so derived files reflect the human edit.
    """
    entries = DERIVED_TRUTH_MAP.get(cp.type.value, [])
    for skill, _ in entries:
        # Avoid duplicate entries for the same skill.
        already = any(d.get("skill") == skill for d in state.pending_re_dispatches)
        if not already:
            state.pending_re_dispatches.append(
                {
                    "skill": skill,
                    "checkpoint_type": cp.type.value,
                    "chapter": cp.chapter,
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

        result = dispatch_skill(skill, project_dir, prompt)
        if result.success:
            log.info("re_dispatch_ok", skill=skill)
        else:
            log.warning("re_dispatch_failed", skill=skill, stderr=result.stderr[:200])
            remaining.append(entry)

    state.pending_re_dispatches = remaining
    return True


def _read_total_chapters(project_dir: Path) -> int:
    """Read total_chapters from novel.json (0 when not yet determined)."""
    novel_path = project_dir / "novel.json"
    if not novel_path.exists():
        return 0
    try:
        data = json.loads(novel_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return 0
    total = data.get("total_chapters", 0)
    return int(total) if isinstance(total, (int, float)) else 0


def _update_total_chapters(project_dir: Path) -> int:
    """Re-read volume_map.md and update novel.json.total_chapters.

    Called after volume-boundary expansion so the chapter-loop termination
    check reflects the revised count (spec \u00a74.2 [I3], \u00a76.5). Returns the
    new total, or 0 when the volume map cannot be read.
    """
    from shenbi.pipeline.triggers import read_volume_boundaries

    boundaries = read_volume_boundaries(project_dir)
    if not boundaries:
        return 0
    new_total = max(boundaries)
    novel_path = project_dir / "novel.json"
    if not novel_path.exists():
        return 0
    try:
        data = json.loads(novel_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return 0
    data["total_chapters"] = new_total
    from shenbi.safe_write import safe_write

    safe_write(novel_path, json.dumps(data, indent=2, ensure_ascii=False))
    log.info("total_chapters_updated", total_chapters=new_total)
    return new_total


def _orchestrate_to_checkpoint(state: PipelineState, project_dir: Path) -> None:
    """Run pipeline steps until a checkpoint is reached or the pipeline completes.

    Assumes the caller already holds the WriteLock and will persist *state*.
    Dispatches to genesis / chapter-loop / closure step runners, and handles
    trigger execution + closure transition at the start of each new chapter.
    """
    from shenbi.pipeline.chapter_loop import run_chapter_step
    from shenbi.pipeline.closure import run_closure_step
    from shenbi.pipeline.genesis import run_genesis_step
    from shenbi.pipeline.transitions import (
        transition_chapter_to_closure,
        transition_closure_to_completed,
    )
    from shenbi.pipeline.triggers import check_triggers, run_triggered_skills

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

        elif phase == PipelinePhase.CHAPTER_LOOP:
            cl = state.chapter_loop
            if cl.step_index == 0 and cl.current_chapter > 1:
                total = _read_total_chapters(project_dir)
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
                # Step advanced without checkpoint: continue the loop.
            else:
                # Closure step failed. The closure runner has no internal
                # retry logic, so raise an escalation checkpoint for human
                # intervention rather than spinning on the same failing step.
                set_checkpoint(
                    state,
                    CheckpointType.ESCALATION,
                    context=f"Closure step {state.closure_step + 1} failed",
                )
                return

        else:
            return


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

    if cp.type == CheckpointType.CHAPTER_MEMO:
        chapter = cp.chapter or 1
        targets = [f"plans/chapter-{chapter}-plan.md"]
    elif cp.type == CheckpointType.STATE_SETTLE:
        # I3: glob all staged truth files rather than hardcoding one.
        from shenbi.pipeline.checkpoint import STAGING_DIR

        staging_truth = project_dir / STAGING_DIR / "truth"
        if staging_truth.is_dir():
            targets = [f"truth/{p.name}" for p in sorted(staging_truth.glob("*.md"))]
        else:
            targets = []
    else:
        return

    for target in targets:
        try:
            commit_staging(project_dir, [target])
        except FileNotFoundError:
            pass

    # Clear staging dir regardless (remove any remaining staged files).
    from shenbi.pipeline.checkpoint import clear_staging

    clear_staging(project_dir)


log = get_logger(__name__)


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new novel project from a seed file.

    Parses the seed, writes ``novel.json`` / ``genre-config.json`` /
    ``genesis-context/*.md``, and bootstraps ``pipeline-state.json`` with the
    genesis phase already in-progress. Refuses to clobber an existing project.
    """
    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd() / "novel"
    state_file = project_dir / "pipeline-state.json"

    if state_file.exists():
        emit_json({"status": CommandStatus.ERROR, "message": "pipeline-state.json already exists"})
        return 1

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
    with WriteLock(project_dir):
        save_state(project_dir, state)

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

            # Staging handling (spec section 2.7): approve/modify commits
            # staging files to their final paths; reject clears staging.
            if decision in (ReviewDecision.APPROVE, ReviewDecision.MODIFY):
                _commit_staging_for_checkpoint(project_dir, cp)
            elif decision == ReviewDecision.REJECT:
                from shenbi.pipeline.checkpoint import clear_staging

                clear_staging(project_dir)

            feedback = None
            if args.feedback:
                feedback = Path(args.feedback).read_text(encoding="utf-8")

            clear_checkpoint(state, decision)

            # G4: On modify, queue re-dispatches for derived truth files
            # (spec section 9.2: truth-sync propagation after human edit).
            if decision == ReviewDecision.MODIFY:
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

    # If chapter loop is active, verify at least the first chapter plan exists.
    if state.phase == PipelinePhase.CHAPTER_LOOP:
        ch = state.chapter_loop.current_chapter
        chapter_plan = project_dir / "plans" / f"chapter-{ch}-plan.md"
        if not chapter_plan.exists():
            # The chapter plan for the current chapter may not exist if
            # we just transitioned from genesis. Don't flag chapter 1 since
            # its plan is created during the first chapter-loop iteration.
            if ch > 1:
                missing.append(f"plans/chapter-{ch}-plan.md")

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

            # Truth-integrity check (spec \u00a73.4): verify truth files exist
            # before resuming, so missing files surface immediately rather than
            # on the first step dispatch.
            _verify_truth_integrity(state, project_dir)

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
                        dispatch_skill(
                            "shenbi-snapshot-manage",
                            project_dir,
                            f"Volume-boundary snapshot after chapter {snap_ch}.",
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


def cmd_rollback(args: argparse.Namespace) -> int:
    """Rollback to a chapter snapshot.

    Placeholder: requires snapshot integration landing in Wave 3/4. The
    ``--chapter`` argument is accepted now so the interface is stable.
    """
    project_dir = Path(args.project_dir)
    log.info("rollback_requested", project_dir=str(project_dir), chapter=args.chapter)
    emit_json(
        {
            "status": "not_implemented",
            "message": "Rollback requires snapshot integration (Wave 3/4)",
        }
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; parses ``argv`` (defaults to ``sys.argv[1:]``)."""
    configure_logging()
    parser = argparse.ArgumentParser(prog="pipeline", description="Novel pipeline orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize novel project from seed file")
    p_init.add_argument("seed_file", type=str, help="Path to seed file")
    p_init.add_argument("--project-dir", type=str, default=None)
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

    p_rollback = sub.add_parser("rollback", help="Rollback to chapter snapshot")
    p_rollback.add_argument("project_dir", type=str)
    p_rollback.add_argument("--chapter", type=int, required=True)
    p_rollback.set_defaults(func=cmd_rollback)

    args = parser.parse_args(argv)
    # argparse stores set_defaults(func=...) as Any; annotate so the dispatched
    # cmd_* return type (int) flows into main's declared return type for mypy.
    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
