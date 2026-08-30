"""T101 (spec #30 T1): the .md main artifact of a decisions-dual-product skill
must not bypass G2 chapter checks. Under file_type="decisions" the gate
partitions per file suffix: .json sidecars take the G2.dec branch, .md files
fall through with chapter semantics (previously they hit a bare continue).
"""

import json
from pathlib import Path

from shenbi.gates.g2 import gate_G2

FIX = Path(__file__).parent / "fixtures" / "decisions"


def _res(files, ftype="decisions"):
    return json.loads(gate_G2([str(f) for f in files], ftype))


def _entries(r):
    # must_fix entries are "ID:file" strings (shared.py fail() structure)
    return r.get("checks", []) + [
        {"id": m.split(":", 1)[0], "s": "FAIL"} for m in r.get("must_fix", [])
    ]


def test_md_gets_chapter_checks_under_decisions_type():
    r = _res([FIX / "chapter-too-short.md"])
    assert any(c.get("id") == "G2.6" and c.get("s") == "FAIL" for c in _entries(r)), r


def test_json_still_gets_decisions_branch():
    r = _res([FIX / "valid-chapter-decisions.json"])
    assert any(c.get("id") == "G2.dec" and c.get("s") == "PASS" for c in _entries(r)), r


def test_dual_product_round_violating_chapter_fails():
    """Acceptance 2 (first half): a violating chapter in a dual-product round fails G2."""
    r = _res([FIX / "chapter-too-short.md", FIX / "valid-chapter-decisions.json"])
    assert r.get("status") != "PASS", r


def test_valid_chapter_md_passes_under_decisions_type():
    r = _res([FIX / "chapter-full.md", FIX / "valid-chapter-decisions.json"])
    assert r.get("status") == "PASS", r
