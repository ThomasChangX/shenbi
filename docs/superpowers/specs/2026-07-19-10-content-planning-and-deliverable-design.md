# Spec 9: Content Planning and Deliverable Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Critical (composite)
> **Merged from:** `2026-07-17-fix-volume-map-not-consumed-design.md`, `2026-07-17-fix-character-archive-completeness-design.md`, `2026-07-17-improve-meta-block-design.md` (C3)
> **Purpose:** Fix the three most severe content planning and delivery defects in the pipeline: the 460-line volume_map.md blueprint is never consumed for per-chapter content/context injection (it IS consumed for structure validation and chapter-count derivation), character archives for major/minor supporting characters are never created, and META blocks embedded in deliverable chapter files constitute ~31% of content that downstream consumers must strip.

---

## 1. Executive Summary

The Shenbi pipeline was designed as a blueprint-driven novel generation system. The Genesis phase produces elaborate planning artifacts including a 100-chapter volume map, character archives, and meta-quality controls. However, three architectural defects prevent these artifacts from fulfilling their purpose:

1. **volume_map.md is never consumed for per-chapter content or context injection.** The 460-line document defines 5 volumes, 100 chapters, 16 cross-volume bridges, and tension curves. It IS read for structure validation and chapter-count derivation (by gates `g2.py:289-290`, `g5.py:233,236`, `g6.py:300-301`, `g4/story_architecture.py:51`, `g4/volume_outlining.py:35`; by `triggers.py:75,283,361-374` for `total_chapters` recompute; by `genesis.py:65` and `cli.py:148,638`), but it is NOT read for per-chapter content/context injection: zero code in `chapter_loop.py`, `context_assemble.py`, or `dispatch_helper.py` injects its content into the LLM prompt at planning or drafting time. Result: 100/100 chapters deviate from the blueprint, 16/16 key plot points are missing, and 4/4 cross-volume bridges are never activated.

2. **Character archives for supporting characters are never created.** The `shenbi-character-design` SKILL.md contract declares writes to `characters/major/*.md` and `characters/minor/*.md`, but after 56 chapters of generation these directories do not exist. Six named supporting characters (Chen Weimin, Zhao Tiezhu, Chu Yunlan, Koen Whiteman, Gangshan Tieya, Middle-aged Woman) lack independent archives, making it impossible for downstream skills to query character state.

3. **META blocks contaminate deliverable chapter files.** The `shenbi-chapter-drafting` SKILL.md (lines 95-130) requires PRE_WRITE_CHECK and POST_WRITE_SELF_CHECK blocks embedded in `chapters/chapter-N.md`. While `shared.py:120-121` strips them for word counting, any consumer reading chapter files directly encounters internal quality-control artifacts. Average META block ratio is 31.3% of file size; worst case (Ch24) is 49.9%.

These three defects share a common root cause: **the pipeline's planning-to-execution bridge is incomplete.** Genesis produces plans, but the chapter loop has no mechanism to consume them.

---

## 2. Root Cause Analysis

### 2.1 volume_map.md: Consumed for Validation, Not for Content Injection

**Evidence chain:**

The `shenbi-volume-outlining` skill generates `outline/volume_map.md` during Genesis -- a 460-line document containing:

| Layer | Content | Status |
|-------|---------|--------|
| L1: Volume | 5 volumes, each with Objective + chapter range | Planned |
| L2: Key Result | 3-4 KRs per volume, each with opening/progression/turn/closing nodes | Planned |
| L3: Chapter | 100 chapters, each with node role and content description | Planned |
| L4: Tension | Four-segment tension curve per volume + proportion constraints | Planned |
| L5: Bridge | 16 cross-volume hooks (item/event/info/character) + expected activation chapters | Planned |

The `shenbi-chapter-planning` SKILL.md contract declares `reads: outline/volume_map.md`. This file IS read elsewhere in the pipeline -- for structure validation and chapter-count derivation. Specifically: `gates/g2.py:289-290` (tension-curve annotation lookup), `gates/g5.py:233,236` (coverage contract), `gates/g6.py:300-301` (volume boundary adherence, G6.11), `gates/g4/story_architecture.py:51` (volume Objective+KR check), `gates/g4/volume_outlining.py:35` (volume coverage), `pipeline/triggers.py:75,283,361-374` (volume parsing and `total_chapters` recompute from `章节数`/`Chapters:` sums), `pipeline/genesis.py:65` (genesis step output path), and `pipeline/cli.py:148,638` (`total_chapters` refresh + contract reads).

However, this declaration **is never enforced for content injection.** The file is not read to build per-chapter LLM context. Tracing the content-generation path:

1. `chapter_loop.py` (1450 lines): zero references to `volume_map` content in chapter planning/drafting
2. `context_assemble.py` (318 lines): zero references to `volume_map`. Route C (line 175, `_ROUTE_C_FILES` at lines 45-49) loads only `book_spine.md`, `audit_drift.md`, and `style_profile.md`
3. `dispatch_helper.py` (656 lines): zero references to `volume_map`. `_build_skill_prompt` does not inject volume context

**Impact cascade:** This is not merely a missing feature -- it explains multiple downstream failures:
- Progressive prose collapse (C2): LLM loses narrative direction, degenerates to parameter enumeration
- Protagonist disappearance (CN1): volume_map explicitly plans character appearances per chapter, but LLM never sees them
- Cross-volume bridge failure (CN2): 16 bridges have precise activation chapters, but no one tracks them
- Overall narrative deviation: pipeline diverges from blueprint starting at Ch10

**Code location:** The contract declared at `skills/shenbi-chapter-planning/SKILL.md` (`reads` frontmatter) is a static declaration with no runtime enforcement of content injection. The pipeline's `dispatch_helper.py:_build_skill_prompt` (approx. line 400-530) assembles skill prompts but does not read the contract's `reads` field to inject declared input files. The `context_assemble.py:assembly_context` function (line 140+) assembles chapter context via three routes (A: entity index, B: embedding search, C: fixed rules) but none include volume_map parsing.

### 2.2 Character Archive Completeness: Asymmetric Gates and Prompt Skew

**Evidence chain:**

```
characters/
├── protagonist.md          Exists (7,976 bytes) -- only Lin Feng
├── relationships.md        Exists (28,340 bytes) -- 6 relationship pairs
├── major/                  Does not exist
└── minor/                  Does not exist
```

The `shenbi-character-design` SKILL.md frontmatter declares:
```yaml
writes:
  - characters/protagonist.md
  - characters/major/*.md       # Never created
  - characters/minor/*.md       # Never created
  - characters/relationships.md
```

**Three root causes converge:**

1. **G4 asymmetry (primary):** `g4/character_design.py` (140 lines) only validates protagonist structure. The `g4_character_design` function (line 18) checks `G4.protag.*` fields (name, role, personality_tags, core_value, goal_surface, goal_deep, fear, arc_type, arc_starting, arc_turning, arc_ending, voice_profile at lines 47-59). The `major_chars` check **already exists** as `G4.cd.major_chars` (lines 118-136: PASS if `characters/major/` contains >= 2 files, WARN if == 1, SKIP if the directory is absent), but there is **no equivalent check for `characters/minor/`.** The gate therefore passes (or skips) as long as protagonist.md validates and major_chars is satisfied; minor character archives are never enforced.

2. **SKILL.md prompt skew (contributing):** The `shenbi-character-design` SKILL.md prompt allocates approximately 80% of its token budget to protagonist design. Supporting characters are briefly mentioned. The flow diagram (lines 38-49) shows "Ask: supporting characters?" as a binary branch, making major/minor generation optional.

3. **`_write_parsed_outputs` may not handle wildcard paths (contributing):** The `dispatch_helper.py:_write_parsed_outputs` function (line 294) parses LLM output using `### FILE: path/to/file.md` markers (line 217-226). Wildcard contract paths like `characters/major/*.md` function as declarative contracts, not executable patterns. If the LLM outputs `### FILE: characters/major/chen-weimin.md`, the system must auto-create the `major/` directory -- but this behavior is not guaranteed.

**Impact:** Six characters appearing in chapter plans and relationships.md have no independent archives:

| Character | First Appears | Role | In relationships.md | Independent Archive |
|-----------|--------------|------|---------------------|---------------------|
| Chen Weimin | Ch10+ | Spiritual mentor | Yes (detailed arc Ch12-45) | No |
| Zhao Tiezhu | Ch12+ | Military partner | Yes (detailed arc Ch12-47) | No |
| Chu Yunlan | Ch25+ | — | Yes (mentioned) | No |
| Koen Whiteman | Ch30+ | — | Yes (mentioned) | No |
| Gangshan Tieya | Ch30+ | — | Yes (mentioned) | No |
| Middle-aged Woman | Ch1-5 | — | No | No |

Downstream skills (chapter-planning, state-settling) cannot query character state by name. `character_matrix.md` was replaced by parametric proxy (fixed in Spec 1: Truth File and State Accumulation), removing the sole structured character tracker. Every LLM call must independently "remember" character traits, causing inconsistency.

### 2.3 META Block: Design Choice with Downstream Risk

**Evidence chain:**

The `shenbi-chapter-drafting` SKILL.md (lines 95-130) explicitly requires META blocks in chapter deliverables:

```markdown
<!--META-BEGIN-->
## PRE_WRITE_CHECK
[core task, hooks to fulfill, taboos, ending pattern, AI traps, resonance gaps, transition budget]
<!--META-END-->

# Chapter Title
[prose content]

<!--META-BEGIN-->
## POST_WRITE_SELF_CHECK
[transition density check, curiosity check, meta-narrative check]
<!--META-END-->
```

The design intent is documented at SKILL.md:129: "Downstream parsers (word count, audit, scoring) must strip META blocks before processing pure prose."

**Stripping implementation** at `gates/shared.py:120-121`:
```python
c = re.sub(r"<!--META-BEGIN-->.*?<!--META-END-->", "", c, flags=re.DOTALL)
```

**This is design, not accident.** However, three problems remain:

1. **File semantic confusion:** `chapter-N.md` is simultaneously a "deliverable novel chapter" and an "internal quality control document." Any consumer bypassing `shared.py` (human reader, external tool, future AI reader) encounters internal checklists.

2. **Git diff noise:** META block changes (plan adjustments) and prose changes are commingled in the same file.

3. **Token waste:** ~31% of tokens per chapter transmit content that downstream must strip.

---

## 3. Unified Fix Strategy

### 3.1 Volume Map Consumption

Three coordinated changes to ensure the volume_map blueprint reaches the LLM at planning and drafting time.

#### 3.1.1 Inject volume_map into context_assemble.py Route C

**Critical:** Volume boundaries MUST be parsed from `volume_map.md` at runtime (using the existing `triggers.py:read_volume_boundaries()` function), NOT hard-coded as Python literals. Hard-coding `('Volume 1', (1, 15))` duplicates the map and will diverge.

**File:** `src/shenbi/pipeline/context_assemble.py`

Current Route C (lines 44-49, 175-184) loads only `book_spine.md`, `audit_drift.md`, `style_profile.md`. Add volume_map extraction:

```python
# Add to _ROUTE_C_FILES or as a separate function call in assemble_context()

def _load_volume_context(project_dir: Path, chapter: int) -> str:
    """Extract current volume context from volume_map.md for the given chapter.

    Returns:
    - Current volume Objective
    - Current KR goal and node
    - Expected chapter content per volume_map
    - Next cross-volume bridge activation chapter
    """
    vm_path = project_dir / 'outline' / 'volume_map.md'
    if not vm_path.exists():
        return ""

    volume_map = vm_path.read_text(encoding='utf-8')

    # Determine which volume this chapter belongs to
    from shenbi.pipeline.triggers import read_volume_boundaries

    # Parse volume boundaries from volume_map.md at runtime (NEVER hard-code)
    boundary_chapters = read_volume_boundaries(project_dir)
    # Returns set of {last-chapter-of-each-volume}, e.g. {15, 35, 55, 75, 100}
    # Build (vol_name, ch_range) tuples from the boundary set
    boundaries_sorted = sorted(boundary_chapters)
    volume_ranges = []
    prev_end = 0
    for i, end in enumerate(boundaries_sorted, 1):
        volume_ranges.append((f"Volume {i}", (prev_end + 1, end)))
        prev_end = end

    current_volume = None
    for vol_name, (ch_start, ch_end) in volume_ranges:
        if ch_start <= chapter <= ch_end:
            current_volume = vol_name
            break

    if not current_volume:
        return ""

    # Extract volume section, chapter node, pending bridges
    # (extraction logic using regex or section parsing)
    ...
```

#### 3.1.2 Deterministic Plan Skeleton Generator

**Critical:** Pre-filled sections from the skeleton MUST be marked as EDITABLE CONTEXT, not locked output. The LLM should see them as "suggested starting point — you may modify, override, or deviate." If the skeleton is treated as immutable, creative deviation drops to ~0%, conflicting with the design intent. Add an explicit instruction in the skeleton prompt: "以下为参考骨架，可根据创作需要调整" (The following is a reference skeleton; adjust as needed for creative purposes).

**New file:** `src/shenbi/pipeline/plan_skeleton.py`

The chapter planning step currently has the LLM generate all 8 plan sections from scratch. Analysis shows 87.5% of content can be deterministically derived from volume_map:

| Section | volume_map Provides | LLM Role | Token Saving |
|---------|--------------------|----------|-------------|
| 1. Current Task | Fully (node role + description) | Polish wording | -80% |
| 2. Reader Expectations | Partial (tension curve) | Combine with previous chapter | -40% |
| 3. Fulfill/Defer Decisions | Cross-volume bridges (bridge_tracker) | Add intra-chapter hooks | -50% |
| 4. Transition Role | Node role (opening/progression/turn/closing) | Polish wording | -80% |
| 5. Key Decisions | Not derivable | **Full LLM** | -0% |
| 6. End-of-Chapter Change | Basic (current node + next chapter) | Refine specifics | -60% |
| 7. Hook Ledger | Bridges (bridge_tracker + pending hooks) | Fill operational details | -50% |
| 8. Don't Do | Partial (volume boundary constraints) | Chapter-level taboos | -30% |
| **Total** | | | **~55%** |

The skeleton generator function `generate_plan_skeleton(project_dir, chapter)` produces a markdown template where sections 1, 4, 6, 7 are pre-filled with deterministic content from volume_map, and sections 2, 3, 5, 8 contain placeholders with guidance for LLM completion. The LLM's role shifts from "generator" to "polisher + creative filler." Expected token reduction: ~55%. Alignment with blueprint: from 0% to near 100%.

#### 3.1.3 Blueprint Alignment Checks (WARN-level, non-blocking)

**File:** `src/shenbi/pipeline/chapter_loop.py`

After chapter drafting completes, add a `_check_volume_map_alignment()` function that:
- Checks key term presence: compares terms from volume_map's chapter node description against chapter text. Warns if >70% missing.
- Checks character appearances: compares expected debut/appearance characters from volume_map against chapter text.
- Emits WARN-level issues only -- blueprint is guidance, creative deviation is allowed.

#### 3.1.4 Cross-Volume Bridge Tracker

**New file:** `truth/bridge_tracker.md`

Tracks all 16 cross-volume bridges with state:

| Bridge ID | Content | Expected Activation Ch | Actual Activation Ch | Status |
|-----------|---------|----------------------|---------------------|--------|
| V1-B1 | Brahmi inscription metal fragment | Ch26 | — | PENDING |
| V1-B4 | Chu Yunlan debut | Ch27 | — | PENDING |

Updated by `shenbi-foreshadowing-track` each chapter: when chapter content contains bridge key terms, mark ACTIVATED.

### 3.2 Character Archive Completeness

#### 3.2.1 Wildcard Path Resolution in _write_parsed_outputs

**File:** `src/shenbi/pipeline/dispatch_helper.py` (line 294)

Modify `_write_parsed_outputs` to:
1. Recognize wildcard patterns (`*`) in contract write paths
2. Auto-create intermediate directories when LLM outputs a `### FILE:` marker with a concrete path under a wildcard pattern
3. Validate that all declared write patterns have at least one corresponding output file

#### 3.2.2 SKILL.md Prompt Restructuring

**File:** `skills/shenbi-character-design/SKILL.md`

Restructure into four explicit phases:
- **Phase 1: Protagonist Depth Portrait** -> `characters/protagonist.md`
- **Phase 2: Major Supporting Character Portraits** -> `characters/major/{slug}.md` (one per character)
- **Phase 3: Minor Character Registration** -> `characters/minor/{slug}.md` (one per character)
- **Phase 4: Relationship Graph** -> `characters/relationships.md`

Add iron law: every character explicitly named in `chapter_outline.md` or `three_act.md` must have a corresponding archive in `major/` or `minor/`. Major = appears in 3+ chapters with independent arc. Minor = appears in 1-2 chapters or as functional role.

#### 3.2.3 G4 Gate Enhancement

**File:** `src/shenbi/gates/g4/character_design.py`

The existing `G4.cd.major_chars` check (lines 118-136) already validates `characters/major/` (PASS if >= 2 files, WARN if == 1, SKIP if absent). Adjust its threshold and add the missing minor check:
- `G4.cd.major_chars` (existing): raise threshold so `characters/major/` contains >= 3 `.md` files (currently >= 2)
- `G4.cd.minor_chars` (new): `characters/minor/` directory must contain >= 2 `.md` files

#### 3.2.4 Historical Archetype-Driven Character Design

Each character archive (major and minor) must declare 1-2 historical figure archetypes as design anchors. This replaces abstract personality-tag-based design with concrete, traceable behavior logic.

**New required fields per character archive:**

```yaml
archetype_sources:
  - name: <historical figure name>
    period: <era>
    traits_borrowed: [<at least 3 borrowed traits>]
    traits_discarded: [<at least 2 discarded traits>]
    adaptation_rationale: <at least 100 characters explaining why this archetype
      was chosen and how it was adapted to the novel's world>
```

**Archetype selection principles** (added to SKILL.md prompt):
1. Prefer specific historical figures over abstract archetypes ("Zhou Enlai 1930s Shanghai underground period" over "wise elder archetype")
2. 1-2 archetypes per character (1 provides core behavioral logic, optional 2nd provides supplementary dimension)
3. Archetypes must be adapted to the novel's world (skills -> world equivalents, social roles -> caste system mapping)
4. Explicit borrow/discard lists: character is not a copy of the historical figure
5. Avoid: overused figures, mythological/fictional figures, living public figures

#### 3.2.5 Restore character_matrix.md with Slug-Based Cross-References

**File:** `truth/character_matrix.md` (restore from parametric proxy)

The matrix should use slug-based cross-references to character archives:

| Character | Slug | Current State | Current Location | Current Emotion | Active Relationships | Arc Stage | Last Updated Ch |
|-----------|------|--------------|-----------------|----------------|---------------------|-----------|----------------|
| Lin Feng | lin-feng | Active | ... | ... | Chen Weimin (mentor) | Stage 1->2 | Ch56 |
| Chen Weimin | chen-weimin | Deceased (Ch45) | — | — | Lin Feng (successor) | Complete | Ch45 |
| Zhao Tiezhu | zhao-tiezhu | Active | ... | ... | Lin Feng (partner) | Stage 3 | Ch56 |

Updated by `shenbi-state-settling` each chapter with arc_log entries.

### 3.3 META Block Strategy

**Short-term (this spec, zero code changes):** Keep status quo. Add documentation and monitoring.

**Mid-term (future spec, after H1 JSON format stabilizes and H2 revision system is fixed):** Move META blocks to separate `chapter-N-meta.md` files.

#### 3.3.1 Documentation (short-term)

**New file:** `docs/framework/chapter-file-format.md`

Document the complete format specification for `chapters/chapter-N.md`:
- META block existence and rationale (quality control self-check)
- Stripping method for downstream consumers (reference `shared.py:120-121`)
- META block field definitions
- Clear statement: "META blocks are not part of the novel prose"

**Update:** `skills/shenbi-chapter-drafting/SKILL.md` around line 129 -- elevate existing comment to prominent warning block.

#### 3.3.2 Monitoring Gate (short-term)

**File:** `src/shenbi/gates/g2.py`

Add `G2.meta_ratio` check: WARN when META block proportion exceeds 50% of chapter file (indicates planning bloat).

#### 3.3.3 Separation Plan (mid-term, deferred)

When `decisions.json` format and revision system (both fixed in Spec 2: Output Validation) are stable:
- `shenbi-chapter-drafting` writes `chapters/chapter-N-meta.md` as separate output
- `chapters/chapter-N.md` becomes pure prose deliverable
- Remove META stripping logic from `shared.py:120-121`
- Update all downstream audit/scoring skills to read from `chapter-N-meta.md`

---

## 4. Affected Files

### Volume Map Consumption
| File | Change |
|------|--------|
| `src/shenbi/pipeline/context_assemble.py` (318 lines) | Add `_load_volume_context()`; inject volume context into Route C assembly (approx. line 175) |
| `src/shenbi/pipeline/plan_skeleton.py` | **New file** -- `generate_plan_skeleton()` for deterministic skeleton from volume_map |
| `src/shenbi/pipeline/chapter_loop.py` (1450 lines) | Add `_check_volume_map_alignment()` WARN-level check after chapter drafting; add bridge_tracker update hook (approx. line 600-700) |
| `src/shenbi/pipeline/dispatch_helper.py` (656 lines) | Inject volume context into shenbi-chapter-planning prompt in `_build_skill_prompt` (approx. line 400-530) |
| `skills/shenbi-chapter-planning/SKILL.md` | Update prompt to receive and consume plan skeleton |
| `truth/bridge_tracker.md` | **New file** -- cross-volume bridge state tracker |
| `skills/shenbi-foreshadowing-track/SKILL.md` | Add bridge_tracker update responsibility |

### Character Archive Completeness
| File | Change |
|------|--------|
| `src/shenbi/pipeline/dispatch_helper.py` (656 lines) | `_write_parsed_outputs` (line 294): add wildcard path resolution + auto-create directories |
| `skills/shenbi-character-design/SKILL.md` | Restructure prompt into 4 phases; add archetype-driven design methodology; add iron laws |
| `src/shenbi/gates/g4/character_design.py` (140 lines) | Raise existing `G4.cd.major_chars` threshold to >= 3 (lines 118-136); add new `G4.cd.minor_chars` (>= 2) check |
| `truth/character_matrix.md` | Restore from parametric proxy with slug-based cross-references |
| `skills/shenbi-state-settling/SKILL.md` | Add character_matrix.md update with arc_log entries per chapter |

### META Block Strategy
| File | Change |
|------|--------|
| `docs/framework/chapter-file-format.md` | **New file** -- chapter format specification with META block documentation |
| `skills/shenbi-chapter-drafting/SKILL.md` (line 129) | Elevate META stripping comment to prominent warning block |
| `src/shenbi/gates/g2.py` (306 lines) | Add `G2.meta_ratio` WARN check (> 50% triggers warning) |

---

## 5. Verification Criteria

### Volume Map Consumption
1. `context_assemble.py` Route C output includes current volume Objective and chapter node info
2. `plan_skeleton.py` generates deterministic skeleton for each chapter; LLM planning prompt receives skeleton, not blank slate
3. Hybrid planning token consumption reduced by >= 40% vs pure LLM planning
4. Over 10 consecutive chapters, key term match rate with volume_map >= 80% (from current 0%)
5. Section 5 (Key Decisions) retains full LLM creative generation -- skeletonization does not eliminate creativity
6. Bridge tracker updates state within expected activation chapter range
7. `just check` passes with zero failures

### Character Archive Completeness
8. After Genesis, `characters/major/` contains >= 3 `.md` files
9. After Genesis, `characters/minor/` contains >= 2 `.md` files
10. Each major character archive includes `archetype_sources` field with >= 1 historical archetype
11. Each archive includes explicit borrow/discard lists (>= 3 borrowed traits, >= 2 discarded)
12. `adaptation_rationale` >= 100 characters per archetype
13. Archetypes are specific historical figures (not abstract type labels)
14. Downstream skills (chapter-planning) can read `characters/major/{slug}.md` successfully
15. State-settling updates `character_matrix.md` using slug references
16. After 10 consecutive chapters, `protagonist.md` `arc_log` contains progressive stage entries

### META Block Strategy
17. `docs/framework/chapter-file-format.md` exists and is complete and accurate
18. SKILL.md warning is prominently visible
19. `just check` passes with zero failures (no code changes)
20. `G2.meta_ratio` WARN triggers when META ratio exceeds 50%

---

## 6. Dependencies

```
Spec 1 (Truth File and State Accumulation)
  ├── character_matrix.md restoration depends on this
  ├── bridge_tracker needs append mode
  ├── character_matrix incremental updates need this
  └── character_matrix.md slug-based cross-references

This Spec
  ├── shenbi-chapter-planning (consumes plan skeleton)
  ├── shenbi-chapter-drafting (consumes volume context)
  ├── shenbi-foreshadowing-track (bridge_tracker updates)
  ├── shenbi-character-design SKILL.md rewrite
  ├── shenbi-state-settling (character_matrix update logic)
  └── shenbi-chapter-drafting SKILL.md (META documentation)

Mid-term:
  └── Spec 2 (Output Validation and Format Enforcement)
      └── META block separation to chapter-N-meta.md
```

---

## 7. Original Code Mapping

This consolidated spec merges the following original issue codes:

| Original Issue Code | Description | Section in This Spec |
|---------------------|-------------|---------------------|
| `volume-map` | volume_map.md not consumed for per-chapter content/context injection (validation consumption exists) | 2.1, 3.1 |
| `character-archive` | Supporting character archives never created | 2.2, 3.2 |
| `C3` | META blocks contaminate deliverable chapter files | 2.3, 3.3 |
