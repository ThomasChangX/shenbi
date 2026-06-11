# T1 Rubric: shenbi-pacing-design

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Four-beat completeness | 20% | Every cycle includes buildup/escalation/explosion/aftermath |
| 4 | Three-line balance | 15% | QUEST/FIRE/CONSTELLATION ratios all present |
| 5 | Monotony prevention | 15% | No more than 3 consecutive chapters of same type |
| 6 | Genre alignment | 15% | Pacing matches genre expectations |
| 7 | Actionability | 10% | Principles detectable and correctable by downstream skills |
| 8 | Scene type catalog | 10% | 6-8 scene types minimum defined with explicit detection criteria |

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

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered → final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
