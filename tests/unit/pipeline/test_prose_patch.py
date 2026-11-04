"""Spec #95 T6a: scene-level merge_prose applier — red/green + characterization."""

from __future__ import annotations

from shenbi.pipeline.prose_patch import (
    ScenePatch,
    apply_scene_replacements,
    parse_scene_replacements,
)

CHAPTER = (
    "# 第9章\n\n## PRE_WRITE_CHECK\n\n- x\n\n"
    "<!--SCENE-->\n场景一原文甲。\n钩一\n"
    "<!--SCENE-->\n场景二原文乙。\n钩二\n"
    "<!--SCENE-->\n场景三原文丙。\n钩三\n"
    "\n## POST_WRITE_SELF_CHECK\n\n- y\n"
)


def test_parse_scene_replacements() -> None:
    payload = "场景1：\n新文一。\n\n场景2：\n新文二。\n"
    patches = parse_scene_replacements(payload)
    assert [p.scene_no for p in patches] == [1, 2]
    assert patches[0].scene_text == "新文一。"


def test_only_listed_scenes_replaced() -> None:
    res = apply_scene_replacements(CHAPTER, [ScenePatch(2, "替换后的场景二。\n新钩二")])
    assert res.unmatched == ()
    assert "场景一原文甲。" in res.new_text  # 未列场景不动
    assert "替换后的场景二。" in res.new_text and "新钩二" in res.new_text
    assert "场景二原文乙。" not in res.new_text
    assert "场景三原文丙。" in res.new_text
    assert "## POST_WRITE_SELF_CHECK" in res.new_text  # PRE/POST 原样保留


def test_unmatched_scene_number_fails_loud() -> None:
    res = apply_scene_replacements(CHAPTER, [ScenePatch(9, "不存在场景")])
    assert res.unmatched == ("场景9",)
    assert res.new_text == CHAPTER  # 未动原章


def test_idempotent_reapplication() -> None:
    patches = [ScenePatch(1, "新文一。"), ScenePatch(3, "新文三。")]
    once = apply_scene_replacements(CHAPTER, patches)
    twice = apply_scene_replacements(once.new_text, patches)
    assert twice.unmatched == ()
    assert once.new_text == twice.new_text  # 幂等（定位键整体替换）


def test_no_markers_all_unmatched() -> None:
    res = apply_scene_replacements("# 无场景章\n正文", [ScenePatch(1, "x")])
    assert res.unmatched == ("场景1",)
