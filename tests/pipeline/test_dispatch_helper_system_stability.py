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
    sys1, _, _ = _build_skill_prompt(skill, tmp_path, "prompt A", 1)
    sys2, _, _ = _build_skill_prompt(skill, tmp_path, "prompt B", 2)
    assert sys1 == sys2
