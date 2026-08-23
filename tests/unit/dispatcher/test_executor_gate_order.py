"""F227: G2 must not validate outputs before skill execution."""

from pathlib import Path
from unittest.mock import patch

from shenbi.dispatcher import executor


def test_g2_runs_after_dispatch_on_fresh_round(tmp_path: Path) -> None:
    calls: list[str] = []
    rd = tmp_path / "round"
    rd.mkdir()

    def fake_dispatch(skill, test_type, round_dir, prompt, agent_id):
        calls.append("dispatch")
        return 0

    with (
        patch("shenbi.dispatcher.modes.internal.dispatch_internal", fake_dispatch),
        patch.object(
            executor, "run_g2", lambda *a, **k: (calls.append("g2"), {"status": "PASS"})[1]
        ),
        patch.object(executor, "run_g1", lambda *a, **k: {"status": "PASS"}),
        patch.object(executor, "detect_mode", lambda: "internal"),
    ):
        rc = executor.dispatch("shenbi-worldbuilding", "generative", rd, "prompt")
    assert rc == 0
    # fresh round: no pre-existing outputs → G2 must run AFTER dispatch
    assert calls == ["dispatch", "g2"]


def test_preexisting_outputs_still_g2_checked(tmp_path: Path) -> None:
    """Re-entry semantics: already-present outputs are G2-checked (post-dispatch
    in the new order — behavior preserved, position moved).
    """
    calls: list[str] = []
    rd = tmp_path / "round"
    rd.mkdir()
    # pre-create one expected output so `preexisting` is non-empty
    out = rd / "skill-output" / "world.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("{}", encoding="utf-8")

    def fake_dispatch(skill, test_type, round_dir, prompt, agent_id):
        calls.append("dispatch")
        return 0

    with (
        patch("shenbi.dispatcher.modes.internal.dispatch_internal", fake_dispatch),
        patch.object(
            executor, "run_g2", lambda *a, **k: (calls.append("g2"), {"status": "PASS"})[1]
        ),
        patch.object(executor, "run_g1", lambda *a, **k: {"status": "PASS"}),
        patch.object(executor, "detect_mode", lambda: "internal"),
    ):
        rc = executor.dispatch("shenbi-worldbuilding", "generative", rd, "prompt")
    assert rc == 0
    assert calls == ["dispatch", "g2"]


def test_g2_failure_returns_nonzero(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()

    def fake_dispatch(skill, test_type, round_dir, prompt, agent_id):
        # produce the output so post-dispatch G2 has something to check
        o = rd / "skill-output" / "world.json"
        o.parent.mkdir(parents=True, exist_ok=True)
        o.write_text("{}", encoding="utf-8")
        return 0

    with (
        patch("shenbi.dispatcher.modes.internal.dispatch_internal", fake_dispatch),
        patch.object(executor, "run_g2", lambda *a, **k: {"status": "FAIL"}),
        patch.object(executor, "run_g1", lambda *a, **k: {"status": "PASS"}),
        patch.object(executor, "detect_mode", lambda: "internal"),
    ):
        rc = executor.dispatch("shenbi-worldbuilding", "generative", rd, "prompt")
    assert rc == 1
