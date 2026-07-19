# tests/unit/skill_utils/drift_detection/test_linguistic_drift.py

from shenbi.skill_utils.drift_detection.linguistic_drift import (
    compute_linguistic_metrics,
    detect_drift,
    frequency_divergence_alarms,
)

NORMAL_PROSE = """
林风站在废料场边缘，望着远处燃烧的天际线。他的手指无意识地摩挲着口袋里的金属碎片。
"你确定要这么做？"陈维民的声音从身后传来，带着一丝不易察觉的颤抖。
林风没有回头。"没有别的路了。"
"""

DEGRADED_PROSE = """
冷在场于第七层深度。系统参数确认：冷值 7.3，在场度 0.89。
冷知道深度在第八层。参数更新：冷值 8.1，在场度 0.92。
冷在场于第九层深度。系统确认：冷值 9.0，在场度 0.95。
静在场。光冷。隙在场。
"""


def test_compute_metrics_normal_prose():
    metrics = compute_linguistic_metrics(NORMAL_PROSE)
    assert metrics["system_term_density"] < 10.0  # < 10 per mille
    assert metrics["dialogue_density"] > 0.0  # has dialogue
    assert metrics["em_dash_density"] < 10.0


def test_compute_metrics_degraded_prose():
    metrics = compute_linguistic_metrics(DEGRADED_PROSE)
    assert metrics["system_term_density"] > 50.0  # > 50 per mille
    assert metrics["short_sentence_chain_density"] > 0.0


def test_detect_drift_triggers_on_large_deviation():
    baseline = compute_linguistic_metrics(NORMAL_PROSE)
    current = compute_linguistic_metrics(DEGRADED_PROSE)
    result = detect_drift(current, baseline)
    assert result.is_drift
    assert result.severity in ("WARN", "HARD", "ESCALATE")


def test_detect_drift_no_false_positive():
    baseline = compute_linguistic_metrics(NORMAL_PROSE)
    similar = NORMAL_PROSE + "\n风起了。\n"
    current = compute_linguistic_metrics(similar)
    result = detect_drift(current, baseline)
    assert not result.is_drift


def test_system_terms_loaded_from_genre_config(tmp_path):
    """SYSTEM_TERMS come from genre-config.json when present (not hardcoded)."""
    import json

    from shenbi.skill_utils.drift_detection.linguistic_drift import load_drift_config

    (tmp_path / "genre-config.json").write_text(
        json.dumps(
            {
                "drift_detection": {
                    "system_terms": ["自定义甲", "自定义乙"],
                    "pattern_fingerprints": ["自定义句式"],
                }
            }
        ),
        encoding="utf-8",
    )

    cfg = load_drift_config(tmp_path)
    assert "自定义甲" in cfg.system_terms
    assert "自定义句式" in cfg.pattern_fingerprints


def test_frequency_divergence_flags_outlier_terms():
    """Generic >3 sigma frequency-divergence alarm catches novel degradation."""
    baseline_text = "林风看着远处的山。" * 50  # normal vocabulary
    # '在场度' is a new outlier term absent from baseline
    degraded = baseline_text + ("在场度 0.89。" * 30)
    current_metrics = compute_linguistic_metrics(degraded)
    baseline_metrics = compute_linguistic_metrics(baseline_text)

    alarms = frequency_divergence_alarms(degraded, baseline_text, sigma_threshold=3.0)
    # The novel outlier term must be flagged without being in SYSTEM_TERMS
    assert any("在场度" in a for a in alarms), (
        "Generic >3 sigma alarm must catch novel degradation terms not in SYSTEM_TERMS"
    )
