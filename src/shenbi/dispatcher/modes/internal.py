"""Internal development fallback mode."""

from __future__ import annotations

from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)


def dispatch_internal(
    skill: str, test_type: str, round_dir: Path, prompt: str, agent_id: str
) -> int:
    """Development fallback: prints dispatcher instructions for manual completion."""
    scores_file = round_dir / "t1-reports" / f"{skill}-{test_type}-scores-subagent.json"
    prompt_file = round_dir / "skill-traces" / f"{skill}-{test_type}-prompt.md"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(prompt)

    log.info("internal_mode_prompt_saved", path=str(prompt_file))
    log.info(
        "internal_mode_banner",
        message="=== Internal Mode: Dispatcher completes scoring manually ===",
    )
    log.info("prompt_saved", path=str(prompt_file))
    log.info("scores_file_target", path=str(scores_file))
    log.info("agent_id", agent_id=agent_id)
    return 0
