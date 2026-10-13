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
PRE_LEN_PACING = 6829
PRE_EST_PACING = 2511
# probe8 fix batch (5716a195): pacing-design's mandatory frontmatter contract
# adds 84 chars / ~34 est-tokens to the system prompt (校验规则 item 1 + the
# template's own frontmatter block). Externalization boundary unchanged —
# the allowance keeps this guard measuring spec §3.5 slimming, not freezing
# prompt size against later mandatory contract elements.
PACING_FRONTMATTER_ADD = 84
#: batch #15 #33: sanctioned year-anchor clause (one blockquote) appended to
#: the SKILL body — net-slimming budget consumed by contract, not bloat.
PACING_ANCHOR_CLAUSE_ADD = 84
PACING_ANCHOR_CLAUSE_TOKENS = 40
PACING_FRONTMATTER_TOKENS = 36


def _system_prompt(skill: str, tmp_path: Path) -> str:
    system, _, _, _ = _build_skill_prompt(skill, tmp_path, "measure", 1)
    return system


def test_chapter_pattern_slimmed(tmp_path: Path) -> None:
    system = _system_prompt("shenbi-chapter-pattern", tmp_path)

    # net char drop: plan-review simulated 526; landed 526 (removed 626, anchor ~101)
    assert PRE_LEN_CHAPTER_PATTERN - len(system) >= 450
    # estimated-token drop: landed 161
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


def test_pacing_design_slimmed(tmp_path: Path) -> None:
    system = _system_prompt("shenbi-pacing-design", tmp_path)

    # net char drop: landed 367 (removed ~480, pointer ~113)
    assert PRE_LEN_PACING - len(system) >= 280 - PACING_FRONTMATTER_ADD - PACING_ANCHOR_CLAUSE_ADD
    # estimated-token drop: landed 144
    assert (
        estimate_prompt_tokens(system)
        <= PRE_EST_PACING - 130 + PACING_FRONTMATTER_TOKENS + PACING_ANCHOR_CLAUSE_TOKENS
    )

    ref = SKILLS_DIR / "shenbi-pacing-design" / "pacing-design-reference.md"
    assert ref.is_file()
    body = (SKILLS_DIR / "shenbi-pacing-design" / "SKILL.md").read_text(encoding="utf-8")
    assert "`pacing-design-reference.md`" in body

    # runtime invariants kept inline
    assert "单调性检测阈值" in body
    assert "## 输出格式" in body
    assert "EXACT 节标题" in body

    # moved teaching markers no longer in the system prompt
    assert "太多=流水账" not in system
    assert "每卷使用全部类型" not in system
