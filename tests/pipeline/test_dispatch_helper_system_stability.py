"""Spec #6 T_A: system prompt byte-stability regression (offline).

Fixes the implicit contract that the system prompt for a given skill is
byte-identical across consecutive _build_skill_prompt calls. The API
path relies on a stable system prefix for provider prompt-cache hits;
_strip_autogen_blocks must stay deterministic (pure regex, no
timestamps/random) for that to hold.
"""

from pathlib import Path

import pytest

from shenbi.pipeline.dispatch_helper import _build_skill_prompt

STABILITY_SKILLS = (
    "shenbi-chapter-pattern",
    "shenbi-review-resonance",
    "shenbi-state-settling",
)


@pytest.mark.parametrize("skill", STABILITY_SKILLS)
def test_system_prompt_byte_stable_across_calls(tmp_path: Path, skill: str) -> None:
    sys1, _, _, _, _ = _build_skill_prompt(skill, tmp_path, "prompt A", 1)
    sys2, _, _, _, _ = _build_skill_prompt(skill, tmp_path, "prompt B", 2)
    assert sys1.encode("utf-8") == sys2.encode("utf-8")


def test_state_settling_prompt_injects_append_only_hard_constraint(tmp_path: Path):
    """Batch #23 fix (probe30 ch4 matrix_structure content_dropped):
    the dispatch user_prompt for shenbi-state-settling MUST contain an
    explicit hard-constraint block forbidding modification of existing
    rows in character_matrix.md (and other append_dedup targets).

    probe30 ch4: state-settling LLM rewrote existing rows despite the
    SKILL.md 铁律 0 (Batch #22 fix). The text-only constraint is too
    easy to ignore when the LLM has high write-pressure (many increments
    in one chapter). The prompt MUST inject a near-final, very explicit
    CRITICAL block before the input files section.
    """
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    # Minimal project scaffold: only the SKILL.md file is needed.
    project_dir = tmp_path
    skill_md = project_dir / "skills" / "shenbi-state-settling" / "SKILL.md"
    skill_md.parent.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(
        "---\nname: shenbi-state-settling\n"
        'description: "state-settling"\n'
        "contract:\n  kind: artifact\n  reads: []\n  writes: []\n  updates: []\n"
        "---\n\n# Test SKILL\n",
        encoding="utf-8",
    )

    system_prompt, user_prompt, output_paths, reads_manifest, _ = _build_skill_prompt(
        "shenbi-state-settling",
        project_dir,
        prompt="Execute state-settling for chapter 1.",
        chapter=1,
        uses_staging=False,
        json_mode=True,
    )

    # The user_prompt MUST contain the hard constraint block — extracted
    # phrases from the constraint to make the test robust to formatting.
    import re as _re

    must_have_patterns = [
        r"character_matrix\.md",
        r"##\s*第N章状态增量|##\s*第\d+章状态增量",  # the required new block header
        r"NEVER\s+modify|never\s+modify",
        r"DO\s+NOT\s+modify\s+(?:the\s+)?existing\s+rows?",
        r"append[\s_-]?only",
    ]
    matched = [
        p for p in must_have_patterns if _re.search(p, user_prompt, _re.IGNORECASE | _re.DOTALL)
    ]
    assert len(matched) >= 3, (
        f"state-settling user_prompt must inject an explicit hard-constraint "
        f"block for character_matrix.md append-only behavior. "
        f"Found only {len(matched)} of required patterns: {matched}"
    )


def test_state_settling_prompt_injects_hooks_colon_bullet_constraint(tmp_path: Path):
    """Batch #26 fix (probe32 ch2 hooks_structure 3-attempt deadlock):
    the dispatch user_prompt for shenbi-state-settling MUST contain an
    explicit hard-constraint block for truth/pending_hooks.md — advancing
    an existing hook is colon-bullet-only (``- last_reinforced:`` /
    ``- 证据:``), NEVER a rewrite of the registry overview table row.

    probe32 ch2 was the FIRST advance-an-existing-hook scenario: the LLM
    read "MH01 advance" in the chapter plan and rewrote MH01's registry
    row status column (PLANTED → RELEVANT), failing G4.ss.hooks_structure
    hook_row_stable_columns_rewritten 3x — the corrective feedback fired
    but the model kept re-emitting its own idea of the file. Same shape
    as batch #23 (character_matrix): pre-emission contract in the prompt,
    not post-hoc gate feedback alone.
    """
    # Minimal project scaffold: only the SKILL.md file is needed.
    project_dir = tmp_path
    skill_md = project_dir / "skills" / "shenbi-state-settling" / "SKILL.md"
    skill_md.parent.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(
        "---\nname: shenbi-state-settling\n"
        'description: "state-settling"\n'
        "contract:\n  kind: artifact\n  reads: []\n  writes: []\n  updates: []\n"
        "---\n\n# Test SKILL\n",
        encoding="utf-8",
    )

    _, user_prompt, _, _, _ = _build_skill_prompt(
        "shenbi-state-settling",
        project_dir,
        prompt="Execute state-settling for chapter 2.",
        chapter=2,
        uses_staging=False,
        json_mode=True,
    )

    import re as _re

    must_have_patterns = [
        r"pending_hooks\.md",
        r"colon[\s-]?bullet",
        r"last_reinforced",
        r"registry|总览表",
        r"stable\s+column|稳定列",
        r"hooks_structure",
    ]
    matched = [
        p for p in must_have_patterns if _re.search(p, user_prompt, _re.IGNORECASE | _re.DOTALL)
    ]
    assert len(matched) >= 4, (
        f"state-settling user_prompt must inject an explicit hard-constraint "
        f"block for pending_hooks.md colon-bullet-only hook advancement. "
        f"Found only {len(matched)} of required patterns: {matched}"
    )
