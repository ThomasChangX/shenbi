"""spec #31 T2b: dual-scorer agreement, opt-in, mocked-subprocess unit tests.

G0.9 注记: 本测试对象是 dispatch 控制流 (subprocess 打桩), scores dict 是
程序内构造的输入而非「真实技能产物 fixture」——dispatch 内部 JSON 协议不属于
G0.9 管辖的 scenario fixture 面; 第二评分 = 主评分的程序化副本 + 单维度受控 delta。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from shenbi.dispatcher.modes import codex as codex_mod

REAL_SCORES: dict[str, Any] = {"1": 90, "2": 85, "3": 80, "4": 88, "5": 82}


def _fake_codex_exec(second_scores: dict[str, Any]):
    """subprocess.run fake: codex-exec calls write .raw JSON; shenbi-score returns score."""
    calls = {"execs": 0, "total": 0}

    def run(cmd: list[str], **kwargs: Any):
        calls["total"] += 1
        if "shenbi-score" in cmd:  # scoring subprocess: no -o flag

            class ScoreResult:
                returncode = 0
                stderr = ""
                stdout = json.dumps({"final_score": 85})

            return ScoreResult()
        # codex exec: cmd 形如 ["codex","exec","-C",str(round_dir),"-o",str(raw_out),prompt]
        idx = calls["execs"]
        calls["execs"] += 1
        out_path = Path(cmd[cmd.index("-o") + 1])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(second_scores if idx == 1 else REAL_SCORES), encoding="utf-8"
        )

        class ExecResult:
            returncode = 0
            stderr = ""
            stdout = ""

        return ExecResult()

    return run, calls


def _manifest(tmp_path: Path) -> dict[str, Any]:
    return json.loads((tmp_path / "pipeline-manifest.json").read_text(encoding="utf-8"))


@pytest.mark.unit
def test_dual_scorer_agreement_no_arbitration(tmp_path, monkeypatch):
    run, calls = _fake_codex_exec(dict(REAL_SCORES))  # 两份一致
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setenv("SHENBI_DUAL_SCORER", "1")
    rc = codex_mod.dispatch_codex("sk", "generative", tmp_path, "p", "a1")
    assert rc == 0
    assert calls["execs"] == 2 and calls["total"] >= 3  # 2×codex exec + ≥1 score
    assert not (tmp_path / "pipeline-manifest.json").exists()  # 一致 → 无仲裁记录
    assert (tmp_path / "t1-reports" / "sk-generative-scores-subagent-2.json").exists()


@pytest.mark.unit
def test_dual_scorer_dispute_writes_arbitration(tmp_path, monkeypatch):
    disputed = dict(REAL_SCORES)
    disputed["2"] = 70  # 差 15 > 5
    run, _ = _fake_codex_exec(disputed)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setenv("SHENBI_DUAL_SCORER", "1")
    rc = codex_mod.dispatch_codex("sk", "generative", tmp_path, "p", "a1")
    assert rc == 0
    entry = _manifest(tmp_path)["gates"]["t1"]["0"]["sk"]["G3-arb"]
    # gate_manifest 语义：首条为裸 dict entry，追加后转 list（gates/gate_manifest.py:80-86）
    if isinstance(entry, list):
        entry = entry[-1]
    assert entry["result"]["needs_arbitration"] is True


@pytest.mark.unit
def test_dual_scorer_disabled_by_default(tmp_path, monkeypatch):
    run, calls = _fake_codex_exec(dict(REAL_SCORES))
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.delenv("SHENBI_DUAL_SCORER", raising=False)
    rc = codex_mod.dispatch_codex("sk", "generative", tmp_path, "p", "a1")
    assert rc == 0
    assert calls["execs"] == 1 and calls["total"] == 2  # 1×codex exec + 1×score：无第二次派发
    assert not (tmp_path / "t1-reports" / "sk-generative-scores-subagent-2.json").exists()
