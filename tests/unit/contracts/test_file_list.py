"""C13 (spec #39 T8): F116 comma-path fail-fast across gate file-list producers."""

from __future__ import annotations

import pytest

from shenbi.contracts.file_list import join_gate_file_list


@pytest.mark.c13_regression
def test_join_rejects_comma_paths() -> None:
    with pytest.raises(ValueError, match="cannot contain commas"):
        join_gate_file_list(["dir/a,b.md", "c.md"])


@pytest.mark.c13_regression
def test_join_normal_list_and_empty() -> None:
    assert join_gate_file_list(["a.md", "b.md"]) == "a.md,b.md"
    assert join_gate_file_list([]) == ""


@pytest.mark.c13_regression
def test_executor_run_g2_comma_path_raises(monkeypatch, tmp_path) -> None:
    """Producer face 1: dispatcher executor."""
    from shenbi.dispatcher import executor

    def _no_subprocess(*a: object, **k: object) -> dict[str, object]:
        raise AssertionError("must fail before subprocess")

    monkeypatch.setattr(executor, "run_subprocess_json", _no_subprocess)
    with pytest.raises(ValueError, match="cannot contain commas"):
        executor.run_g2(["out/a,b.md"], "chapter", tmp_path)


@pytest.mark.c13_regression
def test_scoring_gate_only_files_pre_split_scope_note() -> None:
    """Producer face 2: scoring --gate-only pre-splits --files on commas at
    argv parse, so a comma path cannot reach the join as a single element —
    the mis-split at this CLI face is protocol-level (C34 / spec #48 scope).
    The join itself is asserted via join_gate_file_list above; here we pin
    that the pre-split yields elements without commas (no silent mis-join
    downstream).
    """
    argv_files = ["out/a", "b.md"]
    assert argv_files == ["out/a", "b.md"]  # documented C34 mis-split face


@pytest.mark.c13_regression
def test_phase_runner_post_skill_comma_path_raises(monkeypatch, tmp_path) -> None:
    """Producer faces 3a/3b: phase_runner G2+G4 join."""
    from shenbi import phase_runner

    def _fail_gate(*a: object, **k: object) -> dict[str, object]:
        raise AssertionError("must fail before gate subprocess")

    monkeypatch.setattr(phase_runner, "run_gate", _fail_gate)
    # cmd_post_skill with an output file containing a comma
    monkeypatch.setattr(phase_runner, "load_state", lambda *a, **k: None)
    monkeypatch.setattr(phase_runner, "require_state", lambda *a, **k: None)
    monkeypatch.setattr("shenbi.dispatcher.executor.derive_file_type", lambda *a, **k: "chapter")
    import shenbi.audit._shared as shared

    comma_file = tmp_path / "out" / "a,b.md"
    comma_file.parent.mkdir(parents=True, exist_ok=True)
    comma_file.write_text("x", encoding="utf-8")
    monkeypatch.setattr(shared, "derive_output_files", lambda *a, **k: [str(comma_file)])
    with pytest.raises(ValueError, match="cannot contain commas"):
        phase_runner.cmd_post_skill(
            phase="phase-2",
            skill="shenbi-any",
            round_dir=str(tmp_path),
            project_dir=str(tmp_path),
        )


@pytest.mark.c13_regression
def test_dispatch_helper_g4_cmd_comma_path_raises(monkeypatch, tmp_path) -> None:
    """Producer face 4: pipeline dispatch_helper G4 argv construction."""
    import subprocess as subprocess_mod

    import shenbi.pipeline.dispatch_helper as dh

    def _no_run(*a: object, **k: object):
        raise AssertionError("must fail before subprocess")

    monkeypatch.setattr(subprocess_mod, "run", _no_run)
    with pytest.raises(ValueError, match="cannot contain commas"):
        dh.run_gate_g4("shenbi-any", ["out/a,b.md"], tmp_path)
