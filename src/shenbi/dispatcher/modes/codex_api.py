"""DEPRECATED: codex-api dispatch mode — superseded by unified API executor.

This mode was never reachable: detect_mode() only returns 'codex' or
'internal', and the executor.py branch that referenced it was removed (P0.4).
API dispatch is handled by pipeline/dispatch_helper._dispatch_via_api.

Safe to delete entirely in the next minor release.
"""

from __future__ import annotations

from typing import Any, NoReturn

from shenbi.exceptions import DispatcherError
from shenbi.logging import get_logger

log = get_logger(__name__)


def dispatch_codex_api(*args: Any, **kwargs: Any) -> NoReturn:
    """Placeholder for codex API mode."""
    raise DispatcherError("codex-api mode not implemented. Use codex CLI or internal mode.")
