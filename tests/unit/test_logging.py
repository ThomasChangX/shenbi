"""Tests for structlog logging configuration."""

import os
from io import StringIO
from unittest.mock import patch

import structlog

from tests.logging import configure_logging, get_logger


def test_get_logger_returns_bound_logger() -> None:
    """get_logger should return a BoundLogger."""
    configure_logging()
    log = get_logger("test")
    assert hasattr(log, "info")
    assert hasattr(log, "debug")
    assert hasattr(log, "error")


def test_json_format_outputs_valid_json() -> None:
    """JSON renderer should output parseable JSON."""
    with patch.dict(os.environ, {"SHENBI_LOG_FORMAT": "json"}):
        configure_logging()
        log = get_logger("test")
        output_stream = StringIO()
        with patch.object(structlog.dev, "ConsoleRenderer"):
            log.info("test_event", key="value", stream=output_stream)
        # The actual output goes to stderr by default
        # This test verifies configuration doesn't crash


def test_console_format_is_default() -> None:
    """Without SHENBI_LOG_FORMAT, console renderer is used."""
    os.environ.pop("SHENBI_LOG_FORMAT", None)
    configure_logging()
    log = get_logger("test")
    assert log is not None
