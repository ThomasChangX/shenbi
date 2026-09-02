"""T1b: gate 进程内 jload 守卫扫尾(spec #38 F403 残余——g5.py:59、g_reconcile.py:34)。"""

import json

from shenbi.gates.g5 import gate_G5
from shenbi.gates.g_reconcile import gate_G_RECONCILE


def _t2_phase_deps(tmp_path, monkeypatch) -> None:
    """让 G5 认识一个假 phase 并指向 tmp round 的报告目录。"""
    from shenbi.gates import g5

    monkeypatch.setattr(g5, "TESTS", tmp_path, raising=False) if hasattr(g5, "TESTS") else None
    tiers = tmp_path / "tiers"
    tiers.mkdir(exist_ok=True)
    (tiers / "deps.json").write_text(
        json.dumps({"t2-phases": {"t2-x": {"prerequisites": ["some-skill"]}}}),
        encoding="utf-8",
    )
    (tiers / "acceptance.json").write_text(json.dumps({"t2": 90}), encoding="utf-8")
    monkeypatch.setattr(g5, "TESTS", tmp_path)


def test_g5_malformed_t1_report_structured_fail(tmp_path, monkeypatch) -> None:
    """坏 JSON 的 t1-report → G5.1 report_unreadable 计 mf,而非 ValueError traceback。"""
    _t2_phase_deps(tmp_path, monkeypatch)
    reports = tmp_path / "t1-reports"
    reports.mkdir()
    bad = reports / "some-skill-generative.json"
    bad.write_text("{not json", encoding="utf-8")

    monkeypatch.setattr(
        "shenbi.gates.g5.find_report", lambda d, s, t: bad if d is not None else None
    )
    out = gate_G5(phase_name="t2-x", round_dir=str(tmp_path), project_dir=None)
    assert "G5.1:some-skill:report_unreadable" in out
    assert "Traceback" not in out


def test_g_reconcile_malformed_progress_structured_fail(tmp_path) -> None:
    """坏 JSON 的 progress.json → 结构化 fail,而非 ValueError traceback。"""
    (tmp_path / "progress.json").write_text("{not json", encoding="utf-8")
    out = gate_G_RECONCILE(round_dir=str(tmp_path))
    assert "progress.json unreadable or malformed" in out
