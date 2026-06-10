# Clean Test: shenbi-chapter-drafting

## Skill Under Test
`skills/shenbi-chapter-drafting/SKILL.md`

## Test Setup
A novel project exists with a completed chapter memo at `plans/chapter-7-plan.md`. The agent has drafted chapter 7 and the draft at `drafts/chapter-7.md` is fully correct:
- PRE_WRITE_CHECK completed and logged before drafting
- Chapter follows all memo specifications (plan compliance)
- Zero AI-typical transition word overuse (density well under 1/3000)
- All dialogue matches character voice profiles
- Emotions shown through action/sensation, not stated directly
- Last 300 words create strong pull (chapter-end hook)
- All foreshadowing items from memo present in text
- Varied paragraph lengths throughout
- No meta-narrative prose

## Scenario
All drafted chapter content is correct and follows all skill rules. No defects present.

## Agent Task
Run shenbi-chapter-drafting quality check on the drafted chapter. Expected result: report zero issues.
