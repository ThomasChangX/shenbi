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


def test_trace_writer_compaction_mutual_exclusion(tmp_path: Path) -> None:
    """Concurrent compaction (whole-file replace) and append must not tear (F619)."""
    from shenbi.trace.compaction import compact
    from shenbi.trace.writer import TraceWriter

    w = TraceWriter(tmp_path)
    for i in range(5):
        w.append(actor="seed", actor_role="GATE", action="TEST", target="t", payload={"i": i})
    barrier = threading.Barrier(2)

    def do_compact() -> None:
        barrier.wait(timeout=10)
        compact(tmp_path, snapshot={})

    def do_append() -> None:
        barrier.wait(timeout=10)
        w.append(actor="a", actor_role="GATE", action="TEST", target="t", payload={"i": 99})

    t1 = threading.Thread(target=do_compact)
    t2 = threading.Thread(target=do_append)
    t1.start()
    t2.start()
    t1.join(timeout=25)
    t2.join(timeout=25)
    from shenbi.trace.replay import replay

    events = replay(tmp_path)
    seqs = [e.seq for e in events]
    assert len(seqs) == len(set(seqs))  # chain intact, no duplicate seq
    # both the COMPACTION head and any post-compaction append survive —
    # a lost append (replace landing after it) is the F619 silent-delete shape
    actions = [e.action for e in events]
    assert "COMPACTION" in actions
    assert len(events) in (1, 2)  # compact-only, or compact then append
    if len(events) == 2:
        assert actions == ["COMPACTION", "TEST"]
        assert events[1].payload.get("i") == 99


def test_record_audit_outcome_g7_no_false_tamper(tmp_path: Path) -> None:
    """Concurrent record_audit_outcome keeps the chain verifiable (F531/F536, spec AC4)."""
    from shenbi.audit._shared import AuditResult
    from shenbi.audit.record import record_audit_outcome
    from shenbi.trace.replay import replay

    barrier = threading.Barrier(4)

    def write_one(i: int) -> None:
        barrier.wait(timeout=10)
        record_audit_outcome(
            tmp_path,
            f"skill-{i}",
            AuditResult(skill=f"skill-{i}", violations=(), drift=(), checked_files=("a.md",)),
        )

    threads = [threading.Thread(target=write_one, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=25)
    events = replay(tmp_path)
    seqs = [e.seq for e in events]
    assert len(seqs) == len(set(seqs))  # no duplicate seq
    assert len(events) == 4


def test_gate_manifest_corrupt_fail_loud(tmp_path: Path) -> None:
    """Corrupt manifest is preserved + raises, not silently reset (F416)."""
    import pytest as _pytest

    from shenbi.gates.gate_manifest import ManifestCorruptError, record_gate_result

    (tmp_path / "pipeline-manifest.json").write_text("{not json", encoding="utf-8")
    with _pytest.raises(ManifestCorruptError):
        record_gate_result(tmp_path, "T1", 1, "skill", "G2", {"status": "PASS"})
    assert (tmp_path / "pipeline-manifest.json.corrupt").exists()


def test_gate_manifest_concurrent_writes_conserved(tmp_path: Path) -> None:
    """Two threads' gate records both survive (F416 lock half)."""
    from shenbi.gates.gate_manifest import record_gate_result

    barrier = threading.Barrier(2)

    def write_one(tag: str) -> None:
        barrier.wait(timeout=10)
        record_gate_result(tmp_path, "T1", 1, f"skill-{tag}", "G2", {"tag": tag})

    t1 = threading.Thread(target=write_one, args=("a",))
    t2 = threading.Thread(target=write_one, args=("b",))
    t1.start()
    t2.start()
    t1.join(timeout=25)
    t2.join(timeout=25)
    import json as _json

    data = _json.loads((tmp_path / "pipeline-manifest.json").read_text(encoding="utf-8"))
    skills = data["gates"]["T1"]["1"]
    assert set(skills) == {"skill-a", "skill-b"}


def test_ledger_ctor_no_mkdir(tmp_path: Path) -> None:
    """TokenLedger construction is a read-path op — no cost/ dir side effect (T407)."""
    from shenbi.cost.ledger import TokenLedger

    project = tmp_path / "proj"
    project.mkdir()
    TokenLedger(project)  # constructor may not create cost/
    assert not (project / "cost").exists()


def test_genre_cache_keyed_by_project_dir(tmp_path: Path) -> None:
    """Same chapter across two projects must not cross-pollinate (T607)."""
    import json

    from shenbi.pipeline import dispatch_helper as dh

    for name, marker in (("p1", "one"), ("p2", "two")):
        proj = tmp_path / name
        (proj / "config").mkdir(parents=True)
        (proj / "config" / "genre-config.json").write_text(
            json.dumps({"version": "1.0", "marker": marker}), encoding="utf-8"
        )
    try:
        c1 = dh._load_genre_config_cached(tmp_path / "p1", 1)
        c2 = dh._load_genre_config_cached(tmp_path / "p2", 1)
        assert c1.get("marker") == "one"
        assert c2.get("marker") == "two"
    finally:
        dh._genre_config_cache.clear()


def test_path_lock_registry_bounded() -> None:
    """The per-path lock registry must not grow without bound (T607)."""
    from shenbi.pipeline import truth_io

    for i in range(1000):
        truth_io._path_lock(Path(f"/tmp/nonexistent-{i}.json"))
    assert len(truth_io._PATH_LOCKS) <= truth_io._PATH_LOCKS_MAX


def test_periodic_materialize_removed() -> None:
    """The zero-event periodic materialize call sites are gone (F630 ruling b)."""
    from shenbi.pipeline import chapter_loop

    assert not hasattr(chapter_loop, "_maybe_materialize_progress")
    source = Path(chapter_loop.__file__).read_text(encoding="utf-8")
    assert "materialize_progress(Path(state.project_dir)" not in source


def test_append_jsonl_fsync_and_timestamp(tmp_path: Path, monkeypatch) -> None:
    """append_jsonl stamps a timestamp and fsyncs each append (F534)."""
    import json as _json

    from shenbi.append_helper import append_jsonl

    fsyncs: list[int] = []
    real_fsync = __import__("os").fsync
    monkeypatch.setattr(
        "shenbi.append_helper.os.fsync", lambda fd: (fsyncs.append(fd), real_fsync(fd))
    )
    target = tmp_path / "audits" / "write-audit.jsonl"
    append_jsonl(target, {"skill": "x"})
    append_jsonl(target, {"skill": "y"})
    lines = [
        _json.loads(ln) for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    assert [r["skill"] for r in lines] == ["x", "y"]
    assert all("timestamp" in r for r in lines)
    assert len(fsyncs) >= 2


def test_config_trail_failure_rolls_back(tmp_path: Path, monkeypatch) -> None:
    """A failing audit-trail append rolls genre-config back (F605 verify-before-write)."""
    import json as _json

    from shenbi.config import config_coherence as cc

    cfg = tmp_path / "genre-config.json"
    original = {"version": "1.0", "resonance_global_floor": 70}
    cfg.write_text(_json.dumps(original), encoding="utf-8")

    calls: list[int] = []

    def flaky_append(project_dir, key, old, new, rationale):
        calls.append(len(calls))
        if len(calls) >= 2:
            raise OSError("disk full")

    monkeypatch.setattr(cc, "_append_audit_trail", flaky_append)
    import pytest as _pytest

    with _pytest.raises(OSError):
        cc.update_genre_config(
            tmp_path,
            {"texture.minimum": 3, "antiAi.enabled": True},
            "batch rationale long enough for governance rules",
        )
    assert _json.loads(cfg.read_text(encoding="utf-8")) == original  # rolled back
