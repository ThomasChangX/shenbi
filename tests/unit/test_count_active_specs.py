"""Unit tests for tools/count_active_specs.py (spec #49 R4 — C35 T1507)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from tools.count_active_specs import count_active, declared_count  # noqa: E402


def _write_specs(tmp_path: Path, n: int, header_count: int) -> Path:
    specs = tmp_path / "specs"
    specs.mkdir()
    for i in range(n):
        (specs / f"2026-01-0{i + 1}-spec.md").write_text("# Spec\n", encoding="utf-8")
    (specs / "archive").mkdir()
    (specs / "archive" / "old.md").write_text("# Old\n", encoding="utf-8")  # not counted
    (specs / "INDEX.md").write_text(
        f"# 索引\n\n> **活跃 spec 数**：{header_count}（注记 prose）\n", encoding="utf-8"
    )
    return specs


def test_count_excludes_index_and_archive(tmp_path: Path) -> None:
    specs = _write_specs(tmp_path, n=3, header_count=3)
    assert count_active(specs) == 3


def test_drift_fails(tmp_path: Path) -> None:
    specs = _write_specs(tmp_path, n=3, header_count=4)
    text = (specs / "INDEX.md").read_text(encoding="utf-8")
    assert declared_count(text) == 4
    assert count_active(specs) == 3


def test_missing_marker_returns_none(tmp_path: Path) -> None:
    assert declared_count("# no marker here\n") is None


def test_real_index_consistent() -> None:
    from tools.count_active_specs import SPECS_DIR

    assert count_active(SPECS_DIR) == declared_count(
        (SPECS_DIR / "INDEX.md").read_text(encoding="utf-8")
    )
