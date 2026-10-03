"""Review-decision staging scoping (#39, batch #15).

probe20: an ESCALATION reject ran the UNCONDITIONAL ``clear_staging`` — the
escalation checkpoint owns NO staging, but the wipe destroyed the reviewed
settle increments still sitting in ``staging/truth/``. Every later writer
then merged against shell bases while feedback described a settled world.

Contract: a review decision touches ONLY the products its own checkpoint
type owns (the same target set approve commits). Checkpoint types that own
no staging (escalation, genesis-*, volume-boundary, book-closure) clear
NOTHING.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.state import CheckpointType, PipelineState


def _project_with_staged_truth(tmp_path: Path) -> Path:
    staged_truth = tmp_path / "staging" / "truth"
    staged_truth.mkdir(parents=True)
    (staged_truth / "current_state.md").write_text(
        "| 章节 | 位置 |\n|------|------|\n| 第1章 | 井下 |", encoding="utf-8"
    )
    (staged_truth / "particle_ledger.md").write_text(
        "| 章节 | 变动项 |\n|------|------|\n| 第1章 | 灯油 |", encoding="utf-8"
    )
    meta = tmp_path / "staging" / ".staging-meta.json"
    meta.write_text(
        json.dumps(
            {
                "truth/current_state.md": {"update_mode": "append_dedup", "key_field": "chapter"},
                "truth/particle_ledger.md": {"update_mode": "append_dedup", "key_field": "chapter"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tmp_path


def _review(project: Path, cp_type: CheckpointType, decision: str, chapter: int = 1) -> None:
    """Drive cmd_review the same way test_cli.TestModifyDecision does."""
    import argparse

    from shenbi.pipeline import cli as pipeline_cli
    from shenbi.pipeline.machine import save_state
    from shenbi.pipeline.state import PipelinePhase

    state = PipelineState.default(str(project))
    if cp_type in (CheckpointType.GENESIS_COMPLETE, CheckpointType.ESCALATION):
        state.phase = PipelinePhase.GENESIS
    else:
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.chapter_loop.current_chapter = chapter
    save_state(project, state)
    set_checkpoint(state, cp_type, chapter=chapter, context="test")
    save_state(project, state)

    rc = pipeline_cli.cmd_review(
        argparse.Namespace(project_dir=str(project), decision=decision, feedback=None)
    )
    assert rc == 0, f"pipeline review {decision} must succeed"


class TestRejectScoping:
    def test_escalation_reject_keeps_staged_truth(self, tmp_path):
        project = _project_with_staged_truth(tmp_path)
        _review(project, CheckpointType.ESCALATION, "reject")
        surviving = sorted(p.name for p in (project / "staging" / "truth").glob("*.md"))
        assert surviving == ["current_state.md", "particle_ledger.md"], (
            "#39: an escalation reject must not destroy other checkpoints' staging"
        )

    def test_state_settle_reject_discards_staged_truth(self, tmp_path):
        project = _project_with_staged_truth(tmp_path)
        _review(project, CheckpointType.STATE_SETTLE, "reject")
        staged = project / "staging" / "truth"
        assert not any(staged.glob("*.md")), (
            "settle reject discards its own increments (redo regenerates)"
        )

    def test_per_chapter_reject_discards_staged_truth(self, tmp_path):
        project = _project_with_staged_truth(tmp_path)
        _review(project, CheckpointType.PER_CHAPTER, "reject")
        staged = project / "staging" / "truth"
        assert not any(staged.glob("*.md")), (
            "per-chapter reject owns the same truth set its approve commits"
        )

    def test_chapter_memo_reject_spares_staged_truth(self, tmp_path):
        """A chapter-memo reject owns the PLAN staging, not truth staging —
        settle increments staged earlier must survive it.
        """
        project = _project_with_staged_truth(tmp_path)
        plans = project / "staging" / "plans"
        plans.mkdir(parents=True)
        (plans / "chapter-1-plan.md").write_text("# memo draft", encoding="utf-8")
        _review(project, CheckpointType.CHAPTER_MEMO, "reject")
        surviving = sorted(p.name for p in (project / "staging" / "truth").glob("*.md"))
        assert surviving == ["current_state.md", "particle_ledger.md"]
        assert not (plans / "chapter-1-plan.md").exists(), "own plan staging IS discarded"


class TestPerChapterNoStagingWarn:
    def test_per_chapter_approve_without_staged_truth_warns(self, tmp_path):
        """Observability for silent loss: PER_CHAPTER approve normally
        commits staged truth; finding none after a settle ran is the smoke
        of a #39-class wipe.
        """
        from structlog.testing import capture_logs

        project = tmp_path
        (project / "staging").mkdir(parents=True)
        with capture_logs() as logs:
            _review(project, CheckpointType.PER_CHAPTER, "approve")
        assert any(entry.get("event") == "per_chapter_no_staged_truth" for entry in logs), (
            "PER_CHAPTER approve with zero staged truth must WARN (silent-loss smoke)"
        )


@pytest.mark.parametrize(
    "cp_type",
    [
        CheckpointType.GENESIS_COMPLETE,
        CheckpointType.VOLUME_BOUNDARY,
        CheckpointType.BOOK_CLOSURE,
    ],
)
def test_no_staging_checkpoint_types_reject_clears_nothing(tmp_path, cp_type):
    project = _project_with_staged_truth(tmp_path)
    _review(project, cp_type, "reject")
    surviving = sorted(p.name for p in (project / "staging" / "truth").glob("*.md"))
    assert surviving == ["current_state.md", "particle_ledger.md"], (
        f"{cp_type.value} owns no staging — its reject must clear nothing"
    )
