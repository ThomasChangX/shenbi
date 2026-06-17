"""Unit tests for dispatcher/executor.py happy paths."""

from __future__ import annotations

import os
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
def test_derive_input_files_returns_reads_from_skill_md() -> None:
    """Existing skill shenbi-worldbuilding has Reads: section."""
    files = derive_input_files("shenbi-worldbuilding")
    assert isinstance(files, list)


@pytest.mark.unit
def test_derive_input_files_empty_for_missing_skill() -> None:
    assert derive_input_files("shenbi-nonexistent-skill-xyz") == []


@pytest.mark.unit
def test_derive_output_files_returns_writes_and_updates() -> None:
    files = derive_output_files("shenbi-worldbuilding")
    assert isinstance(files, list)


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
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/local/bin/codex" if cmd == "codex" else None)
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
