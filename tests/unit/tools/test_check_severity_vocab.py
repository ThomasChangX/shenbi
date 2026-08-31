"""spec #34 T903/AC2: check_severity_vocab recompute script tests.

Fixture-driven (G0.9): real chapter-revision outputs from
novel-output/xinghuo-ranqiong (canonical + legacy-severity copies).
"""

from __future__ import annotations

from pathlib import Path

from tools.check_severity_vocab import LEGACY_SEVERITY, LEGAL, collect_severities, main

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "revision-decisions"


def test_canonical_fixture_all_in_vocab() -> None:
    values = collect_severities(FIXTURES / "chapter-sample-revision-decisions.json")
    assert values and all(v in LEGAL for v in values)


def test_legacy_fixture_normalized_in_vocab() -> None:
    # Real production file carrying critical/minor/warning (legacy values)
    values = collect_severities(FIXTURES / "chapter-legacy-severity-revision-decisions.json")
    assert values
    assert all(v in LEGAL or LEGACY_SEVERITY.get(v.lower(), v) in LEGAL for v in values), values


def test_main_exit_zero_on_fixtures(capsys: object) -> None:
    assert main([str(FIXTURES)]) == 0


def test_legacy_map_in_sync_with_gate() -> None:
    """The tolerance map is duplicated in the G4 checker — keep them equal."""
    from shenbi.gates.g4.chapter_revision import _LEGACY_SEVERITY

    assert LEGACY_SEVERITY == _LEGACY_SEVERITY


def test_out_of_vocab_detected(tmp_path: Path) -> None:
    bad = tmp_path / "chapter-1-revision-decisions.json"
    bad.write_text('{"severity": "catastrophic"}', encoding="utf-8")
    values = collect_severities(tmp_path)
    assert values == ["catastrophic"]
    assert main([str(tmp_path)]) == 1
