# T1 Rubric: shenbi-character-design

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Voice distinctness | 20% | Each major character has unique speech markers; interchangeable dialogue = fail |
| 4 | Arc definition | 15% | Protagonist has start state, turning point, end state; missing arc = 0 |
| 5 | Motivation depth | 15% | Surface goals AND deep motivations both explicit |
| 6 | Minor character respect | 10% | Minor characters have agency and independent motivation |
| 7 | Relationship coherence | 10% | Matrix consistent with character profiles |
| 8 | Voice profile operability | 10% | Patterns specific enough for downstream audit skills to use |
| 9 | Fear/weakness grounding | 5% | Every character has explicit fears |

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
