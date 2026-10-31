"""spec #83 T4: retry family routing + matrix diff-area WARN + iron-law pointer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import shenbi.gates.g4.state_settling as state_settling_mod
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
    # 幂等早退：无 live sibling → 双空
    from shenbi.gates.g4.state_settling import _check_matrix_structure

    staging = tmp_path / "character_matrix.md"
    fails, warns = _check_matrix_structure(staging)
    assert fails == [] and warns == []


def test_matrix_diff_area_warn_cooccurs_with_fails(tmp_path: Path) -> None:
    """>50% 重写：WARN 与 content_dropped FAIL 共存（audit-T7 I1 契约钉测）。"""
    from shenbi.gates.g4.state_settling import _check_matrix_structure

    live = tmp_path / "character_matrix.md"
    live.write_text(
        "---\ntype: truth\n---\n\n"
        + "".join(f"## 人物{i}\n- 特征{i}甲\n- 特征{i}乙\n" for i in range(4)),
        encoding="utf-8",
    )
    staged = tmp_path / "character_matrix.staged.md"
    # staged 全量重写：仅保留人物 0（2/8 内容行）→ dropped>50%
    staged.write_text("---\ntype: truth\n---\n\n## 人物0\n- 特征0甲\n- 特征0乙\n", encoding="utf-8")
    with (
        patch.object(state_settling_mod, "_live_sibling", return_value=live),
        patch.object(state_settling_mod, "_current_settle_chapter", return_value=None),
    ):
        fails, warns = _check_matrix_structure(staged)
    assert fails  # content_dropped FAIL 支路照发（每 dropped 行）
    assert any("diff_area" in w for w in warns)  # >50% WARN 共存
    # ≤50% 无 WARN：保留 3/4 人物块（6/8 行）
    staged.write_text(
        "---\ntype: truth\n---\n\n"
        + "".join(f"## 人物{i}\n- 特征{i}甲\n- 特征{i}乙\n" for i in range(3)),
        encoding="utf-8",
    )
    with (
        patch.object(state_settling_mod, "_live_sibling", return_value=live),
        patch.object(state_settling_mod, "_current_settle_chapter", return_value=None),
    ):
        fails2, warns2 = _check_matrix_structure(staged)
    assert not any("diff_area" in w for w in warns2)


def test_ch_space_form_routes_structure() -> None:
    # audit-T7 M1：语料实形 `CH 标记章号与 bundle 章集不符: …`（空格无冒号）→ structure
    assert classify_retry_family("- CH 标记章号与 bundle 章集不符: ch25") == "structure"
