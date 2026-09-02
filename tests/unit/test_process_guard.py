"""T1a: run_subprocess_json 子进程守卫原语(spec #38 F106/F107/F125残余/F204/F124)。"""

import sys

from shenbi.process_guard import run_subprocess_json


def test_timeout_returns_blocked() -> None:
    # 子进程 sleep 超过 timeout → 结构化 blocked,不 raise
    r = run_subprocess_json([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.2)
    assert r["status"] == "blocked"
    assert r["error_kind"] == "timeout"


def test_bad_json_returns_fail_with_stdout_tail() -> None:
    r = run_subprocess_json([sys.executable, "-c", "print('not json')"])
    assert r["status"] == "FAIL"
    assert r["error_kind"] == "bad_json"
    assert "not json" in r["raw_stdout"]


def test_non_dict_json_returns_fail() -> None:
    r = run_subprocess_json([sys.executable, "-c", "print('[1,2]')"])
    assert r["status"] == "FAIL"
    assert r["error_kind"] == "bad_json"


def test_valid_json_passthrough() -> None:
    r = run_subprocess_json(
        [sys.executable, "-c", "import json; print(json.dumps({'status':'PASS'}))"]
    )
    assert r == {"status": "PASS"}


def test_os_error_returns_fail() -> None:
    r = run_subprocess_json(["/nonexistent/binary/xyz"])
    assert r["status"] == "FAIL"
    assert r["error_kind"] == "os_error"


def test_run_gate_timeout_propagates_blocked(monkeypatch, tmp_path) -> None:
    # run_gate 不显式传 timeout(约定由本测试钉死),默认被 patch 为 0.1s 时,
    # 真实 `python -m shenbi.gates.cli` 启动 ~0.4s → 必须结构化 blocked 而非
    # TimeoutExpired traceback。
    import shenbi.phase_runner as pr
    import shenbi.process_guard as pg

    monkeypatch.setattr(pg, "SUBPROCESS_TIMEOUT_DEFAULT", 0.1)
    r = pr.run_gate("G5", ["t2-skill", str(tmp_path), str(tmp_path)])
    assert r.get("status") == "blocked"


def test_gate_only_blocked_exits_one(monkeypatch, capsys) -> None:
    """--gate-only:helper 返回 blocked → exit 1(不静默 exit 0)。"""
    import pytest

    import shenbi.process_guard as pg
    from shenbi import scoring

    monkeypatch.setattr(pg, "run_subprocess_json", lambda *a, **kw: {"status": "blocked"})
    monkeypatch.setattr(sys, "argv", ["shenbi-score", "--gate-only", "G2", "--type", "chapter"])
    with pytest.raises(SystemExit) as ei:
        scoring.main()
    assert ei.value.code == 1


def test_cmd_post_score_malformed_scores_structured_fail(tmp_path) -> None:
    """F124:malformed scores.json → 结构化 ERROR + exit 1,非裸 JSONDecodeError。"""
    import json as _json

    import pytest

    from shenbi.phase_runner import cmd_post_score

    rd = tmp_path / "round"
    rd.mkdir()
    state = rd / "phase-t2-x"
    state.mkdir()
    (state / "phase-state.json").write_text(
        _json.dumps({"state": "started", "steps": []}), encoding="utf-8"
    )
    bad = tmp_path / "scores.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        cmd_post_score("t2-x", str(bad), str(rd))
    assert ei.value.code == 1
