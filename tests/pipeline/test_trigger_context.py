"""R4b: trigger dispatch/G4/subprocess share one N semantics (F373).

Monkeypatch captures dispatch prompt and G4 files — wiring unit test (not a
skill-output scenario; G0.9 does not apply here).
"""

import shutil
from pathlib import Path
from typing import Any

from shenbi.contracts.paths import build_trigger_context, format_path_context
from shenbi.pipeline._shared import read_volume_boundaries
from shenbi.pipeline.state import PipelineState
from shenbi.pipeline.triggers import TriggerResult, run_triggered_skills

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md"


def _mk_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "outline").mkdir(parents=True)
    shutil.copy(FIXTURE, proj / "outline" / "volume_map.md")
    return proj


def test_run_triggered_skills_wires_context_and_g4_paths(tmp_path, monkeypatch):
    from shenbi.pipeline import triggers

    proj = _mk_project(tmp_path)
    captured: dict[str, list[Any]] = {"prompts": [], "g4_files": []}

    def fake_dispatch(skill, project_dir, prompt, **kw):
        captured["prompts"].append((skill, prompt))
        return type("R", (), {"success": True})()

    def fake_g4(skill, files, project_dir, **kw):
        captured["g4_files"].append((skill, list(files)))
        return {"status": "PASS"}

    monkeypatch.setattr(triggers, "dispatch_skill", fake_dispatch)
    monkeypatch.setattr(triggers, "run_gate_g4", fake_g4)

    state = PipelineState.default(str(proj))
    result = TriggerResult()
    result.l2_distill = True
    ok = run_triggered_skills(state, proj, 60, result)
    assert ok is True

    ctx = build_trigger_context(60, read_volume_boundaries(proj))
    line = format_path_context(ctx)
    arc_prompts = [p for s, p in captured["prompts"] if "memory-distill" in s]
    assert arc_prompts and all(line in p for p in arc_prompts)
    assert ("shenbi-memory-distill", ["truth/arcs/arc-5.md"]) in captured["g4_files"]


def test_derive_input_files_per_family():
    """Acceptance: score-arc contract reads resolve to arc-5 via ctx (not arc-60)."""
    from shenbi.dispatcher.executor import derive_input_files

    ctx = build_trigger_context(60, {15, 35, 55, 75, 100})
    reads = derive_input_files("shenbi-score-arc", chapter=60, ctx=ctx)
    assert "truth/arcs/arc-5.md" in reads
    assert not any("arc-60" in r for r in reads)


def test_derive_output_files_per_family():
    from shenbi.audit._shared import derive_output_files

    ctx = build_trigger_context(60, {15, 35, 55, 75, 100})
    writes = derive_output_files("shenbi-score-arc", chapter=60, ctx=ctx)
    assert "audits/arc-5-score.md" in writes


def test_trigger_flow_prompt_lists_arc5_paths(tmp_path):
    """R4 acceptance 'Files to create lists arc-5' — full trigger-flow prompt."""
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    proj = _mk_project(tmp_path)
    # Seed the resolved read input so the prompt-builder injects it (missing
    # reads are skipped entirely — nothing to assert on otherwise).
    arc5 = proj / "truth" / "arcs" / "arc-5.md"
    arc5.parent.mkdir(parents=True)
    arc5.write_text("---\narc: 5\n---\n\n# 弧段 5 摘要\n", encoding="utf-8")
    ctx = build_trigger_context(60, read_volume_boundaries(proj))
    prompt = (
        f"Execute shenbi-score-arc for chapter 60. Project dir: {proj}\n{format_path_context(ctx)}"
    )
    system, user, outs = _build_skill_prompt("shenbi-score-arc", proj, prompt, 60, path_context=ctx)
    assert "audits/arc-5-score.md" in outs
    assert "arc-60" not in user
    assert "truth/arcs/arc-5.md" in user  # reads loop also ctx-routed


def test_audit_watch_paths_per_family():
    """Write-audit blind spot (executor.py:220-225): watch paths resolve per family."""
    from shenbi.dispatcher.executor import _audit_watch_paths

    ctx = build_trigger_context(60, {15, 35, 55, 75, 100})
    watch = _audit_watch_paths("shenbi-score-arc", chapter=60, ctx=ctx)
    assert any("arc-5-score.md" in w for w in watch)
    assert not any("arc-60" in w for w in watch)
