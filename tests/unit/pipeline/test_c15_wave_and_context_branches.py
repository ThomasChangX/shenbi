"""Concurrent-wave exception branches + audit_context_cache residual domains.

F738/F737 (spec #53 C15): wave-level exception isolation in
dispatch_reviews_parallel (worker exception → failed result, wave survives;
raising callback logged, wave survives) and the characters/volume branches of
build_shared_audit_context (truncation sentinel + volume node extraction).
Serial retry/backoff already covered by test_parallel_dispatch_safety.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.audit_context_cache import build_shared_audit_context
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.parallel_dispatch import (
    ReviewTask,
    dispatch_reviews_parallel,
)

REVIEW_SKILL = "shenbi-review-anti-ai"  # READ_ONLY_AUDIT per classify_skill_write_safety


def _task(idx: int) -> ReviewTask:
    return ReviewTask(
        skill=REVIEW_SKILL,
        project_dir=Path("/tmp/proj"),
        prompt=f"review {idx}",
        output_path=f"audits/review-{idx}.md",
    )


@pytest.mark.unit
class TestWaveExceptionBranches:
    def test_worker_exception_becomes_failed_result_wave_survives(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_retry(task: ReviewTask, semaphore: object) -> DispatchResult:
            if "0" in task.output_path:
                raise RuntimeError("worker blew up")
            return DispatchResult(True, 0, "ok", "")

        monkeypatch.setattr("shenbi.pipeline.parallel_dispatch._dispatch_with_retry", fake_retry)
        results = dispatch_reviews_parallel([_task(0), _task(1)])
        assert len(results) == 2  # order preserved, wave survived
        assert results[0].success is False
        assert "worker blew up" in results[0].stderr
        assert results[1].success is True

    def test_raising_callback_is_logged_wave_survives(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shenbi.pipeline.parallel_dispatch._dispatch_with_retry",
            lambda task, semaphore: DispatchResult(True, 0, "ok", ""),
        )
        callbacks: list[int] = []

        def bad_callback(idx: int, result: DispatchResult) -> None:
            callbacks.append(idx)
            raise ValueError("callback blew up")

        results = dispatch_reviews_parallel([_task(0), _task(1)], on_task_complete=bad_callback)
        assert all(r.success for r in results)
        assert len(callbacks) == 2  # every successful task still reached the callback


@pytest.mark.unit
class TestContextCacheCharactersAndVolume:
    def test_characters_truncated_with_sentinel_raw_retained(self, tmp_path: Path) -> None:
        (tmp_path / "truth").mkdir()
        big = "角色" * 2000  # 4000 chars > 3000 cap
        (tmp_path / "truth" / "character_matrix.md").write_text(big, encoding="utf-8")
        ctx = build_shared_audit_context(tmp_path, chapter=1)
        assert ctx.character_list.startswith("角色")
        assert "[TRUNCATED 3000/4000 chars]" in ctx.character_list
        # raw_files keeps the FULL original for read-suppression
        assert ctx.raw_files["truth/character_matrix.md"] == big

    def test_volume_node_extracted_not_in_raw_files(self, tmp_path: Path) -> None:
        (tmp_path / "outline").mkdir()
        volume_map = "# 卷一\n\n## 第1章 废土\n- 节拍 a\n- 节拍 b\n\n## 第2章 余烬\n- 节拍 c\n"
        (tmp_path / "outline" / "volume_map.md").write_text(volume_map, encoding="utf-8")
        ctx = build_shared_audit_context(tmp_path, chapter=1)
        assert "第1章 废土" in ctx.volume_context
        assert "节拍 a" in ctx.volume_context and "节拍 b" in ctx.volume_context
        assert "第2章" not in ctx.volume_context  # stops at next heading
        assert "outline/volume_map.md" not in ctx.raw_files  # no consumer (C28 R2)

    def test_volume_absent_yields_empty_context(self, tmp_path: Path) -> None:
        ctx = build_shared_audit_context(tmp_path, chapter=7)
        assert ctx.volume_context == ""
        assert ctx.character_list == ""
        assert ctx.raw_files == {}
