"""Fallback tests: missing aggregate read fails open to the raw glob pre-G1."""

import fnmatch
from pathlib import Path

from shenbi.pipeline.dispatch_helper import (
    OPTIONAL_READS,
    _resolve_read_with_fallback,
)

FIX = Path("tests/fixtures/audits/chapter-1-consistency.md")


def test_missing_aggregate_falls_back_to_raw_glob(tmp_path: Path):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    (audit_dir / "chapter-1-consistency.md").write_text(
        FIX.read_text(encoding="utf-8"), encoding="utf-8"
    )
    paths = _resolve_read_with_fallback(tmp_path, "audits/chapter-1.aggregate.md")
    # 回退注入 raw glob 的全部匹配
    assert [p.name for p in paths] == ["chapter-1-consistency.md"]


def test_present_aggregate_is_used_directly(tmp_path: Path):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    (audit_dir / "chapter-1.aggregate.md").write_text("# agg\n", encoding="utf-8")
    paths = _resolve_read_with_fallback(tmp_path, "audits/chapter-1.aggregate.md")
    assert [p.name for p in paths] == ["chapter-1.aggregate.md"]


def test_aggregate_registered_as_optional_read():
    # executor G1 前丢弃缺失 optional read 的既有机制（executor.py:177-190）
    # 必须覆盖聚合 read——否则 G1.1 对缺失 declared read 硬 FAIL，
    # reads-loop 回退在 executor 路径上永远走不到
    patterns = OPTIONAL_READS.get("shenbi-chapter-revision", [])
    assert any(fnmatch.fnmatch("chapter-1.aggregate.md", pat) for pat in patterns), (
        f"aggregate not optional for G1: {patterns}"
    )
