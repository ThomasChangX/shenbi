"""spec #71 T8: drafting temperature single-arm change (0.85 -> 0.90)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_drafting_temperature_is_090() -> None:
    cfg = tomllib.loads((_REPO_ROOT / "executor_config.toml").read_text(encoding="utf-8"))
    assert cfg["overrides"]["shenbi-chapter-drafting"]["temperature"] == 0.90
