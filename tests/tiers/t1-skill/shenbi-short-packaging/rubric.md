# T1 Rubric: shenbi-short-packaging

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | No spoilers in blurbs | 20% | Blurb contains zero plot points from act 3 |
| 4 | Evidence-backed selling points | 15% | Every selling point cites specific chapter + paragraph |
| 5 | Cover prompt usability | 15% | Prompts include subject, scene, composition, color palette, style keywords |
| 6 | Platform keyword alignment | 15% | Keywords match target platform tag taxonomy |
| 7 | Candidate quantity | 10% | 3-5 titles, 2-3 blurbs, 3-5 selling points (count verified) |
| 8 | Title distinctness | 10% | Each title candidate is semantically distinct |

## Kill Switches by Test Type

### Bug-Hunt Kill Switches
- Missed planted defect (false negative) -> total score = 0
- HARD-GATE violation -> total score = 0

### Clean Kill Switches
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
