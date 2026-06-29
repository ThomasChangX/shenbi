"""REGISTRY 自动发现 + bootstrap 测试。"""

from __future__ import annotations

from shenbi.contracts.registry import (
    REGISTRY,
    bootstrap_registry,
    load_skill_contract,
)


def test_registry_includes_migrated() -> None:
    from shenbi.contracts.skills.foreshadowing_resolve import Report

    assert REGISTRY["shenbi-foreshadowing-resolve"] is Report


def test_registry_excludes_unmigrated() -> None:
    assert "shenbi-worldbuilding" not in REGISTRY


def test_bootstrap_returns_vocab() -> None:
    reg = bootstrap_registry()
    assert isinstance(reg, dict)
    assert len(reg) > 0
    assert any("pending_hooks" in k for k in reg)


def test_load_unmigrated_returns_none() -> None:
    assert load_skill_contract("shenbi-worldbuilding") is None


def test_load_unknown_returns_none() -> None:
    assert load_skill_contract("shenbi-does-not-exist") is None
