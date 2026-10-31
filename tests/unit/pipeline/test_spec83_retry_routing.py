"""spec #83 T4: retry family routing + matrix diff-area WARN + iron-law pointer."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.retry_routing import classify_retry_family, targeted_feedback_addendum


def test_family_classification_seven_prefixes() -> None:
    # 输入=retry_feedback 文本（monitor_rewind issues 原样进反馈；前缀即结构化 token）
    assert classify_retry_family("- word_band: ch25 短 380\n- G4.word_count: 差 500") == "length"
    assert classify_retry_family("- G4.cd ch25:quote 缺锚") == "content"
    assert classify_retry_family("- scene_domain: 4场景\n- composition: 拆") == "structure"
    # 混合串按优先级 length>structure>content（ch25 全混族主形态）
    assert classify_retry_family("- XC: 单位词根\n- CH:12 缺段") == "structure"
    assert classify_retry_family("- word_band: 短\n- G4.cd: 锚") == "length"


def test_g4_hard_check_id_prefix_channel() -> None:
    # g4_hard check_ids 进反馈文本后同前缀通道（剥 G4. 归一不在此层——前缀 token 匹配）
    assert classify_retry_family("- cp.prop_decl:staging/plans/x.md") == "other"  # planning 族
    assert classify_retry_family("- G4.cd.post_quote_verbatim:x") == "content"


def test_routing_addendum_shapes() -> None:
    assert "扩写" in targeted_feedback_addendum("length", "...")
    assert "场景结构" in targeted_feedback_addendum("structure", "...")
    assert "引句/数字锚" in targeted_feedback_addendum("content", "...")
    assert targeted_feedback_addendum("other", "...") == ""


def test_matrix_structure_warn_channel(tmp_path: Path) -> None:
    # 返回形态 (fails, warns)：全量重写 >50% 走 warns（观测非 FAIL）
    from shenbi.gates.g4.state_settling import _check_matrix_structure

    staging = tmp_path / "character_matrix.md"
    live_dir = tmp_path.parent / (tmp_path.name + "-live")
    # 无 live sibling → 双空（幂等早退）
    fails, warns = _check_matrix_structure(staging)
    assert fails == [] and warns == []
