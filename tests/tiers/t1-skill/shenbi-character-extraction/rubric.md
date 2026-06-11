# T1 Rubric: shenbi-character-extraction

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Evidence grounding | 25% | Every personality tag, speech pattern, and relationship has >=1 quoted passage with chapter.paragraph reference |
| 4 | Voice fingerprint accuracy | 20% | Statistical extraction from actual dialogue |
| 5 | Arc evidence | 15% | Start and turning points backed by chapter-specific behavioral evidence |
| 6 | No fabrication | 15% | Non-derivable items marked "unconfirmed" |
| 7 | Relationship network completeness | 10% | All named character pairs with interaction scenes have relationship entries |

## Kill Switches by Test Type

### Bug-Hunt Kill Switches
- Content not groundable to source text → total score = 0
- Missed planted defect (false negative) -> total score = 0
- HARD-GATE violation -> total score = 0

### Clean Kill Switches
- Content not groundable to source text → total score = 0
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
