# Clean Test: shenbi-location-builder

## Skill Under Test
`skills/shenbi-location-builder/SKILL.md`

## Test Setup
A novel project exists with complete, correct location output:
- `world/locations/capital.md` — narrative prose with sensory signatures, spatial layout, consistent travel times
- `world/locations/port-city.md` — narrative prose with sensory signatures, consistent travel times
- `world/locations/frontier-fort.md` — narrative prose with sensory signatures, consistent travel times
- `world/locations-map.md` — overview map with consistent distances

All travel times and distances are consistent across all location files. Each location has a primary plot function, sensory signatures, and walk-through-able spatial layouts.

## Scenario
All location content is correct and follows all skill rules. No contradictory distances, no missing atmosphere, no format violations.

## Agent Task
Run shenbi-location-builder quality check on the existing output. Expected result: report zero issues.
