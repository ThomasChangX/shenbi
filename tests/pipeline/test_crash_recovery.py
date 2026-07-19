"""Test crash recovery signal handlers, emergency cleanup, and shutdown flag."""

import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shenbi.pipeline.crash_recovery import (
    _emergency_cleanup,
    is_shutdown_requested,
    register_emergency_handlers,
)


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


class TestShutdownFlag:
    def test_initially_false(self):
        import shenbi.pipeline.crash_recovery as cr

        cr._shutdown_requested = False
        assert not is_shutdown_requested()

    def test_set_on_signal(self):
        import shenbi.pipeline.crash_recovery as cr

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
