"""Integration test: genesis -> chapter-loop phase transition (Wave 5 Task 1).

Verifies the cross-module flow end-to-end through the CLI surface: the genesis
orchestrator runs all 17 steps to completion, fires the genesis-complete
checkpoint, and after a human ``approve`` the pipeline transitions into the
chapter loop (chapter 1) and advances until the chapter-memo checkpoint.

This is an integration test in spirit -- it drives the real genesis orchestrator
(``run_genesis_step`` x17), the checkpoint/review state machine, the phase
transition mutator (``transition_genesis_to_chapter_loop``), and the chapter-loop
entry -- but only the *external* subprocess boundaries (skill dispatch, G3/G4
gate CLIs) are mocked. The orchestrator logic under test is the real code.

NOTE on location: placed in ``tests/unit/pipeline/`` rather than the brief's
``tests/integration/pipeline/`` to honour the project-wide convention recorded
in the SDD progress ledger ("Tests in tests/unit/pipeline/") and to share the
``sample_seed_content`` fixture from the pipeline conftest.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from shenbi.pipeline.cli import main
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.genesis import GENESIS_STEPS
from shenbi.pipeline.machine import load_state
from shenbi.pipeline.state import (
    CheckpointType,
    GenesisState,
    PipelinePhase,
)

# Every genesis step passes G4; step 17 additionally passes G3.
_GATE_PASS = {"status": "PASS"}


@pytest.fixture
def seeded_project(tmp_path: Path, sample_seed_content: str) -> Path:
    """Initialize a novel project from a seed file, ready for genesis."""
    seed = tmp_path / "seed.md"
    seed.write_text(sample_seed_content, encoding="utf-8")
    project = tmp_path / "novel"
    assert main(["init", str(seed), "--project-dir", str(project)]) == 0
    return project


@pytest.fixture
def genesis_succeeds() -> Iterator[SimpleNamespace]:
    """Stub the four external boundaries genesis depends on so all 17 steps run.

    ``requires_independent`` returns True only for step 17
    (shenbi-foundation-review), matching the skill contract, so ``run_gate_g3``
    is exercised exactly once -- the same coverage the genesis unit tests use.
    Returns the started mocks so tests can assert call counts.
    """
    with ExitStack() as stack:
        dispatch = stack.enter_context(
            patch(
                "shenbi.pipeline.genesis.dispatch_skill",
                return_value=DispatchResult(True, 0, "{}", ""),
            )
        )
        g4 = stack.enter_context(
            patch("shenbi.pipeline.genesis.run_gate_g4", return_value=_GATE_PASS)
        )
        g3 = stack.enter_context(
            patch("shenbi.pipeline.genesis.run_gate_g3", return_value=_GATE_PASS)
        )
        req = stack.enter_context(
            patch(
                "shenbi.pipeline.genesis.requires_independent",
                side_effect=lambda skill: skill == "shenbi-foundation-review",
            )
        )
        yield SimpleNamespace(dispatch=dispatch, g4=g4, g3=g3, req=req)


@pytest.fixture
def chapter_loop_succeeds() -> Iterator[SimpleNamespace]:
    """Stub chapter-loop dispatch + G4 so the loop runs cleanly past entry.

    Only ``dispatch_skill`` and ``run_gate_g4`` are stubbed: the transition
    into chapter 1 only reaches steps 1-2 before the chapter-memo checkpoint
    stops the loop, and neither step requires an independent agent.
    """
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
        yield SimpleNamespace(dispatch=dispatch, g4=g4)


class TestGenesisCompletesAndCheckpoints:
    """Genesis runs all 17 steps and raises the genesis-complete checkpoint."""

    def test_genesis_runs_17_steps_and_fires_checkpoint(
        self, seeded_project: Path, genesis_succeeds: SimpleNamespace
    ) -> None:
        rc = main(["next", str(seeded_project)])

        assert rc == 0
        state = load_state(seeded_project)
        assert state.pending_checkpoint.type == CheckpointType.GENESIS_COMPLETE
        assert state.genesis.current_step == len(GENESIS_STEPS)
        # All 17 steps dispatched; G4 validated on every one of them.
        assert genesis_succeeds.dispatch.call_count == 17
        assert genesis_succeeds.g4.call_count == 17
        # G3 (independence) only on step 17, the requires_independent_agent skill.
        assert genesis_succeeds.g3.call_count == 1
        assert len(state.genesis.skills_done) == 17

    def test_skills_done_records_all_genesis_skills_in_order(
        self, seeded_project: Path, genesis_succeeds: SimpleNamespace
    ) -> None:
        main(["next", str(seeded_project)])

        state = load_state(seeded_project)
        assert state.genesis.skills_done == [s.skill for s in GENESIS_STEPS]

    def test_genesis_marks_checkpoint_pending_state(
        self, seeded_project: Path, genesis_succeeds: SimpleNamespace
    ) -> None:
        main(["next", str(seeded_project)])

        state = load_state(seeded_project)
        assert state.genesis.state == GenesisState.CHECKPOINT_PENDING
        # Checkpoint artifact points at the foundation-review output.
        assert state.pending_checkpoint.artifact == "foundation/review_report.md"

    def test_next_blocked_while_genesis_checkpoint_pending(
        self, seeded_project: Path, genesis_succeeds: SimpleNamespace
    ) -> None:
        # Run genesis to completion -> genesis-complete checkpoint pending.
        main(["next", str(seeded_project)])

        # A second `next` must be refused (checkpoint still pending).
        rc = main(["next", str(seeded_project)])

        assert rc != 0
        # No extra dispatch happened while blocked.
        assert genesis_succeeds.dispatch.call_count == 17

    def test_optional_step_runs_on_success(
        self, seeded_project: Path, genesis_succeeds: SimpleNamespace
    ) -> None:
        """Step 16 (anchor-curate) is optional but still dispatched on success."""
        main(["next", str(seeded_project)])

        state = load_state(seeded_project)
        # anchor-curate (step 16) ran and is recorded, not skipped.
        assert "shenbi-anchor-curate" in state.genesis.skills_done


class TestGenesisToChapterLoopTransition:
    """Genesis-complete approve -> chapter-loop entry transition flow."""

    def test_approve_transitions_to_chapter_loop(
        self,
        seeded_project: Path,
        genesis_succeeds: SimpleNamespace,
        chapter_loop_succeeds: SimpleNamespace,
    ) -> None:
        # 1. Run genesis to the genesis-complete checkpoint.
        assert main(["next", str(seeded_project)]) == 0

        # 2. Human approves the checkpoint.
        assert main(["review", str(seeded_project), "approve"]) == 0

        # 3. Resume transitions into the chapter loop and runs to the next
        #    checkpoint (chapter-memo, step 2 of chapter 1).
        rc = main(["resume", str(seeded_project)])

        assert rc == 0
        state = load_state(seeded_project)
        assert state.phase == PipelinePhase.CHAPTER_LOOP
        assert state.chapter_loop.current_chapter == 1
        assert state.genesis.state == GenesisState.COMPLETED

    def test_resume_advances_chapter_loop_to_chapter_memo(
        self,
        seeded_project: Path,
        genesis_succeeds: SimpleNamespace,
        chapter_loop_succeeds: SimpleNamespace,
    ) -> None:
        main(["next", str(seeded_project)])
        main(["review", str(seeded_project), "approve"])
        assert main(["resume", str(seeded_project)]) == 0

        state = load_state(seeded_project)
        # Chapter 1 advanced past step 1 (intent-management) and stopped at
        # step 2 (chapter-planning), which raises the chapter-memo checkpoint.
        assert state.chapter_loop.step_index == 2
        assert state.pending_checkpoint.type == CheckpointType.CHAPTER_MEMO
        assert state.pending_checkpoint.chapter == 1
        # Two chapter-loop steps were dispatched before the checkpoint.
        assert chapter_loop_succeeds.dispatch.call_count == 2

    def test_checkpoint_history_records_genesis_approval(
        self,
        seeded_project: Path,
        genesis_succeeds: SimpleNamespace,
        chapter_loop_succeeds: SimpleNamespace,
    ) -> None:
        main(["next", str(seeded_project)])
        main(["review", str(seeded_project), "approve"])
        main(["resume", str(seeded_project)])

        state = load_state(seeded_project)
        last = state.checkpoint_history[-1]
        assert last["type"] == "genesis-complete"
        assert last["decision"] == "approve"
