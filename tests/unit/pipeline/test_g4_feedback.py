"""Tests for enriched G4 retry feedback."""

from shenbi.pipeline.chapter_loop import _enrich_g4_feedback


def test_enrich_adds_format_example_for_known_check():
    """Known check IDs get format example appended."""
    failures = ["G4.rr.verdict:chapter-1-resonance.md:no_valid_verdict"]
    result = _enrich_g4_feedback(failures)

    assert "校准门判定" in result
    assert "判定: 通过" in result
    assert "G4.rr.verdict" in result


def test_enrich_adds_detail_table_example():
    """G4.rr.detail_table gets the scoring table format example."""
    failures = ["G4.rr.detail_table:chapter-2-resonance.md:missing_['裁判理由']"]
    result = _enrich_g4_feedback(failures)

    assert "评分明细表格式" in result
    assert "| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |" in result


def test_enrich_adds_evidence_example():
    """G4.rr.evidence gets the file:line reference example."""
    failures = ["G4.rr.evidence:chapter-3-resonance.md:no_file_line_ref"]
    result = _enrich_g4_feedback(failures)

    assert "chapter-N.md L45-52" in result or "文件和行号" in result


def test_enrich_handles_unknown_checks():
    """Unknown check IDs get generic feedback without format examples."""
    failures = ["G4.unknown_check:file.md:some_issue"]
    result = _enrich_g4_feedback(failures)

    assert "G4.unknown_check" in result
    # Should not crash or add examples for unknown checks


def test_enrich_handles_multiple_failures():
    """Multiple failures all get documented with their examples."""
    failures = [
        "G4.rr.verdict:ch1-res.md:no_valid_verdict",
        "G4.rr.evidence:ch1-res.md:no_file_line_ref",
    ]
    result = _enrich_g4_feedback(failures)

    assert "校准门判定" in result
    assert "文件和行号" in result or "chapter-N.md" in result
