"""Spec #95 T4 drafting half: scene-level shortfall rides the TARGETED-EDIT channel."""

from __future__ import annotations

import pytest

from shenbi.pipeline.scene_splitter import BundleChapters, split_bundle, validate_split

# 单章双场景 bundle（解剖序=真实章：PRE 块在前、双 H1 其后、SCENE 标记）
_S1 = "灯" * 800
_S2 = "灯" * 700
BUNDLE = (
    "===CH:9===\n"
    "## PRE_WRITE_CHECK\n\n- x\n\n"
    "# 第9章\n"
    "# 短章\n\n"
    "<!--SCENE-->\n"
    + _S1
    + "\n钩一\n<!--SCENE-->\n"
    + _S2
    + "\n钩二\n\n## POST_WRITE_SELF_CHECK\n\n- y\n"
)


def _split() -> BundleChapters:
    return split_bundle(BUNDLE)


@pytest.mark.unit
def test_word_band_reports_scene_gap_and_expansion_hint() -> None:
    chapters = _split()
    issues: list[str] = []
    issues = validate_split(chapters.chapters[0], (2800, 4000))
    text = "\n".join(issues)
    assert "word_band:ch9" in text
    assert "差" in text and "字" in text  # 差值在场
    assert "场景1" in text and "场景2" in text  # 逐场景现值
    assert "扩写建议" in text and "禁整章重写" in text  # 扩拍位建议（TARGETED-EDIT 同款铁律）


@pytest.mark.unit
def test_in_band_clean_stays_clean() -> None:
    # 合法形状：两独立型 1900+1900（word_band 与 scene_domain 双过）
    s = (
        "===CH:9===\n## PRE_WRITE_CHECK\n\n- x\n\n# 第9章\n# 章\n\n<!--SCENE-->\n"
        + "灯" * 1900
        + "\n钩一\n<!--SCENE-->\n"
        + "灯" * 1900
        + "\n钩二\n\n## POST_WRITE_SELF_CHECK\n\n- y\n"
    )
    chapters = split_bundle(s)
    assert validate_split(chapters.chapters[0], (2800, 4000)) == []
