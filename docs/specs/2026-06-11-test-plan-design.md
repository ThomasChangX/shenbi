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

**Test-type to dimension mapping:**

| Dimension scope | Bug-hunt | Clean | Generative |
|----------------|----------|-------|------------|
| Universal (instruction adherence, output completeness) | Applies | Applies | Applies |
| Kill switches (false negative for bug-hunt, false positive for clean) | Bug-hunt kill switch only | Clean kill switch only | No kill switch |
| Skill-specific output quality dimensions | Applies to detection/report quality | Applies to report quality | Applies to output quality |
| Prose/narrative quality dimensions (e.g., "Prose quality", "Show-don't-tell") | Does not apply (input is pre-made) | Does not apply (input is pre-made) | Applies |

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
| Foundation | foundation-review → chapter-revision → truth-sync → style-learning | Genesis output |

**Skills not in any T2 phase** (T1-only, enter T3 directly): sequel-writing, market-radar, writing-skills, shenbi-drift-guidance (also in Management), foreshadowing-resolve, shenbi-chapter-pattern (also in Management). These skills are tested at T1 level only; their integration is validated at the pipeline level in T3.

### 2.4 Pipeline Variants (T3)

- **Long-form**: `outline-example.md` → genesis → architecture → planning → drafting (5+ chapters) → audit → revision → state-settling → management. Produces a mini-novel project. After 5 chapters, runs a state-accumulation stress check (see Section 6.1).
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

All bespoke dimension weights sum to exactly 85% per skill. Combined with 15% universal = 100%.

### 4.0 Dispatcher Skill

#### using-shenbi (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Trigger accuracy | 25% | Given test phrases from skill-triggering tests, routes to the correct skill. Wrong route = 0 per instance; 3+ wrong routes in a round = kill switch |
| 4 | 1% rule compliance | 20% | For borderline requests that could match multiple skills, checks all applicable skills before responding. Skipping the check = 0 per instance |
| 5 | HARD-GATE enforcement | 20% | Rejects attempts to proceed without prerequisite (e.g., drafting without a plan, auditing without truth files). Allowing bypass = kill switch |
| 6 | Full skill list coverage | 10% | Can route to all 59 skills; no skill is unreachable from the trigger map |
| 7 | Red flag detection | 10% | Detects and flags red-flag conditions from using-shenbi's Red Flags table |

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
| 6 | Genre alignment | 15% | Pacing matches genre expectations (xianxia = longer buildup, urban = faster pace) |
| 7 | Actionability | 10% | Principles detectable and correctable by downstream skills |
| 8 | Scene type catalog | 10% | 6–8 scene types minimum defined with explicit detection criteria |

#### shenbi-plot-thread-weaver (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | No blank chapters | 20% | Every chapter advances ≥1 thread |
| 4 | Long-line contact discipline | 15% | A-lines don't exceed max_gap (default 2 chapters for P0) |
| 5 | Short-line closure | 15% | C-lines resolve within their planned span |
| 6 | Climax window coordination | 15% | Subplot climaxes complement volume climaxes |
| 7 | Crossing point purpose | 10% | Thread crossings serve dramatic effect |
| 8 | Priority classification accuracy | 10% | P0 = novel-critical, P1 = volume-critical, P2 = arc-supporting, P3 = flavor; classification per definitions in thread_map.md |

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
| 9 | Prohibition specificity | 5% | "Do not do" list names specific avoid-patterns, not generic advice |

#### shenbi-foreshadowing-plant (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Budget enforcement | 20% | ≤8 operations per chapter; violation = 0 |
| 4 | Metadata completeness | 15% | All required fields present; depends_on never omitted |
| 5 | Smokescreen accountability | 15% | Every SMOKESCREEN has documented exit strategy |
| 6 | Existing hook awareness | 15% | Reads pending_hooks.md first; no duplication/contradiction |
| 7 | Strategic placement | 10% | Planting guidance references scene type appropriateness |
| 8 | Type/dimension classification | 10% | Hook type (GENUINE/SMOKESCREEN/SIDE_SHADOW) and dimension (THEMATIC/CHARACTER/SYMBOLIC/STRUCTURAL) assigned per taxonomy in foreshadowing-plant SKILL.md |

#### shenbi-foreshadowing-track (5 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Complete evaluation | 20% | Every active hook assessed, none skipped |
| 4 | Textual evidence | 20% | State transitions require specific text evidence |
| 5 | Core hook protection | 15% | core_hook: true never ABANDONED |
| 6 | Expiry detection | 15% | Hooks exceeding max_distance correctly flagged |
| 7 | Density budget reporting | 15% | Operations vs. budget clearly reported; over-budget items explicitly listed |

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
| 4 | Accuracy | 15% | Extracted summaries match source truth files word-for-word for key facts; no paraphrase drift |
| 5 | Hook urgency calculation | 15% | Computes (current_chapter - last_reinforced) / max_distance; matches test harness computation |
| 6 | Ending diversity check | 15% | Flags if recent 3 chapters share same ending pattern (type classification per chapter-pattern skill) |
| 7 | Recency | 10% | Only summaries from last 3 chapters and hooks with urgency > 0.5 included |
| 8 | Hook debt brief quality | 10% | Debt brief lists every active hook with status, silence chapters, and action suggestion |

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
| 8 | Report completeness | 5% | Polishing report lists all changes with before/after |
| 9 | Structural flag quality | 5% | [polisher-note] annotations are specific and actionable |

#### shenbi-anti-detect (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Content preservation | 15% | No changes to plot, characters, or foreshadowing |
| 4 | Targeted intervention | 15% | Only rewrites at detected marker points; no wholesale rewriting |
| 5 | Audit pass rate | 15% | Anti-AI audit passes after rewriting |
| 6 | Style preservation | 15% | Does not lose authorial voice; zero new AI-typical patterns introduced |
| 7 | Bounded iteration | 15% | After 3 failed passes, reverts to best version |
| 8 | Before/after audit comparison | 10% | Clear before/after error and warning counts with per-marker-type breakdown |

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

Shared dimensions (65%) + unique dimension (20%) = 85%. Combined with 15% universal = 100%.

#### Shared audit dimensions (65%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | True positive rate | 20% | 100% of planted defects found; miss = 0 |
| 4 | False positive rate | 15% | Zero hallucinated findings |
| 5 | Evidence grounding | 10% | Every finding cites specific text (chapter + paragraph) + specific source file and line |
| 6 | Severity accuracy | 10% | Error vs warning classification matches expected severity per finding |
| 7 | Fix actionability | 10% | Each finding has a concrete fix (specific text to change, not vague advice) |

#### Per-audit-skill unique dimension (20%)

| Skill | Unique Dimension | Standard |
|-------|-----------------|----------|
| shenbi-review-character | BDI coverage | All speaking/acting characters assessed; protagonist + every character with dialogue lines mandatory |
| shenbi-review-continuity | Timeline extraction precision | Time markers extracted and cross-compared across ≥2 chapters; every explicit time reference accounted for |
| shenbi-review-dialogue | Voice fingerprint matching | Per-speaker: sentence length, vocabulary range, sentence pattern deviation quantified against voice_profile baseline |
| shenbi-review-pacing | Chapter type classification accuracy | QUEST/FIRE/CONSTELLATION assigned per definitions in rhythm_principles.md for last 5 chapters |
| shenbi-review-anti-ai | Pattern coverage | All 10 deterministic checks (per SKILL.md checklist) executed; zero skipped; each check has PASS/ERROR result |
| shenbi-review-foreshadowing | Lifecycle tracking | Every hook state transition has text evidence citing chapter and specific prose passage |
| shenbi-review-world-rules | Numerical cross-reference | Every numerical claim (ages/dates/distances/counts) verified against truth files with file+field reference |
| shenbi-review-sensitivity | Platform rule application | Platform rules from novel.json target_platform applied; every prohibited word from fatigue list checked |
| shenbi-review-memo-compliance | Section-by-section verification | All 8 memo sections checked independently; each section gets fulfill/partial/missing verdict |
| shenbi-review-motivation | Causal chain reconstruction | Every major action has complete chain: trigger → judgment → action → consequence; missing links flagged |
| shenbi-review-pov | Information leakage detection | Every piece of character knowledge verified against POV character's presence and acquisition channel |
| shenbi-review-reader-pull | Hook strength assessment | Opening hook type classified; chapter-end suspense type classified; mid-chapter traction points counted per 800–1200 word interval |
| shenbi-review-highpoint | Buildup-payoff comparison | Every climax segment has buildup level and payoff level rated on 1–5 scale with text evidence; deflation = payoff < buildup |
| shenbi-review-texture | Laundry-list detection | Sequential markers (然后/接着/之后/随后) counted per paragraph; paragraphs with ≥3 sequential markers and zero conflict flagged |
| shenbi-review-long-span | N-gram extraction accuracy | 6-char n-gram repetition rate computed per formula in SKILL.md against last 5 chapters; threshold cross-checked with test harness |
| shenbi-review-era | Anachronism detection | Every artifact/vocabulary/institution verified against the declared time period; unverified items flagged |
| shenbi-review-fanfic | Mode strictness application | Canon/AU/OOC/CP mode determines severity per SKILL.md severity table; undeclared deviations always error |
| shenbi-review-spinoff | Timeline-aware leakage | Every piece of information in spinoff verified against parent timeline; info revealed in parent chapter N is forbidden in spinoff chapter < N |

### 4.5 Revision Skills

#### shenbi-chapter-revision (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Non-regression | 20% | Blocking/critical/AI-trace counts do not increase |
| 4 | Scope discipline | 15% | Only fixes audit findings; no unrelated changes |
| 5 | Length constraint | 15% | Change within ±15% of original length |
| 6 | Fallback correctness | 10% | Best-version selected by lowest weighted issue count; ties broken by most recent version |
| 7 | Fix accuracy | 15% | Targeted fix resolves the specific issue found |
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

#### shenbi-snapshot-manage (5 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Snapshot completeness | 25% | All 11 truth files included; verify by file count and size > 0 |
| 4 | Immutability | 20% | Post-creation checksum matches; no byte difference after any operation |
| 5 | Human-gate enforcement | 20% | Rollback requires explicit human confirmation (no auto-proceed) |
| 6 | Post-rollback integrity | 15% | Chapters after rollback point flagged as UNVERIFIED in metadata |
| 7 | Operation correctness | 5% | create/view/rollback/list all produce output matching spec format |

#### shenbi-volume-consolidation (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Conciseness | 20% | Volume summary ≤500 words (word count verified) |
| 4 | Unresolved hook completeness | 20% | Every hook in pending_hooks.md with status ≠ RESOLVED is listed |
| 5 | Retrievability | 15% | Archived per-chapter summaries accessible at expected paths |
| 6 | Narrative arc accuracy | 15% | Every major event in volume summary traceable to specific chapter |
| 7 | Key event selection | 15% | Only events affecting character arcs, plot threads, or world state included |

#### shenbi-foundation-review (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Scoring rigor | 20% | Every deduction has a concrete improvement suggestion (which file, which paragraph, what to change) |
| 4 | Threshold enforcement | 20% | 80-point minimum and core-conflict veto (< 18/30 = fail) unconditional |
| 5 | Evidence-based evaluation | 15% | Only existing content scored; no assumed content |
| 6 | Actionability | 15% | Fix suggestions point to exact files/paragraphs |
| 7 | Dimension balance | 15% | All 5 dimensions scored independently; dimension scores sum to total |

#### shenbi-drift-guidance (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Correct classification | 20% | Errors never conducted forward; only warnings pass |
| 4 | Actionability of guidance | 20% | Each item says "what next chapter should do" (specific action, not just "improve X") |
| 5 | Cap enforcement | 15% | ≤5 drift items (exact count verified) |
| 6 | Target specificity | 15% | Every item has a targeted_chapter field with chapter number |
| 7 | Source traceability | 15% | Each drift item traceable to specific audit finding (audit name + finding ID) |

#### shenbi-intent-management (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Human sovereignty | 25% | AI never makes creative decisions; only organizes human input (verify output matches human input verbatim for factual content) |
| 4 | Drift integration completeness | 20% | All drift guidance items merged into current focus (cross-reference drift file with focus file) |
| 5 | Priority clarity | 20% | P0/P1/P2 assigned per definitions: P0 = blocks writing, P1 = quality risk, P2 = nice-to-have |
| 6 | Timeliness | 10% | current_focus.md timestamp is after most recent audit/drift |
| 7 | Format compliance | 10% | Both truth/author_intent.md and truth/current_focus.md follow YAML frontmatter schema from SKILL.md |

#### shenbi-chapter-pattern (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Classification accuracy | 25% | Every chapter assigned to ≥1 of 13 patterns per definitions in SKILL.md; test includes known-type chapters |
| 4 | Threshold strictness | 20% | Hard limits on consecutive patterns enforced (count verified) |
| 5 | Entropy calculation correctness | 15% | Shannon entropy matches independent test harness computation (H = -Σ p_i log2(p_i) over pattern distribution) |
| 6 | Actionability of recommendations | 15% | Next-chapter suggestion names specific primary/secondary patterns and patterns to avoid |
| 7 | Distribution coverage | 10% | Minimum distinct patterns in rolling window verified against SKILL.md threshold |

### 4.7 Import Skills

#### shenbi-import-analysis (7 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Traceability | 20% | Every extracted fact has source chapter + paragraph number reference |
| 4 | Zero guessing | 15% | Non-locatable items marked "unconfirmed" (count verified); no fabricated facts |
| 5 | Pipeline correctness | 15% | Data dependencies between 8 passes respected (pass N reads only outputs of pass < N) |
| 6 | Unconfirmed item completeness | 10% | Exhaustive list; every item not derivable from text is on the list |
| 7 | Pass completeness | 10% | All 8 passes executed; each pass output file non-empty |
| 8 | Cross-pass consistency | 10% | No contradictions between pass outputs (characters in pass 2 exist in pass 1) |
| 9 | Statistics accuracy | 5% | Chapter/word/character counts match source file (byte-verified) |

#### shenbi-character-extraction (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Evidence grounding | 25% | Every personality tag, speech pattern, and relationship has ≥1 quoted passage with chapter.paragraph reference |
| 4 | Voice fingerprint accuracy | 20% | Statistical extraction from actual dialogue (sentence length mean/std verified against source) |
| 5 | Arc evidence | 15% | Start and turning points backed by chapter-specific behavioral evidence with text quotes |
| 6 | No fabrication | 15% | Non-derivable items marked "unconfirmed"; count verified against source coverage |
| 7 | Relationship network completeness | 10% | All named character pairs with interaction scenes have relationship entries |

#### shenbi-world-extraction (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Rule evidence threshold | 20% | Each rule has ≥2 independent textual evidence citations with chapter.paragraph references |
| 4 | Violation-based inference | 15% | Rules inferred from failures and avoidances, not just successes |
| 5 | Power system completeness | 15% | Level names, advancement conditions, ability boundaries, and costs all present |
| 6 | Consistency | 10% | Extracted rules don't contradict story bible narrative |
| 7 | Location coverage | 10% | Top locations extracted with atmosphere, function, and first appearance |
| 8 | Prose format | 15% | story_bible.md is 4-paragraph narrative prose; rules.md is structured with evidence |

#### shenbi-canon-import (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Mode fidelity | 25% | Preservation/deviation rules strictly followed; zero silent mixing of modes |
| 4 | Evidence traceability | 20% | Every canon entry cites original work (chapter/episode/paragraph) |
| 5 | Deviation transparency | 20% | All deviations from original explicitly declared in deviation list |
| 6 | 5-section completeness | 20% | World, character, event, relationship, timeline sections all present and non-empty |

### 4.8 Short Story Layer

#### shenbi-short-outline (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | 3-step enforcement | 20% | Generate → review → revise; no skipped steps; each step produces output |
| 4 | Chapter task completeness | 15% | Every chapter has ≥1 task advancing ≥1 thread |
| 5 | Act proportioning | 15% | 20/60/20 split verified by chapter count per act |
| 6 | No dead chapters | 15% | Zero chapters with task = "transition" or no thread advancement |
| 7 | Thread limit compliance | 10% | ≤1 subplot + ≤1 emotional arc (count verified) |
| 8 | Turning point quality | 10% | Each turning point is a genuine reversal (situation A → situation B with evidence) |

#### shenbi-short-drafting (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Sequential generation | 20% | Chapters generated strictly in order (verify chapter N truth files exist before N+1 starts) |
| 4 | Per-chapter audit rigor | 20% | Every chapter passes all audit checks before acceptance; failed chapters have revision log |
| 5 | Cross-chapter consistency | 20% | Position, timeline, information, relationships, style continuous across all chapters |
| 6 | Revision discipline | 15% | 3-round cap per chapter; fallback to best version after 3 rounds |
| 7 | Batch summary completeness | 10% | Per-chapter status table with word count, audit result, revision rounds, pass/fail |

#### shenbi-short-packaging (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | No spoilers in blurbs | 20% | Blurb contains zero plot points from act 3 (verified against outline) |
| 4 | Evidence-backed selling points | 15% | Every selling point cites specific chapter + paragraph |
| 5 | Cover prompt usability | 15% | Prompts include subject, scene, composition, color palette, style keywords |
| 6 | Platform keyword alignment | 15% | Keywords match target platform tag taxonomy (verified against platform-specific lists) |
| 7 | Candidate quantity | 10% | 3–5 titles, 2–3 blurbs, 3–5 selling points (count verified) |
| 8 | Title distinctness | 10% | Each title candidate is semantically distinct (no two titles share the same imagery/metaphor) |

### 4.9 Special Skills

#### shenbi-market-radar (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Data-backed claims | 20% | Every recommendation references specific leaderboard rank or trend data point |
| 4 | Saturation detection | 15% | Element occurrence > 60% in top-20 titles flagged as saturated (computation verified against raw data) |
| 5 | Trend vs. imitation distinction | 15% | Each trend signal includes a differentiation suggestion, not just "use this element" |
| 6 | Decision checklist actionability | 15% | Every item is a single action with one-line rationale (follow/avoid/research + reason) |
| 7 | Opening strategy relevance | 10% | Strategy tied to specific genre + platform data |
| 8 | Benchmark identification | 10% | ≥2 competitive works named with rationale (why they are comparable) |

#### shenbi-sequel-writing (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Context reconstruction completeness | 25% | All 6 categories rebuilt from files (world state, character relations, emotional arcs, active threads, style fingerprint, current focus); each category has explicit output |
| 4 | Drift detection sensitivity | 20% | Behavioral, voice, style, and setting drift all checked; each drift type produces a finding |
| 5 | Human intent confirmation | 20% | Author intent explicitly re-confirmed before writing starts (human interaction logged) |
| 6 | Historical immutability | 10% | Published chapters never modified; verify checksums match snapshots |
| 7 | Pre-writing report completeness | 10% | All sections of pre-writing report present (breakpoint, state, style, drift) |

#### shenbi-writing-skills (6 dimensions)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Skill completeness | 20% | Every created skill has DOT flowchart, iron laws, anti-rationalization table, red flag checklist (count verified) |
| 4 | Trigger-only descriptions | 15% | Description describes when to use, never what it does; violations flagged per CLAUDE.md spec |
| 5 | Iron law absoluteness | 15% | Rules use MUST/NEVER/ALWAYS; "should"/"prefer"/"recommend" = fail per instance |
| 6 | Pressure-test rigor | 15% | Skills tested against ≥3 real rationalization scenarios (not hypothetical) |
| 7 | Persuasion ethics | 10% | Uses Authority/Commitment/Scarcity/Social Proof/Unity only; Liking/Reciprocity absent |
| 8 | Output format | 10% | SKILL.md follows frontmatter + markdown structure from CLAUDE.md conventions |

## 5. T2: Phase-Level Rating Standards

Each phase test scored 0–100. Phase-type-specific dimensions replace the generic ones where the generic dimension is semantically inapplicable.

### 5.1 Sequential Phase Dimensions (Genesis, Architecture, Planning, Drafting, Import, Management, Foundation)

For phases where skills chain outputs to each other:

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Handoff integrity | 20% | Every skill receives correctly structured input from previous skill; missing fields = -5% per field |
| 2 | Cross-skill consistency | 20% | Zero contradictions between outputs of different skills in same phase (e.g., character-design doesn't violate worldbuilding rules) |
| 3 | State propagation accuracy | 15% | Truth files updated by skill N correctly read by skill N+1; stale reads = -10% per instance |
| 4 | Phase output completeness | 15% | All files expected at phase end present and non-empty (file count verified) |
| 5 | Regression within phase | 15% | No skill's output during T2 run scores below its T1 score on the same input |
| 6 | Execution time | 5% | No single skill exceeds 10 minutes; total phase under 60 minutes (wall clock) |
| 7 | Human gate compliance | 10% | Every hard-gate pause within phase is respected; zero auto-proceeds past hard gates |

Kill switch: any skill's T1 score drops below 90 during T2 integration = phase = 0.

### 5.2 Parallel Phase Dimensions (Audit)

For the audit phase where 18 skills run independently on the same input:

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Cross-audit consistency | 25% | Findings from different audit skills don't contradict each other (e.g., character audit says "in character" but dialogue audit says "voice mismatch") |
| 2 | Full coverage | 20% | All 18 audit skills produce reports; none skipped |
| 3 | Finding deduplication | 15% | Same issue not reported at different severities by different audits without justification |
| 4 | Severity alignment | 15% | Findings about the same passage at different severity levels are cross-referenced and explained |
| 5 | Phase output completeness | 15% | All 18 audit reports present and non-empty |
| 6 | Execution time | 10% | No single audit skill exceeds 10 minutes; total audit phase under 30 minutes |

### 5.3 Short Story Phase Dimensions

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Handoff integrity | 20% | Each skill receives complete output from previous skill (outline → drafting → packaging) |
| 2 | Cross-skill consistency | 20% | Drafting matches outline; packaging matches story content |
| 3 | Phase output completeness | 15% | Outline, all chapters, and packaging materials all present |
| 4 | Regression within phase | 15% | Skills maintain their T1 scores during integration |
| 5 | Story coherence | 15% | The final short story is a coherent narrative (no plot holes, character consistency) |
| 6 | Execution time | 5% | No single skill exceeds 10 minutes; total phase under 45 minutes |
| 7 | Human gate compliance | 10% | Every hard-gate pause respected |

## 6. T3: Pipeline-Level Rating Standards

Full end-to-end pipeline scored 0–100. Dimensions apply per pipeline variant; variant-specific replacements noted.

### 6.1 Universal Pipeline Dimensions

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | End-to-end data integrity | 15% | Every truth file consistent from genesis through final chapter; zero orphaned or contradictory state entries |
| 2 | Novel output coherence | 15% | All character actions groundable to established motivations; no unexplained plot jumps; chapter transitions reference prior events; all planted foreshadowing traceable in text |
| 3 | Cross-phase state consistency | 15% | Genesis world rules hold through drafting; character arcs from character-design visible in chapters; foreshadowing planted = tracked and resolved or deferred |
| 4 | Audit pass rate | 15% | All chapters pass all activated audit dimensions after revision |
| 5 | Revision non-regression | 10% | Chapter revision fixes audit issues without introducing new ones; pre/post audit scores only improve |
| 6 | Foreshadowing lifecycle completeness | 10% | Every planted hook tracked, advanced, and resolved or explicitly deferred; zero orphaned hooks |
| 7 | Full project file completeness | 5% | All expected files exist: novel.json, genre-config.json, world/*, characters/*, truth/*, chapters/*, outline/* |
| 8 | Literary quality | 10% | Final chapters: zero AI-typical phrasing (per anti-ai audit), chapter openings create pull (per reader-pull), emotional beats land (show-don't-tell), dialogue reads naturally (per dialogue audit) |
| 9 | State accumulation integrity | 5% | After 5 chapters: truth files have consistent entries for all chapters, no stale state, character_matrix reflects all relationship changes, pending_hooks has no expired unresolved hooks |

Kill switch: any chapter fails sensitivity audit (platform-prohibited content) = pipeline = 0.

### 6.2 Variant-Specific Dimension Replacements

**Long-form** (uses outline-example.md): all 9 dimensions apply.

**Short-form** (uses outline-example.md):
- Replace dimension 5 (Revision non-regression) with **Pacing tightness** (10%): No chapter exceeds pacing-design word count range by >30%; act proportions match short-outline spec
- Replace dimension 6 (Foreshadowing lifecycle) with **Story completeness** (10%): Story has beginning, climax, and resolution; all threads opened in act 1 are closed by act 3
- Replace dimension 9 (State accumulation) with **Packaging fidelity** (5%): Title, blurb, and selling points accurately represent the generated story content

**Import-form** (uses report-example.txt):
- Replace dimension 2 (Novel output coherence) with **Extraction fidelity** (15%): All extracted characters/world/events traceable to source with zero fabrication; unconfirmed items list is exhaustive
- Replace dimension 4 (Audit pass rate) with **Import completeness** (15%): All 4 import skills produce output; character files, world files, canon files, and analysis all present
- Replace dimension 5 (Revision non-regression) with **Evidence coverage** (10%): ≥80% of extracted facts have chapter.paragraph evidence; <20% marked "unconfirmed"
- Replace dimension 8 (Literary quality) with **Import report quality** (10%): Analysis summary has accurate statistics; downstream task checklist is complete and actionable
- Replace dimension 9 (State accumulation) with **Cross-extraction consistency** (5%): Characters extracted in character-extraction match those identified in import-analysis; world rules in world-extraction match story bible

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
- T1 band breakdown: 42 PASS (90+), 10 CONDITIONAL (60-74), 7 FAIL (0-59)
- T2: not started (T1 incomplete)
- T3: not started
- Fixes applied: promoted BDI to HARD-GATE in shenbi-review-character
- Enhancement signals: 12 confusion points, 8 missing coverage items

## Round 002 (2026-06-12) — Claude
- T1: 55/59 skills at 100.
- T1 band breakdown: 55 PASS (90+), 3 CONDITIONAL (60-74), 1 FAIL (0-59)
- ...
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

### 8.3 Success Criteria and Convergence

The framework is ready when:

- All 59 skills score 100 on T1 (bug-hunt, clean, generative)
- All phases score 100 on T2
- All pipeline variants (long-form, short-form, import) score 100 on T3
- Generated novel output is human-readable, professional-quality Chinese fiction
- Skills are robust enough that switching models doesn't drop scores below 90

**Convergence failure handling:**

If a skill fails to reach 100 after 5 consecutive rounds with no score improvement:

1. **Escalate to design review.** The dimension standard may need refinement rather than the skill needing improvement.
2. **Options:**
   - (a) Refine the dimension standard to be more precise (add measurable threshold)
   - (b) Add a HARD-GATE to the skill for the failing dimension
   - (c) Mark dimension as "acceptable at 90+" with documented rationale in the spec
3. **Decision recorded** in CHANGELOG with explicit justification.
4. **Hard limit:** If a skill cannot reach 90 after 10 rounds, mark as "design-limited" and file a skill redesign task.

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
│   │   ├── using-shenbi/
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
│   │   └── ... (59 skills total including using-shenbi)
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
│   │   ├── import/
│   │   ├── foundation/
│   │   └── short-story/
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
│   ├── outline-example.md         # copied from project root
│   └── report-example.txt         # copied from project root (UTF-8 converted)
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
8. Update CHANGELOG.md with round results, band breakdown, and fixes applied.
