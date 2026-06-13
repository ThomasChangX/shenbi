# Bug-Hunt Test: shenbi-worldbuilding

## Skill Under Test
`skills/shenbi-worldbuilding/SKILL.md`

## Test Setup
A novel project exists with the following worldbuilding files already generated:
- `tests/fixtures/chapter-plan-example.md` — hard rules and soft rules
- `tests/fixtures/chapter-plan-example.md` — narrative prose world bible
- `tests/fixtures/chapter-plan-example.md` — geographical overview
- `tests/fixtures/chapter-plan-example.md` — hidden conflict seeds

## Scenario
The worldbuilding output has been generated for a cultivation-based fantasy novel. Upon review of `tests/fixtures/chapter-plan-example.md`, two hard rules directly contradict each other. The skill should detect this inconsistency during its quality pass.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-plan-example.md`: hard rules section | Hard Rule 3 states "spiritual energy is finite and depletes with use" while Hard Rule 7 states "spiritual energy regenerates infinitely over time for all cultivators" | error |

## Agent Task
Run shenbi-worldbuilding quality check on the existing worldbuilding output. The agent must detect the contradiction between Hard Rule 3 and Hard Rule 7.
