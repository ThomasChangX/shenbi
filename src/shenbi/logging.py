"""Structured logging configuration for Shenbi framework.

Provides configure_logging() and get_logger() for all framework tools.
Output format controlled by SHENBI_LOG_FORMAT env var:
- "json": JSON lines (production, CI)
- "console": human-readable colored output (dev, default)

All output goes to stderr (Unix convention: stdout is for data, stderr is
for diagnostics/logs).
"""

import os
import sys
from typing import Any, cast

import structlog


def configure_logging() -> None:
    """Configure structlog with JSON or console renderer, writing to stderr."""
    log_format = os.environ.get("SHENBI_LOG_FORMAT", "console")
    renderer: Any = (
        structlog.processors.JSONRenderer()
        if log_format == "json"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        # cache_logger_on_first_use=False: required for test environments
        # where capsys replaces sys.stderr temporarily. When True, the
        # first logger created captures sys.stderr permanently, and
        # subsequent configure_logging() calls cannot rebind it.
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger bound to the given name."""
    return cast(structlog.BoundLogger, structlog.get_logger(name))
