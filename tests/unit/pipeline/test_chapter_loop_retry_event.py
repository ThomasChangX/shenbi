"""Spec #81 §2: RETRY trace event emission (helper form + wiring forms)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shenbi.pipeline.chapter_loop import _emit_retry_event


def _seed_trace(project: Path) -> None:
    from shenbi.trace.writer import TraceWriter

    TraceWriter(project).append(actor="test", actor_role="SYSTEM", action="INIT", target="t")


def _events(project: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in (project / "trace.jsonl").read_text().splitlines()]


class TestHelperForm:
    def test_emits_structured_retry(self, tmp_path: Path):
        _seed_trace(tmp_path)
        _emit_retry_event(
            tmp_path,
            chapter=2,
            skill="shenbi-chapter-drafting",
            reason={"kind": "monitor_rewind", "chapter": 2, "issues": ["word_band:ch2:x"]},
            loop_id=4,
        )
        retries = [e for e in _events(tmp_path) if e["action"] == "RETRY"]
        assert len(retries) == 1
        payload = retries[0]["payload"]
        assert payload["loop_id"] == 4
        assert payload["reason"]["kind"] == "monitor_rewind"
        assert payload["reason"]["issues"] == ["word_band:ch2:x"]  # issues 原串形态（deviation ③）
        assert retries[0]["actor_role"] == "SYSTEM"

    def test_no_trace_file_creates_nothing(self, tmp_path: Path):
        """Guard test: TraceWriter.append auto-creates the surface; the helper must not."""
        _emit_retry_event(
            tmp_path, chapter=1, skill="s", reason={"kind": "g4_hard", "check_ids": []}, loop_id=1
        )
        assert not (tmp_path / "trace.jsonl").exists()

    def test_genesis_none_chapter_target(self, tmp_path: Path):
        _seed_trace(tmp_path)
        _emit_retry_event(tmp_path, chapter=None, skill="s", reason={"kind": "g4_hard"}, loop_id=2)
        retries = [e for e in _events(tmp_path) if e["action"] == "RETRY"]
        assert retries[0]["target"] == "ch0" and retries[0]["payload"]["chapter"] is None


class TestWiringForm:
    def test_g4_hard_failure_path_emits_retry(self, tmp_path: Path):
        """Real production path: G4 hard-fail re-dispatch -> one kind=g4_hard
        RETRY event in trace. Harness copied from test_chapter_loop.py::
        test_g4_fail_retries_then_escalates.
        """
        from unittest.mock import patch

        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.dispatch_helper import DispatchResult
        from shenbi.pipeline.state import PipelineState

        _seed_trace(tmp_path)
        with (
            patch("shenbi.pipeline.chapter_loop.dispatch_skill") as mock_disp,
            patch("shenbi.pipeline.revision_router.dispatch_skill") as mock_esc,
            patch("shenbi.pipeline.chapter_loop.run_gate_g4") as mock_g4,
        ):
            mock_disp.return_value = DispatchResult(True, 0, "{}", "")
            mock_esc.return_value = DispatchResult(True, 0, "{}", "")
            mock_g4.return_value = {"status": "FAIL", "must_fix": ["G4.cd.prop_handoff:x:缺"]}
            state = PipelineState.default(str(tmp_path))
            state.chapter_loop.current_chapter = 1
            state.chapter_loop.step_index = 1  # chapter-planning
            state.config.max_revision_retries = 2
            run_chapter_step(state, tmp_path)
        retries = [e for e in _events(tmp_path) if e["action"] == "RETRY"]
        assert len(retries) == 1  # 一次 G4 硬败 = 一发
        payload = retries[0]["payload"]
        assert payload["reason"]["kind"] == "g4_hard"
        assert payload["reason"]["check_ids"] == ["G4.cd.prop_handoff:x:缺"]
        assert payload["loop_id"] == 1  # 首次重派（budget +1 前快照语义）

    def test_monitor_rewind_path_emits_retry(self, tmp_path: Path):
        """audit-T6 I-1: the rewind site's wiring — real step loop through the
        pipeline-scene-split step with issues -> one kind=monitor_rewind RETRY
        carrying the pre-formatted issue strings (deviation ③ form).
        """
        from unittest.mock import patch

        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.state import PipelineState

        _seed_trace(tmp_path)
        issues = ["word_band:ch2:total_chars 1995 不在带 [2800,4000]"]
        with patch("shenbi.pipeline.chapter_loop._run_scene_split_step", return_value=issues):
            state = PipelineState.default(str(tmp_path))
            state.chapter_loop.current_chapter = 1
            state.chapter_loop.step_index = 4  # pipeline-scene-split（CHAPTER_STEPS 序 5，0 基 4）
            state.config.max_audit_retries = 3
            run_chapter_step(state, tmp_path)
        retries = [e for e in _events(tmp_path) if e["action"] == "RETRY"]
        assert len(retries) == 1  # 回卷一次 = 一发
        payload = retries[0]["payload"]
        assert payload["reason"]["kind"] == "monitor_rewind"
        assert payload["reason"]["issues"] == issues  # 原串形态（deviation ③）
        assert payload["loop_id"] == 1  # 首次回卷（budget +1 前快照语义）
