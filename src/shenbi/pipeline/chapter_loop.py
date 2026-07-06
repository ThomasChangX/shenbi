"""Chapter loop orchestrator: per-chapter step sequence with staging, context
assembly, and G4 validation (spec section 6.1).

The chapter loop runs 20 steps per chapter (the spec's 13-step loop expanded
with individual audit-circle skills). Steps 2 (chapter-planning) and 7
(state-settling) write to ``staging/`` and are gated by human-review
checkpoints. Step 4 (pipeline-context-assemble) materializes the three-route
context package (section 7) before chapter-drafting consumes it.

Each dispatched step runs G4 (skill-specific structure). Step 17
(review-resonance) additionally runs G3 (scoring independence) because it is a
``requires_independent_agent`` skill.

dispatch/gate failures retry per spec section 11: up to
``max_revision_retries`` attempts, then an escalation checkpoint is raised.
The retry decision is delegated to
``shenbi.pipeline.error_handler.handle_dispatch_failure`` (W3T8).

Steps 8-11 (audit genre circle + revision routing) are stubbed: W3T4
implements the audit layer, W3T5 implements revision routing. Clear TODO
markers indicate the integration points.
Revision routing (W3T5) is integrated: after review-resonance the router
determines the route and step 18 (chapter-revision) is skipped when no
revision is needed.

The orchestrator is stateless itself: it mutates the passed-in
:class:`PipelineState` in memory and the caller persists it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.pipeline.audit_layer import run_audit_layer
from shenbi.pipeline.dispatch_helper import (
    dispatch_skill,
    requires_independent,
    run_gate_g3,
    run_gate_g4,
)
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.error_handler import handle_dispatch_failure, handle_audit_blocking
from shenbi.pipeline.revision_router import (
    RevisionRoute,
    check_resonance,
    collect_audit_issues,
    route_chapter_revision,
)
from shenbi.pipeline.state import (
    ChapterState,
    CheckpointType,
    PipelineState,
)
from shenbi.status import GateStatus

log = get_logger(__name__)


@dataclass
class ChapterStep:
    """One step in the per-chapter sequence (spec section 6.1).

    Attributes:
        step_num: 1-based step number for logging.
        skill: Skill name dispatched (``shenbi-*``) or pipeline-internal
            identifier (``pipeline-*`` -- not dispatched, just advanced).
        name: Human-readable label.
        checkpoint: Checkpoint type raised after this step succeeds, or None.
        uses_staging: If True, the dispatched skill writes to ``staging/``
            and G4 validates the staging copy (spec section 2.7).
        calls_context_assembly: If True, run :func:`assemble_context` before
            dispatching this step (materializes ``context/chapter-N-context.md``).
        is_audit: If True, this step is part of the audit core circle.
        output_path: Expected output file relative to project dir (with N
            placeholders for chapter number). Used for G4 validation. Empty
            string means no single file (G4 validates generically).
    """

    step_num: int
    skill: str
    name: str
    checkpoint: CheckpointType | None = None
    uses_staging: bool = False
    calls_context_assembly: bool = False
    is_audit: bool = False
    output_path: str = ""


# Full 13-step + sub-steps from spec section 6.1.
# The audit layer (spec step 8) is expanded into 7 individual core-circle
# skills for serial execution. Genre-circle skills are dispatched dynamically
# by the audit sub-orchestrator (W3T4).
CHAPTER_STEPS: list[ChapterStep] = [
    ChapterStep(
        1,
        "shenbi-intent-management",
        "intent-management",
        output_path="truth/current_focus.md",
    ),
    ChapterStep(
        2,
        "shenbi-chapter-planning",
        "chapter-planning",
        checkpoint=CheckpointType.CHAPTER_MEMO,
        uses_staging=True,
        output_path="plans/chapter-N-plan.md",
    ),
    ChapterStep(
        3,
        "shenbi-foreshadowing-plant",
        "foreshadowing-plant",
        output_path="truth/pending_hooks.md",
    ),
    ChapterStep(
        4,
        "pipeline-context-assemble",
        "context-assembly",
        calls_context_assembly=True,
        output_path="context/chapter-N-context.md",
    ),
    ChapterStep(
        5,
        "shenbi-context-composing",
        "context-composing",
        output_path="",
    ),
    ChapterStep(
        6,
        "shenbi-chapter-drafting",
        "chapter-drafting",
        output_path="chapters/chapter-N.md",
    ),
    ChapterStep(
        7,
        "shenbi-state-settling",
        "state-settling",
        checkpoint=CheckpointType.STATE_SETTLE,
        uses_staging=True,
        output_path="",
    ),
    ChapterStep(
        8,
        "shenbi-foreshadowing-track",
        "foreshadowing-track",
        output_path="truth/pending_hooks.md",
    ),
    ChapterStep(
        9,
        "shenbi-foreshadowing-recall",
        "foreshadowing-recall",
        output_path="truth/foreshadowing_recall_result.md",
    ),
    # foreshadowing-resolve is conditional -- handled in run_chapter_step
    # after foreshadowing-track succeeds (spec section 6.1 step 7b).
    # Audit core circle: 7 skills, serial, BLOCKING stops (spec section 6.2).
    ChapterStep(
        10,
        "shenbi-review-anti-ai",
        "audit:anti-ai",
        is_audit=True,
        output_path="audits/chapter-N-anti-ai.md",
    ),
    ChapterStep(
        11,
        "shenbi-review-continuity",
        "audit:continuity",
        is_audit=True,
        output_path="audits/chapter-N-continuity.md",
    ),
    ChapterStep(
        12,
        "shenbi-review-character",
        "audit:character",
        is_audit=True,
        output_path="audits/chapter-N-character.md",
    ),
    ChapterStep(
        13,
        "shenbi-review-pacing",
        "audit:pacing",
        is_audit=True,
        output_path="audits/chapter-N-pacing.md",
    ),
    ChapterStep(
        14,
        "shenbi-review-foreshadowing",
        "audit:foreshadowing",
        is_audit=True,
        output_path="audits/chapter-N-foreshadowing.md",
    ),
    ChapterStep(
        15,
        "shenbi-review-memo-compliance",
        "audit:memo-compliance",
        is_audit=True,
        output_path="audits/chapter-N-memo-compliance.md",
    ),
    ChapterStep(
        16,
        "shenbi-review-pov",
        "audit:pov",
        is_audit=True,
        output_path="audits/chapter-N-pov.md",
    ),
    # Genre circle dispatched dynamically by audit sub-orchestrator (W3T4).
    # TODO(W3T4): from shenbi.pipeline.audit_layer import run_audit_layer
    #   Call after step 16 (last core-circle audit) to run genre-circle skills.
    # review-resonance (independent agent, G3 required, spec section 6.1 step 9).
    ChapterStep(
        17,
        "shenbi-review-resonance",
        "review-resonance",
        output_path="audits/chapter-N-resonance.md",
    ),
    # Revision routing + execution (conditional, spec section 6.1 steps 10-11).
    # Revision routing runs after review-resonance (W3T5 integrated, spec §6.3).
    # Step 18 is skipped when route == RevisionRoute.NO_REVISION.
    ChapterStep(
        18,
        "shenbi-chapter-revision",
        "revision",
        output_path="chapters/chapter-N.md",
    ),
    # Snapshot + drift (spec section 6.1 steps 12-13).
    ChapterStep(
        19,
        "shenbi-snapshot-manage",
        "snapshot-manage",
        output_path="snapshots/chapter-NNN/",
    ),
    ChapterStep(
        20,
        "shenbi-drift-guidance",
        "drift-guidance",
        output_path="truth/drift_guidance.md",
    ),
]

# 0-based index of the last core-circle audit step (for genre-circle trigger).
_LAST_AUDIT_IDX = max(i for i, s in enumerate(CHAPTER_STEPS) if s.is_audit)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gate_passed(result: dict[str, Any]) -> bool:
    """True iff a gate result dict reports PASS (handles str and GateStatus)."""
    return str(result.get("status", "")) == GateStatus.PASS


def _substitute_chapter(path: str, chapter: int) -> str:
    """Replace N / NNN placeholders with the actual chapter number."""
    return path.replace("NNN", f"{chapter:03d}").replace("N", str(chapter))


def _retry_key(chapter: int, skill: str) -> str:
    """Chapter-scoped retry key so retries from different chapters don't collide."""
    return f"ch{chapter}-{skill}"


def _resolve_g4_path(project_dir: Path, step: ChapterStep, chapter: int) -> str:
    """Resolve the output file path for G4 validation.

    For staging steps, returns the staging-relative path so G4 validates the
    staging copy (not the final committed path). Empty string if the step has
    no single output file.
    """
    if not step.output_path:
        return ""
    resolved = _substitute_chapter(step.output_path, chapter)
    if step.uses_staging:
        from shenbi.pipeline.checkpoint import STAGING_DIR

        return f"{STAGING_DIR}/{resolved}"
    return resolved


def _resolve_g4_files(project_dir: Path, step: ChapterStep, chapter: int) -> list[str]:
    """Return list of file paths for G4 validation.

    Single-file steps return one path. State-settling returns all
    staging/truth/*.md files because it writes multiple truth outputs.
    Steps with no output return [].
    """
    single = _resolve_g4_path(project_dir, step, chapter)
    if single:
        return [single]

    # State-settling writes multiple truth files to staging/
    if step.uses_staging and "state-settling" in step.skill:
        from shenbi.pipeline.checkpoint import STAGING_DIR

        staging_truth = project_dir / STAGING_DIR / "truth"
        if staging_truth.exists():
            return sorted(f"{STAGING_DIR}/truth/{p.name}" for p in staging_truth.glob("*.md"))

    return []


def _handle_failure(
    state: PipelineState,
    step: ChapterStep,
    chapter: int,
    failure: str,
    project_dir: Path | str,
) -> bool:
    """Record a dispatch/gate failure for a chapter step.

    Retries per spec section 11 up to ``max_revision_retries`` (default 3),
    then raises an escalation checkpoint. Returns False when the step should
    be retried on the next call (step_index unchanged) or True once an
    escalation checkpoint has been raised.
    """
    key = _retry_key(chapter, step.skill)
    count = state.chapter_loop.retry_counts.get(key, 0) + 1
    state.chapter_loop.retry_counts[key] = count
    if handle_dispatch_failure(state, step.skill, count):
        log.warning(
            "chapter_step_failed_retrying",
            chapter=chapter,
            step=step.step_num,
            skill=step.skill,
            failure=failure,
            attempt=count,
            limit=state.config.max_revision_retries,
        )
        return False
    # Retries exhausted: dispatch escalation-review first, then set checkpoint.
    from shenbi.pipeline.revision_router import dispatch_escalation

    dispatch_escalation(
        project_dir,
        chapter,
        context=f"Chapter {chapter} step {step.step_num} ({step.skill}) failed after {count} {failure} attempts",
    )
    log.error(
        "chapter_step_escalation",
        chapter=chapter,
        step=step.step_num,
        skill=step.skill,
        failure=failure,
        attempts=count,
    )
    set_checkpoint(
        state,
        CheckpointType.ESCALATION,
        chapter=chapter,
        artifact=f"audits/escalation-{chapter}-report.md",
        context=(
            f"Chapter {chapter} step {step.step_num} ({step.skill}) "
            f"failed after {count} {failure} attempts. "
            f"See audits/escalation-{chapter}-report.md for analysis."
        ),
    )
    return True


def _record_step_done(state: PipelineState, step: ChapterStep, chapter: int) -> None:
    """Append the skill to the chapter's steps_done list."""
    key = str(chapter)
    cs = state.chapter_loop.chapter_states.get(key)
    if cs is None:
        cs = ChapterState()
        state.chapter_loop.chapter_states[key] = cs
    if step.skill not in cs.steps_done:
        cs.steps_done.append(step.skill)


def _reset_retries(state: PipelineState, step: ChapterStep, chapter: int) -> None:
    """Clear retry count after a successful step."""
    state.chapter_loop.retry_counts.pop(_retry_key(chapter, step.skill), None)


def _complete_chapter(state: PipelineState, chapter: int) -> bool:
    """Advance to the next chapter, optionally setting a per-chapter checkpoint.

    Returns True when a per-chapter checkpoint is set (review needed), False
    when automatic advancement is configured.
    """
    key = str(chapter)
    cs = state.chapter_loop.chapter_states.get(key)
    if cs is None:
        cs = ChapterState()
        state.chapter_loop.chapter_states[key] = cs
    cs.status = "complete"

    state.chapter_loop.current_chapter = chapter + 1
    state.chapter_loop.step_index = 0
    state.chapter_loop.current_step = ""

    if state.chapter_loop.per_chapter_review_enabled:
        set_checkpoint(
            state,
            CheckpointType.PER_CHAPTER,
            chapter=chapter,
            context=(
                f"Chapter {chapter} complete. Review before proceeding to chapter {chapter + 1}."
            ),
        )
        return True
    return False


def _advance(
    state: PipelineState,
    step_idx: int,
    step: ChapterStep,
    chapter: int,
) -> bool:
    """Bump the step cursor and set checkpoint if the step has one.

    Returns True if a checkpoint was raised or the chapter completed;
    False if the step simply advanced with no human action needed.

    Checkpoint suppression (--auto mode): when the corresponding config
    flag is False the checkpoint is silently skipped and the cursor
    advances as if it were a non-checkpoint step.
    """
    state.chapter_loop.step_index = step_idx + 1
    state.chapter_loop.current_step = ""

    if step.checkpoint is not None:
        # Honour --auto suppression flags so automated runs aren't
        # blocked on every chapter-memo / state-settle.
        cfg = state.config
        if step.checkpoint == CheckpointType.CHAPTER_MEMO and not cfg.chapter_memo_review_required:
            pass  # skip checkpoint, fall through to chapter-completion check
        elif (
            step.checkpoint == CheckpointType.STATE_SETTLE and not cfg.state_settle_review_required
        ):
            pass  # skip checkpoint
        else:
            artifact = (
                _substitute_chapter(step.output_path, chapter)
                if step.output_path
                else f"chapter-{chapter}/{step.name}"
            )
            set_checkpoint(
                state,
                step.checkpoint,
                chapter=chapter,
                artifact=artifact,
                context=f"Review {step.name} for chapter {chapter}",
            )
            return True

    if state.chapter_loop.step_index >= len(CHAPTER_STEPS):
        return _complete_chapter(state, chapter)
    return False


def _run_context_assembly(project_dir: Path, chapter: int) -> None:
    """Materialize the three-route context package for the chapter.

    Calls :func:`assemble_context` + :func:`write_context_file` from
    ``context_assemble``. Missing plan files are tolerated (early-stage
    projects): a warning (with stack trace) is logged and the step continues
    so chapter-drafting can proceed without context.
    """
    try:
        from shenbi.pipeline.context_assemble import (
            assemble_context,
            write_context_file,
        )

        plan_path = f"plans/chapter-{chapter}-plan.md"
        pkg = assemble_context(project_dir, plan_path)
        out = write_context_file(project_dir, chapter, pkg)
        log.info(
            "context_assembled_for_chapter",
            chapter=chapter,
            sections=len(pkg.sections),
            total_tokens=pkg.total_tokens,
            output=str(out),
        )
    except Exception as e:
        log.warning("context_assembly_failed", chapter=chapter, error=str(e), exc_info=True)


def _check_conditional_resolve(state: PipelineState, project_dir: Path, chapter: int) -> None:
    """Dispatch foreshadowing-resolve if TRIGGERED hooks are detected.

    Reads the foreshadowing-track output (``truth/pending_hooks.md``). If any
    hooks have ``state: TRIGGERED``, dispatches ``shenbi-foreshadowing-resolve``
    to handle them (spec section 6.1 step 7b). Missing file or no triggered
    hooks are no-ops.
    """
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        return

    text = hooks_file.read_text(encoding="utf-8")
    triggered_count = _count_triggered_hooks(text)
    if triggered_count > 0:
        log.info("conditional_resolve_triggered", chapter=chapter, count=triggered_count)
        dispatch_skill(
            "shenbi-foreshadowing-resolve",
            project_dir,
            f"Resolve {triggered_count} TRIGGERED hooks for chapter {chapter}.",
        )
    else:
        log.debug("no_triggered_hooks", chapter=chapter)


def _count_triggered_hooks(text: str) -> int:
    r"""Count hooks with state TRIGGERED in the pending_hooks.md content.

    Parses YAML frontmatter (``---\\n...\\n---``) for a ``hooks`` list where
    entries have a ``state`` field. Falls back to a text scan for
    ``state: TRIGGERED`` when frontmatter is absent or malformed.
    """
    # Try YAML frontmatter first.
    if text.startswith("---"):
        import yaml

        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                hooks = fm.get("hooks", [])
                if isinstance(hooks, list):
                    return sum(
                        1 for h in hooks if isinstance(h, dict) and h.get("state") == "TRIGGERED"
                    )
            except Exception:
                pass  # fall through to text scan
    # Fallback: count literal occurrences.
    return text.count("state: TRIGGERED")


def _parse_resonance_score(report_path: Path) -> int | None:
    """Extract resonance score from a review-resonance audit report.

    Attempts three patterns in order:
    1. YAML frontmatter ``resonance_score: 87``
    2. Markdown bold ``**Resonance Score**: 92``
    3. Plain ``Score: 75`` or ``resonance_score: 75``
    """
    if not report_path.exists():
        return None
    text = report_path.read_text(encoding="utf-8")

    # Pattern 1: YAML frontmatter
    if text.startswith("---"):
        import yaml

        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                score = fm.get("resonance_score")
                if isinstance(score, int):
                    return score
            except Exception:
                pass

    # Pattern 2: Markdown bold label (case-insensitive)
    m = re.search(r"\*\*Resonance\s*Score\*\*:\s*(\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Pattern 3: Plain "Score: N" or "resonance_score: N"
    m = re.search(r"(?:Score|resonance_score)\s*:\s*(\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    return None


# ---------------------------------------------------------------------------
# Revision routing helpers (spec §6.3, W3T5)
# ---------------------------------------------------------------------------

_REVISION_ROUTE_KEY = "revision_route"


def _get_chapter_state(state: PipelineState, chapter: int) -> ChapterState:
    """Return the ChapterState for *chapter*, creating it if absent."""
    key = str(chapter)
    cs = state.chapter_loop.chapter_states.get(key)
    if cs is None:
        cs = ChapterState()
        state.chapter_loop.chapter_states[key] = cs
    return cs


def _route_revision_after_resonance(state: PipelineState, project_dir: Path, chapter: int) -> None:
    """Collect audit issues and determine the revision route (spec §6.3).

    Called after the review-resonance step succeeds. Stores the route in the
    chapter's ``audit_results`` so that step 18 (chapter-revision) can decide
    whether to run or skip.
    """
    issues, blocking = collect_audit_issues(project_dir, chapter)
    route = route_chapter_revision(issues, blocking)
    cs = _get_chapter_state(state, chapter)
    cs.audit_results[_REVISION_ROUTE_KEY] = route.value

    # Resonance floor check (spec §6.3). Full borderline/escalation handling
    # is deferred pending chapter_role calibration (Wave 4+); for now a
    # below-floor score with no audit issues is logged so it is visible.
    resonance_ok = check_resonance(cs.resonance_score, state.config.resonance_global_floor)
    if not resonance_ok and not issues:
        log.warning(
            "resonance_below_floor",
            chapter=chapter,
            score=cs.resonance_score,
            floor=state.config.resonance_global_floor,
        )

    log.info(
        "revision_routed",
        chapter=chapter,
        route=route.value,
        issue_count=len(issues),
        blocking=blocking,
    )


def _is_revision_skipped(state: PipelineState, chapter: int) -> bool:
    """True if step 18 (chapter-revision) should be skipped for *chapter*.

    This only applies when the revision router has already run (after
    review-resonance) and determined ``RevisionRoute.NO_REVISION``. Steps
    before review-resonance always proceed normally.
    """
    cs = state.chapter_loop.chapter_states.get(str(chapter))
    if cs is None:
        return False
    return cs.audit_results.get(_REVISION_ROUTE_KEY) == RevisionRoute.NO_REVISION.value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_chapter_step(state: PipelineState, project_dir: Path | str) -> bool:
    """Execute the next chapter step.

    Returns True if a checkpoint was reached (chapter-memo, state-settle,
    per-chapter, or escalation) or all steps are already consumed; False if
    the step simply advanced (or will be retried) and no human action is
    needed yet. Mutates ``state`` in place; the caller persists it.
    """
    project_dir = Path(project_dir)
    step_idx = state.chapter_loop.step_index
    if step_idx >= len(CHAPTER_STEPS):
        return True  # all steps consumed

    step = CHAPTER_STEPS[step_idx]
    chapter = state.chapter_loop.current_chapter
    state.chapter_loop.current_step = step.skill
    log.info("chapter_step", chapter=chapter, step=step.step_num, skill=step.skill)

    # Context assembly (step 4): materialize package before chapter-drafting.
    if step.calls_context_assembly:
        _run_context_assembly(project_dir, chapter)

    # Pipeline-internal steps (not dispatched): advance without dispatch/G4.
    if step.skill.startswith("pipeline-"):
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter)

    # Step 18 (chapter-revision) is conditional -- skip when routing decided
    # no revision is needed (spec §6.3, set during step 17 review-resonance).
    # Scoped to the revision skill ONLY: snapshot (step 19) and drift (step
    # 20) must always run regardless of the revision route.
    if step.skill == "shenbi-chapter-revision" and _is_revision_skipped(state, chapter):
        log.info("revision_step_skipped", chapter=chapter)
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter)

    # Build dispatch prompt (staging steps write to staging/).
    prompt = f"Execute {step.skill} for chapter {chapter}. Project dir: {project_dir}"
    if step.uses_staging:
        prompt += " Write output to staging/ directory."

    # Dispatch the skill.
    result = dispatch_skill(step.skill, project_dir, prompt)

    # State-settling failure: mark settling_failed and pause (spec §11).
    if not result.success and "state-settling" in step.skill:
        from shenbi.pipeline.error_handler import handle_state_settle_failure

        handle_state_settle_failure(state, chapter)
        log.error(
            "chapter_state_settle_failed",
            chapter=chapter,
            step=step.step_num,
        )
        return True  # checkpoint raised, pause for human

    # Scoring failure (review-resonance): exit code 2/3 need special handling.
    if not result.success and "review-resonance" in step.skill:
        from shenbi.pipeline.error_handler import handle_scoring_failure

        if handle_scoring_failure(state, result.returncode):
            log.warning(
                "scoring_failure_retry",
                chapter=chapter,
                exit_code=result.returncode,
            )
            return False  # retry this step, don't advance step_index
        return _handle_failure(state, step, chapter, "scoring", project_dir)

    if not result.success:
        log.error(
            "chapter_dispatch_failed",
            chapter=chapter,
            step=step.step_num,
            skill=step.skill,
        )
        return _handle_failure(state, step, chapter, "dispatch", project_dir)

    # G4: skill-specific structural validation (every dispatched step).
    g4_files = _resolve_g4_files(project_dir, step, chapter)
    g4 = run_gate_g4(step.skill, g4_files, project_dir)
    if not _gate_passed(g4):
        log.error(
            "chapter_g4_failed",
            chapter=chapter,
            step=step.step_num,
            skill=step.skill,
            g4=g4,
        )
        return _handle_failure(state, step, chapter, "gate", project_dir)

    # G3: scoring independence for requires_independent_agent skills (step 17).
    if requires_independent(step.skill):
        g3 = run_gate_g3(step.skill, project_dir)
        if not _gate_passed(g3):
            log.error(
                "chapter_g3_failed",
                chapter=chapter,
                step=step.step_num,
                skill=step.skill,
            )
            return _handle_failure(state, step, chapter, "gate", project_dir)

    # Conditional: foreshadowing-resolve after foreshadowing-track (step 7b).
    if "foreshadowing-track" in step.skill:
        _check_conditional_resolve(state, project_dir, chapter)

    # After last core-circle audit: genre circle + boundary circle via audit_layer.
    if step.is_audit and step_idx == _LAST_AUDIT_IDX:
        gc_path = project_dir / "genre-config.json"
        gc: dict[str, object] = {}
        if gc_path.exists():
            gc = json.loads(gc_path.read_text(encoding="utf-8"))

        cs = _get_chapter_state(state, chapter)
        while True:
            audit_result = run_audit_layer(project_dir, chapter, gc)
            cs.audit_results["blocking_found"] = audit_result.blocking_found
            cs.audit_results["issues"] = audit_result.issues
            cs.audit_results["audit_reports"] = audit_result.audit_reports

            if not audit_result.blocking_found:
                log.info("audit_layer_passed", chapter=chapter)
                break

            cs.audit_retry_count += 1
            if not handle_audit_blocking(state, chapter, cs.audit_retry_count):
                log.error(
                    "audit_blocking_escalation",
                    chapter=chapter,
                    retries=cs.audit_retry_count,
                )
                set_checkpoint(
                    state,
                    CheckpointType.ESCALATION,
                    chapter=chapter,
                    context=(
                        f"Audit BLOCKING persists after {cs.audit_retry_count} "
                        f"revision attempts for chapter {chapter}"
                    ),
                )
                return True  # checkpoint raised, pause for human

            log.info(
                "audit_blocking_revision",
                chapter=chapter,
                retry=cs.audit_retry_count,
            )
            rev = dispatch_skill(
                "shenbi-chapter-revision",
                project_dir,
                f"Revise chapter {chapter} to fix audit BLOCKING issues.",
            )
            if not rev.success:
                return _handle_failure(state, step, chapter, "audit-revision", project_dir)

    # After review-resonance: parse score and run revision routing.
    if "review-resonance" in step.skill:
        # Parse resonance score from the audit report
        cs = _get_chapter_state(state, chapter)
        report_path = project_dir / _substitute_chapter("audits/chapter-N-resonance.md", chapter)
        cs.resonance_score = _parse_resonance_score(report_path)
        log.info(
            "resonance_score_parsed",
            chapter=chapter,
            score=cs.resonance_score,
        )

        _route_revision_after_resonance(state, project_dir, chapter)

    # Success: record, reset retries, advance.
    _record_step_done(state, step, chapter)
    _reset_retries(state, step, chapter)
    return _advance(state, step_idx, step, chapter)
