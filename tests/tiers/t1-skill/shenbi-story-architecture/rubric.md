# T1 Rubric: shenbi-story-architecture

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Three-layer conflict coherence | 20% | Surface, personal, deep conflicts are mutually reinforcing |
| 4 | Dual-line integrity | 15% | Front-stage AND back-stage storylines both defined |
| 5 | OKR executability | 15% | KRs are measurable and map to chapter ranges; "protagonist grows" = fail |
| 6 | Prose quality | 15% | story_frame.md is narrative paragraphs, not bullet lists |
| 7 | Foreshadowing seeding | 10% | Story frame seeds ≥3 foreshadowing lines |
| 8 | Volume map scalability | 10% | Volume structure supports full novel length |

## Kill Switches by Test Type

### Bug-Hunt Kill Switches
- Missed planted defect (false negative) → total score = 0
- HARD-GATE violation → total score = 0

### Clean Kill Switches
- Any hallucinated defect (false positive) → total score = 0
- HARD-GATE violation → total score = 0

### Generative Kill Switches
- HARD-GATE violation → total score = 0

## Dimension Applicability by Test Type

| Dimension scope | Bug-hunt | Clean | Generative |
|----------------|----------|-------|------------|
| Universal (1-2) | Yes | Yes | Yes |
| All bespoke | Yes (detection quality) | Yes (report quality) | Yes (output quality) |
| Prose/narrative quality (dim 6) | No | No | Yes |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered → final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
