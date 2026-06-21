"""Unit tests for dispatcher fallback modes (internal + codex_api)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.dispatcher.modes.codex_api import dispatch_codex_api
from shenbi.dispatcher.modes.internal import dispatch_internal
from shenbi.exceptions import DispatcherError


@pytest.mark.unit
def test_dispatch_internal_writes_prompt_file_and_returns_zero(tmp_path: Path) -> None:
    """dispatch_internal saves the prompt under skill-traces/ and returns 0.

    Covers dispatcher/modes/internal.py:14-24 (the full function body).
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    rc = dispatch_internal(
        "shenbi-worldbuilding", "generative", round_dir, "complete the task", "agent-1"
    )
    assert rc == 0
    prompt_file = round_dir / "skill-traces" / "shenbi-worldbuilding-generative-prompt.md"
    assert prompt_file.exists()
    assert prompt_file.read_text(encoding="utf-8") == "complete the task"


@pytest.mark.unit
def test_dispatch_codex_api_raises_dispatcher_error() -> None:
    """codex-api mode is unimplemented and raises DispatcherError (covers codex_api.py:15)."""
    with pytest.raises(DispatcherError):
        dispatch_codex_api()
