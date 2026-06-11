# Generative Test: shenbi-style-learning

## Skill Under Test
`skills/shenbi-style-learning/SKILL.md`

## Test Setup
A novel project exists with reference writing samples from the human author at `samples/reference-texts/`. There are 5 reference texts totaling approximately 30,000 words, sufficient for statistical analysis.

## Agent Task
Run shenbi-style-learning on the reference texts to produce a style profile. The agent must:
1. Compute all 7 statistical dimensions (average sentence length, vocabulary distribution, dialogue-to-narrative ratio, paragraph length distribution, sentence structure patterns, word frequency analysis, rhythm metrics)
2. Report only objective statistics — "what is," never "what is good or bad"
3. Enforce minimum sample size; flag if insufficient data
4. Ensure reproducibility (same input must produce identical output)
5. Structure the profile for downstream skills (style-polishing, anti-detect) to reference

## Seed Input
Reference writing samples from `samples/reference-texts/`
