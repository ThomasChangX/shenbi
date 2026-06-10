# T1 Rubric: shenbi-location-builder

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Spatial consistency | 20% | Distances/directions/travel times never contradict established facts |
| 4 | Atmosphere quality | 15% | Sensory signatures (sight/sound/smell) and time-of-day associations |
| 5 | Prose format | 15% | Narrative prose, not bullet-point feature lists |
| 6 | Functional clarity | 15% | Each location has a primary plot function |
| 7 | Walk-through-ability | 10% | Spatial layout detailed enough to mentally "walk through" |
| 8 | Cross-location consistency | 10% | New locations don't break distance/travel time to existing ones |

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
| Prose/narrative quality (dim 5) | No | No | Yes |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered → final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
