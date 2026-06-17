"""Unit tests for shenbi.gates.shared.

Business rules under test:
- jload/yload file loaders (JSON / YAML frontmatter)
- word_count_md: CJK character counting (excludes code blocks/frontmatter)
- passed/fail JSON formatters
- write_gate_marker: persists PASS results only
- normalize_file_paths: list/string normalization
- count_transition_words: avoids double-counting 然 compounds
- find_report: flexible filename matching
- read_genre_config: returns {} on missing/corrupt
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.shared import (
    count_transition_words,
    fail,
    find_report,
    jload,
    normalize_file_paths,
    passed,
    read_genre_config,
    word_count_md,
    write_gate_marker,
    yload,
)

pytestmark = pytest.mark.unit

# --- TestJload -----------------------------------------------------------


class TestJload:
    def test_loads_valid_json_file(self, tmp_path: Path) -> None:
        f = tmp_path / "x.json"
        f.write_text('{"a": 1, "b": [2, 3]}', encoding="utf-8")
        assert jload(f) == {"a": 1, "b": [2, 3]}

    def test_accepts_path_or_string(self, tmp_path: Path) -> None:
        f = tmp_path / "x.json"
        f.write_text("{}", encoding="utf-8")
        # Both Path object and str should work
        assert jload(f) == {}
        assert jload(str(f)) == {}

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            jload(f)

    def test_handles_utf8_content(self, tmp_path: Path) -> None:
        f = tmp_path / "zh.json"
        f.write_text('{"name": "世界"}', encoding="utf-8")
        assert jload(f)["name"] == "世界"


# --- TestYload -----------------------------------------------------------


class TestYload:
    def test_loads_frontmatter_from_markdown(self, tmp_path: Path) -> None:
        """Markdown files with --- frontmatter fences are parsed for the
        YAML metadata block only (body ignored).
        """
        f = tmp_path / "x.md"
        f.write_text("---\ntype: world\nname: 测试\n---\n# Body\n", encoding="utf-8")
        data = yload(f)
        assert data["type"] == "world"
        assert data["name"] == "测试"

    def test_loads_full_yaml_when_no_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text("key: value\nlist:\n  - a\n  - b\n", encoding="utf-8")
        data = yload(f)
        assert data["key"] == "value"
        assert data["list"] == ["a", "b"]

    def test_returns_empty_dict_for_empty_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("---\n---\n# Body\n", encoding="utf-8")
        assert yload(f) == {}


# --- TestWordCountMd -----------------------------------------------------


class TestWordCountMd:
    """word_count_md counts CJK characters only (re.findall(r"[一-鿿]", c)).
    Frontmatter, code blocks, and meta sections are stripped first.
    """

    def test_counts_cjk_characters_only(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("世界你好", encoding="utf-8")
        assert word_count_md(f) == 4

    def test_ascii_only_returns_zero(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("hello world\nmore ascii", encoding="utf-8")
        assert word_count_md(f) == 0

    def test_strips_yaml_frontmatter_before_counting(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("---\ntype: world\n---\n正文内容", encoding="utf-8")
        assert word_count_md(f) == 4  # only 正文内容

    def test_strips_code_blocks_before_counting(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("正文\n```python\nprint('世界')\n```\n更多内容", encoding="utf-8")
        # 世界 in code block excluded; 正文 + 更多内容 = 6
        assert word_count_md(f) == 6


# --- TestPassedFailFormat ------------------------------------------------


class TestPassedFailFormat:
    def test_passed_emits_pass_status_with_checks(self) -> None:
        result = passed("G0", [{"id": "x", "s": "PASS"}])
        parsed = json.loads(result)
        assert parsed["status"] == "PASS"
        assert parsed["gate"] == "G0"
        assert parsed["checks"] == [{"id": "x", "s": "PASS"}]
        assert "timestamp" in parsed

    def test_fail_emits_fail_status_with_must_fix(self) -> None:
        result = fail("G2", [], "scoring", ["fix chapter length"])
        parsed = json.loads(result)
        assert parsed["status"] == "FAIL"
        assert parsed["blocked_action"] == "scoring"
        assert "fix chapter length" in parsed["must_fix"]

    def test_passed_and_fail_share_timestamp_format(self) -> None:
        """Both emit ISO-8601 timestamps for downstream correlation."""
        p = json.loads(passed("G", []))
        f = json.loads(fail("G", [], "x", []))
        assert "T" in p["timestamp"]
        assert "T" in f["timestamp"]


# --- TestWriteGateMarker -------------------------------------------------


class TestWriteGateMarker:
    def test_writes_marker_file_on_pass(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = passed("G0", [])
        write_gate_marker(
            "G0", "outline.md", "generative", result_str, str(round_dir), ["outline.md"]
        )
        marker = round_dir / "gate-markers" / "G0-outline.md-generative.json"
        assert marker.exists()
        data = json.loads(marker.read_text(encoding="utf-8"))
        assert data["status"] == "PASS"
        assert data["files_checked"] == ["outline.md"]

    def test_skips_writing_on_fail_result(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = fail("G0", [], "scoring", ["x"])
        write_gate_marker("G0", "f.md", "generative", result_str, str(round_dir), [])
        assert not (round_dir / "gate-markers").exists() or not list(
            (round_dir / "gate-markers").iterdir()
        )

    def test_no_op_when_round_dir_none(self, tmp_path: Path) -> None:
        """Without --round-dir, no marker is written (markers are opt-in)."""
        # Should not raise
        write_gate_marker("G0", "f.md", "generative", passed("G0", []), None, ["f.md"])


# --- TestNormalizeFilePaths ----------------------------------------------


class TestNormalizeFilePaths:
    def test_returns_empty_list_for_none(self) -> None:
        assert normalize_file_paths(None) == []

    def test_splits_comma_separated_string(self) -> None:
        result = normalize_file_paths("a.md, b.md, c.md")
        assert result == ["a.md", "b.md", "c.md"]

    def test_passes_through_list_unchanged(self) -> None:
        result = normalize_file_paths(["a.md", "b.md"])
        assert result == ["a.md", "b.md"]

    def test_converts_tuple_to_list_of_strings(self) -> None:
        result = normalize_file_paths(("a.md", "b.md"))
        assert result == ["a.md", "b.md"]
        assert isinstance(result, list)

    def test_strips_whitespace_in_string_split(self) -> None:
        result = normalize_file_paths("  a.md  ,  b.md  ")
        assert result == ["a.md", "b.md"]


# --- TestCountTransitionWords -------------------------------------------


class TestCountTransitionWords:
    """Transition word counting avoids double-counting 然 compounds.
    虽然/然而/当然/自然/忽然 are NOT standalone transitions and get subtracted
    from the bare 然 count; 突然 IS a transition and is double-counted (然
    once + specific once), so 突然 is subtracted first then added back.
    """

    def test_counts_bare_ran(self) -> None:
        assert count_transition_words("然后他走了") == 1

    def test_excludes_ran_in_sui_ran(self) -> None:
        """虽然 means 'although' — not a transition in this framework."""
        assert count_transition_words("虽然下雨") == 0

    def test_excludes_ran_in_ran_er(self) -> None:
        assert count_transition_words("然而困难") == 0

    def test_counts_tu_ran_once(self) -> None:
        """突然 is in TRANSITION_SPECIFIC; the subtraction+addition yields 1."""
        assert count_transition_words("突然，他出现了") == 1

    def test_counts_multiple_transitions(self) -> None:
        text = "然后他走了。不过她留下了。终于大家都睡了。"
        # 然后=1 (然), 不过=1, 终于=1 -> total 3
        assert count_transition_words(text) == 3

    def test_returns_zero_for_empty_string(self) -> None:
        assert count_transition_words("") == 0


# --- TestFindReport ------------------------------------------------------


class TestFindReport:
    def test_finds_skill_test_type_scores_variant(self, tmp_path: Path) -> None:
        """Preferred form: <skill>-<test_type>-scores.json."""
        (tmp_path / "shenbi-x-generative-scores.json").write_text("{}", encoding="utf-8")
        result = find_report(tmp_path, "shenbi-x", "generative")
        assert result is not None
        assert result.name == "shenbi-x-generative-scores.json"

    def test_falls_back_to_skill_test_type_json(self, tmp_path: Path) -> None:
        (tmp_path / "shenbi-x-bug-hunt.json").write_text("{}", encoding="utf-8")
        result = find_report(tmp_path, "shenbi-x", "bug-hunt")
        assert result is not None
        assert result.name == "shenbi-x-bug-hunt.json"

    def test_falls_back_to_skill_json_only(self, tmp_path: Path) -> None:
        (tmp_path / "shenbi-x.json").write_text("{}", encoding="utf-8")
        result = find_report(tmp_path, "shenbi-x", "generative")
        assert result is not None
        assert result.name == "shenbi-x.json"

    def test_returns_none_when_no_match(self, tmp_path: Path) -> None:
        assert find_report(tmp_path, "missing-skill", "generative") is None

    def test_returns_none_when_test_type_none_and_only_typed_files_exist(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "shenbi-x-generative-scores.json").write_text("{}", encoding="utf-8")
        # When test_type is None, only the bare <skill>.json is searched
        assert find_report(tmp_path, "shenbi-x", None) is None


# --- TestReadGenreConfig -------------------------------------------------


class TestReadGenreConfig:
    def test_loads_valid_genre_config(self, tmp_path: Path) -> None:
        (tmp_path / "genre-config.json").write_text(
            json.dumps({"chapter_word": {"default": 3000}}), encoding="utf-8"
        )
        data = read_genre_config(tmp_path)
        assert data["chapter_word"]["default"] == 3000

    def test_returns_empty_dict_when_missing(self, tmp_path: Path) -> None:
        assert read_genre_config(tmp_path) == {}

    def test_returns_empty_dict_on_invalid_json(self, tmp_path: Path) -> None:
        (tmp_path / "genre-config.json").write_text("not json", encoding="utf-8")
        assert read_genre_config(tmp_path) == {}


class TestSharedErrorPaths:
    """Error-path coverage for shared loaders (PR-52 Step 11).

    Note: several Step-11 categories already exist above (find_report None,
    normalize_file_paths None / comma string, write_gate_marker no round_dir),
    so only the genuinely missing non-dict / primitive / empty-file cases are
    added here to avoid duplication.
    """

    @pytest.mark.unit
    def test_jload_raises_on_non_dict_json(self, tmp_path: Path) -> None:
        """Array JSON should raise ValueError, not silently return."""
        p = tmp_path / "array.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError, match="expected JSON object"):
            jload(str(p))

    @pytest.mark.unit
    def test_jload_raises_on_primitive_json(self, tmp_path: Path) -> None:
        """A JSON string/primitive should raise ValueError, not silently return."""
        p = tmp_path / "str.json"
        p.write_text('"just a string"', encoding="utf-8")
        with pytest.raises(ValueError):
            jload(str(p))

    @pytest.mark.unit
    def test_yload_raises_on_non_dict_yaml(self, tmp_path: Path) -> None:
        """A YAML list is not a mapping -> ValueError with expected YAML mapping."""
        p = tmp_path / "list.yaml"
        p.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="expected YAML mapping"):
            yload(str(p))

    @pytest.mark.unit
    def test_yload_returns_empty_dict_for_empty_file(self, tmp_path: Path) -> None:
        """An empty file parses to an empty dict (no error)."""
        p = tmp_path / "empty.yaml"
        p.write_text("", encoding="utf-8")
        assert yload(str(p)) == {}

    @pytest.mark.unit
    def test_unimplemented_returns_valid_json(self) -> None:
        """unimplemented returns a parseable UNIMPLEMENTED JSON string."""
        from shenbi.gates.shared import unimplemented
        result = unimplemented("G-TEST", "test note")
        parsed = json.loads(result)
        assert parsed["status"] == "UNIMPLEMENTED"
        assert parsed["gate"] == "G-TEST"
        assert "note" in parsed
        assert "checks" in parsed
