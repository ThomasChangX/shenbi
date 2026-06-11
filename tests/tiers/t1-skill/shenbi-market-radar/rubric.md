# T1 Rubric: shenbi-market-radar

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Data-backed claims | 20% | Every recommendation references specific leaderboard rank or trend data point |
| 4 | Saturation detection | 15% | Element occurrence > 60% in top-20 titles flagged as saturated |
| 5 | Trend vs. imitation distinction | 15% | Each trend signal includes a differentiation suggestion |
| 6 | Decision checklist actionability | 15% | Every item is a single action with one-line rationale |
| 7 | Opening strategy relevance | 10% | Strategy tied to specific genre + platform data |
| 8 | Benchmark identification | 10% | >=2 competitive works named with rationale |

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
