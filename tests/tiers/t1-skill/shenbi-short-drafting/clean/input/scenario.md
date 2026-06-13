# Clean Test: shenbi-short-drafting

## Skill Under Test
`skills/shenbi-short-drafting/SKILL.md`

## Test Setup
A short novel project (12 chapters) has a completed outline at `tests/fixtures/short-story-map-example.md`. The short drafting has been correctly run, producing all 12 chapters and a batch summary.

All output is correct:
- All chapters generated strictly in order (each chapter's truth files exist before the next chapter starts)
- Every chapter passed all audit checks before acceptance
- Cross-chapter consistency maintained: position, timeline, information, relationships, style continuous
- Revision discipline maintained: no chapter exceeded 3 revision rounds
- Batch summary complete with per-chapter status table (word count, audit result, revision rounds)

## Scenario
All short drafting output is correct and follows all skill rules.

## Agent Task
Run shenbi-short-drafting quality check on the batch output. Expected result: report zero issues.
