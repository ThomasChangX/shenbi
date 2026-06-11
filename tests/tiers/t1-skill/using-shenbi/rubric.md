# T1 Rubric: using-shenbi

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Kill Switches by Test Type

### Bug-Hunt Kill Switches
- Missed planted defect (wrong route) → total score = 0
- HARD-GATE bypass → total score = 0

### Clean Kill Switches
- Any hallucinated defect (false positive) → total score = 0
- HARD-GATE bypass → total score = 0

### Generative Kill Switches
- 3+ wrong routes in a single round → total score = 0
- HARD-GATE bypass → total score = 0

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Trigger accuracy | 25% | Routes to correct skill per trigger map; wrong route = 0 per instance |
| 4 | 1% rule compliance | 20% | For borderline requests, checks all applicable skills before responding |
| 5 | HARD-GATE enforcement | 20% | Rejects proceeding without prerequisite |
| 6 | Full skill list coverage | 10% | Can route to all 59 skills |
| 7 | Red flag detection | 10% | Detects and flags red-flag conditions |

## Scoring Rules
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
