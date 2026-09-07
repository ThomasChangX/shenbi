# spec #48 C34 (F456): gate_G2 G2.1 resolves relative paths via
# resolve_input_path(fp, rd) instead of bare CWD-relative Path(fp).

import json

from shenbi.gates.g2 import gate_G2


def test_g2_1_resolves_relative_against_rd(tmp_path, monkeypatch):
    rd = tmp_path / "rd"
    other = tmp_path / "other"
    rd.mkdir()
    other.mkdir()
    (rd / "ch3.md").write_text("# 第3章\n\n正文。\n", encoding="utf-8")
    monkeypatch.chdir(other)  # CWD != rd
    result = json.loads(gate_G2(["ch3.md"], "chapter", str(rd)))
    g21 = [c for c in result["checks"] if c["id"] == "G2.1"]
    assert g21 and g21[0]["s"] != "FAIL"  # found via rd, not CWD


def test_g2_1_relative_no_rd_structured_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = json.loads(gate_G2(["nope.md"], "chapter", None))
    # fail() collapses per-check detail into must_fix; the structured reason
    # lives in the G2.1 entry of the non-collapsing path — assert both forms.
    assert any("G2.1" in str(x) for x in result.get("must_fix", [])) or any(
        c.get("id") == "G2.1" and "round_dir" in str(c.get("r", ""))
        for c in result.get("checks", [])
    )
