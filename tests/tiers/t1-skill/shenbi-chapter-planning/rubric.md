# T1 Rubric: shenbi-chapter-planning

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Goal derivation rigor | 15% | Follows priority chain: instruction > override > volume KR > focus > intent |
| 4 | Reader expectation management | 15% | Explicitly states what readers wait for and create/delay/satisfy strategy |
| 5 | Hook accounting | 15% | All hooks tracked; pressured hooks advanced after 5+ chapters silence |
| 6 | Golden chapters discipline | 10% | First N chapters enforce extra constraints |
| 7 | End-of-chapter change | 15% | 1–3 concrete changes defined (information/relationship/physical/power) |
| 8 | Memo 8-section completeness | 10% | All 8 sections populated |
| 9 | Prohibition specificity | 5% | "Do not do" list names specific avoid-patterns, not generic advice |

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
