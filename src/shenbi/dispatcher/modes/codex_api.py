"""Codex API dispatch mode (currently unimplemented)."""

from __future__ import annotations
from typing import Any, NoReturn

from shenbi.exceptions import DispatcherError
from shenbi.logging import get_logger

log = get_logger(__name__)


def dispatch_codex_api(*args: Any, **kwargs: Any) -> NoReturn:
    """Placeholder for codex API mode."""
    raise DispatcherError("codex-api mode not implemented. Use codex CLI or internal mode.")
