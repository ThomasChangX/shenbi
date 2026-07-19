"""Unit tests for shenbi.phase_runner.

Business rules under test:
- State machine: created → started → skills_done → scored → finalized
  (each transition validates current state; mismatch => exit 1)
- Skill MD parsing: Reads/Writes/Updates sections become data contracts
- Gate integration: G5 (start, finalize), G2+G4 (post-skill)
- Marker enforcement: pre-score checks G4 markers for prerequisites
- CLI: each subcommand maps to its handler; missing --round-dir exits 1
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from shenbi import phase_runner
from shenbi.phase_runner import (
    cmd_finalize,
    cmd_post_score,
    cmd_post_skill,
    cmd_pre_score,
    cmd_pre_skill,
    cmd_start,
    load_state,
    main,
    now_iso,
    require_state,
    save_state,
)

pytestmark = pytest.mark.unit

# --- Fixtures -------------------------------------------------------------


@pytest.fixture
def round_dir(tmp_path: Path) -> Path:
    """Round directory with phase-state/ subdirectory pre-created."""
    state_dir = tmp_path / "phase-state"
    state_dir.mkdir()
    return tmp_path


@pytest.fixture
def started_state(round_dir: Path) -> dict[str, Any]:
    """State pre-populated to 'started' for testing mid-flow commands."""
    state = {"phase": "design", "state": "started", "steps": [{"action": "start"}]}
    save_state(str(round_dir), state)
    return state


@pytest.fixture
def skills_done_state(round_dir: Path) -> dict[str, Any]:
    state = {"phase": "design", "state": "skills_done", "steps": []}
    save_state(str(round_dir), state)
    return state


@pytest.fixture
def scored_state(round_dir: Path) -> dict[str, Any]:
    state = {"phase": "design", "state": "scored", "steps": []}
    save_state(str(round_dir), state)
    return state


@pytest.fixture
def fake_g5_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch run_gate to return a G5 PASS — most cmd_* tests want this."""

    def fake_run_gate(gate: str, args: list[str]) -> dict[str, Any]:
        return {"gate": gate, "status": "PASS", "args": args}

    monkeypatch.setattr(phase_runner, "run_gate", fake_run_gate)


@pytest.fixture
def fake_g5_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_gate(gate: str, args: list[str]) -> dict[str, Any]:
        return {
            "gate": gate,
            "status": "FAIL",
            "must_fix": ["G5.1: round structure incomplete"],
            "args": args,
        }

    monkeypatch.setattr(phase_runner, "run_gate", fake_run_gate)


# --- TestLoadState -------------------------------------------------------


class TestLoadState:
    def test_returns_default_created_state_when_no_state_file(self, round_dir: Path) -> None:
        state = load_state(str(round_dir), "design")
        assert state == {"phase": "design", "state": "created", "steps": []}

    def test_loads_existing_state_from_phase_state_dir(
        self, round_dir: Path, started_state: dict[str, Any]
    ) -> None:
        loaded = load_state(str(round_dir), "design")
        assert loaded["state"] == "started"
        assert loaded["phase"] == "design"

    def test_state_file_path_uses_phase_name(self, round_dir: Path) -> None:
        """Different phases get independent state files — design and build
        don't collide.
        """
        save_state(str(round_dir), {"phase": "design", "state": "started", "steps": []})
        build_state = load_state(str(round_dir), "build")
        assert build_state["state"] == "created"


# --- TestSaveState -------------------------------------------------------


class TestSaveState:
    def test_writes_state_to_phase_state_subdir(self, round_dir: Path) -> None:
        state = {"phase": "design", "state": "started", "steps": [{"action": "x"}]}
        save_state(str(round_dir), state)
        state_file = round_dir / "phase-state" / "design.json"
        assert state_file.exists()
        loaded = json.loads(state_file.read_text(encoding="utf-8"))
        assert loaded == state

    def test_creates_phase_state_dir_if_missing(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        state = {"phase": "design", "state": "started", "steps": []}
        save_state(str(round_dir), state)
        assert (round_dir / "phase-state" / "design.json").exists()


# --- TestNowIso ----------------------------------------------------------


class TestNowIso:
    def test_returns_iso_8601_with_timezone(self) -> None:
        ts = now_iso()
        # ISO 8601 with UTC offset: ...+00:00
        assert "T" in ts
        assert ts.endswith("+00:00")

    def test_subsequent_calls_produce_non_decreasing_timestamps(self) -> None:
        t1 = now_iso()
        t2 = now_iso()
        assert t2 >= t1


# --- TestRequireState ----------------------------------------------------


class TestRequireState:
    def test_passes_silently_when_state_in_expected_list(self, round_dir: Path) -> None:
        state = {"phase": "design", "state": "started", "steps": []}
        # No exception, no exit
        require_state(state, ["started", "skills_done"], "test-action")

    def test_exits_with_error_when_state_not_expected(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        state = {"phase": "design", "state": "created", "steps": []}
        with pytest.raises(SystemExit) as exc:
            require_state(state, ["started"], "start")
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert "Cannot start" in emitted["error"]

    def test_error_message_includes_actual_state(self, capsys: pytest.CaptureFixture[str]) -> None:
        state = {"phase": "design", "state": "created", "steps": []}
        with pytest.raises(SystemExit):
            require_state(state, ["started"], "pre-skill")
        emitted = json.loads(capsys.readouterr().out)
        assert "created" in emitted["error"]

    def test_error_message_lists_expected_states(self, capsys: pytest.CaptureFixture[str]) -> None:
        state = {"phase": "design", "state": "created", "steps": []}
        with pytest.raises(SystemExit):
            require_state(state, ["started", "skills_done"], "post-skill")
        emitted = json.loads(capsys.readouterr().out)
        assert "started" in emitted["error"]
        assert "skills_done" in emitted["error"]


# --- TestCmdStart --------------------------------------------------------


class TestCmdStart:
    def test_transitions_created_to_started_on_g5_pass(
        self, round_dir: Path, fake_g5_pass: None
    ) -> None:
        cmd_start("design", str(round_dir), project_dir=None)
        state = load_state(str(round_dir), "design")
        assert state["state"] == "started"

    def test_records_start_step_with_g5_status(self, round_dir: Path, fake_g5_pass: None) -> None:
        cmd_start("design", str(round_dir), project_dir=None)
        state = load_state(str(round_dir), "design")
        assert any(s["action"] == "start" and s["g5_status"] == "PASS" for s in state["steps"])

    def test_emits_ok_status_with_started_state(
        self, round_dir: Path, fake_g5_pass: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        cmd_start("design", str(round_dir), project_dir=None)
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "ok"
        assert emitted["state"] == "started"

    def test_blocks_when_g5_fails(
        self, round_dir: Path, fake_g5_fail: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            cmd_start("design", str(round_dir), project_dir=None)
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "blocked"
        assert emitted["g5"]["status"] == "FAIL"

    def test_preserves_created_state_when_g5_blocks(
        self, round_dir: Path, fake_g5_fail: None
    ) -> None:
        with pytest.raises(SystemExit):
            cmd_start("design", str(round_dir), project_dir=None)
        state = load_state(str(round_dir), "design")
        # State stays created; only step recorded
        assert state["state"] == "created"

    def test_refuses_when_already_started(
        self, round_dir: Path, started_state: dict[str, Any], fake_g5_pass: None
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            cmd_start("design", str(round_dir), project_dir=None)
        assert exc.value.code == 1


# --- TestCmdPreSkill -----------------------------------------------------


_POINT_LOADER_REGISTRY = (
    "concepts:\n"
    "  - {name: world/story_bible.md, kind: world}\n"
    "  - {name: outline/story_frame.md, kind: outline}\n"
    "  - {name: world/locations.md, kind: world}\n"
    "  - {name: truth/current_state.md, kind: truth}\n"
    "patterns: []\n"
    "globs: []\n"
)


def _point_loader_at(monkeypatch: pytest.MonkeyPatch, skills_root: Path) -> None:
    """Redirect contract.load_contract at a tmp skills dir + tmp registry."""
    reg = skills_root / "registry.yaml"
    reg.write_text(_POINT_LOADER_REGISTRY, encoding="utf-8")
    monkeypatch.setattr("shenbi.contracts.legacy.SKILLS", skills_root)
    monkeypatch.setattr("shenbi.contracts.legacy.REGISTRY_PATH", reg)


class TestCmdPreSkill:
    def test_exits_when_skill_md_missing(
        self, round_dir: Path, started_state: dict[str, Any], capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            cmd_pre_skill("design", "shenbi-nonexistent-skill", str(round_dir))
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "error"

    def test_refuses_when_state_not_started(
        self, round_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # State is 'created' (default) — pre-skill needs 'started'
        with pytest.raises(SystemExit) as exc:
            cmd_pre_skill("design", "shenbi-worldbuilding", str(round_dir))
        assert exc.value.code == 1

    def test_extracts_reads_writes_updates_from_frontmatter_contract(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """cmd_pre_skill builds the data contract via load_contract (frontmatter),
        not a body regex — updates fold into writes.
        """
        fake_skills = round_dir / "skills"
        (fake_skills / "shenbi-test-skill").mkdir(parents=True)
        (fake_skills / "shenbi-test-skill" / "SKILL.md").write_text(
            "---\nname: shenbi-test-skill\ndescription: Use when test\n"
            "contract:\n  kind: artifact\n"
            "  reads:\n    - world/story_bible.md\n    - outline/story_frame.md\n"
            "  writes:\n    - world/locations.md\n"
            "  updates:\n    - truth/current_state.md\n"
            "---\n\n# Skill\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(phase_runner, "PROJECT", round_dir)
        _point_loader_at(monkeypatch, fake_skills)
        cmd_pre_skill("design", "shenbi-test-skill", str(round_dir))
        emitted = json.loads(capsys.readouterr().out)
        assert "world/story_bible.md" in emitted["reads"]
        assert "outline/story_frame.md" in emitted["reads"]
        assert "world/locations.md" in emitted["writes"]
        assert "truth/current_state.md" in emitted["writes"]  # updates fold into writes

    def test_emits_execute_skill_action(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        fake_skills = round_dir / "skills"
        (fake_skills / "shenbi-x").mkdir(parents=True)
        (fake_skills / "shenbi-x" / "SKILL.md").write_text(
            "---\nname: shenbi-x\ndescription: Use when x\n"
            "contract:\n  kind: artifact\n  reads: []\n  writes: []\n  updates: []\n"
            "---\n\n# Skill\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(phase_runner, "PROJECT", round_dir)
        _point_loader_at(monkeypatch, fake_skills)
        cmd_pre_skill("design", "shenbi-x", str(round_dir))
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["action"] == "execute_skill"

    def test_returns_empty_lists_when_contract_is_empty(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A skill with a valid empty contract emits reads=[]/writes=[]."""
        fake_skills = round_dir / "skills"
        (fake_skills / "shenbi-bare").mkdir(parents=True)
        (fake_skills / "shenbi-bare" / "SKILL.md").write_text(
            "---\nname: shenbi-bare\ndescription: Use when bare\n"
            "contract:\n  kind: ephemeral\n  reads: []\n  writes: []\n  updates: []\n"
            "---\n\n# Bare skill\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(phase_runner, "PROJECT", round_dir)
        _point_loader_at(monkeypatch, fake_skills)
        cmd_pre_skill("design", "shenbi-bare", str(round_dir))
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["reads"] == []
        assert emitted["writes"] == []


# --- TestCmdPostSkill ----------------------------------------------------


@pytest.mark.last
class TestCmdPostSkill:
    def test_runs_g2_and_g4_when_output_files_present(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """post-skill assumes the skill wrote files under project_dir.
        Both G2 (per-file quality) and G4 (skill-specific) run.
        """
        project_dir = round_dir / "project-output"
        project_dir.mkdir()
        (project_dir / "chapter.md").write_text("hello world", encoding="utf-8")

        gate_calls: list[tuple[str, list[str]]] = []

        def fake_run_gate(gate: str, args: list[str]) -> dict[str, Any]:
            gate_calls.append((gate, args))
            return {"gate": gate, "status": "PASS"}

        monkeypatch.setattr(phase_runner, "run_gate", fake_run_gate)
        cmd_post_skill("design", "shenbi-x", str(round_dir), str(project_dir))
        gates_run = {g for g, _ in gate_calls}
        assert "G2" in gates_run
        assert "G4" in gates_run

    def test_skips_g2_when_no_output_files(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An empty project dir means G2 has nothing to validate."""
        project_dir = round_dir / "project-output"
        project_dir.mkdir()

        def fake_run_gate(gate: str, args: list[str]) -> dict[str, Any]:
            assert gate != "G2", "G2 should not run when no output files"
            return {"gate": gate, "status": "PASS"}

        monkeypatch.setattr(phase_runner, "run_gate", fake_run_gate)
        cmd_post_skill("design", "shenbi-x", str(round_dir), str(project_dir))

    def test_blocks_when_g4_fails(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        project_dir = round_dir / "project-output"
        project_dir.mkdir()
        (project_dir / "x.md").write_text("x", encoding="utf-8")

        def fake_run_gate(gate: str, args: list[str]) -> dict[str, Any]:
            if gate == "G4":
                return {"gate": gate, "status": "FAIL", "must_fix": ["defect"]}
            return {"gate": gate, "status": "PASS"}

        monkeypatch.setattr(phase_runner, "run_gate", fake_run_gate)
        with pytest.raises(SystemExit) as exc:
            cmd_post_skill("design", "shenbi-x", str(round_dir), str(project_dir))
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "blocked"

    def test_refuses_when_state_not_started(
        self, round_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project_dir = round_dir / "p"
        project_dir.mkdir()
        monkeypatch.setattr(phase_runner, "run_gate", lambda g, a: {"gate": g, "status": "PASS"})
        with pytest.raises(SystemExit) as exc:
            cmd_post_skill("design", "shenbi-x", str(round_dir), str(project_dir))
        assert exc.value.code == 1

    def test_records_step_with_gate_statuses(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir = round_dir / "project-output"
        project_dir.mkdir()
        (project_dir / "x.md").write_text("x", encoding="utf-8")
        monkeypatch.setattr(
            phase_runner,
            "run_gate",
            lambda g, a: {"gate": g, "status": "PASS"},
        )
        cmd_post_skill("design", "shenbi-x", str(round_dir), str(project_dir))
        state = load_state(str(round_dir), "design")
        post_skill_steps = [s for s in state["steps"] if s["action"] == "post-skill"]
        assert post_skill_steps
        assert post_skill_steps[-1]["g4"] == "PASS"


# --- TestCmdPreScore -----------------------------------------------------


class TestCmdPreScore:
    def test_transitions_started_to_skills_done_when_all_markers_present(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        deps = {"t2-phases": {"design": {"prerequisites": ["shenbi-x"]}}}
        monkeypatch.setattr(phase_runner, "load_deps", lambda: deps)
        marker_dir = round_dir / "gate-markers"
        marker_dir.mkdir()
        (marker_dir / "G4-shenbi-x-generative.json").write_text("{}", encoding="utf-8")
        cmd_pre_score("design", str(round_dir))
        state = load_state(str(round_dir), "design")
        assert state["state"] == "skills_done"

    def test_blocks_when_marker_missing(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        deps = {"t2-phases": {"design": {"prerequisites": ["shenbi-x", "shenbi-y"]}}}
        monkeypatch.setattr(phase_runner, "load_deps", lambda: deps)
        marker_dir = round_dir / "gate-markers"
        marker_dir.mkdir()
        # Only shenbi-x marker exists; shenbi-y missing
        (marker_dir / "G4-shenbi-x-generative.json").write_text("{}", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            cmd_pre_score("design", str(round_dir))
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "blocked"
        assert "G4-shenbi-y-generative" in emitted["missing_markers"]

    def test_blocks_when_expected_output_missing(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        deps = {"t2-phases": {"design": {"prerequisites": [], "expected_outputs": ["report.md"]}}}
        monkeypatch.setattr(phase_runner, "load_deps", lambda: deps)
        with pytest.raises(SystemExit) as exc:
            cmd_pre_score("design", str(round_dir))
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["missing_output"] == "report.md"

    def test_supports_glob_pattern_expected_output(
        self,
        round_dir: Path,
        started_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Patterns containing '*' use rglob; presence of any match passes."""
        (round_dir / "project-output").mkdir()
        (round_dir / "project-output" / "ch-001.md").write_text("x", encoding="utf-8")
        deps = {"t2-phases": {"design": {"prerequisites": [], "expected_outputs": ["ch-*.md"]}}}
        monkeypatch.setattr(phase_runner, "load_deps", lambda: deps)
        cmd_pre_score("design", str(round_dir))
        state = load_state(str(round_dir), "design")
        assert state["state"] == "skills_done"

    def test_refuses_when_state_not_started(self, round_dir: Path) -> None:
        with pytest.raises(SystemExit) as exc:
            cmd_pre_score("design", str(round_dir))
        assert exc.value.code == 1


# --- TestCmdPostScore ----------------------------------------------------


class TestCmdPostScore:
    def test_transitions_skills_done_to_scored(
        self,
        round_dir: Path,
        skills_done_state: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        scores = tmp_path / "scores.json"
        scores.write_text("{}", encoding="utf-8")
        cmd_post_score("design", str(scores), str(round_dir))
        state = load_state(str(round_dir), "design")
        assert state["state"] == "scored"

    def test_exits_when_scores_file_missing(
        self,
        round_dir: Path,
        skills_done_state: dict[str, Any],
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            cmd_post_score("design", "/nope/scores.json", str(round_dir))
        assert exc.value.code == 1

    def test_records_step_with_scores_file_path(
        self,
        round_dir: Path,
        skills_done_state: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        scores = tmp_path / "scores.json"
        scores.write_text("{}", encoding="utf-8")
        cmd_post_score("design", str(scores), str(round_dir))
        state = load_state(str(round_dir), "design")
        post_score_steps = [s for s in state["steps"] if s["action"] == "post-score"]
        assert post_score_steps
        assert str(scores) == post_score_steps[-1]["scores_file"]

    def test_refuses_when_state_not_skills_done(
        self, round_dir: Path, started_state: dict[str, Any], tmp_path: Path
    ) -> None:
        scores = tmp_path / "scores.json"
        scores.write_text("{}", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            cmd_post_score("design", str(scores), str(round_dir))
        assert exc.value.code == 1


# --- TestCmdFinalize -----------------------------------------------------


class TestCmdFinalize:
    def test_transitions_scored_to_finalized_on_g5_pass(
        self,
        round_dir: Path,
        scored_state: dict[str, Any],
        fake_g5_pass: None,
    ) -> None:
        cmd_finalize("design", str(round_dir), project_dir=None)
        state = load_state(str(round_dir), "design")
        assert state["state"] == "finalized"

    def test_blocks_when_g5_fails(
        self,
        round_dir: Path,
        scored_state: dict[str, Any],
        fake_g5_fail: None,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            cmd_finalize("design", str(round_dir), project_dir=None)
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "blocked"

    def test_refuses_when_state_not_scored(
        self,
        round_dir: Path,
        skills_done_state: dict[str, Any],
        fake_g5_pass: None,
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            cmd_finalize("design", str(round_dir), project_dir=None)
        assert exc.value.code == 1

    def test_blocks_when_marker_missing(
        self,
        round_dir: Path,
        scored_state: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
        fake_g5_pass: None,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Even on G5 PASS, finalize refuses if prerequisite markers are
        missing — they're independent quality gates.
        """
        deps = {"t2-phases": {"design": {"prerequisites": ["shenbi-x"]}}}
        monkeypatch.setattr(phase_runner, "load_deps", lambda: deps)
        with pytest.raises(SystemExit) as exc:
            cmd_finalize("design", str(round_dir), project_dir=None)
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "error"
        assert "G4-shenbi-x-generative" in emitted["missing_marker"]

    def test_records_step_with_g5_status(
        self,
        round_dir: Path,
        scored_state: dict[str, Any],
        fake_g5_pass: None,
    ) -> None:
        cmd_finalize("design", str(round_dir), project_dir=None)
        state = load_state(str(round_dir), "design")
        finalize_steps = [s for s in state["steps"] if s["action"] == "finalize"]
        assert finalize_steps
        assert finalize_steps[-1]["g5_status"] == "PASS"


# --- TestMainCli ---------------------------------------------------------


class TestMainCli:
    def test_exits_when_no_command_given(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["phase-runner"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_exits_when_round_dir_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["phase-runner", "start", "design"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_routes_start_command(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        fake_g5_pass: None,
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            ["phase-runner", "start", "design", "--round-dir", str(round_dir)],
        )
        main()
        state = load_state(str(round_dir), "design")
        assert state["state"] == "started"

    def test_routes_unknown_command_to_error(
        self, monkeypatch: pytest.MonkeyPatch, round_dir: Path
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            ["phase-runner", "bogus", "--round-dir", str(round_dir)],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_routes_pre_skill_command(
        self,
        monkeypatch: pytest.MonkeyPatch,
        round_dir: Path,
        started_state: dict[str, Any],
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            [
                "phase-runner",
                "pre-skill",
                "design",
                "shenbi-x",
                "--round-dir",
                str(round_dir),
            ],
        )
        with pytest.raises(SystemExit):
            # shenbi-x doesn't exist as a real skill — expect error exit
            main()


# --- TestRunGate (smoke) -------------------------------------------------


class TestRunGateSubprocessContract:
    """run_gate shells out to validate-gate.py. Smoke-test that the
    contract holds: valid gate returns dict with status key; invalid
    output falls back to FAIL dict.
    """

    def test_returns_dict_with_status_key_on_valid_json(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _FakeCompleted:
            stdout = json.dumps({"gate": "G5", "status": "PASS"})
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _FakeCompleted())
        result = phase_runner.run_gate("G5", ["arg"])
        assert result["status"] == "PASS"

    def test_returns_fail_dict_on_invalid_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _FakeCompleted:
            stdout = "not json"
            stderr = "error"

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _FakeCompleted())
        result = phase_runner.run_gate("G5", ["arg"])
        assert result["status"] == "FAIL"
        assert result["raw_stdout"] == "not json"


# --- TestPostSkillOutputDiscovery (M5+M8) --------------------------------


class TestPostSkillOutputDiscovery:
    """M5: phase_runner uses derive_output_files instead of rglob.
    M8: G2 file_type comes from derive_file_type instead of hardcoded 'chapter'.
    """

    def test_post_skill_passes_derived_file_type_not_hardcoded_chapter(self, tmp_path, monkeypatch):
        """M8: G2 must receive derive_file_type(skill), not hardcoded 'chapter'."""
        from shenbi.status import PhaseState

        # Setup: a started phase
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        state_dir = round_dir / "phase-state"
        state_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create state file
        state = {"phase": "drafting", "state": PhaseState.STARTED, "steps": []}
        (state_dir / "drafting.json").write_text(json.dumps(state))

        # A real output file so derive_output_files' return survives the
        # exists+size filter and G2 actually runs (otherwise G2 is skipped and
        # there is no file_type to assert on).
        out_file = project_dir / "context.md"
        out_file.write_text("context content", encoding="utf-8")

        # Mock derive_file_type to return 'decisions'
        captured_file_type = []

        def mock_run_gate(gate_name, args):
            if gate_name == "G2":
                captured_file_type.append(args[1])  # file_type is args[1]
                return {"status": "PASS"}
            if gate_name == "G4":
                return {"status": "PASS"}
            return {"status": "PASS"}

        monkeypatch.setattr(phase_runner, "run_gate", mock_run_gate)
        monkeypatch.setattr(
            "shenbi.dispatcher.executor.derive_file_type",
            lambda skill: "decisions",
            raising=True,
        )
        monkeypatch.setattr(
            "shenbi.dispatcher.executor.derive_output_files",
            lambda skill, chapter, rd: [str(out_file)],
            raising=True,
        )

        phase_runner.cmd_post_skill(
            "drafting", "shenbi-context-composing", str(round_dir), str(project_dir)
        )

        # Verify G2 received 'decisions', not 'chapter'
        assert len(captured_file_type) > 0
        assert captured_file_type[0] == "decisions"

    def test_post_skill_uses_derive_output_files_not_rglob(self, tmp_path, monkeypatch):
        """M5: output_files comes from derive_output_files, not rglob.
        When chapter is provided, derive_output_files is the sole source —
        rglob fallback does NOT fire (it only fires when chapter is None).
        """
        from shenbi.status import PhaseState

        round_dir = tmp_path / "round"
        round_dir.mkdir()
        state_dir = round_dir / "phase-state"
        state_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        state = {"phase": "drafting", "state": PhaseState.STARTED, "steps": []}
        (state_dir / "drafting.json").write_text(json.dumps(state))

        # Create a .md file that rglob would find but derive_output_files would NOT
        stray_file = project_dir / "stray.md"
        stray_file.write_text("should not be discovered", encoding="utf-8")

        captured_outputs = []

        def mock_run_gate(gate_name, args):
            if gate_name == "G2":
                captured_outputs.append(args[0])  # file_paths is args[0]
                return {"status": "PASS"}
            if gate_name == "G4":
                return {"status": "PASS"}
            return {"status": "PASS"}

        # derive_output_files returns only contract-declared paths (empty here)
        monkeypatch.setattr(phase_runner, "run_gate", mock_run_gate)
        monkeypatch.setattr(
            "shenbi.dispatcher.executor.derive_output_files",
            lambda skill, chapter, rd: [],
            raising=True,
        )
        monkeypatch.setattr(
            "shenbi.dispatcher.executor.derive_file_type",
            lambda skill: "chapter",
            raising=True,
        )

        # Pass chapter=5 so the rglob fallback does NOT fire.
        # With chapter provided, derive_output_files is the sole source.
        phase_runner.cmd_post_skill(
            "drafting",
            "shenbi-chapter-drafting",
            str(round_dir),
            str(project_dir),
            chapter=5,
        )

        # With empty derive_output_files, G2 should receive empty string (no stray.md)
        if captured_outputs:
            assert "stray.md" not in captured_outputs[0]
