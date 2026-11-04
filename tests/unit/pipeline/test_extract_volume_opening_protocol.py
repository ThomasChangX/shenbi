"""Spec #95 T2: volume_opening_protocol extractor — projection & degrade."""

from __future__ import annotations

import json

from shenbi.pipeline.read_extractors import extract_volume_opening_protocol


def test_projects_scalars_and_protocol() -> None:
    cfg = {
        "chapter_word": {"default": 3200},
        "fatigueWords": ["凝视"],
        "pacing": {"x": 1},
        "chapterTypes": ["battle"],
        "market_params": {
            "payoff_density": {"window": 3, "min": 1},
            "hook_grading": {"max_consecutive_micro": 2},
            "volume_opening_protocol": {
                "热开篇": "危机/对手动作开场，前三章任一不中须整章重排",
                "倒计时": "每章尾锚一个不可逆倒数事件",
                "shadow": True,
            },
        },
    }
    out = extract_volume_opening_protocol(json.dumps(cfg, ensure_ascii=False))
    assert "chapter_word" in out and "fatigueWords" in out
    assert "volume_opening_protocol" in out and "热开篇" in out and "倒计时" in out
    assert "shadow" not in out  # 运行时旗标不进 prompt


def test_absent_protocol_degrades_visibly() -> None:
    cfg = {"chapter_word": {"default": 3200}}
    out = extract_volume_opening_protocol(json.dumps(cfg))
    assert "未声明" in out and "chapter_word" in out


def test_unparseable_json_returns_empty_for_loud_degrade() -> None:
    assert extract_volume_opening_protocol("not json") == ""
