# Shenbi Test, Log, and Analysis Design

## 1. Purpose

Build a skill framework capable of producing great Chinese novels — long form (>5M words) and short form — at professional quality. The test system drives skills toward that goal through iterative testing, logging, analysis, and enhancement.

Model switching is an **improvement strategy**: each model's failures become skill improvements that persist for all subsequent runs. By the end, SKILL.md files contain instructions robust enough that any competent model can follow them to produce quality output.

Secondary output: model comparison data collected as a byproduct.

## 2. Three-Tier Testing Architecture

### 2.1 Tier Structure

| Tier | Scope | Goal | Starts after |
|------|-------|------|--------------|
| T1: Skill | Single skill in isolation | Certify each skill works correctly on its own | — |
| T2: Phase | All skills within one creative phase | Catch intra-phase interactions | T1 for that phase = 100 |
| T3: Pipeline | Full creative pipeline end-to-end | Catch cross-phase cascades; validate novel quality | T1 + T2 all = 100 |

### 2.2 Test Types (T1 level)

- **Bug-hunt** (planted defect): agent must find the known bug. Input has a specific defect planted. Pass = agent detects it at correct severity.
- **Clean** (no defect): agent must not hallucinate problems. Input is correct. Pass = agent reports zero issues.
- **Generative** (open-ended): agent produces novel output (chapter, world, character, etc.). Evaluated against a rubric. No `expected/` directory.

### 2.3 Phase Definitions (T2)

| Phase | Skills involved | Seed input |
|-------|----------------|------------|
| Genesis | worldbuilding → power-system → faction-builder → location-builder → character-design → relationship-map | `outline-example.md` |
| Architecture | story-architecture → volume-outlining → pacing-design → plot-thread-weaver → genre-config | Genesis output |
| Planning | chapter-planning → foreshadowing-plant → context-composing | Architecture output |
| Drafting | chapter-drafting → state-settling → foreshadowing-track → style-polishing / anti-detect / length-normalizing | Planning output |
| Audit (batch) | All 18 review-* skills run on drafted chapter | Drafting output |
| Import | import-analysis → character-extraction → world-extraction → canon-import | `report-example.txt` |
| Management | snapshot-manage → drift-guidance → intent-management → chapter-pattern → volume-consolidation | Drafting output |
| Short story | short-outline → short-drafting → short-packaging | `outline-example.md` |

### 2.4 Pipeline Variants (T3)

- **Long-form**: `outline-example.md` → genesis → architecture → planning → drafting (3+ chapters) → audit → revision → state-settling → management. Produces a mini-novel project.
- **Short-form**: `outline-example.md` → short-outline → short-drafting → short-packaging. Produces a complete short story.
- **Import-form**: `report-example.txt` → import-analysis → character-extraction → world-extraction → canon-import. Produces extracted project files from existing novel.

## 3. Scoring System

### 3.1 Universal Rules

- All scores are 0–100.
- Each dimension scored 0–100, weighted sum = final score.
- Thresholds:
  - 90–100: PASS (excellent)
  - 75–89: PASS (acceptable, enhancement signals logged)
  - 60–74: CONDITIONAL (skill needs improvement)
  - 0–59: FAIL (skill not usable)

### 3.2 Universal Kill Switches

Any violation = total test score 0:

- HARD-GATE violation in the skill spec
- Bug-hunt: missed a planted defect (false negative)
- Clean test: hallucinated a defect (false positive)
- Extraction/audit skills: content not groundable to source text
- T2: any skill's T1 score drops below 90 during integration
- T3: any chapter fails sensitivity audit (platform-prohibited content)

### 3.3 Universal Dimensions (15%, apply to all T1 tests)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed; no skips, no reordering without justification |
| 2 | Output completeness | 5% | All required output files/sections produced; no empty or placeholder content |

## 4. T1: Per-Skill Rating Standards (85% remaining)

Each skill has 5–8 bespoke dimensions with explicit critical standards. Full rubrics live in `tests/tiers/t1-skill/<skill-name>/rubric.md`.

### 4.1 Genesis Skills

#### shenbi-worldbuilding (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Internal consistency | 15% | Zero contradictions within world rules; hard rules are mutually compatible |
| 4 | Prose quality | 10% | story_bible.md is narrative prose paragraphs; bullet-point lists = 0 |
| 5 | Deduplication | 10% | Each fact appears in exactly one canonical file |
| 6 | Hook potential | 15% | "Undercurrent" section seeds ≥3 future conflict sources |
| 7 | Scalability | 15% | Structure supports 200+ chapters without retcon |
| 8 | Rule enforceability | 10% | Hard rules are concrete and testable; "magic is mysterious" = fail |
| 9 | Template completeness | 10% | All required output files present with all required fields |

#### shenbi-character-design (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Voice distinctness | 20% | Each major character has unique speech markers; interchangeable dialogue = fail |
| 4 | Arc definition | 15% | Protagonist has start state, turning point, end state; missing arc = 0 |
| 5 | Motivation depth | 15% | Surface goals AND deep motivations both explicit |
| 6 | Minor character respect | 10% | Minor characters have agency and independent motivation |
| 7 | Relationship coherence | 10% | Matrix consistent with character profiles |
| 8 | Voice profile operability | 10% | Patterns specific enough for downstream audit skills to use |
| 9 | Fear/weakness grounding | 5% | Every character has explicit fears |

#### shenbi-story-architecture (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Three-layer conflict coherence | 20% | Surface, personal, deep conflicts are mutually reinforcing |
| 4 | Dual-line integrity | 15% | Front-stage AND back-stage storylines both defined |
| 5 | OKR executability | 15% | KRs are measurable and map to chapter ranges; "protagonist grows" = fail |
| 6 | Prose quality | 15% | story_frame.md is narrative paragraphs, not bullet lists |
| 7 | Foreshadowing seeding | 10% | Story frame seeds ≥3 foreshadowing lines |
| 8 | Volume map scalability | 10% | Volume structure supports full novel length |

#### shenbi-power-system (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Cost enforcement | 20% | Every power use has visible cost; costless power = 0 |
| 4 | Ceiling definition | 15% | Explicit top tier with population count |
| 5 | Level gap significance | 15% | Each gap is qualitative (new ability type), not just "stronger" |
| 6 | Boundary clarity | 15% | Each level lists can-do / barely-can-do / cannot-do |
| 7 | Protagonist constraint | 10% | Power source has precedent or equivalent cost |
| 8 | Milestone alignment | 10% | Level progression maps to story milestones |

#### shenbi-faction-builder (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Interest-driven realism | 20% | Faction behavior explainable by interest logic; no "evil for evil's sake" |
| 4 | Internal conflict | 15% | Every faction has ≥1 internal factional split |
| 5 | Cross-faction dynamics | 15% | ≥2 factions have explicit relationships |
| 6 | Anchor character consistency | 15% | Referenced characters exist in characters/*.md |
| 7 | Behavioral predictability | 10% | "In situation X, faction does Y" patterns defined |
| 8 | Prose quality | 10% | Faction descriptions are narrative prose |

#### shenbi-location-builder (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Spatial consistency | 20% | Distances/directions/travel times never contradict established facts |
| 4 | Atmosphere quality | 15% | Sensory signatures (sight/sound/smell) and time-of-day associations |
| 5 | Prose format | 15% | Narrative prose, not bullet-point feature lists |
| 6 | Functional clarity | 15% | Each location has a primary plot function |
| 7 | Walk-through-ability | 10% | Spatial layout detailed enough to mentally "walk through" |
| 8 | Cross-location consistency | 10% | New locations don't break distance/travel time to existing ones |

#### shenbi-relationship-map (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Interest-grounded relationships | 20% | Every relationship traceable to interest/emotion/bloodline/mentorship |
| 4 | Information boundary rigor | 15% | Who knows what about whom explicitly recorded |
| 5 | Evolution planning | 15% | Each relationship defines start, turning points, expected end state |
| 6 | Deduplication | 10% | Relationship data in relationships.md only, not duplicated in character cards |
| 7 | Asymmetry tracking | 15% | Information asymmetries tracked as dramatic tension sources |
| 8 | Character reference integrity | 10% | All referenced characters exist in character files |

#### shenbi-pacing-design (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Four-beat completeness | 20% | Every cycle includes buildup/escalation/explosion/aftermath |
| 4 | Three-line balance | 15% | QUEST/FIRE/CONSTELLATION ratios all present |
| 5 | Monotony prevention | 15% | No more than 3 consecutive chapters of same type |
| 6 | Genre alignment | 15% | Pacing matches genre expectations |
| 7 | Actionability | 10% | Principles detectable and correctable by downstream skills |
| 8 | Scene type catalog | 10% | 6–8 scene types minimum defined |

#### shenbi-plot-thread-weaver (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | No blank chapters | 20% | Every chapter advances ≥1 thread |
| 4 | Long-line contact discipline | 15% | A-lines don't exceed max_gap |
| 5 | Short-line closure | 15% | C-lines resolve within planned span |
| 6 | Climax window coordination | 15% | Subplot climaxes complement volume climaxes |
| 7 | Crossing point purpose | 10% | Thread crossings serve dramatic effect |
| 8 | Priority classification | 10% | P0–P3 correctly assigned by scope and impact |

#### shenbi-genre-config (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Change safety | 20% | Backup before modification; rollback capability |
| 4 | Conflict prevention | 15% | Modifications don't contradict existing audit corrections |
| 5 | Fatigue word balance | 15% | Banned words ≤50; caution words have viable replacements |
| 6 | Audit dimension calibration | 15% | Selectively enabled; no false positive floods |
| 7 | Human approval enforcement | 10% | All changes require explicit sign-off |
| 8 | Config structural validity | 10% | JSON is well-formed; all required fields present |

#### shenbi-volume-outlining (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | OKR executability | 20% | KRs map to specific chapter ranges; no vague statements |
| 4 | Tension curve design | 15% | Wave pattern (buildup/rising/explosion/aftermath) |
| 5 | Cross-volume bridging | 15% | Volume ending leaves ≥1 tangible hook |
| 6 | Golden chapters accommodation | 10% | Early chapters may deviate for world-building |
| 7 | Conflict advancement | 15% | Surface/personal/deep conflicts explicitly advanced |
| 8 | Chapter range realism | 10% | Chapter counts match KR complexity |

### 4.2 Planning Skills

#### shenbi-chapter-planning (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Goal derivation rigor | 15% | Follows priority chain: instruction > override > volume KR > focus > intent |
| 4 | Reader expectation management | 15% | Explicitly states what readers wait for and create/delay/satisfy strategy |
| 5 | Hook accounting | 15% | All hooks tracked; pressured hooks advanced after 5+ chapters silence |
| 6 | Golden chapters discipline | 10% | First N chapters enforce extra constraints |
| 7 | End-of-chapter change | 15% | 1–3 concrete changes defined (information/relationship/physical/power) |
| 8 | Memo 8-section completeness | 10% | All 8 sections populated |
| 9 | Prohibition specificity | 5% | "Do not do" list is specific, not generic |

#### shenbi-foreshadowing-plant (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Budget enforcement | 20% | ≤8 operations per chapter; violation = 0 |
| 4 | Metadata completeness | 15% | All required fields present; depends_on never omitted |
| 5 | Smokescreen accountability | 15% | Every SMOKESCREEN has documented exit strategy |
| 6 | Existing hook awareness | 15% | Reads pending_hooks.md first; no duplication/contradiction |
| 7 | Strategic placement | 10% | Planting guidance references scene type appropriateness |
| 8 | Type/dimension accuracy | 10% | Hook type and dimension correctly classified |

#### shenbi-foreshadowing-track (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Complete evaluation | 20% | Every active hook assessed, none skipped |
| 4 | Textual evidence | 20% | State transitions require specific text evidence |
| 5 | Core hook protection | 15% | core_hook: true never ABANDONED |
| 6 | Expiry detection | 15% | Hooks exceeding max_distance correctly flagged |
| 7 | Density budget reporting | 15% | Operations vs. budget clearly reported |

#### shenbi-foreshadowing-resolve (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Chase Power management | 20% | CP above 200 triggers mandatory immediate resolution |
| 4 | Resolution quality | 15% | Core hooks achieve ≥PARTIAL_PAYOFF, never FLAT_PAYOFF |
| 5 | Prioritization | 15% | High-CP hooks resolved first |
| 6 | Volume completeness | 15% | Every active hook inventoried at volume end |
| 7 | Smokescreen handling | 10% | Smoke screens include truth revelation when resolved |
| 8 | Human gate | 10% | ABANDON operations require explicit human approval |

#### shenbi-context-composing (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Completeness | 20% | All P1 items present; higher-priority items never trimmed before lower |
| 4 | Accuracy | 15% | Summaries, character states, world rules correctly extracted |
| 5 | Hook urgency calculation | 15% | Correctly computes (current_chapter - last_reinforced) / max_distance |
| 6 | Ending diversity check | 15% | Flags if recent chapters share same ending pattern |
| 7 | Recency | 10% | Only recent summaries and relevant hooks included |
| 8 | Hook debt brief quality | 10% | Debt brief is actionable for downstream drafting |

### 4.3 Drafting Skills

#### shenbi-chapter-drafting (8 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Plan compliance | 15% | Chapter executes memo specifications |
| 4 | AI-flavor avoidance | 15% | Transition word density ≤1/3000 words; zero meta-narrative prose |
| 5 | Voice fidelity | 15% | Every dialogue line matches character voice_profile |
| 6 | Show-don't-tell | 10% | Emotions shown through action/sensation, not stated |
| 7 | Chapter-end hook | 10% | Last 300 words create pull |
| 8 | Foreshadowing integrity | 10% | Claimed foreshadowing items present in text |
| 9 | Paragraph rhythm | 5% | Varied paragraph lengths |
| 10 | PRE_WRITE_CHECK | 5% | Check completed before drafting |

#### shenbi-style-polishing (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Content preservation | 20% | Zero changes to plot, character behavior, or emotional tone |
| 4 | Word count stability | 15% | Changes bounded to ±15% |
| 5 | AI-flavor avoidance | 15% | Polishing does not introduce AI-typical phrasing |
| 6 | Style fidelity | 15% | If style_profile.md exists, polish respects it |
| 7 | Restraint | 10% | Does not over-polish or rewrite |
| 8 | Report completeness | 5% | Polishing report lists all changes |
| 9 | Structural flag quality | 5% | [polisher-note] annotations are specific and actionable |

#### shenbi-anti-detect (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Content preservation | 20% | No changes to plot, characters, or foreshadowing |
| 4 | Targeted intervention | 15% | Only rewrites at detected marker points |
| 5 | Audit pass rate | 15% | Anti-AI audit passes after rewriting |
| 6 | Style preservation | 15% | Does not lose authorial voice |
| 7 | Bounded iteration | 10% | After 3 failed passes, reverts to best version |
| 8 | Before/after audit comparison | 10% | Clear before/after error and warning counts |
| 9 | Good sentence preservation | 5% | "Good sentences" preserved unchanged |

#### shenbi-length-normalizing (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Narrative preservation | 20% | No events added/removed; no character behavior changes |
| 4 | 25% floor gate | 15% | Rejects if compression would be too severe |
| 5 | Voice preservation | 15% | Expansion does not introduce AI-typical phrasing |
| 6 | Range compliance | 15% | Final word count within target ±15% (soft), ±30% (hard) |
| 7 | Meaningful expansion | 10% | Expansion deepens content rather than padding |
| 8 | Consistency checklist | 10% | Confirms no narrative changes |

#### shenbi-style-learning (5 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Reproducibility | 25% | Same input produces identical output (pure computation) |
| 4 | Statistical validity | 20% | Minimum sample size enforced; insufficient data flagged |
| 5 | Objectivity | 15% | Reports "what is," never "what is good or bad" |
| 6 | Completeness of metrics | 15% | All 7 statistical dimensions computed |
| 7 | Downstream usability | 10% | Profile structured for other skills to reference |

### 4.4 Audit Skills (18 review-* skills)

#### Shared audit dimensions (65%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | True positive rate | 20% | 100% of planted defects found; miss = 0 |
| 4 | False positive rate | 15% | Zero hallucinated findings |
| 5 | Evidence grounding | 10% | Every finding cites specific text + source file/line |
| 6 | Severity accuracy | 10% | Error vs warning classification matches expected |
| 7 | Fix actionability | 10% | Each finding has concrete fix |

#### Per-audit-skill unique dimension (20%)

| Skill | Unique Dimension | Standard |
|-------|-----------------|----------|
| shenbi-review-character | BDI coverage | All speaking/acting characters assessed; protagonist + speaking characters mandatory |
| shenbi-review-continuity | Timeline extraction precision | Time markers extracted and cross-compared across ≥2 chapters |
| shenbi-review-dialogue | Voice fingerprint matching | Per-speaker: sentence length, vocabulary, pattern deviation quantified |
| shenbi-review-pacing | Chapter type classification accuracy | QUEST/FIRE/CONSTELLATION correctly assigned for last 5 chapters |
| shenbi-review-anti-ai | Pattern coverage | All 10 deterministic checks executed; none skipped |
| shenbi-review-foreshadowing | Lifecycle tracking | Every hook state transition has text evidence |
| shenbi-review-world-rules | Numerical cross-reference | Ages/dates/distances verified against prior chapters |
| shenbi-review-sensitivity | Platform rule application | Correct platform rules applied from novel.json target |
| shenbi-review-memo-compliance | Section-by-section verification | All 8 memo sections checked independently |
| shenbi-review-motivation | Causal chain reconstruction | Behavior chain completeness for every major action |
| shenbi-review-pov | Information leakage detection | Cross-POV knowledge verified against presence matrix |
| shenbi-review-reader-pull | Hook strength assessment | Opening/chapter-end/mid-chapter traction all quantified |
| shenbi-review-highpoint | Buildup-payoff comparison | Suppression-explosion level quantified on 1–5 scale |
| shenbi-review-texture | Laundry-list detection | Sequential markers + conflict absence correctly flagged |
| shenbi-review-long-span | N-gram extraction accuracy | 6-char n-gram rate correctly computed against threshold |
| shenbi-review-era | Anachronism detection | Vocabulary/artifact/location all period-verified |
| shenbi-review-fanfic | Mode strictness application | Canon/AU/OOC/CP mode correctly determines severity |
| shenbi-review-spinoff | Timeline-aware leakage | Info revealed later in parent timeline correctly flagged |

### 4.5 Revision Skills

#### shenbi-chapter-revision (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Non-regression | 20% | Blocking/critical/AI-trace counts do not increase |
| 4 | Scope discipline | 15% | Only fixes audit findings; no unrelated changes |
| 5 | Length constraint | 15% | Change within ±15% of original length |
| 6 | Fallback correctness | 10% | Best-version selection logic correctly applied |
| 7 | Fix accuracy | 15% | Targeted fix resolves the specific issue |
| 8 | Content preservation | 10% | Plot, character, foreshadowing unchanged |

### 4.6 State Management Skills

#### shenbi-state-settling (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Extraction accuracy | 20% | Only explicit chapter changes recorded; no inference |
| 4 | Category completeness | 15% | All 9 change categories evaluated |
| 5 | Certainty distinction | 15% | Direct vs. implied changes tagged differently |
| 6 | Incremental correctness | 15% | Appends without rewriting truth files |
| 7 | Human gate | 10% | No truth file updated before human approval |
| 8 | Cross-reference consistency | 10% | Changes to one truth file reflected in related files |

#### shenbi-truth-sync (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Extraction accuracy | 20% | Extracted facts faithfully represent chapter text |
| 4 | Conflict detection completeness | 20% | Every inconsistency between chapter and truth files caught |
| 5 | Incremental correctness | 15% | Only changed portions updated |
| 6 | Auditability | 15% | Before/after diffs preserved |
| 7 | Scope precision | 15% | Only syncs chapters within specified scope |

#### shenbi-snapshot-manage (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Snapshot completeness | 25% | All 11 truth files included; no omissions |
| 4 | Immutability | 20% | Snapshots never modified after creation |
| 5 | Human-gate enforcement | 20% | Rollback requires explicit human confirmation |
| 6 | Post-rollback integrity | 15% | Chapters after rollback point flagged as UNVERIFIED |
| 7 | Operation correctness | 5% | create/view/rollback/list all work as specified |

#### shenbi-volume-consolidation (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Conciseness | 20% | Volume summary under 500 words |
| 4 | Unresolved hook completeness | 20% | Every planted but unresolved hook explicitly listed |
| 5 | Retrievability | 15% | Archived per-chapter summaries remain accessible |
| 6 | Narrative arc accuracy | 15% | Volume summary faithfully represents what happened |
| 7 | Key event selection | 15% | Only significant events included; no trivia |

#### shenbi-foundation-review (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Scoring rigor | 20% | Every deduction has a concrete improvement suggestion |
| 4 | Threshold enforcement | 20% | 80-point minimum and core-conflict veto unconditional |
| 5 | Evidence-based evaluation | 15% | Only existing content scored; no assumed content |
| 6 | Actionability | 15% | Fix suggestions point to exact files/paragraphs |
| 7 | Dimension balance | 15% | All 5 dimensions scored independently |

#### shenbi-drift-guidance (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Correct classification | 20% | Errors never conducted forward; only warnings pass |
| 4 | Actionability of guidance | 20% | Each item says "what next chapter should do" |
| 5 | Cap enforcement | 15% | No more than 5 drift items |
| 6 | Target specificity | 15% | Every item has a targeted_chapter field |
| 7 | Source traceability | 15% | Each drift item traceable to specific audit finding |

#### shenbi-intent-management (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Human sovereignty | 25% | AI never makes creative decisions; only organizes human input |
| 4 | Drift integration completeness | 20% | All drift guidance items merged into current focus |
| 5 | Priority clarity | 20% | P0/P1/P2 clearly separates critical from nice-to-have |
| 6 | Timeliness | 10% | Current focus updated before every chapter planning session |

#### shenbi-chapter-pattern (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Classification accuracy | 25% | Every chapter correctly assigned to ≥1 of 13 patterns |
| 4 | Threshold strictness | 20% | Hard limits on consecutive patterns enforced |
| 5 | Entropy calculation correctness | 15% | Shannon entropy accurately computed across correct window |
| 6 | Actionability of recommendations | 15% | Next-chapter suggestion is specific (which pattern, why) |
| 7 | Distribution coverage | 10% | Minimum distinct patterns in rolling window verified |

### 4.7 Import Skills

#### shenbi-import-analysis (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Traceability | 20% | Every extracted fact traceable to source chapter + paragraph |
| 4 | Zero guessing | 15% | Non-locatable items marked "unconfirmed," not fabricated |
| 5 | Pipeline correctness | 15% | Data dependencies between 8 passes respected |
| 6 | Unconfirmed item completeness | 10% | Exhaustive list of items needing human arbitration |
| 7 | Pass completeness | 10% | All 8 passes executed with non-empty output |
| 8 | Cross-pass consistency | 10% | No contradictions between pass outputs |
| 9 | Statistics accuracy | 5% | Chapter/word/character counts match source |

#### shenbi-character-extraction (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Evidence grounding | 25% | Every personality tag, speech pattern, relationship has quoted passage |
| 4 | Voice fingerprint accuracy | 20% | Statistical extraction from actual dialogue, not impressions |
| 5 | Arc evidence | 15% | Start and turning points backed by chapter-specific behavioral evidence |
| 6 | No fabrication | 15% | Non-derivable items marked "unconfirmed" |
| 7 | Relationship network completeness | 10% | All major relationships mapped with interaction evidence |

#### shenbi-world-extraction (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Rule evidence threshold | 20% | Each rule has ≥2 independent textual evidence citations |
| 4 | Violation-based inference | 15% | Rules inferred from failures and avoidances, not just successes |
| 5 | Power system completeness | 15% | Level names, advancement, boundaries, costs all addressed |
| 6 | Consistency | 15% | Extracted rules don't contradict story bible narrative |
| 7 | Location coverage | 10% | Top locations extracted with atmosphere and function |

#### shenbi-canon-import (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Mode fidelity | 25% | Preservation/deviation rules strictly followed; no silent mixing |
| 4 | Evidence traceability | 20% | Every canon entry cites original work (chapter/episode/paragraph) |
| 5 | Deviation transparency | 20% | All deviations from original explicitly declared |
| 6 | 5-section completeness | 20% | World, character, event, relationship, timeline all present |

### 4.8 Short Story Layer

#### shenbi-short-outline (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | 3-step enforcement | 20% | Generate → review → revise; no skipped steps |
| 4 | Chapter task completeness | 15% | Every chapter has ≥1 task advancing ≥1 thread |
| 5 | Act proportioning | 15% | 20/60/20 split respected |
| 6 | No dead chapters | 15% | Zero "transition" or filler chapters |
| 7 | Thread limit compliance | 10% | ≤1 subplot + ≤1 emotional arc |
| 8 | Turning point quality | 10% | Each turning point is a genuine reversal |

#### shenbi-short-drafting (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Sequential generation | 20% | Chapters generated strictly in order |
| 4 | Per-chapter audit rigor | 20% | Every chapter passes all audit checks before acceptance |
| 5 | Cross-chapter consistency | 20% | Position, timeline, information, relationships, style continuous |
| 6 | Revision discipline | 15% | 3-round cap per chapter; fallback to best version |
| 7 | Batch summary completeness | 10% | Per-chapter status table with word count, audit result, rounds |

#### shenbi-short-packaging (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | No spoilers in blurbs | 20% | Blurb hooks without revealing core twists |
| 4 | Evidence-backed selling points | 20% | Every selling point traceable to specific chapter content |
| 5 | Cover prompt usability | 15% | Prompts detailed enough for image generation models |
| 6 | Platform keyword alignment | 15% | Keywords match target platform tag taxonomy |
| 7 | Candidate quantity | 10% | 3–5 titles, 2–3 blurbs, 3–5 selling points |

### 4.9 Special Skills

#### shenbi-market-radar (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Data-backed claims | 20% | All recommendations reference leaderboard data |
| 4 | Saturation detection | 15% | 60% threshold correctly computed |
| 5 | Trend vs. imitation distinction | 15% | Advises differentiation, not copying |
| 6 | Decision checklist actionability | 15% | Every item immediately actionable with one-line rationale |
| 7 | Opening strategy relevance | 10% | Strategy tied to genre and platform data |
| 8 | Benchmark identification | 10% | Competitive works identified with rationale |

#### shenbi-sequel-writing (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Context reconstruction completeness | 25% | All 6 categories rebuilt from files, not assumed |
| 4 | Drift detection sensitivity | 20% | Behavioral, voice, style, setting drift all checked |
| 5 | Human intent confirmation | 20% | Author intent explicitly re-confirmed |
| 6 | Historical immutability | 15% | Published chapters never modified; only forward writing |

#### shenbi-writing-skills (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Skill completeness | 20% | Every created skill has DOT, iron laws, anti-rationalization, red flags |
| 4 | Trigger-only descriptions | 15% | Descriptions describe when to use, not what it does |
| 5 | Iron law absoluteness | 15% | Rules use absolute language, not suggestions |
| 6 | Pressure-test rigor | 15% | Skills tested against real rationalizations |
| 7 | Persuasion ethics | 10% | Uses Authority/Commitment/Scarcity/Social Proof/Unity; avoids Liking/Reciprocity |

## 5. T2: Phase-Level Rating Standards

Each phase test scored 0–100 with these dimensions:

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Handoff integrity | 20% | Every skill receives correctly structured input from previous skill; missing fields = deduction per occurrence |
| 2 | Cross-skill consistency | 20% | No contradictions between outputs of different skills in same phase (e.g., character-design doesn't violate worldbuilding rules) |
| 3 | State propagation accuracy | 15% | Truth files updated by skill N correctly read by skill N+1; stale reads = fail |
| 4 | Phase output completeness | 15% | All files expected at phase end are present and non-empty |
| 5 | Regression within phase | 15% | No skill's fix causes another skill in same phase to regress below its T1 score |
| 6 | Total phase execution time | 5% | No single skill hangs or loops; reasonable completion |
| 7 | Human gate compliance | 10% | Every hard-gate pause within phase is respected |

Kill switch: any skill's T1 score drops below 90 during T2 integration = phase = 0.

## 6. T3: Pipeline-Level Rating Standards

Full end-to-end pipeline scored 0–100:

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | End-to-end data integrity | 15% | Every truth file consistent from genesis through final chapter; no orphaned or contradictory state |
| 2 | Novel output coherence | 15% | Generated chapters form coherent story matching outline; reader can follow plot, characters, world |
| 3 | Cross-phase state consistency | 15% | Genesis world rules hold through drafting; character arcs visible in chapters; foreshadowing planted = resolved |
| 4 | Audit pass rate | 15% | All chapters pass all activated audit dimensions after revision |
| 5 | Revision non-regression | 10% | Chapter revision fixes audit issues without introducing new ones |
| 6 | Foreshadowing lifecycle completeness | 10% | Every planted hook tracked, advanced, and resolved or explicitly deferred; zero orphaned hooks |
| 7 | Import pipeline fidelity | 10% | When using report-example.txt, extracted characters/world/events traceable to source with zero fabrication |
| 8 | Full project file completeness | 5% | All expected project files exist: novel.json, genre-config.json, world/*, characters/*, truth/*, chapters/*, outline/* |
| 9 | Human readability | 5% | Chapters are readable fiction prose, not AI-structured reports; no meta-commentary, no bullet lists in prose |

Kill switch: any chapter fails sensitivity audit (platform-prohibited content) = pipeline = 0.

## 7. Skill Trace and Enhancement Feedback

### 7.1 Skill Trace (per test report)

Every test report includes a skill trace section:

```markdown
## Skill Trace: <skill-name> / <test-type>

### Agent Execution Log
- Skill loaded: yes/no
- Sections followed: [list which SKILL.md sections executed]
- Sections skipped: [list which sections missed or shortcut]
- Steps reordered: [any deviation from defined flow]
- Hard-gates triggered: [list any HARD-GATE blocks hit]
- Anti-rationalization table invoked: yes/no (if applicable)

### Output Quality
- Completeness: all expected output sections produced?
- Accuracy: findings correct (true positives vs false positives)?
- Actionability: recommendations specific enough to act on?

### Skill Enhancement Signals
- Confusion points: where agent misinterpreted instructions
- Missing coverage: scenarios the skill doesn't handle but should
- Over-specification: instructions that are redundant or contradictory
- Prompt adherence: did agent follow DOT flowcharts exactly?
- Edge cases: novel situations not covered by current spec
```

### 7.2 Enhancement Signals (aggregated per round)

```json
{
  "enhancement_signals": [
    {
      "skill": "shenbi-review-character",
      "signal_type": "confusion_point",
      "description": "Agent skipped BDI evaluation in 2/3 test types",
      "trace_source": "shenbi-review-character.bug-hunt.md",
      "suggested_fix": "Make BDI section a HARD-GATE"
    }
  ]
}
```

### 7.3 CHANGELOG Format

```markdown
## Round 001 (2026-06-11) — Claude
- T1: 42/59 skills at 100. Failures: shenbi-review-character (65), ...
- T2: not started (T1 incomplete)
- T3: not started
- Fixes applied: promoted BDI to HARD-GATE in shenbi-review-character
- Enhancement signals: 12 confusion points, 8 missing coverage items

## Round 002 (2026-06-12) — Claude
- T1: 55/59 skills at 100. Remaining: ...
```

## 8. Model Improvement Loop

### 8.1 Cycle

1. Model A runs full loop (T1 → T2 → T3), fixing skills until all tiers = 100.
2. Model B runs against Model A's improved skills. Catches issues Model A missed. Fixes those too. Loops until all 100.
3. Model C runs against A+B improved skills. Catches issues A+B missed. Loops until all 100.
4. Continue until no model can find remaining issues.

### 8.2 What Gets Fixed

- **SKILL.md improvements** (primary): instructions clarified, HARD-GATEs added, anti-rationalization tables expanded, edge cases documented.
- **Test case improvements**: better planted bugs, more representative clean scenarios, more realistic generative prompts.

### 8.3 Success Criteria

The framework is ready when:

- All 59 skills score 100 on T1 (bug-hunt, clean, generative)
- All phases score 100 on T2
- All pipeline variants (long-form, short-form, import) score 100 on T3
- Generated novel output is human-readable, professional-quality Chinese fiction
- Skills are robust enough that switching models doesn't drop scores below 90

### 8.4 Secondary Output: Model Comparison Data

Collected as a byproduct:

| Dimension | What it measures |
|-----------|-----------------|
| Score velocity | Rounds to reach 100 per tier |
| Dimension weakness pattern | Which dimensions consistently score lowest |
| Novel output quality | Blind human evaluation of generated chapters |
| Token efficiency | Total tokens consumed to reach 100 |
| Fix effectiveness | Delta per round |
| Skill enhancement count | Number of SKILL.md changes needed |

## 9. Directory Structure

```
tests/
├── tiers/
│   ├── t1-skill/
│   │   ├── _template/
│   │   ├── shenbi-review-character/
│   │   │   ├── bug-hunt/
│   │   │   │   ├── input/
│   │   │   │   ├── expected/
│   │   │   │   └── rubric.md
│   │   │   ├── clean/
│   │   │   │   ├── input/
│   │   │   │   ├── expected/
│   │   │   │   └── rubric.md
│   │   │   └── generative/
│   │   │       ├── input/
│   │   │       └── rubric.md
│   │   └── ... (59 skills)
│   ├── t2-phase/
│   │   ├── genesis/
│   │   │   ├── rubric.md
│   │   │   ├── input/
│   │   │   └── expected/
│   │   ├── architecture/
│   │   ├── planning/
│   │   ├── drafting/
│   │   ├── audit/
│   │   ├── management/
│   │   └── import/
│   └── t3-pipeline/
│       ├── long-form/
│       │   ├── rubric.md
│       │   └── input/
│       ├── short-form/
│       │   ├── rubric.md
│       │   └── input/
│       └── import-form/
│           ├── rubric.md
│           └── input/
├── rounds/
│   ├── CHANGELOG.md
│   └── round-NNN-YYYY-MM-DD/
│       ├── meta.json
│       ├── t1-reports/
│       ├── t2-reports/
│       ├── t3-reports/
│       ├── novel-output/
│       ├── skill-traces/
│       ├── enhancement-signals.json
│       └── summary.json
├── fixtures/
│   ├── outline-example/
│   └── report-example/
└── benchmarks/
    └── models/
        ├── claude/
        ├── gemini/
        └── ...
```

## 10. Round Execution Protocol

1. Create round directory with meta.json (model, date, skill versions, tier target).
2. Run tests for the target tier.
3. For each test: execute skill, capture output, score against rubric, generate skill trace.
4. Aggregate into summary.json with all scores, kill-switch status, enhancement signals.
5. Preserve novel-output/ for human review.
6. If any score < 100: identify fixes, apply to SKILL.md or test cases, increment round.
7. If all scores = 100: advance to next tier, or mark round as complete.
8. Update CHANGELOG.md with round results and fixes applied.
