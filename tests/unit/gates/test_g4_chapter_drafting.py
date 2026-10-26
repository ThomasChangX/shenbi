# ---------------------------------------------------------------------------
# regen v3 F4 (2026-10-27): META-wrapped POST block breaks scene tail boundary
# ---------------------------------------------------------------------------
def test_split_scenes_meta_wrapped_post_block_keeps_prose_last_line() -> None:
    """The bundle POST block is META-wrapped (marker line, then H2) —
    the META marker line precedes the trailing H2, so the H2-anchored tail
    boundary swallowed the marker into the last scene and scene_hook_match
    compared the declared hook against "<!--META-BEGIN-->" as the 末行
    (regen v3 ch1: false FAIL on a perfectly landed hook).
    """
    from shenbi.gates.shared import split_scenes

    text = "\n".join(
        [
            "<!--SCENE-->",
            "场景一正文。",
            "第一钩落款。",
            "<!--SCENE-->",
            "场景二正文。",
            "第二钩落款。",
            "",
            "<!--META-BEGIN-->",
            "## POST_WRITE_SELF_CHECK",
            "",
            "- [ ] 金句位: 燃｜口诀化｜场景2",
            "<!--META-END-->",
        ]
    )
    scenes = split_scenes(text)
    assert len(scenes) == 2
    assert scenes[1][1] == "第二钩落款。", (
        "trailing META wrapper must not become the last scene's last line"
    )
