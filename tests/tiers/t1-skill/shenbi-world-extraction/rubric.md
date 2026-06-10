# T1 Rubric: shenbi-world-extraction

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Rule evidence threshold | 20% | Each rule has >=2 independent textual evidence citations with chapter.paragraph references |
| 4 | Violation-based inference | 15% | Rules inferred from failures and avoidances, not just successes |
| 5 | Power system completeness | 15% | Level names, advancement conditions, ability boundaries, and costs all present |
| 6 | Consistency | 10% | Extracted rules don't contradict story bible narrative |
| 7 | Location coverage | 10% | Top locations extracted with atmosphere, function, and first appearance |
| 8 | Prose format | 15% | story_bible.md is 4-paragraph narrative prose; rules.md is structured with evidence |

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
