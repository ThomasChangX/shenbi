"""C30 R5 parallel wave midpoint save points (F377).

The wave dispatch invokes ``on_task_complete`` per SUCCESSFUL task as it
completes (failed tasks are not called), so a caller can persist partial
results mid-wave; a crash then only replays the unfinished segment.
"""

from pathlib import Path

import shenbi.pipeline.parallel_dispatch as pd
from shenbi.pipeline.dispatch_helper import DispatchResult

# Hermetic reference captured at import: if another test leaks a stub over
# pd.dispatch_reviews_parallel (xdist order flake family), calling the
# captured real function keeps this test exercising OUR callback contract.
_REAL_WAVE_DISPATCH = pd.dispatch_reviews_parallel

OK_SKILL = "shenbi-review-group-factual"
FAILING_SKILL = "shenbi-review-group-plan"


def _tasks(tmp_path: Path) -> list[pd.ReviewTask]:
    return [
        pd.ReviewTask(
            skill=OK_SKILL,
            project_dir=tmp_path,
            prompt="audit ok",
            output_path="audits/chapter-1-factual.md",
        ),
        pd.ReviewTask(
            skill=FAILING_SKILL,
            project_dir=tmp_path,
            prompt="audit fail",
            output_path="audits/chapter-1-plan.md",
        ),
    ]


def test_partial_wave_results_survive_via_callback(tmp_path: Path, monkeypatch) -> None:
    """Persistent failure injection: the failing task fails EVERY attempt (the
    retry loop would otherwise turn a one-shot failure into a success).
    """
    monkeypatch.setattr(pd, "MAX_RETRIES", 0)

    def fake_dispatch_skill(skill, *args, **kwargs):
        if skill == FAILING_SKILL:
            return DispatchResult(False, 1, "", "injected failure")
        return DispatchResult(True, 0, "ok", "")

    monkeypatch.setattr(pd, "dispatch_skill", fake_dispatch_skill)

    completed: list[int] = []
    results = _REAL_WAVE_DISPATCH(
        _tasks(tmp_path), on_task_complete=lambda i, r: completed.append(i)
    )
    assert completed == [0]  # success called back; failure NOT called back
    assert results[0].success and not results[1].success


def test_callback_not_required(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pd, "MAX_RETRIES", 0)
    monkeypatch.setattr(
        pd,
        "dispatch_skill",
        lambda skill, *a, **k: DispatchResult(True, 0, "ok", ""),
    )
    results = _REAL_WAVE_DISPATCH(_tasks(tmp_path))  # default None: no crash
    assert all(r.success for r in results)


def test_callback_exception_does_not_break_wave(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pd, "MAX_RETRIES", 0)
    monkeypatch.setattr(
        pd,
        "dispatch_skill",
        lambda skill, *a, **k: DispatchResult(True, 0, "ok", ""),
    )

    def bad_callback(i, r):
        raise RuntimeError("callback blew up")

    results = _REAL_WAVE_DISPATCH(_tasks(tmp_path), on_task_complete=bad_callback)
    assert all(r.success for r in results)  # wave survives a broken callback


def test_replay_scope_limited_to_unfinished(tmp_path: Path, monkeypatch) -> None:
    """Crash after task 0 completed: replay only dispatches the missing segment
    (skills whose output file already exists are filtered out).
    """
    from shenbi.pipeline.chapter_loop import _filter_completed_audit_tasks

    audits = tmp_path / "audits"
    audits.mkdir()
    (audits / "chapter-1-factual.md").write_text("# done pre-crash\n", encoding="utf-8")
    remaining = _filter_completed_audit_tasks(_tasks(tmp_path))
    assert [t.skill for t in remaining] == [FAILING_SKILL]


def test_empty_tasks_no_callback_invocation(tmp_path: Path) -> None:
    called: list[int] = []
    results = _REAL_WAVE_DISPATCH([], on_task_complete=lambda i, r: called.append(i))
    assert results == []
    assert called == []
