# Bug-Hunt Test: shenbi-story-architecture

## Skill Under Test
`skills/shenbi-story-architecture/SKILL.md`

## Test Setup
A novel project exists with story architecture output:
- `story/story_frame.md` — narrative prose story frame with conflict layers
- `story/okr.md` — objectives and key results for the story
- `story/volume_map.md` — volume structure
- `story/foreshadowing.md` — foreshadowing lines

## Scenario
The story architecture has been generated. Upon review of the OKR file, one Key Result is vague and immeasurable: "protagonist grows stronger." This violates the OKR executability requirement that KRs must be measurable and map to specific chapter ranges.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `story/okr.md`: KR-3 under Objective 2 | KR states "protagonist grows stronger" with no measurable criteria and no chapter range mapping | error |

## Agent Task
Run shenbi-story-architecture quality check on the existing architecture output. The agent must detect the vague, unmeasurable Key Result.
