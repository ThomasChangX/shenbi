"""Spec #95 维护批（audit-T13 F4）不变量：merge_prose 声明面=场景清单教学面。

三姊妹技能（anti-detect/length-normalizing/style-polishing）曾声明 updates
mode=merge_prose 却教「完整章节写出至 chapters/」——接入管线写面即死线
（写面对非场景清单形态 fail-loud 拒收）。本不变量在 CI 侧锁死双向一致：
任何声明 merge_prose 的技能，其 SKILL.md 必须教场景级替换清单、不得再教
整章直写。新技能加入 merge_prose 族时清单扩这里（有意识扩面，防无意识复发）。
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SKILLS_DIR = _REPO_ROOT / "skills"

#: merge_prose 技能族（当前四员——扩员须同步本清单， forcing 格式教学）。
_EXPECTED_MERGE_PROSE_SKILLS = {
    "shenbi-anti-detect",
    "shenbi-chapter-revision",
    "shenbi-length-normalizing",
    "shenbi-style-polishing",
}

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _merge_prose_skills() -> set[str]:
    found: set[str] = set()
    for skill_md in sorted(_SKILLS_DIR.glob("*/SKILL.md")):
        m = _FRONTMATTER_RE.match(skill_md.read_text(encoding="utf-8"))
        if not m:
            continue
        try:
            front = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        for entry in (front.get("contract") or {}).get("updates") or []:
            if isinstance(entry, dict) and entry.get("mode") == "merge_prose":
                found.add(skill_md.parent.name)
                break
    return found


def test_merge_prose_skill_set_matches_registry() -> None:
    """族员清点：声明面与期望集一致（双向——新增/移除皆为有意识行为）。"""
    assert _merge_prose_skills() == _EXPECTED_MERGE_PROSE_SKILLS


def test_every_merge_prose_skill_teaches_scene_list() -> None:
    """每个 merge_prose 技能：教「场景级替换清单」、不教「完整章节」直写。

    裸词负向（非「完整章节写出」连续子串）——原 F4 形带粗体标记
    （``**完整章节**写出至``），连续子串断言抓不到，裸词才能抓全变体。
    """
    for name in sorted(_EXPECTED_MERGE_PROSE_SKILLS):
        text = (_SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
        assert "场景级替换清单" in text, f"{name}: 未教场景级替换清单主格式"
        assert "完整章节" not in text, f"{name}: 仍教整章直写（F4 类死线）"
