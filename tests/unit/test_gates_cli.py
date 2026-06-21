"""Tests for the shenbi-validate CLI dispatcher (gates/cli.py main()).

Exercises every gate-dispatch branch plus the usage/unknown-gate paths by
invoking main() with mocked argv and captured stdout.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from shenbi.gates.cli import main


def _run(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> tuple[int, str]:
    monkeypatch.setattr(sys, "argv", ["shenbi-validate", *argv])
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    rc = main()
    return rc, out.getvalue()


@pytest.mark.unit
def test_no_args_prints_usage_and_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Usage is emitted via structlog (stderr); we assert the early-return rc only.
    rc, _ = _run([], monkeypatch)
    assert rc == 1


@pytest.mark.unit
def test_unknown_gate_returns_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(["BOGUS"], monkeypatch)
    assert rc == 1


@pytest.mark.unit
def test_g0_dispatch_emits_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out = _run(["G0"], monkeypatch)
    assert rc == 0
    assert json.loads(out)["gate"] == "G0"


@pytest.mark.unit
def test_g1_dispatch_invalid_files_json_falls_back_to_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # "{bad" is not valid JSON -> except branch -> input_files=[]
    rc, out = _run(["G1", "shenbi-worldbuilding", "{bad"], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g2_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = tmp_path / "x.md"
    f.write_text("# x\n", encoding="utf-8")
    rc, out = _run(["G2", str(f), "report"], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g3_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out = _run(["G3", "shenbi-worldbuilding", "generative", str(tmp_path)], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g4_generative_dispatch_with_shorthand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "novel.json"
    f.write_text('{"title": "T"}', encoding="utf-8")
    rc, out = _run(["G4", "worldbuilding", str(f)], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g4_bughunt_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out = _run(["G4", "bughunt"], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g4_clean_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out = _run(["G4", "clean"], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g5_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    rc, out = _run(["G5", "genesis", str(rd)], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g6_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    rc, out = _run(["G6", "long-form", str(rd)], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g7_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    rc, out = _run(["G7", str(rd)], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g_transition_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    rc, out = _run(["G_TRANSITION", "drafting", "review", str(rd)], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g_dispatch_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    rc, out = _run(["G_DISPATCH", "drafting", str(rd)], monkeypatch)
    assert rc == 0
    json.loads(out)


@pytest.mark.unit
def test_g_reconcile_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    rc, out = _run(["G_RECONCILE", str(rd)], monkeypatch)
    assert rc == 0
    json.loads(out)
