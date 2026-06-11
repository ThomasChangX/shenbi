# Clean Test: shenbi-intent-management

## Skill Under Test
`skills/shenbi-intent-management/SKILL.md`

## Test Setup
A novel project has the following state:
- Human author provided intent: "Focus on developing the rivalry between Lin and Zhao; I want more tension in their interactions."
- Drift guidance at `guidance/drift-chapter-14.md` contains 3 warning-level items about pacing, sensory detail, and dialogue voice.
- `truth/author_intent.md` contains the human's creative vision.

The output at `truth/current_focus.md` is fully correct:
- Contains only human-provided intent items and drift guidance items
- No AI-generated creative suggestions
- All drift guidance items merged into current focus
- P0/P1/P2 priorities assigned per definitions
- Timestamp is after the most recent audit/drift
- YAML frontmatter schema followed for both author_intent.md and current_focus.md

## Scenario
All intent management output is correct and follows all skill rules. No defects present.

## Agent Task
Run shenbi-intent-management quality check on the current_focus.md output. Expected result: report zero issues.
