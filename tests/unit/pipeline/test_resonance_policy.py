"""spec #106 T1: dynamic resonance floor computation.

Structural trend-table inputs constructed inline (G0.9: structural inputs
allowed; these are table layouts, not skill-output impersonation). Replay
values are PINNED to the real vol1 scored sequence (ch1-13) so the
interpolation convention is asserted against ground truth — a synthetic
sequence would reward the forbidden nearest-rank convention.
"""

from pathlib import Path

import pytest

from shenbi.config.thresholds import DEFAULT_THRESHOLDS
from shenbi.contracts.enums import ResonancePolicyMode
from shenbi.pipeline.resonance_policy import (
    effective_resonance_floor,
    resonance_policy_of,
    scored_trend_rows,
)

HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
    " | overall | confidence | human_overridden |"
)
SEP = (
    "|---------|--------------|---------|-----------|---------|---------"
    "|---------|-----------|------------------|"
)
#: vol1 truth: ch1-13 scored rows (ch6/8/10 missing; ch11/12/13 = 79/81/79)
VOL1_FIRST13 = [78, 74, 76, 78, 79, 79, 80, 79, 81, 79]


def _trend(tmp_path: Path, rows: list[str]) -> Path:
    p = tmp_path / "truth" / "resonance_trend.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join([HEADER, SEP, *rows]) + "\n", encoding="utf-8")
    return p


def _row(ch: int, overall, ho: str = "") -> str:
    return f"| {ch} | 推进 | 21 | 20 | 21 | 15 | {overall} | mid | {ho} |"


def _config(**over):
    from shenbi.pipeline.state import PipelineConfig

    return PipelineConfig(**over) if over else PipelineConfig()


def test_scored_rows_parse_pending_and_override(tmp_path):
    _trend(tmp_path, [_row(1, 78), _row(2, "pending"), _row(3, 74, ho="true")])
    rows = scored_trend_rows(tmp_path)
    assert rows == [(1, 78.0, False), (3, 74.0, True)]  # pending 剔除；override 保留带旗


def test_floor_p25_linear_interpolation_vol1_truth(tmp_path):
    # vol1 ch1-13 前序 10 行 → inclusive Q1 = 78.0（ch14 实弹 floor 逐字复现）
    rows = [
        _row(ch, s) for ch, s in zip([1, 2, 3, 4, 5, 7, 9, 11, 12, 13], VOL1_FIRST13, strict=True)
    ]
    _trend(tmp_path, rows)
    fc = effective_resonance_floor(tmp_path, 14, _config())
    assert fc.floor == pytest.approx(78.0)
    assert fc.source == "p25" and fc.window_rows == 10


def test_floor_prior_rows_only_excludes_current(tmp_path):
    rows = [_row(i, 80) for i in range(1, 12)]  # 11 行含 ch11
    _trend(tmp_path, rows)
    fc = effective_resonance_floor(tmp_path, 11, _config())
    assert fc.window_rows == 10  # 前序 ch1-10 入窗；当前章 ch11 不入窗


def test_floor_cold_start_falls_back_to_config_65(tmp_path):
    _trend(tmp_path, [_row(1, 78)])  # 前序仅 1 行 <8
    fc = effective_resonance_floor(tmp_path, 2, _config())
    assert fc.floor == float(DEFAULT_THRESHOLDS.resonance_global_floor) == 65.0
    assert fc.source == "config_fallback"


def test_floor_override_starved_warns_not_silent(tmp_path, capsys):
    from shenbi.logging import configure_logging

    configure_logging()
    # 前序 10 行但 9 行 override → 非 override 已评分 1 行 <8：回落 65 + WARN
    rows = [_row(1, 78)] + [_row(i, 79, ho="true") for i in range(2, 11)]
    _trend(tmp_path, rows)
    fc = effective_resonance_floor(tmp_path, 12, _config())
    assert fc.floor == 65.0 and fc.source == "window_starved"
    assert fc.overridden_in_window == 9
    assert "resonance_window_starved" in capsys.readouterr().err


def test_floor_clamp_50_80(tmp_path):
    rows = [_row(i, 40) for i in range(1, 11)]  # P25=40 → clamp 下界 50
    _trend(tmp_path, rows)
    assert effective_resonance_floor(tmp_path, 12, _config()).floor == 50.0
    rows2 = [_row(i, 95) for i in range(1, 11)]  # P25=95 → cap 80
    _trend(tmp_path, rows2)
    assert effective_resonance_floor(tmp_path, 12, _config()).floor == 80.0


def test_policy_defaults_shadow_and_override():
    pol = resonance_policy_of(_config())
    assert pol["mode"] is ResonancePolicyMode.SHADOW
    assert pol["percentile"] == 25 and pol["window"] == 20 and pol["cap"] == 80
    pol2 = resonance_policy_of(_config(resonance_policy={"mode": "armed"}))
    assert pol2["mode"] is ResonancePolicyMode.ARMED
    # 非法 mode 值降级 shadow（fail-safe：绝不 armed by accident）
    pol3 = resonance_policy_of(_config(resonance_policy={"mode": "yolo"}))
    assert pol3["mode"] is ResonancePolicyMode.SHADOW


def test_percentile_knob_consumed(tmp_path):
    # audit-T1 I-2: percentile is not a dead knob — P10 gives a lower floor
    # than P25 on the same window (both linear interpolation).
    rows = [
        _row(ch, s) for ch, s in zip([1, 2, 3, 4, 5, 7, 9, 11, 12, 13], VOL1_FIRST13, strict=True)
    ]
    _trend(tmp_path, rows)
    p25 = effective_resonance_floor(tmp_path, 14, _config()).floor
    p10 = effective_resonance_floor(
        tmp_path, 14, _config(resonance_policy={"mode": "shadow", "percentile": 10})
    ).floor
    assert p10 < p25 == 78.0


def test_override_headers_sync_with_compute_drift():
    # audit-T1 M3: the exclusion vocab must not fork from compute_drift.
    from shenbi.pipeline import resonance_policy as rp
    from shenbi.skill_utils.drift_detection import compute_drift

    assert set(rp._OVERRIDE_HEADERS) == set(compute_drift._OVERRIDE_HEADERS)


def test_non_dict_policy_degrades_to_shadow():
    # audit-T1 I-1 (policy side): non-dict config value never crashes routing.
    pol = resonance_policy_of(_config(resonance_policy="armed"))  # type: ignore[arg-type]
    assert pol["mode"] is ResonancePolicyMode.SHADOW
