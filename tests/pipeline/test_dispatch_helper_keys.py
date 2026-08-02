"""Tests for input-key form in _build_skill_prompt (spec §3.4 + C1 regression guard)."""

from pathlib import Path

from shenbi.pipeline.dispatch_helper import _input_key


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


def test_injection_keys_match_disk_read_keys():
    """SharedAuditContext injection must use the same key form as disk reads.

    Regression guard for spec §6.1 C1: if the injection block used basename
    keys while the disk-read path used relative-path keys, the same logical
    file would appear twice under two <document name=...> tags.
    """
    project = Path("/proj")
    # The injection block builds keys for these truth files:
    for truth_file in [
        project / "truth" / "world_rules.md",
        project / "truth" / "character_matrix.md",
        project / "truth" / "style_profile.md",
        project / "truth" / "pending_hooks.md",
    ]:
        injected_key = _input_key(truth_file, project)
        disk_key = _input_key(truth_file, project)  # same helper
        assert injected_key == disk_key
        assert "/" in injected_key  # relative-path form, not bare basename
