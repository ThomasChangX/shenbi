# T1 Rubric: shenbi-foreshadowing-plant

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Budget enforcement | 20% | ≤8 operations per chapter; violation = 0 |
| 4 | Metadata completeness | 15% | All required fields present; depends_on never omitted |
| 5 | Smokescreen accountability | 15% | Every SMOKESCREEN has documented exit strategy |
| 6 | Existing hook awareness | 15% | Reads pending_hooks.md first; no duplication/contradiction |
| 7 | Strategic placement | 10% | Planting guidance references scene type appropriateness |
| 8 | Type/dimension classification | 10% | Hook type (GENUINE/SMOKESCREEN/SIDE_SHADOW) and dimension (THEMATIC/CHARACTER/SYMBOLIC/STRUCTURAL) assigned per taxonomy |

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
