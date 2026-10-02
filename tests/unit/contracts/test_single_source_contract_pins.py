"""Batch #10 single-source contract pins.

One theme across the ledger: one canonical form/verdict/caliber per concept —
hook-id family (#21), ERROR⇒结果 linkage and per-trope threshold caliber
(#19/#22), genesis timeline single source (#18). These pins keep the SKILL
contracts (what the model is taught) aligned with the machinery that
enforces them.
"""

from __future__ import annotations

import re
from pathlib import Path

_SKILLS = Path(__file__).resolve().parents[3] / "skills"


def _body(skill: str) -> str:
    text = (_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    return text[m.end() :] if m else text


class TestSettleHookExampleLiveForm:
    """#21: the settle SKILL's pending_hooks increment example must show the
    LIVE (genesis template) heading form — the old ``### MH-001 · `` example
    taught a format that matched neither the live file nor machinery canon,
    so even a perfectly compliant model produced unmergeable output.
    """

    def test_example_uses_live_heading_form(self):
        body = _body("shenbi-state-settling")
        assert "### MH-001" not in body, "stale hyphen-form example must be gone"
        assert re.search(r"### MH\d+（", body), "live-form example heading required"

    def test_example_names_banned_scaffold_forms(self):
        body = _body("shenbi-state-settling")
        assert "## 总览" in body and "frontmatter" in body


class TestWorldbuildingTimelineSingleSource:
    """#18: probe15 genesis needed four adjudication rounds over year
    contradictions restated across four world files. The story_bible
    template must carry a mandatory single-source timeline table and forbid
    absolute-year restatement elsewhere.
    """

    def test_template_has_timeline_section(self):
        body = _body("shenbi-worldbuilding")
        assert "## 世界史时间线" in body

    def test_template_pins_single_source_rule(self):
        body = _body("shenbi-worldbuilding")
        assert "唯一登记" in body
        assert "不得" in body and ("复述" in body or "另立" in body)


class TestFoundationReviewVerdictLinkage:
    """#19: probe15's report certified 通过(90 分)while carrying two P0/ERROR
    rows — score and verdict had no linkage, so the genesis checkpoint could
    not gate on the report.
    """

    def test_error_rows_force_fail_verdict(self):
        body = _body("shenbi-foundation-review")
        assert "任一 [ERROR]" in body, "the ERROR⇒verdict linkage rule is required"
        assert "不通过" in body
        assert "通过 (XX分)" in body or "零 [ERROR]" in body, (
            "通过 must be conditioned on zero ERROR rows"
        )

    def test_trope_threshold_caliber_is_per_trope(self):
        """#22: the report applied two contradictory trope calibers (dimension
        table said per-trope hits ≤ threshold; defect table counted trope
        TYPES > threshold). The contract must pin ONE unit: a violation is a
        single trope's signature hit count exceeding overuse_threshold.
        """
        body = _body("shenbi-foundation-review")
        assert "单条 trope" in body
        assert "命中次数" in body
        assert "类型" in body  # names the NON-violation unit explicitly
