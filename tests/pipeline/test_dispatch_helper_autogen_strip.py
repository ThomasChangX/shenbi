"""Tests for auto-gen block stripping from LLM system prompt (spec §3.8)."""

from shenbi.pipeline.dispatch_helper import _strip_autogen_blocks


def test_strip_removes_data_contract_block():
    text = (
        "# Skill\n\n<!-- AUTO-GENERATED from frontmatter — do not edit -->\n"
        "## 数据契约\n\n- **Reads:** foo.md\n"
        "<!-- END AUTO-GENERATED -->\n\n## Body instructions\n"
    )
    stripped = _strip_autogen_blocks(text)
    assert "AUTO-GENERATED" not in stripped
    assert "数据契约" not in stripped
    assert "## Body instructions" in stripped


def test_strip_removes_autocheck_block():
    text = "Intro\n\n<!-- AUTO-CHECK-START -->\n## auto-check (generated -- do not edit)\n<!-- AUTO-CHECK-END -->\n\nBody"
    stripped = _strip_autogen_blocks(text)
    assert "AUTO-CHECK" not in stripped
    assert "auto-check" not in stripped
    assert "Body" in stripped


def test_strip_preserves_body_with_no_blocks():
    text = "Plain skill body with no auto-gen blocks."
    assert _strip_autogen_blocks(text) == text


def test_strip_handles_both_blocks_together():
    text = (
        "Header\n"
        "<!-- AUTO-GENERATED from frontmatter — do not edit -->\nX\n<!-- END AUTO-GENERATED -->\n"
        "Middle\n"
        "<!-- AUTO-CHECK-START -->\nY\n<!-- AUTO-CHECK-END -->\n"
        "Footer\n"
    )
    stripped = _strip_autogen_blocks(text)
    assert "X" not in stripped
    assert "Y" not in stripped
    assert "Header" in stripped
    assert "Middle" in stripped
    assert "Footer" in stripped
