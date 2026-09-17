"""Spec #6 T_C: externalized-teaching-block slimming assertions (offline).

Pre-slim baselines measured 2026-09-17 on branch f64d13c5 via
_build_skill_prompt (chars via len(); tokens via estimate_prompt_tokens).
Spec §3.5's 887B/869B figures are UTF-8 BYTES — different unit, both
recorded in acceptance evidence.
"""

from pathlib import Path

from shenbi.cost.estimate import estimate_prompt_tokens
from shenbi.pipeline.dispatch_helper import _build_skill_prompt

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"

# Pre-slim constants (captured before externalization, branch f64d13c5)
PRE_LEN_CHAPTER_PATTERN = 7629
PRE_EST_CHAPTER_PATTERN = 2681


def _system_prompt(skill: str, tmp_path: Path) -> str:
    system, _, _ = _build_skill_prompt(skill, tmp_path, "measure", 1)
    return system


def test_chapter_pattern_slimmed(tmp_path: Path) -> None:
    system = _system_prompt("shenbi-chapter-pattern", tmp_path)

    # net char drop: removed 627 chars, anchor block 104 chars (plan-review simulated)
    assert PRE_LEN_CHAPTER_PATTERN - len(system) >= 450
    # estimated-token drop (simulated 159, threshold with margin)
    assert estimate_prompt_tokens(system) <= PRE_EST_CHAPTER_PATTERN - 140

    # externalized file exists + bare-filename reference line in body
    ref = SKILLS_DIR / "shenbi-chapter-pattern" / "chapter-pattern-reference.md"
    assert ref.is_file()
    body = (SKILLS_DIR / "shenbi-chapter-pattern" / "SKILL.md").read_text(encoding="utf-8")
    assert "`chapter-pattern-reference.md`" in body

    # runtime sections kept inline (invariants)
    assert "### 熵评级阈值" in body
    assert "### 熵计算公式输入文档化要求" in body

    # moved teaching markers no longer in the system prompt
    assert "H = -Σ(p_i × log₂(p_i))" not in system
    assert "假设模式分布为" not in system
