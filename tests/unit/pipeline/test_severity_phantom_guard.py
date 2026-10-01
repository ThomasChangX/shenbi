"""Severity-sensor phantom-marker guards (probe6 ch1, 2026-10-01).

An audit report's FORMAT DOCUMENTATION — the numbered submission-format
legend ``4. **严重度**:BLOCKING / CRITICAL / MINOR`` — matched every
severity sensor in the routing/consolidation chain:

* ``revision_router._SEVERITY_BLOCKING_RE`` → ``collect_audit_issues``
  returned a phantom blocking finding → route=regenerate,
  ``revision_count`` inflated toward the cap;
* ``parallel_dispatch.consolidate_review_results`` → review-summary
  reported ``BLOCKING Issues: 1`` and opened a ``## BLOCKING Issues``
  section that human reviewers then had to debunk;
* ``audit_aggregate._KEY_RE`` → the same line became a phantom finding
  unit fed into revision feedback.

A severity VALUE inside an enum list (``BLOCKING / CRITICAL / MINOR``) is
never a finding. These tests pin the guard across all three sites.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.audit_aggregate import extract_finding_units
from shenbi.pipeline.parallel_dispatch import consolidate_review_results
from shenbi.pipeline.revision_router import collect_audit_issues

#: Verbatim from novel-xinghuo-probe6/audits/chapter-1-sensitivity.md L144-146.
FORMAT_DOC_AUDIT = (
    "# 敏感性审查\n\n"
    "后续章节若发现缺陷，须按四要素格式提交：\n\n"
    "1. **位置**：文件路径 + 行号范围\n"
    "2. **原文引述**：≥20 字上下文\n"
    "3. **违反规则**：规则名（精确匹配）\n"
    "4. **严重度**：BLOCKING / CRITICAL / MINOR\n\n"
    "## 5. 评分\n\n**通过（PASS）。**\n"
)

REAL_FINDING_AUDIT = (
    "# 审查\n\n## 缺陷\n- **严重度**: BLOCKING\n- **位置**: chapters/chapter-1.md L10-12\n"
)


def test_router_format_doc_legend_is_not_blocking(tmp_path: Path) -> None:
    d = tmp_path / "audits"
    d.mkdir()
    (d / "chapter-1-sensitivity.md").write_text(FORMAT_DOC_AUDIT, encoding="utf-8")
    issues, blocking = collect_audit_issues(tmp_path, 1)
    assert issues == []
    assert blocking is False


def test_router_real_severity_value_still_blocks(tmp_path: Path) -> None:
    d = tmp_path / "audits"
    d.mkdir()
    (d / "chapter-1-continuity.md").write_text(REAL_FINDING_AUDIT, encoding="utf-8")
    issues, blocking = collect_audit_issues(tmp_path, 1)
    assert blocking is True
    assert issues and issues[0]["severity"] == "BLOCKING"


def test_consolidator_format_doc_legend_counts_zero(tmp_path: Path) -> None:
    d = tmp_path / "audits"
    d.mkdir()
    (d / "chapter-1-sensitivity.md").write_text(FORMAT_DOC_AUDIT, encoding="utf-8")
    out = consolidate_review_results([], 1, skills=[], project_dir=tmp_path)
    assert "- **BLOCKING Issues**: 0" in out
    assert "## BLOCKING Issues" not in out


def test_consolidator_real_severity_value_counted(tmp_path: Path) -> None:
    d = tmp_path / "audits"
    d.mkdir()
    (d / "chapter-1-continuity.md").write_text(REAL_FINDING_AUDIT, encoding="utf-8")
    out = consolidate_review_results([], 1, skills=[], project_dir=tmp_path)
    assert "- **BLOCKING Issues**: 1" in out
    assert "## BLOCKING Issues" in out


def test_aggregate_format_doc_legend_is_not_a_finding_unit() -> None:
    units, _context = extract_finding_units("chapter-1-sensitivity.md", FORMAT_DOC_AUDIT)
    assert units == []


def test_aggregate_real_severity_value_is_a_finding_unit() -> None:
    # Inline-key form with leading content (aggregate's documented finding
    # shape); a bare ``- **严重度**: BLOCKING`` label line is intentionally
    # degraded to context by _LABEL_ONLY_RE.
    report = "# 审查\n- 对白信息倾倒: severity: BLOCKING\n"
    units, _context = extract_finding_units("chapter-1-continuity.md", report)
    assert any(u.severity == "BLOCKING" for u in units)
