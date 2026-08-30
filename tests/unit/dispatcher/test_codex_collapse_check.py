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
