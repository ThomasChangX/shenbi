# T1 Rubric: shenbi-import-analysis

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Traceability | 20% | Every extracted fact has source chapter + paragraph number reference |
| 4 | Zero guessing | 15% | Non-locatable items marked "unconfirmed"; no fabricated facts |
| 5 | Pipeline correctness | 15% | Data dependencies between 8 passes respected |
| 6 | Unconfirmed item completeness | 10% | Exhaustive list; every item not derivable from text is on the list |
| 7 | Pass completeness | 10% | All 8 passes executed; each pass output file non-empty |
| 8 | Cross-pass consistency | 10% | No contradictions between pass outputs |
| 9 | Statistics accuracy | 5% | Chapter/word/character counts match source file |

## Kill Switches by Test Type

### Bug-Hunt Kill Switches
- Content not groundable to source text → total score = 0
- Missed planted defect (false negative) -> total score = 0
- HARD-GATE violation -> total score = 0

### Clean Kill Switches
- Content not groundable to source text → total score = 0
- Any hallucinated defect (false positive) -> total score = 0
- HARD-GATE violation -> total score = 0

### Generative Kill Switches
- HARD-GATE violation -> total score = 0

## Dimension Applicability by Test Type

| Dimension scope | Bug-hunt | Clean | Generative |
|----------------|----------|-------|------------|
| Universal (1-2) | Yes | Yes | Yes |
| All bespoke | Yes (detection quality) | Yes (report quality) | Yes (output quality) |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered -> final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
