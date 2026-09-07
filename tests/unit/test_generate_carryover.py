"""Unit tests for tools/generate_carryover.py (spec #49 R2 — C35)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from tools.generate_carryover import generate_carryover  # noqa: E402

HEADER = (
    "# Findings Ledger\n\n"
    "| ID | 标题 | 类别 | 严重度 | 证据 | 根因 | 验证 | 影响 | 建议方向 | 深度 | 状态 |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|\n"
)


def _ledger(tmp_path: Path, rows: list[str]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    ledger = tmp_path / "findings-ledger.md"
    ledger.write_text(HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return ledger


def test_carries_verified_and_open_all_severities(tmp_path: Path) -> None:
    ledger = _ledger(
        tmp_path,
        [
            "| F1301 | 甲 | error | P1 | e | r | v | i | s | d | verified |",
            "| F1302 | 乙 | error | P1 | e | r | v | i | s | d | open |",
            "| F1320 | 丙 | 文案 | M | e | r | v | i | s | d | verified |",
            "| F1315 | 丁 | error | P2 | e | r | v | i | s | d | verified |",
        ],
    )
    out = tmp_path / "carryover.md"
    count = generate_carryover(ledger, out)
    text = out.read_text(encoding="utf-8")
    assert count == 4
    assert "F1301 P1 verified" in text
    assert "F1320 M verified" in text
    assert "F1315 P2 verified" in text  # full-severity: P2 must be carried


def test_skips_closed_and_merged(tmp_path: Path) -> None:
    ledger = _ledger(
        tmp_path,
        [
            "| F1 | a | error | P1 | e | r | v | i | s | d | closed |",
            "| F2 | b | error | P1 | e | r | v | i | s | d | verified "
            + "| → closed (C-34 spec #48) (merged-into-F433, spec #48, PR #168) |",
            "| F3 | c | error | P1 | e | r | v | i | s | d | open |",
        ],
    )
    out = tmp_path / "carryover.md"
    count = generate_carryover(ledger, out)
    assert count == 1
    assert "F3 " in out.read_text(encoding="utf-8")


def test_real_0814_carryover_contains_f1177_break_links() -> None:
    run = Path("docs/superpowers/audit-runs/2026-08-14")
    out = run / "carryover.md"
    if not out.exists():  # pre-generation fact pin
        pytest.skip("carryover not generated yet")
    text = out.read_text(encoding="utf-8")
    for fid in ("F1301", "F1302", "F1320"):
        assert any(line.startswith(f"{fid} ") for line in text.splitlines()), fid
