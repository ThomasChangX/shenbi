"""C30 R2 resume cursor anchoring + steps_done versioned migration.

Spec #44 (F371/F1114/F797): the resume cursor must anchor on COMMITTED
chapter products (never silently reset to chapter 1 / never skip ahead over
uncommitted chapters), and old-generation step names in steps_done must
migrate on resume with a WARN.
"""

from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    CHAPTER_STEPS,
    PIPELINE_STEPS_VERSION,
    STEP_NAME_MIGRATIONS,
    _clamp_resume_cursor,
    committed_chapter_anchor,
    migrate_steps_done,
)
from shenbi.pipeline.state import ChapterLoopStateData, ChapterState


def _commit_chapters(tmp_path: Path, count: int) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    for n in range(1, count + 1):
        (chapters / f"chapter-{n}.md").write_text(f"# 第{n}章\n", encoding="utf-8")


def test_anchor_is_max_committed_chapter(tmp_path: Path) -> None:
    _commit_chapters(tmp_path, 3)
    (tmp_path / "chapters" / "chapter-2-emergency.md").write_text("x", encoding="utf-8")
    assert committed_chapter_anchor(tmp_path) == 3


def test_anchor_zero_when_no_products(tmp_path: Path) -> None:
    assert committed_chapter_anchor(tmp_path) == 0


def test_anchor_clamps_uncommitted_chapter(tmp_path: Path) -> None:
    _commit_chapters(tmp_path, 3)
    cl = ChapterLoopStateData(current_chapter=6, step_index=0)
    _clamp_resume_cursor(cl, tmp_path)
    assert cl.current_chapter == 4
    assert cl.step_index == 0


def test_anchor_noop_when_mid_committed_chapter(tmp_path: Path) -> None:
    # Revision interrupted INSIDE a committed chapter (progress recorded):
    # the cursor stays — this is not a runaway cursor.
    _commit_chapters(tmp_path, 3)
    cl = ChapterLoopStateData(
        current_chapter=3,
        step_index=2,
        chapter_states={"3": ChapterState(steps_done=["shenbi-chapter-drafting"])},
    )
    _clamp_resume_cursor(cl, tmp_path)
    assert cl.current_chapter == 3


def test_anchor_noop_when_cursor_at_next_uncommitted(tmp_path: Path) -> None:
    _commit_chapters(tmp_path, 3)
    cl = ChapterLoopStateData(current_chapter=4, step_index=1)
    _clamp_resume_cursor(cl, tmp_path)
    assert cl.current_chapter == 4


def test_steps_done_migration_v1_to_v2() -> None:
    migrated, changed = migrate_steps_done(
        [
            "shenbi-chapter-planning",
            "shenbi-foreshadowing-plant",
            "shenbi-review-pacing",
        ]
    )
    assert changed
    assert "shenbi-chapter-planning" in migrated  # 当代名原样保留
    assert "shenbi-foreshadowing-lifecycle" in migrated  # 1:1 映射
    assert "shenbi-review-pacing" not in migrated  # 已并入审计组，重跑


def test_steps_done_migration_idempotent() -> None:
    once, changed = migrate_steps_done(["shenbi-foreshadowing-plant"])
    twice, changed2 = migrate_steps_done(once)
    assert changed and not changed2 and once == twice


def test_migration_map_covers_no_current_names() -> None:
    """Migration-table old names must not be current names (no self-mapping loop)."""
    current = {s.skill for s in CHAPTER_STEPS}
    for table in STEP_NAME_MIGRATIONS.values():
        for old in table:
            assert old not in current, old


def test_steps_version_pin() -> None:
    """Steps-table snapshot pin: any rename/reorder must bump PIPELINE_STEPS_VERSION and update the migration map plus this snapshot."""
    assert PIPELINE_STEPS_VERSION == 2
    assert tuple(s.skill for s in CHAPTER_STEPS) == (
        "pipeline-volume-align",
        "shenbi-chapter-planning",
        "pipeline-context-prepare",
        "shenbi-chapter-drafting",
        "pipeline-post-draft-extract",
        "pipeline-linguistic-drift-check",
        "shenbi-foreshadowing-lifecycle",
        "shenbi-state-settling",
        "shenbi-review-group-factual",
        "shenbi-review-group-character",
        "shenbi-review-group-craft",
        "shenbi-review-group-plan",
        "shenbi-review-resonance",
        "shenbi-review-sensitivity",
        "shenbi-chapter-revision",
    )


def test_clear_checkpoint_consumed_flag() -> None:
    """Event consumption: history entries carry consumed=False; the consuming resume flips it to True."""
    from shenbi.pipeline.machine import clear_checkpoint, set_checkpoint
    from shenbi.pipeline.state import CheckpointType, PipelineState, ReviewDecision

    state = PipelineState()
    set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=1)
    clear_checkpoint(state, ReviewDecision.APPROVE)
    assert state.checkpoint_history[-1]["decision"] == "approve"
    assert state.checkpoint_history[-1]["consumed"] is False


def test_clear_checkpoint_none_noop() -> None:
    """F338: a NONE checkpoint must not enter history."""
    from shenbi.pipeline.machine import clear_checkpoint
    from shenbi.pipeline.state import CheckpointData, CheckpointType, PipelineState, ReviewDecision

    state = PipelineState()
    state.pending_checkpoint = CheckpointData(type=CheckpointType.NONE)
    clear_checkpoint(state, ReviewDecision.APPROVE)
    assert state.checkpoint_history == []
    assert state.pending_checkpoint.type == CheckpointType.NONE
