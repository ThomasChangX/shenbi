"""束5（2026-11-06）裁决 #13 根因：pipeline- 步源 escalation 的 reject
反馈路由到 pipeline- 步键（从不被消费）——须按熔断重派映射落 LLM 步键。
"""

import argparse
from pathlib import Path

from shenbi.pipeline import cli as cli_mod
from shenbi.pipeline.chapter_loop import ESCALATION_PIPELINE_TARGET
from shenbi.pipeline.state import CheckpointType, PipelinePhase, PipelineState


def _state_at_scene_split_checkpoint(tmp_path: Path) -> PipelineState:
    """复刻束5 现场：scene-split 熔断 escalation，step_index 指向 pipeline 步。"""
    state = PipelineState.default(str(tmp_path))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 45
    # pipeline-scene-split 在 CHAPTER_STEPS 的索引
    from shenbi.pipeline.chapter_loop import CHAPTER_STEPS

    idx = next(i for i, st in enumerate(CHAPTER_STEPS) if st.skill == "pipeline-scene-split")
    state.chapter_loop.step_index = idx
    state.pending_checkpoint.type = CheckpointType.ESCALATION
    state.pending_checkpoint.chapter = 45
    return state


def test_scene_split_reject_feedback_routes_to_drafting(tmp_path, monkeypatch) -> None:
    """Reject 的人审反馈必须落 ch{N}-shenbi-chapter-drafting 键（重派消费面）。"""
    from shenbi.pipeline.machine import load_state, save_state

    state = _state_at_scene_split_checkpoint(tmp_path)
    save_state(tmp_path, state)  # cmd_review 从盘载态
    args = argparse.Namespace(
        decision="reject", feedback=None, project_dir=str(tmp_path), redo_steps=None
    )
    # cmd_review 读反馈文件——落盘一份
    fb_path = tmp_path / "fb.md"
    fb_path.write_text("四派振荡归因=约束丢持：按全清单一次成形。", encoding="utf-8")
    args.feedback = str(fb_path)
    # 审查决策走 cmd_review 主入口（含 ESCALATION 路由块）
    rc = cli_mod.cmd_review(args)
    assert rc in (0, None)
    # 正键：drafting（熔断重派目标）；死键不得残留
    state = load_state(tmp_path)
    fb = state.chapter_loop.retry_feedback.get("ch45-shenbi-chapter-drafting", "")
    assert "全清单一次成形" in fb
    assert "ch45-pipeline-scene-split" not in state.chapter_loop.retry_feedback


def test_mapping_covers_scene_split_only() -> None:
    """映射单源：现行唯一 pipeline 熔断步=scene-split→drafting。"""
    assert ESCALATION_PIPELINE_TARGET == {"pipeline-scene-split": "shenbi-chapter-drafting"}
