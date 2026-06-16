"""Unit tests for G0: round creation environment check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from shenbi.gates.g0 import gate_G0


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG0SeedFile:
    def test_skips_when_no_seed_provided(self) -> None:
        result = _result_dict(gate_G0(seed_file=None))
        assert result["status"] == "PASS"
        assert any(c["id"] == "G0.1" and c["s"] == "SKIP" for c in result["checks"])

    def test_fails_when_seed_file_missing(self, tmp_path: Path) -> None:
        result = _result_dict(gate_G0(seed_file=str(tmp_path / "nonexistent.md")))
        assert result["status"] == "FAIL"
        assert "G0.1" in result["must_fix"]

    def test_fails_when_seed_has_no_target_words(self, tmp_path: Path) -> None:
        """G0.2 requires a '目标字数:<N>' line."""
        seed = tmp_path / "seed.md"
        seed.write_text("# Novel\n\nNo target words line here.", encoding="utf-8")
        result = _result_dict(gate_G0(seed_file=str(seed)))
        assert result["status"] == "FAIL"
        assert "G0.2" in result["must_fix"]

    def test_fails_when_target_words_is_zero(self, tmp_path: Path) -> None:
        seed = tmp_path / "seed.md"
        seed.write_text("# Novel\n\n目标字数：0\n", encoding="utf-8")
        result = _result_dict(gate_G0(seed_file=str(seed)))
        assert result["status"] == "FAIL"

    def test_passes_when_target_words_present_and_positive(self, tmp_path: Path) -> None:
        """A seed with target_words > 0 advances past G0.2. Subsequent
        G0 checks may still FAIL based on structure, but G0.2 itself passes.
        """
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# Novel\n\n目标字数：100000\n\n## Setup\n" + ("内容 " * 200),
            encoding="utf-8",
        )
        result = _result_dict(gate_G0(seed_file=str(seed)))
        # G0.2 should pass; the overall result depends on later checks
        # but at minimum G0.1 and G0.2 should not be in must_fix
        assert "G0.1" not in result.get("must_fix", [])
        assert "G0.2" not in result.get("must_fix", [])

    def test_accepts_chinese_colon_in_target_words(self, tmp_path: Path) -> None:
        """Regex accepts both ASCII ':' and Chinese ':'."""
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# Novel\n\n目标字数:50000\n\n## Setup\n" + ("内容 " * 200),
            encoding="utf-8",
        )
        result = _result_dict(gate_G0(seed_file=str(seed)))
        assert "G0.2" not in result.get("must_fix", [])
