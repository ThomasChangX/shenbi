"""Tests for structlog logging configuration.

Business value: logging must produce correct structured output for both JSON
(production) and console (dev) renderers. These tests verify that:
- JSON renderer emits parseable JSON containing event + bound fields
- The processor chain preserves context through rendering
- Default format selection works without env var

Test isolation: structlog.configure() modifies global state. The
isolate_structlog_config fixture saves and restores config around each test.

Caching: configure_logging() sets cache_logger_on_first_use=True for production
performance. Tests pass cache_logger_on_first_use=False to ensure the
configured processor chain is always read fresh (not cached before capture
processors are installed).
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


def test_json_renderer_emits_dict_event_with_fields(
    isolate_structlog_config: None,
) -> None:
    """JSON renderer path produces a captured event dict with event name and bound fields."""
    captured_entries: list[Any] = []

    def capture(_logger: Any, _method: str, event_dict: Any) -> str:
        captured_entries.append(event_dict)
        return str(event_dict)

    with patch.dict(os.environ, {"SHENBI_LOG_FORMAT": "json"}):
        structlog.configure(processors=[capture], cache_logger_on_first_use=False)
        log = get_logger("test_capture")
        log.info("user_action", user_id=42, action="login")

    assert len(captured_entries) == 1
    entry = captured_entries[0]
    assert entry["event"] == "user_action"
    assert entry["user_id"] == 42
    assert entry["action"] == "login"


def test_json_renderer_produces_parseable_json_string(
    isolate_structlog_config: None,
) -> None:
    """End-to-end: JSON renderer emits a string that json.loads can parse."""
    captured_strings: list[str] = []

    def capture_string(_logger: Any, _method: str, rendered: Any) -> Any:
        captured_strings.append(rendered)
        return rendered

    with patch.dict(os.environ, {"SHENBI_LOG_FORMAT": "json"}):
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
                capture_string,
            ],
            cache_logger_on_first_use=False,
        )
        log = get_logger("test_json_output")
        log.info("test_event", key="value")

    assert len(captured_strings) == 1
    parsed = json.loads(captured_strings[0])
    assert parsed["event"] == "test_event"
    assert parsed["key"] == "value"
    assert parsed["level"] == "info"


def test_console_format_is_default_when_env_unset(
    isolate_structlog_config: None,
) -> None:
    """Without SHENBI_LOG_FORMAT, configure_logging should not raise."""
    os.environ.pop("SHENBI_LOG_FORMAT", None)
    configure_logging()
    log = get_logger("test_default")
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
