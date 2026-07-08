from shenbi.contracts.fields import filter_to_fields, match_field


class TestMatchField:
    def test_exact_match(self):
        assert match_field("1. 当前任务", "1. 当前任务") is True

    def test_strips_whitespace(self):
        assert match_field("1. 当前任务", "  1. 当前任务  ") is True

    def test_fullwidth_space_folded(self):
        # I3: U+3000 folded to ASCII space
        assert match_field("1. 当前任务", "1.　当前任务") is True

    def test_multiple_spaces_folded(self):
        assert match_field("1. 当前任务", "1.  当前任务") is True

    def test_no_lowercase(self):
        # Chinese headings: do NOT lowercase (preserves semantics)
        assert match_field("ABC", "abc") is False

    def test_zero_width_not_folded(self):
        # U+200B carries semantic meaning; do NOT fold
        assert match_field("ab", "a\u200bb") is False


class TestFilterToFields:
    MD = "# Title\n\n## 1. 当前任务\n内容A\n\n## 2. 世界设定\n内容B\n\n## 3. 其他\n内容C\n"

    def test_filters_to_declared_sections(self):
        result, matched = filter_to_fields(self.MD, ["1. 当前任务", "2. 世界设定"], "truth/test.md")
        assert matched is True
        assert "内容A" in result
        assert "内容B" in result
        assert "内容C" not in result

    def test_escape_hatch_returns_full_when_no_match(self):
        result, matched = filter_to_fields(self.MD, ["不存在的字段"], "truth/test.md")
        assert matched is False
        assert "内容A" in result  # full text returned

    def test_json_projects_keys(self):
        import json

        data = json.dumps({"fatigueWords": [], "pacing": "fast", "other": "x"})
        result, matched = filter_to_fields(data, ["fatigueWords", "pacing"], "genre-config.json")
        assert matched is True
        assert "fatigueWords" in result
        assert "other" not in result
