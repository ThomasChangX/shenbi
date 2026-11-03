"""Spec #85 T1 — truth_format leaf module (single source for truth-file formats).

Covers: canonical HOOK_ID_RE acceptance/rejections, canon_hook_id semantics,
THREAD_ID_RE, split_frontmatter fence contract, iter_sections exact-level,
HOOK_HEADING_RE two-group contract, find_hook_ids family filter + canon
normalization, hook_family_source embeddable-unit contract, table helpers.
"""

from __future__ import annotations

import re

import pytest

from shenbi.truth_format import (
    HOOK_HEADING_RE,
    HOOK_ID_RE,
    THREAD_ID_RE,
    canon_hook_id,
    find_hook_ids,
    hook_family_source,
    is_separator_row,
    iter_sections,
    split_frontmatter,
    split_table_cells,
)


class TestHookIdRe:
    def test_full_family_acceptance(self) -> None:
        for token in ("MH01", "MH14", "CP-004", "CP009", "H01", "P0-4", "P0-14"):
            m = HOOK_ID_RE.search(f"前置 {token} 后置")
            assert m is not None and m.group(0) == token

    def test_boundary_negatives(self) -> None:
        for token in ("H2O", "P53", "CPR12", "MP3"):
            assert HOOK_ID_RE.search(f"{token} 上下文") is None

    def test_controlled_false_positives_registered(self) -> None:
        # §1.3 已登记受控误报三形（CJK 非 ASCII 边界）
        m1 = HOOK_ID_RE.search("第H2节")
        m2 = HOOK_ID_RE.search("H-1 项")
        m3 = HOOK_ID_RE.search("MH02编年")
        assert m1 is not None and m1.group(0) == "H2"
        assert m2 is not None and m2.group(0) == "H-1"
        assert m3 is not None and m3.group(0) == "MH02"

    def test_no_bare_p_without_hyphen(self) -> None:
        # P14（无连字符）无生产证据，不纳入
        assert HOOK_ID_RE.search("优先级 P14 级") is None


class TestCanonHookId:
    def test_equivalence_forms(self) -> None:
        assert canon_hook_id("MH-001") == "MH1"
        assert canon_hook_id("MH01") == "MH1"
        assert canon_hook_id("mh1") == "MH1"
        assert canon_hook_id("CP-004") == "CP4"

    def test_p_family_passthrough_identity(self) -> None:
        # P 族连字符在数字中间：fullmatch 失败 → pass-through 恒等（M4 整串方案前提）
        assert canon_hook_id("P0-4") == "P0-4"

    def test_non_family_passthrough_upper(self) -> None:
        assert canon_hook_id("CH1-L1") == "CH1-L1"


class TestThreadIdRe:
    def test_thread_tokens(self) -> None:
        for token in ("A1", "AB12", "D12", "KR3"):
            assert THREAD_ID_RE.search(f"线索 {token} 行") is not None

    def test_thread_boundaries(self) -> None:
        assert THREAD_ID_RE.search("A1234") is None  # 4 位超 {1,3}


class TestSplitFrontmatter:
    def test_fence_inclusive_byte_block(self) -> None:
        text = "---\nname: x\n---\n\n正文"
        fm, body = split_frontmatter(text)
        assert fm == "---\nname: x\n---\n"
        assert body == "\n正文"

    def test_no_frontmatter(self) -> None:
        assert split_frontmatter("正文") == ("", "正文")

    def test_thematic_break_first_line_not_fm(self) -> None:
        # truth_io:1819-1824 的 `----` 主题性断线修复
        assert split_frontmatter("----\n正文") == ("", "----\n正文")

    def test_unterminated_fence_is_not_fm(self) -> None:
        # I1: 「无错误模式」契约的唯一未钉分支——无闭合围栏整体不切
        assert split_frontmatter("---\nfoo") == ("", "---\nfoo")

    def test_mid_document_fence_ignored(self) -> None:
        text = "正文\n---\n仍正文"
        fm, _ = split_frontmatter(text)
        assert fm == ""

    def test_crlf_and_trailing_space_first_line_cured(self) -> None:
        # 首行严格 `---`（rstrip 治愈）：`--- \r\n` 变体仍识别为 fm（M6 精确等值）
        assert split_frontmatter("--- \r\nname: x\r\n---\r\n正文") == (
            "--- \r\nname: x\r\n---\r\n",
            "正文",
        )


class TestIterSections:
    def test_level2_excludes_h3(self) -> None:
        text = "## A\na 内容\n### A1\na1 内容\n## B\nb 内容"
        secs = {title: body for title, body in iter_sections(text, level=2)}
        assert set(secs) == {"A", "B"}
        assert "### A1" in secs["A"]

    def test_level3_excludes_h2_ancestors(self) -> None:
        text = "## A\na\n### A1\na1\n### A2\na2"
        secs = {title: body for title, body in iter_sections(text, level=3)}
        assert set(secs) == {"A1", "A2"}

    def test_h2_with_pound_prefix_not_level2(self) -> None:
        # level 参数是构造正则的插值参数，不是量词上界
        text = "### X\nx"
        assert list(iter_sections(text, level=2)) == []


class TestHookHeadingRe:
    def test_two_group_contract(self) -> None:
        m = HOOK_HEADING_RE.match("### P0-4 TRIGGER 证据")
        assert m is not None
        assert m.group(1) == "###"
        assert m.group(2) == "P0-4"

    def test_multiline_derivation(self) -> None:
        # 块扫描位派生形态（truth_io:411 / ledger POOL_SPEC 消费方式）
        block = re.compile(HOOK_HEADING_RE.pattern, re.MULTILINE)
        hits = [m.group(2) for m in block.finditer("## MH01（名）\n正文\n### CP-004（名）\n正文")]
        assert hits == ["MH01", "CP-004"]


class TestFindHookIds:
    def test_family_filter_mh_only(self) -> None:
        text = "MH01 与 CP-001 与 P0-4"
        assert find_hook_ids(text, families=("MH",)) == ["MH1"]

    def test_family_filter_each_family(self) -> None:
        # M4: P/CP/H 归属过滤钉死
        assert find_hook_ids("CP-001", families=("CP",)) == ["CP1"]
        assert find_hook_ids("H01", families=("H",)) == ["H1"]
        assert find_hook_ids("P0-4", families=("P",)) == ["P0-4"]

    def test_canon_normalized_output(self) -> None:
        assert find_hook_ids("MH-01 与 MH01") == ["MH1", "MH1"]

    def test_all_families_default(self) -> None:
        assert find_hook_ids("MH01 与 CP-001 与 P0-4") == ["MH1", "CP1", "P0-4"]


class TestHookFamilySource:
    def test_single_family_unit(self) -> None:
        assert hook_family_source(("MH",)) == r"(?:MH-?\d{1,4})"

    def test_multi_family_long_first_wrapped(self) -> None:
        src = hook_family_source(("MH", "CP", "H", "P"))
        # 长形在前（MH|CP|H 各带 -? 槽）、P 族殿后、整体 (?:...) 包裹
        assert src == r"(?:MH-?\d{1,4}|CP-?\d{1,4}|H-?\d{1,4}|P\d*-\d{1,4})"

    def test_empty_and_unknown_families_raise(self) -> None:
        # I2: 错误契约钉死——静默返空串会让内嵌 (?:) 匹配一切
        with pytest.raises(ValueError, match="non-empty"):
            hook_family_source(())
        with pytest.raises(ValueError, match="unknown hook families"):
            hook_family_source(("MH", "XX"))

    def test_family_source_invariant_across_module(self) -> None:
        # I3: 单源不变量——_FAMILY_SOURCE 每族子串均须出现在两条 RE 的 pattern
        # （spec §3 残余风险②「新族同步家表」在 T10 lint 前的唯一守卫）
        import shenbi.truth_format as tf

        for fam, src_frag in tf._FAMILY_SOURCE.items():
            assert src_frag in HOOK_ID_RE.pattern, fam
            assert src_frag in HOOK_HEADING_RE.pattern, fam

    def test_multifamily_embedding_regression(self) -> None:
        # §2.3.1 C 层 :383/:588 组合形内嵌回归：单一可内嵌单元、单反斜杠、re.match
        src = hook_family_source(("MH", "CP", "H", "P"))
        m = re.match(rf"^\|\s*{src}(?=[\s（(｜|]|$)", "| MH01（名） | x |")
        assert m is not None and m.group(0) == "| MH01"
        # probe32 陷阱防住：CJK 直连不 key
        assert re.match(rf"^\|\s*{src}(?=[\s（(｜|]|$)", "| MH02编年 | x |") is None


class TestTableHelpers:
    def test_split_table_cells_guard(self) -> None:
        assert split_table_cells("| a | b |") == ["a", "b"]
        assert split_table_cells("a | b") is None

    def test_is_separator_row(self) -> None:
        assert is_separator_row(["---", ":---:"])
        assert not is_separator_row(["---", "x"])


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
