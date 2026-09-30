"""Unit tests for G4 escalation_review checker (spec §9.12)."""

from __future__ import annotations

import os
import tempfile

import pytest

from shenbi.gates.g4.escalation_review import g4_escalation_review


@pytest.mark.unit
def test_escalation_review_passes_with_all_sections():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Escalation\n## 触发信号\n内容\n## 升级上下文\n内容\n## 决策选项\n内容")
        f.flush()
        result = g4_escalation_review([f.name])
    os.unlink(f.name)
    assert '"status": "PASS"' in result


@pytest.mark.unit
def test_escalation_review_fails_missing_section():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Escalation\n## 触发信号\n内容")
        f.flush()
        result = g4_escalation_review([f.name])
    os.unlink(f.name)
    assert '"status": "FAIL"' in result


def test_skill_option_library_covers_executor_capacity_class():
    """Fixcheck P3: every capacity-class escalation (faction-builder,
    state-settling, group-character — completion pinned at cap values) was
    answered with the hard-coded redo/rollback example options because the
    template's example list had no capacity option; the right answer
    (executor headroom override / split dispatch) never surfaced.
    """
    from pathlib import Path

    text = Path("skills/shenbi-escalation-review/SKILL.md").read_text(encoding="utf-8")
    assert "输出容量类" in text
    assert "length_truncation" in text
    assert "executor_config.toml" in text
    assert "选项必须匹配失败类别" in text
