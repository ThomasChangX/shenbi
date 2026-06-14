"""Tests for structlog logging configuration.

Business value: logging must produce correct structured output for both JSON
(production) and console (dev) renderers. These tests verify the REAL
production code path in tests/logging.py:
- configure_logging() reads SHENBI_LOG_FORMAT and installs the right renderer
- JSON renderer emits parseable JSON containing event + bound fields
- Console renderer does not emit JSON (stays human-readable)

Test isolation: structlog.configure() modifies global state. The
isolate_structlog_config fixture saves and restores config around each test.

Output capture: structlog's default PrintLogger writes to stdout. We use
capsys to capture the actual rendered output, not a mock processor. This
catches regressions in configure_logging() itself (e.g., processor chain
changes, wrong renderer selection).
"""

import json
import os
from typing import Any
from unittest.mock import patch

import pytest
import structlog

from tests.logging import configure_logging, get_logger


@pytest.fixture()
def isolate_structlog_config() -> Any:
    """Save and restore structlog global config around each test."""
    original_config = structlog.get_config()
    original_env = dict(os.environ)
    yield
    structlog.configure(**original_config)
    os.environ.clear()
    os.environ.update(original_env)


def test_configure_logging_json_emits_parseable_json(
    isolate_structlog_config: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """configure_logging() with SHENBI_LOG_FORMAT=json must emit parseable JSON."""
    with patch.dict(os.environ, {"SHENBI_LOG_FORMAT": "json"}):
        configure_logging()
        log = get_logger("test_json")
        log.info("user_action", user_id=42, action="login")

    captured = capsys.readouterr()
    assert captured.out, "expected JSON output on stdout, got nothing"
    parsed = json.loads(captured.out.strip())
    assert parsed["event"] == "user_action"
    assert parsed["user_id"] == 42
    assert parsed["action"] == "login"
    assert parsed["level"] == "info"
    assert "timestamp" in parsed


def test_configure_logging_console_does_not_emit_json(
    isolate_structlog_config: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """configure_logging() without SHENBI_LOG_FORMAT must NOT emit JSON.

    ConsoleRenderer output is human-readable and should fail json.loads —
    this catches the regression where both renderers accidentally chain
    JSONRenderer.
    """
    os.environ.pop("SHENBI_LOG_FORMAT", None)
    configure_logging()
    log = get_logger("test_console")
    log.info("user_action", user_id=42, action="login")

    captured = capsys.readouterr()
    assert captured.out, "expected console output on stdout, got nothing"
    # ConsoleRenderer output is NOT valid JSON (it's colored human-readable text)
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured.out.strip())
    # But it should still contain the event name and key fields as substrings
    assert "user_action" in captured.out
    assert "login" in captured.out


def test_configure_logging_is_idempotent(isolate_structlog_config: None) -> None:
    """Calling configure_logging() twice should not raise."""
    os.environ.pop("SHENBI_LOG_FORMAT", None)
    configure_logging()
    configure_logging()  # should not raise
    log = get_logger("test_idempotent")
    assert log is not None


def test_get_logger_returns_logger_with_standard_methods(
    isolate_structlog_config: None,
) -> None:
    """get_logger should return an object with standard log level methods."""
    configure_logging()
    log = get_logger("test_methods")
    assert callable(log.info)
    assert callable(log.error)
    assert callable(log.debug)
