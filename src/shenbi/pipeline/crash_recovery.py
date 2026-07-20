"""Crash recovery: signal handlers, emergency snapshots, graceful shutdown.

Handles SIGTERM, SIGINT, and atexit to preserve pipeline state and create
emergency snapshots before exit. The chapter loop checks is_shutdown_requested()
at step boundaries to avoid interrupting an active LLM call.
"""

from __future__ import annotations

import atexit
import signal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from shenbi.pipeline.state import PipelineState

logger = structlog.get_logger(__name__)

# Module-level state for signal handlers
_shutdown_requested = False
_emergency_flag = False
_emergency_state: dict[str, Any] = {}


def reset_emergency_state() -> None:
    """Reset all module-level emergency state to defaults.

    Tests that interact with signal handlers or shutdown flags MUST call
    this (usually via an autouse fixture) to prevent cross-test contamination
    under xdist, where workers share module-level globals across test modules.
    """
    global _shutdown_requested, _emergency_flag  # noqa: PLW0603
    _shutdown_requested = False
    _emergency_flag = False
    _emergency_state.clear()
    # Restore default signal disposition so a second SIGTERM kills immediately,
    # and remove any atexit hooks registered by earlier tests.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def is_shutdown_requested() -> bool:
    """Check if emergency shutdown has been requested.

    Called by chapter loop at step boundaries.
    """
    return _shutdown_requested


def register_emergency_handlers(
    project_dir: Path,
    state: PipelineState,
) -> None:
    """Register signal handlers and atexit hook for crash recovery.

    Must be called at pipeline startup, before the chapter loop begins.
    """
    _emergency_state["project_dir"] = project_dir
    _emergency_state["pipeline_state"] = state

    signal.signal(signal.SIGTERM, _handle_emergency_signal)
    signal.signal(signal.SIGINT, _handle_emergency_signal)
    atexit.register(_emergency_cleanup)


def _handle_emergency_signal(signum: int, frame: object) -> None:
    """Signal handler: ONLY sets atomic flags. No I/O, no locks."""
    global _emergency_flag, _shutdown_requested  # noqa: PLW0603
    _emergency_flag = True
    _shutdown_requested = True
    # Restore default disposition so a second signal terminates immediately
    signal.signal(signum, signal.SIG_DFL)


def _check_emergency_flag(project_dir: Path) -> None:  # pyright: ignore[reportUnusedFunction]
    """Called at step boundaries in main loop. Performs cleanup if flag set."""
    global _emergency_flag  # noqa: PLW0603
    if _emergency_flag:
        _emergency_flag = False
        try:
            _emergency_cleanup(project_dir)
        except Exception:
            pass  # Best-effort cleanup


def _emergency_cleanup(
    project_dir: Path | None = None,
    state: PipelineState | None = None,
) -> None:
    """Best-effort emergency cleanup: save state, create snapshot, clear staging.

    Called by both _check_emergency_flag and atexit (for normal exits with
    unsaved data). All operations wrapped in try/except -- failure must not
    prevent process exit.
    """
    if project_dir is None:
        project_dir = _emergency_state.get("project_dir")
    if state is None:
        state = _emergency_state.get("pipeline_state")

    if not project_dir or not state:
        return

    logger.info("emergency_cleanup_started")

    # 1. Mark current step
    try:
        if hasattr(state, "chapter_loop") and state.chapter_loop:
            cl = state.chapter_loop
            current_skill = getattr(cl, "current_step", "") or "unknown"
            cl.current_step = f"EMERGENCY_SHUTDOWN_AT_{current_skill}"
    except Exception:
        pass

    # 2. Save pipeline state
    try:
        from shenbi.pipeline.machine import save_state

        save_state(project_dir, state)
        logger.info("pipeline_state_saved")
    except Exception as e:
        logger.error("pipeline_state_save_failed", error=str(e))

    # 3. Create emergency snapshot
    try:
        chapter = (
            getattr(state.chapter_loop, "current_chapter", 0)
            if hasattr(state, "chapter_loop")
            else 0
        )
        _snapshot_chapter_files(project_dir, chapter, label="emergency")
        logger.info("emergency_snapshot_created")
    except Exception as e:
        logger.error("emergency_snapshot_failed", error=str(e))

    # 4. Clear staging
    try:
        from shenbi.pipeline.checkpoint import clear_staging

        clear_staging(project_dir)
        logger.info("staging_cleared")
    except Exception:
        pass


def _snapshot_chapter_files(
    project_dir: Path,
    chapter: int,
    label: str = "emergency",
) -> None:
    """Create a snapshot of current chapter files.

    Copies chapter-N.md to chapter-N-{label}.md for recovery.
    """
    from shenbi.safe_write import safe_write

    if chapter <= 0:
        return

    chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not chapter_path.exists():
        return

    snapshot_dir = project_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    snap_path = snapshot_dir / f"chapter-{chapter}-{label}.md"
    safe_write(snap_path, chapter_path.read_bytes())
