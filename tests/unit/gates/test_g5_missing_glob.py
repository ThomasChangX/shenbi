"""F432: checker-having prereq missing glob => FAIL marker, not *.md sweep (spec #60 R5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates import g5
from shenbi.gates.g5 import gate_G5

pytestmark = pytest.mark.unit

MARKER = "missing G5_CHECKER_GLOBS entry"


def test_missing_glob_checker_having_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drafting prereq with a dedicated checker but no glob entry -> FAIL marker."""
    # shenbi-state-settling is a drafting prereq with a checker AND a glob that
    # Task 8 does NOT touch — deleting its entry simulates the F432 drift class
    # and keeps this test valid after the +9 backfill.
    monkeypatch.delitem(g5.G5_CHECKER_GLOBS, "shenbi-state-settling")

    proj = tmp_path / "proj"
    (proj / "chapters").mkdir(parents=True)
    (proj / "chapters" / "chapter-001.md").write_text("# 第一章\n\n正文。\n", encoding="utf-8")

    out = gate_G5(phase_name="drafting", round_dir=str(tmp_path), project_dir=str(proj))
    parsed = json.loads(out)
    assert parsed["status"] == "FAIL"
    assert "G5.5:shenbi-state-settling:missing G5_CHECKER_GLOBS entry" in parsed["must_fix"]


def test_checker_less_prereq_no_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A checker-less prereq hitting the explicit *.md default must NOT be flagged."""
    # Empty the glob table entirely: every prereq falls to defaults; only
    # checker-having ones may be flagged. A checker-less prereq (e.g.
    # shenbi-genre-config is NOT one — pick via runtime sets) must not appear.
    from shenbi.gates.g4.generic import G4_CHECKER_KEYS

    monkeypatch.setattr(g5, "G5_CHECKER_GLOBS", {})

    # audit phase: prereqs are the review-group-* family (checker-less) — they
    # must ride the explicit *.md default, never the FAIL marker (F432 R5).
    proj = tmp_path / "proj"
    (proj / "audits").mkdir(parents=True)
    (proj / "audits" / "chapter-001-anti-ai.md").write_text("# 审计\n\n结论。\n", encoding="utf-8")

    out = gate_G5(phase_name="audit", round_dir=str(tmp_path), project_dir=str(proj))
    parsed = json.loads(out)
    flagged = {x.split(":")[1] for x in parsed.get("must_fix", []) if MARKER in x}
    from shenbi.gates.shared import TESTS as _TESTS

    deps = json.loads((_TESTS / "tiers" / "deps.json").read_text(encoding="utf-8"))
    audit_prereqs = set(deps["t2-phases"]["audit"]["prerequisites"])
    checker_less = audit_prereqs - set(G4_CHECKER_KEYS)
    assert checker_less, "fixture drifted: audit must keep >=1 checker-less prereq"
    assert not (flagged & checker_less)
    assert flagged == audit_prereqs & set(G4_CHECKER_KEYS)
