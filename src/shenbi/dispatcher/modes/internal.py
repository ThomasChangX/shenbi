"""Internal development fallback mode."""

from shenbi.logging import get_logger

log = get_logger(__name__)


def dispatch_internal(skill, test_type, round_dir, prompt, agent_id):
    """Development fallback: prints dispatcher instructions for manual completion."""
    scores_file = round_dir / "t1-reports" / f"{skill}-{test_type}-scores-subagent.json"
    prompt_file = round_dir / "skill-traces" / f"{skill}-{test_type}-prompt.md"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(prompt)

    log.info("internal_mode_prompt_saved", path=str(prompt_file))
    print("=== Internal Mode: Dispatcher completes scoring manually ===")
    print(f"Prompt saved: {prompt_file}")
    print(f"Scores file target: {scores_file}")
    print(f"Agent ID: {agent_id}")
    return 0
