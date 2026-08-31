"""T0 red-first reproduction suite for spec #37 (cluster C11).

Every test here reproduces a LIVE defect on main and is expected to FAIL
(red) until the corresponding fix task lands. Deterministic interleaving
strategies are mandatory — no pure-timing reliance. POSIX-only (flock).
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="flock POSIX-only")


def test_t605_dual_writer_lost_update(tmp_path: Path) -> None:
    """Concurrent state transactions must not lose updates (T605).

    Red on main: `transact_state` does not exist — the unlockable
    load→mutate→save pattern it replaces is exactly the T605 bypass shape.
    Thread exceptions are swallowed by threading, so the observable pytest
    red is the final count assertion (0 != 50). Green after Task 3.
    """
    from shenbi.pipeline.machine import load_state, save_state
    from shenbi.pipeline.state import PipelineState

    save_state(tmp_path, PipelineState(project_dir=str(tmp_path)))
    barrier = threading.Barrier(2)
    n = 25  # per-thread increments

    def bump() -> None:
        import importlib

        # __dict__ lookup keeps basedpyright happy pre-implementation; the
        # KeyError inside the thread is the intended TDD red.
        machine = importlib.import_module("shenbi.pipeline.machine")
        transact_state = machine.__dict__["transact_state"]
        barrier.wait(timeout=10)
        for _ in range(n):
            transact_state(
                tmp_path,
                lambda s: setattr(
                    s.chapter_loop, "current_chapter", s.chapter_loop.current_chapter + 1
                ),
            )

    t1, t2 = threading.Thread(target=bump), threading.Thread(target=bump)
    t1.start()
    t2.start()
    t1.join(timeout=25)
    t2.join(timeout=25)
    assert load_state(tmp_path).chapter_loop.current_chapter == 2 * n


def test_t601_concurrent_integrity_findings_conservation(tmp_path: Path) -> None:
    """5 concurrent per-chapter auditors appending findings must conserve lines (T601)."""
    from shenbi.pipeline.dispatch_helper import _append_integrity_findings

    target = tmp_path / "chapters" / "chapter-001.md"
    target.parent.mkdir(parents=True)
    target.write_text("x", encoding="utf-8")
    barrier = threading.Barrier(5)

    def append_one(i: int) -> None:
        barrier.wait(timeout=10)
        _append_integrity_findings(tmp_path, target, [f"finding-{i}"])

    threads = [threading.Thread(target=append_one, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=25)
    out = tmp_path / "audits" / ".integrity-findings-001.jsonl"
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 5  # red: last-writer-wins drops lines


def test_f531_trace_seq_duplicate(tmp_path: Path) -> None:
    """Two TraceWriter instances appending concurrently must not duplicate seq (F531)."""
    from shenbi.trace.writer import TraceWriter

    barrier = threading.Barrier(2)
    k = 10  # appends per writer

    def write_many(tag: str) -> None:
        barrier.wait(timeout=10)
        w = TraceWriter(tmp_path)
        for i in range(k):
            w.append(actor=tag, actor_role="GATE", action="TEST", target="t", payload={"i": i})

    t1 = threading.Thread(target=write_many, args=("a",))
    t2 = threading.Thread(target=write_many, args=("b",))
    t1.start()
    t2.start()
    t1.join(timeout=25)
    t2.join(timeout=25)
    seqs = [
        json.loads(ln)["seq"]
        for ln in (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert len(seqs) == len(set(seqs)) == 2 * k  # red: both start at seq=1


def test_t604_emergency_cleanup_double_execution(tmp_path: Path, monkeypatch) -> None:
    """Signal path + atexit must trigger emergency cleanup exactly once (T604)."""
    import shenbi.pipeline.crash_recovery as cr
    from shenbi.pipeline import machine

    calls: list[str] = []
    # crash_recovery imports save_state locally (machine.save_state at :125)
    monkeypatch.setattr(machine, "save_state", lambda *a, **k: calls.append("save"))
    cr._emergency_state["project_dir"] = tmp_path
    cr._emergency_state["pipeline_state"] = object()  # truthy sentinel
    cr._emergency_flag = True
    try:
        cr._check_emergency_flag(tmp_path)  # step-boundary path
        cr._emergency_cleanup(tmp_path)  # atexit path fires again
    finally:
        cr._emergency_flag = False  # xdist 安全：模块全局复位
        cr.reset_emergency_state()  # crash_recovery.py:28-45 要求测试后复位
    assert len(calls) == 1  # red: save_state called twice


def test_f630_materialize_clobbers_foreign_keys(tmp_path: Path) -> None:
    """materialize_progress must preserve keys it does not own (F630)."""
    from shenbi.trace.materialize import materialize_progress

    progress = tmp_path / "progress.json"
    progress.write_text(
        json.dumps(
            {
                "custom_key": 1,
                "skills": {"x": {"generative": {"status": "DONE", "score": 95.0}}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    materialize_progress(tmp_path, total_skills=["x"], tier="T1")
    out = json.loads(progress.read_text(encoding="utf-8"))
    assert out.get("custom_key") == 1  # red: wholesale rebuild drops it
    assert out["skills"]["x"]["generative"]["status"] == "DONE"  # red: rebuilt as pending


def test_locked_transact_mutual_exclusion(tmp_path: Path) -> None:
    """locked_transact serializes whole read-modify-write cycles (F206/F347 primitive)."""
    import json

    from shenbi.safe_write import locked_transact

    target = tmp_path / "counter.json"
    target.write_text(json.dumps({"n": 0}), encoding="utf-8")
    barrier = threading.Barrier(2)
    n = 25

    def bump() -> None:
        barrier.wait(timeout=10)
        for _ in range(n):
            locked_transact(target, lambda d: d.update(n=d["n"] + 1))

    t1, t2 = threading.Thread(target=bump), threading.Thread(target=bump)
    t1.start()
    t2.start()
    t1.join(timeout=25)
    t2.join(timeout=25)
    assert json.loads(target.read_text(encoding="utf-8"))["n"] == 2 * n


def test_holder_mode_tracks_write_lock(tmp_path: Path) -> None:
    """holder_mode reports the current thread's L1 mode (spec #37 v3r2)."""
    from shenbi.pipeline.filelock_utils import ReadLock, WriteLock, holder_mode

    assert holder_mode() is None
    with WriteLock(tmp_path):
        assert holder_mode() == "write"
    assert holder_mode() is None
    with ReadLock(tmp_path):
        assert holder_mode() == "read"
    assert holder_mode() is None
