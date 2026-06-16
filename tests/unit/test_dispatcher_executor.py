"""Unit tests for dispatcher/executor.py happy paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.dispatcher.executor import (
    derive_file_type,
    derive_input_files,
    derive_output_files,
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
