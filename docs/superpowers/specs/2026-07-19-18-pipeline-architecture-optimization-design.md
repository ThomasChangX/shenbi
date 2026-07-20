# Spec 6: Pipeline Architecture Optimization Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Critical (Architecture-level reorganization)
> **Consolidates:** 4 source specs into unified pipeline step reorganization, parallelization, structured extraction, and token waste reduction
> **Source Specs:**
> - 2026-07-18-pipeline-step-reorganization-design.md
> - 2026-07-18-parallelize-pipeline-steps-design.md
> - 2026-07-18-structured-chapter-representation-design.md
> - 2026-07-17-reduce-token-waste-design.md (M1)

---

## 1. Executive Summary

The Shenbi per-chapter pipeline runs 20 `CHAPTER_STEPS` (`chapter_loop.py:106-254`), consuming roughly 337K tokens and 43 minutes per chapter. Across 56 chapters, this totals approximately 22.9M tokens and 40 hours of wall-clock time. Systematic analysis reveals that this architecture carries significant redundancy:

1. **3 foreshadowing skills** (plant, track, recall) each independently read the same `pending_hooks.md` (10KB x3) and `volume_map.md` (26KB), performing operations that could be combined into a single lifecycle call.

2. **13 auditors** each independently re-read the full 30KB chapter text (390KB total repeated reads), even though 9 of them only need structured facts (character locations, events, dialogue segments) rather than raw prose.

3. **escalation-review** (not a `CHAPTER_STEP` -- dispatched on demand by `revision_router.dispatch_escalation()`) produces 99.4% identical output across all 55 invocations -- a deterministically replaceable dispatch that wastes ~55 LLM calls.

4. **context-composing** is already replaced by deterministic code (`chapter_loop.py:1182-1197`) but still listed as an LLM step, causing confusion and bloat.

5. **The post-drafting phase runs serially** even though audit reviews are already dispatched in parallel (`parallel_dispatch.py`, invoked at `chapter_loop.py:1090-1168` in two waves). Pairs like state-settling (step 7) and foreshadowing-track (step 8) are write-disjoint (write to different truth files with zero overlap) yet still execute sequentially.

6. **No shared pre-extraction layer** exists: every audit re-parses the same 30KB chapter from scratch rather than consuming a once-extracted structured representation.

**Shared Root Cause:** The pipeline evolved organically without a systematic step-level audit. Steps were added incrementally without evaluating whether existing steps could be merged, deleted, or parallelized. No shared context extraction layer was built because each skill was designed in isolation.

**Fix Strategy:** Delete 3 redundant steps, merge 2 groups (3 foreshadowing -> 1, 13 audit skills -> 6 domain groups), add 4 deterministic steps, build a shared Structured Chapter Representation (SCR) extractor, and parallelize the write-disjoint post-drafting pair (foreshadowing-lifecycle || state-settling -- the only remaining serial pair, since audit reviews are already parallelized). Result: 20 -> 16 steps, ~24 -> ~10 LLM calls (-58%), 961KB -> 280KB input per chapter (-71%), 43min -> 17min per chapter (-60%).

---

## 2. Root Cause Analysis

### 2.1 Per-Source-Spec Root Causes

#### Spec 1: Pipeline Step Reorganization (pipeline-step-reorganization)

**Data Source:** Full audit of all 56 chapters of xinghuo-ranqiong output plus findings from 39 individual specs.

**Assessment Method:** Each of the 20 `CHAPTER_STEPS` evaluated on three dimensions:

| Dimension | Criteria |
|-----------|----------|
| Value Density | Marginal contribution of step output to final novel quality |
| Substitutability | Can deterministic code or another step replace it |
| Context Efficiency | How much input context overlaps with adjacent steps |

**Key Findings:**

- **DELETE-1 (escalation-review):** 55/56 calls produce 99.3% identical template output. Zero chapter-specific information. Deterministically replaceable.
- **DELETE-2 (intent-management):** `author_intent.md` only modified at Ch56 (end of run). `current_focus.md` only contains Ch56 data (overwrite bug CN3). Skill reads neither current chapter nor actual narrative progress. Only useful at volume boundaries.
- **DELETE-3 (context-composing):** Already intercepted by deterministic code at `chapter_loop.py:1182-1197`, but still listed in STEP definitions. Should be formally removed.
- **MERGE-1 (foreshadowing):** 3 skills share the same input dataset (pending_hooks) but call independently. Combining into a single `shenbi-foreshadowing-lifecycle` call (a new skill that does not yet exist) eliminates 2 LLM calls and 2 redundant file reads.
- **MERGE-2 (auditors):** 13 audit skills grouped by context overlap into 6 domain calls, sharing chapter text and truth files once. (Only 7 core-circle audits run as serial `CHAPTER_STEPS`; 6 genre-circle audits are already dispatched dynamically by `audit_layer.py`, and `escalation-review` is dispatched on-demand by the revision router rather than being a step.)
- **ADD-1 through ADD-4:** Four deterministic steps fill gaps: volume alignment check, post-draft fact extraction, linguistic drift detection, pre-revision backup.

#### Spec 2: Parallelize Pipeline Steps (parallelize-pipeline-steps)

**Data Source:** Pairwise read/write dependency analysis of all LLM calls in the pipeline.

**Key Finding:** The core pipeline path (Plan -> Draft -> Audit -> Revise) is necessarily serial (Write-After-Read dependency chain). **Audit reviews are already parallelized:** `src/shenbi/pipeline/parallel_dispatch.py` dispatches all core-circle + genre-circle reviews in two parallel waves via `ThreadPoolExecutor` + `Semaphore(MAX_CONCURRENT_REVIEWS=4)`, invoked at `chapter_loop.py:1090-1168`. However, in the post-drafting phase state-settling (step 7) and foreshadowing-track (step 8) -- the two halves of the proposed `foreshadowing-lifecycle` -- are still serial and write-disjoint:

| Component | Writes To |
|-----------|-----------|
| state-settling | `current_state.md`, `character_matrix.md`, `chapter_summaries.md`, `emotional_arcs.md`, `particle_ledger.md`, `subplot_board.md` |
| foreshadowing-lifecycle | `pending_hooks.md` |

Zero file overlap. Both read `chapter-N.md` (read-only, no conflict). Both depend on drafting completion (same dependency). This post-drafting pair is the remaining parallelization opportunity, and it saves 3.5 minutes per chapter.

**Critical Constraint:** `PipelineState` object must be made thread-safe for concurrent `_record_step_done` calls (note: the existing audit-wave parallel dispatch already established this pattern -- `parallel_dispatch.py` threads run concurrently and step completion is recorded in bulk after consolidation). The `safe_write` mechanism uses `fcntl.flock` per-file, so different file targets mean zero lock contention.

#### Spec 3: Structured Chapter Representation (structured-chapter-representation)

**Data Source:** Classification of all 19 LLM calls by their chapter text consumption pattern.

| Category | Count | Task Nature | Method |
|----------|-------|-------------|--------|
| Facts-Only | 9 | Information extraction / fact checking | Structured facts replace raw text |
| Smart Excerpting | 4 | Need raw text for qualitative judgment | Original relevant passages |
| Not Applicable | 5 | Need full text for creative/texture judgment | Keep full text |

**Key Insight:** 13 of 19 calls don't need the full 30KB chapter text. They need structured facts extracted from it. By extracting once and caching (Map-Reduce pattern), 390KB of repeated chapter text reading is eliminated.

**SCR Extraction Fields (15+):**
- `character_locations`: [{name, location, evidence, line_range}]
- `dialogue_segments`: [{speaker, text, line_range, tags}]
- `event_timeline`: [{description, line_range, characters_involved}]
- `emotional_markers`: [{character, emotion, evidence, confidence}]
- `hook_appearances`: [{hook_id, line_range, context}]
- `world_refs`: [{element, category, line_range}]
- `pov_shifts`: [{from_pov, to_pov, line_range}]
- `decision_points`: [{character, decision, cause_chain, effect, line_range}]
- `paragraph_stats`: {count, lengths, dialogue_density, etc.}
- `sensitive_hits`: [{word, line_range, surrounding_context}]
- `fatigue_word_hits`: [{word, count, line_ranges}]
- `transition_markers`: [{marker, line_range}]
- `opening_paragraph`: raw text
- `closing_paragraph`: raw text
- `implicit_info_passages`: raw text for emotional/relational content

#### Spec 4: Reduce Token Waste (reduce-token-waste, M1)

**Data Source:** Token consumption estimation across 56 chapters.

| Category | Token Estimate | Notes |
|----------|---------------|-------|
| Output files | ~4.1M | All output files |
| META blocks in output | ~65K | 31% per chapter stripped at consumption |
| G4 retry failures | ~170K | 35 resonance retries + 19 other retries |
| Corrupted decisions.json | ~96K | Unparseable JSON |
| Audit output | ~1.1M | 722 files |
| Estimated total waste | ~35% | -- |

**Primary Waste Sources:**
1. G4 retry loops (largest single item): 35 resonance retries at ~4K tokens each
2. META blocks transmitted in every LLM call's prompt context
3. Audit files lack quality filtering -- 722 files, some with thin content
4. No token tracking at dispatch level

**Two-Phase Approach:**
- Phase 1: Add dispatch-level token logging (`response.usage`) for observability
- Phase 2: Eliminate G4 retries via Spec 2 (resonance format fix), strip META for non-drafting calls, implement audit cascading

---

## 3. Unified Fix Strategy

### 3.1 Step Deletions (3 steps eliminated)

#### DELETE-1: Replace escalation-review with Deterministic Summary

See Spec 5 §3.4 for the correct implementation — escalation-review is NOT a CHAPTER_STEPS entry; the fix wires `check_escalation()` into the reactive dispatch path (`chapter_loop.py:414-420`). Do NOT add a branch in `_should_run_step`.

(The `_generate_deterministic_review_summary` function is defined in Spec 5 §3.4; this spec references that implementation and does not duplicate it.)

**Effect:** Eliminates 55/56 LLM calls; retains escalation capability for genuine blocking issues.

#### DELETE-2: Run intent-management Only at Volume Boundaries

```python
# chapter_loop.py -- intent-management gating

if step.skill == "shenbi-intent-management":
    volume_boundaries = _get_volume_boundaries(state.project_dir)
    current_ch = state.chapter_loop.current_chapter

    # Run only at volume boundaries, drift-guidance triggers,
    # or when author_intent.md has been manually modified
    if (current_ch not in volume_boundaries
        and not _drift_guidance_triggered(state)
        and not _author_intent_modified_since_last_run(state)):
        return False
```

**Effect:** Eliminates ~52/56 LLM calls (runs only ~4 times across 56 chapters).

#### DELETE-3: Remove context-composing from STEP List

```python
# chapter_loop.py -- CHAPTER_STEPS definition

# BEFORE: included shenbi-context-composing as a step
# AFTER: removed; deterministic code handles it in _run_context_curation()

CHAPTER_STEPS = [
    # ... other steps ...
    # shenbi-context-composing REMOVED -- handled deterministically
]
```

Mark `skills/shenbi-context-composing/SKILL.md` as DEPRECATED.

### 3.2 Step Merges (16 -> 5 calls eliminated)

#### MERGE-1: 3 Foreshadowing Skills -> 1 Lifecycle Call

**Before:** 3 independent LLM calls each reading pending_hooks.md:
- `shenbi-foreshadowing-plant` (Step 3): read plan + volume_map + pending_hooks
- `shenbi-foreshadowing-track` (Step 8): read chapter + pending_hooks
- `shenbi-foreshadowing-recall` (Step 9): read pending_hooks

**After:** Single `shenbi-foreshadowing-lifecycle` call (after drafting):

```yaml
# New skill: shenbi-foreshadowing-lifecycle
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

**Internal operation order (single LLM call):**
1. **Recall:** Scan pending_hooks for dormant hooks, decide if any should reactivate this chapter
2. **Track:** Compare chapter body against pending_hooks, update lifecycle state per hook
3. **Plant:** Extract new hooks from plan and volume_map, create and register

**Effect:**
- LLM calls: 3 -> 1 (-67%)
- pending_hooks.md reads: 3 -> 1
- volume_map context: 26KB -> ~500B (field-filtered)
- Cross-validation: plant and track in same context can verify consistency

#### MERGE-2: 13 Audit Skills -> 6 Domain-Grouped Calls

**Grouping Logic:** Auditors grouped by shared context overlap.

| Group | Merged Auditors | Shared Context | Rationale |
|-------|----------------|----------------|-----------|
| A: Factual Consistency | continuity + world-rules + pacing | chapter + world files + chapter_summaries | All check "are facts self-consistent" |
| B: Character Integrity | character + dialogue + motivation + pov | chapter + protagonist + character_matrix | All check "are characters consistent" |
| C: Craft Quality | texture + reader-pull + anti-ai | chapter + plan + genre-config | All check "is the writing good" |
| D: Plan Compliance | memo-compliance + foreshadowing | chapter + plan + pending_hooks | Both check "did we follow the plan" |
| E: Resonance Scoring | resonance | chapter + plan + style_profile + trend | Standalone -- different output format |
| F: Compliance | sensitivity | chapter + genre-config + novel.json | Standalone -- special pass/block logic |

**Grouped prompt design:**

```markdown
## Grouped Audit: Character Integrity (character + dialogue + motivation + pov)

Evaluate the provided chapter from four independent dimensions.
Score each dimension separately. Use the standard four-element
defect evidence format for any findings.

### Dimension 1: Character Consistency
[audit instructions...]

### Dimension 2: Dialogue Quality
[audit instructions...]

### Dimension 3: Motivation Plausibility
[audit instructions...]

### Dimension 4: POV Consistency
[audit instructions...]

## Output Format
For each dimension, produce an independent audit report section
using the standard defect evidence format.
```

**Effect:**
- LLM calls: 13 -> 6 (-54%)
- chapter-N.md repeated reads: 13 x 30KB -> 6 x 30KB (-54%)
- With shared context cache: 1 x 30KB shared + 6 x audit-specific instructions
- Cross-dimension validation: same LLM can detect "character OOC in dialogue" (a cross-cutting issue)

**Parallelism constraint:** Grouping core-circle and genre-circle auditors together (Group A/B/C) MUST NOT regress the existing `parallel_dispatch.py` two-wave parallel model. Each group should dispatch as a parallel wave (all skills in the group concurrently), not serially. Verify that the merged groups preserve or improve the current parallelism.

### 3.3 Step Additions (4 deterministic steps)

#### ADD-1: pipeline-volume-align (Deterministic, pre-planning)

```python
def check_volume_alignment(project_dir, chapter, plan_text):
    """Verify chapter plan aligns with volume_map. Non-blocking -- WARN only."""
    vm = (project_dir / 'outline' / 'volume_map.md').read_text()
    node = extract_chapter_node(vm, chapter)

    issues = []
    if node:
        key_terms = extract_key_terms(node['desc'])
        match_rate = sum(1 for t in key_terms if t in plan_text) / len(key_terms)
        if match_rate < 0.3:
            issues.append(f"Volume alignment WARNING: only {match_rate:.0%} "
                          f"key terms from volume_map present in plan")

        expected_chars = extract_expected_characters(vm, chapter)
        for char in expected_chars:
            if char not in plan_text:
                issues.append(f"Volume alignment WARNING: {char} expected "
                              f"this chapter per volume_map but not in plan")

    return issues  # Non-blocking, WARN only
```

#### ADD-2: pipeline-post-draft-extract (Deterministic, pre-state-settling)

```python
def extract_chapter_facts(chapter_text):
    """Deterministically extract key facts from freshly drafted chapter.
    Feeds structured guidance to state-settling instead of raw 30KB text.
    """
    return {
        'character_locations': _extract_character_locations(chapter_text),
        'emotional_state': _extract_emotional_markers(chapter_text),
        'active_conflicts': _extract_conflict_markers(chapter_text),
        'hook_appearances': _extract_hook_references(chapter_text),
        'new_characters': _extract_new_character_introductions(chapter_text),
        'key_events': _extract_event_sentences(chapter_text),
    }
```

**Rationale:** state-settling currently receives only raw chapter text (30KB) with no structural guidance. Pre-extracted facts enable:
- Reduced context for state-settling (send extraction, not full text)
- More accurate truth file updates (explicit "this is what happened")
- Clearer append-vs-overwrite decisions

#### ADD-3: pipeline-linguistic-drift-check (Deterministic, pre-audit)

```python
def check_linguistic_drift(project_dir, chapter):
    """Run linguistic drift detection every chapter. Non-conditional."""
    chapter_text = (project_dir / 'chapters' / f'chapter-{chapter}.md').read_text()
    baseline = _load_baseline(project_dir)
    metrics = compute_linguistic_drift(chapter_text, baseline)

    alerts = []
    if metrics['system_term_density'] > 30:
        alerts.append(f"System term density {metrics['system_term_density']:.0f}‰")
    if metrics['em_dash_density'] > 20:
        alerts.append(f"Em-dash density {metrics['em_dash_density']:.0f}‰")
    if metrics['dialogue_density'] < 1 and chapter > 10:
        alerts.append("Dialogue density near zero -- possible character disappearance")

    # 3 consecutive chapter triggers -> inject corrective instructions
    # into next chapter's planning prompt
    return alerts
```

#### ADD-4: pipeline-pre-revision-snapshot (Deterministic, pre-revision)

Owned by Spec 3 §3.1 (Pre-Revision Backup). This spec references that implementation — do not duplicate.

**Rationale:** Chapters 2/9/12/44/55 permanently lost because revision skill overwrote chapter body with no backup.

### 3.4 Parallelization: foreshadowing-lifecycle || state-settling

The pipeline already has a parallel-dispatch layer for audits (`src/shenbi/pipeline/parallel_dispatch.py`, invoked at `chapter_loop.py:1090-1168`). This section proposes reusing that same concurrency mechanism for the post-drafting pair. After MERGE-1 is implemented, the post-drafting phase has two write-disjoint steps:

```python
import concurrent.futures

# Step 1: drafting (must be serial -- all subsequent steps depend on it)
drafting_result = run_chapter_step(state, drafting_step)

# Step 2: lifecycle || state-settling (parallel -- zero data conflict)
# Reuses the ThreadPoolExecutor + Semaphore pattern already proven by
# parallel_dispatch.dispatch_reviews_parallel() for the audit waves.
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    lifecycle_future = executor.submit(run_chapter_step, state, lifecycle_step)
    settling_future = executor.submit(run_chapter_step, state, state_settling_step)

    lifecycle_result = lifecycle_future.result()
    settling_result = settling_future.result()

# Verify both succeeded
if not lifecycle_result.success or not settling_result.success:
    # Handle failure -- may retry one independently
    ...
```

**Safety verification:**

| Check | lifecycle | state-settling | Verdict |
|-------|-----------|----------------|---------|
| Shared dependency | drafting complete | drafting complete | Same |
| Writes to | `pending_hooks.md` | 6 truth files | Zero overlap |
| Reads other's writes | No | No | Zero read-after-write |
| Reads same files | `chapter-N.md`, `pending_hooks.md` (read) | `chapter-N.md` | Read-only, no conflict |
| Failure isolation | lifecycle fail doesn't affect truth | settling fail doesn't affect hooks | Independent retry |

**Thread safety for PipelineState:**

All `PipelineState` mutations MUST be confined to the main thread (single-writer pattern). Worker threads return results; the main thread applies them to state. This is the actor-model approach and avoids the complexity of fine-grained locking on a rich state object. Worker threads return `dict` results via `Future.result()`; the main thread merges them sequentially.

### 3.5 Shared SCR Extractor (Map-Reduce Pattern)

The Structured Chapter Representation (SCR) is extracted once per chapter via deterministic code and cached to disk. All downstream LLM calls consume relevant SCR fields instead of raw chapter text.

```python
# src/shenbi/pipeline/scr_extractor.py

@dataclass
class StructuredChapterRepresentation:
    chapter: int
    extracted_at: str

    # Facts-Only fields (deterministic, high precision)
    character_locations: list[dict]
    dialogue_segments: list[dict]
    event_timeline: list[dict]
    emotional_markers: list[dict]
    hook_appearances: list[dict]
    world_refs: list[dict]
    pov_shifts: list[dict]
    decision_points: list[dict]
    paragraph_stats: dict
    sensitive_hits: list[dict]
    fatigue_word_hits: list[dict]
    transition_markers: list[dict]

    # Smart-Excerpting fields (original text preserved)
    opening_paragraph: str
    closing_paragraph: str
    implicit_info_passages: list[str]

    # Metadata
    total_chinese_chars: int
    extraction_confidence: float

def extract_scr(project_dir: Path, chapter: int) -> StructuredChapterRepresentation:
    """Once per chapter: deterministic structured extraction."""
    chapter_text = (project_dir / 'chapters' / f'chapter-{chapter}.md').read_text()
    prose = extract_prose(chapter_text)  # Strip META block

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
    cache_path = project_dir / 'context' / f'chapter-{chapter}-scr.json'
    safe_write(cache_path, json.dumps(asdict(scr), ensure_ascii=False, indent=2))
    return scr
```

**SCR Consumer Map:**

```python
SCR_CONSUMER_MAP = {
    'shenbi-chapter-planning': ['volume_node', 'character_locations', 'event_timeline'],
    'shenbi-state-settling': ['character_locations', 'emotional_markers',
                               'event_timeline', 'hook_appearances', 'implicit_info_passages'],
    'shenbi-foreshadowing-lifecycle': ['hook_appearances', 'pending_hooks'],
    'shenbi-review-continuity': ['event_timeline', 'character_locations', 'world_refs'],
    'shenbi-review-character': ['dialogue_segments', 'emotional_markers', 'implicit_info_passages'],
    'shenbi-review-world-rules': ['world_refs', 'world_rules_summary'],
    'shenbi-review-pacing': ['event_timeline', 'paragraph_stats'],
    'shenbi-review-memo-compliance': ['plan_checklist', 'event_timeline'],
    'shenbi-review-foreshadowing': ['hook_appearances', 'pending_hooks'],
    'shenbi-review-pov': ['pov_shifts'],
    'shenbi-review-dialogue': ['dialogue_segments'],
    'shenbi-review-motivation': ['decision_points', 'implicit_info_passages'],
    'shenbi-review-reader-pull': ['opening_paragraph', 'closing_paragraph'],
    'shenbi-review-sensitivity': ['sensitive_hits'],
}
```

### 3.6 Token Waste Reduction

#### Phase 1: Dispatch-Level Token Logging (this spec)

```python
# dispatch_helper.py
def _dispatch_via_api(...):
    response = client.chat.completions.create(...)

    if hasattr(response, 'usage'):
        usage = response.usage
        logger.info("llm_token_usage",
                    skill=skill_name,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens)
        _record_token_usage(state, skill_name, usage)
```

End-of-pipeline summary:
```
Token usage by skill:
  shenbi-chapter-drafting:  avg 12,500 prompt + 8,200 completion
  shenbi-state-settling:    avg 9,100 prompt + 3,400 completion
  shenbi-review-resonance:  avg 14,200 prompt + 2,100 completion
  ...
```

#### Phase 2: Token Reduction (dependent on other specs)

1. Eliminate G4 resonance retries (Spec 2 -- resonance format fix): saves ~85-136K tokens
2. META context stripping for non-drafting calls (this spec, ADD-2): saves ~10-15% prompt tokens
3. Audit cascading: if core 4 auditors all PASS with confidence >90%, skip remaining 9 (saves ~15-20% audit tokens)

### 3.7 Resulting Pipeline: 16 Steps, 10 LLM Calls

**Before (current): 20 `CHAPTER_STEPS`, ~24 LLM calls** (the call count exceeds the step count because 6 genre-circle audits dispatch dynamically on top of the 20 steps; see Appendix A)

```
Step 1:  intent-management        [LLM]
Step 2:  chapter-planning          [LLM]
Step 3:  foreshadowing-plant       [LLM -- currently deterministic-intercepted]
Step 4:  context-assemble          [Deterministic]
Step 5:  context-composing         [LLM -- already deterministic-intercepted]
Step 6:  chapter-drafting          [LLM]
Step 7:  state-settling            [LLM]
Step 8:  foreshadowing-track       [LLM]
Step 9:  foreshadowing-recall      [LLM]
Step 10-16: 7 core-circle audits   [LLM, dispatched in parallel via parallel_dispatch.py]
Step 17: review-resonance          [LLM]
Step 18: chapter-revision          [LLM, conditional]
Step 19: snapshot-manage           [Deterministic]
Step 20: drift-guidance            [LLM]
(+ genre-circle audits)            [LLM, dynamic via audit_layer.py, parallel]
(escalation-review NOT a step -- dispatched on demand by revision_router)
```

**After (optimized): ~16 steps, ~10 LLM calls**

```
Step 1:  volume-align              [Deterministic]  <- ADD-1
Step 2:  chapter-planning          [LLM]            <- volume_map node extraction halves context
Step 3:  context-prepare           [Deterministic]  <- DELETE-3: assemble+curation merged
Step 4:  chapter-drafting          [LLM]
Step 5:  post-draft-extract        [Deterministic]  <- ADD-2
Step 6:  linguistic-drift-check    [Deterministic]  <- ADD-3
Step 7:  foreshadowing-lifecycle   [LLM]            <- MERGE-1: plant+track+recall combined
Step 8:  state-settling            [LLM]            <- supplemented with post-draft-extract context
Step 7+8 run in parallel (ThreadPoolExecutor)
Step 9:  Grouped Audit A: Facts    [LLM]            <- MERGE-2: continuity+world-rules+pacing
Step 10: Grouped Audit B: Chars    [LLM]            <- MERGE-2: character+dialogue+motivation+pov
Step 11: Grouped Audit C: Craft    [LLM]            <- MERGE-2: texture+reader-pull+anti-ai
Step 12: Grouped Audit D: Plan     [LLM]            <- MERGE-2: memo-compliance+foreshadowing
Step 13: Grouped Audit E: Score    [LLM]            <- resonance standalone
Step 14: Grouped Audit F: Compl    [LLM]            <- sensitivity standalone
Step 15: pre-revision-snapshot     [Deterministic]  <- ADD-4
Step 16: chapter-revision          [LLM]            <- conditional
(+ intent-management)              [LLM]            <- DELETE-2: volume boundary only
(+ escalation-review)              [LLM]            <- DELETE-1: escalation trigger only
(+ drift-guidance)                 [LLM]            <- conditional (drift-check alert)
(+ snapshot-manage)                [Deterministic]
```

---

## 4. Effect Summary

### 4.1 Per-Chapter Metrics

| Metric | Current | After Optimization | Improvement |
|--------|---------|-------------------|-------------|
| Total steps | 20 | 16 (+4 conditional) | -20% |
| LLM calls | ~24 | ~10 (+3 conditional) | **-58%** |
| LLM tokens | ~337K | ~130K | **-61%** |
| chapter-N.md reads | 15 | 6 (+shared cache) | -60% |
| pending_hooks.md reads | 4 | 1 (lifecycle merged) | -75% |
| volume_map full transmission | 4 | 0 (node extraction 500B) | -100% |
| Wall time | ~43 min | ~17 min | **-60%** |

### 4.2 LLM Call Reduction Breakdown

| Source | Reduction |
|--------|-----------|
| DELETE-1: escalation-review conditional | -0.9/chapter |
| DELETE-2: intent-management boundary-only | -0.9/chapter |
| DELETE-3: context-composing deterministic | -1/chapter |
| MERGE-1: 3 foreshadowing -> 1 lifecycle | -2/chapter |
| MERGE-2: 13 auditors -> 6 grouped | -7/chapter |
| **Total reduction** | **-11.8/chapter** |

### 4.3 Input Reduction from SCR

| Category | Calls | Current Input/Call | SCR Input/Call | Savings/Call | Total Savings |
|----------|-------|--------------------|-----------------|--------------|---------------|
| Facts-Only | 9 | 30-114KB | 3-8KB | 85-95% | ~400KB |
| Smart Excerpting | 4 | 30-42KB | 5-10KB | 75-85% | ~120KB |
| Not Applicable | 5 | 30-55KB | 30-55KB | 0% | 0 |
| **Total** | **18** | **961KB** | **~280KB** | **71%** | **~680KB** |

### 4.4 Cumulative Time Savings

| Optimization | Per Chapter |
|--------------|-------------|
| Current baseline | ~43 min |
| + Step reorganization (delete + merge) | ~30 min |
| + Parallelization (lifecycle || state-settling) | ~27 min |
| + SCR pre-extraction | **~17 min** |
| **Total improvement** | **-60%** |

---

## 5. Affected Files

### 5.1 Core Pipeline

| File | Change |
|------|--------|
| `src/shenbi/pipeline/chapter_loop.py` | Restructure CHAPTER_STEPS (20 -> 16); add _should_run_step conditioning; extend the existing parallel-dispatch pattern to the lifecycle + state-settling pair; integrate volume-align, post-draft-extract, linguistic-drift-check, pre-revision-snapshot |
| `src/shenbi/pipeline/parallel_dispatch.py` | Extend the existing ThreadPoolExecutor + Semaphore dispatch (currently used for audit waves) to cover the post-drafting pair |
| `src/shenbi/pipeline/dispatch_helper.py` | Add SCR consumer injection; add token logging (`response.usage` -- currently absent); strip META for non-drafting. Note: temperature is hardcoded as `_API_TEMPERATURE = 0.7` (line 49) -- optionally externalize |
| `src/shenbi/pipeline/state.py` | Single-writer pattern: worker threads return `dict` results; main thread merges them sequentially to `PipelineState` (no fine-grained locking) |

### 5.2 New Modules

| File | Purpose |
|------|---------|
| `src/shenbi/pipeline/scr_extractor.py` | Deterministic Structured Chapter Representation extraction |
| `src/shenbi/pipeline/volume_align.py` | Volume map alignment checker |
| `src/shenbi/skill_utils/drift_detection/linguistic_drift.py` | Linguistic drift detection (moved from scattered checks). See Spec 4 §3.2 for the canonical location. |
| `src/shenbi/pipeline/review_checklist.py` | Refactored: static template + dynamic deltas |

### 5.3 Skill Definitions

| File | Change |
|------|--------|
| `skills/shenbi-foreshadowing-lifecycle/SKILL.md` | New skill: combines plant+track+recall |
| `skills/shenbi-foreshadowing-plant/SKILL.md` | Mark DEPRECATED |
| `skills/shenbi-foreshadowing-track/SKILL.md` | Mark DEPRECATED |
| `skills/shenbi-foreshadowing-recall/SKILL.md` | Mark DEPRECATED |
| `skills/shenbi-context-composing/SKILL.md` | Mark DEPRECATED |
| `skills/shenbi-escalation-review/SKILL.md` | Update to document conditional dispatch |
| `skills/shenbi-review-*/SKILL.md` | Update contracts for grouped audit prompts |

### 5.4 Config

| File | Change |
|------|--------|
| `executor_config.toml` (does not yet exist -- to be created) | New config: externalize temperature/max_tokens for the new lifecycle skill (currently `_API_TEMPERATURE = 0.7` is hardcoded in `dispatch_helper.py:49`) |

---

## 6. Verification Criteria

### 6.1 Step Reorganization

1. `CHAPTER_STEPS` list reflects new 16-step structure
2. `_should_run_step` correctly gates escalation-review, intent-management
3. Grouped audit prompts produce separate dimension reports within single LLM response
4. Deprecated skills are unreachable from chapter loop

### 6.2 Parallelization

1. `ThreadPoolExecutor` used for lifecycle + state-settling after drafting (reuses the existing `parallel_dispatch.py` concurrency layer already proven by the audit waves)
2. `safe_write` produces zero deadlocks or race conditions under concurrent execution
3. `pending_hooks.md` content identical between serial and parallel execution (regression test)
4. 6 truth files content identical between serial and parallel execution
5. Failure isolation: lifecycle failure doesn't block state-settling (and vice versa)

### 6.3 SCR Extractor

1. SCR `character_locations` consistent with chapter content (spot-check 5 chapters)
2. Facts-Only calls using SCR produce audit results consistent with full-text calls (A/B test, 3 chapters)
3. Smart Excerpting calls preserve all passages with emotional/relational markers in `implicit_info_passages`
4. SCR cache hit rate 100% (no re-extraction for same chapter)
5. `extraction_confidence >= 0.85` (covers >85% of known extraction patterns)

### 6.4 Token Reduction

1. Pipeline logs include per-step token counts
2. Pipeline completion prints token usage summary by skill
3. Post-optimization retry tokens reduced by >50%

### 6.5 Global

6. `just check` full pass
7. End-to-end test: run 3-chapter mini-pipeline with new architecture

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Grouped audits reduce individual audit quality | Preserve full single-audit checklists within each grouped prompt; groups formed by natural context overlap |
| Foreshadowing lifecycle too complex as single call | Operation order is recall->track->plant, progressive; maintain independent output sections |
| intent-management boundary-only may miss mid-volume adjustments | Also run when drift-guidance triggers or author_intent manually modified |
| Deterministic steps reduce flexibility | All deterministic steps produce WARN not HARD block; LLM can override in subsequent steps |
| SCR new extraction patterns miss critical info | High-recall strategy -- extract more, not less; fall back to full text when extraction_confidence below threshold |
| Regex extraction fails on non-standard text | Multi-layer fallback: regex -> heuristic -> mark "low confidence", pass original text to LLM |
| SCR format evolution breaks cache | SCR includes version number; old versions auto-trigger re-extraction |
| Two parallel calls hit API rate limit | DeepSeek API allows >=2 concurrent; use semaphore if needed |
| PipelineState thread safety | Confine all state mutations to the main thread (single-writer); worker threads return dict results, main thread merges sequentially |

---

## 8. Dependencies

```
Spec 5 (Content Quality Gates and Review Optimization)
  └─ DELETE-1 (escalation-review conditional) detailed implementation
  └─ Review checklist split into static + dynamic
  └─ G4 sub-check infrastructure used by new deterministic steps

Execution order:
  1. Spec 5 (DELETE-1 implementation) -- unblocks escalation-review removal
  2. This Spec (MERGE-1, MERGE-2, ADD-1..4, SCR, parallelization)

### Original Code Mapping

| Original Issue Code | Consolidated Spec |
|---|---|
| step-reorg | Spec 6 (this spec) |
| parallelize | Spec 6 (this spec) |
| SCR | Spec 6 (this spec) |
| M1 | Spec 6 (this spec) |
```

---

## Appendix A: Full Current Step List (20 `CHAPTER_STEPS`)

Source of truth: `CHAPTER_STEPS` at `src/shenbi/pipeline/chapter_loop.py:106-254`.

```
1.  shenbi-intent-management           [LLM]  -- reads author_intent, audit_drift
2.  shenbi-chapter-planning            [LLM]  -- reads 7 files (83KB); staging + CHAPTER_MEMO checkpoint
3.  shenbi-foreshadowing-plant         [LLM]  -- reads plan + volume_map + hooks
4.  pipeline-context-assemble          [DET]  -- assembles context files (+ runs deterministic curation)
5.  shenbi-context-composing           [LLM]  -- intercepted by deterministic code (chapter_loop.py:1182-1197)
6.  shenbi-chapter-drafting            [LLM]  -- reads plan + context + style
7.  shenbi-state-settling              [LLM]  -- reads chapter (30KB), updates 6 truth files; staging + STATE_SETTLE checkpoint
8.  shenbi-foreshadowing-track         [LLM]  -- reads chapter + pending_hooks
9.  shenbi-foreshadowing-recall        [LLM]  -- reads pending_hooks
10. shenbi-review-anti-ai              [LLM]  -- core-circle audit
11. shenbi-review-continuity           [LLM]  -- core-circle audit
12. shenbi-review-character            [LLM]  -- core-circle audit
13. shenbi-review-pacing               [LLM]  -- core-circle audit
14. shenbi-review-foreshadowing        [LLM]  -- core-circle audit
15. shenbi-review-memo-compliance      [LLM]  -- core-circle audit
16. shenbi-review-pov                  [LLM]  -- core-circle audit
17. shenbi-review-resonance            [LLM]  -- independent resonance scoring
18. shenbi-chapter-revision            [LLM]  -- reads chapter + all audit results; conditional
19. shenbi-snapshot-manage             [DET]  -- timestamped snapshot
20. shenbi-drift-guidance              [LLM]  -- drift guidance
```

**Notes on what is NOT a serial `CHAPTER_STEP`:**

- Steps 10-16 (7 core-circle audits) are defined as serial steps but are actually dispatched in a single parallel wave via `parallel_dispatch.dispatch_reviews_parallel()` (`chapter_loop.py:1090-1168`) -- they are consolidated and the loop advances past them in bulk.
- Genre-circle audits (`review-dialogue`, `review-motivation`, `review-world-rules`, `review-texture`, `review-reader-pull`, `review-sensitivity`) are NOT `CHAPTER_STEPS`. They are dispatched dynamically as a second parallel wave based on `genre-config.json` via `audit_layer.get_active_genre_audits()`.
- `escalation-review` is NOT a step. It is dispatched on demand by `revision_router.dispatch_escalation()` only when a revision-retry ceiling or blocking-audit condition is hit.
- `shenbi-foreshadowing-lifecycle` does NOT exist yet -- it is a proposed merge of steps 3, 8, 9.

## Appendix B: SCR Field to Consumer Mapping Matrix

```
                          plan  settle  life  cont  char  world  pace  memo  fore  pov  dial  moti  read  sens
character_locations        x      x                    x                        x
dialogue_segments                            x      x                              x     x
event_timeline             x      x            x                         x
emotional_markers                x            x                                       x
hook_appearances                 x      x                              x
world_refs                                         x      x
pov_shifts                                                                    x
decision_points                                                                    x
paragraph_stats                                        x
sensitive_hits                                                                                         x
fatigue_word_hits                                                   (aux)
transition_markers                                                  (aux)
opening_paragraph                                                                           x
closing_paragraph                                                                           x
implicit_info_passages          x            x                                       x
```
