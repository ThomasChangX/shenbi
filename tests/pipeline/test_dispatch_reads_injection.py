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
        # spec #69 T0: outline/ orphan reads re-anchored to genesis-context/.
        [
            "world/story_bible.md",
            "world/rules.md",
            "genesis-context/chapter_outline.md",
            "genesis-context/three_act.md",
            "characters/major/alice.md",
        ],
        [
            "genesis-context/chapter_outline.md",
            "genesis-context/three_act.md",
            "characters/major/alice.md",
        ],
        # T0 re-pin: the retired outline/ orphan paths must NOT be injected.
        ["outline/chapter_outline.md", "outline/three_act.md"],
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
    _, user_prompt, _, _ = _build_skill_prompt(
        skill=skill,
        project_dir=tmp_path,
        prompt="chapter 5",
        chapter=5,
    )
    for key in expected:
        assert key in user_prompt, f"{skill}: expected input not injected: {key}"
    for key in absent:
        assert key not in user_prompt, f"{skill}: must NOT be injected: {key}"


#: spec #69 T1: genesis-context fragments wired into the five genesis skills.
GENESIS_FRAGMENT_CASES = [
    # (skill, staged fragment files, expected-injected subset)
    (
        "shenbi-worldbuilding",
        ["genesis-context/world_rules.md", "novel.json"],
        ["genesis-context/world_rules.md"],
    ),
    (
        "shenbi-story-architecture",
        [
            "genesis-context/three_act.md",
            "genesis-context/plot_lines.md",
            "genesis-context/surface_conflict.md",
            "genesis-context/personal_conflict.md",
            "genesis-context/deep_conflict.md",
            "novel.json",
        ],
        [
            "genesis-context/three_act.md",
            "genesis-context/plot_lines.md",
            "genesis-context/surface_conflict.md",
            "genesis-context/personal_conflict.md",
            "genesis-context/deep_conflict.md",
        ],
    ),
    (
        "shenbi-faction-builder",
        ["genesis-context/forces.md", "novel.json"],
        ["genesis-context/forces.md"],
    ),
    (
        "shenbi-character-design",
        [
            "genesis-context/protagonist.md",
            "genesis-context/chapter_outline.md",
            "genesis-context/three_act.md",
            "world/story_bible.md",
        ],
        ["genesis-context/protagonist.md"],
    ),
    (
        "shenbi-volume-outlining",
        ["genesis-context/chapter_outline.md", "novel.json"],
        ["genesis-context/chapter_outline.md"],
    ),
]


@pytest.mark.parametrize("skill,files,expected", GENESIS_FRAGMENT_CASES)
def test_genesis_fragment_injected(tmp_path: Path, skill, files, expected):
    for rel in files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(MARK, encoding="utf-8")
    _, user_prompt, _, reads_manifest = _build_skill_prompt(
        skill=skill, project_dir=tmp_path, prompt="genesis", chapter=None
    )
    for key in expected:
        assert key in user_prompt, f"{skill}: expected fragment not injected: {key}"
        # spec §3.3 reads_manifest face: injection is recorded (4th return;
        # entries carry {"path": key, "mode": "full", ...}).
        assert any(e.get("path") == key for e in reads_manifest), (
            f"{skill}: {key} missing from reads_manifest"
        )


@pytest.mark.parametrize(
    "skill,fragment",
    [
        ("shenbi-worldbuilding", "genesis-context/world_rules.md"),
        ("shenbi-character-design", "genesis-context/protagonist.md"),
        ("shenbi-character-design", "genesis-context/chapter_outline.md"),
        ("shenbi-character-design", "genesis-context/three_act.md"),
        ("shenbi-story-architecture", "genesis-context/three_act.md"),
        ("shenbi-story-architecture", "genesis-context/plot_lines.md"),
        ("shenbi-story-architecture", "genesis-context/surface_conflict.md"),
        ("shenbi-story-architecture", "genesis-context/personal_conflict.md"),
        ("shenbi-story-architecture", "genesis-context/deep_conflict.md"),
        ("shenbi-faction-builder", "genesis-context/forces.md"),
        ("shenbi-volume-outlining", "genesis-context/chapter_outline.md"),
    ],
)
def test_genesis_fragment_declared(skill, fragment):
    """Spec §3.3 T0/T1: contract-load face asserts the fragment path in reads."""
    from shenbi.contracts.loader import load_contract

    assert fragment in load_contract(skill)["reads"]


def test_genesis_fragments_optional_legacy_project(tmp_path: Path):
    """Spec §1 missing-file semantics: no fragments staged (USER-mode legacy)
    -> prompt assembles fine, no fragment keys, no failure.
    """
    for skill in (
        "shenbi-worldbuilding",
        "shenbi-character-design",
        "shenbi-story-architecture",
        "shenbi-faction-builder",
        "shenbi-volume-outlining",
    ):
        _, user_prompt, _, _ = _build_skill_prompt(
            skill=skill, project_dir=tmp_path, prompt="genesis", chapter=None
        )
        assert "genesis-context/" not in user_prompt


def test_lifecycle_prompt_reachable(tmp_path):
    """Acceptance 5 (spec #59, F947 offline): GENESIS_STEPS step-9 successor assembles a prompt."""
    from shenbi.pipeline.genesis import GENESIS_STEPS

    step9 = next(s for s in GENESIS_STEPS if s.step_num == 9)
    assert step9.skill == "shenbi-foreshadowing-lifecycle"
    system_prompt, user_prompt, output_paths, _ = _build_skill_prompt(
        skill=step9.skill,
        project_dir=tmp_path,
        prompt="genesis",
        chapter=None,
    )
    combined = system_prompt + user_prompt
    assert "foreshadowing-lifecycle" in combined
    assert output_paths, "prompt assembly must carry output paths"


def test_genesis_outputs_override_excludes_per_chapter_writes(tmp_path):
    """Stage-8 review I1 pin: genesis dispatch output set is the GenesisStep's
    declared output — lifecycle's bridge_tracker/audits must NOT appear.
    """
    system_prompt, user_prompt, output_paths, _ = _build_skill_prompt(
        skill="shenbi-foreshadowing-lifecycle",
        project_dir=tmp_path,
        prompt="genesis",
        chapter=None,
        outputs_override=["truth/pending_hooks.md"],
    )
    # persistence set stays contract-full (r2: narrowing dropped genesis
    # artifacts); the PROMPT instruction is what the override narrows
    assert "truth/pending_hooks.md" in output_paths
    assert "truth/bridge_tracker.md" in output_paths  # persistence allowlist intact
    assert "bridge_tracker" not in user_prompt  # prompt instruction narrowed
    assert "audits/chapter" not in user_prompt


def test_staging_prompt_lists_prefixed_paths(tmp_path):
    """Stage-8 r3 C-1 pin: staged prompts list staging/-prefixed paths so the
    prompt instruction and the persistence lookup keys stay identical.
    """
    _, user_prompt, output_paths, _ = _build_skill_prompt(
        skill="shenbi-chapter-planning",
        project_dir=tmp_path,
        prompt="plan chapter 5",
        chapter=5,
        uses_staging=True,
    )
    assert output_paths and all(p.startswith("staging/") for p in output_paths)
    listed = [ln[2:] for ln in user_prompt.splitlines() if ln.startswith("- ") and "/" in ln]
    assert any(p.startswith("staging/") for p in listed), listed


#: F-3 (probe22 adjudication #009 F-3 / #010): settle's contract declares
#: ``audits/chapter-N-foreshadowing.md`` as its sole reinforcement authority
#: (「唯一确证来源」), but the lifecycle audit lands in ``staging/audits/``
#: 78 seconds before settle dispatches — read resolution only saw live
#: paths, the declared read silently resolved to nothing, and settle
#: invented MH02/MH09 reinforcements from prose. A checkpoint-gated writer
#: must read the SAME staging world it writes into.
AUDIT_MARK = "# lifecycle audit: MH04 advance; MH02 defer（沉默 1 章）\n"


def test_staging_gated_dispatch_serves_staging_twin_read(tmp_path: Path):
    (tmp_path / "staging" / "audits").mkdir(parents=True)
    (tmp_path / "staging" / "audits" / "chapter-2-foreshadowing.md").write_text(
        AUDIT_MARK, encoding="utf-8"
    )
    _, user_prompt, _, _ = _build_skill_prompt(
        skill="shenbi-state-settling",
        project_dir=tmp_path,
        prompt="settle chapter 2",
        chapter=2,
        uses_staging=True,
    )
    assert "staging/audits/chapter-2-foreshadowing.md" in user_prompt
    assert "MH02 defer" in user_prompt


def test_staging_twin_preferred_over_stale_live(tmp_path: Path):
    """Mirror of _append_dedup_base_state_lines' base rule: staged if it
    exists, else live — the staged twin is THIS chapter's state, the live
    copy is the previous chapter's committed state.
    """
    live = tmp_path / "audits" / "chapter-2-foreshadowing.md"
    live.parent.mkdir(parents=True)
    live.write_text("# stale ch1-committed copy\n", encoding="utf-8")
    staged = tmp_path / "staging" / "audits" / "chapter-2-foreshadowing.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(AUDIT_MARK, encoding="utf-8")
    _, user_prompt, _, _ = _build_skill_prompt(
        skill="shenbi-state-settling",
        project_dir=tmp_path,
        prompt="settle chapter 2",
        chapter=2,
        uses_staging=True,
    )
    assert "MH02 defer" in user_prompt
    assert "stale ch1-committed copy" not in user_prompt


def test_non_staging_dispatch_keeps_live_only_reads(tmp_path: Path):
    """Without uses_staging the twin must NOT appear — non-gated dispatches
    keep their live-only read semantics.
    """
    staged = tmp_path / "staging" / "audits" / "chapter-2-foreshadowing.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(AUDIT_MARK, encoding="utf-8")
    _, user_prompt, _, _ = _build_skill_prompt(
        skill="shenbi-state-settling",
        project_dir=tmp_path,
        prompt="settle chapter 2",
        chapter=2,
        uses_staging=False,
    )
    assert "staging/audits/chapter-2-foreshadowing.md" not in user_prompt
