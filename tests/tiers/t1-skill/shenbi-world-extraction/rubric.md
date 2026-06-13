# T1 Rubric: shenbi-world-extraction

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Rule evidence threshold | 20% | Each rule has >=2 independent textual evidence citations with chapter.paragraph references |
| 4 | Violation-based inference | 15% | Rules inferred from failures and avoidances, not just successes |
| 5 | Power system completeness | 15% | Level names, advancement conditions, ability boundaries, and costs all present |
| 6 | Consistency | 10% | Extracted rules don't contradict story bible narrative |
| 7 | Location coverage | 10% | Top locations extracted with atmosphere, function, and first appearance |
| 8 | Prose format | 15% | story_bible.md is 4-paragraph narrative prose; rules.md is structured with evidence |

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

### Rule Evidence Requirements

For dimensions that check rule-type evidence, the provenance of references differs by rule category:

| Rule category | Rule names | Evidence requirement |
|--------------|-----------|---------------------|
| Definition-type | 灵能守恒, 位面物理差, 种姓禁锢 | ≥2 references from world documents OR chapter text |
| Demonstration-type | 金手指边界, 认知摩擦, 革命组织 | ≥2 references from chapter text specifically |

**Note:** Definition-type rules describe world constraints (laws, physics, social structures) and may be evidenced by world-building documents or narrative text. Demonstration-type rules describe observable behaviors (protagonist power limits, reader-author knowledge gaps, revolution dynamics) that must be evidenced by in-chapter occurrences. This distinction prevents scoring rules as "evidenced" when only world documents mention them without narrative demonstration.

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered -> final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
