"""Spec #116 T2: vacuity registry sentinel lint tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import tools.lint_gate_power_baseline as lint

HEADER = (
    "# t\n\n| check | 口径 | 期望点火带 | 分类 | 证据 | 最近回放数 | 归因 |\n"
    "|---|---|---|---|---|---|---|\n"
)


def _write_baseline(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "gate-power-baseline.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_registry_matches_static_sources() -> None:
    """C4 修订：registry∪arms == chapter_drafting.py 单文件扫描 ∪ 显式补充。"""
    drift = lint.registry_drift()
    assert drift == [], drift


def test_missing_baseline_row_is_fail(tmp_path: Path) -> None:
    p = _write_baseline(tmp_path, HEADER)
    assert lint.lint_file(p, today=lint.PRE_ESCALATION, require_full_registry=True) == 1


def test_unclassified_zero_firing_warns_before_escalation(tmp_path: Path) -> None:
    body = HEADER + (
        "| `G4.cd.surge` | state-free | 0% | unclassified | — | 50 章 @ d (r) 0 点火 | — |\n"
    )
    p = _write_baseline(tmp_path, body)
    rc = lint.lint_file(p, today=lint.PRE_ESCALATION, require_full_registry=False)
    assert rc == 0  # WARN 级：exit 0


def test_unclassified_zero_firing_fails_after_escalation(tmp_path: Path) -> None:
    body = HEADER + (
        "| `G4.cd.surge` | state-free | 0% | unclassified | — | 50 章 @ d (r) 0 点火 | — |\n"
    )
    p = _write_baseline(tmp_path, body)
    assert lint.lint_file(p, today=lint.ESCALATION_DATE, require_full_registry=False) == 1


def test_decorative_without_evidence_fails(tmp_path: Path) -> None:
    body = HEADER + (
        "| `G4.cd.meta` | state-free | 0% | decorative |  | 50 章 @ d (r) 0 点火 | — |\n"
    )
    p = _write_baseline(tmp_path, body)
    assert lint.lint_file(p, today=lint.PRE_ESCALATION, require_full_registry=False) == 1


def test_classification_vocab_closed() -> None:
    assert (
        frozenset({"unclassified", "floor-untested", "decorative", "discriminating", "retired"})
        == lint.VALID_CLASSIFICATIONS
    )


def test_escalation_anchor_documented() -> None:
    """M1：升格锚=回填日+30 天（2026-11-19+30），模块常量注释与 baseline 头节同时声明。"""
    assert date(2026, 12, 19) == lint.ESCALATION_DATE
    assert date(2026, 11, 19) == lint.PRE_ESCALATION
