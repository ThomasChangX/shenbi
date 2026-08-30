"""spec #31 T2a: 独立评分后坍缩检测落盘 (F114 接线，零额外派发)."""

from __future__ import annotations

import json

import pytest

from shenbi.dispatcher.modes.codex import _record_collapse_check


@pytest.mark.unit
def test_collapse_check_written(tmp_path):
    scores = {1: 95, 2: 95, 3: 95}  # 多维非全零全同 → 坍缩 (T4 语义)
    result = _record_collapse_check(tmp_path, "sk", "generative", scores)
    out = tmp_path / "t1-reports" / "sk-generative-collapse-check.json"
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == result
    assert result["collapse_suspected"] is True


@pytest.mark.unit
def test_collapse_check_all_zero_no_flag(tmp_path):
    result = _record_collapse_check(tmp_path, "sk", "generative", {1: 0, 2: 0})
    out = tmp_path / "t1-reports" / "sk-generative-collapse-check.json"
    assert result["collapse_suspected"] is False
    assert json.loads(out.read_text(encoding="utf-8"))["collapse_suspected"] is False


@pytest.mark.unit
def test_collapse_check_str_keys_normalized(tmp_path):
    # codex JSON 解析产物是 str 维度键——规范化后照常检测
    result = _record_collapse_check(tmp_path, "sk", "generative", {"1": 95, "2": 95, "3": 95})
    assert result["collapse_suspected"] is True
    persisted = json.loads(
        (tmp_path / "t1-reports" / "sk-generative-collapse-check.json").read_text(encoding="utf-8")
    )
    assert "all_identical" in persisted["signals"]


@pytest.mark.unit
def test_collapse_check_non_numeric_dropped(tmp_path):
    result = _record_collapse_check(tmp_path, "sk", "generative", {"1": 90, "2": 95, "junk": "x"})
    assert result["collapse_suspected"] is False  # 两有效维度不同值
