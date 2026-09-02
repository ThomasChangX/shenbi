"""Unit tests for dispatcher fallback modes (internal + codex_api)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.dispatcher.modes.codex_api import dispatch_codex_api
from shenbi.dispatcher.modes.internal import dispatch_internal
from shenbi.exceptions import DispatcherError


@pytest.mark.unit
def test_dispatch_internal_raises_dispatcher_error(tmp_path: Path) -> None:
    """dispatch_internal hard-rejects because internal mode has no LLM backend.

    Covers dispatcher/modes/internal.py:16-19 (the raise path).
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    with pytest.raises(DispatcherError, match="internal mode has no LLM backend"):
        dispatch_internal(
            "shenbi-worldbuilding", "generative", round_dir, "complete the task", "agent-1"
        )


@pytest.mark.unit
def test_dispatch_codex_api_raises_dispatcher_error() -> None:
    """codex-api mode is unimplemented and raises DispatcherError (covers codex_api.py:15)."""
    with pytest.raises(DispatcherError):
        dispatch_codex_api()


@pytest.mark.c13_regression
def test_internal_error_message_no_misleading_env_var() -> None:
    """F219: the internal-mode rejection must not point at the never-read
    SHENBI_LLM_API_KEY env var.
    """
    from shenbi.dispatcher.modes.internal import dispatch_internal

    with pytest.raises(DispatcherError, match="codex CLI") as exc:
        dispatch_internal("shenbi-x", "generative", Path("/tmp"), "p", "a")
    assert "SHENBI_LLM_API_KEY" not in str(exc.value)


@pytest.mark.c13_regression
def test_codex_raw_scratch_removed_after_parse(monkeypatch, tmp_path) -> None:
    """F218: the .raw scratch file is removed once parsed (also on error)."""
    import subprocess as subprocess_mod

    import shenbi.dispatcher.modes.codex as codex_mod

    class _R:  # minimal subprocess result stub
        returncode = 0
        stderr = ""

    def _fake_run(cmd: list[str], **k: object) -> _R:
        # codex exec writes its raw output to the -o path
        Path(cmd[cmd.index("-o") + 1]).write_text('{"1": 90}', encoding="utf-8")
        return _R()

    monkeypatch.setattr(subprocess_mod, "run", _fake_run)
    out_file = tmp_path / "t1-reports" / "shenbi-x-scores.json"
    result = codex_mod._codex_exec_scores(tmp_path, "prompt", out_file, "shenbi-x")
    assert result == {"1": 90}
    assert not out_file.with_suffix(".raw").exists()


@pytest.mark.c13_regression
def test_codex_raw_scratch_removed_on_parse_error(monkeypatch, tmp_path) -> None:
    """F218: the finally-unlink also fires when JSON extraction fails."""
    import subprocess as subprocess_mod

    import shenbi.dispatcher.modes.codex as codex_mod
    from shenbi.exceptions import SubAgentProtocolError

    class _R:
        returncode = 0
        stderr = ""

    def _fake_run(cmd: list[str], **k: object) -> _R:
        Path(cmd[cmd.index("-o") + 1]).write_text("not json at all", encoding="utf-8")
        return _R()

    monkeypatch.setattr(subprocess_mod, "run", _fake_run)
    out_file = tmp_path / "t1-reports" / "shenbi-x-scores.json"
    with pytest.raises(SubAgentProtocolError):
        codex_mod._codex_exec_scores(tmp_path, "prompt", out_file, "shenbi-x")
    assert not out_file.with_suffix(".raw").exists()
