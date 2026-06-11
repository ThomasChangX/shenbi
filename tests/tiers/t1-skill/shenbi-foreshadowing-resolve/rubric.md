# T1 Rubric: shenbi-foreshadowing-resolve

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Chase Power management | 20% | CP above 200 triggers mandatory immediate resolution |
| 4 | Resolution quality | 15% | Core hooks achieve ≥PARTIAL_PAYOFF, never FLAT_PAYOFF |
| 5 | Prioritization | 15% | High-CP hooks resolved first |
| 6 | Volume completeness | 15% | Every active hook inventoried at volume end |
| 7 | Smokescreen handling | 10% | Smoke screens include truth revelation when resolved |
| 8 | Human gate | 10% | ABANDON operations require explicit human approval |

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
