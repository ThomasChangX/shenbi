"""Genesis orchestrator: 17-step serial sequence with per-step G4 (spec \u00a75.1).

Each step dispatches a skill, runs G4 (skill-specific structure), and on
success advances the genesis cursor. Step 17 (foundation-review) additionally
runs G3 (scoring independence) because it is a ``requires_independent_agent``
skill. After every truth-writing step the Route A entity index
(``truth-index.json``) is rebuilt and Route B embeddings are refreshed when the
model is available (\u00a77.3 degradation path).

dispatch/gate failures retry per spec \u00a711: up to ``max_revision_retries``
attempts, then an escalation checkpoint is raised. The retry/escalation logic
is inlined here because ``pipeline.retry`` (Wave 3c) does not exist yet; once it
does, this module can delegate to it.

The orchestrator is stateless itself: it mutates the passed-in
:class:`PipelineState` in memory and the caller persists it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import (
    dispatch_skill,
    requires_independent,
    run_gate_g3,
    run_gate_g4,
)
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.state import (
    CheckpointType,
    GenesisState,
    PipelineState,
)
from shenbi.pipeline.truth_embed import embed_and_store, is_embed_available
from shenbi.safe_write import safe_write
from shenbi.status import GateStatus

log = get_logger(__name__)


@dataclass
class GenesisStep:
    """One step in the genesis sequence (spec \u00a75.1)."""

    step_num: int
    skill: str
    mode: str = ""
    output_path: str = ""
    optional: bool = False


GENESIS_STEPS: list[GenesisStep] = [
    GenesisStep(1, "shenbi-worldbuilding", output_path="world/story_bible.md"),
    GenesisStep(2, "shenbi-genre-config", output_path="genre-config.json"),
    GenesisStep(
        3, "shenbi-character-design", mode="genesis", output_path="characters/protagonist.md"
    ),
    GenesisStep(4, "shenbi-story-architecture", output_path="outline/story_frame.md"),
    GenesisStep(5, "shenbi-faction-builder", output_path="world/factions.md"),
    GenesisStep(6, "shenbi-volume-outlining", output_path="outline/volume_map.md"),
    GenesisStep(7, "shenbi-pacing-design", output_path="outline/rhythm_principles.md"),
    GenesisStep(8, "shenbi-plot-thread-weaver", output_path="outline/thread_map.md"),
    GenesisStep(
        9, "shenbi-foreshadowing-plant", mode="genesis", output_path="truth/pending_hooks.md"
    ),
    GenesisStep(10, "shenbi-power-system", output_path="world/power_system.md"),
    GenesisStep(11, "shenbi-location-builder", output_path="world/locations.md"),
    GenesisStep(12, "shenbi-relationship-map", output_path="characters/relationships.md"),
    GenesisStep(13, "shenbi-book-spine-init", output_path="truth/book_spine.md"),
    GenesisStep(14, "shenbi-intent-management", output_path="truth/author_intent.md"),
    GenesisStep(15, "shenbi-style-learning", output_path="style/style_profile.md"),
    GenesisStep(
        16, "shenbi-anchor-curate", output_path="benchmarks/anchors/AC-001.md", optional=True
    ),
    GenesisStep(17, "shenbi-foundation-review", output_path="foundation/review_report.md"),
]

# Skills whose writes include truth/outline/characters/world/style files, i.e.
# content the Route A entity index scans (spec \u00a73.2 step 4). genre-config
# and foundation-review are intentionally excluded: they write config/review
# files that carry no indexed entities.
_INDEX_UPDATE_SKILLS: frozenset[str] = frozenset(
    {
        "shenbi-worldbuilding",
        "shenbi-character-design",
        "shenbi-faction-builder",
        "shenbi-story-architecture",
        "shenbi-volume-outlining",
        "shenbi-pacing-design",
        "shenbi-plot-thread-weaver",
        "shenbi-foreshadowing-plant",
        "shenbi-power-system",
        "shenbi-location-builder",
        "shenbi-relationship-map",
        "shenbi-book-spine-init",
        "shenbi-intent-management",
        "shenbi-style-learning",
        "shenbi-anchor-curate",
    }
)


def _gate_passed(result: dict[str, object]) -> bool:
    """True iff a gate result dict reports PASS (handles str and GateStatus)."""
    return str(result.get("status", "")) == GateStatus.PASS


def _update_indexes(project_dir: Path, skill: str) -> None:
    """Rebuild Route A index (truth-index.json) after a truth-writing step.

    No-op for skills not in ``_INDEX_UPDATE_SKILLS``. Missing source directories
    are tolerated by :func:`build_index`, so the Route A write itself never
    raises for an early-stage project. Route B embedding refresh is a separate
    best-effort step: its failure must not mask Route A success (\u00a77.3).
    """
    if skill not in _INDEX_UPDATE_SKILLS:
        return
    index = None
    try:
        from shenbi.pipeline.truth_index import build_index

        index = build_index(project_dir)
        safe_write(project_dir / "truth-index.json", index.to_json())
        log.info("truth_index_updated", skill=skill)
    except Exception as e:
        log.warning("truth_index_update_failed", skill=skill, error=str(e))
        return
    try:
        _update_route_b(project_dir, index, skill)
    except Exception as e:
        log.warning("route_b_update_failed", skill=skill, error=str(e))


def _update_route_b(
    project_dir: Path,
    index: object,
    skill: str,
) -> None:
    """Refresh Route B embeddings from the freshly built Route A index.

    Implements the \u00a77.3 degradation path: when the embedding model is
    unavailable (``sentence_transformers`` not installed) this is a no-op and
    ``route_b_degraded`` is logged so the pipeline can mark it. When available,
    hook and rule entries that carry text content are embedded (\u00a77.4 chunk
    types ``hook`` / ``rule``).
    """
    if not is_embed_available():
        log.info("route_b_degraded", skill=skill)
        return

    from shenbi.pipeline.truth_embed import EmbeddingStore

    hooks = getattr(index, "hooks", {})
    rules = getattr(index, "rules", {})
    store = EmbeddingStore(project_dir / "embeddings.db")
    embedded = 0
    for hook_id, entry in hooks.items():
        text = str(entry.extra.get("content_keywords", ""))
        if text:
            if embed_and_store(
                store, text, f"hook-{hook_id}", entry.file, "hook", entity_refs=hook_id
            ):
                embedded += 1
    for rule_id, entry in rules.items():
        text = str(entry.extra.get("content", ""))
        if text:
            if embed_and_store(
                store, text, f"rule-{rule_id}", entry.file, "rule", entity_refs=rule_id
            ):
                embedded += 1
    if embedded:
        log.info("route_b_embeds_updated", skill=skill, embedded=embedded)


def _advance(state: PipelineState, step_idx: int) -> bool:
    """Bump the genesis cursor and set the completion checkpoint if done.

    Shared by the success path and the optional-skip path. Returns ``True``
    when genesis has finished (all steps consumed), ``False`` when at least
    one step remains.
    """
    state.genesis.current_step = step_idx + 1
    if state.genesis.current_step >= len(GENESIS_STEPS):
        state.genesis.state = GenesisState.CHECKPOINT_PENDING
        set_checkpoint(
            state,
            CheckpointType.GENESIS_COMPLETE,
            artifact="foundation/review_report.md",
            context="Review all genesis outputs before entering chapter loop.",
        )
        return True
    return False


def _step_index(step: GenesisStep) -> int:
    """Return the 0-based cursor index for *step*."""
    return step.step_num - 1


def _handle_failure(
    state: PipelineState,
    step: GenesisStep,
    failure: str,
) -> bool:
    """Record a dispatch/gate failure for a genesis step.

    Optional steps skip forward on the first failure: the cursor advances
    past them with no retry or escalation (the ``optional`` flag marks the
    step as non-blocking). Non-optional steps retry per spec \u00a711 up to
    ``max_revision_retries`` (default 3), then raise an escalation.

    Returns ``False`` when the step should be retried on the next ``cmd_next``
    call (cursor unchanged) or when it was skipped (cursor advanced); ``True``
    once an escalation or genesis-complete checkpoint has been raised.
    """
    if step.optional:
        log.warning("optional_step_skipped", skill=step.skill, step=step.step_num)
        state.genesis.retry_counts.pop(step.skill, None)
        return _advance(state, _step_index(step))

    skill = step.skill
    step_num = step.step_num
    count = state.genesis.retry_counts.get(skill, 0) + 1
    state.genesis.retry_counts[skill] = count
    limit = state.config.max_revision_retries
    if count < limit:
        log.warning(
            "genesis_step_failed_retrying",
            step=step_num,
            skill=skill,
            failure=failure,
            attempt=count,
            limit=limit,
        )
        return False
    log.error(
        "genesis_step_escalation",
        step=step_num,
        skill=skill,
        failure=failure,
        attempts=count,
    )
    set_checkpoint(
        state,
        CheckpointType.ESCALATION,
        context=(f"Genesis step {step_num} ({skill}) failed after {count} {failure} attempts"),
    )
    return True


def run_genesis_step(state: PipelineState, project_dir: Path | str) -> bool:
    """Execute the next genesis step.

    Returns ``True`` if a checkpoint was reached (genesis-complete or
    escalation) or all steps are already done; ``False`` if the step simply
    advanced (or will be retried) and no human action is needed yet. Mutates
    ``state`` in place; the caller is responsible for persisting it.
    """
    project_dir = Path(project_dir)
    step_idx = state.genesis.current_step
    if step_idx >= len(GENESIS_STEPS):
        return True

    step = GENESIS_STEPS[step_idx]
    log.info("genesis_step", step=step.step_num, skill=step.skill)

    # Dispatch the skill (dispatcher CLI runs G1+G2 + write-overreach audit).
    prompt = f"Execute {step.skill}"
    if step.mode:
        prompt += f" in {step.mode} mode"
    prompt += f". Project dir: {project_dir}"

    result = dispatch_skill(step.skill, project_dir, prompt)
    if not result.success:
        log.error("genesis_dispatch_failed", step=step.step_num, skill=step.skill)
        return _handle_failure(state, step, "dispatch")

    # G4: skill-specific structural validation (every step).
    g4 = run_gate_g4(step.skill, [step.output_path], project_dir)
    if not _gate_passed(g4):
        log.error("genesis_g4_failed", step=step.step_num, skill=step.skill, g4=g4)
        return _handle_failure(state, step, "gate")

    # G3: scoring independence for requires_independent_agent skills (step 17).
    if requires_independent(step.skill):
        g3 = run_gate_g3(step.skill, project_dir)
        if not _gate_passed(g3):
            log.error("genesis_g3_failed", step=step.step_num, skill=step.skill, g3=g3)
            return _handle_failure(state, step, "gate")

    # Success: refresh retrieval indexes, reset retries, advance cursor.
    if step.skill in _INDEX_UPDATE_SKILLS:
        _update_indexes(project_dir, step.skill)
    state.genesis.retry_counts.pop(step.skill, None)
    state.genesis.skills_done.append(step.skill)
    return _advance(state, step_idx)
