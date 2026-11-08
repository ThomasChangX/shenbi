"""Spec #99 (4) direct tests: truth_io single-source heading grammar helper
(dual anchors / whitespace tolerance / bundle strip / write-path
increment-family normalization).

These tests pin the SINGLE-SOURCE grammar contract (spec #99 ④): the tolerant
heading grammar lives ONLY in ``increment_heading_re`` — gate, extractor and
write path all consume it. Tampering with any consumer's private copy (the
H4 root cause pattern) breaks these assertions.
"""

from __future__ import annotations

import pytest

from shenbi.pipeline.truth_io import (
    _replace_section,
    increment_heading_re,
    strip_increment_blocks,
)


class TestIncrementHeadingRe:
    @pytest.mark.unit
    def test_halfwidth_spaces_tolerated_both_anchors(self) -> None:
        line = "## 第 47 章状态增量"
        assert increment_heading_re(47).match(line)
        assert increment_heading_re(47, anchored=False).match(line)

    @pytest.mark.unit
    def test_fullwidth_space_u3000_tolerated(self) -> None:
        assert increment_heading_re(47).match("## 第\u300047\u3000章状态增量")

    @pytest.mark.unit
    def test_no_space_form_matches(self) -> None:
        assert increment_heading_re(47).match("## 第47章状态增量")

    @pytest.mark.unit
    def test_nospace_after_hashes_boundary_form_matches(self) -> None:
        # ##第47章 (no space after hashes) — regex tolerates, boundary scan in
        # strip_increment_blocks must not depend on the '## ' prefix.
        assert increment_heading_re(47).match("##第47章状态增量")

    @pytest.mark.unit
    def test_suffixed_heading_anchored_excluded_unanchored_included(self) -> None:
        suffixed = "## 第47章状态增量（手工合并）"
        assert increment_heading_re(47).match(suffixed) is None  # gate 严格形
        assert increment_heading_re(47, anchored=False).match(suffixed)  # 提取器前缀形

    @pytest.mark.unit
    def test_other_chapter_does_not_match(self) -> None:
        assert increment_heading_re(47).match("## 第48章状态增量") is None


class TestStripIncrementBlocks:
    LIVE = (
        "# 角色交互矩阵\n"
        "## 交互总表\n| a | 1 |\n"
        "## 第46章状态增量\n- 旧章行: 保持\n"
        "## 第 47 章状态增量\n### 赵瘸子\n- 自陈: 「旧句」\n"
        "## 第 48 章状态增量\n- 孪生行: 保留前\n"
        "## 交互总表续\n- 尾行: 保持\n"
    )

    @pytest.mark.unit
    def test_spaced_leader_block_stripped_with_subheadings(self) -> None:
        out = strip_increment_blocks(self.LIVE, [47])
        assert "自陈" not in out  # 子标题 ### 赵瘸子 下成员随块剥离
        assert "第 47 章状态增量" not in out

    @pytest.mark.unit
    def test_bundle_twin_stripped_together(self) -> None:
        out = strip_increment_blocks(self.LIVE, [47, 48])
        assert "自陈" not in out and "孪生行" not in out

    @pytest.mark.unit
    def test_other_chapters_and_base_mass_kept(self) -> None:
        out = strip_increment_blocks(self.LIVE, [47])
        assert "第46章状态增量" in out and "旧章行" in out
        assert "孪生行" in out and "尾行" in out and "交互总表" in out

    @pytest.mark.unit
    def test_nospace_boundary_heading_form_stripped(self) -> None:
        live = "## 第47章状态增量\n- x: y\n## 尾节\n- t: 1\n"
        out = strip_increment_blocks(live, [47])
        assert "- x: y" not in out and "- t: 1" in out


class TestWritePathIncrementNormalization:
    @pytest.mark.unit
    def test_heading_form_mismatch_still_replaces(self) -> None:
        live = "## 第 47 章状态增量\n- 旧: 形差异\n## 尾节\n- t: 1\n"
        section = "## 第47章状态增量\n- 新: 归一替换\n"
        merged = _replace_section(live, section)
        assert merged is not None
        assert "- 新: 归一替换" in merged and "- 旧: 形差异" not in merged

    @pytest.mark.unit
    def test_non_increment_headings_stay_exact_match(self) -> None:
        live = "## 交互总表\n- a: 1\n"
        # 形不一致的非增量族标题不得归一命中（红线：仅增量族）
        assert _replace_section(live, "## 交互总表 \n- b: 2\n") is None
