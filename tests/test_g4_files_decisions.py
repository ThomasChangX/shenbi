"""F434 (spec #30 T2): contract-declared decisions sidecars must join the G4
file list so G4.dec actually runs for dual-product skills instead of SKIP.
Contract expansion only APPENDS — it must never short-circuit the
state-settling staging/truth glob.
"""

from pathlib import Path

from shenbi.pipeline.chapter_loop import ChapterStep, _resolve_g4_files


def _step(
    skill: str = "shenbi-chapter-drafting",
    output_path: str = "chapters/chapter-N.md",
    uses_staging: bool = False,
) -> ChapterStep:
    return ChapterStep(
        step_num=1,
        skill=skill,
        name="test-step",
        output_path=output_path,
        uses_staging=uses_staging,
    )


def test_decisions_sidecar_in_g4_files(tmp_path: Path):
    ch = tmp_path / "chapters"
    ch.mkdir()
    (ch / "chapter-2.md").write_text("# 第二章\n" + "正文" * 100, encoding="utf-8")
    (ch / "chapter-2-decisions.json").write_text(
        '{"$schema": "shenbi-decisions-v1"}', encoding="utf-8"
    )
    files = _resolve_g4_files(tmp_path, _step(), chapter=2)
    assert any(str(f).endswith("chapters/chapter-2-decisions.json") for f in files), files
    assert any(str(f).endswith("chapters/chapter-2.md") for f in files), files


def test_missing_sidecar_not_included(tmp_path: Path):
    ch = tmp_path / "chapters"
    ch.mkdir()
    (ch / "chapter-2.md").write_text("x", encoding="utf-8")
    files = _resolve_g4_files(tmp_path, _step(), chapter=2)
    assert not any("decisions" in str(f) for f in files), files


def test_state_settling_glob_not_short_circuited(tmp_path: Path):
    """Regression: sidecar expansion must not drop the staging/truth *.md files."""
    st = tmp_path / "staging" / "truth"
    st.mkdir(parents=True)
    (st / "current_state.md").write_text("x", encoding="utf-8")
    (st / "state-settling-decisions.json").write_text("{}", encoding="utf-8")
    step = _step(skill="shenbi-state-settling", output_path="", uses_staging=True)
    files = _resolve_g4_files(tmp_path, step, chapter=2)
    assert any("current_state.md" in str(f) for f in files), files
    # sidecar appended once state-settling declares it in writes (Task 5);
    # here the guard is that expansion doesn't drop the glob results.


def test_revision_sidecar_appended(tmp_path: Path):
    """chapter-revision's sidecar joins the list; composite G4 re-partitions it."""
    ch = tmp_path / "chapters"
    ch.mkdir()
    (ch / "chapter-3-revision.md").write_text("y", encoding="utf-8")
    (ch / "chapter-3-revision-decisions.json").write_text("{}", encoding="utf-8")
    step = _step(skill="shenbi-chapter-revision", output_path="chapters/chapter-N-revision.md")
    files = _resolve_g4_files(tmp_path, step, chapter=3)
    assert any("revision-decisions.json" in str(f) for f in files), files
