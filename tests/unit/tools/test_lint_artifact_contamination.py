"""Tests for tools/lint_artifact_contamination.py (SDD #56 C18 T2).

Lint-logic unit tests on synthetic tmp_path trees (linter semantics, not
skill-output scenarios — G0.9 does not apply; same precedent as
tests/unit/tools/test_lint_status_strings.py). Real-tree smoke happens in
Task 3's baseline run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.lint_artifact_contamination import (
    META_NARRATION_PATTERNS,
    lint_tree,
    lint_tree_all,
    load_exemptions,
    main,
)


def _write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# --- check (a): meta_narration ---


def test_meta_narration_detects_all_seven_patterns(tmp_path: Path) -> None:
    for i, pat in enumerate(META_NARRATION_PATTERNS):
        _write(tmp_path, f"a{i}.md", f"line with {pat} inside\n")
    _write(tmp_path, "clean.md", "普通正文，无模式\n")
    findings = [f for f in lint_tree(tmp_path) if f["check"] == "meta_narration"]
    assert len(findings) == len(META_NARRATION_PATTERNS)
    assert all(f["path"] != "clean.md" for f in findings)


def test_meta_narration_scans_json_sidecars(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "chapter-1-decisions.json",
        json.dumps({"note": "只读沙箱，请手动复制"}, ensure_ascii=False),
    )
    findings = [f for f in lint_tree(tmp_path) if f["check"] == "meta_narration"]
    assert len(findings) == 1 and findings[0]["path"] == "chapter-1-decisions.json"


# --- check (b): manual_calc ---


def test_manual_calc_requires_pattern_and_number(tmp_path: Path) -> None:
    _write(tmp_path, "with-num.md", "分流为手动计算，overall 70 ≥ 65\n")
    _write(tmp_path, "same-file-split.md", "分流为手动计算。\n表格里有 70。\n")
    _write(tmp_path, "no-num.md", "分流为手动计算。\n")
    _write(tmp_path, "num-only.md", "overall 70\n")
    findings = [f for f in lint_tree(tmp_path) if f["check"] == "manual_calc"]
    assert sorted(str(f["path"]) for f in findings) == ["same-file-split.md", "with-num.md"]


# --- check (c): timestamp ---


def test_timestamp_same_file_non_monotonic(tmp_path: Path) -> None:
    _write(tmp_path, "chain.md", "t1: 2026-07-16T09:23:00Z\nt2: 2026-07-16T08:00:00Z\n")
    findings = [f for f in lint_tree(tmp_path) if f["check"] == "timestamp"]
    assert len(findings) == 1


def test_timestamp_cross_file_signature_full_string_only(tmp_path: Path) -> None:
    # Same full on-the-hour string across 2 files → signature hit.
    _write(tmp_path, "x.md", "produced_at: 2026-07-16T12:00:00Z\n")
    _write(tmp_path, "y.json", '{"produced_at": "2026-07-16T12:00:00Z"}')
    # Same hour, different date → not a signature.
    _write(tmp_path, "z.md", "produced_at: 2026-07-17T12:00:00Z\n")
    findings = [f for f in lint_tree(tmp_path) if f["check"] == "timestamp"]
    assert {f["path"] for f in findings} == {"x.md", "y.json"}


def test_timestamp_cross_file_plain_backwards_not_flagged(tmp_path: Path) -> None:
    # Cross-file disorder is legal (spec: only same-file monotonicity).
    _write(tmp_path, "a.md", "produced_at: 2026-07-16T12:00:01Z\n")
    _write(tmp_path, "b.md", "produced_at: 2026-07-16T09:00:00Z\n")
    findings = [f for f in lint_tree(tmp_path) if f["check"] == "timestamp"]
    assert findings == []


def test_timestamp_non_zero_minute_duplicate_not_signature(tmp_path: Path) -> None:
    # Duplicated full string but NOT on-the-hour → not a fabricated signature.
    _write(tmp_path, "a.md", "produced_at: 2026-07-16T12:00:05Z\n")
    _write(tmp_path, "b.md", "produced_at: 2026-07-16T12:00:05Z\n")
    findings = [f for f in lint_tree(tmp_path) if f["check"] == "timestamp"]
    assert findings == []


# --- check (d): state_reconcile ---


def _make_state_tree(tmp_path: Path) -> None:
    _write(tmp_path, "audits/chapter-1-resonance.md", "ok\n")  # accounted below
    _write(tmp_path, "audits/chapter-1-pov.md", "ok\n")  # NOT accounted → missing
    _write(tmp_path, "audits/chapter-2-pov.md", "ok\n")  # ch2 has empty container → missing
    state = {
        "chapter_loop": {
            "chapter_states": {
                "1": {"audit_results": {"audit_reports": ["audits/chapter-1-resonance.md"]}},
                "2": {"audit_results": {}},  # key-in-but-empty branch
                # ch56-style: chapter key absent entirely → missing branch
            }
        }
    }
    (tmp_path / "pipeline-state.json").write_text(json.dumps(state), encoding="utf-8")


def test_state_reconcile_both_branches(tmp_path: Path) -> None:
    _make_state_tree(tmp_path)
    findings = [f for f in lint_tree(tmp_path) if f["check"] == "state_reconcile"]
    paths = sorted(str(f["path"]) for f in findings)
    assert paths == ["audits/chapter-1-pov.md", "audits/chapter-2-pov.md"]


def test_state_reconcile_no_state_file_ok(tmp_path: Path) -> None:
    _write(tmp_path, "audits/chapter-1-pov.md", "ok\n")
    findings = [f for f in lint_tree(tmp_path) if f["check"] == "state_reconcile"]
    assert findings == []


# --- exemptions ---


def test_exemption_skips_check_for_file(tmp_path: Path) -> None:
    _write(tmp_path, "x.md", "produced_at: 2026-07-16T12:00:00Z\n")
    _write(tmp_path, "y.md", "produced_at: 2026-07-16T12:00:00Z\n")
    exemptions = {
        "timestamp": [
            {"path": "x.md", "reason": "F1163 adjudicated"},
            {"path": "y.md", "reason": "F1163 adjudicated"},
        ]
    }
    findings = lint_tree(tmp_path, exemptions=exemptions)
    assert findings == []


def test_load_exemptions(tmp_path: Path) -> None:
    cfg = tmp_path / "tools" / "artifact-lint-exemptions.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps({"meta_narration": [{"path": "a.md", "reason": "r"}]}), encoding="utf-8"
    )
    loaded = load_exemptions(tmp_path)
    assert loaded == {"meta_narration": [{"path": "a.md", "reason": "r"}]}


# --- CLI exit codes ---


def test_cli_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path, "bad.md", "只读沙箱\n")
    argv = ["--tree", str(tmp_path)]
    assert main(argv) == 1
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["total"] == 1


def test_cli_exit_zero_on_clean_tree(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path, "clean.md", "正常产物\n")
    assert main(["--tree", str(tmp_path)]) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["total"] == 0


def test_cli_missing_tree_errors(tmp_path: Path) -> None:
    assert main(["--tree", str(tmp_path / "nope")]) == 2


def test_malformed_exemption_entry_exits_2(tmp_path: Path) -> None:
    cfg = tmp_path / "tools" / "artifact-lint-exemptions.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"meta_narration": [{"path": "a.md"}]}), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        load_exemptions(tmp_path)
    assert exc.value.code == 2


def test_signature_counts_distinct_files(tmp_path: Path) -> None:
    # Same stamp twice in ONE file + once in another → not a 2-file group.
    _write(tmp_path, "a.md", "t1 2026-07-16T12:00:00Z t2 2026-07-16T12:00:00Z\n")
    _write(tmp_path, "b.md", "produced 2026-07-16T12:00:01Z\n")
    findings = [f for f in lint_tree(tmp_path) if f["check"] == "timestamp"]
    assert findings == []


def test_baseline_out_marks_exempt_entries(tmp_path: Path) -> None:
    _write(tmp_path, "x.md", "produced_at: 2026-07-16T12:00:00Z\n")
    _write(tmp_path, "y.md", "produced_at: 2026-07-16T12:00:00Z\n")
    exemptions = {
        "timestamp": [
            {"path": "x.md", "reason": "F1163 adjudicated"},
            {"path": "y.md", "reason": "F1163 adjudicated"},
        ]
    }
    all_findings = lint_tree_all(tmp_path, exemptions=exemptions)
    assert len(all_findings) == 2 and all(f["exempt"] for f in all_findings)
    assert lint_tree(tmp_path, exemptions=exemptions) == []
