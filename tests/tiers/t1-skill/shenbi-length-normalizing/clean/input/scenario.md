# Clean Test: shenbi-length-normalizing

## Skill Under Test
`skills/shenbi-length-normalizing/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `tests/fixtures/chapter-draft-example.md` (4800 words). The target chapter length is 4000 words. The agent ran length normalization and produced `tests/fixtures/chapter-draft-example.md` with a consistency checklist at `tests/fixtures/report-example.txt`.

The normalization is fully correct:
- Final word count within target +-15% (approximately 3800-4200 words)
- No events added or removed; same 3 scenes as original
- No character behavior changes
- Voice preserved; no AI-typical phrasing introduced
- Any compression deepens content, not pads
- Consistency checklist present and confirms no narrative changes
- 25% floor gate respected (compression ratio within bounds)

## Scenario
All normalized output is correct and follows all skill rules. Length adjusted within range with no narrative changes.

## Agent Task
Run shenbi-length-normalizing quality check on the normalized output. Expected result: report zero issues.
