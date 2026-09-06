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
