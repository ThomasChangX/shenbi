"""T104 (spec #30 T3/T6): G4.dec read side must adopt the same raw_decode
recovery policy as G2, so the same file cannot pass one gate and fail the
other. Recovery produces diagnostics, never a silent pass.
"""

import json
from pathlib import Path

from shenbi.gates.g2 import gate_G2
from shenbi.gates.g4.decisions_validator import g4_decisions

FIX = Path(__file__).parent / "fixtures" / "decisions"


def _g2_verdict(fp: Path) -> tuple[str, list[str]]:
    r = json.loads(gate_G2([str(fp)], "decisions"))
    return r["status"], [m.split(":", 1)[0] for m in r.get("must_fix", [])]


def _g4_verdict(fp: Path) -> tuple[str, list[str]]:
    r = json.loads(g4_decisions([str(fp)]))
    return r["status"], [m.split(":", 1)[0] for m in r.get("must_fix", [])]


def test_valid_sample_g2_g4_agree():
    assert _g2_verdict(FIX / "valid-chapter-decisions.json")[0] == "PASS"
    assert _g4_verdict(FIX / "valid-chapter-decisions.json")[0] == "PASS"


def test_trailing_sample_g2_g4_agree(tmp_path: Path):
    """Truncated/concatenated JSON: both gates recover the first object and
    render the same verdict (no G4 invalid_json vs G2 recovery divergence).
    """
    src = (FIX / "trailing-sample.json").read_text(encoding="utf-8")
    # keep only the recovered payload shape meaningful for both gates
    fp = tmp_path / "chapter-9-decisions.json"
    fp.write_text(src, encoding="utf-8")
    g2s, g2m = _g2_verdict(fp)
    g4s, g4m = _g4_verdict(fp)
    assert g2s == g4s, (g2s, g4s, g2m, g4m)


def test_unrecoverable_json_both_fail(tmp_path: Path):
    fp = tmp_path / "chapter-9-decisions.json"
    fp.write_text("{not json at all", encoding="utf-8")
    assert _g2_verdict(fp)[0] == "FAIL"
    assert _g4_verdict(fp)[0] == "FAIL"


def test_recovered_object_still_schema_validated(tmp_path: Path):
    """Recovery must not bypass DecisionsDoc — a recovered-but-invalid object fails."""
    fp = tmp_path / "chapter-9-decisions.json"
    fp.write_text('{"no": "schema"} trailing garbage', encoding="utf-8")
    assert _g4_verdict(fp)[0] == "FAIL"
    assert _g2_verdict(fp)[0] == "FAIL"


def test_valid_plus_trailing_g2_passes_g4_must_match(tmp_path: Path):
    """Discriminating case: G2 recovers a VALID first object (PASS); G4 must
    agree instead of failing invalid_json (T104's 15-case divergence class).
    """
    raw = (FIX / "valid-chapter-decisions.json").read_text(encoding="utf-8")
    fp = tmp_path / "chapter-9-decisions.json"
    fp.write_text(raw + "\n<<< stale second output block >>>", encoding="utf-8")
    assert _g2_verdict(fp)[0] == "PASS"
    assert _g4_verdict(fp)[0] == "PASS", _g4_verdict(fp)
