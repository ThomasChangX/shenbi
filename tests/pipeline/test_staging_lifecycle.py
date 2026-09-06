"""C30 R1 staging lifecycle: checkpoint-preservation predicate + MODIFY discard.

Spec #44 (F318/F323): staged products that have entered a checkpoint must
survive the emergency (atexit) staging clear; only products that never
entered a checkpoint are temporary. Explicit review decisions (reject /
modify-baseline) clear everything through one audited predicate.
"""

from pathlib import Path

import pytest

from shenbi.pipeline.checkpoint import (
    clear_staging,
    commit_staging,
    discard_staging,
    mark_staging_checkpointed,
    staging_checkpointed_targets,
    staging_path,
)

PLAN_TARGET = "plans/chapter-1-plan.md"
SIDECAR_TARGET = "plans/chapter-1-plan-decisions.json"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    plan = tmp_path / "staging" / "plans"
    plan.mkdir(parents=True)
    src = Path("tests/fixtures/chapter-plan-example.md")
    (plan / "chapter-1-plan.md").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (plan / "chapter-1-plan-decisions.json").write_text(
        Path("tests/fixtures/decisions/valid-chapter-decisions.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return tmp_path


def test_uncheckpointed_staging_cleared_emergency(project: Path) -> None:
    clear_staging(project, preserve_checkpointed=True)
    assert not staging_path(project, PLAN_TARGET).exists()


def test_checkpointed_staging_survives_emergency(project: Path) -> None:
    targets = [PLAN_TARGET, SIDECAR_TARGET]
    mark_staging_checkpointed(project, targets)
    clear_staging(project, preserve_checkpointed=True)
    assert staging_path(project, PLAN_TARGET).exists()
    assert staging_path(project, SIDECAR_TARGET).exists()
    assert staging_checkpointed_targets(project) == set(targets)


def test_marker_survives_new_process_simulated_crash(project: Path) -> None:
    # Cross-process predicate: the marker round-trips through the on-disk
    # JSON (json.dumps -> json.loads), which is what a new process reads.
    mark_staging_checkpointed(project, [PLAN_TARGET])
    assert staging_checkpointed_targets(project) == {PLAN_TARGET}


def test_state_settle_marking_covers_all_staged_truth(project: Path) -> None:
    """C1: STATE_SETTLE marking mirrors the commit glob (truth/*.md), not just sidecars."""
    from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, _mark_staged_for_checkpoint

    truth = project / "staging" / "truth"
    truth.mkdir(parents=True)
    (truth / "pending_hooks.md").write_text("# hooks\n", encoding="utf-8")
    (truth / "current_state.md").write_text("# state\n", encoding="utf-8")
    settling_step = next(s for s in CHAPTER_STEPS if s.skill == "shenbi-state-settling")
    _mark_staged_for_checkpoint(project, settling_step, 1)
    marked = staging_checkpointed_targets(project)
    assert "truth/pending_hooks.md" in marked
    assert "truth/current_state.md" in marked


def test_resume_residual_cleanup_preserves_checkpointed(project: Path) -> None:
    """C2: resume-time residual cleanup must not wipe emergency survivors."""
    from shenbi.pipeline.chapter_loop import _cleanup_residual_staging

    mark_staging_checkpointed(project, [PLAN_TARGET])
    _cleanup_residual_staging(project, has_pending_staging=False)
    assert staging_path(project, PLAN_TARGET).exists()


def test_unreadable_meta_fails_closed_under_preserve(project: Path) -> None:
    """I1: unreadable marker source aborts the preserve-clear instead of wiping."""
    (project / "staging" / ".staging-meta.json").write_text("{not json", encoding="utf-8")
    clear_staging(project, preserve_checkpointed=True)
    assert staging_path(project, PLAN_TARGET).exists()


def test_reject_clears_everything_including_checkpointed(project: Path) -> None:
    mark_staging_checkpointed(project, [PLAN_TARGET])
    clear_staging(project)
    assert not (project / "staging").exists()


def test_discard_staging_logs_and_clears(project: Path) -> None:
    discard_staging(project, reason="modify")
    assert not (project / "staging").exists()


def test_commit_removes_checkpoint_marker(project: Path) -> None:
    mark_staging_checkpointed(project, [PLAN_TARGET])
    commit_staging(project, [PLAN_TARGET])
    assert PLAN_TARGET not in staging_checkpointed_targets(project)
    assert (project / "plans" / "chapter-1-plan.md").exists()


def test_approve_chain_sidecar_reaches_committed_truth(project: Path) -> None:
    """T2 tier (spec R1 acceptance): after approve the sidecar reaches committed truth, surviving a simulated crash."""
    from shenbi.pipeline.cli import _commit_staging_for_checkpoint
    from shenbi.pipeline.machine import set_checkpoint
    from shenbi.pipeline.state import CheckpointType, PipelineState

    mark_staging_checkpointed(project, [PLAN_TARGET, SIDECAR_TARGET])
    state = PipelineState()
    set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=1)
    cp = state.pending_checkpoint

    # 模拟 crash（emergency clear 保留 checkpointed）后仍可 approve
    clear_staging(project, preserve_checkpointed=True)
    _commit_staging_for_checkpoint(project, cp)

    assert (project / "plans" / "chapter-1-plan.md").exists()
    assert (project / "plans" / "chapter-1-plan-decisions.json").exists()
