# Clean Test: shenbi-short-outline

## Skill Under Test
`skills/shenbi-short-outline/SKILL.md`

## Test Setup
A short novel project (20 chapters) has its `tests/fixtures/novel-example.json` and `tests/fixtures/author-intent-example.md` set up. The short outline has been correctly run, producing `tests/fixtures/short-story-map-example.md`.

All output is correct:
- 3 steps executed: generate -> review -> revise
- Every chapter advances >=1 thread
- Act proportioning: Act 1 = 4 chapters (20%), Act 2 = 12 chapters (60%), Act 3 = 4 chapters (20%)
- Zero dead chapters — no chapter has task = "transition"
- Thread limit: 1 subplot + 1 emotional arc
- All turning points are genuine reversals

## Scenario
All short outline output is correct and follows all skill rules.

## Agent Task
Run shenbi-short-outline quality check on the outline. Expected result: report zero issues.
