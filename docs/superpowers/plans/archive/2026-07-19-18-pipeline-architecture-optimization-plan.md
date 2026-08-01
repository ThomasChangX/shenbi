# Pipeline Architecture Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the per-chapter pipeline from 20 `CHAPTER_STEPS` and ~24 LLM calls to ~16 steps and ~10 LLM calls (58% reduction) by deleting 3 redundant steps, merging 2 groups (3 foreshadowing skills into 1 lifecycle call, 7 serial core-circle auditors into domain-grouped calls alongside the already-parallel dynamic genre-circle audits), adding 4 deterministic steps, parallelizing write-disjoint steps (reusing the EXISTING `parallel_dispatch.py` layer), and building a shared Structured Chapter Representation (SCR) extractor.

**Architecture:** The pipeline step list (`CHAPTER_STEPS`, currently 20 steps at `chapter_loop.py:106-254`) is restructured. Three independent foreshadowing skills are merged into a single `foreshadowing-lifecycle` call (NEW skill -- does not exist yet) that performs recall-track-plant sequentially with shared context. Audit topology: 7 core-circle auditors run as serial `CHAPTER_STEPS`; 6 genre-circle auditors already dispatch dynamically and in parallel via `audit_layer.py`. MERGE-2 groups auditors but MUST preserve the existing two-wave parallel dispatch model at `parallel_dispatch.py` (dispatched at `chapter_loop.py:1090-1168`) -- each group dispatches as a parallel wave, not serially. Two write-disjoint post-drafting steps (foreshadowing-lifecycle and state-settling) run in parallel by reusing the EXISTING `parallel_dispatch.py` concurrency layer. Thread safety uses a single-writer (actor-model) pattern: worker threads return dict results, the main thread merges them sequentially to `PipelineState` (no fine-grained `_state_lock`). A deterministic SCR extractor (`scr_extractor.py`) pre-extracts 15+ structured fields from raw chapter text once per chapter, serving all downstream consumers. Four new deterministic steps fill pipeline gaps (volume-align, post-draft-extract, linguistic-drift-check, pre-revision-snapshot). `linguistic_drift.py` lives at `src/shenbi/skill_utils/drift_detection/linguistic_drift.py` (per Spec 4 §3.2), not `pipeline/`. `executor_config.toml` does not exist yet and is created in this plan. Dispatch-level token logging is added.

**Tech Stack:** Python 3.11+, pathlib, structlog, json, concurrent.futures, threading, re

## Global Constraints
1. `just check` full pass at every task boundary
2. `CHAPTER_STEPS` list reflects new ~16-step structure (currently 20 `CHAPTER_STEPS` at `chapter_loop.py:106-254`)
3. `_should_run_step` correctly gates intent-management; escalation-review is NOT a `CHAPTER_STEPS` entry (dispatched reactively per Spec 5)
4. Grouped audit prompts produce separate dimension reports within single LLM response
5. Deprecated skills are unreachable from chapter loop
6. foreshadowing-lifecycle and state-settling run in parallel by REUSING the existing `parallel_dispatch.py` layer (proven by the audit waves)
7. MERGE-2 grouped audits preserve the existing two-wave parallel dispatch model (`parallel_dispatch.py`, invoked at `chapter_loop.py:1090-1168`) -- each group dispatches as a parallel wave
8. `safe_write` produces zero deadlocks or race conditions under concurrent execution
9. `pending_hooks.md` content identical between serial and parallel execution (regression test)
10. Thread safety via single-writer (actor-model): worker threads return dict results, main thread merges sequentially (no `_state_lock`)
11. SCR `character_locations` consistent with chapter content (spot-check 5 chapters)
12. SCR cache hit rate 100% (no re-extraction for same chapter)
13. Pipeline logs include per-step token counts
14. End-to-end test: run 3-chapter mini-pipeline with new architecture

---

## Task 1: Build Deterministic Shared SCR Extractor

**Files:**
- `src/shenbi/pipeline/scr_extractor.py` -- new file
- `tests/pipeline/test_scr_extractor.py` -- new file

**TDD Cycle:**

- [ ] **1a. Write test:** Create `tests/pipeline/test_scr_extractor.py`
  ```python
  """Test Structured Chapter Representation (SCR) extractor."""
  import json
  import pytest
  from pathlib import Path
  from shenbi.pipeline.scr_extractor import (
      extract_scr,
      StructuredChapterRepresentation,
      _extract_character_locations,
      _extract_dialogue_segments,
      _extract_event_timeline,
      _extract_emotional_markers,
      _extract_hook_appearances,
      _extract_world_references,
      _extract_pov_shifts,
      _extract_decision_points,
      _compute_paragraph_stats,
      _scan_sensitive_words,
      _scan_fatigue_words,
      _scan_transition_markers,
      _extract_opening,
      _extract_closing,
      _extract_implicit_passages,
      _compute_confidence,
      extract_prose,
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
          names = {l['name'] for l in locs}
          assert '李明' in names

      def test_includes_evidence_and_line_range(self):
          locs = _extract_character_locations(SAMPLE_CHAPTER)
          for loc in locs:
              assert 'name' in loc
              assert 'evidence' in loc
              assert 'line_range' in loc

  class TestExtractDialogueSegments:
      def test_extracts_dialogue_with_speaker(self):
          segs = _extract_dialogue_segments(SAMPLE_CHAPTER)
          speakers = {s['speaker'] for s in segs}
          assert '王铁' in speakers

      def test_extracts_dialogue_text(self):
          segs = _extract_dialogue_segments(SAMPLE_CHAPTER)
          texts = [s['text'] for s in segs]
          assert any('你确定要这么做' in t for t in texts)

  class TestExtractHookAppearances:
      def test_finds_hook_ids(self):
          hooks = _extract_hook_appearances(SAMPLE_CHAPTER)
          ids = [h['hook_id'] for h in hooks]
          assert 'MH-003' in ids

  class TestExtractEventTimeline:
      def test_extracts_events(self):
          events = _extract_event_timeline(SAMPLE_CHAPTER)
          assert len(events) > 0
          for e in events:
              assert 'description' in e
              assert 'line_range' in e

  class TestComputeParagraphStats:
      def test_counts_paragraphs(self):
          stats = _compute_paragraph_stats(SAMPLE_CHAPTER)
          assert 'count' in stats
          assert stats['count'] > 0

  class TestSCRIntegration:
      def test_full_extraction_produces_valid_scr(self, tmp_path):
          chapters_dir = tmp_path / 'chapters'
          chapters_dir.mkdir()
          (chapters_dir / 'chapter-1.md').write_text(SAMPLE_CHAPTER)

          context_dir = tmp_path / 'context'
          context_dir.mkdir()

          scr = extract_scr(tmp_path, 1)
          assert scr.chapter == 1
          assert scr.total_chinese_chars > 0
          assert len(scr.character_locations) > 0
          assert 0.0 <= scr.extraction_confidence <= 1.0

      def test_scr_cached_to_disk(self, tmp_path):
          chapters_dir = tmp_path / 'chapters'
          chapters_dir.mkdir()
          (chapters_dir / 'chapter-2.md').write_text(SAMPLE_CHAPTER)

          context_dir = tmp_path / 'context'
          context_dir.mkdir()

          extract_scr(tmp_path, 2)
          cache_path = context_dir / 'chapter-2-scr.json'
          assert cache_path.exists()

          cached = json.loads(cache_path.read_text(encoding='utf-8'))
          assert cached['chapter'] == 2

      def test_cache_hit_avoids_re_extraction(self, tmp_path):
          chapters_dir = tmp_path / 'chapters'
          chapters_dir.mkdir()
          (chapters_dir / 'chapter-3.md').write_text(SAMPLE_CHAPTER)

          context_dir = tmp_path / 'context'
          context_dir.mkdir()

          scr1 = extract_scr(tmp_path, 3)
          # Second call should hit cache
          scr2 = extract_scr(tmp_path, 3)
          assert scr1.extracted_at == scr2.extracted_at  # Same timestamp = cached
  ```

- [ ] **1b. Run test -- confirm FAIL.**

- [ ] **1c. Implement** `src/shenbi/pipeline/scr_extractor.py`:

  ```python
  """Deterministic Structured Chapter Representation (SCR) extraction.

  Extracts structured facts from chapter prose once per chapter.
  Cached to disk at context/chapter-N-scr.json.
  All downstream LLM calls consume SCR fields instead of raw chapter text.
  """
  from __future__ import annotations

  import json
  import re
  from collections import Counter
  from dataclasses import dataclass, field, asdict
  from datetime import datetime, timezone
  from pathlib import Path

  from shenbi.safe_write import safe_write


  @dataclass
  class StructuredChapterRepresentation:
      chapter: int
      extracted_at: str

      # Facts-Only fields (deterministic, high precision)
      character_locations: list[dict] = field(default_factory=list)
      dialogue_segments: list[dict] = field(default_factory=list)
      event_timeline: list[dict] = field(default_factory=list)
      emotional_markers: list[dict] = field(default_factory=list)
      hook_appearances: list[dict] = field(default_factory=list)
      world_refs: list[dict] = field(default_factory=list)
      pov_shifts: list[dict] = field(default_factory=list)
      decision_points: list[dict] = field(default_factory=list)
      paragraph_stats: dict = field(default_factory=dict)
      sensitive_hits: list[dict] = field(default_factory=list)
      fatigue_word_hits: list[dict] = field(default_factory=list)
      transition_markers: list[dict] = field(default_factory=list)

      # Smart-Excerpting fields (original text preserved)
      opening_paragraph: str = ""
      closing_paragraph: str = ""
      implicit_info_passages: list[str] = field(default_factory=list)

      # Metadata
      total_chinese_chars: int = 0
      extraction_confidence: float = 0.0


  # --- META stripping ---
  _META_RE = re.compile(r'<!--META-BEGIN-->.*?<!--META-END-->', re.DOTALL)


  def extract_prose(text: str) -> str:
      """Strip META blocks and title line from chapter text."""
      text = _META_RE.sub('', text)
      # Remove H1 title line
      text = re.sub(r'^#\s+.+?\n', '', text, count=1)
      return text.strip()


  # --- Character name extraction ---
  _CHAR_NAMES_RE = re.compile(r'[\u4e00-\u9fff]{2,4}')
  _DIALOGUE_RE = re.compile(r'["""](.+?)["»"]')
  _SPEAKER_RE = re.compile(r'(.+?)(?:说|道|问|答|喊|叫|低语|轻声|沉声|冷冷|缓缓|慢慢)')

  def _extract_character_locations(prose: str) -> list[dict]:
      """Extract character appearances from dialogue attributions and narration."""
      results = []
      seen = set()

      # Find dialogue with speaker patterns
      for match in re.finditer(r'["""](.+?)["»"]\s*(.+?)(?:说|道|问|答)', prose):
          speaker_text = match.group(2).strip()
          speaker_match = re.search(r'[\u4e00-\u9fff]{2,3}', speaker_text)
          if speaker_match:
              name = speaker_match.group()
              if name not in seen:
                  seen.add(name)
                  pos = match.start()
                  line_num = prose[:pos].count('\n') + 1
                  results.append({
                      'name': name,
                      'location': 'dialogue_attribution',
                      'evidence': match.group(0)[:50],
                      'line_range': [line_num, line_num + 1],
                  })

      return results


  def _extract_dialogue_segments(prose: str) -> list[dict]:
      """Extract dialogue segments with speaker attribution."""
      results = []
      for match in re.finditer(r'(?:["""])(.+?)(?:["»"])', prose):
          text = match.group(1)
          pos = match.start()
          line_num = prose[:pos].count('\n') + 1

          # Try to find speaker from preceding context
          before = prose[max(0, pos - 30):pos]
          speaker_match = _SPEAKER_RE.search(before)
          speaker = speaker_match.group(1).strip()[-3:] if speaker_match else 'unknown'

          results.append({
              'speaker': speaker,
              'text': text[:100],
              'line_range': [line_num, line_num + 1],
              'tags': [],
          })

      return results


  def _extract_event_timeline(prose: str) -> list[dict]:
      """Extract event-like sentences from narrative text."""
      results = []
      # Split into sentences roughly
      sentences = re.split(r'[。！？\n]', prose)
      line_num = 1
      for i, sent in enumerate(sentences):
          sent = sent.strip()
          if not sent or len(sent) < 4:
              continue
          # Heuristic: events often contain specific verbs
          if re.search(r'(走|来|去|到|拿|放|看|听|说|做|打|杀|买|卖|数|算)', sent):
              results.append({
                  'description': sent[:80],
                  'line_range': [line_num, line_num + 1],
                  'characters_involved': [],
              })
      return results


  def _extract_emotional_markers(prose: str) -> list[dict]:
      """Extract emotional state indicators."""
      emotion_words = ['怒', '悲', '喜', '惧', '忧', '惊', '静', '冷', '热', '颤', '抖', '微笑', '哭泣']
      results = []
      for word in emotion_words:
          for match in re.finditer(re.escape(word), prose):
              pos = match.start()
              line_num = prose[:pos].count('\n') + 1
              ctx_start = max(0, pos - 10)
              ctx_end = min(len(prose), pos + 10)
              results.append({
                  'character': 'unknown',
                  'emotion': word,
                  'evidence': prose[ctx_start:ctx_end],
                  'confidence': 0.7,
              })
      return results


  def _extract_hook_appearances(prose: str) -> list[dict]:
      """Extract hook ID references from prose."""
      results = []
      for match in re.finditer(r'([A-Z]{2,4}-\d+)', prose):
          hook_id = match.group(1)
          pos = match.start()
          line_num = prose[:pos].count('\n') + 1
          ctx_start = max(0, pos - 30)
          ctx_end = min(len(prose), pos + 30)
          results.append({
              'hook_id': hook_id,
              'line_range': [line_num, line_num + 1],
              'context': prose[ctx_start:ctx_end],
          })
      return results


  def _extract_world_references(prose: str) -> list[dict]:
      """Extract references to world elements (locations, items, systems)."""
      results = []
      # Common world element indicators
      patterns = [
          (r'(灵石|丹药|法器|阵法|功法)', 'cultivation'),
          (r'(铜币|银币|金币|灵石)', 'currency'),
          (r'(山|河|城|镇|村|谷|林|海|原)', 'location'),
      ]
      for pat, category in patterns:
          for match in re.finditer(pat, prose):
              pos = match.start()
              line_num = prose[:pos].count('\n') + 1
              results.append({
                  'element': match.group(1),
                  'category': category,
                  'line_range': [line_num, line_num + 1],
              })
      return results


  def _extract_pov_shifts(prose: str) -> list[dict]:
      """Detect point-of-view transitions using name pattern changes."""
      results = []
      # Simplified: detect when a new character name dominates a paragraph
      paragraphs = prose.split('\n\n')
      prev_dominant = None
      for i, para in enumerate(paragraphs):
          names = re.findall(r'[\u4e00-\u9fff]{2,3}', para)
          if not names:
              continue
          # Most frequent name in paragraph
          dominant = Counter(names).most_common(1)[0][0]
          if prev_dominant and dominant != prev_dominant:
              results.append({
                  'from_pov': prev_dominant,
                  'to_pov': dominant,
                  'line_range': [i * 2, (i + 1) * 2],
              })
          prev_dominant = dominant
      return results


  def _extract_decision_points(prose: str) -> list[dict]:
      """Extract character decision moments."""
      results = []
      decision_indicators = ['决定', '选择', '下定', '毅然', '最终']
      for indicator in decision_indicators:
          for match in re.finditer(re.escape(indicator), prose):
              pos = match.start()
              line_num = prose[:pos].count('\n') + 1
              ctx_start = max(0, pos - 40)
              ctx_end = min(len(prose), pos + 40)
              results.append({
                  'character': 'unknown',
                  'decision': indicator,
                  'cause_chain': '',
                  'effect': '',
                  'line_range': [line_num, line_num + 1],
              })
      return results


  def _compute_paragraph_stats(prose: str) -> dict:
      """Compute paragraph-level statistics."""
      paragraphs = [p.strip() for p in prose.split('\n\n') if p.strip()]
      lengths = [len(p) for p in paragraphs]
      dialogue_count = sum(1 for p in paragraphs if '"' in p or '"' in p or '"' in p)

      return {
          'count': len(paragraphs),
          'lengths': lengths,
          'dialogue_density': dialogue_count / max(len(paragraphs), 1),
          'avg_length': sum(lengths) / max(len(lengths), 1),
      }


  _SENSITIVE_WORDS = ['死', '杀', '血', '尸', '鬼', '魔', '妖', '毒', '咒']

  def _scan_sensitive_words(prose: str) -> list[dict]:
      """Scan for sensitive content words."""
      results = []
      for word in _SENSITIVE_WORDS:
          for match in re.finditer(re.escape(word), prose):
              pos = match.start()
              line_num = prose[:pos].count('\n') + 1
              ctx_start = max(0, pos - 15)
              ctx_end = min(len(prose), pos + 15)
              results.append({
                  'word': word,
                  'line_range': [line_num, line_num + 1],
                  'surrounding_context': prose[ctx_start:ctx_end],
              })
      return results


  _FATIGUE_WORDS = ['骤然', '仿佛', '只见', '突然', '缓缓', '微微', '深深', '轻轻', '慢慢']

  def _scan_fatigue_words(prose: str) -> list[dict]:
      """Scan for AI fatigue indicator words."""
      results = []
      counts = {}
      for word in _FATIGUE_WORDS:
          for match in re.finditer(re.escape(word), prose):
              counts[word] = counts.get(word, 0) + 1
      for word, count in counts.items():
          if count > 0:
              results.append({
                  'word': word,
                  'count': count,
                  'line_ranges': [],
              })
      return results


  _TRANSITION_WORDS = ['接着', '然后', '之后', '随后', '此后', '不久', '过了']

  def _scan_transition_markers(prose: str) -> list[dict]:
      """Scan for temporal transition markers."""
      results = []
      for word in _TRANSITION_WORDS:
          for match in re.finditer(re.escape(word), prose):
              pos = match.start()
              line_num = prose[:pos].count('\n') + 1
              results.append({
                  'marker': word,
                  'line_range': [line_num, line_num + 1],
              })
      return results


  def _extract_opening(prose: str) -> str:
      """Extract opening paragraph of chapter body."""
      paragraphs = [p.strip() for p in prose.split('\n\n') if p.strip()]
      return paragraphs[0] if paragraphs else ''


  def _extract_closing(prose: str) -> str:
      """Extract closing paragraph of chapter body."""
      paragraphs = [p.strip() for p in prose.split('\n\n') if p.strip()]
      return paragraphs[-1] if paragraphs else ''


  def _extract_implicit_passages(prose: str) -> list[str]:
      """Extract passages containing emotional/relational implicit content."""
      results = []
      indicators = ['感到', '觉得', '想起', '记得', '似乎', '好像', '也许', '或许']
      paragraphs = prose.split('\n\n')
      for para in paragraphs:
          if any(ind in para for ind in indicators):
              if len(para) < 200:
                  results.append(para.strip())
      return results[:3]  # Cap at 3 passages


  def _compute_confidence(prose: str) -> float:
      """Estimate extraction confidence based on pattern coverage."""
      if not prose:
          return 0.0
      total_chars = len(prose)
      matched_chars = 0

      # Count characters covered by known patterns
      matched_chars += sum(len(m.group()) for m in re.finditer(r'["""].+?["»"]', prose))
      matched_chars += sum(len(m.group()) for m in re.finditer(r'[\u4e00-\u9fff]{2,4}', prose))

      return min(0.95, matched_chars / max(total_chars, 1))


  def extract_scr(project_dir: Path, chapter: int) -> StructuredChapterRepresentation:
      """Once per chapter: deterministic structured extraction from chapter prose.

      Caches result to context/chapter-N-scr.json.
      """
      cache_path = project_dir / 'context' / f'chapter-{chapter}-scr.json'

      # Return cached if available and fresh
      if cache_path.exists():
          cached = json.loads(cache_path.read_text(encoding='utf-8'))
          return StructuredChapterRepresentation(**cached)

      chapter_path = project_dir / 'chapters' / f'chapter-{chapter}.md'
      if not chapter_path.exists():
          raise FileNotFoundError(f"Chapter file not found: {chapter_path}")

      chapter_text = chapter_path.read_text(encoding='utf-8')
      prose = extract_prose(chapter_text)

      scr = StructuredChapterRepresentation(
          chapter=chapter,
          extracted_at=datetime.now(timezone.utc).isoformat(),
          character_locations=_extract_character_locations(prose),
          dialogue_segments=_extract_dialogue_segments(prose),
          event_timeline=_extract_event_timeline(prose),
          emotional_markers=_extract_emotional_markers(prose),
          hook_appearances=_extract_hook_appearances(prose),
          world_refs=_extract_world_references(prose),
          pov_shifts=_extract_pov_shifts(prose),
          decision_points=_extract_decision_points(prose),
          paragraph_stats=_compute_paragraph_stats(prose),
          sensitive_hits=_scan_sensitive_words(prose),
          fatigue_word_hits=_scan_fatigue_words(prose),
          transition_markers=_scan_transition_markers(prose),
          opening_paragraph=_extract_opening(prose),
          closing_paragraph=_extract_closing(prose),
          implicit_info_passages=_extract_implicit_passages(prose),
          total_chinese_chars=sum(1 for c in prose if '\u4e00' <= c <= '\u9fff'),
          extraction_confidence=_compute_confidence(prose),
      )

      # Cache to disk
      safe_write(cache_path, json.dumps(asdict(scr), ensure_ascii=False, indent=2))
      return scr
  ```

- [ ] **1d. Run test -- confirm PASS.**

- [ ] **1e. Commit:** `feat(pipeline): add deterministic Structured Chapter Representation (SCR) extractor`

---

## Task 2: Add 4 Deterministic Pipeline Steps

**Files:**
- `src/shenbi/pipeline/volume_align.py` -- ADD-1: volume alignment check
- `src/shenbi/skill_utils/drift_detection/linguistic_drift.py` -- ADD-3: linguistic drift detection (per Spec 4 §3.2 canonical location -- NOT `src/shenbi/pipeline/`)
- `src/shenbi/pipeline/chapter_loop.py` -- ADD-2 post-draft-extract, ADD-4 pre-revision-snapshot

**TDD Cycle:**

- [ ] **2a. Write tests:** Create test files for volume_align and linguistic_drift.

  `tests/pipeline/test_volume_align.py`:
  ```python
  """Test volume alignment checker."""
  import pytest
  from pathlib import Path
  from shenbi.pipeline.volume_align import check_volume_alignment, extract_chapter_node, extract_key_terms

  def test_extract_chapter_node(tmp_path):
      outline_dir = tmp_path / 'outline'
      outline_dir.mkdir(parents=True)
      vm = outline_dir / 'volume_map.md'
      vm.write_text("""
  ## Chapter 5: The Bridge

  Key terms: bridge, crossing, river, danger

  ### Chapter 6: The Gate

  Key terms: gate, city, guard, entry
  """)
      node = extract_chapter_node(vm, 5)
      assert node is not None
      assert 'bridge' in node['desc']

  def test_extract_key_terms():
      text = "Key terms: bridge, crossing, river, danger"
      terms = extract_key_terms(text)
      assert 'bridge' in terms

  def test_high_match_rate_no_warning(tmp_path):
      outline_dir = tmp_path / 'outline'
      outline_dir.mkdir(parents=True)
      vm = outline_dir / 'volume_map.md'
      vm.write_text("## Chapter 3: Test\n\nKey terms: copper, coin, mystery")
      issues = check_volume_alignment(tmp_path, 3, "copper coin mystery in the scrapyard")
      # Should not produce warning when key terms match
      assert not any('WARNING' in i for i in issues)

  def test_low_match_rate_warns(tmp_path):
      outline_dir = tmp_path / 'outline'
      outline_dir.mkdir(parents=True)
      vm = outline_dir / 'volume_map.md'
      vm.write_text("## Chapter 3: Test\n\nKey terms: copper, coin, mystery, smith")
      issues = check_volume_alignment(tmp_path, 3, "unrelated content about flowers")
      assert any('WARNING' in i for i in issues)
  ```

- [ ] **2b. Run test -- confirm FAIL.**

- [ ] **2c. Implement** `src/shenbi/pipeline/volume_align.py`:
  ```python
  """Volume alignment checker -- deterministic pre-planning step (ADD-1)."""
  import re
  from pathlib import Path


  def extract_chapter_node(volume_map_path: Path, chapter: int) -> dict | None:
      """Extract the chapter node from volume_map.md."""
      if not volume_map_path.exists():
          return None

      text = volume_map_path.read_text(encoding='utf-8')
      pattern = rf'##\s+Chapter\s+{chapter}[:\s]*(.+?)(?=\n##\s+Chapter|\Z)'
      match = re.search(pattern, text, re.DOTALL)

      if not match:
          # Try alternate pattern: ### Chapter N
          pattern = rf'###\s+Chapter\s+{chapter}[:\s]*(.+?)(?=\n###\s+Chapter|\Z)'
          match = re.search(pattern, text, re.DOTALL)

      if match:
          return {'desc': match.group(1).strip()}
      return None


  def extract_key_terms(text: str) -> list[str]:
      """Extract key terms from text."""
      terms = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
      return list(set(terms))


  def check_volume_alignment(
      project_dir: Path, chapter: int, plan_text: str
  ) -> list[str]:
      """Verify chapter plan aligns with volume_map. Non-blocking -- WARN only."""
      vm_path = project_dir / 'outline' / 'volume_map.md'
      node = extract_chapter_node(vm_path, chapter)

      issues = []
      if not node:
          return issues

      key_terms = extract_key_terms(node['desc'])
      if not key_terms:
          return issues

      match_count = sum(1 for t in key_terms if t in plan_text)
      match_rate = match_count / len(key_terms) if key_terms else 0

      if match_rate < 0.3:
          issues.append(
              f"Volume alignment WARNING: only {match_rate:.0%} "
              f"key terms from volume_map present in plan"
          )

      return issues
  ```

- [ ] **2d. Implement** `src/shenbi/skill_utils/drift_detection/linguistic_drift.py` (per Spec 4 §3.2 canonical location):
  ```python
  """Linguistic drift detection -- deterministic pre-audit step (ADD-3).

  Canonical location per Spec 4 §3.2: src/shenbi/skill_utils/drift_detection/
  """
  import json
  import re
  from pathlib import Path

  from shenbi.safe_write import safe_write


  def _load_baseline(project_dir: Path) -> dict:
      """Load or create linguistic baseline from early chapters."""
      baseline_path = project_dir / 'context' / 'linguistic_baseline.json'
      if baseline_path.exists():
          return json.loads(baseline_path.read_text(encoding='utf-8'))

      # Create baseline from early chapters
      baseline = {
          'system_term_density': 0,
          'em_dash_density': 0,
          'dialogue_ratio': 0,
      }
      chapters_read = 0

      for ch in range(1, 6):
          ch_path = project_dir / 'chapters' / f'chapter-{ch}.md'
          if ch_path.exists():
              text = ch_path.read_text(encoding='utf-8')
              total_chars = len(text)
              system_terms = len(re.findall(r'系统|面板|等级|技能|属性|经验', text))
              em_dashes = text.count('——') + text.count('--')
              dialogue_chars = sum(
                  len(m.group())
                  for m in re.finditer(r'["""].+?["»"]', text)
              )
              baseline['system_term_density'] += system_terms / max(total_chars, 1)
              baseline['em_dash_density'] += em_dashes / max(total_chars, 1)
              baseline['dialogue_ratio'] += dialogue_chars / max(total_chars, 1)
              chapters_read += 1

      if chapters_read > 0:
          for k in baseline:
              baseline[k] /= chapters_read

      safe_write(baseline_path, json.dumps(baseline, indent=2))
      return baseline


  def check_linguistic_drift(project_dir: Path, chapter: int) -> list[str]:
      """Run linguistic drift detection. Returns WARN alerts."""
      chapter_path = project_dir / 'chapters' / f'chapter-{chapter}.md'
      if not chapter_path.exists():
          return []

      text = chapter_path.read_text(encoding='utf-8')
      total_chars = max(len(text), 1)
      baseline = _load_baseline(project_dir)

      alerts = []

      # System term density (per mille)
      system_terms = len(re.findall(r'系统|面板|等级|技能|属性|经验', text))
      system_density = (system_terms / total_chars) * 1000
      if system_density > 30:
          alerts.append(
              f"System term density {system_density:.0f}‰ "
              f"(baseline: {baseline.get('system_term_density', 0) * 1000:.0f}‰)"
          )

      # Em-dash density (per mille)
      em_dashes = text.count('——') + text.count('--')
      em_density = (em_dashes / total_chars) * 1000
      if em_density > 20:
          alerts.append(
              f"Em-dash density {em_density:.0f}‰ "
              f"(baseline: {baseline.get('em_dash_density', 0) * 1000:.0f}‰)"
          )

      # Dialogue density check (>chapter 10, near zero dialogue)
      if chapter > 10:
          dialogue_chars = sum(
              len(m.group())
              for m in re.finditer(r'["""].+?["»"]', text)
          )
          dialogue_ratio = dialogue_chars / total_chars
          if dialogue_ratio < 0.01:
              alerts.append(
                  "Dialogue density near zero -- possible character disappearance"
              )

      return alerts
  ```

- [ ] **2e. Implement ADD-2 and ADD-4 in `src/shenbi/pipeline/chapter_loop.py`:**

  ADD-2: `post_draft_extract()` -- calls `extract_scr()` after drafting:
  ```python
  def _run_post_draft_extract(state, chapter: int) -> None:
      """Deterministic: extract SCR from freshly drafted chapter."""
      from shenbi.pipeline.scr_extractor import extract_scr
      extract_scr(state.project_dir, chapter)
  ```

  ADD-4: `pre-revision-snapshot` (lightweight, before step 18)
  Uses `_create_pre_revision_backup()` from Spec 3 (Dispatch Safety).
  This step is a simple invocation: `_create_pre_revision_backup(state.project_dir, chapter)`.
  No additional implementation needed — the function is implemented in Plan 5.

- [ ] **2f. Run tests -- confirm PASS.**

- [ ] **2g. Run `just check` -- confirm full pass.**

- [ ] **2h. Commit:** `feat(pipeline): add 4 deterministic steps (volume-align, post-draft-extract, linguistic-drift-check, pre-revision-snapshot)`

---

## Task 3: Merge 3 Foreshadowing Skills into 1 Lifecycle Call (MERGE-1)

> **Spec-aligned note:** `shenbi-foreshadowing-lifecycle` does NOT exist yet -- it must be created fresh. (The existing `shenbi-foreshadowing-plant` is also deterministically intercepted at `chapter_loop.py:1186-1192` via `plant_hooks_from_plan`; the lifecycle skill supersedes that interception. The `context-composing` interception is at `chapter_loop.py:1182-1197`.)

**Files:**
- `skills/shenbi-foreshadowing-lifecycle/SKILL.md` -- NEW combined skill (does not exist -- create it)
- `skills/shenbi-foreshadowing-plant/SKILL.md` -- mark DEPRECATED
- `skills/shenbi-foreshadowing-track/SKILL.md` -- mark DEPRECATED
- `skills/shenbi-foreshadowing-recall/SKILL.md` -- mark DEPRECATED

- [ ] **3a. Create** `skills/shenbi-foreshadowing-lifecycle/SKILL.md`:
  ```yaml
  ---
  name: shenbi-foreshadowing-lifecycle
  description: Combined foreshadowing lifecycle -- recall dormant hooks, track active hooks against chapter body, and plant new hooks from plan in a single call.
  ---

  # Foreshadowing Lifecycle

  ## Contract

  ```yaml
  contract:
    reads:
      - {file: plans/chapter-N-plan.md, fields: [7. Hook Ledger]}
      - {file: chapters/chapter-N.md}
      - {file: truth/pending_hooks.md}
      - {file: outline/volume_map.md, fields: [cross-volume bridges]}
    writes: []
    updates:
      - truth/pending_hooks.md
  ```

  ## Internal Operation Order

  Perform three sequential operations in a **single LLM call**:

  ### Phase 1: Recall

  Scan `pending_hooks.md` for hooks whose lifecycle state is DORMANT or whose
  `trigger_condition` matches the current chapter context. Decide if any should
  reactivate. Update state from DORMANT to ACTIVE where reactivation is warranted.

  ### Phase 2: Track

  For each ACTIVE hook in `pending_hooks.md`, scan the chapter body for:
  1. **References**: Is the hook mentioned or advanced?
  2. **Resolution**: Has the hook's resolution condition been met?
  3. **Lifecycle update**: Update `lifecycle_state` per hook based on findings.

  ### Phase 3: Plant

  From the chapter plan Section 7 (Hook Ledger), identify hooks that should be
  newly planted this chapter. For each:
  1. Assign a unique hook ID (format: MH-NNN or CP-NNN or sequel-specific prefix)
  2. Define `trigger_condition` and `resolve_condition`
  3. Set initial `lifecycle_state` to ACTIVE
  4. Register in `pending_hooks.md`

  ## Output Format

  ```
  ### FILE: truth/pending_hooks.md

  [Updated pending_hooks content including all lifecycle changes]

  ### FILE: audits/chapter-N-foreshadowing.md

  [Summary of recall decisions, track findings, and newly planted hooks]
  ```
  ```

- [ ] **3b. Mark** deprecated skills. Add to top of each deprecated SKILL.md:
  ```yaml
  # DEPRECATED: Superseded by shenbi-foreshadowing-lifecycle (2026-07-19).
  # This skill is retained for reference. Do not dispatch.
  ```

- [ ] **3c. Commit:** `feat(skills): merge 3 foreshadowing skills into single lifecycle call`

---

## Task 4: Group Auditors into 6 Domain-Grouped Calls (MERGE-2)

> **Spec-aligned note (Spec 6 §3.2, Appendix A):** Audit topology: only 7 core-circle auditors run as serial `CHAPTER_STEPS`; 6 genre-circle auditors are NOT `CHAPTER_STEPS` -- they dispatch dynamically and in parallel via `audit_layer.get_active_genre_audits()` as a second parallel wave. The existing two-wave parallel dispatch at `parallel_dispatch.py` (invoked at `chapter_loop.py:1090-1168`) MUST be preserved: each grouped skill dispatches as a parallel wave, not serially. Grouping core-circle and genre-circle auditors together MUST NOT regress the existing parallelism. `escalation-review` is NOT an audit step (dispatched on demand by `revision_router`).

**Files:**
- `skills/shenbi-review-group-factual/SKILL.md` -- new: continuity + world-rules + pacing
- `skills/shenbi-review-group-character/SKILL.md` -- new: character + dialogue + motivation + pov
- `skills/shenbi-review-group-craft/SKILL.md` -- new: texture + reader-pull + anti-ai
- `skills/shenbi-review-group-plan/SKILL.md` -- new: memo-compliance + foreshadowing
- `skills/shenbi-review-resonance/SKILL.md` -- keep standalone (unchanged)
- `skills/shenbi-review-sensitivity/SKILL.md` -- keep standalone (unchanged)
- individual audit SKILL.md files (core-circle + genre-circle) -- mark DEPRECATED

- [ ] **4a. Create** `skills/shenbi-review-group-factual/SKILL.md`:
  ```yaml
  ---
  name: shenbi-review-group-factual
  description: Grouped audit for factual consistency -- continuity, world rules, and pacing in one call.
  ---

  # Grouped Audit: Factual Consistency

  ## Contract

  ```yaml
  contract:
    reads:
      - {file: chapters/chapter-N.md}
      - {file: truth/world_rules.md}
      - {file: truth/chapter_summaries.md}
    writes: []
    updates:
      - audits/chapter-N-continuity.md
      - audits/chapter-N-world-rules.md
      - audits/chapter-N-pacing.md
  ```

  ## Evaluation Dimensions

  Evaluate the provided chapter from three independent dimensions.
  Score each separately. Produce three independent audit report sections.

  ### Dimension 1: Continuity (10 min)
  [Standard continuity checks: timeline, character knowledge, event causality]

  ### Dimension 2: World Rules (8 min)
  [Standard world rules checks: power system consistency, location coherence, currency logic]

  ### Dimension 3: Pacing (5 min)
  [Standard pacing checks: scene length, event density, transition quality]

  ## Output Format
  For each dimension, produce an independent audit report section using the
  standard defect evidence format (see skills/_shared/defect-evidence-format.md).
  ```

- [ ] **4b. Create** remaining grouped audit SKILL.md files with similar structure (character, craft, plan groups).

- [ ] **4c. Mark** 9 individual audit skills as DEPRECATED with the same pattern as Task 3b.

- [ ] **4d. Commit:** `feat(skills): group core-circle + genre-circle auditors into 6 domain-grouped calls preserving two-wave parallel dispatch`

---

## Task 5: Restructure CHAPTER_STEPS and Add Conditional Dispatch

**Files:**
- `src/shenbi/pipeline/chapter_loop.py` -- restructure `CHAPTER_STEPS`, add `_should_run_step`

**TDD Cycle:**

- [ ] **5a. Write test:** Create `tests/pipeline/test_chapter_steps_restructured.py`
  ```python
  """Test restructured CHAPTER_STEPS with conditional dispatch."""
  import pytest
  from unittest.mock import MagicMock, patch
  from shenbi.pipeline.chapter_loop import (
      CHAPTER_STEPS,
      _should_run_step,
  )

  def test_chapter_steps_count():
      """CHAPTER_STEPS shrinks from 20 to ~16 core steps."""
      assert len(CHAPTER_STEPS) <= 18  # ~16 core + some conditional

  def test_no_deprecated_skills_in_steps():
      """Ensure deprecated skills are not in CHAPTER_STEPS."""
      deprecated = [
          'shenbi-foreshadowing-plant',
          'shenbi-foreshadowing-track',
          'shenbi-foreshadowing-recall',
          'shenbi-context-composing',
      ]
      step_skills = [s.skill for s in CHAPTER_STEPS]
      for dep in deprecated:
          assert dep not in step_skills

  def test_escalation_review_NOT_a_step():
      """escalation-review is NOT a CHAPTER_STEPS entry (reactive dispatch).
      There is therefore no _should_run_step branch for it."""
      step_skills = [s.skill for s in CHAPTER_STEPS]
      assert 'shenbi-escalation-review' not in step_skills

  def test_intent_management_boundary_only():
      """intent-management should only run at volume boundaries."""
      state = MagicMock()
      step = MagicMock()
      step.skill = "shenbi-intent-management"
      step.conditional = True

      with patch(
          'shenbi.pipeline.chapter_loop._is_volume_boundary',
          return_value=False
      ):
          assert not _should_run_step(state, step)

      with patch(
          'shenbi.pipeline.chapter_loop._is_volume_boundary',
          return_value=True
      ):
          assert _should_run_step(state, step)
  ```

- [ ] **5b. Run test -- confirm FAIL.**

- [ ] **5c. Implement** restructured `CHAPTER_STEPS` in `src/shenbi/pipeline/chapter_loop.py` (currently 20 steps at lines 106-254):
  ```python
  from dataclasses import dataclass, field
  from typing import Literal

  @dataclass
  class StepDef:
      skill: str
      step_type: Literal["core", "audit", "context", "checkpoint"]
      conditional: str | None = None
      # Preserved from ChapterStep for backward compatibility with run_chapter_step
      output_path: str | None = None
      checkpoint: bool = False
      uses_staging: bool = False
      calls_context_assembly: bool = False
      is_audit: bool = False

  CHAPTER_STEPS = [
      # Step 1: Volume alignment (deterministic, pre-planning)
      StepDef(skill="pipeline-volume-align", step_type="checkpoint"),

      # Step 2: Chapter planning (LLM)
      StepDef(skill="shenbi-chapter-planning", step_type="core",
              output_path="plans/chapter-N-plan.md", calls_context_assembly=True),

      # Step 3: Context prepare (deterministic, merged context-assemble + curation)
      StepDef(skill="pipeline-context-prepare", step_type="context",
              calls_context_assembly=True, uses_staging=True),

      # Step 4: Chapter drafting (LLM)
      StepDef(skill="shenbi-chapter-drafting", step_type="core",
              output_path="chapters/chapter-N.md", checkpoint=True),

      # Step 5: Post-draft extract (deterministic)
      StepDef(skill="pipeline-post-draft-extract", step_type="checkpoint"),

      # Step 6: Linguistic drift check (deterministic)
      StepDef(skill="pipeline-linguistic-drift-check", step_type="audit"),

      # Step 7: Foreshadowing lifecycle (LLM, MERGE-1 -- NEW skill)
      StepDef(skill="shenbi-foreshadowing-lifecycle", step_type="core",
              output_path="truth/pending_hooks.md", uses_staging=True),

      # Step 8: State settling (LLM, runs parallel to Step 7)
      StepDef(skill="shenbi-state-settling", step_type="core",
              uses_staging=True),

      # Step 9-14: Grouped audits (LLM, MERGE-2 -- dispatch as parallel waves
      # via the existing parallel_dispatch.py, preserving the two-wave model)
      StepDef(skill="shenbi-review-group-factual", step_type="audit", is_audit=True),
      StepDef(skill="shenbi-review-group-character", step_type="audit", is_audit=True),
      StepDef(skill="shenbi-review-group-craft", step_type="audit", is_audit=True),
      StepDef(skill="shenbi-review-group-plan", step_type="audit", is_audit=True),
      StepDef(skill="shenbi-review-resonance", step_type="audit", is_audit=True),
      StepDef(skill="shenbi-review-sensitivity", step_type="audit", is_audit=True),

      # Step 15: Pre-revision snapshot (deterministic)
      StepDef(skill="pipeline-pre-revision-snapshot", step_type="checkpoint",
              checkpoint=True),

      # Step 16: Chapter revision (LLM, conditional)
      StepDef(skill="shenbi-chapter-revision", step_type="core",
              conditional=True, checkpoint=True),
  ]

  # Conditional steps (not in main list, invoked only when gates open).
  # NOTE: escalation-review is intentionally ABSENT -- it is dispatched
  # reactively from revision_router.dispatch_escalation (Spec 5), NOT from here.
  CONDITIONAL_STEPS = [
      StepDef(skill="shenbi-intent-management", step_type="core", conditional=True),
      StepDef(skill="shenbi-drift-guidance", step_type="core", conditional=True),
      StepDef(skill="shenbi-snapshot-manage", step_type="checkpoint", conditional=True),
  ]
  ```

  Add `_should_run_step()` (NO escalation-review branch -- it is reactive):
  ```python
  def _should_run_step(state, step: StepDef) -> bool:
      """Determine if a step should run based on its conditional gates.

      NOTE: escalation-review is NOT gated here -- it is dispatched reactively
      by revision_router.dispatch_escalation (see Spec 5 Task 5).
      """
      if not step.conditional:
          return True

      if step.skill == "shenbi-intent-management":
          return _is_volume_boundary(state.project_dir, state.chapter_loop.current_chapter)

      if step.skill == "shenbi-drift-guidance":
          return _drift_guidance_triggered(state)

      if step.skill == "shenbi-chapter-revision":
          return _any_audit_has_findings(state)

      return True


  def _is_volume_boundary(project_dir: Path, chapter: int) -> bool:
      """Check if chapter is at a volume boundary."""
      vm_path = project_dir / 'outline' / 'volume_map.md'
      if not vm_path.exists():
          return False
      text = vm_path.read_text(encoding='utf-8')
      pattern = rf'##\s+Volume\s+\d+.*?\n.*?Chapter\s+{chapter}[:\s]'
      return bool(re.search(pattern, text, re.DOTALL))


  def _drift_guidance_triggered(state) -> bool:
      """Check if drift guidance should run (3+ consecutive drift alerts)."""
      alerts = getattr(state, 'drift_alerts', [])
      return len(alerts) >= 3


  def _any_audit_has_findings(state) -> bool:
      """Check if any audit reported findings needing revision."""
      project_dir = state.project_dir
      chapter = state.chapter_loop.current_chapter
      audit_dir = project_dir / 'audits'

      for atype in ['continuity', 'character', 'world-rules',
                    'pacing', 'dialogue', 'motivation', 'pov',
                    'memo-compliance', 'foreshadowing', 'anti-ai',
                    'texture', 'reader-pull', 'sensitivity']:
          af = audit_dir / f'chapter-{chapter}-{atype}.md'
          if af.exists():
              text = af.read_text(encoding='utf-8')
              if 'BLOCKING' in text or 'FAIL' in text:
                  return True
      return False
  ```

- [ ] **5d. Run test -- confirm PASS.**

- [ ] **5e. Run `just check` -- confirm full pass.**

- [ ] **5f. Commit:** `feat(pipeline): restructure CHAPTER_STEPS and add conditional dispatch logic`

---

## Task 6: Parallelize foreshadowing-lifecycle || state-settling (reuse parallel_dispatch.py)

> **Spec-aligned note (Spec 6 §3.4):** Reuse the EXISTING `parallel_dispatch.py` concurrency layer (already proven by the audit waves at `chapter_loop.py:1090-1168`) for this post-drafting pair. Thread safety uses the **single-writer (actor-model) pattern**: all `PipelineState` mutations are confined to the main thread. Worker threads return `dict` results via `Future.result()`; the main thread merges them sequentially. Do NOT add a `_state_lock` -- fine-grained locking on a rich state object is explicitly rejected by the spec.

**Files:**
- `src/shenbi/pipeline/chapter_loop.py` -- add parallel post-draft dispatch that reuses `parallel_dispatch.py`
- `src/shenbi/pipeline/state.py` -- main-thread-only merge helper (single-writer pattern; NO `_state_lock`)

**TDD Cycle:**

- [ ] **6a. Write test:** Create `tests/pipeline/test_parallel_steps.py`
  ```python
  """Test parallel execution of foreshadowing-lifecycle and state-settling.

  Uses the single-writer (actor-model) pattern: workers return dict results,
  the main thread merges. No _state_lock.
  """
  import pytest
  import concurrent.futures
  from unittest.mock import MagicMock, patch
  from shenbi.pipeline.chapter_loop import run_parallel_post_draft_steps

  class TestParallelPostDraft:
      @patch('shenbi.pipeline.chapter_loop.run_chapter_step')
      def test_both_steps_executed_concurrently(self, mock_run):
          mock_run.return_value = MagicMock(success=True, result={})
          state = MagicMock()

          run_parallel_post_draft_steps(state)

          assert mock_run.call_count == 2
          skills_called = [
              c[0][1].skill
              for c in mock_run.call_args_list
          ]
          assert 'shenbi-foreshadowing-lifecycle' in skills_called
          assert 'shenbi-state-settling' in skills_called

      @patch('shenbi.pipeline.chapter_loop.run_chapter_step')
      def test_lifecycle_failure_isolated_from_settling(self, mock_run):
          def side_effect(state, step):
              result = MagicMock()
              result.success = step.skill != 'shenbi-foreshadowing-lifecycle'
              result.result = {}
              return result
          mock_run.side_effect = side_effect
          state = MagicMock()

          run_parallel_post_draft_steps(state)
          # Should not raise; lifecycle failure is logged but does not
          # block state-settling

      def test_state_merged_on_main_thread_single_writer(self):
          """Workers return dict results; the main thread merges to PipelineState.
          No _state_lock should exist -- this is the actor-model pattern."""
          import inspect
          from shenbi.pipeline import state as state_mod
          src = inspect.getsource(state_mod)
          # The single-writer pattern forbids a module-level _state_lock
          assert '_state_lock' not in src, (
              "Use single-writer (actor-model), NOT _state_lock (Spec 6 §3.4)"
          )
  ```

- [ ] **6b. Run test -- confirm FAIL.**

- [ ] **6c. Implement** parallel execution in `src/shenbi/pipeline/chapter_loop.py`, reusing the existing concurrency pattern from `parallel_dispatch.py`:
  ```python
  import concurrent.futures

  def run_parallel_post_draft_steps(state) -> None:
      """Execute foreshadowing-lifecycle and state-settling in parallel.

      Reuses the ThreadPoolExecutor + Future pattern already proven by
      parallel_dispatch.dispatch_reviews_parallel() for the audit waves.
      Worker threads return dict results; the main thread merges them
      sequentially to PipelineState (single-writer / actor-model).

      Both steps depend on drafting completion and write to disjoint files:
      - lifecycle -> pending_hooks.md
      - state-settling -> 6 truth files
      Zero data conflict.
      """
      lifecycle_step = StepDef(
          skill="shenbi-foreshadowing-lifecycle", step_type="llm"
      )
      settling_step = StepDef(
          skill="shenbi-state-settling", step_type="llm"
      )

      with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
          lifecycle_future = executor.submit(
              run_chapter_step, state, lifecycle_step
          )
          settling_future = executor.submit(
              run_chapter_step, state, settling_step
          )

          lifecycle_result = lifecycle_future.result()
          settling_result = settling_future.result()

      # Single-writer: merge results on the main thread ONLY.
      _merge_step_result(state, lifecycle_result)
      _merge_step_result(state, settling_result)

      if not lifecycle_result.success:
          logger.warning("foreshadowing_lifecycle_failed",
                         chapter=state.chapter_loop.current_chapter)

      if not settling_result.success:
          logger.warning("state_settling_failed",
                         chapter=state.chapter_loop.current_chapter)
  ```

- [ ] **6d. Implement** the main-thread merge helper in `src/shenbi/pipeline/state.py` (single-writer pattern -- NO `_state_lock`):
  ```python
  def _merge_step_result(state, result) -> None:
      """Merge a worker thread's dict result into PipelineState on the main thread.

      Single-writer (actor-model) pattern: only the main thread mutates state.
      Worker threads never touch PipelineState directly -- they return dicts.
      """
      # Apply result fields to state sequentially (main thread only).
      # Implementation depends on the result schema; e.g. update chapter_states,
      # retry_feedback, etc. No lock required -- this runs only on the main thread.
      if getattr(result, 'result', None):
          _apply_step_outputs(state, result.result)
  ```

- [ ] **6e. Run test -- confirm PASS.**

- [ ] **6f. Run `just check` -- confirm full pass.**

- [ ] **6g. Commit:** `feat(pipeline): parallelize foreshadowing-lifecycle and state-settling via parallel_dispatch pattern (single-writer)`

---

## Task 7: Add Dispatch-Level Token Logging

**Files:**
- `src/shenbi/pipeline/dispatch_helper.py` -- record `response.usage`

- [ ] **7a. Implement** token logging in `dispatch_helper.py`:
  ```python
  def _log_token_usage(response, skill_name: str, state=None) -> None:
      """Log token usage from API response."""
      if not hasattr(response, 'usage') or response.usage is None:
          return

      usage = response.usage
      logger.info(
          "llm_token_usage",
          skill=skill_name,
          prompt_tokens=usage.prompt_tokens,
          completion_tokens=usage.completion_tokens,
          total_tokens=usage.total_tokens,
      )

      if state:
          _record_token_usage(state, skill_name, usage)


  def _record_token_usage(state, skill_name: str, usage) -> None:
      """Accumulate token usage in pipeline state."""
      if not hasattr(state, 'token_usage'):
          state.token_usage = {}

      if skill_name not in state.token_usage:
          state.token_usage[skill_name] = {
              'prompt_tokens': 0,
              'completion_tokens': 0,
              'total_tokens': 0,
              'calls': 0,
          }

      rec = state.token_usage[skill_name]
      rec['prompt_tokens'] += usage.prompt_tokens
      rec['completion_tokens'] += usage.completion_tokens
      rec['total_tokens'] += usage.total_tokens
      rec['calls'] += 1
  ```

  Call `_log_token_usage(response, skill_name, state)` after every `client.chat.completions.create()` call.

- [ ] **7b.** Add end-of-pipeline summary in chapter completion:
  ```python
  def _print_token_summary(state) -> None:
      """Print token usage summary at end of pipeline."""
      if not hasattr(state, 'token_usage') or not state.token_usage:
          return

      logger.info("token_usage_summary_header", msg="Token usage by skill:")
      for skill_name, rec in sorted(state.token_usage.items()):
          avg_prompt = rec['prompt_tokens'] / max(rec['calls'], 1)
          avg_completion = rec['completion_tokens'] / max(rec['calls'], 1)
          logger.info(
              "token_usage_summary_row",
              skill=skill_name,
              avg_prompt_tokens=int(avg_prompt),
              avg_completion_tokens=int(avg_completion),
              total_tokens=rec['total_tokens'],
              calls=rec['calls'],
          )
  ```

- [ ] **7c. Commit:** `feat(pipeline): add dispatch-level token logging with end-of-run summary`

---

## Task 8: End-to-End Verification

- [ ] **8a.** Run `just check` -- confirm full pass.
- [ ] **8b.** Run 3-chapter mini-pipeline with new architecture.
- [ ] **8c.** Verify: ~16 core steps executed (down from 20 `CHAPTER_STEPS`).
- [ ] **8d.** Verify: foreshadowing-lifecycle and state-settling ran concurrently (check timing logs).
- [ ] **8e.** Verify: SCR cache files exist at `context/chapter-N-scr.json`.
- [ ] **8f.** Verify: Grouped audit output contains separate dimension reports.
- [ ] **8g.** Verify: Token usage summary printed at pipeline completion.
- [ ] **8h.** Verify: Deprecated skills cannot be reached from chapter loop.
- [ ] **8i. Commit:** `test: end-to-end verification of pipeline architecture optimization`
