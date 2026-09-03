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


def test_sbom_layered_per_group() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for group in ("prod", "dev", "docs"):
        assert f"sbom-{group}.cdx.json" in text
    # 分组 sync 是分层的事实载体（F1041 修复本质）；environment 子命令带许可证元数据
    assert "uv sync --frozen --no-dev --all-extras" in text
    assert "uv sync --frozen --only-group dev" in text
    assert "uv sync --frozen --only-group docs" in text
    assert "cyclonedx-py environment" in text
    assert "cyclonedx-py requirements" not in text  # requirements 产物无许可证元数据
    # R2+R3 执法接线：check_licenses 必须消费三份分组 SBOM（dead-wire 守卫）
    assert "tools/check_licenses.py" in text


def test_release_uploads_three_group_sboms() -> None:
    text = RELEASE.read_text(encoding="utf-8")
    for group in ("sbom-prod.cdx.json", "sbom-dev.cdx.json", "sbom-docs.cdx.json"):
        assert group in text
    assert "cyclonedx-py environment" in text
    assert "uv sync --frozen --only-group docs" in text
    assert "uv sync --frozen --no-dev --all-extras" in text
