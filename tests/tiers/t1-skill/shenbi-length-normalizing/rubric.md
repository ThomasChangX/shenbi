# T1 Rubric: shenbi-length-normalizing

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Narrative preservation | 20% | No events added/removed; no character behavior changes |
| 4 | 25% floor gate | 15% | Rejects if compression would be too severe |
| 5 | Voice preservation | 15% | Expansion does not introduce AI-typical phrasing |
| 6 | Range compliance | 15% | Final word count within target +-15% (soft), +-30% (hard) |
| 7 | Meaningful expansion | 10% | Expansion deepens content rather than padding |
| 8 | Consistency checklist | 10% | Confirms no narrative changes |

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
