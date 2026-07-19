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
