# Generative Test: shenbi-faction-builder

## Skill Under Test
`skills/shenbi-faction-builder/SKILL.md`

## Test Setup
A novel project exists with completed worldbuilding and character design output. No faction files exist yet.

## Agent Task
Run shenbi-faction-builder using the worldbuilding and character output as context. Produce all required faction files in `world/factions/` and `world/faction-relations.md`. Ensure every faction has at least one internal factional split, all behavior is explainable by interest logic (no "evil for evil's sake"), ≥2 factions have explicit relationships, all referenced anchor characters exist in character files, behavioral predictability patterns are defined, and faction descriptions are narrative prose.

## Seed Input
Worldbuilding + character output produced by prior skills from `tests/fixtures/outline-example.md`
