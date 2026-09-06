"""Child-process environment whitelist — T1207 (spec #45 R4).

Dispatch-spawned subprocesses (codex exec / uv run) receive an explicit
allowlisted environment instead of a full ``os.environ`` copy, so secrets
like ``SHENBI_LLM_API_KEY`` never reach workspace-write LLM subprocesses.
Two faces are defined: ``codex`` (codex exec CLI) and ``uv`` (uv run of
framework entry points — needs UV_*/PYTHON* too). ``SHENBI_ENV_PASSTHROUGH``
(colon-separated) is the operator escape hatch; explicitly named variables
are passed through even when secret-named (the naming is the intent), with
an INFO log for auditability. See docs/framework/env-policy.md.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

import structlog

log = structlog.get_logger(__name__)

# Variables whose NAME marks them as a secret — never passed through implicitly.
_SECRET_NAME_RE = re.compile(r"KEY|TOKEN|SECRET|PASSWORD", re.IGNORECASE)

# Exact names allowed on every face.
_COMMON_EXACT = frozenset(
    {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TERM",
        "TMPDIR",
        "CODEX_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "NO_PROXY",
        "https_proxy",
        "http_proxy",
        "no_proxy",
    }
)

# Prefixes allowed on every face (secrets excluded by name above).
_COMMON_PREFIXES = ("SHENBI_",)

_UV_EXTRA_EXACT = frozenset({"VIRTUAL_ENV", "PYTHONDONTWRITEBYTECODE"})
_UV_EXTRA_PREFIXES = ("UV_", "PYTHON")


def _is_secret_name(name: str) -> bool:
    return _SECRET_NAME_RE.search(name) is not None


def build_child_env(
    face: str,
    parent: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the allowlisted child environment for *face* ('codex' | 'uv').

    SHENBI_* variables pass through unless secret-named (e.g.
    SHENBI_LLM_API_KEY). SHENBI_ENV_PASSTHROUGH names are added verbatim
    (explicit operator intent) with an INFO log.
    """
    if face not in ("codex", "uv"):
        raise ValueError(f"unknown env-policy face: {face!r}")
    environ = dict(os.environ if parent is None else parent)
    env: dict[str, str] = {}
    prefixes = _COMMON_PREFIXES + (_UV_EXTRA_PREFIXES if face == "uv" else ())
    exact = _COMMON_EXACT | (_UV_EXTRA_EXACT if face == "uv" else frozenset())
    for name, value in environ.items():
        if name in exact or (name.startswith(prefixes) and not _is_secret_name(name)):
            env[name] = value
    passthrough = environ.get("SHENBI_ENV_PASSTHROUGH", "")
    for name in (p.strip() for p in passthrough.split(":")):
        if name and name in environ and name not in env:
            env[name] = environ[name]
            log.info("env_passthrough_explicit", variable=name)
    return env


_SECRET_VALUE_SUBS: tuple[tuple[re.Pattern[str], str], ...] = (
    # OAuth URL one-time parameters (keep the param name, mask the value)
    (re.compile(r"(state|nonce|code_challenge|code)=[^&\s]+"), r"\1=***"),
    # API keys / bearer tokens
    (re.compile(r"sk-[A-Za-z0-9_-]+"), "sk-***"),
    (re.compile(r"Bearer\s+\S+"), "Bearer ***"),
)


def redact(text: str) -> str:
    """F1161 (spec #45 R4): mask secrets in log-bound text."""
    out = text
    for pattern, repl in _SECRET_VALUE_SUBS:
        out = pattern.sub(repl, out)
    return out
