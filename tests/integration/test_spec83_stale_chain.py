"""spec #83 T5 integration: the stale chain across the three real dispatch paths.

Happy chain (writer -> revalidation FAIL -> feedback -> green -> clear -> no
reject) plus per-site rejection behavior: parallel block synthesized failure,
cli pending-queue attempts++/requeue, serial generic _handle_failure route.
Real fixtures drive the revalidation face; dispatch itself is stubbed at the
dispatch_skill seam (no live LLM — core principle 8).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from shenbi.pipeline import chapter_loop
from shenbi.pipeline.chapter_loop import (
    CHAPTER_STEPS,
    _pre_settle_guard,
    _revalidate_revised_chapter,
    run_chapter_step,
    run_parallel_post_draft_steps,
)
from shenbi.pipeline.cli import _execute_pending_re_dispatches
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.state import ChapterState, PipelineState

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "spec83"


def _mini_project(tmp_path: Path, chapter: int = 28) -> Path:
    (tmp_path / "plans").mkdir(exist_ok=True)
    (tmp_path / "chapters").mkdir(exist_ok=True)
    for f in ("plans", "chapters"):
        src = FIX / f / ("chapter-28-plan.md" if f == "plans" else "chapter-28.md")
        (tmp_path / f / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_happy_chain_set_clear_and_no_reject(tmp_path: Path) -> None:
    """置位（写入者语义）→ 复验 FAIL（物象删尽）→ 复验绿 → 清除 → guard 零信号。"""
    d = _mini_project(tmp_path)
    st = PipelineState(project_dir=str(d))
    # 写入者语义（:4584 块内联——直接置位断言语义面）
    st.chapter_loop.chapter_states["28"] = ChapterState(declarations_stale=True)
    # 复验 FAIL：删尽骨哨（结构构造——pre 侧取 pre-rev 备份〔r5.1 取数源〕）
    ch = d / "chapters" / "chapter-28.md"
    original = ch.read_text(encoding="utf-8")
    (d / "chapters" / "chapter-28-pre-rev.md").write_text(original, encoding="utf-8")
    ch.write_text(original.replace("骨哨", "口哨"), encoding="utf-8")
    issues = _revalidate_revised_chapter(d, 28)
    assert any("rev.prop_purged" in i for i in issues)
    # 复验绿（恢复原文后重跑）→ §11 清除点 1 语义
    ch.write_text(original, encoding="utf-8")
    assert _revalidate_revised_chapter(d, 28) == []
    st.chapter_loop.chapter_states["28"].declarations_stale = False
    demoted, hard = _pre_settle_guard(st, d, 28)
    assert demoted == [] and hard == []


def test_parallel_site_rejects_stale(tmp_path: Path) -> None:
    """站点①：并行块 settling 派发前 stale → 合成失败 DispatchResult（stderr 载报文）。"""
    d = _mini_project(tmp_path)
    st = PipelineState(project_dir=str(d))
    st.chapter_loop.current_chapter = 28
    st.chapter_loop.chapter_states["28"] = ChapterState(declarations_stale=True)
    # 强制 hard（shadow:false 转正态）
    (d / "genre-config.json").write_text(
        '{"market_params": {"stale_declarations": {"shadow": false}}}', encoding="utf-8"
    )
    with patch.object(chapter_loop, "dispatch_skill") as mock_dispatch:
        mock_dispatch.return_value = DispatchResult(
            success=True, returncode=0, stdout="", stderr=""
        )
        lifecycle_result, settling_result = run_parallel_post_draft_steps(st)
        assert lifecycle_result.success  # lifecycle 派发不受影响
        assert not settling_result.success
        assert "ss.stale_declarations" in settling_result.stderr
        # settling 真实派发被 guard 短路（只发生了 lifecycle 一次）
        assert mock_dispatch.call_count == 1


def test_cli_queue_site_rejects_stale(tmp_path: Path) -> None:
    """站点②：cli 重派队列 settle entry 派发前 stale → attempts++ 保持排队（镜像 G4 失败分支）。"""
    d = _mini_project(tmp_path)
    st = PipelineState(project_dir=str(d))
    st.chapter_loop.chapter_states["28"] = ChapterState(declarations_stale=True)
    (d / "genre-config.json").write_text(
        '{"market_params": {"stale_declarations": {"shadow": false}}}', encoding="utf-8"
    )
    st.pending_re_dispatches.append(
        {
            "skill": "shenbi-state-settling",
            "chapter": 28,
            "checkpoint_type": "per-chapter",
            "reason": "audit_routed_revision",
        }
    )
    with patch("shenbi.pipeline.dispatch_helper.dispatch_skill") as mock_dispatch:
        mock_dispatch.return_value = DispatchResult(
            success=True, returncode=0, stdout="", stderr=""
        )
        executed = _execute_pending_re_dispatches(st, d)
    assert executed  # 有 entry 被处理
    assert mock_dispatch.call_count == 0  # settle entry 被 guard 拒收——未派发
    requeued = [e for e in st.pending_re_dispatches if e.get("skill") == "shenbi-state-settling"]
    assert requeued and requeued[0].get("attempts", 0) >= 1  # entry 保持排队且 attempts 计入


def test_serial_site_routes_to_handle_failure(tmp_path: Path) -> None:
    """站点③：串行通用路径真实驱动（audit-T5 I 补——STATE_SETTLE redo 落此路径）。

    转正态（shadow:false）下 guard 须在 dispatch_skill **之前**短路：真实
    settle 派发零次、retry_feedback 载报文、_handle_failure 路由（per_chapter
    检查点模式返回 True）。
    """
    d = _mini_project(tmp_path)
    st = PipelineState(project_dir=str(d))
    st.chapter_loop.current_chapter = 28
    st.chapter_loop.chapter_states["28"] = ChapterState(declarations_stale=True)
    (d / "genre-config.json").write_text(
        '{"market_params": {"stale_declarations": {"shadow": false}}}', encoding="utf-8"
    )
    # 游标直接钉到 settling 步（STATE_SETTLE checkpoint redo 的 step_index 重置态）
    settle_idx = next(
        i for i, s_ in enumerate(CHAPTER_STEPS) if s_.skill == "shenbi-state-settling"
    )
    st.chapter_loop.step_index = settle_idx
    st.config.per_chapter_review_enabled = True
    with patch.object(chapter_loop, "dispatch_skill") as mock_dispatch:
        mock_dispatch.return_value = DispatchResult(
            success=True, returncode=0, stdout="", stderr=""
        )
        raised_or_checkpoint = run_chapter_step(st, d)
    assert mock_dispatch.call_count == 0  # guard 先于派发（audit-T5 C1 回归钉）
    fb = st.chapter_loop.retry_feedback.get("ch28-shenbi-state-settling", "")
    assert "ss.stale_declarations" in fb  # 反馈定向载报文
    # _handle_failure 路由面：步骤未标记完成（失败路径，具体 checkpoint/auto-retry
    # 形态由内部失败分类决定——非本断言义务）
    assert (
        "shenbi-state-settling"
        not in st.chapter_loop.chapter_states.get("28", ChapterState()).steps_done
    )
