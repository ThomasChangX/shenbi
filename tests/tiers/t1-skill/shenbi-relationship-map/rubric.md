# T1 Rubric: shenbi-relationship-map

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Interest-grounded relationships | 20% | Every relationship traceable to interest/emotion/bloodline/mentorship |
| 4 | Information boundary rigor | 15% | Who knows what about whom explicitly recorded |
| 5 | Evolution planning | 15% | Each relationship defines start, turning points, expected end state |
| 6 | Deduplication | 10% | Relationship data in relationships.md only, not duplicated in character cards |
| 7 | Asymmetry tracking | 15% | Information asymmetries tracked as dramatic tension sources |
| 8 | Character reference integrity | 10% | All referenced characters exist in character files |

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
