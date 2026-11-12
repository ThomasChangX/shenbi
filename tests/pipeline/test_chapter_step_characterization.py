"""Spec #87 T0: per-regime characterization through the public entry.

These pin behavior BEFORE the five-regime extraction (T3). They must stay
green after T3 without modification — that is the behavior-preservation
proof. Eight paths: the five regimes (audit wave / post-draft pair /
context assembly / pipeline-internal / generic serial) plus the
conditional-skip main-function path and the two serial success-tail
scenarios (resonance :4702 / revision :4728) that the position-scoped
hooks (plan r2.3) exist to carry.

Seam references: test_bundle_stepping.py:382-420 (serial drive),
test_parallel_steps.py:330-371 (wave boundary patches).
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from shenbi.pipeline import chapter_loop as cl
from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, run_chapter_step
from shenbi.pipeline.state import PipelinePhase, PipelineState


def _step_index_of(predicate) -> int:
    return next(i for i, s in enumerate(CHAPTER_STEPS) if predicate(s))


def _state(tmp_path: Path, step_idx: int, chapter: int = 1) -> PipelineState:
    state = PipelineState.default(str(tmp_path))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = chapter
    state.chapter_loop.step_index = step_idx
    return state


def _ok_result():
    return SimpleNamespace(success=True, result={}, stdout="", stderr="", returncode=0)


_G4_PASS = {"status": "PASS", "checks": [], "must_fix": []}


def _results_for(tasks):
    # dispatch_reviews_parallel (parallel_dispatch.py:241) and
    # dispatch_serial_reviews (chapter_loop.py:3787) both return
    # list[DispatchResult]; wave consumers .extend()/concat.
    return [_ok_result() for _ in tasks]


@pytest.mark.unit
def test_audit_wave_regime(tmp_path: Path) -> None:
    """First audit step dispatches the parallel wave and advances.

    Wave seam (test_parallel_steps.py:344-371 precedent): the wave core
    runs through dispatch_reviews_parallel which resolves dispatch_skill
    in the parallel_dispatch namespace — patching cl.dispatch_skill alone
    would let REAL dispatches through. Patch the wave boundary instead.
    """
    state = _state(
        tmp_path,
        _step_index_of(lambda s: s.is_audit),  # first audit step
    )
    wave_calls: list[list[object]] = []

    def _fake_wave(tasks, on_task_complete=None, state=None):
        wave_calls.append(list(tasks))
        return _results_for(tasks)

    with (
        patch(
            "shenbi.pipeline.audit_context_cache.build_shared_audit_context",
            return_value=SimpleNamespace(
                estimated_tokens=0,
                raw_files={},
                world_rules="",
                character_list="",
                style_profile="",
                pending_hooks="",
            ),
        ),
        patch("shenbi.pipeline.audit_layer.get_active_genre_audits", return_value=[]),
        patch(
            "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel",
            side_effect=_fake_wave,
        ),
        patch.object(
            cl,
            "dispatch_serial_reviews",
            side_effect=lambda tasks, pd, state=None: _results_for(tasks),
        ),
        patch.object(cl, "_parse_and_persist_resonance"),
        patch.object(cl, "_route_revision_after_resonance"),
        patch.object(cl, "write_audit_aggregate"),
        patch("shenbi.pipeline.revision_router.dispatch_escalation", lambda *a, **kw: None),
    ):
        reached = run_chapter_step(state, tmp_path)

    assert isinstance(reached, bool)
    assert wave_calls, "audit wave must run the parallel dispatch boundary"
    assert state.chapter_loop.step_index > _step_index_of(lambda s: s.is_audit) or reached


@pytest.mark.unit
def test_post_draft_pair_regime(tmp_path: Path) -> None:
    """Foreshadowing-lifecycle step runs the lifecycle+settling pair.

    Ghost-chain guard (:3893) requires chapters/chapter-1.md to exist
    before the draft-consuming lifecycle/settling pair may dispatch.
    """
    (tmp_path / "chapters").mkdir(parents=True, exist_ok=True)
    (tmp_path / "chapters" / "chapter-1.md").write_text("# 第一章\n\n正文。", encoding="utf-8")

    state = _state(tmp_path, _step_index_of(lambda s: s.skill == "shenbi-foreshadowing-lifecycle"))

    def _pair_dispatch(skill, project_dir, prompt, **kw):
        for rel in ("staging/truth/pending_hooks.md",):  # settling gate: any staging/truth/*.md
            out = Path(project_dir) / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("<!-- unit characterization stub -->\n", encoding="utf-8")
        return _ok_result()

    import time as _time

    with (
        patch.object(_time, "sleep", lambda *_a: None),
        patch.object(cl, "dispatch_skill", side_effect=_pair_dispatch) as dsp,
        patch.object(cl, "run_gate_g4", lambda *a, **kw: dict(_G4_PASS)),
    ):
        reached = run_chapter_step(state, tmp_path)

    skills = [c.args[0] for c in dsp.call_args_list]
    assert isinstance(reached, bool)
    assert "shenbi-foreshadowing-lifecycle" in skills and "shenbi-state-settling" in skills
    assert skills.index("shenbi-foreshadowing-lifecycle") < skills.index("shenbi-state-settling"), (
        "settling must run AFTER lifecycle (staging merge-base ordering)"
    )
    # pair advances two steps (or reaches the audit checkpoint)
    assert (
        state.chapter_loop.step_index
        >= _step_index_of(lambda s: s.skill == "shenbi-foreshadowing-lifecycle") + 2
        or reached
    )


@pytest.mark.unit
def test_context_assembly_regime(tmp_path: Path) -> None:
    """Step 3 (pipeline-context-prepare) assembles context packages, no dispatch."""
    idx = _step_index_of(lambda s: s.calls_context_assembly)
    state = _state(tmp_path, idx)
    assembled: list[int] = []

    with (
        patch.object(cl, "_run_context_assembly", side_effect=lambda pd, n: assembled.append(n)),
        patch.object(cl, "dispatch_skill") as dsp,
    ):
        reached = run_chapter_step(state, tmp_path)

    assert isinstance(reached, bool)
    assert assembled == [1], "context assembly must materialize the package for the chapter"
    dsp.assert_not_called()
    assert state.chapter_loop.step_index > idx or reached


@pytest.mark.unit
def test_pipeline_internal_regime(tmp_path: Path) -> None:
    """pipeline-linguistic-drift-check advances without any dispatch."""
    idx = _step_index_of(lambda s: s.skill == "pipeline-linguistic-drift-check")
    state = _state(tmp_path, idx)

    with patch.object(cl, "dispatch_skill") as dsp:
        reached = run_chapter_step(state, tmp_path)

    dsp.assert_not_called()
    assert isinstance(reached, bool)
    assert state.chapter_loop.step_index > idx or reached


@pytest.mark.unit
def test_serial_dispatch_regime(tmp_path: Path) -> None:
    """chapter-planning dispatches through the serial regime with path context."""
    state = _state(tmp_path, _step_index_of(lambda s: s.skill == "shenbi-chapter-planning"))
    captured: dict[str, object] = {}

    def _fake_dispatch(skill, project_dir, prompt, **kw):
        captured["skill"] = skill
        captured["path_context"] = kw.get("path_context")
        out = Path(project_dir) / "staging" / "plans" / "chapter-1-plan.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# plan", encoding="utf-8")
        return _ok_result()

    import time as _time

    with (
        patch.object(_time, "sleep", lambda *_a: None),
        patch.object(cl, "dispatch_skill", side_effect=_fake_dispatch),
        patch.object(cl, "run_gate_g4", lambda *a, **kw: dict(_G4_PASS)),
    ):
        reached = run_chapter_step(state, tmp_path)

    assert captured["skill"] == "shenbi-chapter-planning"
    assert getattr(captured["path_context"], "chapter", None) == 1, (
        "serial dispatch must carry the chapter [path-context]"
    )
    assert isinstance(reached, bool)
    # planning raises CHAPTER_MEMO checkpoint (or advances)
    idx = _step_index_of(lambda s: s.skill == "shenbi-chapter-planning")
    assert reached or state.chapter_loop.step_index > idx


@pytest.mark.unit
def test_conditional_skip_regime(tmp_path: Path) -> None:
    """chapter-revision with no audit findings skips without dispatch.

    :4452 conditional gate — `_should_run_step` returns False for the
    revision step when `any_audit_has_findings` finds nothing (empty
    tmp_path). The step is recorded done and the cursor advances.
    """
    idx = _step_index_of(lambda s: s.skill == "shenbi-chapter-revision")
    (tmp_path / "chapters").mkdir(parents=True, exist_ok=True)
    (tmp_path / "chapters" / "chapter-1.md").write_text("# 第一章", encoding="utf-8")
    state = _state(tmp_path, idx)

    with patch.object(cl, "dispatch_skill") as dsp:
        reached = run_chapter_step(state, tmp_path)

    dsp.assert_not_called()
    assert isinstance(reached, bool)
    assert state.chapter_loop.step_index > idx or reached
    cs = state.chapter_loop.chapter_states.get("1")
    done = (cs.steps_done if cs is not None else []) or []
    assert any("chapter-revision" in d for d in done)


@pytest.mark.unit
def test_serial_resonance_tail(tmp_path: Path) -> None:
    """Serial review-resonance success: two void tail calls fire exactly once,
    then the gate/add_step_done/_reset_retries bookkeeping still runs.

    Entering at idx 13 (not _FIRST_AUDIT_IDX) routes the audit step through
    the serial regime — the path the position-1 hook (:4702) lives on.
    """
    idx = _step_index_of(lambda s: s.skill == "shenbi-review-resonance")
    state = _state(tmp_path, idx)
    tail_calls: list[str] = []

    import time as _time

    with (
        patch.object(_time, "sleep", lambda *_a: None),
        patch.object(cl, "dispatch_skill", side_effect=lambda *a, **kw: _ok_result()),
        patch.object(cl, "run_gate_g4", lambda *a, **kw: dict(_G4_PASS)),
        patch.object(cl, "run_gate_g3", lambda *a, **kw: {"status": "PASS"}),
        patch.object(
            cl,
            "_parse_and_persist_resonance",
            side_effect=lambda *a, **kw: tail_calls.append("persist"),
        ),
        patch.object(
            cl,
            "_route_revision_after_resonance",
            side_effect=lambda *a, **kw: tail_calls.append("route"),
        ),
    ):
        reached = run_chapter_step(state, tmp_path)

    assert isinstance(reached, bool)
    assert tail_calls == ["persist", "route"], (
        "resonance tail: persist then route, exactly once each"
    )
    assert state.chapter_loop.step_index > idx or reached


@pytest.mark.unit
def test_serial_revision_tail(tmp_path: Path) -> None:
    """Serial chapter-revision success: decisions file ensured, stale flag
    flipped, chapter recorded done, cursor advances.

    Requires: audit findings present (conditional gate open), the chapter
    draft on disk (ghost-chain guard + output gate), revalidation clean.
    """
    idx = _step_index_of(lambda s: s.skill == "shenbi-chapter-revision")
    (tmp_path / "chapters").mkdir(parents=True, exist_ok=True)
    draft = tmp_path / "chapters" / "chapter-1.md"
    draft.write_text("# 第一章\n\n修订后正文。", encoding="utf-8")

    state = _state(tmp_path, idx)
    # Non-vacuous pin (audit-T0 I1): start STALE with a routed revision so
    # the tail block actually flips stale -> False and lands decisions.
    cs0 = (
        state.chapter_loop.chapter_states.setdefault(
            "1", type(state.chapter_loop.chapter_states["1"])()
        )
        if state.chapter_loop.chapter_states.get("1")
        else None
    )
    from shenbi.pipeline.state import ChapterState

    cs = state.chapter_loop.chapter_states.setdefault("1", ChapterState())
    cs.declarations_stale = True
    cs.audit_results["revision_route"] = "auto"

    decisions = tmp_path / "chapters" / "chapter-1-revision-decisions.json"

    with (
        patch.object(cl, "any_audit_has_findings", return_value=True),
        patch.object(cl, "dispatch_skill", side_effect=lambda *a, **kw: _ok_result()),
        patch.object(cl, "_revalidate_revised_chapter", return_value=[]),
    ):
        reached = run_chapter_step(state, tmp_path)

    assert isinstance(reached, bool)
    cs = state.chapter_loop.chapter_states.get("1")
    assert cs is not None, "revision tail must ensure the chapter state exists"
    assert cs.declarations_stale is False, "clean revalidation must clear the stale flag"
    assert decisions.is_file(), "routed revision must land the decisions file"
    assert state.chapter_loop.step_index > idx or reached
