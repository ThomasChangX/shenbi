from __future__ import annotations

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.contracts import load_registry
from shenbi.contracts.registry import bootstrap_registry
from shenbi.gates.shared import PROJECT

_TRUTH_YAML = PROJECT / "docs" / "framework" / "truth-files.yaml"


def _yaml_concept_names() -> set[str]:
    data = yaml.safe_load(_TRUTH_YAML.read_text(encoding="utf-8")) or {}
    return {c["name"] for c in data.get("concepts", [])}


def test_three_registry_sources_agree() -> None:
    """判据 5（本支柱范围）：三表从单一源 truth-files.yaml 派生，文件名集合 diff 为空。

    三源：(1) truth-files.yaml concepts 直读 (2) contract.load_registry concepts
    (3) contracts.bootstrap_registry vocab。三者必相等（实测 54==54==54）。
    全 69 技能契约迁移锁定（判据 8）是支柱一续 + 支柱二的范围。
    """
    src = _yaml_concept_names()
    lr = {c["name"] for c in load_registry().get("concepts", [])}
    br = set(bootstrap_registry().keys())
    assert src == lr == br
    assert len(src) > 0


@pytest.mark.parametrize("name", sorted(_yaml_concept_names()))
def test_every_truth_file_has_kind(name: str) -> None:
    """单一源约束：每个登记 concept 必有非空 kind（派生分层依赖）。"""
    data = yaml.safe_load(_TRUTH_YAML.read_text(encoding="utf-8")) or {}
    kinds = {c["name"]: c.get("kind") for c in data.get("concepts", [])}
    assert kinds.get(name), f"{name} 缺 kind"


@given(st.data())
@settings(max_examples=20, deadline=None)
def test_bootstrap_subset_of_yaml(_data: object) -> None:
    """bootstrap_registry 词汇必 ⊆ truth-files.yaml concept 名集（派生一致性）。"""
    assert set(bootstrap_registry().keys()) <= _yaml_concept_names()
