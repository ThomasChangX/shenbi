"""Complete deterministic trigger system. Spec sections 6.4-6.6.

Determines which periodic/conditional skills fire after each chapter
completes, and provides ordered execution for each trigger category.

Trigger categories (spec section 6.4)::

    if N % 12 == 0:
        -> memory-distill L2 (arc distillation)
        -> score-arc (arc scoring, G3)
        -> style-learning (periodic update)

    if N % 36 == 0:
        -> memory-distill L4 (stratum distillation) -- FIRST  [I14]
        -> score-stratum (stratum scoring, G3)       -- SECOND [I14]

    if is_volume_boundary(N):
        -> foreshadowing-resolve
        -> volume-consolidation L3
        -> review-arc-payoff
        -> score-volume (G3)
        -> memory-distill L5 (book spine rolling review)
        -> style-learning (volume-level update)
        -> drift-guidance volume-level
        -> volume boundary expansion (section 6.5)
        -> [CHECKPOINT: volume-boundary]
        -> snapshot-manage (volume-boundary full snapshot)

    if N == total_chapters:
        -> book_closure (transition to Phase 3)

Write-order constraint [I14]: when ch%36 and volume_boundary both fire,
memory-distill L4 writes data fields first, then score-stratum writes
diagnostic fields. This is enforced by the ordered step list produced by
:func:`get_trigger_steps`.

Genre-config runtime update (section 6.6): when the same drift warning
has been propagated >= :data:`DRIFT_THRESHOLD` times and
``config.genre_config_update_on_drift`` is True, the trigger fires.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import dispatch_skill, run_gate_g4
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.state import CheckpointType, PipelineState
from shenbi.safe_write import safe_write
from shenbi.status import GateStatus

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Intervals (spec section 6.4)
# ---------------------------------------------------------------------------

#: Arc-cycle interval: memory-distill L2 + score-arc + style-learning.
STYLE_INTERVAL = 12

#: Stratum-cycle interval: memory-distill L4 + score-stratum.
STRATUM_INTERVAL = 36

#: Genre-config drift threshold (section 6.6): same warning propagated
#: this many times triggers a genre-config update.
DRIFT_THRESHOLD = 3

#: Path to the volume map (relative to project_dir).
VOLUME_MAP_PATH = "outline/volume_map.md"

#: Path to the audit drift log (relative to project_dir, section 6.7).
AUDIT_DRIFT_PATH = "truth/audit_drift.md"


# ---------------------------------------------------------------------------
# Trigger result
# ---------------------------------------------------------------------------


@dataclass
class TriggerResult:
    """Which triggers fire for a given chapter (spec section 6.4-6.6).

    All fields default to False; :func:`check_triggers` sets them.
    """

    l2_distill: bool = False
    l4_distill: bool = False
    volume_boundary: bool = False
    style_learning: bool = False
    book_closure: bool = False
    score_arc: bool = False
    score_stratum: bool = False
    score_volume: bool = False
    genre_config_update: bool = False

    def any_triggered(self) -> bool:
        """True if any trigger flag is set."""
        return any(
            getattr(self, f)
            for f in (
                "l2_distill",
                "l4_distill",
                "volume_boundary",
                "style_learning",
                "book_closure",
                "score_arc",
                "score_stratum",
                "score_volume",
                "genre_config_update",
            )
        )


@dataclass
class TriggerStep:
    """One triggered skill execution (spec section 6.4-6.5).

    Attributes:
        skill: Full ``shenbi-*`` skill name.
        mode: Dispatch hint (e.g. ``"L2"``, ``"L4"``, ``"L5"``, ``"expand"``).
        output_path: Expected output relative to project_dir (for G4).
        requires_g3: Whether to run G3 (scoring independence) after dispatch.
        category: Which trigger category this step belongs to. Used by the
            volume-boundary logic to raise a checkpoint at the end.
    """

    skill: str
    mode: str = ""
    output_path: str = ""
    requires_g3: bool = False
    category: str = ""


# ---------------------------------------------------------------------------
# Ordered trigger step table
#
# Each entry maps a TriggerResult flag to the skills that should execute when
# that flag is True. The list is pre-ordered to satisfy [I14] and the spec's
# section ordering (arc-cycle before stratum-cycle before volume-boundary).
# ---------------------------------------------------------------------------

TRIGGER_STEPS: list[TriggerStep] = [
    # Arc-cycle (ch%12) -- L2 distill before score-arc.
    TriggerStep(
        skill="shenbi-memory-distill",
        mode="L2",
        output_path="truth/arcs/arc-N.md",
        category="l2_distill",
    ),
    TriggerStep(
        skill="shenbi-score-arc",
        output_path="audits/arc-N-score.md",
        requires_g3=True,
        category="score_arc",
    ),
    # Stratum-cycle (ch%36) -- L4 distill BEFORE score-stratum [I14].
    TriggerStep(
        skill="shenbi-memory-distill",
        mode="L4",
        output_path="truth/book_strata.md",
        category="l4_distill",
    ),
    TriggerStep(
        skill="shenbi-score-stratum",
        output_path="audits/stratum-N-score.md",
        requires_g3=True,
        category="score_stratum",
    ),
    # Style-learning (periodic, ch%12 or volume boundary).
    TriggerStep(
        skill="shenbi-style-learning",
        output_path="style/style_profile.md",
        category="style_learning",
    ),
    # Volume-boundary skills (section 6.4 volume block + 6.5 expansion).
    TriggerStep(
        skill="shenbi-foreshadowing-resolve",
        output_path="truth/pending_hooks.md",
        category="volume_boundary",
    ),
    TriggerStep(
        skill="shenbi-volume-consolidation",
        mode="L3",
        output_path="truth/volume_summaries.md",
        category="volume_boundary",
    ),
    TriggerStep(
        skill="shenbi-review-arc-payoff",
        output_path="audits/volume-N-payoff.md",
        category="volume_boundary",
    ),
    TriggerStep(
        skill="shenbi-score-volume",
        output_path="audits/volume-N-score.md",
        requires_g3=True,
        category="score_volume",
    ),
    TriggerStep(
        skill="shenbi-memory-distill",
        mode="L5",
        output_path="truth/book_spine.md",
        category="volume_boundary",
    ),
    # Style-learning within the volume block (spec section 6.4 position 6:
    # score-volume -> memory-distill L5 -> style-learning -> drift-guidance).
    TriggerStep(
        skill="shenbi-style-learning",
        output_path="style/style_profile.md",
        category="volume_boundary",
    ),
    TriggerStep(
        skill="shenbi-drift-guidance",
        mode="volume",
        output_path="truth/drift_guidance.md",
        category="volume_boundary",
    ),
    # Volume-boundary expansion (section 6.5: progressive creation).
    TriggerStep(
        skill="shenbi-character-design",
        mode="expand",
        output_path="characters/",
        category="volume_boundary",
    ),
    TriggerStep(
        skill="shenbi-faction-builder",
        output_path="world/factions.md",
        category="volume_boundary",
    ),
    TriggerStep(
        skill="shenbi-location-builder",
        output_path="world/locations.md",
        category="volume_boundary",
    ),
    TriggerStep(
        skill="shenbi-relationship-map",
        output_path="characters/relationships.md",
        category="volume_boundary",
    ),
    TriggerStep(
        skill="shenbi-foreshadowing-plant",
        mode="expand",
        output_path="truth/pending_hooks.md",
        category="volume_boundary",
    ),
    TriggerStep(
        skill="shenbi-plot-thread-weaver",
        output_path="outline/thread_map.md",
        category="volume_boundary",
    ),
    # Genre-config runtime update (section 6.6).
    TriggerStep(
        skill="shenbi-genre-config",
        output_path="genre-config.json",
        category="genre_config_update",
    ),
]


# ---------------------------------------------------------------------------
# Volume-boundary detection
# ---------------------------------------------------------------------------

# Match "Chapter Start: N", "Chapter End: N", "Start: N", "End: N", or
# "Chapter N-M" / "Chapters N-M" / "N-M" patterns in volume sections.
_END_RE = re.compile(
    r"(?:chapter\s*)?(?:end|chapter_end|end_chapter)\s*[:\uff1a]\s*(\d+)",
    re.IGNORECASE,
)
_RANGE_RE = re.compile(
    r"chapters?\s*(\d+)\s*[-\u2013\u2014~\u301c]\s*(\d+)",
    re.IGNORECASE,
)


def read_volume_boundaries(project_dir: Path | str) -> set[int]:
    """Parse ``outline/volume_map.md`` and return last-chapter numbers per volume.

    Supports two markdown formats:

    1. Section with ``Chapter End: N`` (or ``End: N``).
    2. ``Chapters N-M`` range notation.

    Returns an empty set if the file does not exist or cannot be parsed.
    """
    if not project_dir:
        raise ValueError("read_volume_boundaries: project_dir is required")
    project_dir = Path(project_dir)
    vm_file = project_dir / VOLUME_MAP_PATH
    if not vm_file.exists():
        return set()

    text = vm_file.read_text(encoding="utf-8")
    boundaries: set[int] = set()

    # Try "Chapter End: N" patterns first.
    for m in _END_RE.finditer(text):
        boundaries.add(int(m.group(1)))

    # Fall back to "Chapters N-M" ranges.
    if not boundaries:
        for m in _RANGE_RE.finditer(text):
            boundaries.add(int(m.group(2)))

    return boundaries


def is_volume_boundary(chapter: int, project_dir: Path | str) -> bool:
    """True if *chapter* is the last chapter of any volume."""
    return chapter in read_volume_boundaries(project_dir)


# ---------------------------------------------------------------------------
# Genre-config drift detection (section 6.6)
# ---------------------------------------------------------------------------

_WARNING_RE = re.compile(
    r"(?:warning|drift|fatigue)\s*[:\uff1a]\s*(.+)",
    re.IGNORECASE,
)


def check_genre_config_drift(project_dir: Path | str) -> bool:
    """True if the same drift warning has propagated >= :data:`DRIFT_THRESHOLD` times.

    Reads ``truth/audit_drift.md`` (section 6.7 rolling window) and counts
    repeated warning strings. Returns False if the file is missing or no
    warning reaches the threshold.
    """
    if not project_dir:
        raise ValueError("check_genre_config_drift: project_dir is required")
    project_dir = Path(project_dir)
    drift_file = project_dir / AUDIT_DRIFT_PATH
    if not drift_file.exists():
        return False

    text = drift_file.read_text(encoding="utf-8")
    warnings: list[str] = []
    for m in _WARNING_RE.finditer(text):
        warnings.append(m.group(1).strip())

    if not warnings:
        return False

    counts = Counter(warnings)
    return any(c >= DRIFT_THRESHOLD for c in counts.values())


# ---------------------------------------------------------------------------
# Total chapters recompute (A1)
# ---------------------------------------------------------------------------


def _count_total_chapters(project_dir: Path) -> int:
    """Parse volume_map.md and sum all volume chapter counts."""
    vmap = project_dir / "truth" / "volume_map.md"
    if not vmap.exists():
        return 0
    text = vmap.read_text(encoding="utf-8")

    total = 0
    for m in re.finditer(r"(?:章节数|Chapters?)\s*:\s*(\d+)", text):
        total += int(m.group(1))
    return total if total > 0 else 0


def _update_total_chapters(state: PipelineState) -> None:
    """Recompute novel.json.total_chapters from volume_map.md.

    Called after volume boundary expansion to ensure the chapter-loop
    termination condition is accurate.
    """
    project_dir = Path(state.project_dir)
    new_total = _count_total_chapters(project_dir)
    if new_total < 1:
        return

    novel_json = project_dir / "novel.json"
    if not novel_json.exists():
        return

    data = json.loads(novel_json.read_text(encoding="utf-8"))
    old_total = data.get("total_chapters", 0)
    if new_total != old_total:
        data["total_chapters"] = new_total
        safe_write(novel_json, json.dumps(data, ensure_ascii=False, indent=2))
        log.info("total_chapters_updated", old=old_total, new=new_total)


# ---------------------------------------------------------------------------
# Public API: check_triggers
# ---------------------------------------------------------------------------


def check_triggers(state: PipelineState, chapter: int, total_chapters: int) -> TriggerResult:
    """Determine which triggers fire after *chapter* (spec section 6.4-6.6).

    Pure detection function: returns a :class:`TriggerResult` with all
    applicable flags set. Does not dispatch any skills.

    Args:
        state: Current pipeline state (project_dir used for volume-map reading).
        chapter: 1-based chapter number just completed.
        total_chapters: From ``novel.json.total_chapters`` (dynamic, section 4.2).
    """
    r = TriggerResult()

    # Arc-cycle (ch%12).
    if chapter > 0 and chapter % STYLE_INTERVAL == 0:
        r.l2_distill = True
        r.score_arc = True
        r.style_learning = True

    # Stratum-cycle (ch%36) -- [I14]: L4 before score-stratum in execution.
    if chapter > 0 and chapter % STRATUM_INTERVAL == 0:
        r.l4_distill = True
        r.score_stratum = True

    # Volume boundary (from volume_map.md).
    if chapter > 0:
        project_dir = Path(state.project_dir)
        if is_volume_boundary(chapter, project_dir):
            r.volume_boundary = True
            r.score_volume = True
            r.style_learning = True

    # Genre-config drift (section 6.6).
    if state.config.genre_config_update_on_drift:
        project_dir = Path(state.project_dir)
        if check_genre_config_drift(project_dir):
            r.genre_config_update = True

    # Book closure (last chapter or beyond).
    if chapter >= total_chapters:
        r.book_closure = True

    return r


# ---------------------------------------------------------------------------
# Execution order helper
# ---------------------------------------------------------------------------


def get_trigger_steps(result: TriggerResult) -> list[TriggerStep]:
    """Return the ordered list of skills to execute for *result*.

    Filters :data:`TRIGGER_STEPS` by the flags set in *result*, preserving
    the pre-defined order. This enforces [I14] (memory-distill L4 before
    score-stratum) and the spec's section ordering.

    ``shenbi-style-learning`` has two table entries: a periodic one
    (``category="style_learning"``, for the ch%12 arc-cycle) and a
    volume-boundary one (``category="volume_boundary"``, positioned after
    memory-distill L5 and before drift-guidance per spec section 6.4). When a
    volume boundary fires, the periodic entry is suppressed so style-learning
    runs exactly once, at the volume-block position.
    """
    active_flags = {
        f
        for f in (
            "l2_distill",
            "l4_distill",
            "volume_boundary",
            "style_learning",
            "score_arc",
            "score_stratum",
            "score_volume",
            "genre_config_update",
        )
        if getattr(result, f)
    }
    # Volume boundary: style-learning is handled by the volume_boundary entry
    # at the correct block position; drop the standalone periodic entry so the
    # skill fires once (spec section 6.4).
    if result.volume_boundary:
        active_flags.discard("style_learning")
    return [step for step in TRIGGER_STEPS if step.category in active_flags]


# ---------------------------------------------------------------------------
# Gate result helper
# ---------------------------------------------------------------------------


def _gate_passed(result: dict[str, Any]) -> bool:
    """True iff a gate result dict reports PASS or SKIP."""
    status = str(result.get("status", ""))
    return status in (GateStatus.PASS, GateStatus.SKIP)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def run_triggered_skills(
    state: PipelineState,
    project_dir: Path | str,
    chapter: int,
    result: TriggerResult,
) -> bool:
    """Execute all triggered skills in spec-defined order.

    Dispatches each triggered skill, runs G4 (and G3 for scoring skills),
    and on success advances. Returns True if a checkpoint was raised
    (volume boundary), False otherwise. Stops on first dispatch/gate
    failure; the caller can retry.

    Return semantics (I1 fix): True means all triggered skills completed
    successfully (checkpoint may or may not have been raised -- check
    ``is_at_checkpoint``). False means at least one skill failed, or no
    triggers were active. The caller must check the return value to avoid
    silently swallowing failures.

    For a volume boundary the snapshot-manage dispatch is NOT performed here:
    it is deferred to the caller, which runs it only after the human reviews
    and clears the checkpoint (spec section 6.4: [CHECKPOINT] -> snapshot).
    Use :func:`volume_snapshot_pending` to detect that a snapshot is owed.

    Mutates ``state`` in place; the caller persists it.
    """
    if not project_dir:
        raise ValueError("run_triggered_skills: project_dir is required")
    project_dir = Path(project_dir)
    steps = get_trigger_steps(result)

    if not steps:
        return False

    log.info(
        "triggered_skills_start",
        chapter=chapter,
        step_count=len(steps),
        flags=[f for f in dir(result) if not f.startswith("_") and getattr(result, f)],
    )

    for step in steps:
        mode_hint = f" Mode: {step.mode}." if step.mode else ""
        prompt = (
            f"Execute {step.skill} for chapter {chapter}.{mode_hint} Project dir: {project_dir}"
        )

        disp = dispatch_skill(step.skill, project_dir, prompt)
        if not disp.success:
            log.error(
                "trigger_dispatch_failed",
                chapter=chapter,
                skill=step.skill,
                mode=step.mode,
            )
            if hasattr(disp, "stderr") and disp.stderr:
                log.error("trigger_stderr", skill=step.skill, stderr_preview=disp.stderr[:2000])
            if hasattr(disp, "returncode"):
                log.error("trigger_rc", skill=step.skill, rc=disp.returncode)
            return False

        g4_file = step.output_path if step.output_path else ""
        g4 = run_gate_g4(step.skill, [g4_file] if g4_file else [], project_dir)
        if not _gate_passed(g4):
            log.error(
                "trigger_g4_failed",
                chapter=chapter,
                skill=step.skill,
                g4=g4,
            )
            return False

        if step.requires_g3:
            from shenbi.pipeline.dispatch_helper import run_gate_g3

            g3 = run_gate_g3(step.skill, project_dir)
            if not _gate_passed(g3):
                log.error(
                    "trigger_g3_failed",
                    chapter=chapter,
                    skill=step.skill,
                )
                return False

        log.info(
            "trigger_step_done",
            chapter=chapter,
            skill=step.skill,
            mode=step.mode,
        )

    # After volume boundary expansion: recompute total_chapters from volume_map
    if result.volume_boundary:
        _update_total_chapters(state)

    # Volume-boundary: raise checkpoint. The snapshot-manage dispatch is
    # deferred to the caller so it runs AFTER the checkpoint is cleared (spec
    # section 6.4: [CHECKPOINT: volume-boundary] -> snapshot-manage). The
    # pending VOLUME_BOUNDARY checkpoint is the signal that a snapshot is owed;
    # see :func:`volume_snapshot_pending`.
    if result.volume_boundary:
        set_checkpoint(
            state,
            CheckpointType.VOLUME_BOUNDARY,
            chapter=chapter,
            artifact="truth/book_spine.md",
            context=(
                f"Volume boundary at chapter {chapter}. Review volume scores, "
                f"expansion, and drift before proceeding. The volume snapshot "
                f"(snapshot-manage) runs after this checkpoint is cleared."
            ),
        )
        return True

    return True


def volume_snapshot_pending(state: PipelineState) -> bool:
    """True when a volume-boundary snapshot awaits checkpoint clearance.

    The caller dispatches ``shenbi-snapshot-manage`` only after the human
    reviews and clears the volume-boundary checkpoint (spec section 6.4,
    Important #2). Until then the snapshot must not run. This helper lets the
    orchestrator (chapter loop / phase transition) detect that a snapshot is
    owed and perform it post-approval.
    """
    return state.pending_checkpoint.type == CheckpointType.VOLUME_BOUNDARY
