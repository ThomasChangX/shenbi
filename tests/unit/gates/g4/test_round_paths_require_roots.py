"""Spec #89 T3: RoundPaths.require_roots collapses the 11-checker preamble."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.paths import RoundPaths


@pytest.mark.unit
def test_require_roots_raises_the_pinned_string() -> None:
    with pytest.raises(ValueError, match="round_dir or project_dir required"):
        RoundPaths.require_roots(None, None, Path("."))


@pytest.mark.unit
def test_require_roots_mutual_defaults() -> None:
    rp = RoundPaths.require_roots("/tmp/rd", None, "/repo")
    assert rp.round_dir == Path("/tmp/rd") and rp.project_dir == Path("/tmp/rd")
    rp2 = RoundPaths.require_roots(None, "/proj", "/repo")
    assert rp2.project_dir == Path("/proj") and rp2.round_dir == Path("/proj")


@pytest.mark.unit
def test_require_roots_explicit_both() -> None:
    rp = RoundPaths.require_roots("/tmp/rd", "/proj", "/repo")
    assert rp.round_dir == Path("/tmp/rd")
    assert rp.project_dir == Path("/proj")
    assert rp.repo_root == Path("/repo")
