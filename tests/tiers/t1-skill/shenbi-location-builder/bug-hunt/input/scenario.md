# Bug-Hunt Test: shenbi-location-builder

## Skill Under Test
`skills/shenbi-location-builder/SKILL.md`

## Test Setup
A novel project exists with location output:
- `world/locations/capital.md` — capital city description
- `world/locations/port-city.md` — port city description
- `world/locations/frontier-fort.md` — frontier fort description
- `world/locations-map.md` — overview map with distances

## Scenario
The location design has been generated. In `world/locations/capital.md`, the travel time from the capital to the port city is stated as "three days by horse." In `world/locations/port-city.md`, the travel time from the port city to the capital is stated as "a half-day ride." These two descriptions of the same route contradict each other, violating spatial consistency.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `world/locations/capital.md` vs `world/locations/port-city.md` | Travel time between capital and port city is "three days by horse" in capital.md but "a half-day ride" in port-city.md — direct contradiction | error |

## Agent Task
Run shenbi-location-builder quality check on the existing location output. The agent must detect the contradictory travel times between the two locations.
