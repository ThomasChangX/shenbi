---
name: shenbi-foreshadowing-lifecycle
description: Combined foreshadowing lifecycle -- recall dormant hooks, track active hooks against chapter body, and plant new hooks from plan in a single call.
contract:
  kind: artifact
  reads:
    - {file: plans/chapter-N-plan.md, fields: [7. 本章 hook 账]}
    - {file: chapters/chapter-N.md}
    - {file: truth/pending_hooks.md}
    - {file: outline/volume_map.md, fields: [cross-volume bridges]}
  writes: []
  updates:
    - truth/pending_hooks.md
---
<!-- AUTO-CHECK-START -->

## auto-check (generated -- do not edit)

<!-- AUTO-CHECK-END -->

<!-- AUTO-GENERATED from frontmatter — do not edit -->

## 数据契约

- **Reads:** plans/chapter-N-plan.md, chapters/chapter-N.md, truth/pending_hooks.md, outline/volume_map.md
- **Writes:** none
- **Updates:** truth/pending_hooks.md

<!-- END AUTO-GENERATED -->

# Foreshadowing Lifecycle

HARD-GATE: Must execute after chapter drafting and state-settling. Combines recall, track, and plant operations into a single LLM call for shared context and consistent lifecycle management.

## Internal Operation Order

Perform three sequential operations in a **single LLM call**:

### Phase 1: Recall

Scan `pending_hooks.md` for hooks whose lifecycle state is DORMANT or whose
`trigger_condition` matches the current chapter context. Decide if any should
reactivate. Update state from DORMANT to ACTIVE where reactivation is warranted.

**Rules:**
1. **Deterministic threshold filtering** -- final verdict (overdue / not overdue) is determined by pure numeric comparison of `last_reinforced`, `max_distance`, and `cultivation_interval` against `current_chapter`.
2. **Exclude RESOLVED** -- resolved hooks are not recalled.
3. **Output traceable** -- each recalled hook must cite `last_reinforced`, `max_distance`, and silence chapter count.

### Phase 2: Track

For each ACTIVE hook in `pending_hooks.md`, scan the chapter body for:
1. **References**: Is the hook mentioned or advanced?
2. **Resolution**: Has the hook's resolution condition been met?
3. **Lifecycle update**: Update `lifecycle_state` per hook based on findings.

**State transition rules** (see `lifecycle-states.md`):
- PLANTED -> RELEVANT: Hook is referenced or contextually relevant in this chapter
- RELEVANT -> TRIGGERED: Hook's trigger condition is met
- TRIGGERED -> RESOLVED: Hook's resolve condition is met
- RELEVANT/TRIGGERED -> EXPIRED: Hook exceeds `max_distance` without resolution
- RELEVANT/TRIGGERED -> DORMANT: Hook's cultivation interval expired without reinforcement

**Iron Laws:**
1. **Every active hook must be evaluated this chapter** -- no skipping.
2. **State transitions require textual evidence** -- must find corresponding content in chapter body before changing state.
3. **core_hook = true MUST NOT be ABANDONED** -- core hook abandonment = story fracture.
4. **Density budget overflow must be reported** -- explain which operations were deferred.
5. **Field ownership**: This skill is the **sole driver** of hook lifecycle state (PLANTED->RELEVANT->TRIGGERED->RESOLVED). `last_reinforced`/`subtlety` fields are maintained by `shenbi-state-settling`; new hooks by this skill (Phase 3); resolution by `shenbi-foreshadowing-resolve`.

### Phase 3: Plant

From the chapter plan Section 7 (Hook Ledger), identify hooks that should be
newly planted this chapter. For each:
1. Assign a unique hook ID (format: MH-NNN or CP-NNN or sequel-specific prefix)
2. Define `trigger_condition` and `resolve_condition`
3. Set initial `lifecycle_state` to ACTIVE
4. Register in `pending_hooks.md`

**Iron Laws:**
1. **Chapter operations must be <= 8** -- includes plant, reinforce, trigger, resolve; hooks exceeding budget must be deferred to next chapter.
2. **Must read existing hooks before planting** -- planting without reading `pending_hooks.md` = duplication or contradiction.
3. **Each new hook must have complete metadata** -- type, dimension, subtlety, cultivation_interval, max_distance, escalation_curve all required.
4. **Cross-thread dependencies must be recorded** -- `depends_on` field must never be omitted (fill `[]` if none).
5. **SMOKESCREEN hooks must have exit strategy** -- mark in `notes` when/how to handle.

**Planting Guide:**

Choose planting position:
1. **Daily-life paragraphs** -- best position, readers most relaxed, easiest to overlook hints.
2. **Battle paragraphs** -- suitable for symbolic foreshadowing (an object, an action).
3. **Dialogue paragraphs** -- suitable for informational hooks (character's "casual mention").
4. **Avoid chapter-end climax paragraphs** -- reader attention is on existing reveals; new hooks will be drowned.

Subtlety strategy:
- Main-thread hooks: subtlety 0.4-0.6 (must be noticeable by some readers)
- Side-thread hooks: subtlety 0.6-0.8 (can be deeper)
- SMOKESCREEN: subtlety 0.3-0.5 (must be noticeable to mislead)
- SIDE_SHADOW: subtlety 0.7-0.9 (extremely subtle, for reread value)

Full type/dimension/curve/subtlety lookup table in `hook-types.md`.

**Genesis mode (--mode genesis):**

Genesis phase has no chapter memo (`plans/chapter-N-plan.md`). Genesis mode extracts cross-volume master hooks from outline:
- **reads**: `outline/story_frame.md` + `outline/volume_map.md` (replaces chapter plan)
- **Extract master hooks**: from volume_map cross-volume hooks, initialize as PLANTED state
- **writes**: same as default mode (`truth/pending_hooks.md`)

Genesis mode flow:
1. Read `outline/story_frame.md` extract three-act cross-volume promises
2. Read `outline/volume_map.md` extract per-volume end-of-volume entity hooks
3. For each cross-volume hook: assign MH ID, set PLANTED, declare resolution volume
4. Append to `truth/pending_hooks.md`

Genesis mode does NOT read `plans/chapter-N-plan.md`, does NOT process hook ledger OPEN items (that is per-chapter mode responsibility).

## Cross-Volume Bridge Tracking

After updating `pending_hooks.md`, also check `truth/bridge_tracker.md`:
1. Read current chapter text
2. For each bridge in PENDING state: if chapter contains bridge key terms (character name, item name, event description), mark ACTIVATED with current chapter number as Actual Activation Ch
3. If a bridge was expected to activate by this chapter but has not, mark DEFERRED with a note
4. Write updated `bridge_tracker.md` back to disk

## Output Format

```
### FILE: truth/pending_hooks.md

[Updated pending_hooks content including all lifecycle changes]

### FILE: audits/chapter-N-foreshadowing.md

# Foreshadowing Lifecycle Report (Chapter N)

## Phase 1: Recall

| Hook ID | Previous State | New State | Reason |
|---------|---------------|-----------|--------|
| H01 | DORMANT | ACTIVE | trigger_condition matched current chapter context |

No overdue hooks to recall (if none).

## Phase 2: Track

### Chapter Operations

| Hook ID | Operation | Previous State | New State | Text Location |
|---------|-----------|---------------|-----------|---------------|
| hook-002 | TRIGGER | RELEVANT | TRIGGERED | Para 4 |
| hook-004 | (new) | — | PLANTED | Para 7 |

### Overdue Warnings

| Hook ID | Last Reinforced | Current Ch | Interval | Status |
|---------|----------------|------------|----------|--------|
| hook-001 | 3 | 8 | 5/5 | OVERDUE |

### Max Distance Approaching

| Hook ID | Plant Ch | Current Ch | max_distance | Status |
|---------|---------|------------|-------------|--------|
| hook-002 | 5 | 20 | 25 | OK (5 ch remaining) |
| hook-005 | 3 | 20 | 15 | WARNING (-5 ch over) |

## Phase 3: Plant

### Planted Items

| Hook ID | Type | Dimension | Subtlety | Curve | max_distance | Depends On |
|---------|------|-----------|---------|-------|--------------|------------|
| hook-004 | GENUINE | CHARACTER | 0.6 | RISING | 20 | — |
| hook-005 | SMOKESCREEN | SYMBOLIC | 0.4 | FLAT | 12 | hook-003 |

### Density Accounting

| Operation Type | This Chapter |
|---------------|-------------|
| plant | X |
| reinforce | X |
| trigger | X |
| resolve | X |
| **Total** | X / 8 |

## Summary

**Active hooks**: X
**This chapter operations**: Y / 8 (density budget)
**State distribution**:
- PLANTED: X
- RELEVANT: X
- TRIGGERED: X

**Risk signals**:
- [OVERDUE] hook-001, hook-003
- [EXPIRED] hook-005
- [DISTANCE WARNING] hook-002 (5 ch remaining)

**Next chapter recommended actions**:
- hook-001 -> recommend REINFORCE (cultivation interval expired)
- hook-005 -> must TRIGGER or handle EXPIRY
```

## Anti-Rationalization

| Excuse | Reality |
|--------|---------|
| "This chapter is too simple, no foreshadowing needed" | Simple chapters are precisely the best time to plant -- readers are off-guard |
| "Readers won't notice such subtle details" | Web novel reread culture and comment culture make details easily discoverable |
| "Plant first, decide usage later" | Unplanned hooks = eventually abandoned = Chase Power debt |
| "Set subtlety high, nobody will find it" | Foreshadowing's purpose is not hiding, it's creating "ah, so that's why" at resolution |
| "Hook didn't appear this chapter, skip update" | No update -> cultivation interval check fails -> hook quietly dies |
| "Manual tracking is too troublesome" | No tracking -> 200 chapters later forgot what was planted -> massive unresolved |
| "Minor hooks don't need tracking" | Minor hooks = story texture; fractured texture is perceptible to readers |

## Defect Evidence Format

Each defect/finding report must follow four-element format:

1. **Location** -- `file_path` Lline-line (e.g. `chapters/chapter-5.md` L23-27)
2. **Original quote** -- use `>` to quote original text, >=20 chars context
3. **Violated rule** -- cite exact rule name from SKILL.md (verbatim match)
4. **Severity** -- BLOCKING | CRITICAL | MINOR

Missing any element invalidates the defect report.
