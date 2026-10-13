"""Bespoke error-path tests for g4_plot_thread_weaver."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.plot_thread_weaver import g4_plot_thread_weaver


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"
    sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True)
    marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


@pytest.mark.unit
def test_fails_when_thread_map_missing(tmp_path: Path) -> None:
    """Missing thread_map.md -> FAIL."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    result = _result(g4_plot_thread_weaver([str(marker)], rd=str(project_dir)))
    assert any("G4.thread.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_no_lines(tmp_path: Path) -> None:
    """thread_map.md without A/B/C lines -> FAIL."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "thread_map.md").write_text("# Threads\nsomething\n", encoding="utf-8")
    result = _result(g4_plot_thread_weaver([str(marker)], rd=str(project_dir)))
    assert any("G4.pt.lines" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_passes_with_valid_thread_map(tmp_path: Path) -> None:
    """thread_map.md with A/B/C, table, blank detection -> PASS.

    Positive fixture follows the SKILL.md contract's own vocabulary
    (classification headings "### A 线(长线)" fullwidth in source, summary
    "**A 线数**", overview-table ID column "A1"), NOT the checker's legacy
    literals — a checker-validated-by-its-own-vocabulary fixture let three
    contract-faithful outputs fail G4 in CI-blind silence (canary
    escalation #4, 2026-09-28).
    """
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "thread_map.md").write_text(
        "# 线索总图\n\n"
        "| ID | 线索 | 优先级 | 类型 | 起 | 止 |\n"
        "|----|------|--------|------|----|----|\n"
        "| A1 | 不被记账的人 | P0 | 长线 | 1 | 3 |\n"
        "| B1 | 第一份差事 | P1 | 中线 | 1 | 2 |\n"
        "| C1 | 一顿热饭 | P2 | 短线 | 1 | 1 |\n\n"
        "### A 线（长线）：跨全书的核心悬念，共 1 条\n内容。\n\n"
        "### B 线（中线）：卷内主要支线，共 1 条\n内容。\n\n"
        "### C 线（短线）：1-3 章内可解的次要情节，共 1 条\n内容。\n\n"
        "**A 线数**: 1\n**B 线数**: 1\n**C 线数**: 1\n\n"
        "空白检测：无空白章节。\n",
        encoding="utf-8",
    )
    result = _result(g4_plot_thread_weaver([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS", result.get("must_fix")


@pytest.mark.unit
def test_passes_with_legacy_literal_vocabulary(tmp_path: Path) -> None:
    """Legacy `## A 长线` literal headings still pass (backward compat)."""
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "thread_map.md").write_text(
        "## A 长线\ncontent\n## B 中线\ncontent\n"
        "## C 短线\ncontent\n"
        "| col1 | col2 | col3 |\n| a | b | c |\n| d | e | f |\n"
        "空白检测\n",
        encoding="utf-8",
    )
    result = _result(g4_plot_thread_weaver([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_single_tier_still_passes_any_match_semantics(tmp_path: Path) -> None:
    """Any single tier match passes — missing_A/B/C fires only when ALL are absent.

    Documents the checker's actual (historical) any-match semantics; the
    three-tier ALL-required tightening was deliberately NOT taken here
    (contract suggests tier counts, doesn't hard-mandate every tier).
    """
    project_dir, marker = _setup(tmp_path)
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "thread_map.md").write_text(
        "### A 线（长线）：只有 A\n| a | b |\n| c | d |\n| e | f |\n空白检测\n",
        encoding="utf-8",
    )
    result = _result(g4_plot_thread_weaver([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"
