"""Year-anchor single-source gate (#33, batch #15).

probe15/probe17: four layers of mutually exclusive year numbers burned four
genesis adjudication rounds — every producer file invented its own absolute
years while worldbuilding's 世界史时间线 is the single anchor registry. #33
pins three faces of one rule:

1. MECHANICAL: ``check_year_anchors`` scans producer outputs for raw year
   forms (``X 年前/年后/来``); 5 exemption zones (story_bible = registry
   home, foundation, benchmarks, style, snapshots) carry years legitimately.
2. GATE: ``gate_G4`` runs the scan for the 13 genesis producers; outline
   files' projections are FLAGGED (WARN), everything else fails.
3. CONTRACT: each producer SKILL carries the anchor-name discipline clause,
   reconciled against GENESIS_STEPS (not a hand-kept list).
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.llm_output_integrity import check_year_anchors


def _write(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


class TestYearScan:
    def test_raw_year_forms_found_with_line_numbers(self, tmp_path):
        p = _write(
            tmp_path,
            "world/factions.md",
            "# 派系\n\n教会立于一千两百年前。\n\n盐户南迁二十年来积怨。\n普通行没有年份。\n",
        )
        findings = check_year_anchors(p)
        assert len(findings) == 2
        assert any("L3" in f and "一千两百年前" in f for f in findings)
        assert any("L5" in f and "二十年来" in f for f in findings)
        assert all(f.startswith("G4.ys.raw_year:") for f in findings)

    def test_arabic_numerals_matched(self, tmp_path):
        p = _write(tmp_path, "world/locations.md", "矿场建于 300 年前。\n")
        assert any("300 年前" in f or "300年前" in f for f in check_year_anchors(p))

    def test_exemption_zones_carry_years_legitimately(self, tmp_path):
        for rel in (
            "world/story_bible.md",
            "foundation/review_report.md",
            "benchmarks/anchors/AC-001.md",
            "style/style_profile.md",
            "snapshots/chapter-001/x.md",
        ):
            p = _write(tmp_path, rel, "一千年前的事件。\n")
            assert check_year_anchors(p) == [], f"{rel} is an exempt zone"

    def test_clean_file_no_findings(self, tmp_path):
        p = _write(tmp_path, "world/locations.md", "净场之后的黑脊，无年数。\n第 3 章 的钩子。\n")
        assert check_year_anchors(p) == []


class TestGateWiring:
    def test_producer_output_with_raw_year_fails_g4(self, tmp_path):
        from shenbi.gates.g4.generic import gate_G4

        p = _write(tmp_path, "world/factions.md", "# 派系\n\n教会立于一千两百年前。\n")
        result = gate_G4(
            "shenbi-faction-builder", "generative", [str(p)], project_dir=str(tmp_path)
        )
        assert "G4.ys.raw_year" in result
        import json

        data = json.loads(result)
        assert any("G4.ys.raw_year" in str(m) for m in data.get("must_fix", [])), (
            "non-outline producer raw years must land in must_fix"
        )

    def test_outline_projection_flagged_warn_not_fail(self, tmp_path):
        import json

        from shenbi.gates.g4.generic import gate_G4

        p = _write(tmp_path, "outline/volume_map.md", "# 卷纲\n\n第一卷：开矿（约百年前背景）\n")
        result = gate_G4(
            "shenbi-volume-outlining", "generative", [str(p)], project_dir=str(tmp_path)
        )
        data = json.loads(result)
        assert not any("G4.ys.raw_year" in str(m) for m in data.get("must_fix", [])), (
            "outline projections are flagged, not failed"
        )
        assert any(
            "G4.ys" in json.dumps(ch, ensure_ascii=False) for ch in data.get("checks", [])
        ) or data.get("status") in ("WARN", "PASS"), "flag must surface somewhere"

    def test_clean_producer_output_unchanged(self, tmp_path):

        from shenbi.gates.g4.generic import gate_G4

        p = _write(tmp_path, "world/factions.md", "# 派系\n\n净场之后的新秩序。\n")
        result = gate_G4(
            "shenbi-faction-builder", "generative", [str(p)], project_dir=str(tmp_path)
        )
        assert "G4.ys" not in result


class TestProducerClausePins:
    def test_all_genesis_producers_carry_anchor_clause(self):
        """Reconciled against GENESIS_STEPS — the list can never drift from
        the actual genesis roster.
        """
        from shenbi.pipeline.genesis import GENESIS_STEPS

        non_producers = {
            "shenbi-genre-config",  # config, not narrative content
            "shenbi-style-learning",  # style zone exemption
            "shenbi-anchor-curate",  # benchmarks zone exemption
            "shenbi-foundation-review",  # reviewer, enumerates instead
        }
        producers = [s.skill for s in GENESIS_STEPS if s.skill not in non_producers]
        assert len(producers) == 13, f"expected 13 producers, got {len(producers)}"
        root = Path(__file__).resolve().parents[3] / "skills"
        missing = [
            sk
            for sk in producers
            if "年代锚" not in (root / sk / "SKILL.md").read_text(encoding="utf-8")
        ]
        assert not missing, f"producer skills missing the year-anchor clause: {missing}"
