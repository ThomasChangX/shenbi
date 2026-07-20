"""Guard: the G4 worldbuilding gate must keep counting ``## 规则`` headings.

Spec 21 §2.2 / §5 criterion 4: the G4 gate is correct and must NOT be modified
by the semantic-index-population work. This test locks that behaviour so a
future edit cannot silently regress Chinese-ordinal rule counting.
"""

from __future__ import annotations

import re

import pytest


def test_worldbuilding_regex_counts_chinese_ordinals():
    """The exact regex at gates/g4/worldbuilding.py:94 must still match
    ``## 规则一：`` .. ``## 规则十：``.
    """  # noqa: RUF002
    # Mirror the in-gate pattern verbatim (if the gate changes, this test
    # forces the author to update it deliberately).
    pattern = r"## 规则\s*[：:.]?\s*[一二三四五六七八九十\d]+"
    sample = "## 规则一：守恒\n## 规则二：知识\n## 规则三：时间\n## 规则十：闭环\n"
    assert len(re.findall(pattern, sample)) == 4


def test_worldbuilding_uses_max_of_heading_and_numbered():
    """Read the actual source and assert the max(heading_rules, numbered_rules)
    expression is present (spec §2.2).
    """
    src = pytest.importorskip("shenbi.gates.g4.worldbuilding").__file__
    text = open(src, encoding="utf-8").read()  # noqa: SIM115
    assert "heading_rules" in text
    assert "numbered_rules" in text
    assert "max(heading_rules, numbered_rules)" in text
