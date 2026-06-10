# T1 Rubric: shenbi-review-highpoint

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Shared Audit Dimensions (65%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | True positive rate | 20% | 100% of planted defects found; miss = 0 |
| 4 | False positive rate | 15% | Zero hallucinated findings |
| 5 | Evidence grounding | 10% | Every finding cites specific text (chapter + paragraph) + specific source file and line |
| 6 | Severity accuracy | 10% | Error vs warning classification matches expected severity per finding |
| 7 | Fix actionability | 10% | Each finding has a concrete fix (specific text to change, not vague advice) |

## Unique Dimension (20%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 8 | Buildup-payoff comparison | 20% | Every climax segment has buildup level and payoff level rated on 1–5 scale with text evidence; deflation = payoff < buildup |

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
| Shared audit (3-7) | Yes | Yes | Yes |
| Unique (8) | Yes | Yes | Yes |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered → final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
