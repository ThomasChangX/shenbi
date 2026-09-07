"""Tests for tools/check_bug_hunt_evidence.py (spec #54 C16, F751)."""

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[3]
TOOL = PROJECT / "tools" / "check_bug_hunt_evidence.py"

_spec = importlib.util.spec_from_file_location("check_bug_hunt_evidence", TOOL)
assert _spec is not None and _spec.loader is not None
check_bug_hunt_evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_bug_hunt_evidence)
parse_evidence_lines = check_bug_hunt_evidence.parse_evidence_lines
verify_scenario = check_bug_hunt_evidence.verify_scenario


def _make_bh(tmp_path: Path, scenario: str, expected: str) -> Path:
    bh = tmp_path / "shenbi-x" / "bug-hunt"
    (bh / "input").mkdir(parents=True)
    (bh / "expected").mkdir(parents=True)
    (bh / "input" / "scenario.md").write_text(scenario, encoding="utf-8")
    (bh / "expected" / "expected-output.md").write_text(expected, encoding="utf-8")
    return bh


def test_parse_evidence_lines() -> None:
    lines = parse_evidence_lines(
        "defect at `tests/fixtures/a.md` L3 and 「锚文本样本」 also `tests/fixtures/b.md`"
    )
    assert lines[0][0] == "tests/fixtures/a.md"
    assert lines[0][1] == "3"
    assert lines[0][2] == "锚文本样本"
    assert lines[1] == ("tests/fixtures/b.md", "3", "锚文本样本")  # same-line pointers apply
    # ASCII straight quotes ARE anchors (F751 fabrications quoted chapter text
    # in straight quotes); tiny spans (<4 non-space chars) are ignored
    assert (
        parse_evidence_lines('defect: `tests/fixtures/b.md` "quoted phrase" here')[0][2]
        == "quoted phrase"
    )
    assert parse_evidence_lines('defect: `tests/fixtures/b.md` "a b" here')[0][2] is None


def test_verify_scenario_hit_and_miss(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "a.md").write_text("l1\nl2\nl3\n", encoding="utf-8")
    (fixtures / "b.md").write_text("内容甲\n", encoding="utf-8")
    bh = _make_bh(
        tmp_path,
        scenario="uses `tests/fixtures/missing.md`",
        expected=(
            "ok: `tests/fixtures/a.md` L1 「内容」free\n"
            "bad-line: `tests/fixtures/a.md` L99\n"
            "bad-anchor: `tests/fixtures/b.md` 「不存在的锚」\n"
        ),
    )
    violations = verify_scenario(bh, fixtures)
    assert len(violations) == 3
    assert any("missing fixture" in v for v in violations)
    assert any("L99 out of range" in v for v in violations)
    assert any("anchor" in v for v in violations)


def test_verify_scenario_clean(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "a.md").write_text("l1\n锚文本样本\n", encoding="utf-8")
    bh = _make_bh(
        tmp_path,
        scenario="reads `tests/fixtures/a.md`",
        expected="defect proven by `tests/fixtures/a.md` L2 「锚文本样本」",
    )
    assert verify_scenario(bh, fixtures) == []


def test_no_fixture_ref_lines_ignored(tmp_path: Path) -> None:
    bh = _make_bh(tmp_path, scenario="no refs", expected="plain prose, no fixtures")
    assert verify_scenario(bh, tmp_path / "fixtures") == []


def test_populated_dir_reference_ok(tmp_path: Path) -> None:
    """Existing non-empty dir ref is a legitimate scope pointer (F789 positive case)."""
    fixtures = tmp_path / "fixtures"
    (fixtures / "audits").mkdir(parents=True)
    (fixtures / "audits" / "a.md").write_text("x\n", encoding="utf-8")
    bh = _make_bh(tmp_path, scenario="audits under `tests/fixtures/audits/`", expected="ok")
    assert verify_scenario(bh, fixtures) == []


@pytest.mark.parametrize("args,expected", [([], 0), (["--warn-only"], 0)])
def test_cli_exit_codes(args: list[str], expected: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_bug_hunt_evidence, "T1", PROJECT / "tests" / "tiers" / "t1-skill")
    monkeypatch.setattr(sys, "argv", ["prog", *args])
    # real library holds 0 evidence violations (F789 fixed, spec #54 C16 T3) → rc 0
    rc = check_bug_hunt_evidence.main()
    assert rc == expected
