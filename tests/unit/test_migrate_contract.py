"""Migrator idempotency: re-running on already-migrated skills is a no-op.

Regression for the Copilot review on PR #6 — the docstring claimed idempotency
but ``_strip_body_contract`` also matched the auto-generated ``## 数据契约`` view,
so a re-run would delete content up to the next ``##`` heading and corrupt
already-migrated files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import migrate_contract_to_frontmatter as migrate


@pytest.mark.unit
def test_migrate_is_noop_on_already_migrated_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A skill whose frontmatter already has ``contract:`` is left untouched."""
    skill = "shenbi-review-anti-ai"  # present in CLASSIFICATION
    skill_dir = tmp_path / skill
    skill_dir.mkdir()
    md = skill_dir / "SKILL.md"
    content = (
        "---\n"
        "name: shenbi-review-anti-ai\n"
        'description: "x"\n'
        "contract:\n"
        "  kind: report\n"
        "  reads: []\n"
        "  writes: []\n"
        "  updates: []\n"
        "---\n"
        "<!-- AUTO-GENERATED from frontmatter — do not edit -->\n\n"
        "## 数据契约\n\n"
        "- **Reads:**\n"
        "- **Writes:**\n\n"
        "<!-- END AUTO-GENERATED -->\n\n"
        "# Real Title\n\n"
        "## 流程\n\n"
        "real body content that must survive a re-run\n"
    )
    md.write_text(content, encoding="utf-8")
    monkeypatch.setattr(migrate, "SKILLS", tmp_path)

    assert migrate.migrate_skill(skill) is True
    # Byte-for-byte unchanged: the auto-generated view and the # Real Title
    # heading both survive (pre-fix, both were deleted up to ## 流程).
    assert md.read_text(encoding="utf-8") == content
