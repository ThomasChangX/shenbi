"""Unit tests for tools/lint_audit_run.py (spec #49 R1 — C35 audit-process hygiene).

Row-format checks + exemption mechanism. Test inputs are tmp_path-assembled
mini ledgers plus references to real frozen audit-run artifacts (G0.9: real
products, not hand-crafted fixtures).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

import tools.lint_audit_run as lar  # noqa: E402

GOOD_ROW = "| F1 | 标题甲 | error | P1 | e | r | v | i | s | d | open |"


def _write_ledger(run_dir: Path, rows: list[str]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    header = (
        "# Findings Ledger\n\n"
        "| ID | 标题 | 类别 | 严重度 | 证据 | 根因 | 验证 | 影响 | 建议方向 | 深度 | 状态 |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    (run_dir / "findings-ledger.md").write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def test_good_row_passes(tmp_path: Path) -> None:
    _write_ledger(tmp_path, [GOOD_ROW])
    assert lar.lint_run(tmp_path) == []


def test_row_columns_too_few(tmp_path: Path) -> None:
    _write_ledger(tmp_path, ["| F1 | x | error | P1 | e | r | v | i | s | d |"])
    assert any(f.check == "row_columns" for f in lar.lint_run(tmp_path))


def test_row_columns_accepts_closure_annotation_columns(tmp_path: Path) -> None:
    annotated = (
        "| F2 | 标题乙 | error | P1 | e | r | v | i | s | d | open "
        "| → closed (C-34 spec #48) (merged-into-F433, spec #48, PR #168) |"
    )
    _write_ledger(tmp_path, [GOOD_ROW, annotated])
    assert not any(f.check == "row_columns" and f.id == "F2" for f in lar.lint_run(tmp_path))


def test_row_columns_rejects_unrecognized_extra_column(tmp_path: Path) -> None:
    _write_ledger(tmp_path, ["| F3 | t | error | P1 | e | r | v | i | s | d | open | 备注正文 |"])
    assert any(f.check == "row_columns" and f.id == "F3" for f in lar.lint_run(tmp_path))


def test_pipe_escape_detects_column_shift(tmp_path: Path) -> None:
    # unescaped pipe inside 标题 shifts severity cell out of vocab
    row = "| F4 | 标|题 | error | P1 | e | r | v | i | s | d | open |"
    _write_ledger(tmp_path, [row])
    assert any(f.check == "pipe_escape" for f in lar.lint_run(tmp_path))


def test_id_unique(tmp_path: Path) -> None:
    _write_ledger(tmp_path, [GOOD_ROW, GOOD_ROW.replace("标题甲", "另一标题")])
    assert any(f.check == "id_unique" for f in lar.lint_run(tmp_path))


def test_dup_row(tmp_path: Path) -> None:
    _write_ledger(tmp_path, [GOOD_ROW, GOOD_ROW])
    assert any(f.check == "dup_row" for f in lar.lint_run(tmp_path))


def test_title_placeholder(tmp_path: Path) -> None:
    _write_ledger(tmp_path, ["| F5 | F5 | error | P1 | e | r | v | i | s | d | open |"])
    assert any(f.check == "title_placeholder" and f.id == "F5" for f in lar.lint_run(tmp_path))


def _write_exemptions(run_dir: Path, entries: list[dict[str, str]]) -> None:
    (run_dir / "audit-lint-exemptions.json").write_text(
        json.dumps({"exemptions": entries}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def test_exemption_mutes_finding(tmp_path: Path) -> None:
    _write_ledger(tmp_path, ["| F6 | t | error | P1 | e | r | v | i | s | d | open | 备注 |"])
    _write_exemptions(
        tmp_path,
        [{"check": "row_columns", "id": "F6", "reason": "frozen", "date": "2026-09-07"}],
    )
    raw = lar.lint_run(tmp_path)
    exemptions = lar.load_exemptions(tmp_path)
    assert lar.apply_exemptions(raw, exemptions) == []


def test_run_level_exemption(tmp_path: Path) -> None:
    _write_ledger(tmp_path, ["| F7 | t | error | P1 | e | r | v | i | s | d | open | 备注 |"])
    _write_exemptions(
        tmp_path,
        [
            {
                "check": "row_columns",
                "id": "run:row_columns",
                "reason": "frozen run",
                "date": "2026-09-07",
            }
        ],
    )
    assert lar.apply_exemptions(lar.lint_run(tmp_path), lar.load_exemptions(tmp_path)) == []


def test_stale_exemption_fails(tmp_path: Path) -> None:
    _write_ledger(tmp_path, [GOOD_ROW])
    _write_exemptions(
        tmp_path,
        [{"check": "row_columns", "id": "F999", "reason": "no hit", "date": "2026-09-07"}],
    )
    problems = lar.validate_exemptions(tmp_path, lar.lint_run(tmp_path))
    assert any(p.check == "stale_exemption" for p in problems)


def test_exemption_schema_violation_fails(tmp_path: Path) -> None:
    _write_ledger(tmp_path, [GOOD_ROW])
    _write_exemptions(tmp_path, [{"check": "row_columns", "id": "F1"}])  # missing reason/date
    problems = lar.validate_exemptions(tmp_path, lar.lint_run(tmp_path))
    assert problems  # schema violation must FAIL


def test_severity_parenthetical_suffix_normalized(tmp_path: Path) -> None:
    row = "| F8 | t | error | M（置信度 medium） | e | r | v | i | s | d | open |"
    _write_ledger(tmp_path, [row])
    assert not any(f.check == "pipe_escape" for f in lar.lint_run(tmp_path))


def test_real_0814_run_lint_has_raw_hits() -> None:
    raw = lar.lint_run(Path("docs/superpowers/audit-runs/2026-08-14"))
    assert raw  # frozen 08-14 run: malformed-row group (F972 family) must hit pre-exemption


@pytest.mark.skipif(
    not (Path("docs/superpowers/audit-runs/2026-08-15") / "audit-lint-exemptions.json").exists(),
    reason="Task 3 exemptions not landed yet",
)
def test_real_0815_run_after_exemptions() -> None:
    raw = lar.lint_run(Path("docs/superpowers/audit-runs/2026-08-15"))
    exemptions = lar.load_exemptions(Path("docs/superpowers/audit-runs/2026-08-15"))
    assert lar.apply_exemptions(raw, exemptions) == []


def test_corrupt_exemption_file_fails_not_crashes(tmp_path: Path) -> None:
    _write_ledger(tmp_path, [GOOD_ROW])
    (tmp_path / "audit-lint-exemptions.json").write_text("{not json", encoding="utf-8")
    findings = lar.lint_run_full(tmp_path)
    assert any(f.check == "exemption_schema" for f in findings)


def test_missing_run_dir_flagged(capsys: pytest.CaptureFixture[str]) -> None:
    assert lar.main([str(Path("docs/superpowers/audit-runs/nonexistent"))]) == 1
    assert "does not exist" in capsys.readouterr().out


# ---- Task 2: counts_reconcile + report_internal ----


def _write_mini_run(
    run_dir: Path,
    ledger_rows: list[str],
    report_body: str,
    zones: dict[str, str] | None = None,
) -> None:
    _write_ledger(run_dir, ledger_rows)
    (run_dir / "final-report.md").write_text(f"# Final Report\n{report_body}", encoding="utf-8")
    zones_dir = run_dir / "zones"
    zones_dir.mkdir(exist_ok=True)
    for name, content in (zones or {"Z1.files": "a.py\nb.py\n"}).items():
        (zones_dir / name).write_text(content, encoding="utf-8")


def test_counts_reconcile_prefix_mismatch(tmp_path: Path) -> None:
    rows = [GOOD_ROW, "| T1 | t | error | P1 | e | r | v | i | s | d | open |"]
    _write_mini_run(
        tmp_path,
        rows,
        "```\nF=1 T=2 D=0 G=0 total=3\nP0=0 P1=2 P2=0 M=0 (sum=2)\n```\n",
    )
    assert any(f.id == "prefix:T" for f in lar.reconcile(tmp_path))


def test_report_internal_total_vs_ledger(tmp_path: Path) -> None:
    _write_mini_run(tmp_path, [GOOD_ROW], "**总 findings: 5**\n")
    assert any(f.id == "total_claim" for f in lar.report_internal(tmp_path))


def test_report_internal_sum_line(tmp_path: Path) -> None:
    _write_mini_run(tmp_path, [GOOD_ROW], "```\nP0=1 P1=3 P2=0 M=0 (sum=5)\n```\n")
    assert any(f.id == "sum_claim" for f in lar.report_internal(tmp_path))


def test_report_internal_severity_vs_ledger(tmp_path: Path) -> None:
    _write_mini_run(tmp_path, [GOOD_ROW], "```\nP0=0 P1=2 P2=0 M=0 (sum=2)\n```\n")
    assert any(f.id == "severity:P1" for f in lar.report_internal(tmp_path))


def test_reconcile_zones_union_vs_table_a(tmp_path: Path) -> None:
    _write_mini_run(
        tmp_path,
        [GOOD_ROW],
        "| tracked 文件（表 A） | 1 |",
        zones={"Z1.files": "a.py\nb.py\n", "Z2.files": "b.py\nc.py\n"},  # union=3
    )
    assert any(f.id == "zones_union" for f in lar.reconcile(tmp_path))


def test_reconcile_clean_mini_run(tmp_path: Path) -> None:

    rows = [GOOD_ROW, "| T1 | t | error | P1 | e | r | v | i | s | d | open |"]
    _write_mini_run(
        tmp_path,
        rows,
        "```\nF=1 T=1 D=0 G=0 total=2\nP0=0 P1=2 P2=0 M=0 (sum=2)\n```\n**总 findings: 2**\n",
        zones={"Z1.files": "a.py\nb.py\n"},
    )
    (tmp_path / "final-report.md").write_text(
        (tmp_path / "final-report.md").read_text(encoding="utf-8")
        + "\n| tracked 文件（表 A） | 2 |\n",
        encoding="utf-8",
    )
    assert lar.reconcile(tmp_path) == []
    assert lar.report_internal(tmp_path) == []


def test_real_0814_reconcile_hits_f969_f973() -> None:

    run = Path("docs/superpowers/audit-runs/2026-08-14")
    assert any(f.id == "zones_union" for f in lar.reconcile(run))  # F973: 2755 vs 2738
    assert any(f.id == "total_claim" for f in lar.report_internal(run))  # F969: 781 vs 786


def test_missing_report_is_explicit_fail(tmp_path: Path) -> None:
    _write_ledger(tmp_path, [GOOD_ROW])  # no final-report.md
    hits = lar.reconcile(tmp_path)
    assert any(f.id == "report_missing" for f in hits)


def test_missing_zones_dir_is_explicit_fail(tmp_path: Path) -> None:
    _write_ledger(tmp_path, [GOOD_ROW])
    (tmp_path / "final-report.md").write_text("| tracked 文件（表 A） | 2 |\n", encoding="utf-8")
    assert any(f.id == "zones_missing" for f in lar.reconcile(tmp_path))


# ---- Task 3: verify_carryover ----


def test_verify_carryover_flags_uncarried(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mod = lar
    # fake audit-runs root containing prev + next runs
    prev, nxt = tmp_path / "2026-01-01", tmp_path / "2026-01-02"
    _write_ledger(prev, [GOOD_ROW])
    (prev / "carryover.md").write_text(
        "# 承接清单\n\nF1 P1 open 标题甲\nF2 P1 verified 标题乙\n", encoding="utf-8"
    )
    _write_ledger(nxt, ["| F2 | t | error | P1 | e | r | v | i | s | d | open |"])
    monkeypatch.setattr(mod, "AUDIT_RUNS_DIR", tmp_path)
    hits = mod.verify_carryover(prev)
    assert [f.id for f in hits] == ["F1"]  # F2 carried, F1 broken


def test_verify_carryover_skips_without_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mod = lar
    run = tmp_path / "2026-01-01"
    run.mkdir()
    monkeypatch.setattr(mod, "AUDIT_RUNS_DIR", tmp_path)
    assert mod.verify_carryover(run) == []
