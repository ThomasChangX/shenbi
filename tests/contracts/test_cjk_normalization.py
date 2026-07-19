"""Test CJK zero-width and NFKC normalization in fields.py."""

from shenbi.contracts.fields import _normalize_ws


class TestCJKNormalization:
    def test_normalizes_ideographic_space(self):
        text = "第一章\u3000开始"
        result = _normalize_ws(text)
        assert "\u3000" not in result

    def test_strips_zero_width_non_joiner(self):
        text = "测试\u200c文本"
        result = _normalize_ws(text)
        assert "\u200c" not in result

    def test_strips_zero_width_space(self):
        text = "测试\u200b文本"
        result = _normalize_ws(text)
        assert "\u200b" not in result

    def test_strips_byte_order_mark(self):
        text = "\ufeff测试文本"
        result = _normalize_ws(text)
        assert "\ufeff" not in result

    def test_strips_zero_width_joiner(self):
        text = "测试\u200d文本"
        result = _normalize_ws(text)
        assert "\u200d" not in result

    def test_applies_nfkc_normalization(self):
        # Fullwidth ASCII 'A' (U+FF21) should normalize to 'A' (U+0041)
        text = "\uff21BC"
        result = _normalize_ws(text)
        assert "ABC" in result

    def test_collapses_multiple_spaces(self):
        text = "第一章   第二章"
        result = _normalize_ws(text)
        assert "第一章 第二章" in result

    def test_strips_leading_trailing_whitespace(self):
        text = "  测试文本  "
        result = _normalize_ws(text)
        assert result == "测试文本"

    def test_preserves_normal_text(self):
        text = "第一章 废料场"
        result = _normalize_ws(text)
        assert result == "第一章 废料场"
