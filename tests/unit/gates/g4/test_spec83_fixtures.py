"""spec #83 fixture pack presence + anchor assertions (G0.9 copy proof).

Exact copies of novel-xinghuo-vol1 real run artifacts: chapters are
drafting outputs, plans are planning outputs, truth is the facts-system
runtime state, outline/genesis-context are the outline faces, characters
are the voice-card faces. Anchors pin the spec's canonical evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec83"  # tests/unit/gates/g4/ 深四层

CHAPTERS = (1, 2, 6, 13, 16, 17, 19, 23, 25, 26, 28, 30, 31, 33, 35)


def test_chapter_pack_present() -> None:
    for n in CHAPTERS:
        assert (FIX / "chapters" / f"chapter-{n}.md").is_file(), f"chapter-{n}.md 缺席"
    assert (FIX / "plans" / "chapter-28-plan.md").is_file()
    assert (FIX / "plans" / "chapter-1-plan.md").is_file()


def test_chapter_anchor_evidence() -> None:
    # spec 钦定实证锚：ch1:231 嵌套实证句 / ch6 截断金句正文 / ch28 双声明
    ch1 = (FIX / "chapters" / "chapter-1.md").read_text(encoding="utf-8")
    assert "却不知道明天城就破了" in ch1
    ch6 = (FIX / "chapters" / "chapter-6.md").read_text(encoding="utf-8")
    assert "册子认得人" in ch6
    ch28p = (FIX / "plans" / "chapter-28-plan.md").read_text(encoding="utf-8")
    assert "计数: 鉴录名数 4+0" in ch28p and "计数: 鉴录名数 4 +1" in ch28p
    # 轮 5 C1 锚：ch26:26 章首裸「剩」/ch23:300 深位袋底/ch1:229 转折词密度行
    ch26 = (FIX / "chapters" / "chapter-26.md").read_text(encoding="utf-8")
    assert "纸包里剩一百零三文" in ch26
    ch23 = (FIX / "chapters" / "chapter-23.md").read_text(encoding="utf-8")
    assert "袋底剩一百四十三文" in ch23
    assert "- [ ] 转折词密度: 0 / 3625字 = 0" in ch1


def test_truth_faces_present() -> None:
    ledger = (FIX / "truth" / "particle_ledger.md").read_text(encoding="utf-8")
    assert "余额一百零三文" in ledger  # 现值行实形（轮 5 C1 锚）
    assert (FIX / "truth" / "prop_registry.md").is_file()
    counters = json.loads((FIX / "truth" / "facts" / "counters.json").read_text(encoding="utf-8"))
    # 实文件嵌套在 "facts" 键下（轮 2 M5）；r5.1：终态 4（ch9 时序绿测另行构造 facts=3）
    assert counters["facts"]["鉴录名数"]["value"] == 4
    assert (FIX / "truth" / "facts" / "props.json").is_file()


def test_outline_and_seed_faces_present() -> None:
    vm = (FIX / "outline" / "volume_map.md").read_text(encoding="utf-8")
    assert "四件" in vm  # :88 四件清单一把哨实证
    outline = (FIX / "genesis-context" / "chapter_outline.md").read_text(encoding="utf-8")
    assert "还账进度表（私账打卡）" in outline  # :370 实锚（轮 1 I3）


def test_character_cards_sufficient() -> None:
    # 判据 5 声口面：≥5 张带卡面标记卡（regen_accept len(cards)<5 硬 FAIL）
    cards = list((FIX / "characters").rglob("*.md"))
    assert len(cards) >= 5
    assert not any(p.name == "relationships.md" for p in cards)  # 非卡面不拷
    from shenbi.text.voice_lexicon import catchphrases_from_card

    marker_cards = [p for p in cards if catchphrases_from_card(p.read_text(encoding="utf-8"))]
    assert len(marker_cards) >= 5
