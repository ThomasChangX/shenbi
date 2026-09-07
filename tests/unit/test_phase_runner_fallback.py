# spec #48 C34 (F115 residual): cmd_post_skill rglob fallback must not sweep
# arbitrary pre-existing .md files into G2 when no declared outputs exist.

import json
from pathlib import Path

from shenbi import phase_runner
from shenbi.status import PhaseState


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    round_dir = tmp_path / "round"
    state_dir = round_dir / "phase-state"
    state_dir.mkdir(parents=True)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    state = {"phase": "drafting", "state": PhaseState.STARTED, "steps": []}
    (state_dir / "drafting.json").write_text(json.dumps(state))
    # pre-existing unrelated .md in the project tree — the old rglob fallback
    # swept exactly this kind of file into G2.
    (project_dir / "unrelated.md").write_text("旧文件", encoding="utf-8")
    return round_dir, project_dir


def test_rglob_fallback_no_sweep_when_no_declared_outputs(tmp_path, monkeypatch):
    round_dir, project_dir = _setup(tmp_path)
    g2_calls: list[list[str]] = []

    def mock_run_gate(gate_name, args):
        if gate_name == "G2":
            g2_calls.append(list(args))
        return {"status": "PASS"}

    monkeypatch.setattr(phase_runner, "run_gate", mock_run_gate)
    phase_runner.cmd_post_skill("drafting", "worldbuilding", str(round_dir), str(project_dir))
    assert not g2_calls, (
        f"F115 residual: G2 ran on undeclared pre-existing .md files (args={g2_calls})"
    )
