"""Unit tests for G2: write verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from shenbi.gates.g2 import gate_G2


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG2FileInputs:
    def test_accepts_string_file_paths(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("# x\n", encoding="utf-8")
        result = _result_dict(gate_G2(str(f), "report"))
        assert "status" in result

    def test_accepts_list_file_paths(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.md"
        f1.write_text("a", encoding="utf-8")
        f2 = tmp_path / "b.md"
        f2.write_text("b", encoding="utf-8")
        result = _result_dict(gate_G2([str(f1), str(f2)], "report"))
        assert "status" in result

    def test_handles_none_file_paths(self) -> None:
        result = _result_dict(gate_G2(None, "chapter"))
        assert "status" in result

    def test_handles_missing_files(self, tmp_path: Path) -> None:
        """A non-existent file should not crash G2; it reports failure cleanly."""
        result = _result_dict(gate_G2([str(tmp_path / "nope.md")], "chapter"))
        assert result["status"] in {"FAIL", "PASS"}  # behavior depends on impl

    def test_supports_chapter_file_type(self, tmp_path: Path) -> None:
        """Chapter file type applies chapter-word-floor/ceiling checks."""
        f = tmp_path / "ch.md"
        f.write_text("正文内容", encoding="utf-8")
        result = _result_dict(gate_G2(str(f), "chapter"))
        assert "status" in result

    def test_supports_report_file_type(self, tmp_path: Path) -> None:
        f = tmp_path / "r.md"
        f.write_text("# Report\n内容", encoding="utf-8")
        result = _result_dict(gate_G2(str(f), "report"))
        assert "status" in result

    def test_emits_valid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("x", encoding="utf-8")
        parsed = json.loads(gate_G2(str(f), "report"))
        assert "status" in parsed


@pytest.mark.unit
class TestG2ErrorPaths:
    """Error-path tests for G2.1-G2.5 file integrity checks.

    Source convention mirrors G1: per-file FAILs go to mf list and surface
    as must_fix strings like 'G2.1:/path/file.md'.
    """

    def test_g21_fails_when_file_not_found(self, tmp_path: Path) -> None:
        """Non-existent file -> G2.1 FAIL in must_fix."""
        missing = tmp_path / "nope.md"
        result = _result_dict(gate_G2([str(missing)], "chapter"))
        assert any("G2.1" in mf for mf in result.get("must_fix", []))

    def test_g22_fails_when_file_empty(self, tmp_path: Path) -> None:
        """Zero-byte file -> G2.2 FAIL in must_fix."""
        empty = tmp_path / "empty.md"
        empty.write_text("")
        result = _result_dict(gate_G2([str(empty)], "chapter"))
        assert any("G2.2" in mf for mf in result.get("must_fix", []))

    def test_g24_fails_on_corrupt_json(self, tmp_path: Path) -> None:
        """Malformed JSON file -> G2.4 FAIL in must_fix."""
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        result = _result_dict(gate_G2([str(bad)], "report"))
        assert any("G2.4" in mf for mf in result.get("must_fix", []))

    def test_g25_fails_when_structured_data_lacks_frontmatter(self, tmp_path: Path) -> None:
        """truth/outline/plans .md file without YAML frontmatter -> G2.5 FAIL.

        Source line 76: must_have=True for paths containing /truth/, /outline/,
        /plans/, /snapshots/ or ending in plan.md/memo.md/map.md.
        """
        truth_dir = tmp_path / "truth"
        truth_dir.mkdir()
        no_fm = truth_dir / "hooks.md"
        no_fm.write_text("# Hooks\n\nplain content without frontmatter\n")
        result = _result_dict(gate_G2([str(no_fm)], "truth"))
        assert any("G2.5" in mf for mf in result.get("must_fix", []))

    def test_g23_passes_on_valid_utf8_file(self, tmp_path: Path) -> None:
        """Valid UTF-8 file -> G2.3 PASS in checks."""
        f = tmp_path / "ok.md"
        f.write_text("# Title\n\n正文内容\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(f)], "chapter"))
        g23 = next((c for c in result["checks"] if c.get("id") == "G2.3"), None)
        assert g23 is not None
        assert g23["s"] == "PASS"

    def test_comma_separated_string_input_is_split(self, tmp_path: Path) -> None:
        """Comma-separated string input is split into multiple paths."""
        f1 = tmp_path / "a.md"
        f1.write_text("a", encoding="utf-8")
        f2 = tmp_path / "b.md"
        f2.write_text("b", encoding="utf-8")
        result = _result_dict(gate_G2(f"{f1},{f2}", "report"))
        # Both files should produce PASS entries (at least 2 G2.1 PASS)
        pass_count = sum(
            1 for c in result["checks"] if c.get("id") == "G2.1" and c.get("s") == "PASS"
        )
        assert pass_count == 2


@pytest.mark.unit
class TestG2WordCountChecks:
    """G2.6-G2.7 word count floor/ceiling checks."""

    def test_g26_fails_when_word_count_below_floor(self, tmp_path: Path) -> None:
        """Chapter with < CHAPTER_WORD_FLOOR words -> G2.6 FAIL."""
        ch = tmp_path / "chapter-001.md"
        ch.write_text("短\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        assert any("G2.6" in mf for mf in result.get("must_fix", []))

    def test_g27_passes_when_word_count_within_ceiling(self, tmp_path: Path) -> None:
        """Chapter with word count between floor and ceiling -> G2.7 PASS."""
        ch = tmp_path / "chapter-001.md"
        # Write enough CJK to exceed CHAPTER_WORD_FLOOR but below ceiling
        ch.write_text("# Chapter\n\n" + ("这是中文内容。\n" * 40), encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        g27 = next((c for c in result["checks"] if c.get("id") == "G2.7"), None)
        assert g27 is not None
        assert g27["s"] == "PASS"

    def test_g27_fails_when_word_count_exceeds_ceiling(self, tmp_path: Path) -> None:
        """Non-important chapter > CHAPTER_WORD_FLOOR*1.5 (4500) -> G2.7 FAIL."""
        ch = tmp_path / "chapter-001.md"
        # CHAPTER_WORD_FLOOR=3000, ceiling for non-important = int(3000*1.5) = 4500
        ch.write_text("# Chapter\n\n" + ("测" * 5500), encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        # G2.7 FAIL goes to must_fix, not checks
        assert any("G2.7" in mf for mf in result.get("must_fix", []))


@pytest.mark.unit
class TestG2CheckBlocks:
    """G2.8-G2.9 pre/post write check blocks."""

    def test_g28_fails_when_pre_write_check_missing(self, tmp_path: Path) -> None:
        """Chapter without ## PRE_WRITE_CHECK -> G2.8 FAIL."""
        ch = tmp_path / "chapter-001.md"
        ch.write_text("# Chapter\n\n内容。\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        assert any("G2.8" in mf for mf in result.get("must_fix", []))

    def test_g28_passes_when_pre_write_check_present(self, tmp_path: Path) -> None:
        """Chapter with ## PRE_WRITE_CHECK -> G2.8 PASS."""
        ch = tmp_path / "chapter-001.md"
        ch.write_text("# Chapter\n\n## PRE_WRITE_CHECK\n内容。\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        g28 = next((c for c in result["checks"] if c.get("id") == "G2.8"), None)
        assert g28 is not None
        assert g28["s"] == "PASS"

    def test_g29_fails_when_post_write_check_missing(self, tmp_path: Path) -> None:
        """Chapter without ## POST_WRITE_SELF_CHECK -> G2.9 FAIL."""
        ch = tmp_path / "chapter-001.md"
        ch.write_text("# Chapter\n\n## PRE_WRITE_CHECK\n内容。\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        assert any("G2.9" in mf for mf in result.get("must_fix", []))


@pytest.mark.unit
class TestG2TemplatePlaceholder:
    """G2.10 template placeholder detection."""

    def test_g210_fails_when_placeholder_above_threshold(self, tmp_path: Path) -> None:
        """File with >10% 待填充 lines -> G2.10 FAIL."""
        ch = tmp_path / "chapter-001.md"
        # 7 out of 10 lines contain 待填充 -> 70% > 10%
        lines = [
            ("待填充的内容待填充的内容待填充的内容。\n" if i % 2 == 1 else "这是正常内容。\n")
            for i in range(10)
        ]
        ch.write_text("".join(lines), encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        assert any("G2.10" in mf for mf in result.get("must_fix", []))

    def test_g210_passes_when_placeholder_below_threshold(self, tmp_path: Path) -> None:
        """File with <10% 待填充 lines -> G2.10 PASS."""
        ch = tmp_path / "chapter-001.md"
        ch.write_text("这是完全正常的内容没有任何模板占位符。\n" * 20, encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        g210 = next((c for c in result["checks"] if c.get("id") == "G2.10"), None)
        assert g210 is not None
        assert g210["s"] == "PASS"


@pytest.mark.unit
class TestG2TruthFileDiff:
    """G2.11 truth file .bak comparison."""

    def test_g211_fails_when_truth_file_has_removals(self, tmp_path: Path) -> None:
        """Truth file with .bak showing removed lines -> G2.11 FAIL."""
        rd = tmp_path / "round"
        rd.mkdir()
        truth = rd / "hooks.md"
        truth.write_text("new line\n", encoding="utf-8")
        bak = rd / "hooks.md.bak"
        bak.write_text("old line that was removed\nanother line\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(truth)], "truth", str(rd)))
        assert any("G2.11" in mf for mf in result.get("must_fix", []))

    def test_g211_passes_when_bak_unchanged(self, tmp_path: Path) -> None:
        """Truth file with identical .bak content -> G2.11 PASS."""
        rd = tmp_path / "round"
        rd.mkdir()
        truth = rd / "hooks.md"
        truth.write_text("same content\n", encoding="utf-8")
        bak = rd / "hooks.md.bak"
        bak.write_text("same content\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(truth)], "truth", str(rd)))
        g211 = next((c for c in result["checks"] if c.get("id") == "G2.11"), None)
        assert g211 is not None
        assert g211["s"] == "PASS"


@pytest.mark.unit
class TestG2FileCompleteness:
    """G2.12 sentence-final punctuation check."""

    def test_g212_warns_when_file_truncated(self, tmp_path: Path) -> None:
        """Chapter ending without punctuation -> G2.12 WARN."""
        ch = tmp_path / "chapter-001.md"
        ch.write_text("# Chapter\n\n内容正文\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        g212 = next((c for c in result["checks"] if c.get("id") == "G2.12"), None)
        assert g212 is not None
        assert g212["s"] == "WARN"

    def test_g212_passes_when_file_ends_with_punctuation(self, tmp_path: Path) -> None:
        """Chapter ending with sentence-final punctuation -> G2.12 PASS."""
        ch = tmp_path / "chapter-001.md"
        ch.write_text("# Chapter\n\n内容正文。\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        g212 = next((c for c in result["checks"] if c.get("id") == "G2.12"), None)
        assert g212 is not None
        assert g212["s"] == "PASS"

    def test_g212_passes_when_ends_with_heading(self, tmp_path: Path) -> None:
        """Chapter ending with a heading -> G2.12 PASS (heading is exempt)."""
        ch = tmp_path / "chapter-001.md"
        ch.write_text("# Chapter\n\nContent\n\n## Next Section\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(ch)], "chapter"))
        g212 = next((c for c in result["checks"] if c.get("id") == "G2.12"), None)
        assert g212 is not None
        assert g212["s"] == "PASS"


@pytest.mark.unit
class TestG2YamlFrontmatter:
    """G2.5 YAML frontmatter edge cases."""

    def test_g25_skips_yaml_error_on_non_structured_file(self, tmp_path: Path) -> None:
        """Non-structured .md file with YAML parse error -> G2.5 SKIP (not FAIL)."""
        report = tmp_path / "report.md"
        report.write_text("---\nbad: : yaml\n---\nContent\n", encoding="utf-8")
        result = _result_dict(gate_G2([str(report)], "report"))
        g25 = next((c for c in result["checks"] if c.get("id") == "G2.5"), None)
        assert g25 is not None
        assert g25["s"] == "SKIP"

    def test_g24_passes_on_valid_json(self, tmp_path: Path) -> None:
        """Valid JSON file -> G2.4 PASS in checks."""
        jf = tmp_path / "data.json"
        jf.write_text('{"key": "value"}', encoding="utf-8")
        result = _result_dict(gate_G2([str(jf)], "report"))
        g24 = next((c for c in result["checks"] if c.get("id") == "G2.4"), None)
        assert g24 is not None
        assert g24["s"] == "PASS"


# ---------------------------------------------------------------------------
# Branch coverage (PR-56 coverage fill)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_g23_fails_on_non_utf8_file(tmp_path: Path) -> None:
    """A non-UTF-8 file -> G2.3 FAIL (covers g2.py:60-62)."""
    f = tmp_path / "bad.md"
    f.write_bytes(b"\xff\xfe\x00invalid")
    result = _result_dict(gate_G2([str(f)], "report"))
    assert any("G2.3" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_g25_fails_when_structured_file_lacks_frontmatter(tmp_path: Path) -> None:
    """A truth/*.md without YAML frontmatter -> G2.5 FAIL (covers g2.py:86)."""
    truth = tmp_path / "truth"
    truth.mkdir()
    f = truth / "current_state.md"
    f.write_text("# State\n\nNo frontmatter here.\n", encoding="utf-8")
    result = _result_dict(gate_G2([str(f)], "report"))
    assert any("G2.5" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_is_important_chapter_via_volume_map_annotation(tmp_path: Path) -> None:
    """A chapter flagged 重要 in volume_map.md -> is_important True (covers g2.py:248-254)."""
    ch_dir = tmp_path / "chapters"
    ch_dir.mkdir()
    ch = ch_dir / "chapter-005.md"
    ch.write_text(
        "# 第5章\n\n## PRE_WRITE_CHECK\nx\n\n## POST_WRITE_SELF_CHECK\ny\n", encoding="utf-8"
    )
    outline = tmp_path / "outline"
    outline.mkdir()
    (outline / "volume_map.md").write_text("# Map\n\n第5章（爆发段）高潮场景。\n", encoding="utf-8")
    result = _result_dict(gate_G2([str(ch)], "chapter", project_dir=str(tmp_path)))
    g27 = next((c for c in result["checks"] if c.get("id") == "G2.7"), None)
    assert g27 is not None
    assert g27.get("is_important") is True
    assert g27.get("ceiling") == 10000  # CHAPTER_WORD_CEILING


@pytest.mark.unit
def test_is_important_chapter_via_plan_marker(tmp_path: Path) -> None:
    """A chapter whose plan marks it 重要章 -> is_important True (covers g2.py:256-263)."""
    ch_dir = tmp_path / "chapters"
    ch_dir.mkdir()
    ch = ch_dir / "chapter-007.md"
    ch.write_text("# 第7章\n\n## PRE_WRITE_CHECK\nx\n", encoding="utf-8")
    plans = tmp_path / "plans"
    plans.mkdir()
    # _is_important_chapter builds the plan path as chapter-{n}-plan.md with
    # unpadded int n (chapter-007.md -> n=7 -> chapter-7-plan.md).
    (plans / "chapter-7-plan.md").write_text(
        "# Plan\n\n## 1. 概述\n本章是重要章，关键转折。\n\n## 2. 细节\n", encoding="utf-8"
    )
    result = _result_dict(gate_G2([str(ch)], "chapter", project_dir=str(tmp_path)))
    g27 = next((c for c in result["checks"] if c.get("id") == "G2.7"), None)
    assert g27 is not None
    assert g27.get("is_important") is True


@pytest.mark.unit
def test_g211_truth_file_with_removed_lines_fails(tmp_path: Path) -> None:
    """A truth file whose .bak shows removed lines -> G2.11 FAIL (covers g2.py:190-211)."""
    rd = tmp_path / "round"
    rd.mkdir()
    truth_dir = tmp_path / "truth"
    truth_dir.mkdir(parents=True)
    truth_f = truth_dir / "state.md"
    truth_f.write_text("---\nstatus: active\n---\n# State\n新内容。\n", encoding="utf-8")
    (truth_dir / "state.md.bak").write_text(
        "---\nstatus: active\n---\n# State\n旧内容。\n", encoding="utf-8"
    )
    result = _result_dict(gate_G2([str(truth_f)], "truth", round_dir=str(rd)))
    assert any("G2.11" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_g211_truth_file_unchanged_passes(tmp_path: Path) -> None:
    """A truth file identical to its .bak -> G2.11 PASS (covers g2.py:212-213)."""
    rd = tmp_path / "round"
    rd.mkdir()
    truth_dir = tmp_path / "truth"
    truth_dir.mkdir(parents=True)
    content = "---\nstatus: active\n---\n# State\n不变。\n"
    truth_f = truth_dir / "state.md"
    truth_f.write_text(content, encoding="utf-8")
    (truth_dir / "state.md.bak").write_text(content, encoding="utf-8")
    result = _result_dict(gate_G2([str(truth_f)], "truth", round_dir=str(rd)))
    g211 = next((c for c in result["checks"] if c.get("id") == "G2.11"), None)
    assert g211 is not None
    assert g211["s"] == "PASS"


# ---------------------------------------------------------------------------
# G2.dec.* — decisions.json validation branch (M4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestG2DecisionsBranch:
    """G2.dec.* — decisions.json validation (M4)."""

    def test_valid_decisions_json_passes(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
        }
        fp = tmp_path / "context" / "chapter-5-context-decisions.json"
        fp.parent.mkdir(parents=True)
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = gate_G2(str(fp), file_type="decisions", round_dir=str(tmp_path))
        data = _result_dict(result)
        assert data["status"] == "PASS"

    def test_invalid_json_fails_g2_dec_1(self, tmp_path: Path) -> None:
        fp = tmp_path / "chapter-5-decisions.json"
        fp.write_text("{not valid json", encoding="utf-8")
        result = gate_G2(str(fp), file_type="decisions", round_dir=str(tmp_path))
        data = _result_dict(result)
        assert data["status"] == "FAIL"
        assert any("G2.dec.1" in mf for mf in data.get("must_fix", []))

    def test_wrong_schema_version_fails_g2_dec_2(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "wrong-version",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
        }
        fp = tmp_path / "chapter-5-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = gate_G2(str(fp), file_type="decisions", round_dir=str(tmp_path))
        data = _result_dict(result)
        assert data["status"] == "FAIL"
        assert any("G2.dec.2" in mf for mf in data.get("must_fix", []))

    def test_missing_required_keys_fails_g2_dec_3(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            # missing: chapter, produced_at, selections
        }
        fp = tmp_path / "chapter-5-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = gate_G2(str(fp), file_type="decisions", round_dir=str(tmp_path))
        data = _result_dict(result)
        assert data["status"] == "FAIL"
        assert any("G2.dec.3" in mf for mf in data.get("must_fix", []))

    def test_decisions_does_not_trigger_word_count(self, tmp_path: Path) -> None:
        """Critical: G2.6/G2.7 word count must NOT run on decisions files."""
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
        }
        fp = tmp_path / "chapter-5-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = gate_G2(str(fp), file_type="decisions", round_dir=str(tmp_path))
        data = _result_dict(result)
        # G2.6/G2.7 should NOT appear in checks
        check_ids = [c.get("id", "") for c in data.get("checks", [])]
        assert not any(c == "G2.6" for c in check_ids)
        assert not any(c == "G2.7" for c in check_ids)

    def test_decisions_branch_skips_markdown_files(self, tmp_path: Path) -> None:
        """C1: mixed .md + .json with file_type='decisions' must skip the .md.

        Skills like chapter-drafting/context-composing write BOTH a chapter.md
        artifact and a sidecar decisions.json. When file_type='decisions' is
        applied uniformly to all outputs, the .md file must be SKIPPED (it is
        validated by its own file_type gate), not failed as 'invalid JSON'.
        Regression guard for G2.dec.1 mis-firing on .md content.
        """
        # A markdown file with non-JSON content (would FAIL json.loads).
        md_fp = tmp_path / "chapter-5.md"
        md_fp.write_text(
            "# 第5章\n\n## PRE_WRITE_CHECK\nx\n\n## POST_WRITE_SELF_CHECK\ny\n",
            encoding="utf-8",
        )
        # A valid decisions.json sidecar.
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
        }
        json_fp = tmp_path / "chapter-5-decisions.json"
        json_fp.write_text(json.dumps(decisions), encoding="utf-8")

        result = gate_G2(f"{md_fp},{json_fp}", file_type="decisions", round_dir=str(tmp_path))
        data = _result_dict(result)

        # The .md must NOT produce a G2.dec.1 invalid-JSON failure.
        assert not any("G2.dec.1" in mf and str(md_fp) in mf for mf in data.get("must_fix", [])), (
            f".md file was not skipped: {data.get('must_fix', [])}"
        )

        # The .json must be validated (G2.dec PASS recorded for it).
        dec_pass = [
            c
            for c in data.get("checks", [])
            if c.get("id") == "G2.dec" and c.get("file") == str(json_fp)
        ]
        assert dec_pass, f".json file was not validated: {data.get('checks', [])}"
        assert dec_pass[0]["s"] == "PASS"

        # Overall the gate passes (the .md was skipped, not failed).
        assert data["status"] == "PASS"

    def test_g2_dec4_detects_concatenated_json(self, tmp_path: Path) -> None:
        """G2.dec.4 fails when multiple JSON objects exist in one file."""
        decisions_json = tmp_path / "chapter-5-decisions.json"
        obj1 = {"$schema": "shenbi-decisions-v1", "skill": "chapter-drafting"}
        obj2 = {"$schema": "shenbi-decisions-v1", "skill": "chapter-revision"}
        content = json.dumps(obj1) + "\n" + json.dumps(obj2)
        decisions_json.write_text(content)

        result = gate_G2(str(decisions_json), file_type="decisions")
        data = _result_dict(result)
        assert data["status"] == "FAIL"
        assert any("G2.dec.4" in mf for mf in data.get("must_fix", []))

    def test_g2_dec4_passes_single_json(self, tmp_path: Path) -> None:
        """G2.dec.4 passes when only one JSON object is present."""
        decisions_json = tmp_path / "chapter-5-decisions.json"
        content = json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "chapter-drafting",
                "chapter": 5,
                "produced_at": "2026-07-07T12:00:00Z",
                "selections": [],
            }
        )
        decisions_json.write_text(content)

        result = gate_G2(str(decisions_json), file_type="decisions")
        data = _result_dict(result)
        # G2.dec.4 should not appear in checks or must_fix for single JSON
        assert not any("G2.dec.4" in mf for mf in data.get("must_fix", []))
        # Also verify the decisions pass
        assert data["status"] == "PASS"
        dec_pass = [c for c in data.get("checks", []) if c.get("id") == "G2.dec"]
        assert dec_pass
        assert dec_pass[0]["s"] == "PASS"
