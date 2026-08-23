"""Acceptance tests for spec #4 §6 (F10)."""

from pathlib import Path

from shenbi.pipeline.audit_aggregate import write_audit_aggregate

FIX = Path("tests/fixtures/audits/chapter-1-consistency.md")


def test_revision_input_bytes_drop_with_overlap(tmp_path: Path):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for name in ("chapter-1-consistency.md", "chapter-1-character.md"):
        (audit_dir / name).write_text(FIX.read_text(encoding="utf-8"), encoding="utf-8")
    raw_bytes = sum(p.stat().st_size for p in audit_dir.glob("chapter-1-*.md"))
    out = write_audit_aggregate(tmp_path, 1)
    assert out is not None
    assert out.stat().st_size < 0.5 * raw_bytes  # 双份重叠 → 显著下降


def test_lossless_every_raw_finding_survives(tmp_path: Path):
    from shenbi.pipeline.audit_aggregate import extract_finding_units

    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for name in ("chapter-1-consistency.md", "chapter-1-character.md"):
        (audit_dir / name).write_text(FIX.read_text(encoding="utf-8"), encoding="utf-8")
    write_audit_aggregate(tmp_path, 1)
    out = (audit_dir / "chapter-1.aggregate.md").read_text(encoding="utf-8")
    raw = FIX.read_text(encoding="utf-8")
    units, _ = extract_finding_units("chapter-1-consistency.md", raw)
    # 非空集护栏（fixture 有真实 WARNING 发现——发现项表行 + 建议修复项）
    assert len(units) >= 2, "lossless check must be non-vacuous"
    # 独立覆盖断言（非自证）：聚合含全部 raw finding 的 text
    for u in units:
        assert u.text in out, f"finding lost: {u.text[:60]}"
    # 修复建议（WARNING 级）逐字存活——revision 的可操作输入
    assert "了" in out and "密度" in out
    # 每份 raw 报告在聚合中被引用
    assert "chapter-1-consistency.md" in out
    assert "chapter-1-character.md" in out
