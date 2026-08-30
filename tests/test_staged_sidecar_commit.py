"""audit-T5 C1 (spec #30 T2 follow-up): staged decisions sidecars must be
committed with their sibling artifacts — commit sites used to move only
*.md / hardcoded targets and then rmtree staging, destroying the sidecar
that G4.dec had just validated.
"""

from pathlib import Path

from shenbi.pipeline.chapter_loop import staged_decisions_targets


def test_staged_sidecar_listed_for_chapter_planning(tmp_path: Path):
    st = tmp_path / "staging" / "plans"
    st.mkdir(parents=True)
    (st / "chapter-3-plan.md").write_text("plan", encoding="utf-8")
    (st / "chapter-3-plan-decisions.json").write_text("{}", encoding="utf-8")
    targets = staged_decisions_targets(tmp_path, "shenbi-chapter-planning", 3)
    assert targets == ["plans/chapter-3-plan-decisions.json"]


def test_unstaged_sidecar_not_listed(tmp_path: Path):
    assert staged_decisions_targets(tmp_path, "shenbi-chapter-planning", 3) == []


def test_state_settling_staged_sidecar_listed(tmp_path: Path):
    st = tmp_path / "staging" / "truth"
    st.mkdir(parents=True)
    (st / "state-settling-decisions.json").write_text("{}", encoding="utf-8")
    targets = staged_decisions_targets(tmp_path, "shenbi-state-settling", 2)
    assert "truth/state-settling-decisions.json" in targets


def test_parallel_auto_settle_commits_sidecar(tmp_path: Path):
    """audit-T5 C3: the --auto parallel settle path copies the staged sidecar
    to live truth/ (drove production code, not a mirrored glob).
    """
    from shenbi.pipeline.chapter_loop import _auto_settle_parallel
    from shenbi.pipeline.state import PipelineState

    st = tmp_path / "staging" / "truth"
    st.mkdir(parents=True)
    (st / "current_state.md").write_text("x", encoding="utf-8")
    (st / "state-settling-decisions.json").write_text("{}", encoding="utf-8")
    state = PipelineState()
    state.config.state_settle_review_required = False
    assert _auto_settle_parallel(state, tmp_path, chapter=2) is True
    assert (tmp_path / "truth" / "state-settling-decisions.json").exists()
    assert (tmp_path / "truth" / "current_state.md").exists()
