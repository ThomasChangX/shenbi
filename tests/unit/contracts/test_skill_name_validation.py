"""T12-06 (spec #22 R3): skill-name lexical validation shared by all three
path join points (dispatch_helper / contracts.legacy._skill_path /
phase_runner) + plugins/generate.py output containment.
"""

from pathlib import Path

import pytest

from shenbi.contracts.legacy import ContractError, validate_skill_name

BAD = ["../escape", "a/b", "/abs/skill", "", "UPPER", "shenbi x", "shenbi/../shenbi", "."]
GOOD = ["shenbi-worldbuilding", "using-shenbi", "a", "shenbi-2nd"]


@pytest.mark.parametrize("bad", BAD)
def test_rejects_bad_names(bad: str) -> None:
    with pytest.raises(ContractError):
        validate_skill_name(bad)


@pytest.mark.parametrize("good", GOOD)
def test_accepts_good_names(good: str) -> None:
    assert validate_skill_name(good) == good


def test_all_repo_skills_pass() -> None:
    skills_dir = Path(__file__).resolve().parents[3] / "skills"
    for d in skills_dir.iterdir():
        if d.is_dir():
            validate_skill_name(d.name)  # must not raise


def test_generate_output_containment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # minimal master: load_master is monkeypatched so its internal validation
    # never runs; the containment check fires before gen_codex needs real fields
    import shenbi.plugins.generate as gen

    master = {"platforms": {"evil": {"format": "codex-cli", "output": "../../etc/pwned.json"}}}
    monkeypatch.setattr(gen, "load_master", lambda: master)
    with pytest.raises(ValueError):
        gen.generate_all()
