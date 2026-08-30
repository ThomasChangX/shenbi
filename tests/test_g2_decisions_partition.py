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


def test_snapshot_backup_md_still_skipped(tmp_path):
    """audit-T1 I1: revision backup copies are not artifacts — no chapter checks."""
    snap = tmp_path / "state_snapshot-pre-rev.md"
    snap.write_text("# snapshot\nshort", encoding="utf-8")
    rev = tmp_path / "chapter-3-revision.md"
    rev.write_text("# 第三章\n" + "正文" * 2500, encoding="utf-8")
    r = _res([snap, rev])
    assert not any(
        c.get("file") == str(snap) and c.get("id") in ("G2.6", "G2.5") for c in r.get("checks", [])
    ) and not any(str(snap) in m for m in r.get("must_fix", [])), r


def test_nonsidecar_json_not_schema_validated_as_decisions(tmp_path):
    """PR #120 review: genre-config.json in a decisions-type output set must
    not be DecisionsDoc-validated — generic G2.4 syntax check only.
    """
    import shutil

    cfg = tmp_path / "genre-config.json"
    src = Path("tests/fixtures/genre-config-example.json")
    shutil.copy(src, cfg)
    dec = tmp_path / "genre-config-decisions.json"
    dec.write_text(
        (FIX / "valid-chapter-decisions.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    r = _res([cfg, dec])
    dec_checks = [c for c in r["checks"] if c.get("id") == "G4.dec" or c.get("id") == "G2.dec"]
    assert any(c.get("file") == str(dec) for c in dec_checks), r
    assert not any("DecisionsDoc" in m or "G2.dec.2" in m for m in r.get("must_fix", [])), r
    # valid config JSON passes the syntax check
    assert any(
        c.get("id") == "G2.4" and c.get("file") == str(cfg) and c.get("s") == "PASS"
        for c in r["checks"]
    ), r
