"""R5: closure per-step explicit context (F379/F313) + genesis sentinels (F3B5/F380)."""

import json
import shutil
from pathlib import Path

from shenbi.contracts.paths import PathContext
from shenbi.pipeline.closure import (
    CLOSURE_STEPS,
    _closure_step_context,
    _resolve_closure_g4_path,
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md"


def _mk_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "novel.json").write_text(json.dumps({"total_chapters": 100}), encoding="utf-8")
    return proj


def _mk_cn_project(tmp_path: Path) -> Path:
    proj = tmp_path / "cnproj"
    (proj / "outline").mkdir(parents=True)
    shutil.copy(FIXTURE, proj / "outline" / "volume_map.md")
    (proj / "novel.json").write_text(json.dumps({"total_chapters": 100}), encoding="utf-8")
    return proj


def test_closure_step_contexts(tmp_path):
    proj = _mk_cn_project(tmp_path)
    by_num = {s.step_num: s for s in CLOSURE_STEPS}
    assert _closure_step_context(by_num[2], proj) == PathContext(chapter=100, arc=8)  # 100//12
    assert _closure_step_context(by_num[4], proj) == PathContext(chapter=100, volume=5)
    assert _closure_step_context(by_num[5], proj) == PathContext(chapter=100, volume=5)
    assert _closure_step_context(by_num[6], proj) == PathContext(chapter=100)  # F313: chapter
    assert _closure_step_context(by_num[10], proj) == PathContext(chapter=100)


def test_closure_g4_paths_resolved(tmp_path):
    """Acceptance: closure step 6 G4 checks chapter-100-long-span.md."""
    proj = _mk_cn_project(tmp_path)
    by_num = {s.step_num: s for s in CLOSURE_STEPS}
    assert _resolve_closure_g4_path(by_num[6], proj) == "audits/chapter-100-long-span.md"
    assert _resolve_closure_g4_path(by_num[10], proj) == "snapshots/chapter-100/"


def test_closure_prompt_build_all_steps(tmp_path):
    """Acceptance: all 10 closure steps build prompts (no UnresolvedPathError)."""
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    proj = _mk_cn_project(tmp_path)
    for step in CLOSURE_STEPS:
        ctx = _closure_step_context(step, proj)
        prompt = (
            f"Execute {step.skill} for book closure (step {step.step_num}). Project dir: {proj}"
        )
        system, user, outs = _build_skill_prompt(
            step.skill, proj, prompt, ctx.chapter if ctx else None, path_context=ctx
        )
        assert outs, f"step {step.step_num} produced no output paths"
        assert all("-N" not in o and "NNN" not in o for o in outs), outs


def test_dispatch_skill_injects_context_line(tmp_path, monkeypatch):
    """dispatch_skill(path_context=...) appends the carrier line to the prompt."""
    from shenbi.pipeline import dispatch_helper as dh

    captured: dict[str, object] = {}

    def fake_api(skill, pd, prompt, **kw):
        captured["prompt"] = prompt
        captured["kw"] = kw
        return type("R", (), {"success": True, "stderr": "", "returncode": 0})()

    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    monkeypatch.setattr(dh, "_dispatch_via_api", fake_api)
    dh.dispatch_skill(
        "shenbi-score-volume",
        tmp_path,
        "Execute for book closure.",
        path_context=PathContext(chapter=100, volume=5),
    )
    assert "[path-context] chapter=100 volume=5" in str(captured["prompt"])


def test_escalation_genesis_sentinel(tmp_path):
    """F3B5: chapter=None escalation resolves to the genesis artifact name."""
    from shenbi.contracts.paths import resolve_contract_path

    assert (
        resolve_contract_path(
            "audits/escalation-N-report.md", None, PathContext(escalation="genesis")
        )
        == "audits/escalation-genesis-report.md"
    )


def test_anchor_curate_sentinel(tmp_path):
    """F380: AC-NNN resolves via anchor ctx (genesis table sentinel AC-001.md)."""
    from shenbi.contracts.paths import resolve_contract_path

    assert (
        resolve_contract_path("benchmarks/anchors/AC-NNN.md", None, PathContext(anchor=1))
        == "benchmarks/anchors/AC-001.md"
    )


def test_escalation_genesis_wiring(tmp_path, monkeypatch):
    """F3B5 wiring: chapter=None escalation dispatch passes the genesis sentinel."""
    from shenbi.contracts.paths import PathContext
    from shenbi.pipeline import revision_router as rr

    captured: dict[str, object] = {}

    def fake(skill, pd, prompt, **kw):
        captured.update(kw)
        return type("R", (), {"success": True})()

    monkeypatch.setattr(rr, "dispatch_skill", fake)
    assert rr.dispatch_escalation(tmp_path, None, "ctx") is True
    assert captured.get("path_context") == PathContext(escalation="genesis")


def test_anchor_curate_wiring(tmp_path, monkeypatch):
    """F380 wiring: genesis step 16 dispatch passes anchor ctx (conditional)."""
    from shenbi.pipeline import genesis as gs
    from shenbi.pipeline.state import PipelineState

    captured: list[tuple[str, dict[str, object]]] = []

    def fake(skill, pd, prompt, **kw):
        captured.append((skill, kw))
        return type("R", (), {"success": True})()

    monkeypatch.setattr(gs, "dispatch_skill", fake)
    monkeypatch.setattr(gs, "run_gate_g4", lambda *a, **k: {"status": "PASS"})
    monkeypatch.setattr(gs, "_update_indexes", lambda *a, **k: None)

    state = PipelineState.default(str(tmp_path))
    state.genesis.current_step = 15  # 0-based: GENESIS_STEPS[15] = step 16 anchor-curate
    gs.run_genesis_step(state, tmp_path)
    anchor_calls = [kw for skill, kw in captured if skill == "shenbi-anchor-curate"]
    assert anchor_calls and anchor_calls[0].get("path_context") == PathContext(anchor=1)

    captured.clear()
    state2 = PipelineState.default(str(tmp_path))
    state2.genesis.current_step = 14  # adjacent non-anchor step (step 15)
    gs.run_genesis_step(state2, tmp_path)
    non_anchor = [kw for skill, kw in captured if skill != "shenbi-anchor-curate"]
    assert non_anchor and all(kw.get("path_context") is None for kw in non_anchor)
