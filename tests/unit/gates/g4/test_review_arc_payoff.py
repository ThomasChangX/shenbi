"""Tests for g4_review_arc_payoff.

Validates the review-arc-payoff output report carries the structured signal the
spec §6.4 gate depends on: a 5-dimension 评分明细 table with the required column
set, all five dimension rows, a 门判定 section with a valid verdict, an explicit
伏笔兑现质量 ≥15 sub-floor check, and file+line evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.review_arc_payoff import g4_review_arc_payoff


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_review_arc_payoff(fps, rd))


# Valid report: full 5-dim table + gate verdict + foreshadow sub-floor + evidence.
VALID = """# 弧级正向质量门报告

## 评分明细

| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |
|------|------|------|--------|------|----------|
| 弧情感交付 | 20 | 25 | high | `chapters/chapter-12.md` L45-60 | 高潮落地 |
| 伏笔兑现质量 | 18 | 25 | high | `chapters/chapter-11.md` L30-38 | 挣来的 |
| 线索收束 | 16 | 20 | mid | `truth/pending_hooks.md` L5 | 有意携带 |
| 期待债务结算 | 12 | 15 | mid | `truth/pending_hooks.md` L9 | 净偿还 |
| 角色弧推进 | 13 | 15 | high | `chapters/chapter-10.md` L5 | 弧推进 |

## 门判定

overall 79 ≥ 80 ✗
伏笔兑现质量 18 ≥ 子地板 15 ✓
判定: 阻断
"""


@pytest.mark.unit
def test_valid_report_passes(tmp_path: Path) -> None:
    f = tmp_path / "audits" / "volume-1-payoff.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(VALID, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_missing_confidence_column_fails(tmp_path: Path) -> None:
    f = tmp_path / "audits" / "volume-1-payoff.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(
        "# 报告\n\n## 评分明细\n\n| 维度 | 得分 |\n|------|------|\n| 弧情感交付 | 10 |\n",
        encoding="utf-8",
    )
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.ap.detail_table" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_missing_dimension_row_fails(tmp_path: Path) -> None:
    # Table has all columns but only 4 of 5 dimensions (missing 角色弧推进).
    body = VALID.replace(
        "| 角色弧推进 | 13 | 15 | high | `chapters/chapter-10.md` L5 | 弧推进 |\n", ""
    )
    f = tmp_path / "audits" / "volume-1-payoff.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.ap.dims" in mf for mf in result["must_fix"])


@pytest.mark.unit
@pytest.mark.parametrize("verdict", ["放行", "阻断"])
def test_accepts_each_valid_verdict(tmp_path: Path, verdict: str) -> None:
    body = VALID.replace("判定: 阻断", f"判定: {verdict}")
    f = tmp_path / "audits" / "volume-1-payoff.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS"
    assert any(c["id"] == "G4.ap.verdict" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_missing_gate_section_fails(tmp_path: Path) -> None:
    body = VALID.replace("## 门判定", "## 其它")
    f = tmp_path / "audits" / "volume-1-payoff.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.ap.verdict" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_invalid_verdict_value_fails(tmp_path: Path) -> None:
    body = VALID.replace("判定: 阻断", "判定: 优秀")
    f = tmp_path / "audits" / "volume-1-payoff.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.ap.verdict" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_missing_foreshadow_subfloor_fails(tmp_path: Path) -> None:
    # Gate section present + valid verdict, but no 伏笔兑现质量 ≥15 line.
    body = VALID.replace("伏笔兑现质量 18 ≥ 子地板 15 ✓\n", "兑现检查略\n")
    f = tmp_path / "audits" / "volume-1-payoff.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.ap.foreshadow_floor" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_missing_file_line_evidence_fails(tmp_path: Path) -> None:
    # Strip every file/line ref from the evidence cells.
    body = VALID
    for ref in [
        "`chapters/chapter-12.md` L45-60",
        "`chapters/chapter-11.md` L30-38",
        "`truth/pending_hooks.md` L5",
        "`truth/pending_hooks.md` L9",
        "`chapters/chapter-10.md` L5",
    ]:
        body = body.replace(ref, "叙事平淡")
    f = tmp_path / "audits" / "volume-1-payoff.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.ap.evidence" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_empty_file_list_skips() -> None:
    result = _run([])
    assert result["status"] == "PASS"
    assert any(c.get("s") == "SKIP" for c in result["checks"])


@pytest.mark.unit
def test_nonexistent_file_fails(tmp_path: Path) -> None:
    result = _run([str(tmp_path / "nope.md")])
    assert result["status"] == "FAIL"
    assert any("G4.ap.not_found" in mf for mf in result["must_fix"])
