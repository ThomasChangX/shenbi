"""Atexit-safe logging guard for _emergency_cleanup (crash_recovery).

The emergency cleanup runs in atexit context where pytest has already
closed its captured streams — a closed-stream logger call used to escape
the callback (first log line sat before any try block) and skip the entire
state-surgery sequence: save, emergency snapshot, staging clear. These
tests pin that a fully poisoned logger can no longer abort the cleanup.
"""

from pathlib import Path

import pytest

from shenbi.pipeline import crash_recovery
from shenbi.pipeline.state import PipelineState


class _PoisonLogger:
    """Logger stub whose every call raises like a closed stream does."""

    def __getattr__(self, name: str) -> object:
        def _raise(*args: object, **kwargs: object) -> None:
            raise ValueError("I/O operation on closed file")

        return _raise


class _RecordingLogger:
    """Logger stub capturing events to prove the guard preserves logging."""

    def __init__(self) -> None:
        self.events: list[str] = []

    def info(self, event: str, **kw: object) -> None:
        self.events.append(event)

    def error(self, event: str, **kw: object) -> None:
        self.events.append(event)

    def warning(self, event: str, **kw: object) -> None:
        self.events.append(event)


@pytest.fixture(autouse=True)
def _reset_cleanup_latch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate the one-shot latch and module state per test."""
    monkeypatch.setattr(crash_recovery, "_cleanup_done", False)
    monkeypatch.setattr(crash_recovery, "_emergency_state", {})


def _make_state(tmp_path: Path, current_chapter: int) -> PipelineState:
    """Minimal real state — the cleanup duck-types into chapter_loop fields."""
    state = PipelineState(project_dir=str(tmp_path))
    state.chapter_loop.current_step = "chapter-drafting"
    state.chapter_loop.current_chapter = current_chapter
    return state


def test_poisoned_logger_does_not_abort_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A closed-stream logger must not skip the state-surgery steps."""
    monkeypatch.setattr(crash_recovery, "logger", _PoisonLogger())
    state = _make_state(tmp_path, current_chapter=3)

    crash_recovery._emergency_cleanup(tmp_path, state)  # must not raise

    assert state.chapter_loop.current_step == "EMERGENCY_SHUTDOWN_AT_chapter-drafting", (
        "log failure escaped the callback and skipped the surgery steps"
    )


def test_guard_preserves_normal_logging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Healthy logger still receives the cleanup events via the guard."""
    recorder = _RecordingLogger()
    monkeypatch.setattr(crash_recovery, "logger", recorder)
    state = _make_state(tmp_path, current_chapter=0)

    crash_recovery._emergency_cleanup(tmp_path, state)

    assert "emergency_cleanup_started" in recorder.events
