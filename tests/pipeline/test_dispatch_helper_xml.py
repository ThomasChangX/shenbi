"""Test that _build_skill_prompt uses <document> XML tags, not nested ``` fences."""


def test_prompt_uses_xml_tags_not_nested_fences():
    """LLM prompts must use <document> tags, not nested ``` fences."""
    import tempfile
    from pathlib import Path

    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        # shenbi-worldbuilding reads novel.json
        (project_dir / "novel.json").write_text('{"title": "Test Novel"}', encoding="utf-8")

        system_prompt, user_prompt, _ = _build_skill_prompt(
            "shenbi-worldbuilding", project_dir, "test prompt", chapter=None
        )

        # Must use <document> tags, not nested ``` fences
        assert "<document" in user_prompt, "Expected <document> tags in user prompt"
        assert "```\n```" not in user_prompt, "Found nested code fences in user prompt"
