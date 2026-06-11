# T1 Rubric: shenbi-plot-thread-weaver

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | No blank chapters | 20% | Every chapter advances ≥1 thread |
| 4 | Long-line contact discipline | 15% | A-lines don't exceed max_gap (default 2 chapters for P0) |
| 5 | Short-line closure | 15% | C-lines resolve within their planned span |
| 6 | Climax window coordination | 15% | Subplot climaxes complement volume climaxes |
| 7 | Crossing point purpose | 10% | Thread crossings serve dramatic effect |
| 8 | Priority classification accuracy | 10% | P0 = novel-critical, P1 = volume-critical, P2 = arc-supporting, P3 = flavor |

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
