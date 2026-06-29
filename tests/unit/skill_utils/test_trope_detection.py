"""Unit tests for skill_utils/trope_detection/match_tropes.py."""

from __future__ import annotations

import json

import pytest

from shenbi.skill_utils.trope_detection import (
    Trope,
    count_trope_hits,
    trope_overuse,
)
from shenbi.skill_utils.trope_detection.match_tropes import (
    load_trope_inventory,
    main,
)


@pytest.mark.unit
def test_count_hits_matches_signature_keywords() -> None:
    t = Trope("废柴逆袭", ["主角开局被退婚", "获得金手指"], 2, "淡化")
    beats = [
        "主角开局被退婚，未婚妻当众悔婚",
        "主角获得金手指老爷爷",
        "主角吃了一碗面",
    ]
    assert count_trope_hits(beats, t) == 2


@pytest.mark.unit
def test_overuse_flagged_above_threshold() -> None:
    t = Trope("天降系统", ["系统面板", "任务奖励"], 1, "改")
    assert trope_overuse(2, t) is True
    assert trope_overuse(1, t) is False


@pytest.mark.unit
def test_count_hits_zero_when_no_signature_present() -> None:
    t = Trope("废柴逆袭", ["主角开局被退婚", "获得金手指"], 2, "淡化")
    beats = ["主角吃了一碗面", "主角睡了一觉"]
    assert count_trope_hits(beats, t) == 0


@pytest.mark.unit
def test_count_hits_empty_beats() -> None:
    t = Trope("废柴逆袭", ["主角开局被退婚"], 2, "淡化")
    assert count_trope_hits([], t) == 0


@pytest.mark.unit
def test_count_hits_empty_signatures_never_matches() -> None:
    """A trope with no signatures never matches any beat."""
    t = Trope("空模板", [], 0, "")
    assert count_trope_hits(["任何内容", "主角开局被退婚"], t) == 0


@pytest.mark.unit
def test_count_hits_each_beat_counted_at_most_once() -> None:
    """A single beat matching multiple signatures counts as one hit."""
    t = Trope("天降系统", ["系统面板", "任务奖励"], 1, "改")
    beats = ["脑海中出现系统面板，完成任务奖励循环"]
    assert count_trope_hits(beats, t) == 1


@pytest.mark.unit
def test_trope_is_frozen() -> None:
    import dataclasses

    t = Trope("天降系统", ["系统面板"], 1, "改")
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.trope = "改不了"  # type: ignore[misc]


@pytest.mark.unit
def test_trope_overuse_boundary_is_strict_greater() -> None:
    """overuse_threshold is exclusive: hit_count == threshold is NOT overuse."""
    t = Trope("t", ["s"], 3, "h")
    assert trope_overuse(3, t) is False
    assert trope_overuse(4, t) is True


FIXTURE = "tests/fixtures/genre-config-example.json"


@pytest.mark.unit
def test_load_trope_inventory_reads_fixture() -> None:
    tropes = load_trope_inventory(FIXTURE)
    assert len(tropes) == 2
    assert tropes[0].trope == "废柴逆袭"
    assert tropes[1].trope == "天降系统"
    assert tropes[0].overuse_threshold == 2
    assert tropes[1].overuse_threshold == 1
    assert "主角开局被退婚/受辱" in tropes[0].signatures


@pytest.mark.unit
def test_main_cli_outputs_json(tmp_path, capsys, monkeypatch) -> None:
    """main() loads --config tropeInventory and --beats-file, prints JSON."""
    config = tmp_path / "genre.json"
    config.write_text(
        json.dumps(
            {
                "tropeInventory": [
                    {
                        "trope": "天降系统",
                        "signatures": ["系统面板", "任务奖励"],
                        "overuse_threshold": 1,
                        "rewrite_hint": "改",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    beats = tmp_path / "beats.txt"
    beats.write_text("脑海中出现系统面板\n完成任务奖励循环\n吃面\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "match_tropes.py",
            "--config",
            str(config),
            "--beats-file",
            str(beats),
        ],
    )
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["sample"]["beats"] == 3
    assert out["results"][0]["trope"] == "天降系统"
    assert out["results"][0]["hits"] == 2
    assert out["results"][0]["overuse"] is True


# ===========================================================================
# §10 套路检测测试 — fixture-scenario overuse detection (full report path)
# ===========================================================================
#
# These exercise the full ``load_trope_inventory`` → ``match_all`` path against
# the real ``genre-config-example.json`` tropeInventory with beats that do / do
# not over-trigger a trope, asserting hits are correct, ``overuse_threshold``
# flags fire, and the report carries the actionable ``rewrite_hint``.

from shenbi.skill_utils.trope_detection.match_tropes import match_all  # noqa: E402


@pytest.mark.unit
def test_fixture_overuse_detected_via_match_all() -> None:
    """Real fixture: 天降系统 over-triggered (>1 hit) → overuse flagged."""
    tropes = load_trope_inventory(FIXTURE)
    # two distinct beats each matching a 天降系统 signature → 2 hits > threshold 1
    beats = [
        "脑海中出现系统面板，显示任务列表",
        "任务-奖励循环驱动行为，主角不断刷任务",
        "主角吃了一碗面",
    ]
    results = {r["trope"]: r for r in match_all(beats, tropes)}

    assert results["天降系统"]["hits"] == 2
    assert results["天降系统"]["overuse"] is True
    assert results["天降系统"]["overuse_threshold"] == 1
    assert results["废柴逆袭"]["overuse"] is False


@pytest.mark.unit
def test_fixture_overuse_result_carries_rewrite_hint() -> None:
    """An overused trope's result carries the actionable rewrite_hint."""
    tropes = load_trope_inventory(FIXTURE)
    beats = [
        "脑海中出现系统面板",
        "任务-奖励循环驱动行为",
    ]
    results = {r["trope"]: r for r in match_all(beats, tropes)}
    flagged = results["天降系统"]
    assert flagged["overuse"] is True
    assert flagged["rewrite_hint"]  # non-empty, actionable
    assert "系统" in flagged["rewrite_hint"]


@pytest.mark.unit
def test_fixture_clean_outline_no_overuse() -> None:
    """Beats with no trope signatures → every result overuse=False, zero hits."""
    tropes = load_trope_inventory(FIXTURE)
    beats = [
        "主角与村民商议秋收分配",
        "主角独自在山路上行走，回忆往事",
        "集市上有人争吵，主角旁观",
    ]
    for r in match_all(beats, tropes):
        assert r["hits"] == 0
        assert r["overuse"] is False


@pytest.mark.unit
def test_fixture_selective_overuse_only_flagged_trope() -> None:
    """Only the trope exceeding its threshold is flagged; the other is not.

    废柴逆袭 (threshold 2) gets exactly 2 hits → NOT overuse (strict >).
    天降系统 (threshold 1) gets 2 hits → overuse. So the report flags exactly
    one trope and reports the right hit counts for both.
    """
    tropes = load_trope_inventory(FIXTURE)
    beats = [
        # 废柴逆袭: 2 hits (== threshold, not overuse)
        "主角开局被退婚/受辱，未婚妻离去",
        "获得金手指(系统/老爷爷/血脉)老爷爷苏醒",
        # 天降系统: 2 hits (> threshold 1, overuse)
        "脑海中出现系统面板",
        "系统解释一切机制",
    ]
    by_trope = {r["trope"]: r for r in match_all(beats, tropes)}
    assert by_trope["废柴逆袭"]["hits"] == 2
    assert by_trope["废柴逆袭"]["overuse"] is False
    assert by_trope["天降系统"]["hits"] == 2
    assert by_trope["天降系统"]["overuse"] is True


@pytest.mark.unit
def test_match_all_full_report_structure() -> None:
    """Every match_all result exposes the full §10 report contract."""
    tropes = load_trope_inventory(FIXTURE)
    results = match_all(["主角吃面"], tropes)
    assert len(results) == len(tropes)
    for r in results:
        assert set(r) == {
            "trope",
            "hits",
            "overuse",
            "overuse_threshold",
            "rewrite_hint",
        }


@pytest.mark.unit
def test_fixture_cli_with_real_genre_config(tmp_path, capsys, monkeypatch) -> None:
    """main() against the real fixture config + a beats file → full JSON report."""
    beats = tmp_path / "beats.txt"
    beats.write_text(
        "脑海中出现系统面板\n任务-奖励循环驱动行为\n主角吃面\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        ["match_tropes.py", "--config", FIXTURE, "--beats-file", str(beats)],
    )
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["sample"]["beats"] == 3
    assert out["sample"]["tropes"] == 2
    by_trope = {r["trope"]: r for r in out["results"]}
    assert by_trope["天降系统"]["hits"] == 2
    assert by_trope["天降系统"]["overuse"] is True
    assert by_trope["天降系统"]["rewrite_hint"]
