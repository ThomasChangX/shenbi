import pytest

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
        # U+200B is a zero-width character; removed per _normalize_ws spec
        assert match_field("ab", "a\u200bb") is True


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


class TestPartialMatchEscapeHatch:
    """Spec #9 R3 (F218): any declared field missing -> full file + WARN
    (AGENTS.md field-level reads contract), not silent partial drop.
    """

    def test_partial_match_returns_full_text(self):
        from shenbi.contracts.fields import filter_to_fields

        text = "## A\na\n\n## B\nb\n\n## C\nc"
        out, matched = filter_to_fields(text, ["A", "B", "MISSING"], "x.md")
        assert matched is False
        assert out == text  # full-file fallback, not the partial fragment

    def test_partial_match_warns_with_missing_list(self):
        from shenbi.contracts import fields as fields_mod

        text = "## A\na\n\n## B\nb"
        warned: list[str] = []
        orig = fields_mod.log.warning

        def spy(event: str, **kw: object) -> None:
            warned.append(event)
            orig(event, **kw)

        fields_mod.log.warning = spy  # type: ignore[method-assign]
        try:
            fields_mod.filter_to_fields(text, ["A", "MISSING1", "MISSING2"], "x.md")
        finally:
            fields_mod.log.warning = orig  # type: ignore[method-assign]
        assert "field_filter_missing_fields" in warned

    def test_full_match_still_filters(self):
        from shenbi.contracts.fields import filter_to_fields

        text = "## A\na\n\n## B\nb"
        out, matched = filter_to_fields(text, ["A", "B"], "x.md")
        assert matched is True
        assert "## A" in out and "## B" in out

    def test_json_partial_returns_full(self):
        from shenbi.contracts.fields import filter_to_fields

        out, matched = filter_to_fields('{"a": 1, "b": 2}', ["a", "z"], "x.json")
        assert matched is False
        assert '"b"' in out  # full-file fallback

    def test_json_full_match_still_projects(self):
        from shenbi.contracts.fields import filter_to_fields

        out, matched = filter_to_fields('{"a": 1, "b": 2}', ["a"], "x.json")
        assert matched is True
        assert '"b"' not in out


# --- Spec #16: frontmatter/H2 extraction hardening (F263/F264/F271) -------


class TestExtractH2SectionsSpec16:
    def test_duplicate_h2_first_wins(self) -> None:
        """F264: a repeated H2 must not overwrite the first section's body."""
        from shenbi.contracts.fields import extract_h2_sections

        text = "## A\nfirst body\n\n## B\nother\n\n## A\nsecond body\n"
        sections = extract_h2_sections(text)
        assert sections["A"] == "first body"
        assert sections["B"] == "other"

    def test_h2_inside_fenced_code_ignored(self) -> None:
        """F271: `## ` lines inside ``` fences are content, not headings."""
        from shenbi.contracts.fields import extract_h2_sections

        text = "## Real\noutside\n\n```\n## Fake\nfenced\n```\n"
        sections = extract_h2_sections(text)
        assert "Fake" not in sections
        assert "Real" in sections


class TestProductionCurrentStateF845:
    """Spec #28 R1/F845: revised fields must hit the production-tree copy."""

    def test_production_current_state_declared_fields_hit_no_escape_hatch(self, monkeypatch):
        from pathlib import Path

        from shenbi.contracts import fields as fields_mod

        prod = Path(__file__).resolve().parents[2] / "fixtures" / "truth-current_state-xinghuo.md"
        text = prod.read_text(encoding="utf-8")
        warns: list[str] = []
        monkeypatch.setattr(
            fields_mod.log, "warning", lambda event, **kw: warns.append(event), raising=True
        )
        filtered, matched = fields_mod.filter_to_fields(
            text, ["系统演化阶段", "参数当前位置", "进行中的情节线"], str(prod)
        )
        assert matched is True
        assert "系统演化阶段" in filtered
        assert not warns  # no field_filter_missing_fields escape-hatch


@pytest.mark.c13_regression
def test_duplicate_h2_warns() -> None:
    """F233 residual: duplicate H2 sections are disclosed (first-wins kept)."""
    from structlog.testing import capture_logs

    from shenbi.contracts.fields import extract_h2_sections

    text = "## 系统演化阶段\n第一段\n## 系统演化阶段\n第二段\n"
    with capture_logs() as logs:
        sections = extract_h2_sections(text)
    assert sections["系统演化阶段"] == "第一段"
    assert any(
        e.get("event") == "duplicate_h2_first_wins" and e.get("heading") == "系统演化阶段"
        for e in logs
        if e.get("log_level") == "warning"
    )


@pytest.mark.c13_regression
def test_unknown_extension_passthrough_warns() -> None:
    """T305: non-md/json extensions pass through with a WARN."""
    from structlog.testing import capture_logs

    with capture_logs() as logs:
        text, matched = filter_to_fields("# 不过滤", ["字段"], "data/list.yaml")
    assert text == "# 不过滤" and matched is True
    assert any(
        e.get("event") == "field_filter_unknown_extension_passthrough"
        for e in logs
        if e.get("log_level") == "warning"
    )
