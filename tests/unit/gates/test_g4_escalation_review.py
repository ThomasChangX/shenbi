"""Unit tests for G4 escalation_review checker (spec §9.12)."""
from __future__ import annotations

import pytest
import tempfile
import os
from pathlib import Path

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
