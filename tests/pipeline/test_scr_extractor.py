"""Test Structured Chapter Representation (SCR) extractor."""

import json

from shenbi.pipeline.scr_extractor import (
    _compute_paragraph_stats,
    _extract_character_locations,
    _extract_dialogue_segments,
    _extract_event_timeline,
    _extract_hook_appearances,
    extract_prose,
    extract_scr,
)

SAMPLE_CHAPTER = """# 沉

废料场的风很大。李明站在铁堆上，数着手中的铜币。

"你确定要这么做？"王铁的声音从身后传来。

李明没有回头。"我没有选择。"

第三十七枚铜币落入布袋。李明的手指微微颤抖。如果算错了，这些铜币的数量就不对了。

他想起昨天的事——那个老人的话依然在耳边回响。MH-003的秘密必须守住。

从废料场到铁匠铺，他走了很久。每一步都像踩在刀刃上。
"""


class TestExtractProse:
    def test_strips_meta_block(self):
        text = "<!--META-BEGIN-->...<!--META-END-->\n\n# Title\n\nBody text."
        prose = extract_prose(text)
        assert "META" not in prose
        assert "Body text" in prose


class TestExtractCharacterLocations:
    def test_finds_characters_by_dialogue(self):
        locs = _extract_character_locations(SAMPLE_CHAPTER)
        names = {l["name"] for l in locs}
        assert "李明" in names

    def test_includes_evidence_and_line_range(self):
        locs = _extract_character_locations(SAMPLE_CHAPTER)
        for loc in locs:
            assert "name" in loc
            assert "evidence" in loc
            assert "line_range" in loc


class TestExtractDialogueSegments:
    def test_extracts_dialogue_with_speaker(self):
        segs = _extract_dialogue_segments(SAMPLE_CHAPTER)
        speakers = {s["speaker"] for s in segs}
        assert "王铁" in speakers

    def test_extracts_dialogue_text(self):
        segs = _extract_dialogue_segments(SAMPLE_CHAPTER)
        texts = [s["text"] for s in segs]
        assert any("你确定要这么做" in t for t in texts)


class TestExtractHookAppearances:
    def test_finds_hook_ids(self):
        hooks = _extract_hook_appearances(SAMPLE_CHAPTER)
        ids = [h["hook_id"] for h in hooks]
        assert "MH-003" in ids


class TestExtractEventTimeline:
    def test_extracts_events(self):
        events = _extract_event_timeline(SAMPLE_CHAPTER)
        assert len(events) > 0
        for e in events:
            assert "description" in e
            assert "line_range" in e


class TestComputeParagraphStats:
    def test_counts_paragraphs(self):
        stats = _compute_paragraph_stats(SAMPLE_CHAPTER)
        assert "count" in stats
        assert stats["count"] > 0


class TestSCRIntegration:
    def test_full_extraction_produces_valid_scr(self, tmp_path):
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "chapter-1.md").write_text(SAMPLE_CHAPTER)

        context_dir = tmp_path / "context"
        context_dir.mkdir()

        scr = extract_scr(tmp_path, 1)
        assert scr.chapter == 1
        assert scr.total_chinese_chars > 0
        assert len(scr.character_locations) > 0
        assert 0.0 <= scr.extraction_confidence <= 1.0

    def test_scr_cached_to_disk(self, tmp_path):
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "chapter-2.md").write_text(SAMPLE_CHAPTER)

        context_dir = tmp_path / "context"
        context_dir.mkdir()

        extract_scr(tmp_path, 2)
        cache_path = context_dir / "chapter-2-scr.json"
        assert cache_path.exists()

        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        assert cached["chapter"] == 2

    def test_cache_hit_avoids_re_extraction(self, tmp_path):
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "chapter-3.md").write_text(SAMPLE_CHAPTER)

        context_dir = tmp_path / "context"
        context_dir.mkdir()

        scr1 = extract_scr(tmp_path, 3)
        # Second call should hit cache
        scr2 = extract_scr(tmp_path, 3)
        assert scr1.extracted_at == scr2.extracted_at  # Same timestamp = cached


def test_extract_prose_strips_contract_header_and_title() -> None:
    """z11 R1c: contract header + original title line both stripped from prose."""
    text = "# Chapter 7:\n\n# 第7章 试炼\n\n正文开始。"
    assert extract_prose(text) == "正文开始。"


# ---------------------------------------------------------------------------
# Spec #32 F333: line_range must map to REAL newline positions in the prose,
# and POV shifts must not be fabricated from high-frequency CJK bigrams.
# ---------------------------------------------------------------------------
class TestEventTimelineLineRange:
    def test_line_range_matches_real_newline_position(self):
        """Events on a later physical line must report that line, not a
        per-sentence counter (the old bug: line_num incremented once per
        re.split segment regardless of actual newlines).
        """
        # Line 1 filler (no event verbs), event on physical line 3.
        prose = (
            "天空是灰色的。\n"  # line 1 — filler
            "灰得彻底。\n"  # line 2 — filler
            "李明走进铁匠铺。\n"  # line 3 — event (走/进)
            "他拿起锤子。"  # line 4 — event (拿)
        )
        events = _extract_event_timeline(prose)
        assert events, "sanity: events extracted"
        first = events[0]
        # The first event sentence lives on physical line 3, not line 1.
        assert first["description"].startswith("李明")
        assert first["line_range"][0] == 3
        assert events[1]["line_range"][0] == 4

    def test_multiple_sentences_on_one_line_share_the_line(self):
        prose = "李明走进铁匠铺。他拿起锤子。\n他放下锤子。"
        events = _extract_event_timeline(prose)
        assert [e["line_range"][0] for e in events] == [1, 1, 2]


class TestPovShifts:
    def test_no_explicit_pov_markers_returns_empty(self):
        """No explicit POV evidence -> empty list, never fabricated dominant
        high-frequency CJK 2-3 char substrings.
        """
        from shenbi.pipeline.scr_extractor import _extract_pov_shifts

        # Two paragraphs of plain narration; no POV markers. The old code
        # reported a "shift" between the most frequent bigrams of each
        # paragraph (e.g. 李明 -> 铜币), which is not a POV fact.
        prose = "李明数着铜币，铜币很多，铜币闪着光。\n\n王铁站在铁堆旁看着远处的废料场。"
        assert _extract_pov_shifts(prose) == []

    def test_explicit_pov_marker_still_detected(self):
        from shenbi.pipeline.scr_extractor import _extract_pov_shifts

        prose = "视角：李明\n\n李明数着铜币。\n\n视角：王铁\n\n王铁看着铁堆。"
        shifts = _extract_pov_shifts(prose)
        assert shifts, "explicit 视角 markers must still yield a shift"
        assert shifts[0]["from_pov"] == "李明"
        assert shifts[0]["to_pov"] == "王铁"
