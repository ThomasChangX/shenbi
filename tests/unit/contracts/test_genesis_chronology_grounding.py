"""Genesis chronology grounding contracts (probe7/probe8 P1, 2026-10-01).

probe7: power_system 里程碑表 carried a second chronology (52/57/58/40 vs
authoritative 43-44/46/45/79) plus a fake self-check citing story_frame
"章节里程碑" — a layer the file never contained. probe8 escalated to THREE
mutually contradictory chronologies under one agreeing chapter count:
power_system Y、relationships/factions Z、locations' parallel event history
(8 tables + two story-level endpoint collisions). Every drifting skill had
the authoritative volume_map sitting unread on disk — none of the four
world-layer skills declared it as a contract read (faction-builder runs
before volume-outlining; its drift was inherited from a stale skeleton).

Same batch: rhythm_principles frontmatter missing three probes in a row
(reconcile blind spot each time), genre-config's tropeInventory contract
loophole ("可选" — probe8 dropped the field legally) and the ghost-buffer
保量 claim (124 = 118+6 chapters invented inside chapter_word.note).
"""

from __future__ import annotations

from pathlib import Path

from shenbi.contracts.loader import load_contract

_SKILLS = Path(__file__).parents[3] / "skills"


def _body(skill: str) -> str:
    return (_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 4a — world-layer chronology grounding reads
# ---------------------------------------------------------------------------


def test_power_system_reads_volume_map() -> None:
    contract = load_contract("shenbi-power-system")
    assert "outline/volume_map.md" in contract["reads"], (
        "probe7/probe8: 里程碑表 invented a second/third chronology while "
        "the authoritative volume_map sat unread — it must be a contract read"
    )


def test_power_system_body_pins_chronology_authority() -> None:
    body = _body("shenbi-power-system")
    assert "以 outline/volume_map.md" in body or "以 volume_map" in body
    assert "不得自创编年" in body
    # probe7 :272 fake self-check cited story_frame 章节里程碑 (no such layer)
    assert "story_frame 无章号" in body or "story_frame 不含章号" in body


def test_location_builder_reads_volume_map() -> None:
    contract = load_contract("shenbi-location-builder")
    assert "outline/volume_map.md" in contract["reads"], (
        "probe8: all 8 功能事件表 misaligned plus invented events (哗变/清乡/"
        "炸桥) and two story-level endpoint collisions — ground on volume_map"
    )


def test_location_builder_body_pins_event_table_alignment() -> None:
    body = _body("shenbi-location-builder")
    assert "功能事件" in body
    assert "volume_map" in body
    assert "不得自创编年" in body or "卷纲之外" in body


def test_relationship_map_reads_grounding() -> None:
    contract = load_contract("shenbi-relationship-map")
    for grounding in ("novel.json", "outline/story_frame.md", "outline/volume_map.md"):
        assert grounding in contract["reads"], (
            f"probe8: relationships.md declared itself 权威源 while carrying "
            f"the Z chronology — {grounding} must be a grounding read"
        )


def test_relationship_map_body_pins_chronology_authority() -> None:
    body = _body("shenbi-relationship-map")
    assert "演化轨迹" in body
    assert "volume_map" in body
    assert "不得自创编年" in body


def test_faction_builder_reads_volume_map_as_optional() -> None:
    contract = load_contract("shenbi-faction-builder")
    assert "outline/volume_map.md" in contract["reads"], (
        "scoped-redo re-dispatch (probe8 redo list item 4) needs the outline "
        "on the redo path; first pass tolerates its absence via OPTIONAL_READS"
    )


def test_faction_builder_registered_in_optional_reads() -> None:
    from shenbi.pipeline.dispatch_helper import OPTIONAL_READS

    assert "outline/volume_map.md" in OPTIONAL_READS.get("shenbi-faction-builder", []), (
        "faction-builder (step 5) runs before volume-outlining (step 6) — "
        "the read must be registered optional or G1 hard-fails on ramp-up"
    )


def test_faction_builder_body_pins_no_absolute_chapter_numbers() -> None:
    body = _body("shenbi-faction-builder")
    assert "禁止落死章号" in body or "不得落死章号" in body
    assert "相对表述" in body


# ---------------------------------------------------------------------------
# 4b — pacing-design frontmatter (three probes: 6/7/8)
# ---------------------------------------------------------------------------


def test_pacing_design_body_pins_frontmatter_output() -> None:
    body = _body("shenbi-pacing-design")
    assert "total_chapters" in body
    assert "frontmatter" in body
    assert "produced_at" in body


# ---------------------------------------------------------------------------
# 4e — genre-config tropeInventory contract + ghost-buffer chapters
# ---------------------------------------------------------------------------


def test_genre_config_body_pins_trope_inventory_required() -> None:
    body = _body("shenbi-genre-config")
    assert "tropeInventory" in body
    # probe8 dropped the field legally — the contract said 可选. It must now
    # be declared 必填 (presence + signatures/rewrite_hint + overuse_threshold).
    assert "必填" in body


def test_genre_config_body_pins_no_ghost_buffer_chapters() -> None:
    body = _body("shenbi-genre-config")
    assert "缓冲章" in body
    assert "ceil" in body


# ---------------------------------------------------------------------------
# 4f — foundation-review interception (probe8 应拦未拦)
# ---------------------------------------------------------------------------


def test_foundation_review_body_pins_event_chapter_cross_check() -> None:
    body = _body("shenbi-foundation-review")
    assert "对章号" in body or "逐事件" in body
    assert "volume_map" in body
    # probe8: reviewer accepted power_system's milestone table without ever
    # diffing it against volume_map, with the full corpus visible.
    assert "story_frame 无章号" in body or "story_frame 不含章号" in body
