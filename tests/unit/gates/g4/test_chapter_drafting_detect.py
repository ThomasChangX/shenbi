# spec #48 C34 (F407): chapter_drafting project_root via genre-config
# ancestor walk (was: skill-output-only upward climb).

import json
import shutil
from pathlib import Path

from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


def test_fatigue_words_use_project_genre_config(tmp_path, monkeypatch):
    # project-output layout: genre-config at real project root, chapter md in
    # round dir. Custom fatigue word "咣当" appears >8 times — only detected
    # when project_root resolves to the genre-config ancestor (RED today:
    # skill-output climb falls back to default list without the custom word).
    pd = tmp_path / "pd"
    rd = tmp_path / "rd"
    pd.mkdir()
    rd.mkdir()
    shutil.copy(FIXTURES / "genre-config-example.json", pd / "genre-config.json")
    gc = json.loads((pd / "genre-config.json").read_text(encoding="utf-8"))
    gc["fatigue_words"] = ["咣当"]
    (pd / "genre-config.json").write_text(json.dumps(gc), encoding="utf-8")
    body = "第3章\n\n" + "咣当" * 9
    chapter = rd / "chapter-3-x.md"
    chapter.write_text(body, encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # CWD independent
    result = json.loads(g4_chapter_drafting([str(chapter)], str(rd), str(pd), str(tmp_path)))
    must_fix = " ".join(str(x) for x in result.get("must_fix", []))
    assert (
        "G4.fatigue" in must_fix and ">8" in must_fix
    )  # custom word only detectable via resolved project_root
