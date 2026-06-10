# T1 Rubric: shenbi-volume-outlining

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | OKR executability | 20% | KRs map to specific chapter ranges; no vague statements |
| 4 | Tension curve design | 15% | Wave pattern (buildup/rising/explosion/aftermath) |
| 5 | Cross-volume bridging | 15% | Volume ending leaves ≥1 tangible hook |
| 6 | Golden chapters accommodation | 10% | Early chapters may deviate for world-building |
| 7 | Conflict advancement | 15% | Surface/personal/deep conflicts explicitly advanced |
| 8 | Chapter range realism | 10% | Chapter counts match KR complexity |

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
