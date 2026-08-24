"""Tests for linguistic drift detection and 3-tier intervention."""

from pathlib import Path

import pytest

from shenbi.skill_utils.drift_detection.linguistic_drift import (
    compute_linguistic_metrics,
    detect_drift,
)


def test_intervention_triggers_on_degraded_text():
    """3-tier intervention should fire when system term density exceeds thresholds."""
    normal = "林风站在山顶，望着远方。" * 20
    degraded = "冷在场于第七层深度。冷值7.3，在场度0.89。" * 20

    baseline = compute_linguistic_metrics(normal)
    current = compute_linguistic_metrics(degraded)
    result = detect_drift(current, baseline)

    assert result.is_drift
    assert result.severity in ("WARN", "HARD", "ESCALATE")
    assert len(result.message) > 20


def test_escalate_without_is_drift_reachable():
    """R3 (F612): stm >100‰ (ESCALATE) reachable with is_drift=False.
    baseline stm=30 使比值 110/30≈3.7 不越阈——正是 F612 的「baseline 污染」场景。
    """
    baseline = {"dialogue_density": 50.0, "system_term_density": 30.0}
    current = {"dialogue_density": 30.0, "system_term_density": 110.0}  # 比值正常, stm 超标
    result = detect_drift(current, baseline)
    assert result.severity == "ESCALATE"
    assert result.is_drift is False  # 正是 F612 场景


def test_is_drift_implies_at_least_warn():
    """R3 安全前提(须固化): is_drift=True implies severity >= WARN."""
    import itertools

    for stm, dlg in itertools.product([0.0, 35.0, 60.0, 110.0], [50.0, 5.0, 0.0]):
        base = {"dialogue_density": 50.0, "system_term_density": 1.0}
        cur = {"dialogue_density": dlg, "system_term_density": stm}
        r = detect_drift(cur, base)
        if r.is_drift:
            assert r.severity in ("WARN", "HARD", "ESCALATE"), (stm, dlg, r)


def test_escalate_message_reflects_severity():
    """R3 附带: severity=ESCALATE + is_drift=False 时 message 不得称'未检出'."""
    baseline = {"dialogue_density": 50.0, "system_term_density": 30.0}
    current = {"dialogue_density": 30.0, "system_term_density": 110.0}
    r = detect_drift(current, baseline)
    assert "No linguistic drift" not in r.message
    assert "ESCALATE" in r.message


def test_stm_110_escalate_raises_through_check(tmp_path):
    """R3 验收原文: stm 110 permille 触发 ESCALATE — 经 _check_linguistic_drift 断言 raise."""
    import json
    import shutil

    from shenbi.pipeline.chapter_loop import DriftEscalationError, _check_linguistic_drift

    src = Path("tests/fixtures/multi-chapter-example")
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    for ch in (1, 2, 3):
        shutil.copy(src / f"chapter-{ch}.md", chapters / f"chapter-{ch}.md")
    (chapters / "chapter-4.md").write_text(
        "冷在场于第七层深度。冷值7.3，在场度0.89。系统阈值参数格式串。" * 30,
        encoding="utf-8",
    )
    style = tmp_path / "style"
    style.mkdir()
    # 污染 baseline：stm=30 使 ch4 比值不越阈、is_drift=False，纯绝对阈值 ESCALATE
    (style / "linguistic_baseline.json").write_text(
        json.dumps({"dialogue_density": 50.0, "system_term_density": 30.0}),
        encoding="utf-8",
    )
    with pytest.raises(DriftEscalationError):
        _check_linguistic_drift(tmp_path, 4)
