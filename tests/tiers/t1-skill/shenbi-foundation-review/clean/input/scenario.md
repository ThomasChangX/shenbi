# Clean Test: shenbi-foundation-review

## Skill Under Test
`skills/shenbi-foundation-review/SKILL.md`

## Test Setup
A novel project's foundation has been reviewed at `tests/fixtures/report-example.txt`. The review is fully correct:
- Premise clarity: 21/25
- Core conflict strength: 22/30
- Character foundations: 20/25
- World consistency: 15/20
- Total score: 85/100 (above 80-point minimum)
- Core-conflict score 22/30 (above 18/30 threshold, no veto needed)
- Every deduction has a concrete improvement suggestion (file, paragraph, what to change)
- All 5 dimensions scored independently
- All scores based on existing content only
- Verdict: PASS

## Scenario
All foundation review output is correct and follows all skill rules. No defects present.

## Agent Task
Run shenbi-foundation-review quality check on the review output. Expected result: report zero issues.
