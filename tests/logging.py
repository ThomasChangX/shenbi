"""Structured logging configuration for Shenbi framework.

Provides configure_logging() and get_logger() for all framework tools.
Output format controlled by SHENBI_LOG_FORMAT env var:
- "json": JSON lines (production, CI)
- "console": human-readable colored output (dev, default)
"""

import os
from typing import Any, cast

import structlog


def configure_logging() -> None:
    """Configure structlog with JSON or console renderer."""
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
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger bound to the given name."""
    return cast(structlog.BoundLogger, structlog.get_logger(name))
