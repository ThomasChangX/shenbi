"""Spec #68 T3: failure taxonomy + audits input (raw-glob priority)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
AUDIT_SEEDS = [
    FIXTURES / "audits" / "chapter-1-character.md",
    FIXTURES / "audits" / "chapter-1-consistency.md",
]


class TestTaxonomyRules:
    """映射表与路由表覆盖面。"""

    def test_all_eight_categories_present(self):
        from tools.report_longitudinal import TAXONOMY_RULES

        assert set(TAXONOMY_RULES) == {
            "连续性断裂",
            "人物漂移",
            "世界规则违反",
            "伏笔丢失",
            "风格衰减",
            "重复",
            "节奏崩溃",
            "敏感性",
        }

    def test_routes_cover_categories(self):
        from tools.report_longitudinal import SUBSYSTEM_ROUTES, TAXONOMY_RULES

        assert set(SUBSYSTEM_ROUTES) == set(TAXONOMY_RULES)
        assert all(v for v in SUBSYSTEM_ROUTES.values())

    def test_classify_known_and_unknown(self):
        from shenbi.pipeline.audit_aggregate import FindingUnit
        from tools.report_longitudinal import classify

        units = [
            FindingUnit("WARNING", "人物语气与既定性格不符，对话脱离人设", ("a.md",)),
            FindingUnit("CRITICAL", "前文伏笔丢失：第2章埋设的金属片不再被提及", ("a.md",)),
            FindingUnit("WARNING", "无法归类的任意发现文本 xyzzy", ("b.md",)),
        ]
        counts, unclassified = classify(units)
        assert counts["人物漂移"] == 1 and counts["伏笔丢失"] == 1
        assert unclassified == 1


class TestMergeUnits:
    """合并 glue：(severity, text) 键去重 + reporters 并集。"""

    def test_dedup_on_severity_text_union_reporters(self):
        from tools.report_longitudinal import merge_units

        line = "- [WARNING] 人物语气与既定性格不符，对话脱离人设\n"
        units = merge_units(
            [
                ("chapter-1-character.md", line),
                ("chapter-1-consistency.md", line),
            ]
        )
        assert len(units) == 1
        assert units[0].reporters == ("chapter-1-character.md", "chapter-1-consistency.md")

    def test_real_fixture_seeds_produce_units(self):
        from tools.report_longitudinal import merge_units

        reports = [(p.name, p.read_text(encoding="utf-8")) for p in AUDIT_SEEDS]
        units = merge_units(reports)
        assert units, "真实 fixture 审计报告应产出至少一条 severity 发现"


class TestLoadAuditUnits:
    """raw glob 优先 + resonance 排除 + aggregate 回退 break 语义。"""

    def test_raw_glob_priority(self, tmp_path):
        from tools.report_longitudinal import load_audit_units

        audits = tmp_path / "audits"
        audits.mkdir()
        (audits / "chapter-1-character.md").write_text(
            "- [WARNING] 人物语气与既定性格不符，对话脱离人设\n", encoding="utf-8"
        )
        (audits / "chapter-1.aggregate.md").write_text(
            "# Chapter 1 — Audit Aggregate\n\n## WARNING Findings (1)\n\n- 无关条目\n",
            encoding="utf-8",
        )
        units, source = load_audit_units(tmp_path, 1)
        assert source == "raw" and len(units) == 1

    def test_resonance_report_excluded_from_raw_glob(self, tmp_path):
        """resonance 报告不是失败发现——混入即污染热力图（spec §2 理由③）。"""
        from tools.report_longitudinal import load_audit_units

        audits = tmp_path / "audits"
        audits.mkdir()
        (audits / "chapter-1-resonance.md").write_text(
            "## 共振评估\n\n- [WARNING] 共振分 78：人物弧线落地不足\n", encoding="utf-8"
        )
        units, source = load_audit_units(tmp_path, 1)
        assert source == "none" and units == []

    def test_aggregate_fallback_breaks_at_resonance_h2(self, tmp_path):
        """aggregate 回退：遇第一个非 severity H2 即 break——内嵌 resonance
        正文里的伪 `## WARNING Findings` 不得重臂 severity。"""
        from tools.report_longitudinal import load_audit_units

        audits = tmp_path / "audits"
        audits.mkdir()
        (audits / "chapter-1.aggregate.md").write_text(
            "# Chapter 1 — Audit Aggregate\n\n## CRITICAL Findings (1)\n\n"
            "- 人物语气与既定性格不符，对话脱离人设\n\n"
            "## Resonance 报告（逐字保留）\n\n### chapter-1-resonance.md\n\n"
            "## WARNING Findings (2)\n\n- 嵌入正文里的伪 H2 分节\n",
            encoding="utf-8",
        )
        units, source = load_audit_units(tmp_path, 1)
        assert source == "aggregate" and len(units) == 1
        assert units[0].severity == "CRITICAL"

    def test_none_when_absent(self, tmp_path):
        from tools.report_longitudinal import load_audit_units

        units, source = load_audit_units(tmp_path, 1)
        assert units == [] and source == "none"
