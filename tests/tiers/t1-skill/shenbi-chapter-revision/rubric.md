# T1 Rubric: shenbi-chapter-revision

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Non-regression | 20% | Blocking/critical/AI-trace counts do not increase |
| 4 | Scope discipline | 15% | Only fixes audit findings; no unrelated changes |
| 5 | Length constraint | 15% | Change within ±15% of original length |
| 6 | Fallback correctness | 10% | Best-version selected by lowest weighted issue count; ties broken by most recent version |
| 7 | Fix accuracy | 15% | Targeted fix resolves the specific issue found |
| 8 | Content preservation | 10% | Plot, character, foreshadowing unchanged |

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
