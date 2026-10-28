"""T2: facts JSON 侧车 IO——flock 原子写 + 空种子 bootstrap（spec §1.1/§4 F15 空种子语义）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.exceptions import TruthFileParseError
from shenbi.facts.enums import FactsDim
from shenbi.facts.store import load_facts, save_facts, seed_empty


def test_load_absent_returns_none(tmp_path: Path):
    assert load_facts(tmp_path, FactsDim.PROPS) is None  # 门检 WARN 降级依据


def test_load_corrupt_raises_truth_parse_error(tmp_path: Path):
    target = tmp_path / "truth" / "facts"
    target.mkdir(parents=True)
    (target / "props.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(TruthFileParseError):
        load_facts(tmp_path, FactsDim.PROPS)


def test_save_then_load_roundtrip(tmp_path: Path, props_file):
    save_facts(tmp_path, props_file)
    back = load_facts(tmp_path, FactsDim.PROPS)
    assert back is not None
    assert back.props()["火纹骨哨"].owner == "那罕"
    assert (tmp_path / "truth" / "facts" / "props.json").is_file()


def test_seed_empty_idempotent_creates_three_dims(tmp_path: Path):
    seed_empty(tmp_path)
    for dim in ("props", "counters", "identity"):
        assert (tmp_path / "truth" / "facts" / f"{dim}.json").is_file()
    before = (tmp_path / "truth" / "facts" / "props.json").read_text(encoding="utf-8")
    seed_empty(tmp_path)  # 幂等：不覆写
    after = (tmp_path / "truth" / "facts" / "props.json").read_text(encoding="utf-8")
    assert before == after


def test_seed_empty_files_are_valid_empty_facts(tmp_path: Path):
    seed_empty(tmp_path)
    for dim in FactsDim:
        loaded = load_facts(tmp_path, dim)
        assert loaded is not None and loaded.is_empty
