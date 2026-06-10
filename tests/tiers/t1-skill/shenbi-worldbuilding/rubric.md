# T1 Rubric: shenbi-worldbuilding

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Internal consistency | 15% | Zero contradictions within world rules; hard rules are mutually compatible |
| 4 | Prose quality | 10% | story_bible.md is narrative prose paragraphs; bullet-point lists = 0 |
| 5 | Deduplication | 10% | Each fact appears in exactly one canonical file |
| 6 | Hook potential | 15% | "Undercurrent" section seeds ≥3 future conflict sources |
| 7 | Scalability | 15% | Structure supports 200+ chapters without retcon |
| 8 | Rule enforceability | 10% | Hard rules are concrete and testable; "magic is mysterious" = fail |
| 9 | Template completeness | 10% | All required output files present with all required fields |

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
| Prose/narrative quality (dim 4) | No | No | Yes |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered → final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
