"""tools/align_precommit_lock.py: hook revs and uv.lock stay aligned (spec #97)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import align_precommit_lock as tool

REPO = Path(__file__).resolve().parents[3]

_CONFIG = """\
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.17.6
    hooks:
      - id: ruff
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v2.4.1
    hooks:
      - id: mypy
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.11.0.1-1
    hooks:
      - id: shellcheck
  - repo: local
"""


def _lock(ruff: str) -> str:
    return (
        '[[package]]\nname = "ruff"\nversion = "' + ruff + '"\n\n'
        '[[package]]\nname = "mypy"\nversion = "2.4.1"\n\n'
        '[[package]]\nname = "shellcheck-py"\nversion = "0.11.0.1"\n'
    )


def test_hook_revs_drop_the_v_and_a_packaging_suffix() -> None:
    assert tool.hook_revs(_CONFIG) == {
        "ruff": "0.17.6",
        "mypy": "2.4.1",
        "shellcheck-py": "0.11.0.1",
    }


def test_locked_versions_read_the_package_blocks() -> None:
    assert tool.locked_versions(_lock("0.17.5")) == {
        "ruff": "0.17.5",
        "mypy": "2.4.1",
        "shellcheck-py": "0.11.0.1",
    }


def test_mismatches_name_only_the_hook_that_moved() -> None:
    assert tool.mismatches(_CONFIG, _lock("0.17.5")) == [("ruff", "0.17.6")]


def test_aligned_tree_has_nothing_to_do() -> None:
    assert tool.mismatches(_CONFIG, _lock("0.17.6")) == []


def test_hook_missing_from_the_lock_counts_as_moved() -> None:
    lock = _lock("0.17.6").replace('[[package]]\nname = "ruff"\nversion = "0.17.6"\n\n', "")

    assert tool.mismatches(_CONFIG, lock) == [("ruff", "0.17.6")]


def test_repo_hooks_and_lock_are_aligned() -> None:
    """The drift gate: a hook bump that skips uv.lock fails here (spec #97)."""
    config = (REPO / ".pre-commit-config.yaml").read_text("utf-8")
    lock = (REPO / "uv.lock").read_text("utf-8")

    assert tool.mismatches(config, lock) == []


def test_main_pins_each_moved_hook(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text(_CONFIG, "utf-8")
    (tmp_path / "uv.lock").write_text(_lock("0.17.5"), "utf-8")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path, check: bool) -> SimpleNamespace:
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(tool, "REPO", tmp_path)
    monkeypatch.setattr(tool.subprocess, "run", fake_run)

    assert tool.main() == 0
    assert calls == [["uv", "lock", "--upgrade-package", "ruff==0.17.6"]]


def test_main_fails_when_a_pin_cannot_be_resolved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text(_CONFIG, "utf-8")
    (tmp_path / "uv.lock").write_text(_lock("0.17.5"), "utf-8")
    monkeypatch.setattr(tool, "REPO", tmp_path)
    monkeypatch.setattr(
        tool.subprocess, "run", lambda cmd, cwd, check: SimpleNamespace(returncode=1)
    )

    assert tool.main() == 1
