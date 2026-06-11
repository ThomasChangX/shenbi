# Clean Test: shenbi-style-learning

## Skill Under Test
`skills/shenbi-style-learning/SKILL.md`

## Test Setup
A novel project exists with reference writing samples at `samples/reference-texts/`. The agent has run style learning and produced a style profile at `config/style_profile.md`.

The style profile is fully correct:
- All 7 statistical dimensions computed and present
- All metrics are objective statistics: average sentence length, vocabulary distribution, dialogue-to-narrative ratio, paragraph length distribution, sentence structure patterns, word frequency analysis, rhythm metrics
- Zero subjective judgments — no "good/bad/strong/weak" language anywhere
- Profile is structured for downstream skills to reference
- Sample size meets minimum threshold
- Computations are deterministic and reproducible

## Scenario
All style profile content is correct and follows all skill rules. Purely objective statistics with no subjective assessments.

## Agent Task
Run shenbi-style-learning quality check on the produced style profile. Expected result: report zero issues.
