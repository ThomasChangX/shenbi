# Spec 5: Content Quality Gates and Review Optimization Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Critical / High
> **Consolidates:** 4 source specs into unified quality enforcement and review optimization strategy
> **Source Specs:**
> - 2026-07-17-fix-chapter-title-degradation-design.md
> - 2026-07-17-fix-plan-content-mismatch-and-factual-errors-design.md
> - 2026-07-17-fix-review-summary-all-identical-design.md (RS1)
> - 2026-07-17-fix-static-review-checklist-design.md

---

## 1. Executive Summary

The Shenbi novel pipeline produces 56 chapters across a 40-hour continuous run, yet four systemic quality failures undermine the output:

1. **Chapter titles degrade** from poetic single/double-character names (Ch1-16: "废料场", "痕迹", "沉") to date-label placeholders (Ch36-56: "Saturday", "第四周Saturday", "第五周周五"), including duplicate titles ("又一天" x2, "Saturday" x2) and a rule violation at Ch40 ("第40章" -- forbidden by SKILL.md).

2. **Plan-content mismatches go undetected**: Ch20's plan Section 7 Hook Ledger explicitly requires MH-003 advancement, but the chapter body contains zero MH-003 references. The continuity auditor observed this but flagged it only as a "suggestion" rather than a defect.

3. **Review summaries are 99.4% identical** across all 55 chapters: the `escalation-review` skill is dispatched reactively (only on retry exhaustion from `revision_router.dispatch_escalation` at `chapter_loop.py:414-420`, or on closure failure at `cli.py:284`), yet produces a static template ("Reviews executed: 11, Successful: 11, Failed: 0") with zero chapter-specific information when it does run. *Verified: `escalation-review` is NOT a `CHAPTER_STEPS` entry -- it is not dispatched 55 times unconditionally per chapter. Each dispatch that does occur still produces templated output.* (See Appendix B for the similarity analysis basis.)

4. **Review checklists appear static in output**: `context/review-checklist-N.json` shows `ai_blacklist` stuck at 14 items and `hook_deliverables` at 0 across observed chapters -- even though the story evolves and chapter plans declare hooks. *Verified against `src/shenbi/pipeline/review_checklist.py` (477 lines): the checklist is NOT frozen at Genesis. It uses mtime-based cache invalidation (`_get_max_source_mtime`, lines 195-224) comparing genre-config, chapter file, and `truth/` mtimes against the cache mtime, and `hook_deliverables` IS populated via `_extract_hook_deliverables` (lines 314-374) reading `truth/pending_hooks.md`. The static-output symptom persists despite regeneration logic existing -- see §2.4 for the real root cause.*

**Shared Root Cause:** Missing G4 quality enforcement for chapter titles, hook fulfillment, arithmetic consistency, and factual accuracy. *Verified: G4 is a package at `src/shenbi/gates/g4/` (one module per skill, e.g. `g4/chapter_drafting.py`, `g4/escalation_review.py`) -- there is no `g4.py`.* The `escalation-review` dispatch, while already reactive (not unconditional), produces templated output when it does run, and the deterministic escalation helper at `src/shenbi/skill_utils/escalation/check.py` exists but is never wired into dispatch decisions.

**Fix Strategy:** Introduce G4 sub-checks for titles, hook fulfillment, and arithmetic consistency (verified: both `G4.cd.title` and `G4.cd.hook_fulfillment` are genuine gaps -- neither exists yet in `g4/chapter_drafting.py`). Wire the EXISTING-but-unwired `check_escalation()` helper (`src/shenbi/skill_utils/escalation/check.py`) into the reactive escalation-review dispatch path so templated LLM reports are only produced when signals are non-empty. Diagnose why the EXISTING `_extract_hook_deliverables` (`review_checklist.py:314-374`, reads `truth/pending_hooks.md`) and mtime-based invalidation (`_get_max_source_mtime`, lines 195-224) yield static output despite already being implemented -- the fix targets the data/trigger path, not re-adding extraction.

---

## 2. Root Cause Analysis

### 2.1 Per-Source-Spec Root Causes

#### Spec 1: Chapter Title Degradation (fix-chapter-title-degradation)

**Symptom:** Titles evolve from poetic names to date labels. Duplicate titles appear. Ch40 uses "第40章" in violation of SKILL.md line 125.

**Root Cause:** No automated enforcement of chapter title rules. The planning prompt lacks title quality constraints. No G4 gate checks title conformance.

**Data Evidence:**

| Phase | Title Examples | Pattern |
|-------|---------------|---------|
| Ch1-16 | 废料场, 痕迹, 沉, 见, 持, 晨 | Poetic single/double character |
| Ch25-35 | 秋, 又一天, 冷, 三天 | Transitional |
| Ch36-56 | Saturday, 第四周Saturday, 第五周周五, 周三 | Date labels |

#### Spec 2: Plan-Content Mismatch and Factual Errors (fix-plan-content-mismatch-and-factual-errors)

**Symptom:** Ch20 plan declares MH-003 advancement but chapter body has zero MH-003 presence. Three factual arithmetic errors across Ch10 (copper coin miscount: "四十六枚半" vs correct ~40.5), Ch35 (beam count: "十六张" vs correct 15), Ch50 (date discrepancy: "五日" vs "四日").

**Root Cause:** No cross-validation between chapter plan hook ledger and chapter body. Continuity audit prompt lacks explicit arithmetic verification instructions.

#### Spec 3: Review Summary All Identical (fix-review-summary-all-identical, RS1)

**Symptom:** All 55 `audits/chapter-N-review-summary.md` files share 99.4% pairwise similarity. The only variation is the chapter number. Content is a static template:

```
# Chapter N -- Consolidated Review Results
- **Reviews executed**: 11
- **Successful**: 11
- **Failed**: 0
```

**Root Cause:** `shenbi-escalation-review` is dispatched reactively (on retry exhaustion via `revision_router.dispatch_escalation` at `chapter_loop.py:414-420`, and on closure failure at `cli.py:284`) -- NOT as a regular per-chapter `CHAPTER_STEPS` entry. *Verified: `escalation-review` does not appear in the `CHAPTER_STEPS` list (steps 1-20); the "55 unconditional dispatches" framing is inaccurate.* However, when escalation-review does dispatch, the LLM produces a fixed template regardless of actual audit results, and a deterministic helper `check_escalation()` exists at `src/shenbi/skill_utils/escalation/check.py` (returns `list[EscalationSignal]`) that was intended to gate execution -- but it is never imported or called by `chapter_loop.py` or `_should_run_step`. *Verified: the conditional gate logic exists in isolation but is not wired into the dispatch path.*

#### Spec 4: Static Review Checklist (fix-static-review-checklist)

**Symptom:** `context/review-checklist-N.json` *appears* static across Ch1, Ch20, Ch40, Ch55 in the frozen fields (`ai_blacklist`, `hook_deliverables`), though note `transition_budget` already varies (5/8/5/10) in the data below -- so the checklist is not wholly frozen:

| Field | Ch1 | Ch20 | Ch40 | Ch55 |
|-------|-----|------|------|------|
| transition_budget | 5 | 8 | 5 | 10 |
| ai_blacklist | 14 items | 14 items | 14 items | 14 items |
| hook_deliverables | 0 | 0 | 0 | 0 |

**Root Cause:** *Verified against `src/shenbi/pipeline/review_checklist.py`: the checklist is NOT generated once and frozen. It already has mtime-based cache invalidation (`_get_max_source_mtime`, lines 195-224) comparing genre-config, chapter file, and `truth/` mtimes against the cache mtime, and `hook_deliverables` IS populated via `_extract_hook_deliverables` (lines 314-374) which reads `truth/pending_hooks.md` (PLANTED/ACTIVE/PENDING hooks with urgency classification). The regeneration and extraction logic exists and runs when sources change.* The observed static output (blacklist stuck at 14, hook_deliverables at 0) therefore reflects a different failure: either the source `truth/pending_hooks.md` is not being updated with the right state, or the extraction's filter (PLANTED/ACTIVE/PENDING) excludes the hooks that should appear, or the observed samples coincided with cache hits. The fix is to diagnose why the existing extraction yields empty results in practice, not to add extraction that already exists.

---

## 3. Unified Fix Strategy

### 3.1 G4.cd.title Checks: Chapter Title Quality Enforcement

Introduce a new G4 sub-gate `G4.cd.title` that runs post-planning (when the title is assigned in the chapter plan) and post-drafting (to catch title drift in the final chapter output).

```python
# g4/chapter_drafting.py -- new check

def check_chapter_title(title: str, previous_titles: dict[str, int]) -> list[str]:
    """G4.cd.title: Validate chapter title quality.

    Checks:
    - No chapter numbers in title
    - No duplicate titles
    - No day-of-week labels (WARN, not HARD)
    - Thematic naming encouraged (1-4 Chinese characters)
    """
    issues = []

    # HARD FAIL: Chapter number in title
    if re.search(r'第\d+章', title):
        issues.append("G4.cd.title:contains_chapter_number -- "
                       "title must not include chapter number (SKILL.md:125)")

    # HARD FAIL: Duplicate title
    if title in previous_titles:
        issues.append(f"G4.cd.title:duplicate_of_ch{previous_titles[title]} -- "
                       f"title '{title}' already used")

    # WARN: Day-of-week or date label
    if re.search(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|'
                  r'周[一二三四五六日])', title):
        issues.append("G4.cd.title:day_label_instead_of_thematic_name -- "
                       "prefer thematic 1-4 character name over date label")

    return issues
```

**Planning Prompt Enhancement:** Add title quality requirements to the chapter planning prompt:

```markdown
## Chapter Title Requirements
- Title must be a 1-4 Chinese character thematic phrase
- Prohibited: day-of-week labels (Monday, 周一, etc.)
- Prohibited: chapter numbers (第N章)
- Prohibited: duplicate of any previous chapter title
```

### 3.2 G4.cd.hook_fulfillment: Plan-Content Cross-Validation

Introduce `G4.cd.hook_fulfillment` that validates the chapter plan's hook ledger against the actual chapter body:

```python
# g4/chapter_drafting.py -- new check

def check_hook_fulfillment(plan_path: Path, chapter_path: Path) -> list[str]:
    """G4.cd.hook_fulfillment: Verify plan-declared hooks appear in chapter body.

    Extracts hook IDs from plan Section 7 (Hook Ledger) and searches
    for their presence in the chapter prose.
    """
    plan_text = plan_path.read_text(encoding='utf-8')
    chapter_text = chapter_path.read_text(encoding='utf-8')

    # Extract hook IDs from plan Section 7
    plan_hooks = set(re.findall(r'MH-\d+', plan_text))
    # Extract hook IDs from chapter body
    chapter_hooks = set(re.findall(r'MH-\d+', chapter_text))

    missing = plan_hooks - chapter_hooks
    if missing:
        return [f"G4.cd.hook_unfulfilled: plan requires hooks {sorted(missing)} "
                f"but none found in chapter body"]
    return []
```

### 3.3 Arithmetic Consistency Verification

Augment the continuity audit prompt with explicit arithmetic verification instructions:

```markdown
## Arithmetic Consistency Verification (Continuity Audit)

For each chapter, verify:
1. **Currency accumulation**: Copper/silver coin totals must be arithmetically
   consistent with previous chapters. Recompute from known baselines.
2. **Date and count patterns**: Verify daily-increment patterns
   (e.g., "每日+1" sequences). Flag discrepancies > 0.
3. **Inventory tracking**: If a character acquires or expends items,
   verify the running totals.

Report any arithmetic discrepancy with:
- The incorrect value found in the chapter
- The correct computed value
- The line reference
```

This is injected into the existing continuity audit prompt template, not a separate LLM call.

### 3.4 Make Escalation-Review Conditional

The core fix: `escalation-review` is already dispatched reactively (on retry exhaustion at `chapter_loop.py:414-420` via `revision_router.dispatch_escalation`, and on closure failure at `cli.py:284`) -- NOT as a per-chapter `CHAPTER_STEPS` entry. The fix is to wire the EXISTING deterministic `check_escalation()` helper (`src/shenbi/skill_utils/escalation/check.py`, returns `list[EscalationSignal]`) into those reactive dispatch points so a templated LLM report is only produced when signals are non-empty; otherwise a deterministic summary is generated instead.

*Verified: `check_escalation()` currently exists but is never imported or called by `chapter_loop.py` or `_should_run_step`. There is no `shenbi-escalation-review` branch in `_should_run_step` to add because the skill is not a `CHAPTER_STEPS` entry.*

```python
# chapter_loop.py: reactive dispatch path (chapter_loop.py:414-420)
# Wire the EXISTING check_escalation() helper before dispatch_escalation

# check_escalation signature (skill_utils/escalation/check.py:53):
# check_escalation(resonance_scores, sensitivity_blocking, volume_objective_met,
#                  regeneration_attempts, arc_score=None, stratum_axis_drift=False)
from shenbi.skill_utils.escalation.check import check_escalation

# Gather arguments from pipeline state
resonance_scores = _get_recent_resonance_scores(project_dir, chapter)  # list[float]
signals = check_escalation(
    resonance_scores=resonance_scores,
    sensitivity_blocking=_has_sensitivity_blocking(cs),
    volume_objective_met=True,
    regeneration_attempts=cs.revision_count,
)
if not signals:
    # Generate deterministic summary instead of templated LLM report
    _generate_deterministic_review_summary(
        state.project_dir, state.chapter_loop.current_chapter
    )
    # Skip the escalation-review LLM dispatch
else:
    dispatch_escalation(project_dir, chapter, context=...)
```

**Deterministic Review Summary Generation:**

```python
def _generate_deterministic_review_summary(project_dir: Path, chapter: int) -> None:
    """Generate review summary by scanning audit files on disk. No LLM call.

    Only creates the summary file when escalation signals are absent.
    When escalation IS triggered, the LLM-based escalation-review handles it.
    """
    audit_dir = project_dir / 'audits'
    results = {}

    for audit_type in ALL_AUDIT_TYPES:
        audit_file = audit_dir / f'chapter-{chapter}-{audit_type}.md'
        if audit_file.exists():
            # Parse the audit verdict from the file
            verdict = _parse_audit_verdict(audit_file)
            results[audit_type] = verdict

    # Only generate if we have results
    if not results:
        return

    # Render summary from parsed results
    summary_path = audit_dir / f'chapter-{chapter}-review-summary.md'
    summary = _render_summary_template(chapter, results)
    safe_write(summary_path, summary)
```

### 3.5 Split Review Checklist: Static Template + Dynamic Deltas

Split the review checklist into two layers:

1. **Static Template (Genesis):** `context/review-checklist-template.json` -- generated once during Genesis, contains invariant fields (genre rules, formatting constraints, base ai_blacklist).
2. **Dynamic Deltas (per-chapter):** `context/review-checklist-chapter-N.json` -- generated each chapter by `context-composing`, contains evolving fields (hook_deliverables, chapter-specific ai_blacklist additions, transition_budget adjustments).

> **Filename convention:** aligned with Spec 10 (Data Storage Optimization) §3.2 and Spec 11 validation protocol.

```python
# review_checklist.py -- refactored generation

def build_review_checklist(project_dir: Path, chapter: int) -> dict:
    """Build the full review checklist by merging static template with
    per-chapter dynamic deltas.
    """
    # Load static template (Genesis, once)
    static = _load_static_template(project_dir)

    # Build dynamic deltas from current chapter state
    dynamic = {
        'hook_deliverables': _extract_hook_deliverables(
            project_dir, chapter
        ),
        'ai_blacklist_additions': _scan_recent_fatigue_patterns(
            project_dir, chapter
        ),
        'transition_budget': _compute_transition_budget(
            project_dir, chapter
        ),
    }

    # Merge: dynamic overrides/extend static
    merged = dict(static)
    merged['hook_deliverables'] = dynamic['hook_deliverables']
    merged['ai_blacklist'] = (
        static.get('ai_blacklist', []) +
        dynamic['ai_blacklist_additions']
    )
    merged['transition_budget'] = dynamic['transition_budget']

    return merged
```

### 3.6 Auto-Populate hook_deliverables (EXISTS -- diagnose empty output instead)

*Verified: `_extract_hook_deliverables` already EXISTS at `src/shenbi/pipeline/review_checklist.py:314-374`. It does NOT read from the chapter plan Section 7 as originally proposed -- it reads from `truth/pending_hooks.md` (YAML frontmatter `hooks` list) and filters to PLANTED/ACTIVE/PENDING states with urgency classification (normal/attention/URGENT based on silence vs max_distance). The original design below (plan Section 7 extraction) is preserved as an ALTERNATIVE approach; the real task is to diagnose why the existing `pending_hooks.md`-based extraction yields empty results in practice.*

Original proposed approach (chapter plan Section 7 extraction -- alternative to the existing `pending_hooks.md` reader):

```python
def _extract_hook_deliverables(project_dir: Path, chapter: int) -> list[dict]:
    """Extract hook deliverables from chapter plan Section 7 Hook Ledger.

    Parses the plan's hook ledger table to identify hooks that this
    chapter must advance, resolve, or reference.
    """
    plan_path = project_dir / 'plans' / f'chapter-{chapter}-plan.md'
    if not plan_path.exists():
        return []

    plan_text = plan_path.read_text(encoding='utf-8')

    deliverables = []
    # Parse the hook ledger table (typically a markdown table in Section 7)
    # Format: | Hook ID | Operation | Description |
    for match in re.finditer(
        r'\|\s*(MH-\d+)\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|',
        plan_text
    ):
        hook_id = match.group(1)
        operation = match.group(2)
        description = match.group(3).strip()
        deliverables.append({
            'hook_id': hook_id,
            'operation': operation,
            'description': description,
        })

    return deliverables
```

### 3.7 Ensure Context-Composing Checklist Regeneration Uses Current Sources

*Verified: `review_checklist.py` already implements mtime-based cache invalidation (`_get_max_source_mtime`, lines 195-224) comparing genre-config, chapter file, and `truth/` mtimes against the cache mtime. The checklist is NOT "frozen at Genesis" -- it regenerates when its source files change. The remaining risk is that `truth/` files are not being touched when they should be (e.g., `pending_hooks.md` not updated with hook state changes), causing the mtime check to register no change and yield a cache hit. The fix is to ensure the upstream truth files are updated each chapter so the existing invalidation fires:

```python
# chapter_loop.py: context-composing step configuration

# Invalidate any cached checklist before composing
_checklist_cache.clear()

# Force regeneration based on current truth file state
context_composing_step = StepDef(
    skill="shenbi-context-composing",
    force_regenerate=True,  # Never use cached output
    reads=[
        "truth/current_state.md",
        "truth/chapter_summaries.md",
        "truth/pending_hooks.md",
        "plans/chapter-N-plan.md",
    ],
)
```

---

## 4. Affected Files

### 4.1 G4 Quality Checks

*Verified: G4 is a package at `src/shenbi/gates/g4/` (not `g4.py`). `G4.cd.title` and `G4.cd.hook_fulfillment` do NOT currently exist -- confirmed genuine gaps to add. The existing `g4/chapter_drafting.py` module is the correct home for both new checks.*

| File | Change | Location |
|------|--------|----------|
| `src/shenbi/gates/g4/chapter_drafting.py` | Add `G4.cd.title` check function (verified: does not exist) | New check in chapter_drafting module |
| `src/shenbi/gates/g4/chapter_drafting.py` | Add `G4.cd.hook_fulfillment` check function (verified: does not exist) | New check in chapter_drafting module |
| `src/shenbi/pipeline/chapter_loop.py` | Call new G4 checks post-drafting | `_run_g4_checks()` after step 6 |
| `skills/shenbi-chapter-planning/SKILL.md` | Add title quality constraints to prompt template | System prompt section |
| `skills/shenbi-review-continuity/SKILL.md` | Add arithmetic verification instructions | Audit instructions section |

### 4.2 Escalation-Review Conditionalization

*Verified facts: (a) `escalation-review` is NOT a `CHAPTER_STEPS` entry -- it is dispatched reactively from `revision_router.dispatch_escalation` (`chapter_loop.py:414-420`) on retry exhaustion and from `cli.py:284` on closure failure. (b) A deterministic `check_escalation()` helper already EXISTS at `src/shenbi/skill_utils/escalation/check.py` (returns `list[EscalationSignal]`) but is never imported or called by `chapter_loop.py` or `_should_run_step` -- the gate logic exists in isolation, unwired. (c) The G4 checker `src/shenbi/gates/g4/escalation_review.py` (35 lines) EXISTS and validates the report has three sections (触发信号, 升级上下文, 决策选项); it only checks section presence and does NOT detect templated/identical summaries.*

| File | Change | Location |
|------|--------|----------|
| `src/shenbi/skill_utils/escalation/check.py` | **EXISTS (verified)** -- wire `check_escalation()` into dispatch decision; currently never imported by `chapter_loop.py` or `_should_run_step` | `check_escalation()` (line 53) |
| `src/shenbi/pipeline/chapter_loop.py` | Wire existing `check_escalation()` into the reactive dispatch path (import + call before `dispatch_escalation`) | Around `chapter_loop.py:414-420` |
| `src/shenbi/pipeline/chapter_loop.py` | Add `_generate_deterministic_review_summary()` | New function |
| `src/shenbi/pipeline/chapter_loop.py` | Add `_parse_audit_verdict()` helper | New function |
| `src/shenbi/gates/g4/escalation_review.py` | **EXISTS (verified)** -- optionally extend to detect templated summaries beyond the existing section-presence check | `g4_escalation_review()` (line 11) |

### 4.3 Review Checklist Split

*Verified against `src/shenbi/pipeline/review_checklist.py` (477 lines): mtime-based cache invalidation already EXISTS (`_get_max_source_mtime`, lines 195-224) and `_extract_hook_deliverables` already EXISTS (lines 314-374, reads `truth/pending_hooks.md`). The static-output symptom persists despite this logic -- the fix must target why the existing extraction yields empty/blacklist-frozen results in practice, not re-add logic that already exists.*

| File | Change | Location |
|------|--------|----------|
| `src/shenbi/pipeline/review_checklist.py` | Split into static + dynamic layers | `build_review_checklist()` |
| `src/shenbi/pipeline/review_checklist.py` | `_extract_hook_deliverables()` **EXISTS (verified, lines 314-374)** -- diagnose why it yields empty results instead of re-adding | `_extract_hook_deliverables()` |
| `src/shenbi/pipeline/review_checklist.py` | Add `_scan_recent_fatigue_patterns()` (verified: does not exist) | New function |
| `src/shenbi/pipeline/review_checklist.py` | `_get_max_source_mtime()` **EXISTS (verified, lines 195-224)** -- mtime invalidation already present | `_get_max_source_mtime()` |
| `src/shenbi/pipeline/chapter_loop.py` | Remove caching of context-composing output | `_run_context_curation()` |
| `skills/shenbi-context-composing/SKILL.md` | Update to generate dynamic deltas | Contract section |

---

## 5. Verification Criteria

### 5.1 Title Quality

1. Run 10 consecutive chapters -- zero date-label titles
2. Zero duplicate titles across all chapters
3. Zero titles containing chapter numbers
4. `G4.cd.title` check catches all three violation categories in regression tests

### 5.2 Plan-Content Alignment

1. Ch20 simulation regression: `G4.cd.hook_fulfillment` catches MH-003 absence
2. All plan-declared hooks with `advance` or `resolve` operations appear in chapter body (or are flagged)
3. Continuity audit catches Ch10 copper coin arithmetic error

### 5.3 Review Summary

*Note: `escalation-review` is dispatched reactively (retry exhaustion / closure failure), not 55 times unconditionally per chapter. Verification targets the dispatches that DO occur.*

1. Zero templated `review-summary.md` files generated when no escalation signals present (deterministic summary used instead)
2. When escalation IS triggered, `review-summary.md` contains chapter-specific information (not generic template)
3. Deterministic summary correctly reflects each audit type's presence/verdict
4. All reactive escalation-review dispatches that occur with empty signals are replaced by deterministic generation

### 5.4 Review Checklist

1. `ai_blacklist` shows variation across 3 consecutive chapters (reflecting different AI fatigue patterns)
2. `hook_deliverables` count >= number of active hooks declared in chapter plan
3. Checklist regenerates each chapter -- the mtime-based invalidation (`_get_max_source_mtime`, verified existing at lines 195-224) fires correctly when upstream `truth/` files are updated (diagnose why it currently yields cache hits)

### 5.5 Global

6. `just check` full pass
7. No regression in chapter generation quality

---

## 6. Dependencies

```
Spec 6 (Pipeline Architecture Optimization)
  └─ DELETE-1 (escalation-review conditional) ← this spec's §3.4 is the
     detailed implementation of that architectural decision. Note:
     escalation-review is already reactive (not a CHAPTER_STEPS entry);
     §3.4 wires the existing unwired check_escalation() helper.

Spec 8 (LLM Context Engineering)
  └─ Shared audit context cache ← complements review checklist extraction

No hard prerequisites. All fixes are independently implementable.
The title and hook fulfillment checks are additive (new G4 sub-checks).
The escalation-review and checklist fixes are standalone changes to
dispatch logic and generation code.

### Original Code Mapping

| Original Issue Code | Consolidated Spec |
|---|---|
| title-degradation | Spec 5 (this spec) |
| plan-content-mismatch | Spec 5 (this spec) |
| RS1 | Spec 5 (this spec) |
| static-review-checklist | Spec 5 (this spec) |
```

---

## Appendix A: Title Degradation Data

Full title evolution across 56 chapters:

| Chapter Range | Representative Titles | Pattern |
|---------------|----------------------|---------|
| Ch1-16 | 废料场, 痕迹, 沉, 见, 持, 晨, 醒, 夜, 雨, 雾, 石, 火, 风, 尘, 光, 影 | Poetic single/double character |
| Ch17-24 | 路, 渡, 桥, 门, 窗, 镜, 锁, 钥 | Object/metaphor names |
| Ch25-35 | 秋, 又一天, 冷, 三天, 归, 行, 等, 望, 听, 说, 记 | Transitional; first "又一天" appears |
| Ch36-56 | Saturday, 第四周Saturday, 第五周周五, 周三, 周末, 周一, 周二... | Date labels dominant |

## Appendix B: Review Summary Similarity Analysis

Agent 2 Audit 2a methodology:
- Compared all 55 `review-summary.md` files pairwise
- Computed normalized Levenshtein similarity
- Mean pairwise similarity: 99.4%
- Only variance: chapter number in file header
- Zero chapter-specific audit findings, scores, or recommendations

*Correction note: the original analysis assumed these 55 files came from 55 unconditional per-chapter `escalation-review` dispatches. Verified against code: `escalation-review` is NOT a `CHAPTER_STEPS` entry and is dispatched only reactively (`chapter_loop.py:414-420` on retry exhaustion; `cli.py:284` on closure failure). The presence of 55 near-identical summary files therefore indicates either (a) the summaries are generated by a different step, or (b) retry exhaustion occurred pervasively across chapters. The templated-output problem and the §3.4 fix (wire `check_escalation()` so empty signals produce deterministic summaries instead of LLM reports) remain valid regardless of how the files were produced.*
