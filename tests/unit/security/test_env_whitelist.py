"""T1207/F1161 (spec #45 R4): env whitelist for dispatch subprocesses and
secret redaction in framework logs.
"""

import pytest

from shenbi.env_policy import build_child_env, redact


def test_codex_face_whitelist_drops_secrets():
    env = build_child_env(
        "codex",
        {
            "PATH": "/bin",
            "SHENBI_LLM_API_KEY": "sk-x",
            "OPENAI_API_KEY": "k",
            "OPENAI_BASE_URL": "u",
            "SHENBI_LOG_FORMAT": "json",
            "SNEAKY": "nope",
        },
    )
    assert env["PATH"] == "/bin"
    assert env["OPENAI_BASE_URL"] == "u"
    assert env["SHENBI_LOG_FORMAT"] == "json"
    assert "SHENBI_LLM_API_KEY" not in env
    assert "OPENAI_API_KEY" not in env
    assert "SNEAKY" not in env


def test_uv_face_adds_uv_python():
    env = build_child_env("uv", {"PATH": "/bin", "UV_PROJECT_ENVIRONMENT": "/x", "PYTHONPATH": "y"})
    assert env["UV_PROJECT_ENVIRONMENT"] == "/x"
    assert env["PYTHONPATH"] == "y"


def test_passthrough_escape_hatch():
    env = build_child_env(
        "codex",
        {"PATH": "/bin", "MY_TOOL_TOKEN": "t", "SHENBI_ENV_PASSTHROUGH": "MY_TOOL_TOKEN"},
    )
    assert env["MY_TOOL_TOKEN"] == "t"


def test_unknown_face_rejected():
    with pytest.raises(ValueError):
        build_child_env("shell", {"PATH": "/bin"})


def test_wiring_codex_exec_spawn_uses_whitelist(monkeypatch, tmp_path):
    """Wiring: _codex_exec_scores passes an allowlisted env to codex exec."""
    import json

    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured.update(kwargs)
        raw = tmp_path / "scores.raw"
        raw.write_text(json.dumps({"final_score": 90}), encoding="utf-8")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setenv("SHENBI_LLM_API_KEY", "sk-secret")
    monkeypatch.setattr("shenbi.dispatcher.modes.codex.subprocess.run", fake_run)

    from shenbi.dispatcher.modes.codex import _codex_exec_scores

    out = tmp_path / "scores.json"
    _codex_exec_scores(tmp_path, "prompt", out, "skill-x")
    env = captured["env"]
    assert isinstance(env, dict)
    assert "SHENBI_LLM_API_KEY" not in env


def test_redact_processor_in_logging_pipeline(capsys):
    """F1161: structlog events are redacted end-to-end."""
    from shenbi.logging import configure_logging, get_logger

    configure_logging()
    get_logger("sec-test").warning(
        "oauth residue", url="https://x?state=abc123&code_challenge=zz", token="sk-abc123"
    )
    err = capsys.readouterr().err
    assert "abc123" not in err and "sk-abc123" not in err
    assert "state=***" in err and "sk-***" in err


def test_redact_masks_all_secret_shapes():
    text = "url?state=abc&code_challenge=x y sk-abc123 Bearer tok99"
    out = redact(text)
    assert "abc" not in out and "sk-abc123" not in out and "tok99" not in out
    assert "state=***" in out and "code_challenge=***" in out
    assert "sk-***" in out and "Bearer ***" in out
