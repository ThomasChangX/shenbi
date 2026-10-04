"""Genesis orchestrator: 17-step serial sequence with per-step G4 (spec \u00a75.1).

Each step dispatches a skill, runs G4 (skill-specific structure), and on
success advances the genesis cursor. Step 17 (foundation-review) additionally
runs G3 (scoring independence) because it is a ``requires_independent_agent``
skill. After every truth-writing step the Route A entity index
(``truth-index.json``) is rebuilt and Route B embeddings are refreshed when the
model is available (\u00a77.3 degradation path).

dispatch/gate failures retry per spec \u00a711: up to ``max_revision_retries``
attempts, then an escalation checkpoint is raised. The retry decision is
delegated to ``shenbi.pipeline.error_handler.handle_dispatch_failure``
(W3T8), so this module only mutates state (retry counts, checkpoints).

The orchestrator is stateless itself: it mutates the passed-in
:class:`PipelineState` in memory and the caller persists it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from shenbi.contracts.paths import PathContext
from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import (
    dispatch_skill,
    requires_independent,
    run_gate_g3,
    run_gate_g4,
)
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.error_handler import handle_dispatch_failure
from shenbi.pipeline.state import (
    CheckpointType,
    GenesisState,
    PipelineState,
)
from shenbi.pipeline.truth_embed import embed_and_store, is_embed_available
from shenbi.pipeline.truth_io import split_table_cells
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
        9, "shenbi-foreshadowing-lifecycle", mode="genesis", output_path="truth/pending_hooks.md"
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
        "shenbi-foreshadowing-lifecycle",
        "shenbi-power-system",
        "shenbi-location-builder",
        "shenbi-relationship-map",
        "shenbi-book-spine-init",
        "shenbi-intent-management",
        "shenbi-style-learning",
        "shenbi-anchor-curate",
    }
)


#: Genesis steps whose real pipeline output set exceeds the single
#: ``output_path`` (stage-8 r2: narrowing persistence to output_path alone
#: silently dropped legit multi-file genesis artifacts). probe10: with the
#: quarantine validation following outputs_override, worldbuilding's prompt
#: under-declared rules/locations and the step shipped without them.
GENESIS_EXTRA_OUTPUTS: dict[str, list[str]] = {
    "shenbi-worldbuilding": ["world/rules.md", "world/locations.md"],
    # G4-story-architecture reads volume_map (>=1 卷 with Objective+KR) and
    # rhythm_principles (non-empty) — both are this step's genesis skeletons,
    # later overwritten by steps 6/7 (probe12: step 4 escalated 3x without
    # them in the prompt/required set).
    "shenbi-story-architecture": ["outline/volume_map.md", "outline/rhythm_principles.md"],
}


#: #48/#49 (probe21 genesis whack-a-mole): a scoped redo re-dispatched with
#: only the reviewer feedback honored the explicit bindings but SHUFFLED every
#: unbound layer (canon → anchor names → 规则五 semantics → 规则1-4 numbering +
#: anchor table; four review rounds). The redo prompt now carries a
#: machine-extracted structure binding of the current on-disk baseline so
#: everything the feedback does not explicitly change is frozen; the
#: genesis-complete raise diffs the frozen snapshot against the regenerated
#: files and reports drift in the checkpoint context.
_BINDING_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
_BINDING_SEPARATOR_CELL_RE = re.compile(r":?-{3,}:?")
_BINDING_MAX_LINES = 120
_BINDING_MAX_CHARS = 8000

BINDING_FREEZE_HEADER = (
    "[重做结构绑定（机器提取自当前盘上基线）——除反馈明确要求修改者外，"
    "以下标题/表头/键值必须逐字保留，不得重编号、改名、增删]"
)


def _structure_binding_lines(text: str) -> list[str]:
    """Structure-level binding lines: headings verbatim, table headers
    verbatim, and each data row's FIRST cell (its key value — anchor names,
    canon terms, volume titles). Prose and frontmatter are not bound (the
    semantic layer is the feedback's job, not the freeze's).
    """
    lines = text.split("\n")
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break
    pipe_rows = [i for i in range(start, len(lines)) if lines[i].lstrip().startswith("|")]
    bindings: list[str] = []
    for i in range(start, len(lines)):
        line = lines[i]
        if _BINDING_HEADING_RE.match(line):
            bindings.append(line.strip())
            continue
        if i not in pipe_rows:
            continue
        cells = split_table_cells(line)
        if cells is None:
            continue
        if cells and all(_BINDING_SEPARATOR_CELL_RE.fullmatch(c) for c in cells if c):
            continue  # separator rows are structural filler
        nxt = next((j for j in pipe_rows if j > i), None)
        nxt_cells = split_table_cells(lines[nxt]) if nxt is not None else None
        if (
            nxt_cells is not None
            and nxt_cells
            and all(_BINDING_SEPARATOR_CELL_RE.fullmatch(c) for c in nxt_cells if c)
        ):
            bindings.append(line.strip())  # table header — frozen verbatim
        elif cells and cells[0].strip():
            bindings.append(f"· {cells[0].strip()}")  # row identity (key value)
    return bindings


def extract_structure_bindings(project_dir: Path, skill: str) -> str:
    """Snapshot the regen target set's structure bindings (headings, table
    headers, first-column key values) for *skill*'s scoped redo.
    """
    step = next((s for s in GENESIS_STEPS if s.skill == skill), None)
    if step is None:
        return ""
    rels: list[str] = (
        [step.output_path, *GENESIS_EXTRA_OUTPUTS.get(skill, [])]
        if step.output_path
        else list(GENESIS_EXTRA_OUTPUTS.get(skill, []))
    )
    parts: list[str] = []
    total = 0
    for rel in rels:
        if not rel:
            continue
        paths = (
            sorted(project_dir.glob(rel))
            if any(ch in rel for ch in "*?")
            else ([project_dir / rel] if (project_dir / rel).exists() else [])
        )
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            blines = _structure_binding_lines(text)[:_BINDING_MAX_LINES]
            if not blines:
                continue
            block = f"{rel}:\n" + "\n".join(f"  {b}" for b in blines)
            if total + len(block) > _BINDING_MAX_CHARS:
                log.info("genesis_binding_capped", skill=skill, file=rel)
                continue
            total += len(block)
            parts.append(block)
    return "\n\n".join(parts)


def _skill_binding_drift(skill: str, frozen: str, project_dir: Path) -> str:
    """Per-skill drift note for one frozen snapshot: ``skill: 丢失[...]新增[...]``
    — empty when the structure held (or the target vanished; G4 not_found
    owns that signal). Shared by the genesis-complete report and the
    write-side guard in :func:`run_genesis_step`.
    """
    current = extract_structure_bindings(project_dir, skill)
    if not current:
        return ""
    frozen_lines = [
        l.strip() for l in frozen.split("\n") if l.strip() and not l.strip().endswith(":")
    ]
    current_lines = [
        l.strip() for l in current.split("\n") if l.strip() and not l.strip().endswith(":")
    ]
    current_set = set(current_lines)
    frozen_set = set(frozen_lines)
    missing = [l for l in frozen_lines if l not in current_set][:10]
    added = [l for l in current_lines if l not in frozen_set][:10]
    if not missing and not added:
        return ""
    bits: list[str] = []
    if missing:
        bits.append("丢失「" + "」「".join(missing) + "」")
    if added:
        bits.append("新增「" + "」「".join(added) + "」")
    return f"{skill}: " + "；".join(bits)


def binding_drift_report(state: PipelineState, project_dir: Path) -> str:
    """#49: diff each redo skill's frozen binding snapshot against the
    REGENERATED files. Structural drift (renamed rules, shuffled anchors,
    renumbering) is reported for the reviewer — the machine cannot tell a
    feedback-sanctioned rename from an unsanctioned shuffle, so this is
    evidence, not a verdict.
    """
    if not state.genesis.frozen_bindings:
        return ""
    notes: list[str] = []
    for skill, frozen in state.genesis.frozen_bindings.items():
        note = _skill_binding_drift(skill, frozen, project_dir)
        if note:
            notes.append(note)
    if not notes:
        log.info("genesis_binding_held", skills=sorted(state.genesis.frozen_bindings))
        return ""
    return "[结构绑定漂移—人工核对反馈是否明确要求这些变更] " + "；".join(notes)


def mark_skill_done(state: PipelineState, skill: str) -> None:
    """Record skill completion idempotently.

    F367 (spec #39 T9): a REJECT-redo of the same skill must not append a
    duplicate completion record (18-row artifacts were observed in audits).
    """
    if skill not in state.genesis.skills_done:
        state.genesis.skills_done.append(skill)


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
    except Exception as e:  # noqa: BLE001 (C13 allowlist: intentional broad catch, structured handling per spec #39 T5)
        log.warning("truth_index_update_failed", skill=skill, error=str(e))
        return
    try:
        _update_route_b(project_dir, index, skill)
    except Exception as e:  # noqa: BLE001 (C13 allowlist: intentional broad catch, structured handling per spec #39 T5)
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
    store = EmbeddingStore(project_dir / "truth-embeddings.db")
    embedded = 0
    try:
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
    finally:
        # F328 (C28 R2b): the sqlite handle was never closed — genesis leaked
        # one connection per skill (the model itself stays resident as the
        # process singleton by design).
        store.close()
    if embedded:
        log.info("route_b_embeds_updated", skill=skill, embedded=embedded)


def _advance(state: PipelineState, step_idx: int, project_dir: Path | str | None = None) -> bool:
    """Bump the genesis cursor and set the completion checkpoint if done.

    Shared by the success path and the optional-skip path. Returns ``True``
    when genesis has finished (all steps consumed), ``False`` when at least
    one step remains. At completion, the chapter-count reconciliation
    (fixcheck P1: five derivation sources with no comparison point —
    ceil(target/default) vs novel.json vs three frontmatters silently
    diverged 100-vs-50) runs deterministically and any mismatch leads the
    checkpoint context as MUST-FIX: GENESIS_COMPLETE already gates entry
    to the chapter loop, so the reviewer gets machine evidence instead of
    hoping the foundation-review LLM catches the arithmetic.
    """
    state.genesis.current_step = step_idx + 1
    if state.genesis.current_step >= len(GENESIS_STEPS):
        state.genesis.state = GenesisState.CHECKPOINT_PENDING
        context = "Review all genesis outputs before entering chapter loop."
        if project_dir is not None:
            from shenbi.pipeline._shared import (
                reconcile_chapter_counts,
                reconcile_first_appearances,
            )

            issues = reconcile_chapter_counts(Path(project_dir))
            issues.extend(reconcile_first_appearances(Path(project_dir)))
            if issues:
                log.error("genesis_chapter_count_reconcile_failed", issues=issues)
                context = (
                    "MUST-FIX 章数对账不一致（进入章节循环前必须消解）: "
                    + "；".join(issues)
                    + " ｜ "
                    + context
                )
        # #49: scoped-redo binding drift leads the reviewer's evidence —
        # renames/renumbering the feedback did not sanction surface here
        # instead of via a hand diff (probe21: four rounds to converge).
        if project_dir is not None and state.genesis.frozen_bindings:
            drift = binding_drift_report(state, Path(project_dir))
            if drift:
                log.error("genesis_binding_drift_detected")
                context = drift + " ｜ " + context
            state.genesis.frozen_bindings = {}  # consumed at raise
        set_checkpoint(
            state,
            CheckpointType.GENESIS_COMPLETE,
            artifact="foundation/review_report.md",
            context=context,
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
    project_dir: Path | str,
) -> bool:
    """Record a dispatch/gate failure for a genesis step.

    Optional steps skip forward on the first failure: the cursor advances
    past them with no retry or escalation (the ``optional`` flag marks the
    step as non-blocking). Non-optional steps retry per spec §11 up to
    ``max_revision_retries`` (default 3), then raise an escalation.

    Returns ``False`` when the step should be retried on the next ``cmd_next``
    call (cursor unchanged) or when it was skipped (cursor advanced); ``True``
    once an escalation or genesis-complete checkpoint has been raised.
    """
    if step.optional:
        log.warning("optional_step_skipped", skill=step.skill, step=step.step_num)
        state.genesis.retry_counts.pop(step.skill, None)
        return _advance(state, _step_index(step), project_dir)

    skill = step.skill
    step_num = step.step_num
    count = state.genesis.retry_counts.get(skill, 0) + 1
    state.genesis.retry_counts[skill] = count
    if handle_dispatch_failure(state, skill, count):
        log.warning(
            "genesis_step_failed_retrying",
            step=step_num,
            skill=skill,
            failure=failure,
            attempt=count,
            limit=state.config.max_revision_retries,
        )
        return False
    # Retries exhausted: dispatch escalation-review first, then set checkpoint.
    from shenbi.pipeline.revision_router import dispatch_escalation

    dispatch_escalation(
        project_dir,
        None,  # genesis has no chapter context — N-paths filtered
        context=f"Genesis step {step_num} ({skill}) failed after {count} {failure} attempts",
        details=state.genesis.retry_feedback.get(skill),
        failing_skill=skill,
    )
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
        chapter=None,  # spec #34 F336/F352: genesis 语义=未进章，统一 None（非 0 哨兵）
        artifact="audits/escalation-genesis-report.md",
        context=(
            f"Genesis step {step_num} ({skill}) "
            f"failed after {count} {failure} attempts. "
            f"See audits/escalation-genesis-report.md for analysis."
        ),
    )
    return True


def genesis_finalize_volume_map(project_dir: Path) -> int:
    """Deterministic total_chapters fixation hook (spec #6 R2).

    Runs at genesis step-6 success: no LLM involvement, no later genesis step
    rewrites volume_map (GENESIS_STEPS verified). Delegates to the single
    write-point in _shared.update_total_chapters.
    """
    from shenbi.pipeline._shared import update_total_chapters

    total = update_total_chapters(project_dir)
    if total:
        log.info("genesis_total_chapters_fixed", total_chapters=total)
    return total


def _sync_spine_total(project_dir: Path) -> None:
    """Sync spine-init's ``total_chapters: 0`` placeholder (probe3 P2-R).

    spine-init's template ships the legitimate pending_intent placeholder
    even though novel.json's total was deterministically fixed at step 6 —
    so every new project's genesis-complete reconciliation fired a false
    MUST-FIX that only a routine human edit (0→N) could clear. Only the 0
    placeholder is patched (same R2 spirit as the volume-map fixation
    hook); a non-zero divergent value is left for the gate to catch, and
    the status vocabulary stays memory-distill's.
    """
    spine = project_dir / "truth" / "book_spine.md"
    novel = project_dir / "novel.json"
    if not spine.exists() or not novel.exists():
        return
    try:
        total = json.loads(novel.read_text(encoding="utf-8")).get("total_chapters")
    except (OSError, ValueError):
        return
    if not isinstance(total, int) or total <= 0:
        return
    text = spine.read_text(encoding="utf-8")
    patched, n = re.subn(
        r"^total_chapters:\s*0\s*$",
        f"total_chapters: {total}",
        text,
        flags=re.MULTILINE,
    )
    if n:
        safe_write(spine, patched.encode("utf-8"))
        log.info("genesis_spine_total_synced", total_chapters=total)


def _genesis_sidecar_paths(skill: str, output_path: str | None) -> list[str]:
    """Contract-declared decisions sidecars for a genesis step (spec #30 T2
    parity with the chapter loop, probe3 P2-R).

    probe3: genre-config-decisions.json was doubly invisible at genesis —
    ``outputs_override`` narrowed the model's instruction to the step's main
    artifact (so the sidecar was never even requested), and the chapter
    loop's sidecar expansion is existence-gated (so its absence never
    reached G4). Genesis includes the skill's static decisions sidecars in
    BOTH the instruction and the G4 file list; chapter-templated paths are
    excluded (genesis has no chapter context).
    """
    if not output_path:
        return []
    sidecars: list[str] = []
    try:
        from shenbi.contracts import load_contract

        contract = load_contract(skill)
    except Exception as e:  # noqa: BLE001 — contract issues surface in G0
        log.warning("genesis_sidecar_contract_unavailable", skill=skill, error=str(e))
        return []
    for out in contract.get("writes", []):
        name = Path(out).name
        if "decisions" not in name or "{" in out or "chapter" in name:
            continue
        if out not in sidecars:
            sidecars.append(out)
    return sidecars


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
    if step.skill in state.genesis.skills_done:
        # Scoped redo (probe8 ``--redo-steps``): the cursor was rewound over
        # steps the adjudication ruled 保留不动 — they stay done and must
        # advance without re-dispatch.
        state.genesis.current_step = step_idx + 1
        return False
    log.info("genesis_step", step=step.step_num, skill=step.skill)

    # Build prompt, injecting G4 failure feedback from prior attempts
    prompt = f"Execute {step.skill}"
    if step.mode:
        prompt += f" in {step.mode} mode"
    prompt += f". Project dir: {project_dir}"

    # Inject prior G4 failure details as corrective feedback on retry
    prev_g4_failure = state.genesis.retry_feedback.get(step.skill)
    if prev_g4_failure:
        # The slot carries both G4 must-fix feedback and genesis-complete
        # review-reject feedback (scoped redo, probe8) — keep the header
        # accurate for either source.
        prompt += (
            f"\n\n## CORRECTIVE FEEDBACK (prior attempt was rejected)\n"
            f"Failure details — fix every issue they name in your new output:\n"
            f"```\n{prev_g4_failure}\n```\n"
        )

    step_ctx = (
        PathContext(anchor=1) if step.skill == "shenbi-anchor-curate" else None
    )  # F380 (spec #6): AC-NNN -> AC-001.md genesis sentinel, conditional on this step
    sidecars = _genesis_sidecar_paths(step.skill, step.output_path)
    extras = GENESIS_EXTRA_OUTPUTS.get(step.skill, [])
    outputs_override = ([step.output_path] + extras + sidecars) if step.output_path else None
    result = dispatch_skill(
        step.skill,
        project_dir,
        prompt,
        path_context=step_ctx,
        # Stage-8 review I1: the GenesisStep's declared output IS the genesis
        # output set — keeps per-chapter-mode contract writes (lifecycle's
        # bridge_tracker) out of the genesis "Files to create" instruction.
        # Static decisions sidecars stay IN (spec #30 T2; probe3: excluding
        # them meant the sidecar was never requested and never produced).
        outputs_override=outputs_override,
    )
    if not result.success:
        log.error("genesis_dispatch_failed", step=step.step_num, skill=step.skill)
        if hasattr(result, "stderr") and result.stderr:
            log.error(
                "genesis_dispatch_stderr", skill=step.skill, stderr_preview=result.stderr[:2000]
            )
            # probe14 #2: dispatch failures (parse/quarantine) retried blind —
            # the stderr now carries the missing-path signature + expected
            # ### FILE format, so route it into the corrective slot.
            state.genesis.retry_feedback[step.skill] = (
                f"上一次派发失败（输出未落盘）：{result.stderr}"
            )
        if hasattr(result, "returncode"):
            log.error("genesis_dispatch_rc", skill=step.skill, rc=result.returncode)
        return _handle_failure(state, step, "dispatch", project_dir)

    # G4: skill-specific structural validation (every step). Sidecars join
    # the file list UNCONDITIONALLY (not existence-gated) so a never-produced
    # sidecar surfaces as not_found instead of staying invisible.
    g4_files = ([step.output_path] + sidecars) if step.output_path else []
    g4 = run_gate_g4(step.skill, g4_files, project_dir)
    if _gate_passed(g4):
        # Canary defect 'retry_feedback 永不清': stale corrective feedback
        # from a PRIOR failure stayed injected into every later dispatch
        # prompt for the same skill. A pass retires it.
        state.genesis.retry_feedback.pop(step.skill, None)
    if not _gate_passed(g4):
        log.warning(
            "genesis_g4_failed",
            step=step.step_num,
            skill=step.skill,
            g4=str(g4.get("must_fix", [])),
        )
        # Store G4 failure for retry feedback
        must_fix = g4.get("must_fix", [])
        state.genesis.retry_feedback[step.skill] = (
            f"G4 check failed: {must_fix}\nFull result: {json.dumps(g4, default=str)}"
        )
        # Auto mode: retry once, then continue regardless — EXCEPT a missing
        # declared artifact (not_found): advancing skills_done without a
        # contract-declared write is silent data loss (probe3:
        # genre-config-decisions.json), so it consumes the retry budget and
        # escalates like any hard failure.
        if state.config.per_chapter_review_enabled:
            return _handle_failure(state, step, "gate", project_dir)
        if any("not_found" in str(item) for item in must_fix):
            log.error(
                "genesis_g4_not_found_no_auto_continue",
                step=step.step_num,
                skill=step.skill,
                must_fix=must_fix,
            )
            return _handle_failure(state, step, "gate", project_dir)
        count = state.genesis.retry_counts.get(step.skill, 0) + 1
        state.genesis.retry_counts[step.skill] = count
        if count <= 1:
            log.info("genesis_g4_retry_auto", step=step.step_num, attempt=count)
            return False
        log.info(
            "genesis_g4_continue_auto",
            step=step.step_num,
            msg="continuing despite G4 failure in auto mode",
        )
        state.genesis.retry_counts.pop(step.skill, None)
        # Fall through to success path

    # G3: scoring independence for requires_independent_agent skills (step 17).
    if requires_independent(step.skill):
        # G3.4 is fail-closed on progress.json scorer evidence — record it
        # BEFORE the gate runs. Each genesis dispatch is a distinct
        # fresh-context agent, so per-dispatch route ids are the honest
        # independence claim (canary escalation #5 dead-wire repair).
        from shenbi.pipeline.dispatch_helper import record_scorer_evidence

        record_scorer_evidence(
            project_dir,
            scorer_route=f"genesis-dispatch:{step.skill}",
            generator_routes={s: f"genesis-dispatch:{s}" for s in state.genesis.skills_done},
            extra_progress={
                "phase": state.phase.value,
                "genesis_current_step": step.step_num,
                "genesis_completed_skills": list(state.genesis.skills_done),
            },
        )
        g3 = run_gate_g3(step.skill, project_dir)
        if not _gate_passed(g3):
            log.error("genesis_g3_failed", step=step.step_num, skill=step.skill, g3=g3)
            return _handle_failure(state, step, "gate", project_dir)

    # Success: refresh retrieval indexes, reset retries, advance cursor.
    if step.skill in _INDEX_UPDATE_SKILLS:
        _update_indexes(project_dir, step.skill)
    if step.skill == "shenbi-volume-outlining":  # step 6: volume map landed (R2)
        genesis_finalize_volume_map(project_dir)
    if step.skill == "shenbi-book-spine-init":  # probe3 P2-R: placeholder 0 → real total
        _sync_spine_total(project_dir)
    state.genesis.retry_counts.pop(step.skill, None)
    mark_skill_done(state, step.skill)
    # #49 write-side guard (probe22 adjudication #002 P0-1 / #003 P3-4): a
    # redone step whose output drifts from its frozen structure bindings must
    # not let the cycle continue silently — probe22's unsanctioned canon swap
    # landed at step 1 and steps 2-17 all dispatched on the wrong base before
    # the genesis-complete report surfaced it. The machine cannot judge a
    # feedback-sanctioned rename from an unsanctioned shuffle, so it STOPS
    # instead of verdicting: raise the checkpoint NOW with the drift leading
    # the context and the freeze intact — the reject redo list then decides
    # (listed step = contested, re-dispatched against the ORIGINAL freeze;
    # unlisted frozen skill = drift ruled sanctioned, freeze consumed).
    frozen = state.genesis.frozen_bindings.get(step.skill)
    if frozen:
        drift = _skill_binding_drift(step.skill, frozen, project_dir)
        if drift:
            log.error("genesis_redo_step_binding_drift", step=step.step_num, skill=step.skill)
            remaining = [
                s.step_num
                for s in GENESIS_STEPS[step_idx + 1 :]
                if s.skill not in state.genesis.skills_done
            ]
            if remaining:
                verdict = (
                    f"漂移若为反馈明示授权：reject 并附 --redo-steps "
                    f"{','.join(map(str, remaining))} 续跑其余步骤（未列出即认可本步现状）；"
                    f"若为越权改写：reject 并附 --redo-steps {step.step_num} 与修正反馈"
                )
            else:
                verdict = (
                    "漂移若为反馈明示授权（其余步骤均已完结）：approve 进入章节循环；"
                    "若为越权改写：reject 并附 --redo-steps "
                    f"{step.step_num} 与修正反馈"
                )
            state.genesis.current_step = len(GENESIS_STEPS)
            state.genesis.state = GenesisState.CHECKPOINT_PENDING
            set_checkpoint(
                state,
                CheckpointType.GENESIS_COMPLETE,
                artifact="foundation/review_report.md",
                context=(
                    f"[重做步骤 {step.step_num}（{step.skill}）结构绑定漂移——本步已停，"
                    f"后续步骤未派发] {drift} ｜ {verdict} ｜ "
                    f"Review all genesis outputs before entering chapter loop."
                ),
            )
            return True
    return _advance(state, step_idx, project_dir)
