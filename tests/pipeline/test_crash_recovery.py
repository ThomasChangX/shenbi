"""Test crash recovery signal handlers, emergency cleanup, and shutdown flag."""

import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import shenbi.pipeline.crash_recovery as cr
from shenbi.pipeline.crash_recovery import (
    _check_emergency_flag,
    _emergency_cleanup,
    _handle_emergency_signal,
    _snapshot_chapter_files,
    is_shutdown_requested,
    register_emergency_handlers,
    reset_emergency_state,
)


@pytest.fixture(autouse=True)
def _reset_crash_state():
    """Prevent cross-test contamination of module-level emergency globals under xdist."""
    reset_emergency_state()


class TestSignalHandlers:
    def test_registers_sigterm_and_sigint(self):
        with patch("signal.signal") as mock_signal:
            register_emergency_handlers(Path("/tmp"), MagicMock())
            assert mock_signal.call_count >= 2
            signals_registered = [c[0][0] for c in mock_signal.call_args_list]
            assert signal.SIGTERM in signals_registered
            assert signal.SIGINT in signals_registered

    def test_registers_atexit(self):
        with patch("atexit.register") as mock_atexit:
            register_emergency_handlers(Path("/tmp"), MagicMock())
            mock_atexit.assert_called_once()

    def test_handle_emergency_signal_sets_flags(self):
        """_handle_emergency_signal must set _shutdown_requested and _emergency_flag."""
        cr._shutdown_requested = False
        cr._emergency_flag = False
        _handle_emergency_signal(signal.SIGTERM, None)
        assert cr._shutdown_requested is True
        assert cr._emergency_flag is True

    def test_handle_emergency_signal_restores_default(self):
        """_handle_emergency_signal restores SIG_DFL so second signal kills."""
        with patch("signal.signal") as mock_signal:
            _handle_emergency_signal(signal.SIGTERM, None)
            # First call sets the flags, second call (inside function) restores default
            mock_signal.assert_called_with(signal.SIGTERM, signal.SIG_DFL)

    def test_check_emergency_flag_clears_and_cleans(self, tmp_path):
        """_check_emergency_flag clears flag and calls cleanup when flag is set."""
        cr._emergency_flag = True
        cr._emergency_state["project_dir"] = tmp_path
        cr._emergency_state["pipeline_state"] = MagicMock()
        with patch("shenbi.pipeline.crash_recovery._emergency_cleanup") as mock_cleanup:
            _check_emergency_flag(tmp_path)
            mock_cleanup.assert_called_once()
        assert cr._emergency_flag is False

    def test_check_emergency_flag_noop_when_flag_false(self, tmp_path):
        """_check_emergency_flag is a no-op when _emergency_flag is False."""
        cr._emergency_flag = False
        with patch("shenbi.pipeline.crash_recovery._emergency_cleanup") as mock_cleanup:
            _check_emergency_flag(tmp_path)
            mock_cleanup.assert_not_called()

    def test_emergency_cleanup_noop_without_project_dir(self):
        """_emergency_cleanup returns early when project_dir and state are both None."""
        cr._emergency_state.clear()
        # Should not raise
        _emergency_cleanup(project_dir=None, state=None)

    def test_emergency_cleanup_noop_with_empty_state(self):
        """_emergency_cleanup returns early when state has no project_dir."""
        cr._emergency_state.clear()
        _emergency_cleanup()

    def test_emergency_cleanup_with_mock_state(self, tmp_path):
        """_emergency_cleanup saves state and creates snapshot with valid inputs."""
        state = MagicMock()
        state.chapter_loop = MagicMock()
        state.chapter_loop.current_chapter = 5
        # _emergency_cleanup uses function-local imports for save_state,
        # clear_staging — patch at the import target, not on crash_recovery.
        with (
            patch("shenbi.pipeline.machine.save_state") as mock_save,
            patch("shenbi.pipeline.crash_recovery._snapshot_chapter_files") as mock_snap,
            patch("shenbi.pipeline.checkpoint.clear_staging") as mock_clear,
        ):
            _emergency_cleanup(tmp_path, state)
            mock_save.assert_called_once()
            mock_snap.assert_called_once_with(tmp_path, 5, label="emergency")
            mock_clear.assert_called_once()

    def test_emergency_cleanup_handles_save_failure(self, tmp_path):
        """_emergency_cleanup continues on save_state failure (best-effort)."""
        state = MagicMock()
        state.chapter_loop = MagicMock()
        state.chapter_loop.current_chapter = 1
        with patch("shenbi.pipeline.machine.save_state", side_effect=RuntimeError("fail")):
            # Should not raise
            _emergency_cleanup(tmp_path, state)

    def test_snapshot_chapter_zero_returns_early(self, tmp_path):
        """_snapshot_chapter_files returns early when chapter <= 0."""
        # Should not raise or create any files
        _snapshot_chapter_files(tmp_path, chapter=0, label="test")
        assert not (tmp_path / "snapshots").exists()


class TestResetEmergencyState:
    """Tests for reset_emergency_state — used by autouse fixtures under xdist."""

    def test_resets_shutdown_flag(self):
        cr._shutdown_requested = True
        reset_emergency_state()
        assert cr._shutdown_requested is False

    def test_resets_emergency_flag(self):
        cr._emergency_flag = True
        reset_emergency_state()
        assert cr._emergency_flag is False

    def test_clears_emergency_state_dict(self):
        cr._emergency_state["key"] = "value"
        reset_emergency_state()
        assert cr._emergency_state == {}

    def test_restores_signal_handlers(self):
        with patch("signal.signal") as mock_signal:
            reset_emergency_state()
            assert mock_signal.call_count == 2
            mock_signal.assert_any_call(signal.SIGTERM, signal.SIG_DFL)
            mock_signal.assert_any_call(signal.SIGINT, signal.SIG_DFL)


class TestShutdownFlag:
    def test_initially_false(self):
        cr._shutdown_requested = False
        assert not is_shutdown_requested()

    def test_set_on_signal(self):
        cr._shutdown_requested = True
        assert is_shutdown_requested()


class TestEmergencyCleanup:
    def test_saves_pipeline_state(self, tmp_path):
        state = MagicMock()
        _emergency_cleanup(tmp_path, state)
        # Should attempt to save state
        # (save_state from shenbi.pipeline.machine is called if available)

    def test_cleanup_failure_does_not_prevent_exit(self, tmp_path):
        state = MagicMock()
        state.save.side_effect = RuntimeError("disk full")
        # Should not raise -- emergency cleanup is best-effort
        try:
            _emergency_cleanup(tmp_path, state)
        except Exception:
            pytest.fail("_emergency_cleanup should not raise on failure")
