"""T1 tests for the F10 audit aggregation layer (spec §5.1a)."""

from pathlib import Path

from shenbi.pipeline.audit_aggregate import (
    FindingUnit,
    extract_finding_units,
    render_aggregate,
    write_audit_aggregate,
)

FIXTURE = Path("tests/fixtures/audits/chapter-1-consistency.md")


def _content() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_extract_captures_real_fixture_warning_findings():
    # 真实产物 fixture（novel-output anti-ai 审计副本）：表行 + **WARNING** 列表项
    units, ctx = extract_finding_units("chapter-1-consistency.md", _content())
    assert len(units) >= 2
    assert {u.severity for u in units} == {"WARNING", "ERROR"}
    assert any(u.severity == "WARNING" and "微微" in u.text for u in units)
    assert any(u.severity == "ERROR" and "破折号" in u.text for u in units)
    # 上下文保留结果/评分行
    assert any("通过" in line for line in ctx)
    # 空表行（全 — 的 OOC 行）与 BDI PASS 行不得成为 finding
    assert all(u.severity in {"BLOCKING", "CRITICAL", "WARNING", "ERROR"} for u in units)


def test_extract_captures_blocking_and_critical_forms():
    content = (
        "## Findings\n"
        "| 段落 | 类型 | 严重度 |\n|---|---|---|\n"
        "| P3 | 了-密度 | **BLOCKING** |\n"
        "- P5 对白信息倾倒：severity: CRITICAL\n"
    )
    units, _ = extract_finding_units("chapter-1-x.md", content)
    assert len(units) == 2
    assert units[0].severity == "BLOCKING"
    assert units[1].severity == "CRITICAL"


def test_extract_degrades_non_entry_severity_to_context():
    # 标题/段落形态的 severity 行不丢：降级为逐字 context（无损优先）
    content = "## BLOCKING：第 7 段 OOC\nP5 对白信息倾倒：CRITICAL\n| 结果 | 通过（1 warning） |\n"
    units, ctx = extract_finding_units("chapter-1-x.md", content)
    assert units == []
    assert any("BLOCKING：第 7 段 OOC" in line for line in ctx)
    assert any("P5 对白信息倾倒：CRITICAL" in line for line in ctx)
    # 表格形态的元数据行不得虚增 finding
    assert any("通过" in line for line in ctx)


def test_render_is_lossless_and_deduped():
    raw = _content()
    units, ctx = extract_finding_units("chapter-1-character.md", raw)
    units2, _ = extract_finding_units("chapter-1-consistency.md", raw)
    merged: dict[tuple[str, str], FindingUnit] = {}
    for u in [*units, *units2]:
        merged.setdefault((u.severity, u.text), u)
    out = render_aggregate(1, list(merged.values()), {"chapter-1-consistency.md": ctx})
    # 无损：每个 raw 单元的 text 都出现在聚合（真实 fixture 有 WARNING，非空集）
    assert units, "fixture must yield at least one finding (non-vacuous)"
    for u in [*units, *units2]:
        assert u.text in out
    # 对账断言（防解析器自证）：报告方计数 == 去重条目数
    assert out.count("报告方:") == len(merged)
    # 不以 --- 开头（G1.3）
    assert not out.startswith("---")
    # 双份相同内容 → 聚合显著小于 2×raw
    assert len(out) < 2 * len(raw)


def test_resonance_report_preserved_verbatim(tmp_path: Path):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    raw = _content()
    (audit_dir / "chapter-1-character.md").write_text(raw, encoding="utf-8")
    (audit_dir / "chapter-1-resonance.md").write_text(raw, encoding="utf-8")
    out = write_audit_aggregate(tmp_path, 1)
    assert out is not None
    agg = out.read_text(encoding="utf-8")
    # resonance 全文逐字保留（spec §5.1a：其单条 read 已删，只能经聚合存活）
    assert raw in agg


def test_write_audit_aggregate_end_to_end(tmp_path: Path):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for name in ("chapter-1-consistency.md", "chapter-1-character.md"):
        (audit_dir / name).write_text(_content(), encoding="utf-8")
    out = write_audit_aggregate(tmp_path, 1)
    assert out is not None and out.name == "chapter-1.aggregate.md"
    first = out.read_text(encoding="utf-8")
    # 幂等：重跑内容一致
    write_audit_aggregate(tmp_path, 1)
    assert out.read_text(encoding="utf-8") == first
    # 点分隔：聚合文件不被 chapter-1-*.md glob 匹配
    assert all(p.name != "chapter-1.aggregate.md" for p in audit_dir.glob("chapter-1-*.md"))


def test_write_returns_none_when_no_reports(tmp_path: Path):
    assert write_audit_aggregate(tmp_path, 1) is None


def test_fixcheck_ch2_debris_not_counted_and_summary_excluded(tmp_path: Path):
    """Fixcheck ch2 (adjudication #14-7): the aggregate said BLOCKING
    Findings(6) while the truth was 2 — the bare-word IGNORECASE regex
    counted the review-summary's counter lines and per-report echoes
    (double counting: the summary is downstream of the same raw reports),
    severity LABEL lines (``- **严重度**: CRITICAL``), a lowercase PASS
    row, and fix-suggestion prose mentioning "CRITICAL 1". The sensor now
    accepts only anchored marker forms, and the summary is excluded from
    the glob.
    """
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    (audit_dir / "chapter-2-anti-ai.md").write_text(
        "| 5 | AI 标记词 | ERROR | ai_marker_hits = 4：心中暗道×1（框架预计算口径） |\n"
        "- **严重度**: CRITICAL\n"
        "- [BLOCKING] 全章禁用词 4 处：按 fatigueWords.替换建议逐词落地。\n",
        encoding="utf-8",
    )
    (audit_dir / "chapter-2-world-rules.md").write_text(
        "- [BLOCKING] 阁楼拆页段战力天花板越界：二选一修复。\n- **严重度**: WARNING\n",
        encoding="utf-8",
    )
    (audit_dir / "chapter-2-sensitivity.md").write_text(
        "- 现代词汇分层（genre-config rule-001，blocking）：公开对话均未出现网络流行语。PASS。\n",
        encoding="utf-8",
    )
    (audit_dir / "chapter-2-foreshadowing.md").write_text(
        "- [CRITICAL] MH-001 铁盒：正文缺「烫」与重量的一笔。\n"
        "  - **修复方案**：要么在正文补上一笔（see 备忘合规报告 CRITICAL 1 的 (a)）。\n",
        encoding="utf-8",
    )
    (audit_dir / "chapter-2-review-summary.md").write_text(
        "- **BLOCKING Issues**: 2\n- **CRITICAL Issues**: 2\n"
        "- chapter-2-anti-ai.md (chapter-2-anti-ai.md): - [BLOCKING] 全章禁用词 4 处…\n",
        encoding="utf-8",
    )

    out = write_audit_aggregate(tmp_path, 2)
    assert out is not None
    body = out.read_text(encoding="utf-8")

    def _count(sev: str) -> int:
        import re as _re

        m = _re.search(rf"## {sev} Findings \((\d+)\)", body)
        return int(m.group(1)) if m else 0

    assert _count("BLOCKING") == 2, body  # the two bracket findings, not 6
    assert _count("CRITICAL") == 1, body  # bracket only — no label/prose/echo
    assert _count("ERROR") == 1, body  # four-element table cell (real form)
    # the summary contributed nothing (no counters, no echo double-count)
    assert "Issues**" not in body and "chapter-2-anti-ai.md (chapter-2-anti-ai.md)" not in body
    # the real finding appears exactly once
    assert body.count("全章禁用词 4 处") == 1, body
    # PASS row is dropped entirely (lowercase prose, no anchored marker)
    assert "PASS。" not in body
    # fix-suggestion prose degrades to verbatim CONTEXT (lossless), never a
    # finding — the counts above already prove it produced no unit
    findings_part = body.split("## 报告上下文")[0]
    assert "CRITICAL 1 的 (a)" not in findings_part
