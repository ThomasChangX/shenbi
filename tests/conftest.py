"""Pytest global fixtures and configuration."""

import os
from pathlib import Path
from typing import Any

import pytest
import structlog
from hypothesis import settings

settings.register_profile("ci", max_examples=1000, deadline=None)
settings.register_profile("dev", max_examples=100, deadline=200)
settings.register_profile("debug", max_examples=10, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


@pytest.fixture(autouse=True)
def _isolate_structlog_config() -> Any:
    """Snapshot and restore global structlog config around every test.

    shenbi.logging.configure_logging() (called by gates/cli.py and
    dispatcher/cli.py main(), and directly by some tests) mutates the global
    structlog config: it rebinds the PrintLogger to the current sys.stderr
    with cache_logger_on_first_use=True. If a test triggers this and pytest
    later closes that capture stream, any subsequent log.* call in another
    test raises ``ValueError: I/O operation on closed file`` (observed as
    flaky compute_score weight_mismatch failures under xdist). Restoring the
    config at teardown ensures no test can leak a stale/closed logger.
    """
    original_config = structlog.get_config()
    yield
    structlog.configure(**original_config)


@pytest.fixture
def tmp_project_dir(tmp_path: Path) -> Path:
    """Temporary project directory for test isolation."""
    project = tmp_path / "project"
    project.mkdir()
    return project


@pytest.fixture
def sample_worldbuilding_output(tmp_project_dir: Path) -> Path:
    """Minimal worldbuilding output for testing downstream skills."""
    base = tmp_project_dir
    (base / "novel.json").write_text(
        '{"title": "Test", "genre": ["test"], "language": "zh", "target_words": 100000}'
    )
    (base / "world").mkdir()
    (base / "world" / "story_bible.md").write_text("# Bible\n## A\nx\n## B\nx\n## C\nx\n## D\nx\n")
    return base
