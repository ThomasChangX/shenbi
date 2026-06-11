# T1 Rubric: shenbi-context-composing

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Completeness | 20% | All P1 items present; higher-priority items never trimmed before lower |
| 4 | Accuracy | 15% | Extracted summaries match source truth files word-for-word for key facts |
| 5 | Hook urgency calculation | 15% | Computes (current_chapter - last_reinforced) / max_distance |
| 6 | Ending diversity check | 15% | Flags if recent 3 chapters share same ending pattern |
| 7 | Recency | 10% | Only summaries from last 3 chapters and hooks with urgency > 0.5 included |
| 8 | Hook debt brief quality | 10% | Debt brief lists every active hook with status, silence chapters, and action suggestion |

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
