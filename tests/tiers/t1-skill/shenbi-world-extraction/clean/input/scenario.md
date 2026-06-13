# Clean Test: shenbi-world-extraction

## Skill Under Test
`skills/shenbi-world-extraction/SKILL.md`

## Test Setup
A fantasy novel manuscript with 20 chapters has been analyzed. The world extraction has been correctly run, producing `tests/fixtures/chapter-plan-example.md`, `tests/fixtures/chapter-plan-example.md`, `tests/fixtures/chapter-plan-example.md`, `tests/fixtures/chapter-plan-example.md`, and `tests/fixtures/chapter-plan-example.md`.

All output is correct:
- Every rule has >=2 independent textual evidence citations with chapter.paragraph references
- Rules are inferred from both successes and failures/avoidances
- Power system includes level names, advancement conditions, ability boundaries, and costs
- Extracted rules don't contradict story bible narrative
- Top locations have atmosphere, function, and first appearance
- story_bible.md is exactly 4 paragraphs of narrative prose
- rules.md is structured with evidence sections

## Scenario
All world extraction output is correct and follows all skill rules.

## Agent Task
Run shenbi-world-extraction quality check on the extracted world files. Expected result: report zero issues.
