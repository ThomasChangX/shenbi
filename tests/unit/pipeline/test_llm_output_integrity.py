"""Tests for the unified LLM-output integrity module."""

from __future__ import annotations

from shenbi.pipeline.llm_output_integrity import (
    check_audit_completeness,
    check_audit_line_refs,
    check_markdown_fence_balance,
    check_prose_leakage,
    detect_write_failure,
)

# --- detect_write_failure (dominance rule) ---


class TestDetectWriteFailure:
    def test_chinese_sandbox_at_start(self):
        content = "由于沙箱限制，我无法直接写文件。请使用现有内容。"
        is_fail, sig = detect_write_failure(content)
        assert is_fail is True
        assert sig is not None
        assert "沙箱" in sig or "sandbox" in sig.lower()

    def test_english_readonly_at_start(self):
        content = (
            "I cannot write the file in this read-only sandbox. "
            "Use the existing content from input."
        )
        is_fail, _ = detect_write_failure(content)
        assert is_fail is True

    def test_dominant_region_over_half(self):
        # Match is not at start (there's a title line) but the diagnostic
        # region spans >50% of the output.
        content = (
            "Title\n"
            "The file on disk can't be updated (read-only sandbox). "
            "Use the existing content from input markers was already provided."
        )
        is_fail, _ = detect_write_failure(content)
        assert is_fail is True

    def test_passing_mention_is_not_failure(self):
        # Legitimate prose that mentions "sandbox" / "cannot write" in passing.
        content = (
            "林烽穿过沙箱般的废墟，心中暗道：'我不能写下这段历史。' "
            "他继续前行，脚步声回荡在空旷的走廊里。" * 20
        )
        is_fail, _ = detect_write_failure(content)
        assert is_fail is False

    def test_clean_prose_is_not_failure(self):
        content = "林烽推开门，映入眼帘的是一间陈旧的教室。" * 50
        is_fail, _ = detect_write_failure(content)
        assert is_fail is False


# --- check_prose_leakage ---


class TestCheckProseLeakage:
    def test_model_leakage_flagged(self, tmp_path):
        p = tmp_path / "chapter-56.md"
        p.write_text("正文内容……\nNow the decisions JSON:\n```json", encoding="utf-8")
        issues = check_prose_leakage(p)
        assert any("G4.pi.model_leakage" in i for i in issues)

    def test_unfinished_ending_flagged(self, tmp_path):
        p = tmp_path / "chapter-56.md"
        p.write_text("他走到门前，准备：", encoding="utf-8")
        issues = check_prose_leakage(p)
        assert any("G4.pi.unfinished_ending" in i for i in issues)

    def test_clean_prose_no_issues(self, tmp_path):
        p = tmp_path / "chapter-1.md"
        p.write_text("林烽推开门，走进教室。" * 200, encoding="utf-8")
        assert check_prose_leakage(p) == []


# --- check_markdown_fence_balance ---


class TestCheckFenceBalance:
    def test_odd_fences_flagged(self, tmp_path):
        p = tmp_path / "chapter-1.md"
        p.write_text("text\n```\ncode\nmore text", encoding="utf-8")
        issues = check_markdown_fence_balance(p)
        assert len(issues) == 1
        assert "G4.pi.fence_imbalance" in issues[0]

    def test_even_fences_ok(self, tmp_path):
        p = tmp_path / "chapter-1.md"
        p.write_text("text\n```\ncode\n```\nmore", encoding="utf-8")
        assert check_markdown_fence_balance(p) == []


# --- check_audit_completeness ---


class TestCheckAuditCompleteness:
    def test_aborted_stub_flagged(self, tmp_path):
        p = tmp_path / "chapter-32-foreshadowing.md"
        p.write_text("所有输入文件已确认。现在执行完整的伏笔审计……", encoding="utf-8")
        issues = check_audit_completeness(p)
        # Short AND no verdict AND has preamble — at least one of these fires.
        assert len(issues) >= 1
        assert any(
            ("too_short" in i) or ("aborted_stub" in i) or ("no_verdict" in i) for i in issues
        )

    def test_complete_audit_no_issues(self, tmp_path):
        p = tmp_path / "chapter-32-foreshadowing.md"
        body = "# 伏笔审计\n\n" + ("详尽分析内容。" * 100) + "\n\n判定：通过 (PASS)"
        p.write_text(body, encoding="utf-8")
        assert check_audit_completeness(p) == []


# --- check_audit_line_refs ---


class TestCheckAuditLineRefs:
    def test_stale_ref_flagged(self, tmp_path):
        audit = tmp_path / "chapter-55-foreshadowing.md"
        audit.write_text("参见 chapter-55.md L41-45 的细节。", encoding="utf-8")
        chapter = tmp_path / "chapter-55.md"
        chapter.write_text("line1\nline2\nline3\n", encoding="utf-8")
        issues = check_audit_line_refs(audit, chapter)
        assert len(issues) == 1
        assert "G4.av.stale_line_ref" in issues[0]
        assert "L41-45" in issues[0]

    def test_valid_ref_ok(self, tmp_path):
        audit = tmp_path / "chapter-1-continuity.md"
        audit.write_text("参见 chapter-1.md L2-3。", encoding="utf-8")
        chapter = tmp_path / "chapter-1.md"
        chapter.write_text("\n".join(f"line{i}" for i in range(20)) + "\n", encoding="utf-8")
        assert check_audit_line_refs(audit, chapter) == []

    def test_missing_chapter_no_issue(self, tmp_path):
        audit = tmp_path / "chapter-1-continuity.md"
        audit.write_text("参见 chapter-1.md L2-3。", encoding="utf-8")
        assert check_audit_line_refs(audit, tmp_path / "chapter-1.md") == []
