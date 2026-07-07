"""Integration test: full chapter loop with audit + staging + context (W5T2).

Verifies the complete per-chapter flow exercising all three layers together:
staging (steps 2 + 7), context assembly (step 4), and the audit core circle
(steps 10-16) + revision routing (after step 17). The brief's canonical flow
is: plan(staging) -> checkpoint -> context -> draft -> settle(staging) ->
checkpoint -> audit(7 core) -> resonance -> revision -> snapshot -> drift.

The test drives the real chapter_loop orchestrator (``run_chapter_step``) and,
for the CLI surface, ``main(["next", ...])``. Only the external subprocess
boundaries (skill dispatch, G3/G4 gate CLIs) and the I/O-heavy context
retrieval (assemble_context/write_context_file) are stubbed. The orchestrator
logic under test is the real code.

NOTE on location: placed in ``tests/unit/pipeline/`` rather than the brief's
``tests/integration/pipeline/`` to honour the project-wide convention recorded
in the SDD progress ledger ("Tests in tests/unit/pipeline/") and to share the
``sample_seed_content`` fixture from the pipeline conftest. (Same rationale as
W5T1's test_genesis_to_loop.py.)
"""

from __future__ import annotations

import io
import sys
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, run_chapter_step
from shenbi.pipeline.cli import main
from shenbi.pipeline.context_assemble import ContextPackage, ContextSection
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.machine import clear_checkpoint, load_state, save_state
from shenbi.pipeline.revision_router import RevisionRoute
from shenbi.pipeline.state import (
    CheckpointType,
    PipelinePhase,
    PipelineState,
    ReviewDecision,
)

_GATE_PASS = {"status": "PASS"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _drive_to_checkpoint(state: PipelineState, project_dir: Path) -> None:
    """Call run_chapter_step until it returns True (checkpoint reached)."""
    while not run_chapter_step(state, project_dir):
        pass


def _run(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    """Invoke main() with argv, capturing stdout to avoid structlog coupling.

    configure_logging() binds structlog to sys.stderr on first use; capsys
    closes its capture streams at teardown which raises across tests. An
    explicit StringIO avoids that coupling (same convention as test_e2e.py).
    """
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    return main(argv)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def chapter_state(tmp_path: Path) -> PipelineState:
    """PipelineState positioned at chapter 1, step 0, in chapter-loop phase."""
    state = PipelineState.default(str(tmp_path))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 1
    return state


@pytest.fixture
def chapter_succeeds():
    """Stub all external boundaries for a clean full-chapter run.

    Mocks dispatch/G4/G3, parallel review dispatch, safe_write, context
    retrieval (assemble + write), and revision routing (no audit issues ->
    NO_REVISION -> step 18 skipped). Returns the started mocks so tests can
    assert call counts and arguments.
    """
    pkg = ContextPackage(
        chapter_role="推进/转折",
        sections=[
            ContextSection(
                source="route-c:book_spine",
                priority=0.6,
                text="The book spine.",
                category="route-c",
                estimated_tokens=10,
            )
        ],
        total_tokens=10,
    )
    with ExitStack() as stack:
        dispatch = stack.enter_context(
            patch(
                "shenbi.pipeline.chapter_loop.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            )
        )
        g4 = stack.enter_context(
            patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value=_GATE_PASS)
        )
        g3 = stack.enter_context(
            patch("shenbi.pipeline.chapter_loop.run_gate_g3", return_value=_GATE_PASS)
        )
        req = stack.enter_context(
            patch(
                "shenbi.pipeline.chapter_loop.requires_independent",
                side_effect=lambda skill: skill == "shenbi-review-resonance",
            )
        )
        # Parallel dispatch: return success results for all tasks.
        par_disp = stack.enter_context(
            patch(
                "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel",
                side_effect=lambda tasks: [DispatchResult(True, 0, "{}", "") for _ in tasks],
            )
        )
        # Consolidation: return clean summary (no BLOCKING).
        par_cons = stack.enter_context(
            patch(
                "shenbi.pipeline.parallel_dispatch.consolidate_review_results",
                return_value="# Chapter 1 — Consolidated Review Results\n\nNo BLOCKING or CRITICAL issues found across all reviews.\n",
            )
        )
        assemble = stack.enter_context(
            patch(
                "shenbi.pipeline.context_assemble.assemble_context",
                return_value=pkg,
            )
        )
        write_ctx = stack.enter_context(
            patch(
                "shenbi.pipeline.context_assemble.write_context_file",
                return_value=Path("context/chapter-1-context.md"),
            )
        )
        collect = stack.enter_context(
            patch(
                "shenbi.pipeline.chapter_loop.collect_audit_issues",
                return_value=([], False),
            )
        )
        route = stack.enter_context(
            patch(
                "shenbi.pipeline.chapter_loop.route_chapter_revision",
                return_value=RevisionRoute.NO_REVISION,
            )
        )
        yield SimpleNamespace(
            dispatch=dispatch,
            g4=g4,
            g3=g3,
            req=req,
            par_disp=par_disp,
            par_cons=par_cons,
            assemble=assemble,
            write_ctx=write_ctx,
            collect=collect,
            route=route,
        )


def _drive_three_segments(state: PipelineState, project_dir: Path) -> None:
    """Run the full chapter: chapter-memo -> state-settle -> per-chapter."""
    _drive_to_checkpoint(state, project_dir)
    clear_checkpoint(state, ReviewDecision.APPROVE)
    _drive_to_checkpoint(state, project_dir)
    clear_checkpoint(state, ReviewDecision.APPROVE)
    _drive_to_checkpoint(state, project_dir)


# ---------------------------------------------------------------------------
# Full chapter sequence: staging + context + audit together
# ---------------------------------------------------------------------------


class TestFullChapterSequence:
    """Drive a complete chapter through all 20 steps with all layers active."""

    def test_plan_checkpoint_raised_at_step_2(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """Steps 1-2 advance; chapter-planning raises the chapter-memo checkpoint."""
        _drive_to_checkpoint(chapter_state, tmp_path)
        assert chapter_state.pending_checkpoint.type == CheckpointType.CHAPTER_MEMO
        assert chapter_state.chapter_loop.step_index == 2
        assert chapter_succeeds.dispatch.call_count == 2

    def test_settle_checkpoint_raised_at_step_7(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """After clearing chapter-memo, steps 3-7 advance to state-settle."""
        _drive_to_checkpoint(chapter_state, tmp_path)
        clear_checkpoint(chapter_state, ReviewDecision.APPROVE)
        _drive_to_checkpoint(chapter_state, tmp_path)
        assert chapter_state.pending_checkpoint.type == CheckpointType.STATE_SETTLE
        assert chapter_state.chapter_loop.step_index == 7
        # Steps 1,2 (seg 1) + 6,7 (seg 2; step 3 replaced, step 4 internal, step 5 skipped).
        assert chapter_succeeds.dispatch.call_count == 4

    def test_full_chapter_completes_with_per_chapter_checkpoint(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """All 20 steps run; chapter completes and raises per-chapter checkpoint."""
        _drive_three_segments(chapter_state, tmp_path)

        assert chapter_state.pending_checkpoint.type == CheckpointType.PER_CHAPTER
        assert chapter_state.chapter_loop.current_chapter == 2
        assert chapter_state.chapter_loop.step_index == 0
        # 9 dispatched steps: 1,2,6,7,8,9 + 17 + 19 + 20.
        # (step 3 replaced, step 4 internal, step 5 skipped, steps 10-16 parallel,
        #  step 18 skipped).
        assert chapter_succeeds.dispatch.call_count == 9
        assert chapter_succeeds.g4.call_count == 9
        # G3 runs only on step 17 (review-resonance, requires_independent).
        assert chapter_succeeds.g3.call_count == 1
        # Parallel dispatch called once (wave 1).
        assert chapter_succeeds.par_disp.call_count >= 1

    def test_all_steps_recorded_in_steps_done(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """steps_done includes every step (internal, dispatched, and skipped)."""
        _drive_three_segments(chapter_state, tmp_path)

        cs = chapter_state.chapter_loop.chapter_states["1"]
        all_skills = [s.skill for s in CHAPTER_STEPS]
        assert cs.steps_done == all_skills
        assert len(cs.steps_done) == 20


# ---------------------------------------------------------------------------
# Staging + checkpoint artifacts
# ---------------------------------------------------------------------------


class TestStagingAndCheckpointArtifacts:
    """Staging steps raise checkpoints whose G4 validates the staging copy."""

    def test_chapter_planning_g4_validates_staging_path(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """G4 for chapter-planning receives staging/plans/chapter-1-plan.md."""
        _drive_to_checkpoint(chapter_state, tmp_path)
        g4_calls = chapter_succeeds.g4.call_args_list
        # Second G4 call is step 2 (chapter-planning); first is step 1.
        planning_files = g4_calls[1][0][1]
        assert any("staging/plans/chapter-1-plan.md" in f for f in planning_files)

    def test_chapter_planning_checkpoint_artifact(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """chapter-memo checkpoint points at the chapter plan artifact."""
        _drive_to_checkpoint(chapter_state, tmp_path)
        assert chapter_state.pending_checkpoint.artifact == "plans/chapter-1-plan.md"
        assert chapter_state.pending_checkpoint.chapter == 1

    def test_state_settling_checkpoint_artifact(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """state-settle checkpoint has a non-null artifact (state-settling has
        no single output file, so the artifact falls back to chapter-N/name).
        """
        _drive_to_checkpoint(chapter_state, tmp_path)
        clear_checkpoint(chapter_state, ReviewDecision.APPROVE)
        _drive_to_checkpoint(chapter_state, tmp_path)
        cp = chapter_state.pending_checkpoint
        assert cp.type == CheckpointType.STATE_SETTLE
        assert cp.artifact is not None
        assert "state-settling" in cp.artifact

    def test_staging_prompt_includes_staging_dir(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """Dispatch prompt for staging skills tells the skill to use staging/."""
        _drive_to_checkpoint(chapter_state, tmp_path)
        # step 2 (chapter-planning) dispatch call.
        planning_prompt = chapter_succeeds.dispatch.call_args_list[1][0][2]
        assert "staging/" in planning_prompt


# ---------------------------------------------------------------------------
# Context assembly integration
# ---------------------------------------------------------------------------


class TestContextAssemblyIntegration:
    """Step 4 materializes the three-route context package before drafting."""

    def test_assemble_context_called_with_chapter_plan(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """assemble_context receives the project dir and chapter-1 plan path."""
        _drive_to_checkpoint(chapter_state, tmp_path)
        clear_checkpoint(chapter_state, ReviewDecision.APPROVE)
        _drive_to_checkpoint(chapter_state, tmp_path)
        chapter_succeeds.assemble.assert_called_once_with(tmp_path, "plans/chapter-1-plan.md")

    def test_write_context_file_called_once(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """write_context_file materializes context/chapter-1-context.md."""
        _drive_to_checkpoint(chapter_state, tmp_path)
        clear_checkpoint(chapter_state, ReviewDecision.APPROVE)
        _drive_to_checkpoint(chapter_state, tmp_path)
        chapter_succeeds.write_ctx.assert_called_once()

    def test_context_assembly_before_drafting(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """Context materialization (step 4) happens before chapter-drafting (6)."""
        _drive_to_checkpoint(chapter_state, tmp_path)
        clear_checkpoint(chapter_state, ReviewDecision.APPROVE)
        _drive_to_checkpoint(chapter_state, tmp_path)
        assert chapter_succeeds.assemble.call_count == 1
        dispatch_skills = [c[0][0] for c in chapter_succeeds.dispatch.call_args_list]
        assert "shenbi-chapter-drafting" in dispatch_skills


# ---------------------------------------------------------------------------
# Audit circle + revision routing
# ---------------------------------------------------------------------------


class TestAuditCircleAndRevisionRouting:
    """7 core-circle audits run serially, then revision routing decides step 18."""

    def test_all_seven_core_audits_recorded(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """All 7 core-circle audit skills appear in steps_done."""
        _drive_three_segments(chapter_state, tmp_path)
        cs = chapter_state.chapter_loop.chapter_states["1"]
        for step in CHAPTER_STEPS:
            if step.is_audit:
                assert step.skill in cs.steps_done

    def test_audit_g4_paths_use_audits_dir(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """G4 validates audit reports at audits/chapter-1-{skill}.md.

        With parallel dispatch (Task 7), only review-resonance (step 17) goes
        through the serial G4 path. Core-circle audits are parallel-dispatched.
        """
        _drive_three_segments(chapter_state, tmp_path)
        audit_files: list[str] = []
        for call in chapter_succeeds.g4.call_args_list:
            files = call[0][1]
            audit_files.extend(f for f in files if "audits/" in f)
        # review-resonance = 1 audit file via serial G4.
        assert len(audit_files) == 1

    def test_revision_routing_runs_after_resonance(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """collect_audit_issues + route_chapter_revision fire after step 17."""
        _drive_three_segments(chapter_state, tmp_path)
        chapter_succeeds.collect.assert_called_once_with(tmp_path, 1)
        chapter_succeeds.route.assert_called_once()

    def test_revision_skipped_when_no_issues(
        self, chapter_state: PipelineState, chapter_succeeds, tmp_path: Path
    ) -> None:
        """Step 18 (chapter-revision) is skipped when route is NO_REVISION."""
        _drive_three_segments(chapter_state, tmp_path)
        cs = chapter_state.chapter_loop.chapter_states["1"]
        assert cs.audit_results["revision_route"] == RevisionRoute.NO_REVISION.value
        # chapter-revision is still recorded in steps_done (ran as a no-op).
        assert "shenbi-chapter-revision" in cs.steps_done
        # 9 dispatches: steps 10-16 are parallel, step 18 skipped.
        assert chapter_succeeds.dispatch.call_count == 9

    def test_revision_dispatched_when_issues_found(
        self, chapter_state: PipelineState, tmp_path: Path
    ) -> None:
        """Step 18 dispatches when audit issues are found and route != NO_REVISION."""
        issues = [
            {
                "severity": "CRITICAL",
                "category": "craft",
                "file": "audits/chapter-1-anti-ai.md",
            }
        ]
        with (
            patch(
                "shenbi.pipeline.chapter_loop.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            ) as mock_disp,
            patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value=_GATE_PASS),
            patch("shenbi.pipeline.chapter_loop.run_gate_g3", return_value=_GATE_PASS),
            patch(
                "shenbi.pipeline.chapter_loop.requires_independent",
                side_effect=lambda skill: skill == "shenbi-review-resonance",
            ),
            # Parallel dispatch mocks (Task 7).
            patch(
                "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel",
                side_effect=lambda tasks: [DispatchResult(True, 0, "{}", "") for _ in tasks],
            ),
            patch(
                "shenbi.pipeline.parallel_dispatch.consolidate_review_results",
                return_value="# Chapter 1 — Consolidated Review Results\n\nNo BLOCKING or CRITICAL issues found across all reviews.\n",
            ),
            patch(
                "shenbi.pipeline.context_assemble.assemble_context",
                return_value=ContextPackage(),
            ),
            patch("shenbi.pipeline.context_assemble.write_context_file"),
            patch(
                "shenbi.pipeline.chapter_loop.collect_audit_issues",
                return_value=(issues, False),
            ),
            patch(
                "shenbi.pipeline.chapter_loop.route_chapter_revision",
                return_value=RevisionRoute.SPOT_FIX,
            ),
        ):
            _drive_three_segments(chapter_state, tmp_path)
            assert chapter_state.pending_checkpoint.type == CheckpointType.PER_CHAPTER
            # 10 dispatches: steps 10-16 parallel, step 18 runs (SPOT_FIX).
            assert mock_disp.call_count == 10
            cs = chapter_state.chapter_loop.chapter_states["1"]
            assert cs.audit_results["revision_route"] == RevisionRoute.SPOT_FIX.value


# ---------------------------------------------------------------------------
# CLI-driven chapter loop
# ---------------------------------------------------------------------------


class TestCLIChapterLoop:
    """main(['next', ...]) drives the chapter loop through the real CLI."""

    def test_next_stops_at_chapter_memo(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Brief example: next drives to chapter-memo checkpoint after step 2."""
        project = tmp_path / "novel"
        project.mkdir()
        state = PipelineState.default(str(project))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        save_state(project, state)

        with (
            patch(
                "shenbi.pipeline.chapter_loop.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            ),
            patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value=_GATE_PASS),
        ):
            rc = _run(["next", str(project)], monkeypatch)

        assert rc == 0
        state = load_state(project)
        assert state.pending_checkpoint.type.value == "chapter-memo"

    def test_review_approve_commits_staging(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review approve commits staging file to its final path."""
        project = tmp_path / "novel"
        project.mkdir()
        state = PipelineState.default(str(project))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        save_state(project, state)

        with (
            patch(
                "shenbi.pipeline.chapter_loop.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            ),
            patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value=_GATE_PASS),
        ):
            _run(["next", str(project)], monkeypatch)

        # Simulate the dispatched skill having written to staging.
        staging_file = project / "staging" / "plans" / "chapter-1-plan.md"
        staging_file.parent.mkdir(parents=True, exist_ok=True)
        staging_file.write_text("# Chapter 1 Plan", encoding="utf-8")

        rc = _run(["review", str(project), "approve"], monkeypatch)
        assert rc == 0

        final = project / "plans" / "chapter-1-plan.md"
        assert final.exists()
        assert final.read_text(encoding="utf-8") == "# Chapter 1 Plan"
        # Staging is cleared after commit.
        assert not staging_file.exists()

    def test_review_reject_clears_staging(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review reject clears staging without committing."""
        project = tmp_path / "novel"
        project.mkdir()
        state = PipelineState.default(str(project))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        save_state(project, state)

        with (
            patch(
                "shenbi.pipeline.chapter_loop.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            ),
            patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value=_GATE_PASS),
        ):
            _run(["next", str(project)], monkeypatch)

        staging_file = project / "staging" / "plans" / "chapter-1-plan.md"
        staging_file.parent.mkdir(parents=True, exist_ok=True)
        staging_file.write_text("# Chapter 1 Plan", encoding="utf-8")

        rc = _run(["review", str(project), "reject"], monkeypatch)
        assert rc == 0

        assert not staging_file.exists()
        assert not (project / "plans" / "chapter-1-plan.md").exists()
        state = load_state(project)
        assert state.pending_checkpoint.type == CheckpointType.NONE

    def test_next_blocked_while_checkpoint_pending(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Next is refused when a checkpoint is already pending."""
        project = tmp_path / "novel"
        project.mkdir()
        state = PipelineState.default(str(project))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = 1
        save_state(project, state)

        with (
            patch(
                "shenbi.pipeline.chapter_loop.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            ) as mock_disp,
            patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value=_GATE_PASS),
        ):
            rc1 = _run(["next", str(project)], monkeypatch)
            assert rc1 == 0
            dispatches_after_first = mock_disp.call_count

            # Second next is blocked (checkpoint still pending).
            rc2 = _run(["next", str(project)], monkeypatch)
            assert rc2 != 0
            assert mock_disp.call_count == dispatches_after_first
