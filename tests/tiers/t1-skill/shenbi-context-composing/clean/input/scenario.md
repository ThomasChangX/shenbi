# Clean Test: shenbi-context-composing

## Skill Under Test
`skills/shenbi-context-composing/SKILL.md`

## Test Setup
A novel project exists with correct context assembly output for chapter 10:
- P1 (chapter plan memo): complete, no sections trimmed
- P2 (recent summaries): last 3 chapter summaries included (chapters 7-9)
- P3 (active hooks): top 3 hooks by urgency, correctly computed as (current_chapter - last_reinforced) / max_distance
- P4 (drift guidance): included in full
- P5 (world rules): 5 most relevant rules
- P6 (character states): only chapter 10 cast
- P7 (style profile): summary section only
- Hook debt brief lists every active hook with status, silence chapters, and action suggestion
- Ending diversity check performed: recent 3 chapters have different ending patterns (cliffhanger, resolution, open question)

## Scenario
All context assembly content is correct and follows all skill rules. Priority ordering is respected, no P1 items trimmed before lower-priority items.

## Agent Task
Run shenbi-context-composing quality check on the existing context assembly. Expected result: report zero issues.
