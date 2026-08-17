"""Shared fixtures for pipeline tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shenbi.pipeline.crash_recovery import reset_emergency_state


@pytest.fixture(autouse=True)
def _reset_crash_recovery_state() -> Any:
    """Reset module-level crash-recovery globals around every pipeline unit test.

    Signal-handler tests (tests/pipeline/test_crash_recovery.py et al.) set
    ``_shutdown_requested`` via ``_handle_emergency_signal``; their per-file
    autouse fixtures only reset on setup, so the flag leaks to whatever test
    runs next in the same xdist worker. ``run_chapter_step`` then returns
    early at the shutdown check and the audit waves never dispatch (observed
    as PR-CI order flake: "parallel wave must have run" with seed 1194147792).
    Resetting both before and after each test closes the leak for every file
    in this package, present and future.
    """
    reset_emergency_state()
    yield
    reset_emergency_state()


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Temporary novel project directory."""
    project = tmp_path / "novel-project"
    project.mkdir()
    return project


@pytest.fixture
def sample_seed_content() -> str:
    """Minimal seed file content matching outline-example.md format."""
    return """# Test Novel

## Basic Info
- Genre: fantasy, adventure
- Era: medieval
- Core concept: A test novel
- Target word count: 200000
- Ending direction: Happy ending

## Protagonist
- Name: Test Hero
- Personality: brave, curious

## World Rules
- Rule 1: Magic exists
- Rule 2: Dragons are real

## Core Conflict
- Surface: Kingdom at war
- Personal: Hero seeks revenge
- Deep: Freedom vs duty

## Three-Act Structure
- Act 1: Hero discovers powers
- Act 2: Hero trains and fights
- Act 3: Hero saves kingdom

## Narrative Techniques
- Show/Tell ratio: 70/30
- Deep themes: courage, sacrifice
"""
