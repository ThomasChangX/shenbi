# T1 Rubric: shenbi-style-polishing

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Content preservation | 20% | Zero changes to plot, character behavior, or emotional tone |
| 4 | Word count stability | 15% | Changes bounded to +-15% |
| 5 | AI-flavor avoidance | 15% | Polishing does not introduce AI-typical phrasing |
| 6 | Style fidelity | 15% | If style_profile.md exists, polish respects it |
| 7 | Restraint | 10% | Does not over-polish or rewrite |
| 8 | Report completeness | 5% | Polishing report lists all changes with before/after |
| 9 | Structural flag quality | 5% | [polisher-note] annotations are specific and actionable |

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
