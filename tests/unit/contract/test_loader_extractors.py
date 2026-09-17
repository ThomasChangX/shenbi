"""Loader extractor sidecar tests (spec #65 §4.2): closed registry,
fields/extractor mutex, sidecar normalization. Staged-skill pattern from
tests/unit/contract/test_dict_reads.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.contracts.loader import ContractError, load_contract

pytestmark = pytest.mark.unit


def _write_skill(root: Path, name: str, reads_yaml: str) -> None:
    skills = root / "skills"
    d = skills / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ncontract:\n  kind: report\n  reads:\n{reads_yaml}"
        "\n  writes: [audits/chapter-N-x.md]\n  updates: []\n---\n# body\n",
        encoding="utf-8",
    )  # --- delimiters REQUIRED (loader.read_frontmatter_contract rejects text
    # not starting with '---'; without them test_unknown_extractor_name_
    # fails_loud false-passes: ShenbiError.__str__ renders the skill-name
    # kwarg, and "shenbi-test-bad-extractor" matches match="extractor")


EXTRACTOR_READS = "    - {file: outline/volume_map.md, extractor: volume_chapter}\n"


def test_extractor_lands_in_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_skill(tmp_path, "shenbi-test-extractor", EXTRACTOR_READS)
    monkeypatch.setattr("shenbi.contracts.loader.SKILLS", tmp_path / "skills")
    c = load_contract("shenbi-test-extractor")
    assert all(isinstance(r, str) for r in c["reads"])
    assert c["read_extractors"] == {"outline/volume_map.md": "volume_chapter"}
    assert c["read_fields"] == {}


def test_unknown_extractor_name_fails_loud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_skill(
        tmp_path,
        "shenbi-test-bad-extractor",
        "    - {file: outline/volume_map.md, extractor: volume_chapters}\n",  # typo
    )
    monkeypatch.setattr("shenbi.contracts.loader.SKILLS", tmp_path / "skills")
    with pytest.raises(ContractError, match="extractor"):
        load_contract("shenbi-test-bad-extractor")


def test_fields_and_extractor_mutex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_skill(
        tmp_path,
        "shenbi-test-bad-mutex",
        "    - {file: outline/volume_map.md, fields: [汇总], extractor: volume_chapter}\n",
    )
    monkeypatch.setattr("shenbi.contracts.loader.SKILLS", tmp_path / "skills")
    with pytest.raises(ContractError, match="mutually exclusive"):
        load_contract("shenbi-test-bad-mutex")
