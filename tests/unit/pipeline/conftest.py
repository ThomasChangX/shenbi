"""Shared fixtures for pipeline tests."""

from __future__ import annotations

from pathlib import Path

import pytest


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
