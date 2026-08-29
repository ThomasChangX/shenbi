"""z11 R1b: G2.13 chapter-contract check + exemption list (SDD #20, F1301/F1302)."""

import json
from pathlib import Path

from shenbi.gates.g2 import gate_G2
from shenbi.gates.shared import load_chapter_exemptions

FIX = Path("tests/fixtures/z11")


def test_exemptions_load() -> None:
    ex = load_chapter_exemptions()
    assert 40 in ex.get("xinghuo-ranqiong", set())


def test_g2_chapter_contract_meta_exemption_passes(tmp_path: Path) -> None:
    proj = tmp_path / "novel-output" / "xinghuo-ranqiong" / "chapters"
    proj.mkdir(parents=True)
    f = proj / "chapter-40.md"
    f.write_text(
        "# Chapter 40:\n\n" + FIX.joinpath("chapter-40-no-meta.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    result = json.loads(gate_G2(str(f), "chapter"))
    assert any(c["id"] == "G2.13" and c["s"] == "PASS" for c in result["checks"])


def test_g2_chapter_contract_fails_on_no_header_no_meta(tmp_path: Path) -> None:
    proj = tmp_path / "novel-output" / "other" / "chapters"
    proj.mkdir(parents=True)
    f = proj / "chapter-99.md"
    f.write_text("无头无 META 正文。", encoding="utf-8")
    result = json.loads(gate_G2(str(f), "chapter"))
    assert result["status"] == "FAIL"
    assert any("G2.13" in x for x in result.get("must_fix", []))


def test_g2_chapter_contract_passes_compliant(tmp_path: Path) -> None:
    f = tmp_path / "novel-output" / "xinghuo-ranqiong" / "chapter-41.md"
    f.parent.mkdir(parents=True)
    body = FIX.joinpath("chapter-41-with-meta.md").read_text(encoding="utf-8")
    f.write_text("# Chapter 41:\n\n" + body, encoding="utf-8")
    result = json.loads(gate_G2(str(f), "chapter"))
    assert any(c["id"] == "G2.13" and c["s"] == "PASS" for c in result["checks"])


def test_g2_chapter_contract_skips_non_novel_rounds(tmp_path: Path) -> None:
    """test-tier round chapters (PRE/POST shape) are out of the novel contract scope."""
    rd = tmp_path / "round" / "chapters"
    rd.mkdir(parents=True)
    f = rd / "ch001.md"
    f.write_text("# Chapter\n\n" + "字" * 3500, encoding="utf-8")
    result = json.loads(gate_G2(str(f), "chapter"))
    g213 = next(c for c in result["checks"] if c["id"] == "G2.13")
    assert g213["s"] == "SKIP"
