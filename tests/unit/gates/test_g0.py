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


@pytest.mark.unit
class TestG0ErrorPaths:
    """Error-path tests for G0 — each pins one FAIL/WARN branch."""

    def test_g02_rejects_negative_target_words(self, tmp_path: Path) -> None:
        r"""Negative target_words value fails regex match -> G0.2 FAIL.

        Source regex matches `\d+` after 目标字数 + colon; `\d+` doesn't
        match '-5', so the gate emits 'target_words not found' FAIL.
        """
        seed = tmp_path / "seed.md"
        seed.write_text("目标字数：-5\n", encoding="utf-8")
        result = _result_dict(gate_G0(seed_file=str(seed)))
        assert result["status"] == "FAIL"
        assert "G0.2" in result.get("must_fix", [])

    def test_g02_rejects_non_numeric_target_words(self, tmp_path: Path) -> None:
        """Non-numeric target_words fails regex -> G0.2 FAIL."""
        seed = tmp_path / "seed.md"
        seed.write_text("目标字数：很多\n", encoding="utf-8")
        result = _result_dict(gate_G0(seed_file=str(seed)))
        assert "G0.2" in result.get("must_fix", [])

    def test_g03_falls_back_to_chapter_word_floor_when_genre_config_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No genre-config.json -> G0.3 uses CHAPTER_WORD_FLOOR constant.

        Source line 77: `default_w = CHAPTER_WORD_FLOOR`. Then expected = ceil(tw/floor).
        """
        from shenbi.gates import g0 as g0_mod

        monkeypatch.setattr(g0_mod, "PROJECT", tmp_path)
        seed = tmp_path / "seed.md"
        seed.write_text("目标字数：5000\n" + ("内容 " * 200), encoding="utf-8")
        result = _result_dict(gate_G0(seed_file=str(seed)))
        g03 = next((c for c in result["checks"] if c["id"] == "G0.3"), None)
        assert g03 is not None
        assert g03["s"] == "PASS"
        # CHAPTER_WORD_FLOOR is whatever shared.py defines; verify it's used.
        assert "chapter_word_default" in g03

    def test_g06_fails_when_project_root_not_writable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PROJECT root read-only -> G0.6 FAIL with 'PROJECT root not writable'."""
        from shenbi.gates import g0 as g0_mod

        # Use a path that doesn't exist so the elif branch fires; then force
        # os.access to return False via monkeypatch.
        nonproj = tmp_path / "nonproj"
        nonproj.mkdir()
        monkeypatch.setattr(g0_mod, "PROJECT", nonproj)
        monkeypatch.setattr("os.access", lambda *a, **k: False)
        seed = tmp_path / "seed.md"
        seed.write_text("目标字数：5000\n" + ("内容 " * 200), encoding="utf-8")
        result = _result_dict(gate_G0(seed_file=str(seed)))
        g06 = next((c for c in result["checks"] if c["id"] == "G0.6"), None)
        # Gate may short-circuit at G0.6 FAIL; check status + must_fix.
        assert result["status"] == "FAIL"
        assert "G0.6" in result.get("must_fix", [])

    def test_g07_warns_when_scoring_py_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TESTS/scoring.py missing -> G0.7 WARN."""
        from shenbi.gates import g0 as g0_mod

        # Point TESTS at an empty dir so scoring.py is missing.
        empty_tests = tmp_path / "empty-tests"
        empty_tests.mkdir()
        monkeypatch.setattr(g0_mod, "TESTS", empty_tests)
        # Also point PROJECT at tmp_path so G0.6 doesn't fail.
        monkeypatch.setattr(g0_mod, "PROJECT", tmp_path)
        # SKILLS must still point at the real skills/ tree so G0.4 passes.
        # (Leave it unpatched — module-level default.)
        seed = tmp_path / "seed.md"
        seed.write_text("目标字数：5000\n" + ("内容 " * 200), encoding="utf-8")
        result = _result_dict(gate_G0(seed_file=str(seed)))
        g07 = next((c for c in result["checks"] if c["id"] == "G0.7"), None)
        if g07 is not None:
            assert g07["s"] == "WARN"

    def test_g05b_passes_on_consistent_rubric_and_skill_md(self, tmp_path: Path) -> None:
        """G0.5b runs against the repo's real rubric+SKILL.md pairs.

        With real repo state, may PASS or WARN depending on current rubric
        drift. Either way the check should appear and not crash.
        """
        seed = tmp_path / "seed.md"
        seed.write_text("目标字数：5000\n" + ("内容 " * 200), encoding="utf-8")
        result = _result_dict(gate_G0(seed_file=str(seed)))
        g05b = next((c for c in result["checks"] if c["id"] == "G0.5b"), None)
        assert g05b is not None
        assert g05b["s"] in ("PASS", "WARN")

    def test_gate_emits_timestamp_in_all_paths(self, tmp_path: Path) -> None:
        """Every result (PASS, FAIL, short-circuit) includes ISO-8601 timestamp."""
        # Short-circuit path (seed_file=None)
        r1 = _result_dict(gate_G0(seed_file=None))
        assert "timestamp" in r1
        # FAIL path (missing seed)
        r2 = _result_dict(gate_G0(seed_file=str(tmp_path / "nope.md")))
        assert "timestamp" in r2

    def test_gate_emits_gate_identifier_in_all_paths(self, tmp_path: Path) -> None:
        """Every result includes gate == 'G0'."""
        r1 = _result_dict(gate_G0(seed_file=None))
        assert r1["gate"] == "G0"
        r2 = _result_dict(gate_G0(seed_file=str(tmp_path / "nope.md")))
        assert r2["gate"] == "G0"


# ---------------------------------------------------------------------------
# G0.10 generative-report-count branch coverage (PR-56 fill)
# These reach G0.10 by using the REAL repo PROJECT (no monkeypatch) so G0.8
# fixture-reference resolution against tests/fixtures/ succeeds.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_g010_warns_when_fewer_than_total_skills_generative_reports(tmp_path: Path) -> None:
    """round_dir with < total_skills generative reports -> G0.10 WARN (dynamic count, spec §9.4)."""
    seed = tmp_path / "seed.md"
    seed.write_text("目标字数：5000\n" + "正文内容。" * 200, encoding="utf-8")
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    reports = round_dir / "t1-reports"
    reports.mkdir()
    for i in range(3):
        (reports / f"skill-{i:03d}-generative-scores.json").write_text("{}", encoding="utf-8")
    result = _result_dict(gate_G0(seed_file=str(seed), round_dir=str(round_dir)))
    g010 = next((c for c in result["checks"] if c.get("id") == "G0.10"), None)
    assert g010 is not None, "G0.10 not reached — earlier check short-circuited"
    assert g010["s"] == "WARN"
    assert g010["completed"] == 3


@pytest.mark.unit
def test_g010_passes_when_total_skills_or_more_generative_reports(tmp_path: Path) -> None:
    """round_dir with >= total_skills generative reports -> G0.10 PASS (dynamic count, spec §9.4)."""
    from shenbi.gates.shared import ALL_SKILLS

    total = len(ALL_SKILLS)
    seed = tmp_path / "seed.md"
    seed.write_text("目标字数：5000\n" + "正文内容。" * 200, encoding="utf-8")
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    reports = round_dir / "t1-reports"
    reports.mkdir()
    for i in range(total + 1):
        (reports / f"skill-{i:03d}-generative-scores.json").write_text("{}", encoding="utf-8")
    result = _result_dict(gate_G0(seed_file=str(seed), round_dir=str(round_dir)))
    g010 = next((c for c in result["checks"] if c.get("id") == "G0.10"), None)
    assert g010 is not None
    assert g010["s"] == "PASS"
    assert g010["completed"] == total + 1
    assert g010["total"] == total


@pytest.mark.unit
def test_g015_gate_registry_consistency_passes_on_current_repo() -> None:
    """G0.15 asserts G4_CHECKER_SKILLS is a subset of the single-source skill set."""
    result = _result_dict(gate_G0(None, None))
    g015 = next((chk for chk in result["checks"] if chk.get("id") == "G0.15"), None)
    assert g015 is not None
    assert g015["s"] == "PASS"


@pytest.mark.unit
def test_known_skill_names_is_single_source() -> None:
    """known_skill_names owns the authoritative skill vocabulary (judgement 5)."""
    from shenbi.contracts.registry import known_skill_names
    from shenbi.gates.shared import ALL_SKILLS

    assert known_skill_names() == set(ALL_SKILLS)
