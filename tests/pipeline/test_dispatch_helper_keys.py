"""Tests for input-key form in _build_skill_prompt (spec §3.4 + C1 regression guard)."""

from pathlib import Path

from shenbi.pipeline.dispatch_helper import _input_key
from tests.pipeline.conftest import assemble_shared_context_project


def test_input_key_uses_relative_path():
    """Keys must be project-relative, not basename (spec §3.4 collision bug)."""
    project = Path("/proj")
    key = _input_key(Path("/proj/truth/pending_hooks.md"), project)
    assert key == "truth/pending_hooks.md"


def test_input_key_distinguishes_same_basename_different_dirs():
    """Two files with the same basename in different dirs get distinct keys (the bug)."""
    project = Path("/proj")
    a = _input_key(Path("/proj/dir_a/hooks.md"), project)
    b = _input_key(Path("/proj/dir_b/hooks.md"), project)
    assert a != b
    assert a == "dir_a/hooks.md"
    assert b == "dir_b/hooks.md"


#: The exact key set the production injection block (dispatch_helper
#: `_INJECT_FROM_CACHE`) must inject. C28 R1 (F312) canonical paths — the old
#: truth/world_rules.md and truth/style_profile.md entries were phantoms.
#: Drift in the injection block's key set turns this red.
EXPECTED_INJECTION_KEYS = (
    "world/rules.md",
    "truth/character_matrix.md",
    "style/style_profile.md",
    "truth/pending_hooks.md",
)


def test_injection_block_pins_canonical_keys(tmp_path):
    """SharedAuditContext injection drives _build_skill_prompt with the canonical keys.

    Regression guard for spec §6.1 C1 + C28 R1 (F312): the injected keys must
    match the disk-read key form AND the canonical paths. A phantom key or a
    key drift in _INJECT_FROM_CACHE fails here (the old form called the same
    helper twice and compared — always green).
    """
    from shenbi.pipeline.audit_context_cache import build_shared_audit_context
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    assemble_shared_context_project(tmp_path)

    ctx = build_shared_audit_context(tmp_path, 3)
    _, user_prompt, _ = _build_skill_prompt(
        skill="shenbi-review-anti-ai",
        project_dir=tmp_path,
        prompt="audit chapter 3",
        chapter=3,
        shared_context=ctx,
    )
    for key in EXPECTED_INJECTION_KEYS:
        assert key in user_prompt, f"injection key drifted/missing: {key}"
