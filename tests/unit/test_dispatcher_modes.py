"""Unit tests for dispatcher fallback modes (internal + codex_api)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.dispatcher.modes.codex_api import dispatch_codex_api
from shenbi.dispatcher.modes.internal import dispatch_internal
from shenbi.exceptions import DispatcherError


@pytest.mark.unit
def test_dispatch_internal_raises_dispatcher_error(tmp_path: Path) -> None:
    """dispatch_internal hard-rejects because internal mode has no LLM backend.

    Covers dispatcher/modes/internal.py:16-19 (the raise path).
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    with pytest.raises(DispatcherError, match="internal mode has no LLM backend"):
        dispatch_internal(
            "shenbi-worldbuilding", "generative", round_dir, "complete the task", "agent-1"
        )


@pytest.mark.unit
def test_dispatch_codex_api_raises_dispatcher_error() -> None:
    """codex-api mode is unimplemented and raises DispatcherError (covers codex_api.py:15)."""
    with pytest.raises(DispatcherError):
        dispatch_codex_api()
