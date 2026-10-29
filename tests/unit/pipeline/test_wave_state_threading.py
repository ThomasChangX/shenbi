"""Spec #81 §2 rev4: parallel/serial review-wave state threading.

Review-group is the largest failure family (30/38 forensics in the mining
report); wave DISPATCH without loop_id would recreate the B-1 blind spot
exactly there.
"""

from __future__ import annotations

from pathlib import Path
from threading import Semaphore
from types import SimpleNamespace
from typing import Any

from shenbi.pipeline import parallel_dispatch as pd
from shenbi.pipeline.chapter_loop import _dispatch_serial_reviews


class _FakeResult:
    def __init__(self) -> None:
        self.success = True
        self.returncode = 0
        self.stdout = "ok"
        self.stderr = ""


def _task(skill: str = "shenbi-review-anti-ai") -> pd.ReviewTask:
    return pd.ReviewTask(
        skill=skill,
        project_dir=Path("."),
        prompt="review chapter 1",
        output_path="reviews/x.md",
        shared_context=None,
    )


class TestWaveThreading:
    def test_dispatch_with_retry_forwards_state(self, tmp_path: Path, monkeypatch):
        captured: dict[str, Any] = {}

        def _capture(*, state=None, **kw):
            captured["state"] = state
            return _FakeResult()

        monkeypatch.setattr(pd, "dispatch_skill", _capture)
        sent = SimpleNamespace(marker="wave-state")
        result = pd._dispatch_with_retry(_task(), Semaphore(4), state=sent)
        assert result.success
        assert captured["state"] is sent  # 透传到 dispatch_skill

    def test_dispatch_with_retry_stateless_default(self, tmp_path: Path, monkeypatch):
        captured: dict[str, Any] = {}

        def _capture(*, state=None, **kw):
            captured["state"] = state
            return _FakeResult()

        monkeypatch.setattr(pd, "dispatch_skill", _capture)
        pd._dispatch_with_retry(_task(), Semaphore(4))
        assert captured["state"] is None  # 无 state 调用点兼容

    def test_parallel_wave_entry_forwards_state(self, tmp_path: Path, monkeypatch):
        captured: dict[str, Any] = {}

        def _capture(*, state=None, **kw):
            captured["state"] = state
            return _FakeResult()

        monkeypatch.setattr(pd, "dispatch_skill", _capture)
        sent = SimpleNamespace(marker="entry-state")
        results = pd.dispatch_reviews_parallel([_task()], state=sent)
        assert len(results) == 1 and results[0].success
        assert captured["state"] is sent

    def test_serial_subwave_forwards_state(self, tmp_path: Path, monkeypatch):
        captured: dict[str, Any] = {}

        def _capture(*, state=None, **kw):
            captured["state"] = state
            return _FakeResult()

        monkeypatch.setattr(pd, "dispatch_skill", _capture)
        sent = SimpleNamespace(marker="serial-state")
        results = _dispatch_serial_reviews([_task()], tmp_path, state=sent)
        assert len(results) == 1 and results[0].success
        assert captured["state"] is sent  # WRITE_SHARED 串行成员同享 loop_id 覆盖
