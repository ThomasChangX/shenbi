"""Tests for g4_review_resonance.

Validates the review-resonance output report has the 评分明细 table with the
required column set, a 校准门判定 section with a 判定 verdict, and evidence
that carries file+line references.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.review_resonance import g4_review_resonance


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_review_resonance(fps, rd))


# Valid report: full table + calibration verdict + file/line evidence.
VALID = """# 共鸣评分报告

## 评分明细

| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |
|------|------|------|--------|------|----------|
| 情感落地 | 22 | 30 | high | `chapters/chapter-1.md` L45 | show-don't-tell |

## 校准门判定

判定: 通过
"""


@pytest.mark.unit
def test_valid_report_passes(tmp_path: Path) -> None:
    f = tmp_path / "audits" / "chapter-1-resonance.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(VALID, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_missing_confidence_column_fails(tmp_path: Path) -> None:
    f = tmp_path / "audits" / "chapter-1-resonance.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(
        "# 共鸣评分报告\n\n## 评分明细\n\n| 维度 | 得分 |\n|------|------|\n| x | 10 |\n",
        encoding="utf-8",
    )
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.rr.detail_table" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_missing_full_score_column_fails(tmp_path: Path) -> None:
    f = tmp_path / "audits" / "chapter-1-resonance.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(
        "# 共鸣评分报告\n\n## 评分明细\n\n| 维度 | 得分 | 置信度 |\n| x | 10 | high |\n",
        encoding="utf-8",
    )
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.rr.detail_table" in mf for mf in result["must_fix"])


@pytest.mark.unit
@pytest.mark.parametrize("verdict", ["通过", "阻断", "待人机复核"])
def test_accepts_each_valid_verdict(tmp_path: Path, verdict: str) -> None:
    body = VALID.replace("判定: 通过", f"判定: {verdict}")
    f = tmp_path / "audits" / "chapter-1-resonance.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "PASS"
    assert any(c["id"] == "G4.rr.verdict" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_missing_calibration_section_fails(tmp_path: Path) -> None:
    f = tmp_path / "audits" / "chapter-1-resonance.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(
        "# 共鸣评分报告\n\n## 评分明细\n\n"
        "| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |\n"
        "|------|------|------|--------|------|----------|\n"
        "| 情感落地 | 22 | 30 | high | `c.md` L45 | show |\n",
        encoding="utf-8",
    )
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.rr.verdict" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_invalid_verdict_value_fails(tmp_path: Path) -> None:
    body = VALID.replace("判定: 通过", "判定: 优秀")
    f = tmp_path / "audits" / "chapter-1-resonance.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.rr.verdict" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_missing_file_line_evidence_fails(tmp_path: Path) -> None:
    # Table is structurally complete but the 证据 cell has no L<digits> ref.
    body = VALID.replace("`chapters/chapter-1.md` L45", "叙事平淡")
    f = tmp_path / "audits" / "chapter-1-resonance.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.rr.evidence" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_empty_file_list_skips() -> None:
    result = _run([])
    assert result["status"] == "PASS"
    assert any(c.get("s") == "SKIP" for c in result["checks"])


@pytest.mark.unit
def test_nonexistent_file_fails(tmp_path: Path) -> None:
    result = _run([str(tmp_path / "nope.md")])
    assert result["status"] == "FAIL"
    assert any("G4.rr.not_found" in mf for mf in result["must_fix"])
