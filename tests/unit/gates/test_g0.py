"""Unit tests for G0: round creation environment check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

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


@pytest.mark.unit
class TestG0HappyPath:
    """Happy-path tests for G0.3-G0.9 — each exercises one check on valid input."""

    def test_g03_expected_chapters_via_genre_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """G0.3 reads chapter_word.default from PROJECT/skill-output/<proj>/genre-config.json."""
        from shenbi.gates import g0 as g0_mod

        skill_output = tmp_path / "skill-output" / "proj"
        skill_output.mkdir(parents=True)
        (skill_output / "genre-config.json").write_text(
            json.dumps({"chapter_word": {"default": 5000}}), encoding="utf-8"
        )
        monkeypatch.setattr(g0_mod, "PROJECT", tmp_path)

        seed = tmp_path / "seed.md"
        seed.write_text("目标字数：10000\n", encoding="utf-8")
        result = _result_dict(gate_G0(seed_file=str(seed)))
        g03 = next((c for c in result["checks"] if c["id"] == "G0.3"), None)
        assert g03 is not None, "G0.3 not emitted (earlier check may have short-circuited)"
        assert g03["s"] == "PASS"
        assert g03["expected_chapters"] == 2  # ceil(10000/5000)

    def test_g04_passes_on_clean_repo(self, tmp_path: Path) -> None:
        """G0.4 PASSes against the repo's real skills/ tree.

        Note: when seed_file=None the gate SHORT-CIRCUITS at G0.1 and never
        reaches G0.4 (see src/shenbi/gates/g0.py line 62 — returns passed()
        immediately after appending the G0.1 SKIP check). To exercise G0.4
        we must pass a real seed_file so the gate walks past G0.1/G0.2/G0.3.
        ALL_SKILLS and SKILLS are module-level constants in shared.py
        pointing at the actual repo layout, so G0.4 inspects the real
        skills/ tree regardless of monkeypatch.
        """
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# Novel\n\n目标字数：5000\n\n## Setup\n" + ("内容 " * 200),
            encoding="utf-8",
        )
        result = _result_dict(gate_G0(seed_file=str(seed)))
        g04 = next(
            (c for c in result["checks"] if c["id"] == "G0.4"),
            None,
        )
        assert g04 is not None, "G0.4 check not emitted (earlier check may have short-circuited)"
        assert g04["s"] == "PASS"

    def test_g06_passes_when_skill_output_writable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """G0.6 PASSes when PROJECT root is writable."""
        from shenbi.gates import g0 as g0_mod

        monkeypatch.setattr(g0_mod, "PROJECT", tmp_path)
        seed = tmp_path / "seed.md"
        seed.write_text("目标字数：5000\n" + ("内容 " * 200), encoding="utf-8")
        result = _result_dict(gate_G0(seed_file=str(seed)))
        g06 = next(
            (c for c in result["checks"] if c["id"] == "G0.6"),
            None,
        )
        assert g06 is not None, "G0.6 check not emitted (earlier check may have short-circuited)"
        assert g06["s"] == "PASS"
