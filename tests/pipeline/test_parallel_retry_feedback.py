"""#18-5 (probe23): wave retries must deliver the rejection reason.

probe23 ch2 resonance: the increment-shape guard rejected all three
attempts with the same pointed teaching stderr (「合法增量是…」), but
``_dispatch_with_retry`` re-sent the IDENTICAL prompt — the model never
learned why its output was rejected, burned ~107k completion tokens on
three identical whole-file scaffolds, and the review-summary increment
was lost (``parallel_review_wave2_empty`` → empty ch2 review summary).

The dispatch layer already designs ``result.stderr`` as retry feedback
(``build_retry_feedback(exc)`` / ``str(IncrementShapeError)``); the wave
loop simply never delivered it into the next attempt's prompt.
"""

from __future__ import annotations

import time
from pathlib import Path
from threading import Semaphore

from shenbi.pipeline import parallel_dispatch as pd
from shenbi.pipeline.dispatch_helper import DispatchResult

SHAPE_STDERR = (
    "输出未落盘——append_dedup（key: chapter）增量包含整档脚手架："
    "frontmatter（--- 块）、一级标题（# 审计纠偏）。合法增量是行级追加。"
)


def _make_task(tmp_path: Path) -> pd.ReviewTask:
    return pd.ReviewTask(
        skill="shenbi-review-resonance",
        project_dir=tmp_path,
        prompt="BASE PROMPT",
        output_path="audits/chapter-2-resonance.md",
    )


def test_retry_prompt_carries_rejection_feedback(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_dispatch(
        skill, project_dir, prompt, shared_context=None, path_context=None, state=None
    ):
        calls.append(prompt)
        if len(calls) == 1:
            return DispatchResult(False, -1, "", SHAPE_STDERR)
        return DispatchResult(True, 0, "", "")

    monkeypatch.setattr(pd, "dispatch_skill", fake_dispatch)
    monkeypatch.setattr(time, "sleep", lambda _s: None)

    result = pd._dispatch_with_retry(_make_task(tmp_path), Semaphore(1))

    assert result.success is True
    assert len(calls) == 2
    assert "BASE PROMPT" in calls[1]
    assert "合法增量" in calls[1]
    assert "合法增量" not in calls[0]  # the first attempt is not pre-polluted


def test_identical_rejection_is_not_appended_twice(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_dispatch(
        skill, project_dir, prompt, shared_context=None, path_context=None, state=None
    ):
        calls.append(prompt)
        if len(calls) < 3:
            return DispatchResult(False, -1, "", SHAPE_STDERR)
        return DispatchResult(True, 0, "", "")

    monkeypatch.setattr(pd, "dispatch_skill", fake_dispatch)
    monkeypatch.setattr(time, "sleep", lambda _s: None)

    result = pd._dispatch_with_retry(_make_task(tmp_path), Semaphore(1))

    assert result.success is True
    assert len(calls) == 3
    assert calls[2].count("合法增量") == 1  # same reason injected once, not stacked
