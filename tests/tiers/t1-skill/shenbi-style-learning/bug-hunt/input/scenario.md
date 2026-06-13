# Bug-Hunt Test: shenbi-style-learning

## Skill Under Test
`skills/shenbi-style-learning/SKILL.md`

## Test Setup
A novel project exists with reference writing samples at `tests/fixtures/samples/reference-texts/`. The agent has run style learning on the reference texts and produced a style profile at `tests/fixtures/style-profile-example.md`.

## Scenario
The style learning pass has been completed. The produced style profile at `tests/fixtures/style-profile-example.md` contains subjective judgments mixed with objective statistics. Specifically:

1. **Subjective quality judgments**: The profile includes statements like:
   - "This writing demonstrates excellent use of short sentences for pacing"
   - "The author's dialogue is particularly strong and engaging"
   - "The sentence variety is impressive and keeps readers interested"
   - "Weak transitions between paragraphs could be improved"

   These are subjective assessments of quality (good/bad), not objective measurements of what is.

2. **Missing statistical dimensions**: The profile only computes 5 of the 7 required statistical dimensions. Missing are: (a) dialogue-to-narrative ratio, and (b) paragraph length distribution.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/style-profile-example.md`: throughout prose analysis sections | Subjective judgments — profile contains "excellent," "strong," "impressive," "weak" assessments instead of pure objective statistics | error |
| `tests/fixtures/style-profile-example.md`: metrics section | Incomplete metrics — only 5 of 7 required statistical dimensions computed; missing dialogue-to-narrative ratio and paragraph length distribution | error |

## Agent Task
Run shenbi-style-learning quality check on the produced style profile. The agent must detect the subjective quality judgments (violating objectivity) and the missing statistical dimensions.
