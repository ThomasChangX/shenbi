# Spec 4: Context Persistence and Linguistic Drift Prevention Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Critical
> **Consolidated from:**
> - `2026-07-17-fix-progressive-prose-collapse-design.md` (C2)
> - `2026-07-17-fix-context-assembly-persistence-gap-design.md` (H3)
> - `2026-07-17-fix-cross-chapter-template-duplication-design.md` (HN1)
> - `2026-07-17-fix-chapter-content-looping-design.md`

---

## 1. Executive Summary

The shenbi pipeline suffers from a progressive, self-reinforcing collapse of prose quality across long-generation runs. Starting around Chapter 30, natural Chinese narrative prose degrades into parameter-enumeration strings -- a regression that accelerates monotonically from 9.6 per mille system-term density at Ch30 to 135.8 per mille at Ch53. This collapse goes completely undetected by the existing drift-detection system because it only analyzes resonance scores (which are produced by an LLM that is itself contaminated by the degraded context). The root cause is a two-part feedback loop: (1) 43/56 chapters (77%) are missing their L3 compressed context files (`context/chapter-N-context.md`), so the LLM sees only parametric planning language and produces parametric prose; (2) the resulting degraded prose normalizes the resonance scorer's expectations, so score-based drift detection never triggers. Additional symptoms include cross-chapter template duplication (9 chapter-pair openings at >60% similarity) and content looping (Ch36-39 forming a 32-52% overlap cluster).

**Impact scope:** 27/56 chapters (48%) show some degree of prose degradation. Ch40 onward (17 chapters, 30%) are essentially undeliverable as literature. Template duplication creates a mechanical reading experience. Content looping means four consecutive chapters fail to advance the narrative.

---

## 2. Root Cause Analysis (Per-Source-Spec Breakdown)

### 2.1 Progressive Prose Collapse (C2, consumed into this spec)

**Discovery:** System-term density analysis across all 56 chapters:

| Phase | Chapters | System-Term Density (per mille) | "冷" Occurrences | "在场于" Occurrences | Narrative Characteristic |
|-------|----------|--------------------------------|-----------------|---------------------|--------------------------|
| Normal narrative | Ch1-15 | 0-5.5 | 0-3 | 0 | Natural Chinese prose |
| Early degradation | Ch25-29 | 5.3-11.7 | 2-33 | 0 | Parameterized phrasing appears |
| Mid degradation | Ch30-35 | 9.6-28.6 | 54-197 | 0 | "——" enumeration chains |
| Severe degradation | Ch40-45 | 33.6-74.8 | 33+ | 100+ | System-spec prose style |
| Extreme degradation | Ch46-56 | 74.8-135.8 | 114+ | 405+ | Unreadable enumeration |

**Degraded prose example (Ch50):**
> "冷知道自己在周二——冷知道周二在周一之后——冷知道周二在第二周——冷知道周一在周日之后——冷知道周日——冷知道周日不在——冷在场于周二——"

**Normal prose comparison (Ch1):**
> "他把铜线缠成圈塞进布袋。布袋里已经装了几块碎黄铜和一小截铅管，加起来不到两斤。"

**The self-reinforcing feedback loop:**

```
L3 context missing (H3)
  -> LLM sees system parameters, not narrative prose
    -> Prose degrades into parameter enumeration
      -> Resonance scorer (also an LLM) is contaminated by degraded context
        -> Scorer normalizes degraded prose as "acceptable"
          -> Drift detection based on resonance scores finds no issue
            -> No intervention -> Degradation continues and accelerates
```

**Why existing drift detection did not trigger:**

`src/shenbi/skill_utils/drift_detection/compute_drift.py:86-146` uses three trigger conditions, all based on resonance scores:
1. **Monotonic decline** (line 86-107): >=3 consecutive non-excluded chapters with cumulative decline >=3 points
2. **Below mean-2sigma** (line 109-133): >=2 consecutive chapters below mean minus 2 standard deviations
3. **Volume-level decline** (line 136-146): consecutive 2-volume score decline

**Critical flaw:** All three conditions are based on resonance scores produced by `shenbi-review-resonance` -- an LLM-based scorer. When the LLM's context window is saturated with parameterized language, the resonance scorer's judgment is also contaminated. The scorer becomes "accustomed" to degraded prose and does not assign significantly lower scores. The scoring system is measuring itself with its own corrupted instrument.

**What is missing:** The detector does not analyze the text itself -- it only analyzes scores about the text. Missing dimensions:
- System-term density ("参数", "在场于", "格式串", "槽位", "帧序列", etc.)
- Em-dash density (degraded prose uses "——" as enumeration separators)
- Short-sentence chain density (consecutive <10-character sentences)
- Pattern density ("冷在" / "冷知道"句式)
- Dialogue density (quotation mark frequency -- natural prose has dialogue)

### 2.2 Context Assembly Persistence Gap (H3, consumed into this spec)

**Discovery:** Context file coverage across 56 chapters:

| Status | Chapters | Count |
|--------|----------|-------|
| Has context | Ch1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 55, 56 | 13 (23%) |
| Missing context | Ch2, 13-54 | 43 (77%) |

**Critical correlation:** Ch13 is the exact point where context files begin to go missing en masse, and Ch30 is where system-term density begins its significant upward trend. The 17-chapter delay between context loss and visible prose degradation is consistent with the expected behavior of a gradually degrading LLM context window -- the narrative anchor erodes slowly, then collapses.

**Context generation mechanism (verified against code):**

- `chapter_loop.py:566` (`_run_context_assembly`): Calls `assemble_context` (from `context_assemble.py:209-260`) which uses Route A (entity index) + Route B (embedding search) + Route C (fixed rules). **Critical:** `assemble_context` itself does NOT write to disk — it returns a `ContextPackage`. Persistence is handled by a **separate function** `write_context_file` (`context_assemble.py:263-271`, line 270: `safe_write(out, pkg.to_markdown())`). The `_run_context_assembly` wrapper calls both (lines 575-582).
- **Persistence gap confirmed:** The entire `_run_context_assembly` body is wrapped in `try/except Exception` (lines 574, 590-591) that only does `log.warning("context_assembly_failed", ...)` — there is **no post-check verifying the file exists, and no fallback**. If `write_context_file` throws, the pipeline silently continues to chapter-drafting with no context file.
- Followed by `_run_context_curation` (`chapter_loop.py:594`) which calls `curate_context` (from `context_curation.py:81-115`). **Second persistence gap (newly discovered):** `curate_context` returns a curated 9-section string, but `_run_context_curation` (line 607) only logs its length — **the curated string is never written to disk**. The curation output is computed and discarded.
- Step 4 wiring confirmed: `chapter_loop.py:127-133` defines `ChapterStep(4, "pipeline-context-assemble", ...)`, dispatched at lines 1170-1174.

**Root cause (verified — hypotheses 1 and 2 confirmed):**
1. ~~Step 4 is skipped under certain conditions~~ — Step 4 IS wired and runs
2. **`assemble_context` returns data but persistence fails silently** — CONFIRMED: the try/except swallows errors with no post-check
3. ~~Context file is overwritten~~ — not applicable
4. ~~Context assembly only triggers at volume boundaries~~ — it runs per-chapter at step 4

**The curated context (`_run_context_curation`) is NEVER persisted** — this is a second, independent persistence failure. The 9-section L3 document that curation produces is computed and then discarded.

### 2.3 Cross-Chapter Template Duplication (HN1, consumed into this spec)

**Discovery (D25 + Agent 2):** 9 chapter-pair openings exceed 60% similarity:

| Chapter Pair | Opening Similarity | Pattern |
|-------------|-------------------|---------|
| Ch43-Ch46 | 83% | "冷知道深度在第X层——冷在第X日知道深度" |
| Ch50-Ch51 | 82% | "冷知道自己在周X——冷知道周X在周X之后" |
| Ch43-Ch45 | 81% | Same template, weekday substitution only |
| Ch51-Ch53 | 63% | Same as above |
| Ch52-Ch53 | 75% | "冷知道周X在周X之后" |

Ch41-Ch42 endings are **100% identical**.

**Impact:** These are not "stylistic consistency" -- they are template fill-in-the-blank. Readers encountering nearly identical openings in consecutive chapters perceive mechanical repetition. This is a direct symptom of the prose collapse (C2).

### 2.4 Chapter Content Looping (consumed into this spec)

**Discovery (Agent 2):** Ch36-39 form a content-overlap cluster:

| Chapter Pair | Similarity |
|-------------|-----------|
| Ch37-Ch38 (adjacent) | 45.4% |
| Ch38-Ch39 (adjacent) | 47.1% |
| Ch37-Ch39 (non-adjacent) | **51.9%** |

Non-adjacent overlap exceeding adjacent overlap indicates content is cycling through four chapters rather than advancing linearly. The narrative is looping.

---

## 3. Unified Fix Strategy

The fix operates on two fronts simultaneously: (A) restore the L3 context layer to give the LLM narrative anchors, and (B) add text-linguistic drift detection as an independent alarm system that does not rely on contaminated LLM scoring.

### 3.1 Force Persistence of `context/chapter-N-context.md` and Curated Context

**Location:** `chapter_loop.py:_run_context_assembly` (line 566) and `_run_context_curation` (line 594)

**Two persistence gaps must be fixed:**

**Gap 1: Assembly persistence failure (try/except swallows errors)**
The existing `_run_context_assembly` wraps `assemble_context` + `write_context_file` in try/except that only logs a warning. Add mandatory post-check with fallback:

```python
def _run_context_assembly(project_dir: Path, chapter: int) -> None:
    """Run context assembly -- MUST produce context/chapter-N-context.md."""
    from shenbi.pipeline.context_assemble import assemble_context, write_context_file

    context_path = project_dir / "context" / f"chapter-{chapter}-context.md"
    try:
        pkg = assemble_context(project_dir, chapter)
        write_context_file(pkg, context_path)  # explicit write call
    except Exception:
        logger.exception("context_assembly_failed", chapter=chapter)

    # HARD VERIFY: output file must exist
    if not context_path.exists():
        logger.error("context_assembly_no_output", chapter=chapter)
        # Fallback: write minimal context (Route C fixed rules only)
        _write_minimal_context(project_dir, chapter)
```

**Gap 2: Curated context is computed but never written (newly discovered)**
`_run_context_curation` (line 594-608) calls `curate_context()` which returns a curated string, but the return value is only logged, never persisted:

```python
def _run_context_curation(project_dir: Path, chapter: int) -> None:
    """Run context curation -- MUST persist curated context."""
    from shenbi.pipeline.context_curation import curate_context
    from shenbi.safe_write import safe_write

    curated_path = project_dir / "context" / f"chapter-{chapter}-curated.md"
    try:
        curated = curate_context(project_dir, chapter)
        # FIX: Actually write the curated output (currently discarded!)
        safe_write(curated_path, curated)
    except Exception:
        logger.exception("context_curation_failed", chapter=chapter)

    if not curated_path.exists():
        logger.error("context_curation_no_output", chapter=chapter)
```

**Startup coverage audit** (at pipeline resume initialization):

```python
def _audit_context_coverage(project_dir: Path, state: PipelineState) -> dict:
    """Audit context file coverage for all completed chapters."""
    missing = []
    for ch in range(1, state.chapter_loop.current_chapter):
        ctx_path = project_dir / "context" / f"chapter-{ch}-context.md"
        if not ctx_path.exists():
            missing.append(ch)

    if missing:
        logger.warning("context_coverage_gap", missing_chapters=missing,
                       gap_ratio=f"{len(missing)}/{state.chapter_loop.current_chapter - 1}")

    return {"missing": missing, "total": state.chapter_loop.current_chapter - 1}
```

**Backfill command** for existing gaps:

```bash
uv run pipeline backfill-context <project_dir> --chapters 13-54
```

Backfill logic runs `assemble_context` + `curate_context` for each missing chapter. These are deterministic functions and can be re-executed safely.

### 3.2 Create Linguistic Drift Detector

**Location:** New file `src/shenbi/skill_utils/drift_detection/linguistic_drift.py`

**Module location (canonical):** `src/shenbi/skill_utils/drift_detection/linguistic_drift.py` — co-located with the existing `compute_drift.py`. Spec 6's ADD-3 reference to `src/shenbi/pipeline/linguistic_drift.py` is SUPERSEDED — all drift detection code lives under `skill_utils/drift_detection/`.

**Design rationale — these are pragmatic domain-specific alarm detectors, NOT industry-standard stylometry.** Classical stylometry (Burrows' Delta, Zeta, n-gram authorship attribution) uses function-word frequencies, type-token ratio, Yule's K lexical diversity. The 5 metrics proposed here are **ad hoc surface counters tuned to the specific observed failure mode** (system-term leakage, em-dash enumeration, pattern fingerprinting). They are deliberately cheap, deterministic, and independent of LLM scoring — which is the actual goal (an alarm system that works even when the LLM scorer is contaminated). State-of-the-art linguistic drift detection uses embedding-based novelty (sentence-embedding cosine), repetition metrics (distinct-n, self-BLEU), perplexity probes, and Burrows' Delta on sliding windows. These could be future enhancements (see Shout-Out spec), but the proposed metrics are sufficient as a gap-filling first alarm.

Create a text-analysis-based drift detector with five metrics:

```python
import re
from difflib import SequenceMatcher

# System terms that indicate parametric/prose degradation
SYSTEM_TERMS = re.compile(
    r'(参数|系统|格式串|历法|槽位|帧序列|阈值|在场于|'
    r'知道.{0,10}在|Phase\s+\d|MH-\d+|P[012]\.\d+)'
)

# **Important:** `SYSTEM_TERMS` and the `pattern_density` fingerprints
# (`冷在`, `冷知道`) are project-specific. They MUST be moved to a
# per-project configuration file (e.g.,
# `genre-config.json -> drift_detection.system_terms`) rather than
# hardcoded. Additionally, a generic frequency-divergence alarm should be
# added as a second-tier check: compute the baseline vocabulary
# distribution from the first 3 chapters and flag ANY term whose
# frequency diverges >3σ from baseline. This catches novel-specific
# degradation patterns without hardcoding.

def compute_linguistic_metrics(chapter_text: str) -> dict:
    """Compute linguistic metrics for a chapter's prose text.

    Returns dict with 5 metrics, each normalized per mille of text length.
    """
    text_len = max(len(chapter_text), 1)

    metrics = {
        # 1. System term density -- parametric language indicator
        'system_term_density': len(SYSTEM_TERMS.findall(chapter_text)) / text_len * 1000,

        # 2. Em-dash density -- enumeration separator in degraded prose
        'em_dash_density': chapter_text.count('——') / text_len * 1000,

        # 3. Short-sentence chain density -- consecutive <=15 char sentences
        'short_sentence_chain_density': _short_chain_chars(chapter_text) / text_len * 1000,

        # 4. Pattern density -- "冷在"/"冷知道"句式 fingerprint of degradation
        'pattern_density': (
            chapter_text.count('冷在') + chapter_text.count('冷知道')
        ) / text_len * 1000,

        # 5. Dialogue density -- quotation mark frequency, proxy for natural conversation
        'dialogue_density': chapter_text.count('"') / text_len * 1000,
    }

    return metrics


def _short_chain_chars(text: str) -> int:
    """Count characters in chains of 5+ consecutive short sentences (<=15 chars)."""
    short_sents = re.findall(r'(?:[^。]{1,15}。){5,}', text)
    return sum(len(s) for s in short_sents)


def compute_linguistic_drift(chapter_text: str, baseline: dict) -> dict:
    """Compute linguistic drift as deviation from baseline metrics.

    Returns dict with 'metrics', 'deviations' (per-metric), and 'max_deviation'.
    """
    metrics = compute_linguistic_metrics(chapter_text)

    deviations = {}
    for key, value in metrics.items():
        if key in baseline and baseline[key] > 0:
            deviations[key] = abs(value - baseline[key]) / baseline[key]

    max_deviation = max(deviations.values()) if deviations else 0.0

    return {
        'metrics': metrics,
        'deviations': deviations,
        'max_deviation': max_deviation,
    }
```

### 3.3 Add 4th Trigger Condition to Drift Detection

**Location:** `compute_drift.py` (after line 146, after `detect_volume_drift`)

Add a linguistic drift trigger condition alongside the three existing score-based conditions:

```python
def check_linguistic_drift_trigger(chapter_text: str, baseline_metrics: dict) -> tuple[bool, str]:
    """Check if linguistic drift exceeds trigger thresholds.

    Returns (triggered, severity_level).

    Thresholds:
        - Any single metric deviation > 500% from baseline triggers
        - Severity based on system_term_density absolute value
    """
    result = compute_linguistic_drift(chapter_text, baseline_metrics)

    if result['max_deviation'] <= 5.0:  # 500% threshold
        return False, "normal"

    density = result['metrics']['system_term_density']

    if density > 100:
        return True, "ESCALATE"
    elif density > 50:
        return True, "HARD"
    else:
        return True, "WARN"
```

### 3.4 Three-Tier Intervention Strategy

When linguistic drift is detected, apply tiered intervention:

| Tier | Trigger | Action |
|------|---------|--------|
| **WARN** | density 30-50 per mille, or moderate deviation | Inject corrective directive into next chapter's PRE_WRITE_CHECK: "Avoid parametric language; use natural dialogue and concrete sensory detail" |
| **HARD** | density >50 per mille, or >500% deviation | Force-trigger `shenbi-drift-guidance` skill; write specific corrective instructions to `audit_drift.md`; inject mandatory style constraints |
| **ESCALATE** | density >100 per mille, or >1000% deviation | Pause auto-generation; trigger human review checkpoint; require manual approval before continuing |

**Intervention injection point** -- in `_should_run_step` or chapter planning prompt assembly (`chapter_loop.py`, around the drift-guidance trigger):

```python
# After linguistic drift check, before chapter planning
triggered, severity = check_linguistic_drift_trigger(chapter_text, baseline_metrics)
if triggered:
    corrective_directive = _build_corrective_directive(severity, result)
    # Inject into next chapter's planning context
    state.chapter_loop.next_chapter_context_override = corrective_directive
```

### 3.5 Establish Baselines from Bootstrap or First 3 Chapters

**Location:** Integrated into `shenbi-style-learning`'s `compute_stats.py` and the new `linguistic_drift.py`

Baseline establishment strategy:

1. **Primary source:** `style/style_profile.md` after first formal extraction (Chapter 3+)
2. **Fallback:** Compute from the first 3 completed chapters' prose text
3. **Bootstrap:** If fewer than 3 chapters exist, use seed-fingerprint approximations

```python
def establish_linguistic_baseline(project_dir: Path, state: PipelineState) -> dict:
    """Establish linguistic baseline metrics from available chapters."""
    # Try style_profile first
    style_profile = project_dir / "style" / "style_profile.md"
    if style_profile.exists():
        # Extract linguistic baseline from style profile
        baseline = _extract_baseline_from_style_profile(style_profile)
        if baseline:
            return baseline

    # Fallback: compute from first 3 completed chapters
    completed = min(state.chapter_loop.current_chapter - 1, 3)
    if completed >= 1:
        chapter_texts = []
        for ch in range(1, completed + 1):
            ch_path = project_dir / "chapters" / f"chapter-{ch}.md"
            if ch_path.exists():
                chapter_texts.append(ch_path.read_text())

        if chapter_texts:
            combined = "\n".join(chapter_texts)
            return compute_linguistic_metrics(combined)

    # Bootstrap: return conservative defaults
    return _bootstrap_baseline()
```

### 3.6 Opening Similarity Check

**Location:** `linguistic_drift.py` (new function), triggered before chapter planning

```python
def check_opening_similarity(prev_chapter_text: str, current_chapter_text: str,
                              threshold: float = 0.6, chars: int = 300) -> str | None:
    """Check if chapter openings are too similar.

    Returns warning string if similarity exceeds threshold, None otherwise.
    """
    prev_open = prev_chapter_text[:chars]
    curr_open = current_chapter_text[:chars]
    ratio = SequenceMatcher(None, prev_open, curr_open).ratio()

    if ratio > threshold:
        return f"OPENING_DUPLICATE: {ratio:.0%} similarity in first {chars} characters"
    return None
```

**Intervention:** When opening similarity exceeds 60%, inject into next chapter's PRE_WRITE_CHECK:
- "Previous chapter opening is {ratio}% similar to this one. Use a different opening approach."
- "Prohibited: '冷知道/冷在/冷在场于'句式 as opening"

### 3.7 Sliding Window Content Looping Check

**Location:** `linguistic_drift.py` (new function), integrated into drift detection pipeline

```python
def check_window_redundancy(chapter_texts: list[str], window_size: int = 4,
                             threshold: float = 0.35) -> str | None:
    """Detect content looping within a sliding window of chapters.

    Returns warning string if max pairwise similarity in window exceeds threshold.
    """
    if len(chapter_texts) < window_size:
        return None

    window = chapter_texts[-window_size:]
    max_sim = 0.0

    for i in range(len(window)):
        for j in range(i + 1, len(window)):
            sim = SequenceMatcher(None, window[i], window[j]).ratio()
            max_sim = max(max_sim, sim)

    if max_sim > threshold:
        return f"WINDOW_REDUNDANCY: max_sim={max_sim:.0%} in {window_size}-chapter window"
    return None
```

### 3.8 Inject Corrective Directives into Chapter Planning

All drift detection results (linguistic, opening similarity, content looping) are consolidated and injected into the next chapter's planning context before the drafting skill runs.

**Integration point:** In `chapter_loop.py`, before dispatching `shenbi-chapter-drafting` (or in the PRE_WRITE_CHECK phase of chapter planning):

```python
# Consolidate all drift warnings
drift_warnings = []

# Linguistic drift check
triggered, severity = check_linguistic_drift_trigger(current_text, baseline)
if triggered:
    drift_warnings.append(_build_corrective_directive(severity, result))

# Opening similarity check
opening_warning = check_opening_similarity(prev_text, current_text)
if opening_warning:
    drift_warnings.append(opening_warning)

# Content looping check
recent_texts = _load_recent_chapter_texts(project_dir, chapter, window=4)
looping_warning = check_window_redundancy(recent_texts)
if looping_warning:
    drift_warnings.append(looping_warning)

# Inject into next chapter planning context
if drift_warnings:
    state.chapter_loop.drift_corrective_context = "\n".join(drift_warnings)
```

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/pipeline/chapter_loop.py:566` (`_run_context_assembly`) | Replace error-swallowing try/except with explicit `write_context_file` call + post-check + fallback | Force persistence of L3 context; close 77% coverage gap |
| `src/shenbi/pipeline/chapter_loop.py:594` (`_run_context_curation`) | **Add `safe_write` for curated output** (currently computed and discarded) | Close newly-discovered second persistence gap |
| `src/shenbi/pipeline/context_assemble.py:209-260` (`assemble_context`) + `:263-271` (`write_context_file`) | Reference only (already correct structure) | Assembly returns ContextPackage; write is separate function — spec must use both |
| `src/shenbi/pipeline/chapter_loop.py` (resume entry) | Add `_audit_context_coverage()` | Surface context gaps at pipeline start |
| `src/shenbi/pipeline/cli.py` (new command) | Add `backfill-context` CLI command | Allow backfilling context files for already-generated chapters |
| `src/shenbi/skill_utils/drift_detection/linguistic_drift.py` (new file) | Create linguistic drift detector with 5 metrics | Add text-based detection independent of LLM scoring |
| `src/shenbi/skill_utils/drift_detection/compute_drift.py:147` (after) | Add `check_linguistic_drift_trigger()` as 4th trigger condition | Integrate linguistic drift into existing detection framework |
| `src/shenbi/skill_utils/drift_detection/linguistic_drift.py` | Add `check_opening_similarity()` | Detect template-duplicate chapter openings |
| `src/shenbi/skill_utils/drift_detection/linguistic_drift.py` | Add `check_window_redundancy()` | Detect content looping in sliding 4-chapter windows |
| `src/shenbi/pipeline/chapter_loop.py` (pre-drafting) | Inject corrective directives from drift detection into planning context | Close the loop: detect -> intervene |
| `skills/shenbi-style-learning/SKILL.md` | Add linguistic baseline extraction instructions | Ensure style learning captures text metrics, not just scores |
| `skills/shenbi-drift-guidance/SKILL.md` | Add linguistic correction directives for HARD/ESCALATE tiers | Give LLM concrete anti-drift writing instructions |

---

## 5. Verification Criteria

1. **Context persistence** (`tests/unit/pipeline/test_context_assembly.py`):
   - Run `assemble_context` -> assert `context/chapter-N-context.md` exists
   - Run `_audit_context_coverage` -> correctly report missing chapters
   - Mini-pipeline (3 chapters): every chapter has context file

2. **Linguistic drift detector** (`tests/unit/skill_utils/test_linguistic_drift.py`):
   - Normal prose (Ch1 excerpt) -> `max_deviation < 1.0` from baseline
   - Degraded prose (Ch50 excerpt) -> `max_deviation > 5.0`, `system_term_density > 50 per mille`
   - Baseline correctly computed from normal prose chapters

3. **Opening similarity:**
   - Two identical openings -> `check_opening_similarity()` returns warning with ratio >= 90%
   - Two distinct openings -> returns None
   - Threshold 60% correctly distinguishes template duplication from coincidental similarity

4. **Content looping:**
   - 4 chapters with 45% max pairwise similarity -> `check_window_redundancy()` triggers
   - 4 chapters with 20% max pairwise similarity -> does not trigger
   - Non-adjacent similarity properly detected (Ch37-Ch39 case)

5. **Three-tier intervention:**
   - WARN tier: corrective directive injected but pipeline continues
   - HARD tier: `shenbi-drift-guidance` forcibly triggered
   - ESCALATE tier: pipeline pauses for human review

6. **End-to-end validation:**
   - Generate 10+ chapters with fixed pipeline
   - Monitor system-term density trend -- must not monotonically increase
   - Chapter opening similarity <= 40% for any 5 consecutive chapters
   - Any 4-chapter sliding window max similarity <= 35%

7. **Regression:** `just check` passes fully

---

## 6. Dependencies

```
Spec 4 (this spec, Context Persistence and Linguistic Drift Prevention)
    |
    +---> Depends on: Spec 1 (Truth File and State Accumulation) -- needs resonance_trend.md data for baseline
    +---> Depends on: Spec 2 (Output Validation and Format Enforcement) -- needs valid JSON decisions for planning context
    +---> Depends on: Spec 3 (Dispatch Safety and File Integrity) -- snapshot integrity enables recovery if drift requires rollback

Prerequisites:
    - H3's context assembly mechanism (consumed into this spec, Spec 4)
    - compute_drift.py existing framework (extended, not replaced)
```

### 6.1 Original Issue Code Mapping

| Original Issue Code | Description | Consolidated To |
|---|---|---|
| C2 | Progressive Prose Collapse | Spec 4 (this spec) |
| H3 | Context Assembly Persistence Gap | Spec 4 (this spec) |
| HN1 | Template Duplication | Spec 4 (this spec) |
| content-looping | Chapter Content Looping | Spec 4 (this spec) |
| CN1 | 主角消失 (Protagonist Disappearance) | Spec 1 |
| CN2 | Hook System Bifurcation | Spec 1 |
| CN3 | Truth File Overwrite | Spec 1 |
| CN4 | Resonance Score Null | Spec 1 |
| CN5 | Style Learning Never Updated | Spec 1 |
| CN6 | Pipeline State Stale Data | Spec 1 |
| H1 | JSON Corruption | Spec 2 |
| H2 | Revision System Failure | Spec 2 |
| M5 | G4 Format Mismatch | Spec 2 |
| C1 | Revision Overwrite Chapter Content | Spec 3 |
| H4 | Staging Residue Leak | Spec 3 |
| M3 | Snapshot Coverage Gaps | Spec 3 |
| LN1-LN3 | Snapshot Bloat / Lockfile / Budget Copy | Spec 3 |
| title-degradation, plan-content-mismatch, RS1, static-review-checklist | Review Quality Issues | Spec 5 |
| step-reorganization, parallelize, SCR, M1 | Pipeline Architecture | Spec 6 |
| maturity-bp-fixes, crash-recovery, runtime-optimizations, L1-L3, M2, H5, M4 | Pipeline Infrastructure | Spec 7 |
| llm-context-optimization | LLM Context Engineering | Spec 8 |
| volume-map, character-archive, C3 | Content Planning and Deliverable Design | Spec 9 |
| gate-markers, review-checklist-static, snapshot-differential | Data Storage Optimization | Spec 10 |
| validation, chapter-size-time | End-to-End Validation Protocol | Spec 11 |
