# T1 Rubric: shenbi-canon-import

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Mode fidelity | 25% | Preservation/deviation rules strictly followed; zero silent mixing of modes |
| 4 | Evidence traceability | 20% | Every canon entry cites original work (chapter/episode/paragraph) |
| 5 | Deviation transparency | 20% | All deviations from original explicitly declared in deviation list |
| 6 | 5-section completeness | 20% | World, character, event, relationship, timeline sections all present and non-empty |

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
