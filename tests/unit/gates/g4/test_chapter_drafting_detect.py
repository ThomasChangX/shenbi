# spec #48 C34 (F407): chapter_drafting project_root via genre-config
# ancestor walk (was: skill-output-only upward climb).

import json
import shutil
from pathlib import Path

from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


def test_fatigue_words_use_project_genre_config(tmp_path, monkeypatch):
    # spec #93 T6 — the gate reads the contract's real shape (camelCase
    # fatigueWords nested object). 眸光一凝 is in the fixture's 禁用 list and
    # has ZERO substring collision with FATIGUE_BASE (colliding words already
    # FAIL today via base counting — word-choice constraint in the spec).
    # Real skill outputs never write a top-level snake `fatigue_words` key
    # (the shape the old test hand-injected).
    pd = tmp_path / "pd"
    rd = tmp_path / "rd"
    pd.mkdir()
    rd.mkdir()
    shutil.copy(FIXTURES / "genre-config-example.json", pd / "genre-config.json")
    body = "第3章\n\n" + "眸光一凝" * 9
    chapter = rd / "chapter-3-x.md"
    chapter.write_text(body, encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # CWD independent
    result = json.loads(g4_chapter_drafting([str(chapter)], str(rd), str(pd), str(tmp_path)))
    must_fix = " ".join(str(x) for x in result.get("must_fix", []))
    assert (
        "G4.fatigue" in must_fix and ">8" in must_fix
    )  # configured word only detectable via the contract shape


def test_fatigue_malformed_config_falls_back_to_base(tmp_path, monkeypatch):
    # Malformed shape (禁用 not a list) -> fall back to FATIGUE_BASE without
    # crashing the gate (defensive surface).
    pd = tmp_path / "pd"
    rd = tmp_path / "rd"
    pd.mkdir()
    rd.mkdir()
    (pd / "genre-config.json").write_text(
        json.dumps({"fatigueWords": {"禁用": "not-a-list", "慎用": []}}), encoding="utf-8"
    )
    body = "第3章\n\n" + "突然" * 9  # 突然 ∈ FATIGUE_BASE
    chapter = rd / "chapter-3-x.md"
    chapter.write_text(body, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = json.loads(g4_chapter_drafting([str(chapter)], str(rd), str(pd), str(tmp_path)))
    must_fix = " ".join(str(x) for x in result.get("must_fix", []))
    assert "G4.fatigue" in must_fix and ">8" in must_fix
