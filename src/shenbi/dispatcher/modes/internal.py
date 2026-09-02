"""Internal development fallback mode — hard-reject: no LLM backend."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

from shenbi.exceptions import DispatcherError
from shenbi.logging import get_logger

log = get_logger(__name__)


def dispatch_internal(
    skill: str, test_type: str, round_dir: Path, prompt: str, agent_id: str
) -> NoReturn:
    """Hard-reject: internal mode has no LLM backend, cannot score.

    F219 (spec #39 T9): the old message pointed at SHENBI_LLM_API_KEY, an
    env var no dispatch route reads — the real alternatives are the codex
    CLI or the pipeline API entrypoint.
    """
    raise DispatcherError(
        "internal mode has no LLM backend, cannot score. "
        "Install the codex CLI for dispatch, or use the pipeline API "
        "entrypoint (pipeline/dispatch_helper)."
    )
