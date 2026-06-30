"""REGISTRY auto-discovery + bootstrap tests."""

from __future__ import annotations

from shenbi.contracts.registry import (
    REGISTRY,
    bootstrap_registry,
    load_skill_contract,
)


def test_registry_includes_migrated() -> None:
    from shenbi.contracts.skills.foreshadowing_resolve import Report

    assert REGISTRY["shenbi-foreshadowing-resolve"] is Report


def test_registry_includes_all_functional_skills() -> None:
    assert "shenbi-worldbuilding" in REGISTRY
    assert "shenbi-pacing-design" in REGISTRY


def test_bootstrap_returns_vocab() -> None:
    reg = bootstrap_registry()
    assert isinstance(reg, dict)
    assert len(reg) > 0
    assert any("pending_hooks" in k for k in reg)


def test_load_migrated_returns_model() -> None:
    assert load_skill_contract("shenbi-worldbuilding") is not None


def test_load_unknown_returns_none() -> None:
    assert load_skill_contract("shenbi-does-not-exist") is None
