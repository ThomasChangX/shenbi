"""T1 tests for cli_utils output channels (spec #50 / C36)."""

import json

import pytest

from shenbi.cli_utils import echo, emit_json


def test_echo_writes_stdout_with_newline(capsys):
    echo("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
    assert captured.err == ""


def test_echo_err_writes_stderr(capsys):
    echo("boom", err=True)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "boom\n"


def test_emit_json_non_escaped_utf8(capsys):
    emit_json([{"detail": "中文"}])
    captured = capsys.readouterr()
    assert captured.out == json.dumps([{"detail": "中文"}], ensure_ascii=False) + "\n"


def test_echo_broken_pipe_exits_clean(monkeypatch):
    import sys

    class _Closed:
        def write(self, _):
            raise BrokenPipeError

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", _Closed())
    with pytest.raises(SystemExit) as exc:
        echo("x")
    assert exc.value.code == 0
