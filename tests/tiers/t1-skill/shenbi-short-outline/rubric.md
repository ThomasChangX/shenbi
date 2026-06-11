# T1 Rubric: shenbi-short-outline

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | 3-step enforcement | 20% | Generate -> review -> revise; no skipped steps |
| 4 | Chapter task completeness | 15% | Every chapter has >=1 task advancing >=1 thread |
| 5 | Act proportioning | 15% | 20/60/20 split verified by chapter count per act |
| 6 | No dead chapters | 15% | Zero chapters with task = "transition" or no thread advancement |
| 7 | Thread limit compliance | 10% | <=1 subplot + <=1 emotional arc |
| 8 | Turning point quality | 10% | Each turning point is a genuine reversal |

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
