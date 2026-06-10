# T1 Rubric: shenbi-faction-builder

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Interest-driven realism | 20% | Faction behavior explainable by interest logic; no "evil for evil's sake" |
| 4 | Internal conflict | 15% | Every faction has ≥1 internal factional split |
| 5 | Cross-faction dynamics | 15% | ≥2 factions have explicit relationships |
| 6 | Anchor character consistency | 15% | Referenced characters exist in characters/*.md |
| 7 | Behavioral predictability | 10% | "In situation X, faction does Y" patterns defined |
| 8 | Prose quality | 10% | Faction descriptions are narrative prose |

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
| Prose/narrative quality (dim 8) | No | No | Yes |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered → final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
