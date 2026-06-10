# Clean Test: shenbi-style-polishing

## Skill Under Test
`skills/shenbi-style-polishing/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `drafts/chapter-7.md`. The chapter has been polished and the result is at `drafts/chapter-7-polished.md`. A polishing report is at `reports/chapter-7-polish-report.md`.

The polishing is fully correct:
- All changes are purely prose style improvements (sentence rhythm, word choice, pacing of descriptions)
- Zero content changes: no plot alterations, no character behavior changes, no emotional tone shifts
- Word count within +-15% of original
- No AI-typical phrasing introduced
- Polishing report lists all changes with before/after pairs
- All [polisher-note] annotations are specific and actionable
- No over-polishing or rewriting

## Scenario
All polished content is correct and follows all skill rules. Polishing only touched prose style with zero content changes.

## Agent Task
Run shenbi-style-polishing quality check comparing the original draft with the polished version. Expected result: report zero issues.
