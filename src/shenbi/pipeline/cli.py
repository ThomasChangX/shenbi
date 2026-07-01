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

from shenbi.cli_utils import emit_json
from shenbi.logging import configure_logging, get_logger
from shenbi.pipeline.filelock_utils import ReadLock, WriteLock
from shenbi.pipeline.machine import (
    clear_checkpoint,
    is_at_checkpoint,
    load_state,
    save_state,
)
from shenbi.pipeline.seed_parser import parse_seed
from shenbi.pipeline.state import (
    CheckpointType,
    GenesisState,
    PipelineState,
    ReviewDecision,
)
from shenbi.safe_write import safe_write
from shenbi.status import CommandStatus

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
    except FileNotFoundError:
        emit_json({"status": CommandStatus.ERROR, "message": "project not found"})
        return 1

    if not is_at_checkpoint(state):
        emit_json({"status": CommandStatus.ERROR, "message": "no pending checkpoint to review"})
        return 1

    decision = ReviewDecision(args.decision)
    feedback = None
    if args.feedback:
        feedback = Path(args.feedback).read_text(encoding="utf-8")

    clear_checkpoint(state, decision)

    if feedback:
        state.checkpoint_history[-1]["feedback"] = feedback

    save_state(project_dir, state)

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
    """Execute toward the next checkpoint.

    Placeholder: orchestrators (Wave 3) implement the actual generation. The
    state machine and checkpoint primitives it depends on are already in place.
    """
    project_dir = Path(args.project_dir)

    try:
        with WriteLock(project_dir):
            state = load_state(project_dir)
    except FileNotFoundError:
        emit_json({"status": CommandStatus.ERROR, "message": "project not found"})
        return 1

    if is_at_checkpoint(state):
        emit_json(
            {
                "status": CommandStatus.BLOCKED,
                "message": "pending checkpoint requires review",
                "checkpoint": state.pending_checkpoint.type.value,
            }
        )
        return 1

    # Wave 3 replaces this with real orchestration. "not_implemented" is a
    # transient placeholder status, deliberately not added to the canonical
    # CommandStatus vocabulary (which it will leave once Wave 3 lands).
    emit_json(
        {
            "status": "not_implemented",
            "message": "Orchestrators not yet implemented (Wave 3). State machine is ready.",
            "phase": state.phase.value,
        }
    )
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume after a checkpoint review (delegates to next until Wave 3)."""
    return cmd_next(args)


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
