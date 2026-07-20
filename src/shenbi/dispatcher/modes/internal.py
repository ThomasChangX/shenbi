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

    Set ``SHENBI_LLM_API_KEY`` to use API mode, or install the codex CLI
    for IDE agent dispatch.
    """
    raise DispatcherError(
        "internal mode has no LLM backend, cannot score. Set SHENBI_LLM_API_KEY to use API mode."
    )
