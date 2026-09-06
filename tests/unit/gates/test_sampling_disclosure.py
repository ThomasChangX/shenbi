"""C29 R2 sampling disclosure (F459/F235) — input_sampled fields + sentinel helper.

Scenario inputs derive from real fixtures under tests/fixtures/ (G0.9): chapter
drafts are concatenated to exceed clip limits; the invalid genre config is a
real-product copy with required fields nulled (upstream-generator style, the
healthy producer cannot emit it).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.g4.genre_config import g4_genre_config
from shenbi.gates.g6_checks import check_continuity
from shenbi.gates.shared import clip_with_disclosure

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


class TestClipWithDisclosure:
    def test_under_limit_not_sampled(self):
        text, sampled = clip_with_disclosure("short text", 100)
        assert text == "short text"
        assert sampled is False

    def test_over_limit_sampled(self):
        long = "x" * 200
        text, sampled = clip_with_disclosure(long, 100)
        assert text == "x" * 100
        assert sampled is True


class TestContinuitySamplingDisclosure:
    def test_clipped_chapters_flag_input_sampled(self, tmp_path: Path):
        draft = (_FIXTURES / "chapter-8-example.md").read_text(encoding="utf-8")
        # Single draft ~2.5K chars; doubled exceeds the 3000-char clip
        (tmp_path / "chapter-1.md").write_text(draft * 2, encoding="utf-8")
        (tmp_path / "chapter-2.md").write_text(draft * 2, encoding="utf-8")

        checks, _mf = check_continuity(sorted(tmp_path.glob("chapter-*.md")))

        g64 = [chk for chk in checks if chk["id"] == "G6.4"]
        assert g64, "expected a G6.4 check entry"
        assert g64[0].get("input_sampled") is True

    def test_short_chapters_not_flagged(self, tmp_path: Path):
        (tmp_path / "chapter-1.md").write_text("第1天 开始", encoding="utf-8")
        (tmp_path / "chapter-2.md").write_text("第2天 继续", encoding="utf-8")

        checks, _mf = check_continuity(sorted(tmp_path.glob("chapter-*.md")))

        g64 = [chk for chk in checks if chk["id"] == "G6.4"]
        assert g64
        assert "input_sampled" not in g64[0]


class TestGenreConfigErrorCount:
    def test_full_error_count_disclosed(self, tmp_path: Path):
        """F235: errors[:5] truncation replaced by full count + first 5 details."""
        cfg = json.loads((_FIXTURES / "genre-config-example.json").read_text(encoding="utf-8"))
        # Null 7 required fields (upstream-generator mutation of a real product)
        keys = list(cfg.keys())[:7]
        for k in keys:
            cfg[k] = None
        bad = tmp_path / "genre-config.json"
        bad.write_text(json.dumps(cfg), encoding="utf-8")

        result_str = g4_genre_config([str(bad)])
        import re

        m = re.search(r"\+(\d+) more errors \(total (\d+)\)", result_str)
        assert m, f"expected '+N more errors (total M)' disclosure in: {result_str}"
        assert int(m.group(2)) > 5  # F235: full count, not the old errors[:5] silent drop


class TestGateLevelAggregation:
    def test_gate_g6_emits_sampling_disclosed(self, tmp_path: Path):
        """C29 R2: top-level sampling_disclosed summary on the gate result."""
        import json as _json

        from shenbi.gates.g6 import gate_G6

        round_dir = tmp_path / "round"
        project_dir = tmp_path / "project-output"
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)
        draft = (_FIXTURES / "chapter-8-example.md").read_text(encoding="utf-8")
        for n in (1, 2, 3):
            (chapters / f"chapter-{n}.md").write_text(draft * 3, encoding="utf-8")

        parsed = _json.loads(gate_G6("long-form", str(round_dir), str(project_dir)))
        assert "sampling_disclosed" in parsed
        assert "checks ran on sampled input" in parsed["sampling_disclosed"]
        # at least one check carries the per-check flag
        assert any(chk.get("input_sampled") for chk in parsed.get("checks", []))

    def test_sampled_checks_summary_skips_skip_checks(self):
        from shenbi.gates.shared import sampled_checks_summary
        from shenbi.status import GateStatus

        checks = [
            {"id": "A", "s": GateStatus.PASS},
            {"id": "B", "s": GateStatus.PASS, "input_sampled": True},
            {"id": "C", "s": GateStatus.SKIP, "r": "n/a"},
        ]
        assert sampled_checks_summary(checks) == "1/2 checks ran on sampled input"
        assert sampled_checks_summary([{"id": "A", "s": GateStatus.PASS}]) is None


class TestCountSamplingDisclosure:
    def test_g53_files_sampled_disclosed(self, tmp_path: Path):
        """C29 R2b: file-count sampling (outline[:3], output[:8], char_dir[:6]) disclosed."""
        import json as _json

        from shenbi.gates.g5 import gate_G5

        project_dir = tmp_path / "project-output"
        outline = project_dir / "outline"
        outline.mkdir(parents=True)
        base = (_FIXTURES / "outline-example.md").read_text(encoding="utf-8")
        # >12 outline files forces the [:3] count-sampling to bite
        for i in range(13):
            (outline / f"vol-{i:02d}.md").write_text(base, encoding="utf-8")

        round_dir = tmp_path / "round"
        round_dir.mkdir()
        parsed = _json.loads(gate_G5("foundation", str(round_dir), str(project_dir)))
        g53 = [chk for chk in parsed.get("checks", []) if chk.get("id") == "G5.3"]
        assert g53, f"expected G5.3 check, got checks={parsed.get('checks')}"
        # exact denominator: 13 outline files, cap 3 — per-point encoding
        assert g53[0].get("files_sampled") == "outline:3/13"

    def test_g69_constraints_cap_disclosed(self, tmp_path: Path):
        """C29 R2b: G6.9 constraints[:10] cap disclosed as findings_capped."""
        import json as _json

        from shenbi.gates.g6 import gate_G6

        project_dir = tmp_path / "project-output"
        world = project_dir / "world"
        chapters = project_dir / "chapters"
        world.mkdir(parents=True)
        chapters.mkdir(parents=True)
        # >10 distinct numeric constraints in world/rules.md (real-shape content)
        rules = "\n".join(f"规则{i}: 不超过 {i + 2} 人参与" for i in range(12))
        (world / "rules.md").write_text(rules, encoding="utf-8")
        draft = (_FIXTURES / "chapter-8-example.md").read_text(encoding="utf-8")
        (chapters / "chapter-1.md").write_text(draft, encoding="utf-8")

        parsed = _json.loads(gate_G6("long-form", str(tmp_path / "round"), str(project_dir)))
        g69 = [chk for chk in parsed.get("checks", []) if chk.get("id") == "G6.9"]
        assert g69, f"expected G6.9 check, got checks={parsed.get('checks')}"
        assert g69[0].get("findings_capped") == "10/12"
