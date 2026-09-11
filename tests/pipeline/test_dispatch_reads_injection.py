"""Spec #58 C20 acceptance 2: declared reads must be injected for the five
read-side P1 skills (offline; F947 — no real dispatch). Precedent:
tests/pipeline/test_dispatch_helper_keys.py tmp_path assembly.
"""

from pathlib import Path

import pytest

from shenbi.pipeline.dispatch_helper import _build_skill_prompt

MARK = "# spec58 acceptance\n"

CASES = [
    # (skill, files to place, expected injected keys, keys that must be ABSENT)
    (
        "shenbi-book-spine-init",  # F803
        [
            "outline/story_frame.md",
            "outline/volume_map.md",
            "novel.json",
            "characters/protagonist.md",
            "world/rules.md",
        ],
        ["characters/protagonist.md", "world/rules.md"],
        [],
    ),
    (
        "shenbi-character-design",  # F809 — nested placement: the dispatcher's
        # stdlib glob has no recursive=True, so `**` is single-level
        # (characters/<dir>/*.md), matching characters/major/alice.md.
        [
            "world/story_bible.md",
            "world/rules.md",
            "outline/chapter_outline.md",
            "outline/three_act.md",
            "characters/major/alice.md",
        ],
        ["outline/chapter_outline.md", "outline/three_act.md", "characters/major/alice.md"],
        [],
    ),
    (
        "shenbi-context-composing",  # F811: near-chapter in, current out
        [
            "plans/chapter-5-plan.md",
            "truth/book_spine.md",
            "truth/book_strata.md",
            "truth/volume_summaries.md",
            "truth/arcs/arc-1.md",
            "truth/chapter_summaries.md",
            "truth/pending_hooks.md",
            "truth/audit_drift.md",
            "world/rules.md",
            "truth/character_matrix.md",
            "style/style_profile.md",
            "chapters/chapter-2.md",
            "chapters/chapter-3.md",
            "chapters/chapter-4.md",
            "chapters/chapter-5.md",
        ],
        ["chapters/chapter-2.md", "chapters/chapter-3.md", "chapters/chapter-4.md"],
        ["chapters/chapter-5.md"],  # N=5: 组装时不存在，不得注入
    ),
    (
        "shenbi-foundation-review",  # F821 (genre-config from the real fixture)
        [
            "world/rules.md",
            "outline/story_frame.md",
            "truth/current_state.md",
            "truth/chapter_summaries.md",
            "truth/book_spine.md",
        ],
        ["genre-config.json", "truth/book_spine.md"],
        [],
    ),
    (
        "shenbi-memory-distill",  # F836: L5 inputs no longer filtered out
        [
            "truth/chapter_summaries.md",
            "truth/volume_summaries.md",
            "truth/pending_hooks.md",
            "truth/character_matrix.md",
            "truth/author_intent.md",
            "truth/book_spine.md",
            "world/rules.md",
        ],
        ["truth/author_intent.md", "truth/book_spine.md", "world/rules.md"],
        [],
    ),
]


@pytest.mark.parametrize("skill,files,expected,absent", CASES)
def test_required_inputs_injected(tmp_path: Path, skill, files, expected, absent):
    for rel in files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(MARK, encoding="utf-8")
    if skill == "shenbi-foundation-review":
        gc = tmp_path / "genre-config.json"
        gc.write_text(
            Path("tests/fixtures/genre-config-example.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    _, user_prompt, _ = _build_skill_prompt(
        skill=skill,
        project_dir=tmp_path,
        prompt="chapter 5",
        chapter=5,
    )
    for key in expected:
        assert key in user_prompt, f"{skill}: expected input not injected: {key}"
    for key in absent:
        assert key not in user_prompt, f"{skill}: must NOT be injected: {key}"
