# spec #48 C34 cluster-level acceptance: G4 file resolution matrix
# (3 layouts × relative/absolute × CWD inside/outside × project_dir rd/≠rd).
# Fixtures assembled from real tests/fixtures products (G0.9).

import json
import shutil
from pathlib import Path

import pytest

from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _chapter_fixture() -> Path:
    drafts = sorted(FIXTURES.glob("chapter-*-draft.md")) or sorted(FIXTURES.rglob("chapter-*.md"))
    assert drafts, "no real chapter fixture available"
    return drafts[0]


LAYOUTS = ["skill-output", "novel-output", "project-output"]


def _assemble(base: Path, layout: str) -> tuple[Path, Path]:
    """Build a layout-shaped project; return (rd, project_dir)."""
    if layout == "project-output":
        pd = base / "pd"
        rd = base / "rd"
        pd.mkdir(parents=True)
        rd.mkdir()
        (rd / "project-output").mkdir()
    else:
        rd = base / layout / "proj-x" / "round"
        rd.mkdir(parents=True)
        pd = rd
    shutil.copy(
        FIXTURES / "genre-config-example.json", _project_root(pd, layout) / "genre-config.json"
    )
    target_dir = rd / "project-output" if layout == "project-output" else rd
    shutil.copy(_chapter_fixture(), target_dir / "chapter-3-x.md")
    return rd, pd


def _project_root(pd: Path, layout: str) -> Path:
    return pd if layout == "project-output" else pd.parent


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("relative", [True, False], ids=["rel", "abs"])
@pytest.mark.parametrize("cwd_inside", [True, False], ids=["cwd-in", "cwd-out"])
@pytest.mark.parametrize("pd_differs", [False, True], ids=["pd-eq-rd", "pd-ne-rd"])
def test_g4_locates_same_file_across_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    layout: str,
    relative: bool,
    cwd_inside: bool,
    pd_differs: bool,
) -> None:
    rd, pd = _assemble(tmp_path / "case", layout)
    chapter_dir = rd / "project-output" if layout == "project-output" else rd
    target = chapter_dir / "chapter-3-x.md"
    rel_fp = "project-output/chapter-3-x.md" if layout == "project-output" else "chapter-3-x.md"
    fp = rel_fp if relative else str(target)
    monkeypatch.chdir(rd if cwd_inside else tmp_path)
    gpd = pd if pd_differs else rd
    result = json.loads(g4_chapter_drafting([fp], str(rd), str(gpd), str(tmp_path)))
    must_fix = " ".join(str(x) for x in result.get("must_fix", []))
    assert "G4.file_not_found" not in must_fix, (
        f"layout={layout} rel={relative} cwd_in={cwd_inside} pd_ne={pd_differs}: "
        "checker failed to locate the chapter file"
    )
    assert (
        any(c.get("id") == "G4.fatigue" for c in result.get("checks", []))
        or "G4.fatigue" in must_fix
    )
