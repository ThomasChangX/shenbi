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
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from shenbi.contracts.paths import resolve_chapter_path
from shenbi.contracts.schemas.hooks import HookState, parse_hook_state

import yaml

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write
from shenbi.pipeline.audit_layer import run_audit_layer
from shenbi.pipeline.dispatch_helper import (
    dispatch_skill,
    requires_independent,
    run_gate_g3,
    run_gate_g4,
)
from shenbi.pipeline.machine import set_checkpoint
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
    SoftFailTracker,
)
from shenbi.status import GateStatus
from datetime import UTC

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
    # D20: snapshot-manage is handled inline by _snapshot_chapter_files, which
    # writes a timestamped flatfile snapshots/chapter-NNN-{ts}.md (never a
    # fixed path). The old output_path="snapshots/chapter-NNN/" was a fictional
    # directory that never existed on disk. Empty output_path = no single file.
    ChapterStep(
        19,
        "shenbi-snapshot-manage",
        "snapshot-manage",
        output_path="",
    ),
    ChapterStep(
        20,
        "shenbi-drift-guidance",
        "drift-guidance",
        output_path="truth/drift_guidance.md",
    ),
]

# 0-based index of the first core-circle audit step (for parallel dispatch trigger).
_FIRST_AUDIT_IDX = min(i for i, s in enumerate(CHAPTER_STEPS) if s.is_audit)

# 0-based index of the last core-circle audit step (for genre-circle trigger).
_LAST_AUDIT_IDX = max(i for i, s in enumerate(CHAPTER_STEPS) if s.is_audit)


# ---------------------------------------------------------------------------
# G4 Severity Classification (spec §11)
# ---------------------------------------------------------------------------


class G4Severity(StrEnum):
    """Classification of G4 validation failures."""

    HARD = "hard"
    SOFT = "soft"
    WARN = "warn"


G4_CHECK_MAP: dict[str, G4Severity] = {
    "not_found": G4Severity.HARD,
    "pre_check": G4Severity.HARD,
    "post_check": G4Severity.HARD,
    "meta": G4Severity.HARD,
    "word_count": G4Severity.HARD,
    "no_visual_scene": G4Severity.HARD,
    "content_overlap": G4Severity.HARD,
    "no_valid_verdict": G4Severity.HARD,
    "no_file_line_ref": G4Severity.HARD,
    "missing_cols": G4Severity.HARD,
    "missing_sections": G4Severity.HARD,
    "no_result": G4Severity.HARD,
    "no_evidence": G4Severity.HARD,
    "cp.sections": G4Severity.HARD,
    "cp.chapter_role": G4Severity.HARD,
    "cp.s7_hook_ops": G4Severity.HARD,
    "transition": G4Severity.SOFT,
    "fatigue": G4Severity.SOFT,
    "cd.chapter_end_hook": G4Severity.SOFT,
    "cp.golden": G4Severity.WARN,
    "cp.s5_choice": G4Severity.WARN,
}


def _classify_g4_failures(must_fix: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Partition G4 must_fix into (hard, soft, warn) by substring matching against G4_CHECK_MAP."""
    hard: list[str] = []
    soft: list[str] = []
    warn: list[str] = []
    for item in must_fix:
        matched = False
        for key, severity in G4_CHECK_MAP.items():
            if key in item:
                if severity == G4Severity.HARD:
                    hard.append(item)
                elif severity == G4Severity.SOFT:
                    soft.append(item)
                else:
                    warn.append(item)
                matched = True
                break
        if not matched:
            hard.append(item)  # conservative default
    return hard, soft, warn


def _extract_check_id(must_fix_item: str) -> str:
    """Extract the G4 check ID from a must_fix string like 'G4.transition:path:7>6'."""
    m = re.match(r"G4\.([a-z_.]+)", must_fix_item)
    return m.group(1) if m else must_fix_item.split(":", maxsplit=1)[0].replace("G4.", "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gate_passed(result: dict[str, Any]) -> bool:
    """True iff a gate result dict reports PASS (handles str and GateStatus)."""
    return str(result.get("status", "")) == GateStatus.PASS


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
    resolved = resolve_chapter_path(step.output_path, chapter)
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
    from shenbi.pipeline.error_handler import handle_dispatch_failure

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
    project_dir: Path | None = None,
) -> bool:
    """Bump the step cursor and set checkpoint if the step has one.

    Returns True if a checkpoint was raised or the chapter completed;
    False if the step simply advanced with no human action needed.

    Checkpoint suppression (--auto mode): when the corresponding config
    flag is False the checkpoint is silently skipped, staging files are
    auto-committed to their final paths, and the cursor advances as if
    it were a non-checkpoint step.
    """
    if project_dir is None:
        project_dir = Path(state.project_dir)

    state.chapter_loop.step_index = step_idx + 1
    state.chapter_loop.current_step = ""

    if step.checkpoint is not None:
        # Honour --auto suppression flags so automated runs aren't
        # blocked on every chapter-memo / state-settle.
        cfg = state.config
        if step.checkpoint == CheckpointType.CHAPTER_MEMO and not cfg.chapter_memo_review_required:
            # Auto mode: commit staging immediately since no human review
            from shenbi.pipeline.checkpoint import commit_staging

            target = resolve_chapter_path(step.output_path, chapter)
            try:
                commit_staging(project_dir, [target])
                log.info("staging_auto_committed", chapter=chapter, target=target)
            except FileNotFoundError:
                log.warning("staging_auto_commit_skipped_no_file", chapter=chapter, target=target)
            # Fall through to chapter-completion check (no checkpoint raised)
        elif (
            step.checkpoint == CheckpointType.STATE_SETTLE and not cfg.state_settle_review_required
        ):
            from shenbi.pipeline.checkpoint import STAGING_DIR

            staging_truth = project_dir / STAGING_DIR / "truth"
            if staging_truth.exists():
                for src in staging_truth.glob("*.md"):
                    dst = project_dir / "truth" / src.name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    safe_write(dst, src.read_bytes())
                log.info(
                    "staging_auto_committed_state_settle",
                    chapter=chapter,
                    files=len(list(staging_truth.glob("*.md"))),
                )
            else:
                log.warning("staging_auto_commit_skipped_no_truth", chapter=chapter)
            # Fall through to chapter-completion check (no checkpoint raised)
        else:
            artifact = (
                resolve_chapter_path(step.output_path, chapter)
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


def _run_context_curation(project_dir: Path, chapter: int) -> None:
    """Run deterministic context curation after assembly.

    Replaces the ``shenbi-context-composing`` LLM call (step 5) with
    deterministic Python operations: 9-section structuring, ending
    diversity check, and hook debt briefing generation.

    Curation failures are non-fatal: a warning is logged and the pipeline
    continues without curated context.
    """
    try:
        from shenbi.pipeline.context_curation import curate_context

        curated = curate_context(project_dir, chapter)
        log.info("context_curated", chapter=chapter, length=len(curated))
    except Exception as e:
        log.warning("context_curation_failed", chapter=chapter, error=str(e), exc_info=True)


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
    entries have a ``state`` field. State comparison goes through
    :func:`parse_hook_state` (fix D22): case-insensitive, and the
    non-canonical ``TRIGGER`` spelling folds to ``TRIGGERED``. Falls back to a
    text scan for ``state: TRIGGERED`` when frontmatter is absent or malformed.
    """
    # Try YAML frontmatter first.
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                hooks = fm.get("hooks", [])
                if isinstance(hooks, list):
                    return sum(
                        1
                        for h in hooks
                        if isinstance(h, dict)
                        and parse_hook_state(str(h.get("state", ""))) == HookState.TRIGGERED
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
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                score = fm.get("resonance_score")
                if isinstance(score, int):
                    return score
            except Exception:
                # YAML frontmatter parse error — score not retrievable from
                # this format, fall through to markdown-bold and plain-text patterns.
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


def _build_resonance_trend_row(chapter: int, overall: int) -> str:
    """Build a 7-column markdown table row for resonance_trend.md.

    Format MUST match what parse_resonance_scores
    (src/shenbi/orchestration/escalation_bridge.py:15-17) reads:
    lines starting with "|", split on "|", requires >=7 cells, reads
    cells[6] (7th column) as the overall score.

    Only the overall score (cs.resonance_score, an int) is available here;
    the upstream parser _parse_resonance_score (chapter_loop.py:667) returns
    int|None with no per-dimension breakdown. Columns without data use "-"
    placeholders so the column count stays at 7. Key column (cells[0]) is
    Ch{N} for key-based dedup.

    Column layout (split("|")[1:-1] yields exactly these cells):
        cells[0] = Ch{N}     (key)
        cells[1..5] = "-"    (placeholder dimensions)
        cells[6] = {overall} (7th column — what parse_resonance_scores reads)
    """
    return f"| Ch{chapter} | - | - | - | - | - | {overall} |"


# ---------------------------------------------------------------------------
# Adaptive triggering (spec §6.1 steps 9, 19-20 / Phase 4.2)
# ---------------------------------------------------------------------------


def _load_manifest(project_dir: Path) -> dict[str, Any]:
    """Load the snapshot manifest from ``snapshots/manifest.json``.

    Returns a dict with ``chapters`` (dict of chapter→filenames),
    ``last_recall_chapter``, and ``last_drift_chapter``. Returns an empty
    skeleton when the manifest file does not exist.
    """
    manifest_path = project_dir / "snapshots" / "manifest.json"
    if manifest_path.exists():
        return cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    return {"chapters": {}}


def _save_manifest(project_dir: Path, manifest: dict[str, Any]) -> None:
    """Persist the snapshot manifest to ``snapshots/manifest.json``."""
    manifest_path = project_dir / "snapshots" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    safe_write(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))


def _get_snapshot_retention(project_dir: Path) -> int:
    """Return the number of chapters of snapshots to retain.

    Defaults to 50 (matching ``PipelineConfig.snapshot_retention_chapters``).
    """
    return 50


def _get_last_recall_chapter(project_dir: Path) -> int | None:
    """Return the chapter number where recall last ran, or None."""
    manifest = _load_manifest(project_dir)
    return manifest.get("last_recall_chapter")


def _get_last_drift_chapter(project_dir: Path) -> int | None:
    """Return the chapter number where drift guidance last ran, or None."""
    manifest = _load_manifest(project_dir)
    return manifest.get("last_drift_chapter")


def _should_run_recall(project_dir: Path, chapter: int) -> bool:
    """Determine whether foreshadowing recall should run for *chapter*.

    Triggers when any of these conditions are met:

    1. Any hook's silence (``chapter - last_reinforced``) is within 3 chapters
       of its ``max_distance``.
    2. More than 5 hooks are in ``TRIGGERED`` state.
    3. More than 8 chapters have elapsed since the last recall run.
    """
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        return False

    # Lazy import to avoid circular dependency at module level.
    from shenbi.pipeline.context_curation import _read_pending_hooks

    hooks = _read_pending_hooks(project_dir)

    # Condition 2: >5 TRIGGERED hooks
    triggered_count = sum(
        1 for h in hooks if parse_hook_state(str(h.get("state", ""))) == HookState.TRIGGERED
    )
    if triggered_count > 5:
        log.info(
            "recall_triggered_by_triggered_count",
            chapter=chapter,
            triggered_count=triggered_count,
        )
        return True

    # Condition 1: any hook near max_distance
    for h in hooks:
        last_reinforced = h.get("last_reinforced", 0)
        max_dist = h.get("max_distance", 0)
        if max_dist <= 0:
            continue
        silence = chapter - last_reinforced
        if silence >= max_dist - 3:
            log.info(
                "recall_triggered_by_max_distance",
                chapter=chapter,
                hook_id=h.get("id", "?"),
                silence=silence,
                max_distance=max_dist,
            )
            return True

    # Condition 3: >8 chapters since last recall
    last = _get_last_recall_chapter(project_dir)
    if last is not None and chapter - last > 8:
        log.info(
            "recall_triggered_by_chapter_gap",
            chapter=chapter,
            last_recall=last,
            gap=chapter - last,
        )
        return True

    return False


def _get_recent_resonance_scores(project_dir: Path, chapter: int, window: int = 3) -> list[int]:
    """Collect resonance scores from the most recent *window* audit reports.

    Reads ``audits/chapter-N-resonance.md`` for chapters
    ``[chapter - window + 1, chapter]``. Missing or unparseable reports are
    skipped (returns whatever could be collected).
    """
    scores: list[int] = []
    for ch in range(max(1, chapter - window + 1), chapter + 1):
        report_path = project_dir / "audits" / f"chapter-{ch}-resonance.md"
        score = _parse_resonance_score(report_path)
        if score is not None:
            scores.append(score)
    return scores


def _should_run_drift(project_dir: Path, chapter: int) -> bool:
    """Determine whether drift guidance should run for *chapter*.

    Triggers when either:

    1. The 3-chapter resonance moving average drops more than 10 points
       compared to the previous window (0-100 scale).
    2. More than 12 chapters have elapsed since the last drift run.
    """
    # Condition 1: 3-chapter MA drop >10 points
    current_scores = _get_recent_resonance_scores(project_dir, chapter, window=3)
    prev_scores = _get_recent_resonance_scores(project_dir, chapter - 1, window=3)

    if len(current_scores) >= 3 and len(prev_scores) >= 3:
        current_ma = sum(current_scores) / len(current_scores)
        prev_ma = sum(prev_scores) / len(prev_scores)
        drop = prev_ma - current_ma
        if drop > 10:
            log.info(
                "drift_triggered_by_resonance_drop",
                chapter=chapter,
                current_ma=round(current_ma, 1),
                prev_ma=round(prev_ma, 1),
                drop=round(drop, 1),
            )
            return True

    # Condition 2: >12 chapters since last drift
    last = _get_last_drift_chapter(project_dir)
    if last is not None and chapter - last > 12:
        log.info(
            "drift_triggered_by_chapter_gap",
            chapter=chapter,
            last_drift=last,
            gap=chapter - last,
        )
        return True

    return False


def _prune_old_snapshots(project_dir: Path) -> None:
    """Remove snapshot files older than the retention window.

    Keeps only the most recent ``snapshot_retention_chapters`` worth of
    snapshots. Removes files from disk and updates the manifest.
    """
    retention = _get_snapshot_retention(project_dir)
    manifest = _load_manifest(project_dir)
    chapters_dict = manifest.get("chapters", {})

    all_chapters = sorted(int(k) for k in chapters_dict)
    if not all_chapters:
        return

    keep_from = max(all_chapters) - retention
    to_prune = [ch for ch in all_chapters if ch < keep_from]

    if not to_prune:
        return

    snap_dir = project_dir / "snapshots"
    for ch in to_prune:
        ch_key = str(ch)
        for filename in chapters_dict.get(ch_key, []):
            file_path = snap_dir / filename
            if file_path.exists():
                file_path.unlink()
        chapters_dict.pop(ch_key, None)

    _save_manifest(project_dir, manifest)
    log.info("snapshots_pruned", pruned=len(to_prune), retention=retention)


def _snapshot_chapter_files(project_dir: Path, chapter: int) -> None:
    """Create a timestamped file-based snapshot of chapter outputs.

    Copies chapter files, audit reports, and truth files into a single
    timestamped markdown file under ``snapshots/``. Updates the manifest
    and prunes old snapshots.

    This replaces the ``shenbi-snapshot-manage`` LLM dispatch with pure
    file operations — no git dependency.
    """
    from datetime import datetime

    snap_dir = project_dir / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    snap_filename = f"chapter-{chapter:03d}-{timestamp}.md"
    snap_path = snap_dir / snap_filename

    parts: list[str] = []

    # Chapter file
    chapter_file = project_dir / "chapters" / f"chapter-{chapter}.md"
    if chapter_file.exists():
        parts.append(f"## Chapter {chapter}\n\n{chapter_file.read_text(encoding='utf-8')}")

    # Audit files
    audit_dir = project_dir / "audits"
    if audit_dir.exists():
        for audit_file in sorted(audit_dir.glob(f"chapter-{chapter}-*.md")):
            parts.append(f"## Audit: {audit_file.stem}\n\n{audit_file.read_text(encoding='utf-8')}")

    # Truth files
    truth_dir = project_dir / "truth"
    if truth_dir.exists():
        for truth_file in sorted(truth_dir.glob("*.md")):
            parts.append(f"## Truth: {truth_file.name}\n\n{truth_file.read_text(encoding='utf-8')}")

    content = "\n\n---\n\n".join(parts) if parts else f"# Snapshot Chapter {chapter}\n\n(no files)"
    safe_write(snap_path, content.encode("utf-8"))

    # Update manifest
    manifest = _load_manifest(project_dir)
    chapter_key = str(chapter)
    manifest.setdefault("chapters", {})
    manifest["chapters"].setdefault(chapter_key, [])
    manifest["chapters"][chapter_key].append(snap_filename)
    _save_manifest(project_dir, manifest)

    log.info(
        "snapshot_created",
        chapter=chapter,
        file=snap_filename,
        size=len(content),
    )

    # Prune old snapshots
    _prune_old_snapshots(project_dir)


def _update_last_recall_manifest(project_dir: Path, chapter: int) -> None:
    """Record that recall ran at *chapter* in the manifest."""
    manifest = _load_manifest(project_dir)
    manifest["last_recall_chapter"] = chapter
    _save_manifest(project_dir, manifest)


def _update_last_drift_manifest(project_dir: Path, chapter: int) -> None:
    """Record that drift guidance ran at *chapter* in the manifest."""
    manifest = _load_manifest(project_dir)
    manifest["last_drift_chapter"] = chapter
    _save_manifest(project_dir, manifest)


def _should_run_step(step: ChapterStep, state: PipelineState, project_dir: Path) -> bool:
    """Determine whether *step* should execute based on adaptive triggering rules.

    Returns True if the step should execute normally (dispatch + gates).
    Returns False if the step should be skipped for this chapter.

    For ``shenbi-snapshot-manage``, the file-based snapshot is taken inline
    and the LLM dispatch is always skipped (returns False).
    """
    skill = step.skill
    chapter = state.chapter_loop.current_chapter

    if skill == "shenbi-foreshadowing-recall":
        return _should_run_recall(project_dir, chapter)

    if skill == "shenbi-drift-guidance":
        return _should_run_drift(project_dir, chapter)

    if skill == "shenbi-snapshot-manage":
        # Replace LLM dispatch with deterministic file-based snapshot.
        _snapshot_chapter_files(project_dir, chapter)
        return False

    # All other steps run unconditionally.
    return True


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


def _is_revision_routed(route: str | None) -> bool:
    """Check if a revision route was actually assigned.

    Returns True for any non-None route, including 'no_revision'.
    """
    return route is not None


def _ensure_revision_decisions_exists(
    project_dir: Path,
    chapter: int,
    state: PipelineState | None = None,
    log: Any = None,
) -> None:
    """Write a minimal revision decisions file if one does not exist.

    The file conforms to DecisionsDoc (extra="forbid"): $schema, skill,
    chapter, selections, adjustments, produced_at. The skip decision is
    documented in ``selections`` (not a ``route`` key). This ensures every
    chapter routed through revision (including no-revision) produces an
    audit-trail artifact.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Chapter number.
        state: Optional pipeline state for checking revision routing.
        log: Optional logger for recording fallback writes.
    """
    rev_path = project_dir / "chapters" / f"chapter-{chapter}-revision-decisions.json"
    if rev_path.exists():
        return

    if state is not None:
        ch_state = state.chapter_loop.chapter_states.get(str(chapter))
        route = ch_state.audit_results.get(_REVISION_ROUTE_KEY) if ch_state else None
        if not _is_revision_routed(route):
            return  # Chapter was never routed through revision

    from datetime import datetime

    min_decisions = {
        "$schema": "shenbi-decisions-v1",
        "skill": "shenbi-chapter-revision",
        "chapter": chapter,
        "selections": [
            {
                "target": "no_revision_needed",
                "selected": [],
                "basis": "arc_relevance",
                "severity": "low",
                "omitted": [],
            }
        ],
        "adjustments": [],  # empty = no changes made
        "produced_at": datetime.now(UTC).isoformat(),
    }
    safe_write(rev_path, json.dumps(min_decisions, ensure_ascii=False, indent=2))
    if log is not None:
        log.info("revision_decisions_fallback_written", chapter=chapter)


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

    # ── Parallel review dispatch (Task 7) ──────────────────────────────
    # When the first audit step is reached, dispatch all core-circle and
    # genre-circle reviews in two parallel waves instead of serial steps.
    if step_idx == _FIRST_AUDIT_IDX and step.is_audit:
        from shenbi.pipeline.parallel_dispatch import (
            ReviewTask,
            consolidate_review_results,
            dispatch_reviews_parallel,
        )
        from shenbi.pipeline.audit_layer import (
            audit_relative_path,
            audit_suffix,
            get_active_genre_audits,
        )
        from shenbi.pipeline.dispatch_helper import DispatchResult
        from shenbi.safe_write import safe_write

        # Wave 1: Core-circle reviews (7 skills in parallel)
        core_skills = [s.skill for s in CHAPTER_STEPS if s.is_audit and "review" in s.skill]
        core_tasks = [
            ReviewTask(
                skill=skill,
                project_dir=project_dir,
                prompt=f"Execute {skill} for chapter {chapter}. Project dir: {project_dir}",
                output_path=f"audits/chapter-{chapter}-{audit_suffix(skill)}.md",
            )
            for skill in core_skills
        ]
        log.info("parallel_review_wave1_start", chapter=chapter, count=len(core_tasks))
        core_results = dispatch_reviews_parallel(core_tasks)

        # Wave 2: Genre-circle reviews (conditionally active, in parallel)
        gc_path = project_dir / "genre-config.json"
        genre_gc = json.loads(gc_path.read_text(encoding="utf-8")) if gc_path.exists() else {}
        genre_skills = get_active_genre_audits(genre_gc)
        genre_tasks = [
            ReviewTask(
                skill=skill,
                project_dir=project_dir,
                prompt=f"Execute {skill} audit for chapter {chapter}.",
                output_path=audit_relative_path(chapter, skill),
            )
            for skill in genre_skills
        ]
        genre_results: list[DispatchResult] = []
        if genre_tasks:
            log.info("parallel_review_wave2_start", chapter=chapter, count=len(genre_tasks))
            genre_results = dispatch_reviews_parallel(genre_tasks)

        # Consolidate all results
        all_results = core_results + genre_results
        consolidated = consolidate_review_results(all_results, chapter)
        summary_path = project_dir / "audits" / f"chapter-{chapter}-review-summary.md"
        safe_write(summary_path, consolidated)

        # Record all review steps as done and advance past them
        for i in range(_FIRST_AUDIT_IDX, _LAST_AUDIT_IDX + 1):
            if i < len(CHAPTER_STEPS):
                _record_step_done(state, CHAPTER_STEPS[i], chapter)

        state.chapter_loop.step_index = _LAST_AUDIT_IDX + 1
        state.chapter_loop.current_step = ""

        # Check for blocking issues
        cs = _get_chapter_state(state, chapter)
        # The consolidated summary always contains "- **BLOCKING Issues**: N".
        # Only the "## BLOCKING Issues" H2 section is present when actual
        # blocking issues exist (see consolidate_review_results in parallel_dispatch.py).
        cs.audit_results["blocking_found"] = "## BLOCKING Issues" in consolidated
        cs.audit_results["audit_reports"] = [t.output_path for t in core_tasks + genre_tasks]

        _reset_retries(state, step, chapter)
        return _advance(
            state,
            _LAST_AUDIT_IDX,
            CHAPTER_STEPS[_LAST_AUDIT_IDX],
            chapter,
            project_dir=project_dir,
        )

    # Context assembly (step 4): materialize package before chapter-drafting.
    if step.calls_context_assembly:
        _run_context_assembly(project_dir, chapter)
        # Also run deterministic curation — replaces context-composing LLM call
        _run_context_curation(project_dir, chapter)

    # Pipeline-internal steps (not dispatched): advance without dispatch/G4.
    if step.skill.startswith("pipeline-"):
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter, project_dir=project_dir)

    # context-composing replaced by deterministic curation in step 4
    if step.skill == "shenbi-context-composing":
        log.info("context_composing_replaced_by_curation", chapter=chapter)
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter, project_dir=project_dir)

    # foreshadowing-plant replaced by deterministic YAML generation
    if step.skill == "shenbi-foreshadowing-plant":
        from shenbi.pipeline.hook_planting import plant_hooks_from_plan

        count = plant_hooks_from_plan(project_dir, chapter)
        log.info("foreshadowing_plant_replaced_by_deterministic", chapter=chapter, count=count)
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter, project_dir=project_dir)

    # Step 18 (chapter-revision) is conditional -- skip when routing decided
    # no revision is needed (spec §6.3, set during step 17 review-resonance).
    # Scoped to the revision skill ONLY: snapshot (step 19) and drift (step
    # 20) must always run regardless of the revision route.
    if step.skill == "shenbi-chapter-revision" and _is_revision_skipped(state, chapter):
        log.info("revision_step_skipped", chapter=chapter)
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        _ensure_revision_decisions_exists(project_dir, chapter, state, log)
        return _advance(state, step_idx, step, chapter, project_dir=project_dir)

    # Adaptive triggering: recall, drift, snapshot run only when data indicates need.
    if not _should_run_step(step, state, project_dir):
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        # Update manifest tracking for steps that were handled inline.
        if step.skill == "shenbi-snapshot-manage":
            pass  # snapshot already taken + manifest updated in _snapshot_chapter_files
        return _advance(state, step_idx, step, chapter, project_dir=project_dir)

    # Build dispatch prompt (staging steps write to staging/).
    prompt = f"Execute {step.skill} for chapter {chapter}. Project dir: {project_dir}"
    if step.uses_staging:
        prompt += " Write output to staging/ directory."

    # Inject MODIFY feedback if present (one-shot consumption)
    if state.chapter_loop.modify_feedback:
        prompt += (
            f"\n\nHuman review feedback (incorporate these changes): "
            f"{state.chapter_loop.modify_feedback}"
        )
        state.chapter_loop.modify_feedback = None

    # Inject prior G4 failure details as corrective feedback on retry
    retry_key = _retry_key(chapter, step.skill)
    prev_g4_feedback = state.chapter_loop.retry_feedback.get(retry_key)
    if prev_g4_feedback:
        prompt += (
            f"\n\n## CORRECTIVE FEEDBACK (prior attempt failed G4 validation)\n"
            f"Your previous output failed the structural check:\n"
            f"```\n{prev_g4_feedback}\n```\n"
            f"Fix these issues in your new output."
        )

    # Dispatch the skill.
    result = dispatch_skill(
        step.skill,
        project_dir,
        prompt,
        uses_staging=step.uses_staging,
    )

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
        must_fix = g4.get("must_fix", [])
        hard_fails, soft_fails, warn_fails = _classify_g4_failures(must_fix)

        # Edge case: G4 failed but must_fix was empty or all items unmatched.
        # Treat as a single generic HARD failure (conservative default).
        if not hard_fails and not soft_fails and not warn_fails:
            hard_fails = ["G4.generic_failure: (no must_fix details)"]

        for w in warn_fails:
            log.info("chapter_g4_warn", chapter=chapter, step=step.step_num, item=w)

        for s in soft_fails:
            tracker_key = _extract_check_id(s)
            tracker = state.chapter_loop.soft_fail_trackers.get(tracker_key)
            if tracker is None:
                tracker = SoftFailTracker(check_id=tracker_key)
                state.chapter_loop.soft_fail_trackers[tracker_key] = tracker
            should_escalate = tracker.record(chapter)
            log.warning(
                "chapter_g4_soft_fail",
                chapter=chapter,
                step=step.step_num,
                item=s,
                occurrences=len(tracker.occurrences),
            )
            if should_escalate:
                log.error(
                    "chapter_g4_soft_escalated",
                    chapter=chapter,
                    check_id=tracker_key,
                    occurrences=tracker.occurrences,
                )

        if hard_fails:
            state.chapter_loop.retry_feedback[retry_key] = (
                f"G4 HARD check failed: {hard_fails}\nFull result: {json.dumps(g4, default=str)}"
            )
            if state.config.per_chapter_review_enabled:
                return _handle_failure(state, step, chapter, "gate", project_dir)
            count = state.chapter_loop.retry_counts.get(retry_key, 0) + 1
            state.chapter_loop.retry_counts[retry_key] = count
            if count <= 1:
                log.info(
                    "chapter_g4_retry_auto_hard",
                    chapter=chapter,
                    step=step.step_num,
                    attempt=count,
                    hard_fails=hard_fails,
                )
                return False
            log.info("chapter_g4_continue_auto", chapter=chapter, step=step.step_num)
            state.chapter_loop.retry_counts.pop(retry_key, None)
        # No hard fails → fall through to advance

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
        while cs.audit_retry_count < 100:
            audit_result = run_audit_layer(project_dir, chapter, gc)
            cs.audit_results["blocking_found"] = audit_result.blocking_found
            cs.audit_results["issues"] = audit_result.issues
            cs.audit_results["audit_reports"] = audit_result.audit_reports

            if not audit_result.blocking_found:
                log.info("audit_layer_passed", chapter=chapter)
                break

            cs.audit_retry_count += 1
            from shenbi.pipeline.error_handler import handle_audit_blocking

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

        if cs.audit_retry_count >= 100:
            log.error(
                "audit_hard_cap_reached",
                chapter=chapter,
                retries=cs.audit_retry_count,
            )
            set_checkpoint(
                state,
                CheckpointType.ESCALATION,
                chapter=chapter,
                context=(
                    f"Audit revision hard cap (100) reached for chapter {chapter}. "
                    f"Manual review required."
                ),
            )
            return True

    # After review-resonance: parse score and run revision routing.
    if "review-resonance" in step.skill:
        # Parse resonance score from the audit report
        cs = _get_chapter_state(state, chapter)
        report_path = project_dir / resolve_chapter_path("audits/chapter-N-resonance.md", chapter)
        cs.resonance_score = _parse_resonance_score(report_path)
        log.info(
            "resonance_score_parsed",
            chapter=chapter,
            score=cs.resonance_score,
        )

        _route_revision_after_resonance(state, project_dir, chapter)

        # Persist to resonance_trend.md as a MARKDOWN TABLE ROW (not YAML).
        # _parse_resonance_score (chapter_loop.py:667) already ran and stored the
        # overall int in cs.resonance_score. Reuse it — do NOT re-parse.
        overall = cs.resonance_score  # int | None
        if overall is not None:
            from shenbi.pipeline.truth_io import write_truth_file

            trend_row = _build_resonance_trend_row(chapter, overall)
            write_truth_file(
                project_dir,
                "resonance_trend.md",
                trend_row,
                mode="upsert_markdown_row",
                key_field="chapter",  # dedup on first column (Ch{N})
            )
            log.info("resonance_score_persisted", chapter=chapter, overall=overall)

    # Success: record, reset retries, advance.
    _record_step_done(state, step, chapter)
    _reset_retries(state, step, chapter)

    # After chapter-revision step succeeds, ensure decisions file exists
    if "chapter-revision" in step.skill:
        _ensure_revision_decisions_exists(project_dir, chapter, state, log)

    # Update manifest tracking for adaptive steps that just ran.
    if step.skill == "shenbi-foreshadowing-recall":
        _update_last_recall_manifest(project_dir, chapter)
    elif step.skill == "shenbi-drift-guidance":
        _update_last_drift_manifest(project_dir, chapter)

    return _advance(state, step_idx, step, chapter, project_dir=project_dir)
