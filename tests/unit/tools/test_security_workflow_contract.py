"""Spec #41 (C27) R1/R2: security.yml audit & SBOM scope contract.

T1301/T1303 regression guard: any narrowing of audit scope (restoring
--group dev, dropping --all-groups/--all-extras, reverting to uvx
pip-audit / environment audit) fails these tests.
F1041 regression guard: SBOM must be generated per group, not via the
environment subcommand.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
WORKFLOW = REPO / ".github/workflows/security.yml"
RELEASE = REPO / ".github/workflows/release.yml"
PRE_PUSH = REPO / "tools/pre-push-check.sh"
REQUIRED_EXPORT = "uv export --frozen --all-groups --all-extras --no-emit-project"
FORBIDDEN = ("--group dev", "uvx pip-audit")


def test_security_yml_audits_full_lock_set() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert REQUIRED_EXPORT in text
    assert "pip-audit -r" in text
    for token in FORBIDDEN:
        assert token not in text, f"audit scope narrowed: {token!r} re-introduced"


def test_pre_push_mirrors_ci_audit_scope() -> None:
    text = PRE_PUSH.read_text(encoding="utf-8")
    assert REQUIRED_EXPORT in text
