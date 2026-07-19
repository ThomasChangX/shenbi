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


def test_check_opening_similarity_identical():
    from shenbi.skill_utils.drift_detection.linguistic_drift import check_opening_similarity

    # Same opening paragraph, different content after 300 chars.
    # The opening must be >= 300 chars so both [:300] slices are identical.
    opening = (
        "冷在场于第七层深度。冷知道深度在第八层。"
        "参数确认：冷值七点三，在场度零点八九。系统运行正常。"
        "周围的空间微微扭曲，冷感受到一种异样的波动。"
        "这是从未有过的体验。冷闭上眼，深吸一口气。"
        "深度感知器发出连续的蜂鸣声，表示一切在可控范围内。"
        "冷在场于第七层深度。冷知道深度在持续变化中。"
        "参数更新中，请稍候。系统确认：冷值稳定，在场度正常。"
        "冷在场于第七层深度。冷知道深度已锁定。一切就绪。"
        "冷在场于第七层深度。冷知道深度在第八层。冷知道深度已锁定。"
        "冷在场于第七层深度。冷知道深度在第八层。一切就绪。系统正常。"
        "冷在场于第七层深度。冷知道深度已锁定。一切就绪系统正常。"
    )  # >= 300 chars to fill the comparison window entirely
    ch1 = opening + "接下来是完全不同的故事内容。" * 30
    ch2 = opening + "后来的发展截然不同且出乎意料。" * 30
    similarity = check_opening_similarity(ch1, ch2)
    assert similarity > 0.9, f"Expected >0.9, got {similarity}"


def test_check_opening_similarity_different():
    from shenbi.skill_utils.drift_detection.linguistic_drift import check_opening_similarity

    ch1 = (
        "林风站在山顶，望着远方的云海翻涌。晨光透过云层洒下金色的光辉。"
        "山风拂过他的衣角，带来松涛的低语。他已经在这里站了整整一个时辰。"
        "脑海中回放着过去一年的种种经历，那些战斗与离别。"
        "他想起了师傅临别前说的那句话。"
        "林风站在山顶，望着远方的云海翻涌。晨光透过云层洒下金色的光辉。"
    )
    ch2 = (
        "陈维民推开实验室的门，灯光自动亮起。各种仪器发出轻微的嗡鸣声。"
        "他快步走到操作台前，屏幕上跳动着复杂的数据流。最后一个样本已经完成。"
        "手指敲击键盘的声音在空旷的实验室里显得格外清晰。"
        "这个项目耗费了三年的心血，终于到了最关键的时刻。"
        "陈维民推开实验室的门，灯光自动亮起。各种仪器发出轻微的嗡鸣声。"
    )
    similarity = check_opening_similarity(ch1, ch2)
    assert similarity < 0.6, f"Expected <0.6, got {similarity}"


def test_check_window_redundancy_detects_looping():
    from shenbi.skill_utils.drift_detection.linguistic_drift import check_window_redundancy

    # Chapters with highly similar structure/vocabulary simulating content looping.
    # Each chapter varies only the depth number and parameter values.
    tmpl = (
        "冷在场于第{n1}层深度。系统参数确认：冷值{val1}，在场度{val2}。"
        "冷知道深度在持续变化。参数更新中，请稍候。"
        "周围的空间微微扭曲，冷感受到一种异样的波动。"
        "这是第{n2}次深度跳跃尝试。冷在场于第{n3}层深度。"
        "系统参数：冷值{val3}，在场度{val4}。一切正常。"
    )
    chapters = [
        tmpl.format(
            n1="七",
            val1="七点三",
            val2="零点八九",
            n2="三",
            n3="七",
            val3="七点三",
            val4="零点八九",
        ),
        tmpl.format(
            n1="八",
            val1="八点一",
            val2="零点九二",
            n2="四",
            n3="八",
            val3="八点一",
            val4="零点九二",
        ),
        tmpl.format(
            n1="九",
            val1="九点零",
            val2="零点九五",
            n2="五",
            n3="九",
            val3="九点零",
            val4="零点九五",
        ),
        tmpl.format(
            n1="十",
            val1="十点二",
            val2="零点九一",
            n2="六",
            n3="十",
            val3="十点二",
            val4="零点九一",
        ),
    ]
    max_sim = check_window_redundancy(chapters, window_size=4)
    assert max_sim > 0.35, f"Expected >0.35, got {max_sim}"
