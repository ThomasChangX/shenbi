# T1 Rubric: shenbi-foreshadowing-track

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Complete evaluation | 20% | Every active hook assessed, none skipped |
| 4 | Textual evidence | 20% | State transitions require specific text evidence |
| 5 | Core hook protection | 15% | core_hook: true never ABANDONED |
| 6 | Expiry detection | 15% | Hooks exceeding max_distance correctly flagged |
| 7 | Density budget reporting | 15% | Operations vs. budget clearly reported; over-budget items explicitly listed |

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
