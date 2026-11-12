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


def test_extractor_wired_into_prompt(tmp_path, monkeypatch) -> None:
    """audit-T5 C1 wiring test: the projection actually replaces the read.

    The first cut of the dispatch-loop branch computed ``extracted`` and
    dropped it (classic dead-wire); this pins the sentinel + the shadow-flag
    non-leak + loud-degrade end-to-end through build_skill_prompt.
    """
    import json as _json

    import shenbi.pipeline.dispatch_helper as dh

    cfg = {
        "chapter_word": {"default": 3200},
        "market_params": {
            "payoff_density": {"window": 3, "min": 1},
            "hook_grading": {"max_consecutive_micro": 2},
            "volume_opening_protocol": {"热开篇": "危机开场", "shadow": True},
        },
    }
    (tmp_path / "genre-config.json").write_text(
        _json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
    )
    warned: list[str] = []

    def _spy(event: str, **kw: object) -> None:
        warned.append(event)

    monkeypatch.setattr(dh.log, "warning", _spy)
    _, user_prompt, _, _, _ = dh.build_skill_prompt(
        "shenbi-chapter-planning", tmp_path, "plan 第2章", chapter=2
    )
    assert "[extractor:volume_opening_protocol]" in user_prompt
    assert "热开篇: 危机开场" in user_prompt
    assert "chapter_word" in user_prompt
    assert "shadow" not in user_prompt  # 运行时旗标不泄漏
    assert "extractor_failed_fulltext" not in warned


def test_unparseable_genre_config_loud_degrades(tmp_path, monkeypatch) -> None:
    """audit-T5 C1: "" must land in the loud fulltext+WARN branch, not silent."""
    import shenbi.pipeline.dispatch_helper as dh

    (tmp_path / "genre-config.json").write_text("not json", encoding="utf-8")
    warned: list[str] = []

    def _spy(event: str, **kw: object) -> None:
        warned.append(event)

    monkeypatch.setattr(dh.log, "warning", _spy)
    _, user_prompt, _, _, _ = dh.build_skill_prompt(
        "shenbi-chapter-planning", tmp_path, "plan 第2章", chapter=2
    )
    assert "extractor_failed_fulltext" in warned
    assert "not json" in user_prompt  # fulltext fallback
