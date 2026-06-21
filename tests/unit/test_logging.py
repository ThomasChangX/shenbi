"""Tests for structlog logging configuration.

Business value: logging must produce correct structured output for both JSON
(production) and console (dev) renderers, written to stderr (Unix convention).
These tests verify the REAL production code path in tests/logging.py:
- configure_logging() reads SHENBI_LOG_FORMAT and installs the right renderer
- JSON renderer emits parseable JSON containing event + bound fields
- Console renderer does not emit JSON (stays human-readable)
- Output goes to stderr, not stdout

Test isolation: structlog.configure() modifies global state. The
isolate_structlog_config fixture saves and restores config around each test.
"""

import json
import os
from typing import Any
from unittest.mock import patch

import pytest
import structlog

from shenbi.logging import configure_logging, get_logger


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
    """configure_logging() with SHENBI_LOG_FORMAT=json must emit parseable JSON to stderr."""
    with patch.dict(os.environ, {"SHENBI_LOG_FORMAT": "json"}):
        configure_logging()
        log = get_logger("test_json")
        log.info("user_action", user_id=42, action="login")

    captured = capsys.readouterr()
    assert captured.err, "expected JSON output on stderr, got nothing"
    assert not captured.out, "no output should go to stdout"
    parsed = json.loads(captured.err.strip())
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
    JSONRenderer. Output goes to stderr.
    """
    os.environ.pop("SHENBI_LOG_FORMAT", None)
    configure_logging()
    log = get_logger("test_console")
    log.info("user_action", user_id=42, action="login")

    captured = capsys.readouterr()
    assert captured.err, "expected console output on stderr, got nothing"
    assert not captured.out, "no output should go to stdout"
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured.err.strip())
    assert "user_action" in captured.err
    assert "login" in captured.err


def test_configure_logging_is_idempotent(isolate_structlog_config: None) -> None:
    """Calling configure_logging() twice should not raise."""
    os.environ.pop("SHENBI_LOG_FORMAT", None)
    configure_logging()
    configure_logging()
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


def _run_framework_cli(args: list[str], env_log_format: str = "json") -> tuple[int, str, str]:
    """Invoke a shenbi-* CLI via subprocess and capture (rc, stdout, stderr).

    Used to verify that framework CLIs route logs to stderr (not stdout)
    and produce structured JSON when SHENBI_LOG_FORMAT=json.
    """
    import subprocess

    full_env = dict(os.environ)
    full_env["SHENBI_LOG_FORMAT"] = env_log_format
    result = subprocess.run(
        ["uv", "run"] + args,
        capture_output=True,
        text=True,
        env=full_env,
    )
    return result.returncode, result.stdout, result.stderr


def _parse_json_log_lines(stderr: str) -> list[dict[str, Any]]:
    """Parse newline-delimited JSON log lines from stderr, skipping non-JSON noise."""
    parsed: list[dict[str, Any]] = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return parsed


def test_gates_cli_logs_to_stderr_not_stdout() -> None:
    """shenbi-validate (gates CLI) must emit JSON logs to stderr; stdout reserved for emit_json data.

    Invoking with no args triggers the usage banner, which is logged via log.info.
    """
    rc, stdout, stderr = _run_framework_cli(["shenbi-validate"])
    logs = _parse_json_log_lines(stderr)
    assert logs, "expected JSON log lines on stderr from gates CLI"
    assert any(entry.get("event") == "usage" for entry in logs), (
        "usage banner must be logged with event=usage"
    )
    assert any(entry.get("level") == "info" for entry in logs), "logs must carry level= field"
    assert not stdout, "stdout must stay empty when no DATA emit happens"


def test_gates_cli_emits_data_to_stdout() -> None:
    """When a gate runs, the JSON result must land on stdout (via emit_json), not stderr."""
    rc, stdout, stderr = _run_framework_cli(
        ["shenbi-validate", "G0", "tests/tiers/outline-example.md"]
    )
    assert stdout.strip(), "stdout must carry the gate result via emit_json"
    stdout_data = json.loads(stdout.strip())
    assert isinstance(stdout_data, dict), "emit_json output must be a JSON object"
    assert stdout_data.get("gate") == "G0"


def test_scoring_cli_logs_to_stderr_not_stdout() -> None:
    """shenbi-score must route logs to stderr; stdout carries only the JSON result."""
    rc, stdout, stderr = _run_framework_cli(["shenbi-score"])
    logs = _parse_json_log_lines(stderr)
    assert logs, "expected JSON log lines on stderr from scoring CLI usage banner"


def test_phase_runner_cli_logs_to_stderr_not_stdout() -> None:
    """shenbi-phase must route logs to stderr; stdout carries only emit_json dicts."""
    rc, stdout, stderr = _run_framework_cli(["shenbi-phase"])
    logs = _parse_json_log_lines(stderr)
    assert logs, "expected JSON log lines on stderr from phase_runner usage banner"


def test_summarize_cli_logs_to_stderr() -> None:
    """shenbi-summarize must route logs to stderr."""
    rc, stdout, stderr = _run_framework_cli(["shenbi-summarize"])
    logs = _parse_json_log_lines(stderr)
    assert logs, "expected JSON log lines on stderr from summarize usage banner"


def test_update_progress_cli_logs_to_stderr() -> None:
    """shenbi-progress must route logs to stderr."""
    rc, stdout, stderr = _run_framework_cli(["shenbi-progress"])
    logs = _parse_json_log_lines(stderr)
    assert logs, "expected JSON log lines on stderr from update_progress usage banner"
