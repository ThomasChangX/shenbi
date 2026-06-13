# Clean Test: shenbi-story-architecture

## Skill Under Test
`skills/shenbi-story-architecture/SKILL.md`

## Test Setup
A novel project exists with a complete, correct story architecture:
- `tests/fixtures/chapter-plan-example.md` — narrative prose paragraphs (no bullet lists), with three mutually reinforcing conflict layers
- `tests/fixtures/chapter-plan-example.md` — all KRs are measurable with specific chapter ranges
- `tests/fixtures/outline-example.md` — volume structure supports full novel length
- `tests/fixtures/pending-hooks-example.md` — ≥3 foreshadowing lines seeded

All KRs are concrete and measurable. The front-stage and back-stage storylines are both defined. The three conflict layers are mutually reinforcing.

## Scenario
All story architecture content is correct and follows all skill rules. No vague KRs, no missing conflict layers, no prose format violations.

## Agent Task
Run shenbi-story-architecture quality check on the existing output. Expected result: report zero issues.
