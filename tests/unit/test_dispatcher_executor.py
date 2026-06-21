"""Unit tests for dispatcher/executor.py happy paths."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from shenbi.dispatcher.executor import (
    derive_file_type,
    derive_input_files,
    derive_output_files,
    detect_mode,
    generate_agent_id,
)


@pytest.mark.unit
def test_derive_file_type_returns_chapter_for_drafting() -> None:
    assert derive_file_type("shenbi-chapter-drafting") == "chapter"


@pytest.mark.unit
def test_derive_file_type_returns_truth_for_state_settling() -> None:
    assert derive_file_type("shenbi-state-settling") == "truth"


@pytest.mark.unit
def test_derive_file_type_defaults_to_chapter_for_unknown() -> None:
    assert derive_file_type("shenbi-unknown-skill") == "chapter"


@pytest.mark.unit
def test_derive_files_delegate_to_contract_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    """derive_input_files/derive_output_files delegate to load_contract (no regex)."""
    monkeypatch.setattr(
        "shenbi.dispatcher.executor.load_contract",
        lambda s: {
            "kind": "artifact",
            "reads": ["plans/chapter-N-plan.md"],
            "writes": ["chapters/chapter-N.md"],
            "updates": ["truth/current_state.md"],
        },
    )
    assert derive_input_files("shenbi-x") == ["plans/chapter-N-plan.md"]
    # writes + updates both fold into output files
    assert derive_output_files("shenbi-x") == ["chapters/chapter-N.md", "truth/current_state.md"]


@pytest.mark.unit
def test_derive_files_empty_when_skill_has_no_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    """A skill outside the contract system (meta skill) raises ContractError -> []."""
    from shenbi.contract import ContractError

    def raise_contract_error(_skill: str) -> None:
        raise ContractError("no contract")

    monkeypatch.setattr("shenbi.dispatcher.executor.load_contract", raise_contract_error)
    assert derive_input_files("using-shenbi") == []
    assert derive_output_files("using-shenbi") == []


@pytest.mark.unit
def test_generate_agent_id_is_unique() -> None:
    round_dir = Path("/tmp/round-001")
    id1 = generate_agent_id(round_dir, "skill-x", "generative")
    id2 = generate_agent_id(round_dir, "skill-x", "generative")
    assert id1 != id2
    assert "skill-x" in id1
    assert "generative" in id1


@pytest.mark.unit
def test_generate_agent_id_contains_round_dir_name() -> None:
    round_dir = Path("/tmp/round-042")
    agent_id = generate_agent_id(round_dir, "skill-y", "discriminating")
    assert "round-042" in agent_id


@pytest.mark.unit
def test_detect_mode_returns_codex_when_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """detect_mode returns 'codex' when shutil.which('codex') finds it."""
    monkeypatch.setattr(
        shutil, "which", lambda cmd: "/usr/local/bin/codex" if cmd == "codex" else None
    )
    assert detect_mode() == "codex"


@pytest.mark.unit
def test_detect_mode_returns_codex_api_with_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """detect_mode returns 'codex-api' when CODEX_API_KEY env var is set."""
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    monkeypatch.setenv("CODEX_API_KEY", "sk-test-key")
    # Re-import to pick up monkeypatched env
    from shenbi.dispatcher.executor import detect_mode as dm

    assert dm() == "codex-api"


@pytest.mark.unit
def test_detect_mode_returns_internal_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """detect_mode returns 'internal' when neither codex nor env var is available."""
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    monkeypatch.delenv("CODEX_API_KEY", raising=False)
    from shenbi.dispatcher.executor import detect_mode as dm

    assert dm() == "internal"


@pytest.mark.unit
def test_run_g1_returns_parsed_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_g1 parses subprocess stdout JSON into a dict."""
    import subprocess

    def mock_run(*a, **kw):
        return type("R", (), {"stdout": '{"status": "PASS"}'})()

    monkeypatch.setattr(subprocess, "run", mock_run)
    from shenbi.dispatcher.executor import run_g1

    result = run_g1("skill-x", [], Path("/tmp"))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_run_g2_returns_parsed_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_g2 parses subprocess stdout JSON into a dict."""
    import subprocess

    def mock_run(*a, **kw):
        return type("R", (), {"stdout": '{"status": "PASS"}'})()

    monkeypatch.setattr(subprocess, "run", mock_run)
    from shenbi.dispatcher.executor import run_g2

    result = run_g2(["out.md"], "chapter", Path("/tmp"))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_dispatch_returns_0_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dispatch returns 0 when all gates pass and internal mode succeeds."""
    import subprocess
    from pathlib import Path

    def mock_run(*a, **kw):
        return type("R", (), {"stdout": '{"status": "PASS"}'})()

    monkeypatch.setattr(subprocess, "run", mock_run)

    import shenbi.dispatcher.executor as exec_mod
    from shenbi.dispatcher.executor import dispatch

    monkeypatch.setattr(exec_mod, "detect_mode", lambda: "internal")

    import shenbi.dispatcher.modes.internal as internal_mod

    monkeypatch.setattr(internal_mod, "dispatch_internal", lambda *a, **kw: 0)

    result = dispatch("shenbi-worldbuilding", "generative", Path("/tmp/round-001"), "test")
    assert result == 0


@pytest.mark.unit
def test_dispatch_routes_to_codex_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dispatch routes to codex-api mode when detect_mode returns 'codex-api'."""
    import subprocess
    from pathlib import Path

    import shenbi.dispatcher.executor as exec_mod
    import shenbi.dispatcher.modes.codex_api as codex_api_mod

    def mock_run(*a, **kw):
        return type("R", (), {"stdout": '{"status": "PASS"}'})()

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(exec_mod, "detect_mode", lambda: "codex-api")
    monkeypatch.setattr(codex_api_mod, "dispatch_codex_api", lambda *a, **kw: 0)

    from shenbi.dispatcher.executor import dispatch

    result = dispatch("shenbi-worldbuilding", "generative", Path("/tmp/round-001"), "test")
    assert result == 0
