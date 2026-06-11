# Bug-Hunt Test: shenbi-worldbuilding

## Skill Under Test
`skills/shenbi-worldbuilding/SKILL.md`

## Test Setup
A novel project exists with the following worldbuilding files already generated:
- `world/rules.md` — hard rules and soft rules
- `world/story_bible.md` — narrative prose world bible
- `world/map.md` — geographical overview
- `world/undercurrent.md` — hidden conflict seeds

## Scenario
The worldbuilding output has been generated for a cultivation-based fantasy novel. Upon review of `world/rules.md`, two hard rules directly contradict each other. The skill should detect this inconsistency during its quality pass.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `world/rules.md`: hard rules section | Hard Rule 3 states "spiritual energy is finite and depletes with use" while Hard Rule 7 states "spiritual energy regenerates infinitely over time for all cultivators" | error |

## Agent Task
Run shenbi-worldbuilding quality check on the existing worldbuilding output. The agent must detect the contradiction between Hard Rule 3 and Hard Rule 7.
