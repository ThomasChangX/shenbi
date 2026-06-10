# Generative Test: shenbi-location-builder

## Skill Under Test
`skills/shenbi-location-builder/SKILL.md`

## Test Setup
A novel project exists with completed worldbuilding output including the world map. No location files exist yet.

## Agent Task
Run shenbi-location-builder using the worldbuilding output as context. Produce all required location files in `world/locations/` and update `world/locations-map.md`. Ensure all distances, directions, and travel times are mutually consistent (no contradictions), each location has sensory signatures and time-of-day associations, descriptions are narrative prose (not bullet-point lists), each location has a primary plot function, spatial layouts are detailed enough to mentally "walk through," and new locations are consistent with existing world map data.

## Seed Input
Worldbuilding output produced by shenbi-worldbuilding from `tests/fixtures/outline-example.md`
