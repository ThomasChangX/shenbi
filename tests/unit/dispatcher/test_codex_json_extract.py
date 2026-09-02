"""T2a: codex JSON 提取候选化(spec #38 F203——最内层扁平正则丢嵌套外层)。"""

import pytest

from shenbi.dispatcher.modes.codex import _extract_json_object
from shenbi.exceptions import SubAgentProtocolError


def test_nested_object_wins_over_innermost() -> None:
    """嵌套 scores 输出:完整外层对象胜出,而非最内层扁平片段。"""
    text = 'Here is the result: {"scores": {"维度A": 88}, "summary": "ok"} done.'
    out = _extract_json_object(text)
    assert out["summary"] == "ok"
    assert out["scores"] == {"维度A": 88}


def test_flat_object_still_works() -> None:
    text = "blah {'a': 1}"  # 单引号非合法 JSON,不采
    with pytest.raises(SubAgentProtocolError):
        _extract_json_object(text)


def test_flat_valid_json() -> None:
    text = 'prefix {"a": 1} suffix'
    assert _extract_json_object(text) == {"a": 1}


def test_multiple_flat_candidates_ambiguous_raises() -> None:
    """均扁平且多个合法候选 → 显式拒绝,不猜首匹配。"""
    text = '{"a": 1} and {"b": 2}'
    with pytest.raises(SubAgentProtocolError):
        _extract_json_object(text)


def test_no_json_raises() -> None:
    with pytest.raises(SubAgentProtocolError):
        _extract_json_object("no braces at all")
