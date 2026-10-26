"""Spec #78 T1 tests: recall registry seeding + weight checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.text.recall_weight import (
    RecallEntry,
    cold_run,
    detect_recall,
    emotion_band_warnings,
    escalation_action,
    load_recall_registry,
    recall_warnings,
    seed_recall_registry,
)


@pytest.mark.unit
def test_seeding_deng_alias_expansion(tmp_path: Path) -> None:
    (tmp_path / "characters" / "major").mkdir(parents=True)
    (tmp_path / "outline").mkdir()
    (tmp_path / "characters" / "major" / "deng.md").write_text(
        "---\nname: 灯\nrole: 情感主轴\ncurrent_state: active\n"
        "aliases_note: 卷一为染坊学徒萤\n---\n卡。\n",
        encoding="utf-8",
    )
    (tmp_path / "outline" / "volume_map.md").write_text(
        "## 第一卷：x（第1—10章）\n\n  | 第3章 | 转折 | 双死拍——萤死在怀里 |\n",
        encoding="utf-8",
    )
    target = seed_recall_registry(tmp_path)
    entries = load_recall_registry(target)
    # 卡面 active 但死亡章从节点表取证 + 化名进别名（weight 高=情感主轴）
    assert any(e.death_chapter == 3 and "萤" in e.aliases and e.weight == "高" for e in entries)


@pytest.mark.unit
def test_seeding_minor_heuristic(tmp_path: Path) -> None:
    (tmp_path / "characters" / "minor").mkdir(parents=True)
    (tmp_path / "outline").mkdir()
    (tmp_path / "characters" / "minor" / "lao-shu-shi.md").write_text(
        "---\nname: 老塾师\n---\n他拒用旌名而死。\n", encoding="utf-8"
    )
    (tmp_path / "outline" / "volume_map.md").write_text(
        "  | 第6章 | 承接 | 老塾师拒用旌名而死 |\n", encoding="utf-8"
    )
    entries = load_recall_registry(seed_recall_registry(tmp_path))
    assert any(e.name == "老塾师" for e in entries)


@pytest.mark.unit
def test_detect_recall_three_lexicons(tmp_path: Path) -> None:
    e = RecallEntry(name="萤", death_chapter=3, aliases=("那珂",))
    assert detect_recall("他把红纸包收好。", e, ["红纸包"])
    assert detect_recall("「那珂，水凉。」", e, [])
    assert not detect_recall("他推门，落座，研墨。", e, [])


@pytest.mark.unit
def test_recall_window_warn_and_half_window(tmp_path: Path) -> None:
    (tmp_path / "truth").mkdir()
    (tmp_path / "chapters").mkdir()
    (tmp_path / "truth" / "recall_registry.md").write_text(
        "| 死者名 | 死亡章 | 权重 | 化名 | 末触章 |\n|---|---|---|---|---|\n| 萤 | 2 | 高 | — | 2 |\n",
        encoding="utf-8",
    )
    for n in range(3, 11):
        (tmp_path / "chapters" / f"chapter-{n}.md").write_text(
            "他推门，落座，研墨。", encoding="utf-8"
        )
    # 高权重半窗 4：ch10 距 ch2 = 8 > 4 → WARN
    rows = recall_warnings(tmp_path, 10, recall_window=8)
    assert any("萤" in r and "超窗8章" in r and "窗4" in r for r in rows), rows
    # 中权重全窗 8：8 > 8 不成立 → 无 WARN
    (tmp_path / "truth" / "recall_registry.md").write_text(
        "| 死者名 | 死亡章 | 权重 | 化名 | 末触章 |\n|---|---|---|---|---|\n| 萤 | 2 | 中 | — | 2 |\n",
        encoding="utf-8",
    )
    assert recall_warnings(tmp_path, 10, recall_window=8) == []
    # 触点重置
    (tmp_path / "chapters" / "chapter-8.md").write_text("半张红纸从怀里滑出。", encoding="utf-8")
    assert recall_warnings(tmp_path, 10, recall_window=8, extra_lexicons=("红纸",)) == []


@pytest.mark.unit
def test_cold_run_and_escalation(tmp_path: Path) -> None:
    (tmp_path / "plans").mkdir(parents=True)
    (tmp_path / "outline").mkdir()
    for n, tone in ((6, "悲"), (7, "惧"), (8, "平")):
        (tmp_path / "plans" / f"chapter-{n}-plan.md").write_text(
            f"emotion_tone: {tone}\n", encoding="utf-8"
        )
    (tmp_path / "outline" / "volume_map.md").write_text(
        "  | 第12章 | 转折 | 灰烬反扑 |\n", encoding="utf-8"
    )
    assert cold_run(tmp_path, 8) == 3
    assert "第12章" in (escalation_action(tmp_path, 8) or "")
    assert escalation_action(tmp_path, 8) != "CHECKPOINT"
    # 5 连 → CHECKPOINT
    for n in (4, 5):
        (tmp_path / "plans" / f"chapter-{n}-plan.md").write_text(
            "emotion_tone: 悲\n", encoding="utf-8"
        )
    assert escalation_action(tmp_path, 8) == "CHECKPOINT"
    # 卷末降级（3 连取用降级；5 连熔断不受卷末影响——先验证 5 连仍 CHECKPOINT）
    assert escalation_action(tmp_path, 8) == "CHECKPOINT"
    (tmp_path / "outline" / "volume_map.md").write_text(
        "  | 第2章 | 转折 | 已过 |\n", encoding="utf-8"
    )
    # 回到 3 连（删两章 memo）→ 卷末无后续节点 → None（降级 WARN 语义）
    (tmp_path / "plans" / "chapter-4-plan.md").unlink()
    (tmp_path / "plans" / "chapter-5-plan.md").unlink()
    assert cold_run(tmp_path, 8) == 3
    assert escalation_action(tmp_path, 8) is None
    # emotion-band 行
    rows = emotion_band_warnings(tmp_path, 8)
    assert any("[emotion-band]" in r and "冷章" in r for r in rows)


@pytest.mark.unit
def test_genre_recall_window_domain(tmp_path: Path) -> None:
    import json

    from shenbi.contracts.skills.genre_config import GenreConfig

    gc = Path(__file__).resolve().parents[3] / "novel-xinghuo-vol1/genre-config.json"
    if not gc.is_file():
        pytest.skip("project data not present")
    base = json.loads(gc.read_text(encoding="utf-8"))
    base["market_params"]["recall_window"] = {"window": 8}
    GenreConfig.model_validate(base)
    base["market_params"]["recall_window"] = {"window": 99}
    with pytest.raises(ValueError, match="recall_window"):
        GenreConfig.model_validate(base)
