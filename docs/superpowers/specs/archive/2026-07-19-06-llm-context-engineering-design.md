# Spec 8: LLM Context Engineering Design

> **Date:** 2026-07-19
> **Status:** Consolidated Design
> **Severity:** High (systemic efficiency defect -- 38% token waste across full pipeline run)
> **Source Merged:**
> - `2026-07-18-optimize-llm-context-design.md` (comprehensive ~781-line LLM context audit and optimization plan)
> **Purpose:** Provide a unified, actionable plan to eliminate systematic context waste in every LLM call across the Shenbi pipeline -- compressing redundancy, supplementing critical omissions, restructuring prompt organization per industry best practices, and fixing 3 code bugs + 4 architecture defects discovered in `dispatch_helper.py`.

---

## 1. Executive Summary

### 1.1 The Scale of the Problem

Each chapter loop produces ~24 LLM calls. Each call pushes ~17K tokens of context (average). Per-chapter total: ~408K tokens. Across 56 chapters: **~22.9 million tokens**.

An estimated **38% (~153K tokens/chapter, ~8.7M tokens total)** is waste -- duplicate content (13 auditors each independently load the same 30KB chapter), irrelevant content (volume_map's 99% unrelated chapters), or stale data (truth files with only the last chapter's data).

### 1.2 Audit Methodology

A dedicated agent performed a line-by-line audit of `dispatch_helper.py` and a per-skill audit of all 32 SKILL.md files, evaluating each LLM call against four dimensions:

| Dimension | Assessment Standard |
|---|---|
| **Compression opportunity** | How much context can be removed without degrading output quality |
| **Supplementation need** | What critical context is missing that causes known output defects |
| **Structural optimization** | Whether context organization follows "instruction first, graded prompts, negative constraints" best practices |
| **Batching opportunity** | Whether multiple LLM calls can be merged into one |

### 1.3 Findings Summary

| Category | Count | Impact |
|---|---|---|
| Code bugs in `dispatch_helper.py` | 3 | Silent data loss, format corruption, truncation edge cases |
| Architecture defects | 4 | 88% audit context waste, 33K-token single calls, missing field filters |
| Per-skill context waste | 12 fixes needed | volume_map bloat, META blocks, state-settling context starvation |
| SKILL.md prompt bloat | 7 redundancy categories | ~500+ lines of duplicated content across 32 files |
| **Total fixes** | **26** | Projected 40% token reduction per chapter |

### 1.4 Projected Impact

| Metric | Current | After Optimization |
|---|---|---|
| LLM calls per chapter | 24 | 14-24 (cascade-dependent) |
| Total tokens per chapter | 408K | ~253K |
| Effective information ratio | 62% | ~90% |
| 56-chapter total tokens | 22.9M | ~14.2M |
| **Net savings** | -- | **~155K tokens/chapter (-38%)** |

---

## 2. Per-Skill Context Audit Summary

### 2.1 shenbi-chapter-planning (~22.5K tokens)

**Current:** 7 input files (83KB raw) + 5KB system prompt + 1.5KB user template.

| File | Size | Effective | Problem |
|---|---|---|---|
| `volume_map.md` | 26KB | **2%** | 460 lines; only 2 lines relevant to current chapter |
| `current_focus.md` | 20KB | 100% | Correct |
| `current_state.md` | 10KB | **1%** | Coverage bug: only Ch56 data present |
| `pending_hooks.md` | 10KB | 80% | Unstructured |
| `chapter_summaries.md` | 6KB | **2%** | Coverage bug: only 1 chapter present |
| `story_frame.md` | 5KB | 100% | Correct |
| `author_intent.md` | 5KB | 100% | Correct |

**Waste ratio: 53%.** Fix: volume_map chapter-node extraction; skip stale files if CN3 not yet fixed; standardize pending_hooks format.

**Missing:** Previous 3 chapters' actual ending paragraphs (makes Section 2 "what is the reader waiting for" more precise); previous chapter's resonance score (to adjust ambition level).

### 2.2 shenbi-chapter-drafting (~10K tokens)

**Current:** chapter plan + context + style_profile + genre-config + audit_drift.

**Waste ratio: 25%.** Fix: skip bootstrap style_profile if CN4 not yet fixed; verify field-level reads of plan sections 1/3/6/8 are actually executed.

**Critical missing:** volume_map current chapter node (drafting does not read volume_map at all -- chapters can drift from volume outline); previous chapter ending paragraphs (for continuity in opening).

### 2.3 shenbi-state-settling (~9K tokens) -- Most Severe Context Starvation

**Current:** Only `chapters/chapter-N.md` (30KB). **One file. Zero structural context.**

**Waste ratio: N/A (under-fed, not over-fed).** This is a **supplementation** problem, not compression.

**Critical missing:**

| Missing Context | Purpose | Estimated Size |
|---|---|---|
| Previous truth file versions | Know what changed -- append, not overwrite | ~5KB |
| volume_map current chapter node | Know this chapter's position in the arc | ~500B |
| character_matrix.md | Update character state without parameter replacement | ~4KB |
| Previous chapter_summary | Maintain cross-chapter continuity | ~1KB |
| Previous pending_hooks | Append new hooks without overwriting old | ~5KB |

**This is the direct root cause of CN3 (overwrite mode) and CN1 (character disappearance) -- the LLM lacks sufficient context to make correct "append vs. overwrite" decisions.**

### 2.4 Audit Group (13 skills x ~20K tokens = 260K tokens/chapter) -- Largest Waste Source

**Current:** Each auditor independently receives `chapter-N.md` (30KB) + `chapter-N-plan.md` (13KB) + shared truth files (~30KB).

**Problem:** 13 auditors each independently load the same 30KB chapter file = 390KB redundant transmission.

```
Traditional:                          Shared Cache:
Audit 1  <-- chapter(30KB)           Audit 1  --+
Audit 2  <-- chapter(30KB)           Audit 2  --+
...                                   ...        +-- Shared: chapter(30KB) + plan(13KB) + truth(30KB)
Audit 13 <-- chapter(30KB)           Audit 13 --+   = 73KB total (not 13 x 73KB)

Each: 73KB context                   Each: 3KB audit-specific + 73KB shared
Total: 13 x 73KB = 949KB             Total: 73KB + 13 x 3KB = 112KB
Savings: 837KB/chapter (88%)
```

### 2.5 shenbi-review-resonance (~14K tokens)

**Missing:** Previous 5 chapters' resonance trend (post-CN3 fix) to assess improvement/degradation; volume_map tension curve position to adjust scoring standards by arc position.

**Structure:** Resonance audit format requirements too strict -- G4 retried 35 times. Fix: add complete examples in prompt, not just field name lists (see Spec 2: Output Validation).

### 2.6 shenbi-chapter-revision (~14K tokens)

**Missing:** Audit report summary (which audits found issues, which passed) to focus revision scope; previous revision history (for second revisions) to avoid repeating ineffective changes.

### 2.7 shenbi-context-composing (~18K tokens)

**Waste:** volume_map (same as planning -- extract chapter node); review checklist static fields (see Spec 10: Data Storage Optimization).

**Missing:** Previous chapter context file for continuity; current chapter resonance score to adjust tension level.

### 2.8 shenbi-foreshadowing-plant/track/recall (~8-12K tokens each)

**Missing:** volume_map cross-volume bridges (which hooks activate N chapters later) for hook lifecycle planning; previous pending_hooks (post-CN3) to know what is PLANTED/TRIGGERED.

### 2.9 shenbi-escalation-review (~8K tokens)

**Waste ratio: nearly 100%.** 55 out of 56 calls produced identical template output. Fix: **completely skip** this call when no escalation signal exists (see Spec 5: Content Quality Gates). Pure waste elimination.

---

## 3. Three Code Bugs (from dispatch_helper.py Audit)

### Bug 1: Glob Patterns Never Expanded (Silent Data Loss)

**File:** `src/shenbi/pipeline/dispatch_helper.py:142-161`

**Root cause:** Multiple SKILL.md contracts declare glob reads:
```yaml
reads:
  - chapters/*.md           # review-long-span, review-arc-payoff
  - characters/major/*.md   # review-character, review-dialogue, review-motivation
```

But `_build_skill_prompt` L146: `full_path = project_dir / resolved` passes literal `*` to `Path.exists()` -- returns False. Result: `[file not found: chapters/*.md]` placeholder text.

**Impact:**
- `review-long-span` cannot perform cross-chapter n-gram analysis (its core function)
- Character review skills cannot see supporting character profiles in `major/` directory
- **Silent failure -- no log, no alert, LLM receives placeholder text without knowing it is an error**

**Fix:** `_resolve_read_path` with `glob.glob()` expansion, sorted by mtime (newest first), capped at 50 files. Industry practice: LangChain `DirectoryLoader` -- glob patterns should be expanded at context build time with priority-ordered budget constraints.

```python
def _resolve_read_path(project_dir: Path, read_path: str, chapter: int | None) -> list[tuple[str, str]]:
    resolved = resolve_or_skip(read_path, chapter)
    if resolved is None:
        return []
    if '*' in resolved or '?' in resolved:
        pattern = str(project_dir / resolved)
        matches = sorted(globmod.glob(pattern, recursive=True))
        if not matches:
            log.warning("glob_no_matches", pattern=pattern)
            return [(resolved, f"[glob matched 0 files: {resolved}]")]
        matches_with_mtime = [(m, Path(m).stat().st_mtime) for m in matches]
        matches_with_mtime.sort(key=lambda x: -x[1])
        results = []
        for m_path, _ in matches_with_mtime[:50]:
            rel = str(Path(m_path).relative_to(project_dir))
            results.append((rel, m_path))
        return results
    full_path = project_dir / resolved
    return [(resolved, str(full_path))] if full_path.exists() else [(resolved, f"[file not found: {resolved}]")]
```

### Bug 2: Code Fence Nesting Conflicts

**File:** `src/shenbi/pipeline/dispatch_helper.py:241-243`

**Root cause:** Input file content is wrapped in ``` ``` ``` markers. If the file itself contains ``` ``` ``` (e.g., META blocks with code examples), the inner fence prematurely closes the outer wrapper -- LLM parsing becomes ambiguous.

**Industry practice:** Anthropic Context Engineering recommends XML `<document>` tags for separating multiple documents -- they do not conflict with Markdown and are in Anthropic's fine-tuning data.

**Fix:** Replace code fence wrapping with XML document tags:

```python
for fname, content in input_texts.items():
    # Escape the actual closing tag wrapper ('</document>', not '</doc>')
    # to prevent content from prematurely closing the outer wrapper.
    # Better: escape all '<' in content to '\u003c' to prevent any tag injection.
    safe_content = content.replace('<', '\u003c')
    user_parts.append(f'<document name="{fname}">\n{safe_content}\n</document>')
```

### Bug 3: UTF-8 Truncation at Byte Boundary (Edge Case)

**File:** `src/shenbi/pipeline/dispatch_helper.py:169`

**Analysis:** Python `text[:limit]` operates at character (code point) boundaries, not byte boundaries. Chinese characters are 1 code point = 1 in `len()`. Truncation is actually at character boundaries -- **no UTF-8 corruption in practice.** However, the current code gives **no truncation indicator** -- the LLM receives truncated text without knowing it is incomplete.

**Industry practice:** Anthropic principle: when content is truncated, explicitly inform the model to prevent incorrect inferences from incomplete information.

**Fix:** `_safe_truncate` with truncation indicator and paragraph/sentence boundary awareness:

```python
def _safe_truncate(text: str, limit: int, label: str = "") -> str:
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    # Backtrack to last complete paragraph
    last_para = truncated.rfind('\n\n')
    if last_para > limit * 0.7:
        truncated = truncated[:last_para]
    elif limit > 500:
        for sent_end in ['。\n', '.\n', '！\n', '?\n', '？\n']:
            last_sent = truncated.rfind(sent_end)
            if last_sent > limit * 0.5:
                truncated = truncated[:last_sent + 1]
                break
    removed = len(text) - len(truncated)
    truncated += f"\n\n[Truncation indicator: {removed} characters ({removed//4} tokens) omitted. Original file: {label}]"
    return truncated
```

---

## 4. Four Architecture Defects

### Defect 1: No Shared Audit Context Cache

**File:** `src/shenbi/pipeline/dispatch_helper.py` (new function needed)

**Problem:** 13 audit skills each independently load the same 30KB chapter, 13KB plan, and ~30KB truth files. Each auditor receives a full 73KB context when only ~3KB is audit-specific instructions. The curated context (`context_assemble.py` + `context_curation.py`) generates high-quality 9-section curated context (~12K chars) per chapter, but **not a single audit skill reads it**.

**Industry practice:** LangChain `BaseCache` -- when multiple calls share the same underlying data, use a cache layer.

**Fix:** `_build_shared_audit_context()` -- load chapter, plan, and curated context once. Distribute specific sections of curated context to each auditor by type (P7 world rules to world-rules auditor, P5+P6 character context to character auditor, etc.). Result: 1 load of 73KB + 13 x 3KB audit-specific = 112KB total (vs. 949KB without cache). **88% reduction.**

### Defect 2: World Files 33K Tokens Sent in Full

**File:** `src/shenbi/pipeline/dispatch_helper.py`, new `world_summarizer.py`

**Problem:** `review-world-rules` single call receives 7 files totaling ~115K characters (33K tokens). `world/power_system.md` (28.8K chars) and `world/locations.md` (24.9K chars) are sent in full without any summarization.

**Industry practice:** LlamaIndex `SummaryIndex` -- deterministically summarize large documents before context injection.

**Fix:** `summarize_world_files()` -- extract rule names + key constraints from `power_system.md`; extract location names + key features from `locations.md`. Keep to max 2000 chars each. Reduces `review-world-rules` from 33K to ~10K tokens (-70%) while retaining all rule names for verification.

### Defect 3: Only 40% of Reads Declare Field Filters

**Problem:** The largest files most in need of field filtering lack it entirely:
- `chapters/chapter-N.md` (31K+) -- never field-filtered
- `world/power_system.md` (28.8K) -- never field-filtered
- `outline/volume_map.md` (26.3K) -- never field-filtered

**Industry practice:** OpenAI needle-in-haystack problem -- in long documents sent to LLMs, only a small portion is relevant. Field filtering (Layer B) is the implemented solution but coverage is incomplete.

**Fix:** Systematically declare field filters for all files >5KB in every SKILL.md contract. The `filter_to_fields` function (`fields.py:44-52`) already supports H2 section extraction -- only the YAML contract declarations are missing.

### Defect 4: Equal-Weight Truncation

**Problem:** When total input exceeds 128K, every file gets equal budget -- a 500-byte `audit_drift` and a 30K-byte `chapter` receive the same slice.

**Industry practice:** Anthropic "Context Window Budgeting" -- allocate tokens to the most important content, not equally.

**Fix:** `_FILE_PRIORITY_WEIGHTS` + `_budgeted_truncate`:

```python
_FILE_PRIORITY_WEIGHTS = {
    'plan': 1.0,           # Chapter plan -- highest priority
    'chapter': 0.9,        # Chapter body
    'volume_map': 0.8,     # Volume outline
    'story_frame': 0.7,    # Story framework
    'current_state': 0.6,  # Current state
    'pending_hooks': 0.6,  # Foreshadowing hooks
    'character': 0.5,      # Character data
    'style': 0.4,          # Style profile
    'audit_drift': 0.4,    # Drift audit
    'world': 0.3,          # World setting (reference)
    'default': 0.5,
}
```

Budget is allocated proportionally by weight. Minimum 500 chars per file; maximum per-file cap respected.

---

## 5. Twelve Fixes with Industry Best Practice Annotations

### Fix 1: _resolve_read_path with Glob Expansion

**Source:** Bug 1. **Industry practice:** Anthropic structured tool use -- resolve all references deterministically before LLM invocation.

**Implementation:** Replace `dispatch_helper.py:142-161` simple path concatenation with `_resolve_read_path()` that calls `glob.glob()` when `*` or `?` is detected. Results sorted by mtime; capped at 50 files. Logs warning on zero matches.

**Additional benefit:** Restores `review-long-span` cross-chapter n-gram analysis; enables `review-character` to read `characters/major/*.md`.

### Fix 2: Replace Code Fences with XML `<document>` Tags

**Source:** Bug 2. **Industry practice:** Anthropic Context Engineering -- `<document>` tags for multi-document separation. These are parsed correctly by models fine-tuned on Anthropic data, never conflict with Markdown, and support metadata attributes (token count, truncation status).

**Implementation:** Replace `dispatch_helper.py:241-243` ``` ``` ``` wrapping with `<document name="...">...</document>`. Escape the actual wrapper closing tag `</document>` appearing in content — note the wrapper is `</document>`, NOT `</doc>`. The safest approach is to escape all `<` in content to `\u003c` to prevent any tag injection.

### Fix 3: _safe_truncate with Truncation Indicator

**Source:** Bug 3. **Industry practice:** Google character-aware processing -- ensure truncation is semantically safe and explicitly communicated.

**Implementation:** `_safe_truncate()` truncates at paragraph/sentence boundaries near the limit, appends truncation indicator with counts. This prevents the model from making inferences based on incomplete data and gives it metadata to weight the truncated content appropriately.

### Fix 4: _build_shared_audit_context Cache

**Source:** Defect 1. **Industry practice:** LangChain `BaseCache` pattern -- cache shared underlying data across multiple LLM calls.

**Implementation:** New function in `dispatch_helper.py`. Loads chapter text, plan, and curated context once. Distributes curated context sections by audit type. Cached per chapter. Each auditor receives: shared context + 3KB audit-specific checklist. **88% audit context reduction.**

### Fix 5: Deterministic World File Summarizer

**Source:** Defect 2. **Industry practice:** LlamaIndex `SummaryIndex` -- deterministic pre-summarization of large reference documents.

**Implementation:** New file `src/shenbi/pipeline/world_summarizer.py`. Regex-extracts rule names + key numbers from `power_system.md`, location names + key features from `locations.md`. No LLM call needed -- purely deterministic. **70% reduction for review-world-rules.**

### Fix 6: Systematic Field Declarations for All Files >5KB

**Source:** Defect 3. **Industry practice:** Anthropic primacy effect -- front-load important information by filtering irrelevant sections before context assembly.

**Implementation:** Update all SKILL.md contracts for skills reading files >5KB. Declare `fields:` for `chapter-N.md` (section-specific), `power_system.md` (core rules only), `volume_map.md` (current volume objective + current chapter node + cross-volume bridges). The `filter_to_fields` extraction logic already exists.

### Fix 7: _FILE_PRIORITY_WEIGHTS + _budgeted_truncate

**Source:** Defect 4. **Industry practice:** OpenAI priority-driven context allocation -- not all tokens are equal; instruction tokens matter more than reference tokens.

**Implementation:** Replace `dispatch_helper.py:163-192` equal-weight truncation with priority-weighted budget allocation. Plans and chapters get higher budgets; world reference files get lower. Minimum 500 chars per file guaranteed.

### Fix 8: Audit Cascading -- Core 4 Pass, Skip 8

**Source:** Per-skill audit (Section 2.4). **Industry practice:** Google "Early Exit" pattern -- low-cost classifiers run first; high-cost models invoked only when uncertain.

**Implementation:** In `chapter_loop.py:_run_audits`:
```python
CORE_AUDITS = ['continuity', 'character', 'world-rules', 'pacing']
# memo-compliance ALWAYS runs (scoring requires it) — do NOT cascade-skip it.
# resonance ALWAYS runs (scoring requires it) — do NOT cascade-skip it.
ALWAYS_RUN = {'memo-compliance', 'resonance'}
CASCADABLE_AUDITS = ['dialogue', 'motivation', 'sensitivity', 'foreshadowing',
                     'pov', 'anti-ai', 'texture', 'reader-pull']
```
**Cascade trigger (N-chapter-streak heuristic):** Skip cascaded audits when the previous N=3 chapters' corresponding cascaded audits ALL passed with zero HARD failures. This is a simple, verifiable heuristic that does not require a confidence score — there is no "confidence >90%" signal available from the audit results. `memo-compliance` and `resonance` always run regardless of the cascade (scoring requires them), so they are excluded from `CASCADABLE_AUDITS`. **Up to 80K tokens saved per chapter** (8 cascaded audits x ~10K tokens each, vs. 9 when memo-compliance was wrongly included).

### Fix 9: Remove Stale Data from Context

**Source:** Context freshness check. **Industry practice:** Anthropic clean context principle -- stale data leads to incorrect model inferences; validate freshness before injection.

**Implementation:** `_validate_context_freshness()` in `dispatch_helper.py`. Checks cumulative truth files (`chapter_summaries`, `resonance_trend`) for coverage breadth; flags files with only 1-2 chapters when at chapter 10+. Checks `style_profile` for bootstrap mode beyond chapter 3. Logs WARNING with root cause attribution.

### Fix 10: Three-Tier Instruction Hierarchy

**Source:** Prompt structure optimization. **Industry practice:** Anthropic instruction hierarchy -- HARD CONSTRAINTS (violation = retry) at top, GUIDELINES (preferred but flexible) in middle, REFERENCE (for context only) at bottom.

**Implementation:** `_build_user_prompt_with_hierarchy()` replaces flat input list with:
1. L1: HARD CONSTRAINTS -- volume alignment, 8-section completeness, output format
2. L2: GUIDELINES -- hook selection, transition budget, chapter objective derivation
3. L3: TASK -- the actual prompt
4. L4: REFERENCE -- input files wrapped in `<document>` tags

### Fix 11: Volume Map Chapter-Specific Extraction

**Source:** Per-skill audit -- planning (53% waste), drafting (missing entirely), state-settling (missing entirely). **Industry practice:** Deterministic pre-extraction reduces LLM context and improves focus.

**Implementation:** Extract only the current chapter's node from `volume_map.md` before context assembly. A 26KB, 460-line file becomes a ~500B node. Applied to: planning, drafting (new), state-settling (new), context-composing, foreshadowing skills.

### Fix 12: Truth File Dedup + Review Checklist Static Extraction + Escalation-Review Skip + State-Settling Supplement

**Combined fix addressing multiple small wins:**
- Truth file dedup: Remove duplicate truth file reads in audit shared context (covered by Fix 4)
- Review checklist static extraction: Move static checklist fields from review skill system prompts to shared templates (see Spec 10: Data Storage Optimization)
- Escalation-review skip: When no escalation signal, skip entirely (see Spec 5: Content Quality Gates) -- saves 8K tokens/chapter
- State-settling supplement: Add previous truth versions + volume_map node + character_matrix + chapter_summary + pending_hooks to state-settling context (addresses CN1 + CN3 root cause)

---

## 5b. SKILL.md Prompt Bloat Reduction

An agent audited all 32 SKILL.md files and found 7 categories of redundant content:

| # | Redundancy Pattern | Scope | Waste | Fix |
|---|---|---|---|---|
| 1 | **Auto-generated data contract blocks** (`## Data Contract`) | 32 skills | ~160-320 lines | Remove or collapse -- duplicates frontmatter |
| 2 | **Four-element defect evidence format** (position+quote+rule+severity) | 20 review skills | ~120 lines verbatim repeats | Extract to `skills/_shared/defect-evidence-format.md` |
| 3 | **U-gap/negative gate explanations** | resonance + arc-payoff | ~30 lines duplicate | Extract to shared architecture doc |
| 4 | **Pipeline integration mode descriptions** | drafting + context-composing | ~16 lines | Extract to shared reference |
| 5 | **State-settling human approval gate template** | 1 skill | 65 lines -> 15 lines | Compress to structural description |
| 6 | **Foreshadowing-resolve CP formula duplication** | 1 skill | Appears 2x | De-duplicate |
| 7 | **AUTO-CHECK empty blocks** | 32 skills | ~100 lines | Remove empty comment blocks |

**Additional finding:** The two largest system prompts are `shenbi-review-resonance` (~12,600 chars) and `shenbi-review-arc-payoff` (~12,100 chars). Both spend 15-20 lines explaining the same architectural concept. Extracting shared docs saves ~40 lines.

**System prompt size distribution:**
| Size Range | Skill Count | Representatives |
|---|---|---|
| <3,000 chars | 4 | escalation-review (1,000), foreshadowing-recall (1,800) |
| 3,000-6,000 | 20 | Most audit skills |
| 6,000-10,000 | 5 | chapter-planning, state-settling, chapter-revision |
| >10,000 | 2 | resonance (12,600), arc-payoff (12,100) |

---

## 6. Expected Impact

### 6.1 Token Reduction Per Chapter

| Optimization | Savings/Chapter | Type |
|---|---|---|
| Audit shared context cache | -84K tokens | Compression |
| Audit cascading (N=3 chapter zero-HARD-failure streak skip; 8 cascaded audits — `memo-compliance` and `resonance` always run) | -80K tokens | Compression |
| Volume map chapter-node extraction | -6K tokens | Compression |
| Escalation-review conditional skip | -8K tokens | Compression |
| World file deterministic summarization | -23K tokens | Compression |
| Field filter declarations for large files | -15K tokens | Compression |
| SKILL.md prompt bloat reduction | -10K tokens (amortized) | Compression |
| Truth file repair (waste -> useful) | +16K -> useful | Fix |
| State-settling context supplementation | +7K tokens | Supplement |
| **Net effect** | **-155K tokens/chapter (-38%)** | |

### 6.2 56-Chapter Total

| Metric | Before | After |
|---|---|---|
| Total tokens | 22.9M | ~14.2M |
| Token cost (est. $0.50/1M tokens) | ~$11.45 | ~$7.10 |
| Effective information ratio | 62% | ~90% |

### 6.3 Implementation Complexity

| Fix | Complexity | Dependencies |
|---|---|---|
| Fix 1 (glob expansion) | Low | None |
| Fix 2 (XML tags) | Low | None |
| Fix 3 (safe truncate) | Low | None |
| Fix 4 (audit cache) | Medium | Requires curated context generation |
| Fix 5 (world summarizer) | Low | None |
| Fix 6 (field declarations) | Low | None |
| Fix 7 (priority truncation) | Medium | Fix 3 |
| Fix 8 (audit cascading) | Medium | Fix 4 |
| Fix 9 (freshness check) | Low | None |
| Fix 10 (instruction hierarchy) | Medium | Fix 2 |
| Fix 11 (volume map extraction) | Medium | Spec Volume Map Consumption |
| Fix 12 (combined small wins) | Low-Medium | Spec 1, Spec 5, Spec 10 |
| SKILL.md bloat reduction | Low | None (content-only changes) |

---

## 7. Affected Files

| File | Fix(es) | Change |
|---|---|---|
| `src/shenbi/pipeline/dispatch_helper.py:142-161` | Fix 1 | Glob expansion in `_resolve_read_path` |
| `src/shenbi/pipeline/dispatch_helper.py:241-243` | Fix 2 | Code fence -> XML `<document>` tags |
| `src/shenbi/pipeline/dispatch_helper.py:169` | Fix 3 | `_safe_truncate` with indicator + boundary awareness |
| `src/shenbi/pipeline/dispatch_helper.py` (new function) | Fix 4 | `_build_shared_audit_context` cache |
| `src/shenbi/pipeline/world_summarizer.py` (new) | Fix 5 | Deterministic world file summarizer |
| `skills/shenbi-chapter-planning/SKILL.md` | Fix 6, Fix 11 | Field declarations + volume map extraction |
| `skills/shenbi-review-world-rules/SKILL.md` | Fix 5, Fix 6 | Field declarations for world files |
| `skills/shenbi-chapter-drafting/SKILL.md` | Fix 6, Fix 11 | Field declarations + volume map node |
| `skills/shenbi-state-settling/SKILL.md` | Fix 12 | Context supplementation declarations |
| `src/shenbi/pipeline/dispatch_helper.py:163-192` | Fix 7 | Priority-weighted budget allocation |
| `src/shenbi/pipeline/chapter_loop.py:_run_audits` | Fix 8 | Audit cascading logic |
| `src/shenbi/pipeline/dispatch_helper.py` (new function) | Fix 9 | `_validate_context_freshness` |
| `src/shenbi/pipeline/dispatch_helper.py:_build_user_prompt` | Fix 10 | Three-tier instruction hierarchy |
| `src/shenbi/pipeline/dispatch_helper.py` | Fix 11 | Volume map chapter-node extraction |
| `src/shenbi/pipeline/dispatch_helper.py` | Fix 12 | Escalation-review skip + state-settling supplement |
| `skills/_shared/defect-evidence-format.md` (new) | SKILL.md | Shared defect evidence format |
| `skills/_shared/u-shaped-gap-explanation.md` (new) | SKILL.md | Shared U-gap explanation |
| `skills/_shared/pipeline-integration-mode.md` (new) | SKILL.md | Shared pipeline integration pattern |
| `skills/_shared/anti-rationalization-base.md` (new) | SKILL.md | Shared anti-rationalization table base |
| All 32 `skills/*/SKILL.md` | SKILL.md | Remove data contract blocks, AUTO-CHECK empty blocks, dedup |

---

## 8. Verification Criteria

1. Glob patterns in SKILL.md `reads:` contracts produce actual file content (not `[file not found]`)
2. `review-long-span` receives multi-chapter content for n-gram analysis
3. Character review skills can read `characters/major/*.md`
4. No ``` ``` ``` code fence used for content wrapping in dispatch_helper; all content uses `<document>` tags
5. Truncated content includes truncation indicator with character/token counts
6. Truncation indicator is at paragraph or sentence boundary, not mid-word
7. 13 audit skills share a single chapter+plan+truth load (verify via log or cache hit counter)
8. Audit context cache hit rate = 12/13 (first auditor populates, 12 subsequent hit cache)
9. `review-world-rules` context < 10K tokens (down from 33K)
10. Deterministic world summarizer output preserves all rule names from `power_system.md`
11. All files >5KB in any skill's contract have field filter declarations
12. `filter_to_fields` is called for each field-declared file
13. Budgeted truncation assigns more characters to `plan` files than `world` files
14. When the previous N=3 chapters' cascaded audits all passed with zero HARD failures, cascaded audits for the current chapter are skipped
15. When any of the previous N=3 chapters had a HARD failure in a cascaded audit, all audits run as before
16. Resonance and memo-compliance audits always run regardless of cascade
17. Stale cumulative truth files (only 1-2 chapters at chapter 10+) produce WARNING log
18. Bootstrap `style_profile` beyond chapter 3 produces WARNING log
19. User prompts follow L1 HARD CONSTRAINTS -> L2 GUIDELINES -> L3 TASK -> L4 REFERENCE structure
20. Volume map context for planning/drafting/state-settling is chapter-node only, not full 26KB file
21. No escalation signal -> `escalation-review` LLM call is completely skipped
22. State-settling context includes previous truth file versions
23. `skills/_shared/` directory exists with 4 shared reference files
24. No audit SKILL.md contains verbatim four-element defect evidence format (references shared file instead)
25. No SKILL.md contains empty AUTO-CHECK blocks
26. `shenbi-review-resonance` SKILL.md and `shenbi-review-arc-payoff` SKILL.md < 8,000 chars each
27. Total token consumption per chapter reduced by >=30% vs. pre-optimization baseline
28. `just check` full suite passes at every stage
29. No regression: chapter output quality maintained or improved (golden set scores)

---

## 9. Dependencies

```
Spec 1 (Truth File and State Accumulation)
    |-- Required for: state-settling context supplementation (Fix 12)
    |-- Required for: context freshness validation (Fix 9)
    |-- Without this fix: truth files remain single-chapter, state-settling stays starved

Spec 5 (Content Quality Gates and Review Optimization)
    |-- Required for: Fix 12 escalation-review conditional skip
    |-- 55/56 calls currently produce identical templates -- pure waste

Spec 9 (Content Planning and Deliverable Design)
    |-- Required for: Fix 11 (volume map chapter-node extraction)
    |-- Required for: planning, drafting, state-settling volume map supplementation

Spec 10 (Data Storage Optimization)
    |-- Required for: context-composing review checklist reduction (Section 2.7)
    |-- Required for: Fix 12 (review checklist static extraction component)

Internal Dependencies:
    Fix 1 (glob) ---------- independent
    Fix 2 (XML tags) ------ independent
    Fix 3 (safe truncate) - independent
    Fix 4 (audit cache) --- independent
    Fix 5 (world summarizer) independent
    Fix 6 (field declarations) independent (content-only YAML changes)
    Fix 7 (priority trunc) - depends on Fix 3
    Fix 8 (cascade) -------- depends on Fix 4
    Fix 9 (freshness) ------ independent
    Fix 10 (hierarchy) ----- depends on Fix 2
    Fix 11 (volume extract) depends on Spec 9 (Content Planning)
    Fix 12 (combined) ------ depends on Spec 1, Spec 5, Spec 10
    SKILL.md bloat -------- independent (content-only changes across 32 files)

### Original Code Mapping

| Original Issue Code | Consolidated Spec |
|---|---|
| llm-context-opt | Spec 8 (this spec) |
```
