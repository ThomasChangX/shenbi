# Bug-Hunt Test: shenbi-location-builder

## Skill Under Test
`skills/shenbi-location-builder/SKILL.md`

## Test Setup
A novel project exists with location output:
- `tests/fixtures/chapter-plan-example.md` — capital city description
- `tests/fixtures/chapter-plan-example.md` — port city description
- `tests/fixtures/chapter-plan-example.md` — frontier fort description
- `tests/fixtures/chapter-plan-example.md` — overview map with distances

## Scenario
The location design has been generated. In `tests/fixtures/chapter-plan-example.md`, the travel time from the capital to the port city is stated as "three days by horse." In `tests/fixtures/chapter-plan-example.md`, the travel time from the port city to the capital is stated as "a half-day ride." These two descriptions of the same route contradict each other, violating spatial consistency.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-plan-example.md` vs `tests/fixtures/chapter-plan-example.md` | Travel time between capital and port city is "three days by horse" in capital.md but "a half-day ride" in port-city.md — direct contradiction | error |

## Agent Task
Run shenbi-location-builder quality check on the existing location output. The agent must detect the contradictory travel times between the two locations.
