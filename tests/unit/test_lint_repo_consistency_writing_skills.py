"""Spec #90 T4: writing-skills machine-contract section face, red on missing."""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
LINT = REPO / "tools" / "lint_repo_consistency.py"


def _load_lint():
    spec = importlib.util.spec_from_file_location("lrc", LINT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_face_green_on_current_tree() -> None:
    mod = _load_lint()
    assert mod.find_missing_machine_contract_section(REPO) == []


def test_face_red_on_missing_section(tmp_path) -> None:
    mod = _load_lint()
    fake = tmp_path / "skills" / "shenbi-writing-skills"
    fake.mkdir(parents=True)
    fake.joinpath("SKILL.md").write_text("# writing skills\n\n(no section)\n", encoding="utf-8")
    assert mod.find_missing_machine_contract_section(tmp_path) == [
        "writing-skills: machine-contract section missing (spec #90)"
    ]
