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
    # 真实 fixture：发现项表 warning 行 + 建议修复 **[WARNING]** 列表项
    units, ctx = extract_finding_units("chapter-1-consistency.md", _content())
    assert len(units) >= 2
    assert all(u.severity == "WARNING" for u in units)
    assert any("了" in u.text and "密度" in u.text for u in units)
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
    # 无损：每个 raw 单元的 text 都出现在聚合（fixture 有真实 WARNING，非空集）
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
