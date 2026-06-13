# Bug-Hunt Test: shenbi-pacing-design

## Skill Under Test
`skills/shenbi-pacing-design/SKILL.md`

## Test Setup
A novel project exists with pacing design output:
- `tests/fixtures/chapter-plan-example.md` — pacing cycles, scene types, three-line balance
- `tests/fixtures/chapter-plan-example.md` — catalog of scene types with detection criteria

## Scenario
The pacing design has been generated. Upon review of the pacing cycles, Cycle 3 (chapters 18-24) includes three of the four required beats: buildup (chapter 18-19), escalation (chapter 20-21), and explosion (chapter 22-23). However, the aftermath beat is completely missing — the cycle jumps directly from the explosion into the next cycle's buildup. This violates the four-beat completeness requirement.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-plan-example.md`: Cycle 3 (chapters 18-24) | Missing "aftermath" beat — cycle has only buildup, escalation, explosion | error |

## Agent Task
Run shenbi-pacing-design quality check on the existing pacing output. The agent must detect the pacing cycle missing the aftermath beat.
